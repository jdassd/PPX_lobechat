#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件管理相关 API
"""
from __future__ import annotations

import difflib
import filecmp
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable, List, Tuple

from api.core.context import checkpoint, iter_progress, publish_output, record_inputs, record_item, run_process
from api.core.journal import save_manifest
from api.core.outputs import atomic_output, output_asset, write_output

try:
    import py7zr
except ImportError:  # pragma: no cover
    py7zr = None

from api.utils import (
    api_error,
    api_success,
    clamp_int,
    ensure_directory,
    ensure_file_path,
    format_bytes,
)


class FileTool:
    """文件工具"""

    def _validate(self, options: Dict | None) -> Dict:
        if options is None:
            return {}
        if not isinstance(options, dict):
            raise ValueError('参数格式错误')
        return options

    @staticmethod
    def _validate_archive_members(target_dir: Path, names: Iterable[str]) -> None:
        """拒绝会写出目标目录或触发 Windows 特殊路径语义的归档成员。"""
        root = target_dir.resolve()
        for raw_name in names:
            name = str(raw_name or '').replace('\\', '/')
            member = PurePosixPath(name)
            parts = member.parts
            unsafe = (
                not name
                or '\x00' in name
                or member.is_absolute()
                or '..' in parts
                or any(':' in part for part in parts)
            )
            if unsafe:
                raise ValueError(f'归档包含不安全路径：{raw_name}')

            destination = root.joinpath(*(part for part in parts if part not in {'', '.'})).resolve()
            try:
                destination.relative_to(root)
            except ValueError as exc:
                raise ValueError(f'归档包含越界路径：{raw_name}') from exc

    def _iter_files(self, root: Path, recursive: bool = True) -> Iterable[Path]:
        if recursive:
            yield from (
                path
                for path in root.rglob('*')
                if path.is_file() and not {'.ppx_recycle', '.ppx_history'}.intersection(path.relative_to(root).parts)
            )
        else:
            yield from (path for path in root.iterdir() if path.is_file() and path.name not in {'.ppx_recycle', '.ppx_history'})

    def _parse_common_filters(self, options: Dict) -> Dict:
        extensions = options.get('extensions') or []
        if isinstance(extensions, str):
            extensions = [extensions]
        normalized_ext = [ext.lower().lstrip('.') for ext in extensions if ext]
        return {
            'keyword': str(options.get('keyword', '')).lower(),
            'extensions': normalized_ext,
            'min_size': int(options.get('minSize') or 0),
            'max_size': int(options.get('maxSize') or 0),
            'start_time': float(options.get('modifiedStart') or 0),
            'end_time': float(options.get('modifiedEnd') or 0),
            'recursive': bool(options.get('recursive', True)),
            'retry_inputs': options.get('_retryInputs'),
        }

    def _match_common_filters(self, path: Path, filters: Dict) -> bool:
        keyword = filters['keyword']
        extensions = filters['extensions']
        min_size = filters['min_size']
        max_size = filters['max_size']
        start_time = filters['start_time']
        end_time = filters['end_time']

        if keyword and keyword not in path.name.lower():
            return False
        if extensions and path.suffix.lower().lstrip('.') not in extensions:
            return False
        stat = path.stat()
        if min_size and stat.st_size < min_size:
            return False
        if max_size and stat.st_size > max_size:
            return False
        if start_time and stat.st_mtime < start_time:
            return False
        if end_time and stat.st_mtime > end_time:
            return False
        return True

    def _collect_filtered_files(self, directory: Path, filters: Dict, ensure_non_empty: bool = True) -> List[Path]:
        if filters.get('retry_inputs') is not None:
            files = [Path(raw).resolve() for raw in filters['retry_inputs']]
            for path in files:
                path.relative_to(directory.resolve())
        else:
            files = [
                path
                for path in self._iter_files(directory, recursive=filters['recursive'])
                if self._match_common_filters(path, filters)
            ]
        if ensure_non_empty and not files:
            raise ValueError('未匹配到任何文件')
        record_inputs(files)
        return files

    def _search_with_fd(self, directory: Path, filters: Dict, limit: int):
        """尝试使用 fd/fdfind 进行快速文件名搜索，不满足条件或失败时返回 None."""
        fd_path = shutil.which('fd') or shutil.which('fdfind')
        if not fd_path:
            return None
        keyword = filters['keyword']
        extensions = filters['extensions']
        args = [
            fd_path,
            '--hidden',
            '--follow',
            '--type',
            'f',
            '--max-results',
            str(limit),
        ]
        for ext in extensions:
            args += ['--extension', ext]
        pattern = keyword or ''
        if not pattern:
            # 使用空模式时 fd 需要一个通配符，这里使用 '.' 匹配全部文件
            pattern = '.'
        args.append(pattern)
        args.append(str(directory))
        try:
            proc = subprocess.run(args, capture_output=True, text=True)
        except Exception:
            return None
        # returncode 为 1 时表示无匹配结果，也视为正常
        if proc.returncode not in (0, 1):
            return None
        matched = []
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            path = Path(line)
            if not path.is_absolute():
                path = directory / path
            try:
                if not path.is_file():
                    continue
                if not self._match_common_filters(path, filters):
                    continue
                stat = path.stat()
            except OSError:
                continue
            matched.append({
                'name': path.name,
                'path': str(path),
                'size': stat.st_size,
                'sizeText': format_bytes(stat.st_size),
                'modified': stat.st_mtime,
                'ext': path.suffix.lower(),
            })
            if len(matched) >= limit:
                break
        return matched

    @staticmethod
    def _hash_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
        hasher = hashlib.sha256()
        with path.open('rb') as handler:
            for chunk in iter(lambda: handler.read(chunk_size), b''):
                checkpoint()
                hasher.update(chunk)
        return hasher.hexdigest()

    def _build_new_name(self, path: Path, rule: str, params: Dict, index: int) -> str:
        suffix = params.get('extension')
        if suffix:
            suffix = suffix if suffix.startswith('.') else f'.{suffix}'
        else:
            suffix = path.suffix
        stem = path.stem
        padding = max(1, int(params.get('padding') or len(str(index))))
        prefix = params.get('prefix') or 'file_'

        if rule == 'sequence':
            return f'{prefix}{str(index).zfill(padding)}{suffix}'
        if rule == 'timestamp':
            fmt = params.get('format', '%Y%m%d_%H%M%S')
            stamp = datetime.now().strftime(fmt)
            return f'{stamp}_{str(index).zfill(padding)}{suffix}'
        if rule == 'replace':
            search = params.get('search') or ''
            replace = params.get('replace') or ''
            return f"{stem.replace(search, replace)}{suffix}"
        if rule == 'regex':
            pattern = params.get('pattern')
            if not pattern:
                raise ValueError('请提供正则表达式')
            repl = params.get('replace') or ''
            new_stem = re.sub(pattern, repl, stem)
            return f'{new_stem}{suffix}'
        if rule == 'template':
            template = params.get('template') or '{name}_{index}'
            now = datetime.now()
            # 处理 {index:N} 格式的自定义padding
            def replace_index_with_padding(match):
                pad = int(match.group(1)) if match.group(1) else padding
                return str(index).zfill(pad)
            result = re.sub(r'\{index(?::(\d+))?\}', replace_index_with_padding, template)
            # 替换其他变量
            replacements = {
                '{name}': stem,
                '{ext}': suffix,
                '{date}': now.strftime('%Y%m%d'),
                '{time}': now.strftime('%H%M%S'),
                '{datetime}': now.strftime('%Y%m%d_%H%M%S'),
                '{year}': now.strftime('%Y'),
                '{month}': now.strftime('%m'),
                '{day}': now.strftime('%d'),
                '{hour}': now.strftime('%H'),
                '{minute}': now.strftime('%M'),
                '{second}': now.strftime('%S'),
            }
            for key, value in replacements.items():
                result = result.replace(key, value)
            # 如果模板已包含扩展名变量，则不再追加
            if '{ext}' in template:
                return result
            return f'{result}{suffix}'
        return f'{stem}_{index}{suffix}'

    def _sanitize_category_name(self, label: str) -> str:
        safe = re.sub(r'[<>:"/\\\\|?*]+', '_', (label or '').strip())
        safe = safe.strip('_') or '未分类'
        return safe[:80]

    def _read_text_file(self, path: Path, preferred: str | None) -> Tuple[str, str]:
        encodings = []
        if preferred:
            encodings.append(preferred)
        encodings.extend(['utf-8', 'utf-8-sig', 'gbk', 'latin-1'])
        for encoding in encodings:
            try:
                with path.open('r', encoding=encoding) as handler:
                    return handler.read(), encoding
            except UnicodeDecodeError:
                continue
        raise ValueError(f'无法按常见编码读取 {path.name}')

    def file_search(self, options: Dict | None = None):
        """文件搜索"""
        try:
            opts = self._validate(options)
            directory = ensure_directory(opts.get('directory'), auto_create=False)
            filters = self._parse_common_filters(opts)
            limit = clamp_int(opts.get('limit', 500), 50, 2000)

            # 优先尝试使用 fd 这类开源文件搜索引擎，加速大目录检索
            matched = self._search_with_fd(directory, filters, limit)
            if matched is None:
                matched = []
                for path in self._iter_files(directory, recursive=filters['recursive']):
                    if not self._match_common_filters(path, filters):
                        continue
                    stat = path.stat()
                    matched.append({
                        'name': path.name,
                        'path': str(path),
                        'size': stat.st_size,
                        'sizeText': format_bytes(stat.st_size),
                        'modified': stat.st_mtime,
                        'ext': path.suffix.lower(),
                    })
                    if len(matched) >= limit:
                        break
            return api_success('搜索完成', items=matched)
        except Exception as exc:
            return api_error(f'搜索失败：{exc}')

    def _collect_directory_stats(self, root: Path) -> Tuple[int, int, int, Counter, List[dict]]:
        total_size = 0
        file_count = 0
        dir_count = 0
        ext_counter: Counter = Counter()
        largest: List[dict] = []

        for dirpath, dirnames, filenames in os.walk(root):
            dir_count += len(dirnames)
            for filename in filenames:
                path = Path(dirpath) / filename
                try:
                    stat = path.stat()
                except OSError:
                    continue
                total_size += stat.st_size
                file_count += 1
                ext_counter[path.suffix.lower()] += 1
                largest.append({
                    'name': path.name,
                    'path': str(path),
                    'size': stat.st_size,
                })

        largest.sort(key=lambda item: item['size'], reverse=True)
        largest = largest[:10]
        return total_size, file_count, dir_count, ext_counter, largest

    def _iter_archive_entries(self, path: Path) -> Iterable[Tuple[Path, Path]]:
        if path.is_file():
            yield path, Path(path.name)
            return
        for root, _, files in os.walk(path):
            for filename in files:
                file_path = Path(root) / filename
                rel_path = file_path.relative_to(path.parent)
                yield file_path, rel_path

    def file_compress(self, options: Dict | None = None):
        """压缩打包"""
        try:
            opts = self._validate(options)
            raw_items = opts.get('items') or []
            if not raw_items:
                raise ValueError('请至少选择一个文件或文件夹')
            items = [Path(item if isinstance(item, str) else item.get('path')) for item in raw_items]
            for path in items:
                if not path.exists():
                    raise FileNotFoundError(f'路径不存在：{path}')
            fmt = str(opts.get('format', 'zip')).lower()
            output_dir = Path(opts.get('outputDir') or items[0].parent)
            output_dir.mkdir(parents=True, exist_ok=True)
            filename = opts.get('archiveName') or f'archive_{int(time.time())}'
            if fmt not in {'zip', '7z'}:
                raise ValueError('当前仅支持 ZIP 和 7Z')
            suffix = f'.{fmt}'
            dest = output_dir / f'{filename}{suffix}'

            with atomic_output(dest) as (temporary, dest):
                if fmt == 'zip':
                    password = str(opts.get('password') or '').strip()
                    if password:
                        # 使用 7-Zip 创建带密码的 ZIP（ZipCrypto），兼容常见解压工具
                        seven_zip = shutil.which('7z') or shutil.which('7za') or shutil.which('7zz')
                        if not seven_zip:
                            raise OSError('未检测到 7-Zip，暂不支持 ZIP 密码压缩，请改用 7Z 格式或安装 7-Zip')
                        common_root = os.path.commonpath([str(path.parent) for path in items])
                        rel_paths = [os.path.relpath(str(path), common_root) for path in items]
                        cmd = [
                            seven_zip,
                            'a',
                            '-tzip',
                            '-y',
                            f'-p{password}',
                            '-mem=ZipCrypto',
                            str(temporary),
                        ] + rel_paths
                        proc = subprocess.run(cmd, cwd=common_root, capture_output=True, text=True)
                        if proc.returncode != 0:
                            stderr = proc.stderr.strip() or '调用 7-Zip 创建带密码 ZIP 失败'
                            raise RuntimeError(stderr)
                    else:
                        compression = zipfile.ZIP_DEFLATED
                        with zipfile.ZipFile(temporary, 'w', compression=compression, compresslevel=6) as handler:
                            for path in iter_progress(items):
                                if path.is_dir():
                                    for file_path in path.rglob('*'):
                                        checkpoint()
                                        if file_path.resolve() in {temporary.resolve(), dest.resolve()}:
                                            continue
                                        if file_path.is_file():
                                            handler.write(file_path, file_path.relative_to(path.parent))
                                else:
                                    handler.write(path, arcname=path.name)
                else:
                    if py7zr is None:
                        raise ImportError('缺少 py7zr 依赖，请运行 pip install py7zr')
                    password = opts.get('password') or None
                    with py7zr.SevenZipFile(temporary, 'w', password=password) as handler:
                        for path in iter_progress(items):
                            handler.writeall(path, arcname=path.name)
            return api_success('压缩完成', file=str(dest))
        except Exception as exc:
            return api_error(f'压缩失败：{exc}')

    def file_decompress(self, options: Dict | None = None):
        """解压缩"""
        try:
            opts = self._validate(options)
            archive = ensure_file_path(opts.get('archiveFile'))
            target_dir = Path(opts.get('targetDir') or archive.parent / 'extract')
            target_dir.mkdir(parents=True, exist_ok=True)
            suffix = archive.suffix.lower()
            files = []
            with tempfile.TemporaryDirectory(prefix='.ppx-extract-', dir=target_dir) as staging:
                staging_path = Path(staging)
                if suffix == '.zip':
                    with zipfile.ZipFile(archive, 'r') as handler:
                        password = opts.get('password')
                        pwd = password.encode('utf-8') if password else None
                        self._validate_archive_members(staging_path, (item.filename for item in handler.infolist()))
                        for member in iter_progress(handler.infolist(), '正在验证并解压'):
                            if (member.external_attr >> 16) & 0o170000 == 0o120000:
                                raise ValueError('压缩包包含符号链接，未提取')
                            handler.extract(member, staging_path, pwd=pwd)
                elif suffix == '.7z':
                    if py7zr is None:
                        raise ImportError('缺少 py7zr 依赖')
                    with py7zr.SevenZipFile(archive, 'r', password=opts.get('password') or None) as handler:
                        self._validate_archive_members(staging_path, handler.getnames())
                        handler.extractall(staging_path)
                else:
                    raise ValueError('当前仅支持解压 ZIP / 7Z')
                for path in iter_progress(list(staging_path.rglob('*')), '正在提交解压结果'):
                    self._safe_child(staging_path, path)
                    if path.is_symlink():
                        raise ValueError('压缩包包含符号链接，未提交')
                    if path.is_file():
                        final = write_output(target_dir / path.relative_to(staging_path), lambda dest: shutil.copy2(path, dest), allow_empty=True)
                        files.append(str(final))
            return api_success('解压完成', outputDir=str(target_dir), files=files, outputAssets=[output_asset(path) for path in files])
        except Exception as exc:
            return api_error(f'解压失败：{exc}')

    def file_batch_copy(self, options: Dict | None = None):
        """批量复制"""
        try:
            opts = self._validate(options)
            source_dir = ensure_directory(opts.get('sourceDir') or opts.get('directory'), auto_create=False)
            target_dir = ensure_directory(opts.get('targetDir'), auto_create=True)
            filters = self._parse_common_filters(opts)
            filters['recursive'] = bool(opts.get('recursive', True))
            files = self._collect_filtered_files(source_dir, filters)
            conflict_policy = str(opts.get('conflictPolicy', 'skip')).lower()
            copied = 0
            skipped = 0
            total_bytes = 0
            assets, failures, preview = [], [], []
            for path in iter_progress(files, '正在复制文件'):
                relative = path.relative_to(source_dir)
                dest = target_dir / relative
                if dest.exists() and conflict_policy != 'overwrite':
                    skipped += 1
                    preview.append({'from': str(path), 'to': str(dest), 'action': 'skip', 'reason': '目标已存在'})
                    record_item(path, 'skipped', '目标已存在')
                    continue
                preview.append({'from': str(path), 'to': str(dest), 'action': 'copy', 'reason': '已有同名文件时生成副本'})
                if opts.get('dryRun'):
                    continue
                try:
                    dest = write_output(dest, lambda target: shutil.copy2(path, target), allow_empty=True)
                    assets.append(output_asset(dest))
                    copied += 1
                    total_bytes += path.stat().st_size
                    record_item(path, 'success', outputs=[assets[-1]])
                except Exception as exc:
                    checkpoint()
                    failures.append({'input': str(path), 'error': str(exc)})
                    record_item(path, 'failed', str(exc))
            return api_success(
                '复制预演完成' if opts.get('dryRun') else f'复制完成：{copied} 个成功，{len(failures)} 个失败，{skipped} 个跳过',
                copied=copied,
                skipped=skipped,
                size=total_bytes,
                sizeText=format_bytes(total_bytes),
                outputDir=str(target_dir),
                outputAssets=assets, failures=failures, preview=preview, dryRun=bool(opts.get('dryRun')),
                partial=bool(failures and copied), code=0 if copied or opts.get('dryRun') or not failures else -1,
            )
        except Exception as exc:
            return api_error(f'批量复制失败：{exc}')

    def file_batch_delete(self, options: Dict | None = None):
        """批量删除"""
        try:
            opts = self._validate(options)
            directory = ensure_directory(opts.get('directory'), auto_create=False)
            filters = self._parse_common_filters(opts)
            filters['recursive'] = bool(opts.get('recursive', True))
            files = self._collect_filtered_files(directory, filters)
            files = [path for path in files if '.ppx_recycle' not in path.relative_to(directory).parts]
            if not files:
                raise ValueError('未匹配到可安全删除的文件')
            dry_run = bool(opts.get('dryRun', False))
            preview = [str(path) for path in files]
            if dry_run:
                return api_success('预览删除列表', preview=preview, count=len(preview))
            # v2.3 只允许可恢复删除，并为每批操作写入可审计、可恢复的清单。
            batch_id = f'{int(time.time())}-{uuid.uuid4().hex[:8]}'
            recycle_dir = directory / '.ppx_recycle' / batch_id
            recycle_dir.mkdir(parents=True, exist_ok=True)
            total_size = 0
            manifest_items = []
            manifest = {'schemaVersion': 2, 'id': batch_id, 'directory': str(directory), 'createdAt': time.time(), 'items': manifest_items}
            manifest_path = recycle_dir / 'manifest.json'
            save_manifest(manifest_path, manifest)
            failures = []
            for path in iter_progress(files, '正在移入回收目录'):
                target = recycle_dir / path.relative_to(directory)
                record = {'original': str(path), 'recycled': str(target), 'size': 0, 'status': 'pending'}
                manifest_items.append(record)
                try:
                    file_size = path.stat().st_size
                    record['size'] = file_size
                    target.parent.mkdir(parents=True, exist_ok=True)
                    save_manifest(manifest_path, manifest)
                    shutil.move(str(path), str(target))
                    record['status'] = 'done'
                    total_size += file_size
                    publish_output(target)
                    record_item(path, 'success', outputs=[output_asset(target)])
                except Exception as exc:
                    checkpoint()
                    record['status'] = 'failed'
                    failures.append({'input': str(path), 'error': str(exc)})
                    record_item(path, 'failed', str(exc))
                finally:
                    save_manifest(manifest_path, manifest)
            payload = {
                'id': batch_id,
                'deleted': sum(item['status'] == 'done' for item in manifest_items),
                'size': total_size,
                'sizeText': format_bytes(total_size),
                'failures': failures, 'partial': bool(failures and any(item['status'] == 'done' for item in manifest_items)),
            }
            payload['recycleDir'] = str(recycle_dir)
            return api_success('已移入回收目录', code=0 if payload['deleted'] or not failures else -1, **payload)
        except Exception as exc:
            return api_error(f'批量删除失败：{exc}')

    def file_batch_rename(self, options: Dict | None = None):
        """批量改名"""
        try:
            opts = self._validate(options)
            directory = ensure_directory(opts.get('directory'), auto_create=False)
            filters = self._parse_common_filters(opts)
            filters['recursive'] = bool(opts.get('recursive', True))
            files = self._collect_filtered_files(directory, filters)
            rule = str(opts.get('rule', 'sequence')).lower()
            params = opts.get('ruleParams') or {}
            start_index = int(params.get('start', 1))
            dry_run = bool(opts.get('dryRun', False))
            renamed = []
            skipped = []
            transaction_id = f'{int(time.time())}-{uuid.uuid4().hex[:8]}' if not dry_run else ''
            history_dir = directory / '.ppx_history' / 'rename'
            manifest = {'schemaVersion': 2, 'id': transaction_id, 'directory': str(directory), 'createdAt': time.time(), 'mappings': []}
            manifest_path = history_dir / f'{transaction_id}.json'
            failures = []
            planned = set()
            for offset, path in enumerate(iter_progress(files, '正在重命名')):
                record = None
                try:
                    original_order = opts.get('_inputOrder') or {}
                    index = start_index + int(original_order.get(str(path), offset))
                    new_name = self._build_new_name(path, rule, params, index)
                    dest = path.with_name(new_name)
                    if dest == path or dest.exists() or os.path.normcase(str(dest)) in planned:
                        skipped.append(str(path))
                        record_item(path, 'skipped', '名称未改变' if dest == path else '目标已存在')
                        continue
                    record = {'from': str(path), 'to': str(dest), 'signature': self._hash_file(path) if not dry_run else None, 'status': 'pending'}
                    planned.add(os.path.normcase(str(dest)))
                    if not dry_run:
                        manifest['mappings'].append(record)
                        save_manifest(manifest_path, manifest)
                        dest = write_output(dest, lambda target: shutil.copy2(path, target), allow_empty=True)
                        record['to'] = str(dest)
                        save_manifest(manifest_path, manifest)
                        path.unlink()
                        record['status'] = 'done'
                        record_item(path, 'success', outputs=[output_asset(dest)])
                    renamed.append(record)
                except Exception as exc:
                    checkpoint()
                    if record:
                        record['status'] = 'failed'
                    failures.append({'input': str(path), 'error': str(exc)})
                    record_item(path, 'failed', str(exc))
                finally:
                    if not dry_run and record:
                        save_manifest(manifest_path, manifest)
            message = '重命名预览' if dry_run else '重命名完成'
            return api_success(message, renamed=renamed, skipped=skipped, dryRun=dry_run, transactionId=transaction_id,
                               failures=failures, partial=bool(failures and renamed), code=0 if renamed or not failures else -1)
        except Exception as exc:
            return api_error(f'批量改名失败：{exc}')

    @staticmethod
    def _safe_child(root: Path, candidate: Path) -> Path:
        resolved_root = root.resolve()
        resolved = candidate.resolve()
        try:
            resolved.relative_to(resolved_root)
        except ValueError as exc:
            raise ValueError('目标路径超出允许范围') from exc
        return resolved

    def _load_recycle_manifest(self, directory: Path, batch_dir: Path) -> Dict:
        recycle_root = directory / '.ppx_recycle'
        safe_batch = self._safe_child(recycle_root, batch_dir)
        manifest_path = safe_batch / 'manifest.json'
        if manifest_path.is_file():
            payload = json.loads(manifest_path.read_text(encoding='utf-8'))
            if isinstance(payload, dict) and isinstance(payload.get('items'), list):
                return payload
        items = []
        for path in safe_batch.rglob('*'):
            if not path.is_file() or path.name == 'manifest.json':
                continue
            relative = path.relative_to(safe_batch)
            items.append({'original': str(directory / relative), 'recycled': str(path), 'size': path.stat().st_size})
        return {
            'schemaVersion': 1,
            'id': safe_batch.name,
            'directory': str(directory),
            'createdAt': safe_batch.stat().st_mtime,
            'items': items,
        }

    def file_recycle_list(self, options: Dict | None = None):
        """列出指定目录内由 PPX 创建的可恢复删除批次。"""
        try:
            opts = self._validate(options)
            directory = ensure_directory(opts.get('directory'), auto_create=False)
            recycle_root = directory / '.ppx_recycle'
            if not recycle_root.is_dir():
                return api_success('回收站为空', batches=[])
            batches = []
            for batch_dir in sorted((path for path in recycle_root.iterdir() if path.is_dir()), reverse=True):
                manifest = self._load_recycle_manifest(directory, batch_dir)
                items = manifest.get('items') or []
                total_size = sum(int(item.get('size') or 0) for item in items)
                batches.append({
                    'id': manifest.get('id') or batch_dir.name,
                    'recycleDir': str(batch_dir),
                    'createdAt': float(manifest.get('createdAt') or batch_dir.stat().st_mtime),
                    'count': len(items),
                    'size': total_size,
                    'sizeText': format_bytes(total_size),
                    'files': [item.get('original') for item in items[:100]],
                })
            return api_success('回收站读取完成', batches=batches)
        except Exception as exc:
            return api_error(f'读取回收站失败：{exc}')

    def file_recycle_restore(self, options: Dict | None = None):
        """按批次恢复安全删除的文件，默认不覆盖已有文件。"""
        try:
            opts = self._validate(options)
            directory = ensure_directory(opts.get('directory'), auto_create=False)
            batch_id = str(opts.get('id') or '').strip()
            if not batch_id or Path(batch_id).name != batch_id:
                raise ValueError('回收批次编号无效')
            batch_dir = self._safe_child(directory / '.ppx_recycle', directory / '.ppx_recycle' / batch_id)
            if not batch_dir.is_dir():
                raise FileNotFoundError('回收批次不存在')
            manifest = self._load_recycle_manifest(directory, batch_dir)
            conflict_policy = str(opts.get('conflictPolicy') or 'rename').lower()
            restored = []
            skipped = []
            remaining = list(manifest.get('items') or [])
            failures = []
            for item in iter_progress(list(remaining), '正在恢复文件'):
                source = self._safe_child(batch_dir, Path(item.get('recycled') or ''))
                target = self._safe_child(directory, Path(item.get('original') or ''))
                if not source.is_file():
                    remaining.remove(item)
                    continue
                if target.exists():
                    if conflict_policy == 'skip':
                        skipped.append(str(target))
                        continue
                    index = 1
                    while True:
                        candidate = target.with_name(f'{target.stem}_restored_{index}{target.suffix}')
                        if not candidate.exists():
                            target = candidate
                            break
                        index += 1
                target.parent.mkdir(parents=True, exist_ok=True)
                try:
                    item['restoreTarget'] = str(target)
                    save_manifest(batch_dir / 'manifest.json', manifest)
                    target = write_output(target, lambda dest: shutil.copy2(source, dest), allow_empty=True)
                    source.unlink()
                    remaining.remove(item)
                    restored.append({'from': str(source), 'to': str(target)})
                except Exception as exc:
                    checkpoint()
                    failures.append({'input': str(source), 'error': str(exc)})
                finally:
                    manifest['items'] = remaining
                    save_manifest(batch_dir / 'manifest.json', manifest)
            if remaining:
                manifest['items'] = remaining
                save_manifest(batch_dir / 'manifest.json', manifest)
            else:
                (batch_dir / 'manifest.json').unlink(missing_ok=True)
                for folder in sorted([batch_dir, *(p for p in batch_dir.rglob('*') if p.is_dir())], key=lambda p: len(p.parts), reverse=True):
                    try:
                        folder.rmdir()
                    except OSError:
                        pass
            return api_success('文件恢复完成', restored=restored, skipped=skipped, restoredCount=len(restored), failures=failures,
                               partial=bool(failures and restored), code=0 if restored or not failures else -1)
        except Exception as exc:
            return api_error(f'恢复失败：{exc}')

    def file_recycle_purge(self, options: Dict | None = None):
        """永久清理一个回收批次，或清理超过保留天数的批次。"""
        try:
            opts = self._validate(options)
            directory = ensure_directory(opts.get('directory'), auto_create=False)
            recycle_root = directory / '.ppx_recycle'
            if not recycle_root.is_dir():
                return api_success('回收站为空', purged=0)
            batch_id = str(opts.get('id') or '').strip()
            older_days = max(0, int(opts.get('olderThanDays') or 0))
            threshold = time.time() - older_days * 86400
            candidates = []
            for batch_dir in recycle_root.iterdir():
                if not batch_dir.is_dir():
                    continue
                if batch_id and batch_dir.name != batch_id:
                    continue
                if not batch_id and older_days and batch_dir.stat().st_mtime > threshold:
                    continue
                candidates.append(self._safe_child(recycle_root, batch_dir))
            for batch_dir in candidates:
                shutil.rmtree(batch_dir, ignore_errors=False)
            return api_success('回收站清理完成', purged=len(candidates))
        except Exception as exc:
            return api_error(f'清理回收站失败：{exc}')

    def file_batch_rename_undo(self, options: Dict | None = None):
        """根据事务清单撤销一次批量重命名。"""
        try:
            opts = self._validate(options)
            directory = ensure_directory(opts.get('directory'), auto_create=False)
            transaction_id = str(opts.get('transactionId') or opts.get('id') or '').strip()
            if not transaction_id or Path(transaction_id).name != transaction_id:
                raise ValueError('重命名事务编号无效')
            history_root = directory / '.ppx_history' / 'rename'
            manifest_path = self._safe_child(history_root, history_root / f'{transaction_id}.json')
            if not manifest_path.is_file():
                raise FileNotFoundError('重命名事务不存在或已撤销')
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            restored = []
            skipped = []
            remaining = list(manifest.get('mappings') or [])
            for mapping in iter_progress(list(reversed(remaining)), '正在撤销重命名'):
                source = self._safe_child(directory, Path(mapping.get('to') or ''))
                target = self._safe_child(directory, Path(mapping.get('from') or ''))
                if not source.exists() and target.exists():
                    remaining.remove(mapping)
                    continue
                if not source.exists() or target.exists() or (mapping.get('signature') and self._hash_file(source) != mapping['signature']):
                    skipped.append({'from': str(source), 'to': str(target)})
                    continue
                source.rename(target)
                remaining.remove(mapping)
                manifest['mappings'] = remaining
                save_manifest(manifest_path, manifest)
                publish_output(target)
                restored.append({'from': str(source), 'to': str(target)})
            if not skipped:
                manifest_path.unlink()
            return api_success('批量重命名已撤销', restored=restored, skipped=skipped, restoredCount=len(restored))
        except Exception as exc:
            return api_error(f'撤销重命名失败：{exc}')

    def file_classify_undo(self, options: Dict | None = None):
        """Undo recorded classification; preserve files edited since processing."""
        try:
            opts = self._validate(options)
            directory = ensure_directory(opts.get('directory'), auto_create=False)
            transaction = str(opts.get('transactionId') or '')
            if not transaction or Path(transaction).name != transaction:
                raise ValueError('分类事务编号无效')
            manifest_path = directory / '.ppx_history' / 'classify' / f'{transaction}.json'
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            target_root = Path(manifest['targetDir'])
            restored, skipped = [], []
            for record in iter_progress(manifest['mappings'], '正在撤销分类'):
                if record.get('status') == 'undone':
                    continue
                source = self._safe_child(target_root, Path(record['to']))
                target = self._safe_child(directory, Path(record['from']))
                if not source.is_file() or not record.get('signature') or self._hash_file(source) != record['signature']:
                    skipped.append(record)
                    continue
                if manifest['operation'] == 'move':
                    if target.exists():
                        skipped.append(record)
                        continue
                    target = write_output(target, lambda dest: shutil.copy2(source, dest), allow_empty=True)
                    restored.append({'from': str(source), 'to': str(target)})
                source.unlink()
                record['status'] = 'undone'
                save_manifest(manifest_path, manifest)
            return api_success('分类撤销完成；已修改或冲突的文件保留', restored=restored, skipped=skipped,
                               restoredCount=len(restored), outputAssets=[output_asset(item['to']) for item in restored])
        except Exception as exc:
            return api_error(f'分类撤销失败：{exc}')

    def file_deduplicate(self, options: Dict | None = None):
        """文件去重"""
        try:
            opts = self._validate(options)
            directory = ensure_directory(opts.get('directory'), auto_create=False)
            mode = str(opts.get('mode', 'content')).lower()
            filters = self._parse_common_filters(opts)
            filters['recursive'] = bool(opts.get('recursive', True))
            limit = clamp_int(opts.get('limit', 5000), 100, 20000)
            groups: Dict[str, List[Path]] = {}
            scanned = 0
            for path in self._iter_files(directory, recursive=filters['recursive']):
                if not self._match_common_filters(path, filters):
                    continue
                key = path.name.lower() if mode == 'name' else self._hash_file(path)
                groups.setdefault(key, []).append(path)
                scanned += 1
                if scanned >= limit:
                    break
            duplicates = []
            space_saved = 0
            for items in groups.values():
                if len(items) < 2:
                    continue
                sizes = [item.stat().st_size for item in items]
                keep_size = max(sizes)
                space_saved += sum(sizes) - keep_size
                duplicates.append({
                    'count': len(items),
                    'sizeEach': format_bytes(sizes[0]),
                    'files': [str(item) for item in items],
                })
            return api_success(
                '去重扫描完成',
                groups=duplicates,
                totalGroups=len(duplicates),
                spaceSaved=format_bytes(space_saved),
                scanned=scanned,
            )
        except Exception as exc:
            return api_error(f'文件去重失败：{exc}')

    # -------------------- P2 功能 --------------------

    def file_auto_classify(self, options: Dict | None = None):
        """按类型/大小/日期分类整理"""
        try:
            opts = self._validate(options)
            directory = ensure_directory(opts.get('directory') or opts.get('sourceDir'), auto_create=False)
            target_dir_opt = opts.get('targetDir')
            if target_dir_opt:
                target_dir = ensure_directory(target_dir_opt, auto_create=True)
            else:
                target_dir = directory / '_classified'
                target_dir.mkdir(parents=True, exist_ok=True)
            mode = str(opts.get('mode', 'type')).lower()
            if mode not in {'type', 'size', 'date'}:
                mode = 'type'
            operation = str(opts.get('operation', 'copy')).lower()
            if operation not in {'copy', 'move'}:
                operation = 'copy'
            conflict_policy = str(opts.get('conflictPolicy', 'rename')).lower()
            recursive = bool(opts.get('recursive', True))
            dry_run = bool(opts.get('dryRun', False))
            filters = self._parse_common_filters(opts)
            filters['recursive'] = recursive
            files = self._collect_filtered_files(directory, filters, ensure_non_empty=False)
            if not files:
                raise ValueError('未匹配到任何文件')

            type_map = []
            for entry in opts.get('typeMap') or []:
                label = entry.get('label') or entry.get('name')
                extensions = entry.get('extensions') or entry.get('exts') or []
                normalized = [ext.lower().lstrip('.') for ext in extensions if ext]
                if label and normalized:
                    type_map.append((label, normalized))
            if not type_map:
                type_map = [
                    ('图片', ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'tiff']),
                    ('视频', ['mp4', 'mov', 'avi', 'mkv', 'webm']),
                    ('音频', ['mp3', 'wav', 'flac', 'aac', 'ogg']),
                    ('文档', ['pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt']),
                    ('压缩包', ['zip', '7z', 'rar', 'gz']),
                ]

            raw_buckets = opts.get('sizeBuckets') or []
            if not raw_buckets:
                raw_buckets = [
                    {'label': '≤1MB', 'maxMB': 1},
                    {'label': '1-10MB', 'minMB': 1, 'maxMB': 10},
                    {'label': '10-100MB', 'minMB': 10, 'maxMB': 100},
                    {'label': '≥100MB', 'minMB': 100},
                ]
            size_buckets = []
            for bucket in raw_buckets:
                label = bucket.get('label') or '未分组'
                min_bytes = bucket.get('minBytes')
                max_bytes = bucket.get('maxBytes')
                if min_bytes is None and bucket.get('minMB') is not None:
                    min_bytes = float(bucket['minMB']) * 1024 * 1024
                if max_bytes is None and bucket.get('maxMB') is not None:
                    max_bytes = float(bucket['maxMB']) * 1024 * 1024
                min_b = int(min_bytes) if min_bytes is not None else None
                max_b = int(max_bytes) if max_bytes is not None else None
                size_buckets.append({'label': label, 'min': min_b, 'max': max_b})

            date_format = opts.get('dateFormat') or '%Y-%m'
            date_field = str(opts.get('dateField', 'modified')).lower()
            fallback_label = opts.get('fallbackLabel') or '未分类'

            target_root = target_dir.resolve()
            directory_root = directory.resolve()
            summary = {
                'mode': mode,
                'operation': operation,
                'matched': len(files),
            }
            operations = []
            categories = Counter()
            total_size = 0

            def resolve_category(path: Path, stat) -> str:
                if mode == 'size':
                    size = stat.st_size
                    for bucket in size_buckets:
                        min_b = bucket['min']
                        max_b = bucket['max']
                        if (min_b is None or size >= min_b) and (max_b is None or size < max_b):
                            return bucket['label']
                    return fallback_label
                if mode == 'date':
                    if date_field == 'created':
                        timestamp = getattr(stat, 'st_ctime', stat.st_mtime)
                    elif date_field == 'accessed':
                        timestamp = getattr(stat, 'st_atime', stat.st_mtime)
                    else:
                        timestamp = stat.st_mtime
                    dt = datetime.fromtimestamp(timestamp)
                    try:
                        return dt.strftime(date_format)
                    except Exception:
                        return dt.strftime('%Y-%m')
                ext = path.suffix.lower().lstrip('.')
                for label, exts in type_map:
                    if ext in exts:
                        return label
                return ext.upper() or fallback_label

            planned = set()
            failures = []
            transaction_id = f'{int(time.time())}-{uuid.uuid4().hex[:8]}'
            manifest_path = directory / '.ppx_history' / 'classify' / f'{transaction_id}.json'
            manifest = {'schemaVersion': 2, 'id': transaction_id, 'directory': str(directory), 'targetDir': str(target_dir), 'operation': operation, 'mappings': []}
            for path in iter_progress(files, '正在分类文件'):
                if target_root != directory_root and target_root in path.resolve().parents:
                    record_item(path, 'skipped', '跳过本工具输出目录')
                    continue
                try:
                    stat = path.stat()
                    safe_label = self._sanitize_category_name(resolve_category(path, stat))
                    signature = self._hash_file(path) if not dry_run else None
                    base = target_dir / safe_label / path.name
                except Exception as exc:
                    checkpoint()
                    failures.append({'input': str(path), 'error': str(exc)})
                    record_item(path, 'failed', str(exc))
                    continue
                dest = base
                index = 2
                if conflict_policy == 'skip' and dest.exists():
                    record_item(path, 'skipped', '目标已存在')
                    continue
                while dest.exists() or os.path.normcase(str(dest)) in planned:
                    dest = base.with_name(f'{base.stem}_{index}{base.suffix}')
                    index += 1
                planned.add(os.path.normcase(str(dest)))
                record = {'from': str(path), 'to': str(dest), 'category': safe_label, 'status': 'pending',
                          'signature': signature}
                if dry_run:
                    operations.append(record)
                else:
                    manifest['mappings'].append(record)
                    save_manifest(manifest_path, manifest)
                    try:
                        dest = write_output(dest, lambda target: shutil.copy2(path, target), allow_empty=True)
                        record['to'] = str(dest)
                        record['signature'] = self._hash_file(dest)
                        save_manifest(manifest_path, manifest)
                        if operation == 'move':
                            path.unlink()
                        record['status'] = 'done'
                        operations.append(record)
                        record_item(path, 'success', outputs=[output_asset(dest)])
                    except Exception as exc:
                        checkpoint()
                        record['status'] = 'failed'
                        failures.append({'input': str(path), 'error': str(exc)})
                        record_item(path, 'failed', str(exc))
                    finally:
                        save_manifest(manifest_path, manifest)
                if dry_run or record['status'] == 'done':
                    categories[safe_label] += 1
                    total_size += stat.st_size

            summary['processed'] = len(operations)
            summary['totalBytes'] = total_size
            summary['totalSize'] = format_bytes(total_size)

            payload = {
                'summary': summary, 'transactionId': transaction_id, 'failures': failures,
                'partial': bool(failures and operations), 'code': 0 if operations or not failures else -1,
                'categories': [{'label': label, 'count': count} for label, count in categories.most_common()],
                'operations': operations,
                'outputDir': str(target_dir),
                'dryRun': dry_run,
            }
            message = '分类预览' if dry_run else '文件分类完成'
            return api_success(message, **payload)
        except Exception as exc:
            return api_error(f'文件分类失败：{exc}')

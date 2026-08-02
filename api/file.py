#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件管理相关 API
"""
from __future__ import annotations

import difflib
import filecmp
import hashlib
import os
import re
import shutil
import subprocess
import time
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable, List, Tuple

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
            yield from (path for path in root.rglob('*') if path.is_file())
        else:
            yield from (path for path in root.iterdir() if path.is_file())

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
        files = [
            path
            for path in self._iter_files(directory, recursive=filters['recursive'])
            if self._match_common_filters(path, filters)
        ]
        if ensure_non_empty and not files:
            raise ValueError('未匹配到任何文件')
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

    def _hash_file(self, path: Path, chunk_size: int = 1024 * 1024) -> str:
        hasher = hashlib.md5()
        with path.open('rb') as handler:
            for chunk in iter(lambda: handler.read(chunk_size), b''):
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
                        str(dest),
                    ] + rel_paths
                    proc = subprocess.run(cmd, cwd=common_root, capture_output=True, text=True)
                    if proc.returncode != 0:
                        stderr = proc.stderr.strip() or '调用 7-Zip 创建带密码 ZIP 失败'
                        raise RuntimeError(stderr)
                else:
                    compression = zipfile.ZIP_DEFLATED
                    with zipfile.ZipFile(dest, 'w', compression=compression, compresslevel=6) as handler:
                        for path in items:
                            if path.is_dir():
                                for file_path in path.rglob('*'):
                                    if file_path.is_file():
                                        handler.write(file_path, file_path.relative_to(path.parent))
                            else:
                                handler.write(path, arcname=path.name)
            else:
                if py7zr is None:
                    raise ImportError('缺少 py7zr 依赖，请运行 pip install py7zr')
                password = opts.get('password') or None
                with py7zr.SevenZipFile(dest, 'w', password=password) as handler:
                    for path in items:
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
            if suffix == '.zip':
                with zipfile.ZipFile(archive, 'r') as handler:
                    password = opts.get('password')
                    pwd = password.encode('utf-8') if password else None
                    self._validate_archive_members(target_dir, (item.filename for item in handler.infolist()))
                    handler.extractall(target_dir, pwd=pwd)
            elif suffix == '.7z':
                if py7zr is None:
                    raise ImportError('缺少 py7zr 依赖，请运行 pip install py7zr')
                with py7zr.SevenZipFile(archive, 'r', password=opts.get('password') or None) as handler:
                    self._validate_archive_members(target_dir, handler.getnames())
                    handler.extractall(target_dir)
            else:
                raise ValueError('当前仅支持解压 ZIP / 7Z')
            files = [str(path) for path in target_dir.rglob('*') if path.is_file()]
            return api_success('解压完成', outputDir=str(target_dir), files=files[:50])
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
            for path in files:
                relative = path.relative_to(source_dir)
                dest = target_dir / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.exists() and conflict_policy != 'overwrite':
                    skipped += 1
                    continue
                shutil.copy2(path, dest)
                copied += 1
                total_bytes += path.stat().st_size
            return api_success(
                '复制完成',
                copied=copied,
                skipped=skipped,
                size=total_bytes,
                sizeText=format_bytes(total_bytes),
                outputDir=str(target_dir),
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
            # v2.0 只允许可恢复删除：文件先移入当前目录下的 .ppx_recycle。
            recycle_dir = directory / '.ppx_recycle' / str(int(time.time()))
            recycle_dir.mkdir(parents=True, exist_ok=True)
            total_size = 0
            for path in files:
                total_size += path.stat().st_size
                target = recycle_dir / path.relative_to(directory)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(path), str(target))
            payload = {
                'deleted': len(files),
                'size': total_size,
                'sizeText': format_bytes(total_size),
            }
            payload['recycleDir'] = str(recycle_dir)
            return api_success('已移入回收目录', **payload)
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
            for offset, path in enumerate(files):
                index = start_index + offset
                new_name = self._build_new_name(path, rule, params, index)
                dest = path.with_name(new_name)
                if dest == path:
                    skipped.append(str(path))
                    continue
                if dest.exists() and dest != path:
                    # v2.0 禁止覆盖已有文件，避免批量改名造成不可恢复的数据丢失。
                    skipped.append(str(path))
                    continue
                renamed.append({'from': str(path), 'to': str(dest)})
                if not dry_run:
                    path.rename(dest)
            message = '重命名预览' if dry_run else '重命名完成'
            return api_success(message, renamed=renamed, skipped=skipped, dryRun=dry_run)
        except Exception as exc:
            return api_error(f'批量改名失败：{exc}')

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

            def resolve_conflict(dest: Path) -> Path:
                if not dest.exists():
                    return dest
                if conflict_policy == 'overwrite':
                    if not dry_run:
                        dest.unlink()
                    return dest
                index = 1
                while True:
                    candidate = dest.with_name(f'{dest.stem}_{index}{dest.suffix}')
                    if not candidate.exists():
                        return candidate
                    index += 1

            for path in files:
                stat = path.stat()
                resolved_path = path.resolve()
                if operation == 'move' and target_root != directory_root and target_root in resolved_path.parents:
                    continue
                label = resolve_category(path, stat)
                safe_label = self._sanitize_category_name(label)
                dest_dir = target_dir / safe_label
                dest = dest_dir / path.name
                dest = resolve_conflict(dest)
                if dest == path:
                    continue
                operations.append({'from': str(path), 'to': str(dest), 'category': safe_label})
                categories[safe_label] += 1
                total_size += stat.st_size
                if dry_run:
                    continue
                dest_dir.mkdir(parents=True, exist_ok=True)
                if operation == 'copy':
                    shutil.copy2(path, dest)
                else:
                    shutil.move(str(path), str(dest))

            summary['processed'] = len(operations)
            summary['totalBytes'] = total_size
            summary['totalSize'] = format_bytes(total_size)

            payload = {
                'summary': summary,
                'categories': [{'label': label, 'count': count} for label, count in categories.most_common()],
                'operations': operations[: min(len(operations), 80)],
                'outputDir': str(target_dir),
                'dryRun': dry_run,
            }
            message = '分类预览' if dry_run else '文件分类完成'
            return api_success(message, **payload)
        except Exception as exc:
            return api_error(f'文件分类失败：{exc}')

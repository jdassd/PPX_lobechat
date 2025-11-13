#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件管理相关 API
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import time
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
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
        return f'{stem}_{index}{suffix}'

    def file_search(self, options: Dict | None = None):
        """文件搜索"""
        try:
            opts = self._validate(options)
            directory = ensure_directory(opts.get('directory'), auto_create=False)
            filters = self._parse_common_filters(opts)
            limit = clamp_int(opts.get('limit', 500), 50, 2000)

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

    def file_directory_analyze(self, options: Dict | None = None):
        """目录分析"""
        try:
            opts = self._validate(options)
            directory = ensure_directory(opts.get('directory'), auto_create=False)
            total_size, file_count, dir_count, counter, largest = self._collect_directory_stats(directory)
            top_ext = counter.most_common(6)
            stats = {
                'totalSize': format_bytes(total_size),
                'fileCount': file_count,
                'dirCount': dir_count,
                'topExtensions': [{'ext': ext or '(无扩展名)', 'count': count} for ext, count in top_ext],
                'largestFiles': [{'name': item['name'], 'path': item['path'], 'size': format_bytes(item['size'])} for item in largest],
            }
            return api_success('分析完成', stats=stats)
        except Exception as exc:
            return api_error(f'目录分析失败：{exc}')

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
                    handler.extractall(target_dir, pwd=pwd)
            elif suffix == '.7z':
                if py7zr is None:
                    raise ImportError('缺少 py7zr 依赖，请运行 pip install py7zr')
                with py7zr.SevenZipFile(archive, 'r', password=opts.get('password') or None) as handler:
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
            delete_policy = str(opts.get('deletePolicy', 'recycle')).lower()
            dry_run = bool(opts.get('dryRun', False))
            preview = [str(path) for path in files]
            if dry_run:
                return api_success('预览删除列表', preview=preview, count=len(preview))
            recycle_dir = None
            if delete_policy != 'permanent':
                recycle_dir = directory / '.ppx_recycle' / str(int(time.time()))
                recycle_dir.mkdir(parents=True, exist_ok=True)
            total_size = 0
            for path in files:
                total_size += path.stat().st_size
                if recycle_dir:
                    target = recycle_dir / path.relative_to(directory)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(path), str(target))
                else:
                    path.unlink()
            payload = {
                'deleted': len(files),
                'size': total_size,
                'sizeText': format_bytes(total_size),
            }
            if recycle_dir:
                payload['recycleDir'] = str(recycle_dir)
            return api_success('删除完成', **payload)
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
            conflict_policy = str(opts.get('conflictPolicy', 'skip')).lower()
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
                    if conflict_policy == 'overwrite':
                        dest.unlink()
                    else:
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

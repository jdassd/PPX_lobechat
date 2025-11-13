#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件管理相关 API
"""
from __future__ import annotations

import os
import time
import zipfile
from collections import Counter
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

    def file_search(self, options: Dict | None = None):
        """文件搜索"""
        try:
            opts = self._validate(options)
            directory = ensure_directory(opts.get('directory'), auto_create=False)
            keyword = str(opts.get('keyword', '')).lower()
            extensions = opts.get('extensions') or []
            extensions = [ext.lower().lstrip('.') for ext in extensions if ext]
            min_size = int(opts.get('minSize') or 0)
            max_size = int(opts.get('maxSize') or 0)
            start_time = float(opts.get('modifiedStart') or 0)
            end_time = float(opts.get('modifiedEnd') or 0)
            recursive = bool(opts.get('recursive', True))
            limit = clamp_int(opts.get('limit', 500), 50, 2000)

            matched = []
            for path in self._iter_files(directory, recursive=recursive):
                if keyword and keyword not in path.name.lower():
                    continue
                if extensions and path.suffix.lower().lstrip('.') not in extensions:
                    continue
                stat = path.stat()
                if min_size and stat.st_size < min_size:
                    continue
                if max_size and stat.st_size > max_size:
                    continue
                if start_time and stat.st_mtime < start_time:
                    continue
                if end_time and stat.st_mtime > end_time:
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

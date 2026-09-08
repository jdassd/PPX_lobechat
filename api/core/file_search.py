"""One bounded, cancellable filename-search contract on every platform."""
from __future__ import annotations

import os
import stat
import time
from pathlib import Path

from api.core.context import checkpoint
from api.utils import format_bytes

_INTERNAL_DIRECTORIES = {'.ppx_recycle', '.ppx_history'}


class _SearchStopped(Exception):
    pass


def search_files(directory, filters, limit, *, max_entries=500000, max_depth=128, max_seconds=30):
    """Search only regular files inside the chosen root; never follow links.

    Results are complete only after traversal finishes. Finding one additional
    eligible file proves truncation; filtered-out files never consume the limit.
    Scan problems retain usable matches but explicitly make the result partial.
    """
    root = Path(directory).resolve()
    result = {'items': [], 'truncated': False, 'complete': True, 'scannedEntries': 0,
              'skippedLinks': 0, 'errorCount': 0, 'errors': [], 'limit': limit}
    started = time.monotonic()
    keyword = filters.get('keyword', '').casefold()
    extensions = {value.casefold() for value in filters.get('extensions', [])}

    def issue(path, code, message):
        result['errorCount'] += 1
        result['complete'] = False
        if len(result['errors']) < 20:
            result['errors'].append({'path': str(path), 'code': code, 'message': message})

    def budget(path):
        checkpoint()
        if result['scannedEntries'] >= max_entries:
            issue(path, 'SEARCH_SCAN_LIMIT', f'已检查 {max_entries} 个条目，请缩小搜索目录')
            raise _SearchStopped
        if time.monotonic() - started >= max_seconds:
            issue(path, 'SEARCH_TIME_LIMIT', '搜索达到时间上限，请缩小范围后重试')
            raise _SearchStopped

    def visit(folder, depth):
        budget(folder)
        if depth > max_depth:
            issue(folder, 'SEARCH_DEPTH_LIMIT', f'子目录层级超过 {max_depth} 层')
            return
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    budget(folder)
                    result['scannedEntries'] += 1
                    if entry.name in _INTERNAL_DIRECTORIES:
                        continue
                    path = Path(entry.path)
                    excluded = filters.get('exclude_directory')
                    if excluded is not None and (path == excluded or excluded in path.parents):
                        continue
                    try:
                        metadata = entry.stat(follow_symlinks=False)
                        # Windows junctions are reparse points, but are not
                        # necessarily reported as symbolic links on Python 3.10.
                        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400):
                            result['skippedLinks'] += 1
                            continue
                        if stat.S_ISDIR(metadata.st_mode):
                            if filters.get('recursive', True):
                                visit(path, depth + 1)
                            continue
                        if not stat.S_ISREG(metadata.st_mode):
                            continue
                        if keyword and keyword not in entry.name.casefold():
                            continue
                        if extensions and path.suffix.lstrip('.').casefold() not in extensions:
                            continue
                        if filters.get('min_size') and metadata.st_size < filters['min_size']:
                            continue
                        if filters.get('max_size') and metadata.st_size > filters['max_size']:
                            continue
                        if filters.get('start_time') and metadata.st_mtime < filters['start_time']:
                            continue
                        if filters.get('end_time') and metadata.st_mtime > filters['end_time']:
                            continue
                        if len(result['items']) == limit:
                            result.update(truncated=True, complete=False)
                            raise _SearchStopped
                        result['items'].append({'name': entry.name, 'path': str(path), 'relativePath': path.relative_to(root).as_posix(),
                                                'size': metadata.st_size, 'sizeText': format_bytes(metadata.st_size),
                                                'modified': metadata.st_mtime, 'ext': path.suffix.lower()})
                    except OSError as exc:
                        issue(path, 'SEARCH_IO', str(exc))
        except OSError as exc:
            issue(folder, 'SEARCH_IO', str(exc))

    try:
        visit(root, 0)
    except _SearchStopped:
        pass
    result['items'].sort(key=lambda item: (item['path'].casefold(), item['path']))
    result['matchedCount'] = len(result['items'])
    result['partial'] = not result['complete']
    return result

"""Plan portable archive member names and reject destructive name collisions."""
from __future__ import annotations

import os
from pathlib import Path, PurePosixPath

from api.core.context import checkpoint


def iter_archive_entries(items, *, base_dir=None, exclude=()):
    root = Path(base_dir).resolve() if base_dir else None
    if root is not None and not root.is_dir():
        raise ValueError('保留路径的根目录不存在')
    excluded = {Path(path).resolve() for path in exclude}
    seen = {}
    directories = set()
    files = set()

    def claim(path, relative):
        checkpoint()
        canonical = path.resolve()
        if canonical in excluded:
            return None
        if root is not None:
            try:
                relative = canonical.relative_to(root)
            except ValueError as exc:
                raise ValueError(f'输入不在保留路径的根目录中：{path}') from exc
        name = relative.as_posix().rstrip('/')
        if name in {'', '.'}:
            return None
        parts = PurePosixPath(name).parts
        if PurePosixPath(name).is_absolute() or '..' in parts or '\\' in name or any(':' in part for part in parts):
            raise ValueError(f'归档中的路径不受支持：{name}')
        key = name.casefold()
        is_directory = path.is_dir()
        parents = {PurePosixPath(*parts[:index]).as_posix().casefold() for index in range(1, len(parts))}
        if parents & files or (not is_directory and key in directories):
            raise ValueError(f'归档内文件与目录名称冲突：{name}')
        if key in seen:
            if seen[key] == canonical:
                return None
            raise ValueError(f'归档内存在同名路径：{name}；请选择共同根目录保留相对路径')
        seen[key] = canonical
        directories.update(parents)
        (directories if is_directory else files).add(key)
        return path, name

    def walk_error(error):
        raise error

    for item in items:
        checkpoint()
        path = Path(os.path.abspath(item))
        if not path.exists():
            raise FileNotFoundError(f'路径不存在：{path}')
        if root is not None:
            try:
                path.resolve().relative_to(root)
            except ValueError as exc:
                raise ValueError(f'输入不在保留路径的根目录中：{path}') from exc
        if path.is_file():
            entry = claim(path, Path(path.name))
            if entry:
                yield entry
            continue
        if not path.is_dir():
            raise ValueError(f'只支持普通文件或目录：{path}')
        for folder, child_dirs, child_files in os.walk(path, onerror=walk_error, followlinks=False):
            checkpoint()
            folder = Path(folder)
            if not child_dirs and not child_files:
                entry = claim(folder, folder.relative_to(path.parent))
                if entry:
                    yield entry
            for filename in child_files:
                file_path = folder / filename
                entry = claim(file_path, file_path.relative_to(path.parent))
                if entry:
                    yield entry

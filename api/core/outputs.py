"""Safe output allocation and atomic file publication."""
from __future__ import annotations

import os
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path

_lock = threading.RLock()
_reserved: set[str] = set()


def unique_path(path: Path | str) -> Path:
    target = Path(path).expanduser().absolute()
    target.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        candidate = target
        index = 2
        while candidate.exists() or candidate.is_symlink() or os.path.normcase(str(candidate)) in _reserved:
            candidate = target.with_name(f'{target.stem}_{index}{target.suffix}')
            index += 1
        return candidate


@contextmanager
def atomic_output(path: Path | str, *, allow_empty=False):
    """Yield a temporary sibling and final path; never replace existing user files."""
    with _lock:
        final = unique_path(path)
        identity = os.path.normcase(str(final))
        _reserved.add(identity)
    temporary = final.with_name(f'.{final.stem}.{uuid.uuid4().hex}.tmp{final.suffix}')
    from api.core.context import current_context
    context = current_context()
    if context:
        context.emit(temporaryPath=str(temporary))
    try:
        yield temporary, final
        from api.core.context import checkpoint, publish_output
        checkpoint()
        if not temporary.is_file() or (temporary.stat().st_size == 0 and not allow_empty):
            raise ValueError('处理引擎未生成有效输出文件')
        # Hard-link publication is atomic and fails if the destination appeared.
        # Both files live in the same directory / filesystem.
        if os.name == 'nt':
            os.rename(temporary, final)
        else:
            os.link(temporary, final)
        publish_output(final)
    finally:
        temporary.unlink(missing_ok=True)
        if context:
            context.emit(temporaryRemoved=str(temporary))
        with _lock:
            _reserved.discard(identity)


def output_asset(path: str | Path) -> dict:
    value = Path(path)
    exists = value.exists()
    return {
        'path': str(value), 'name': value.name,
        'kind': 'directory' if value.is_dir() else 'file',
        'exists': exists,
        'size': value.stat().st_size if exists and value.is_file() else None,
    }


def write_output(path, writer, *, allow_empty=False):
    with atomic_output(path, allow_empty=allow_empty) as (temporary, final):
        writer(temporary)
    return final

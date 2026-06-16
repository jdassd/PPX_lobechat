#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用校验函数
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Sequence


def ensure_file_path(path: str | Path, allow_empty: bool = False) -> Path:
    """确保文件存在"""
    if not path:
        if allow_empty:
            return Path()
        raise ValueError('请选择文件')
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f'文件不存在：{target}')
    if not target.is_file():
        raise ValueError(f'不是有效文件：{target}')
    return target


def ensure_directory(path: str | Path, auto_create: bool = False) -> Path:
    """确保目录存在"""
    if not path:
        raise ValueError('请选择目录')
    target = Path(path)
    if target.exists():
        if not target.is_dir():
            raise ValueError(f'路径不是目录：{target}')
        return target
    if auto_create:
        target.mkdir(parents=True, exist_ok=True)
        return target
    raise FileNotFoundError(f'目录不存在：{target}')


def ensure_output_directory(source: Path, preferred: str | None, suffix: str) -> Path:
    """根据源文件和偏好路径生成输出目录"""
    if preferred:
        return ensure_directory(preferred, auto_create=True)
    fallback = source.parent / f'{source.stem}_{suffix}'
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def ensure_files_payload(options: dict, key: str = 'files') -> List[Path]:
    """从参数中解析文件列表"""
    raw = options.get(key)
    if isinstance(raw, (str, Path)):
        raw_list: Sequence[str | Path] = [raw]
    elif isinstance(raw, Iterable):
        raw_list = list(raw)
    else:
        raw_list = []
    files: List[Path] = []
    for item in raw_list:
        if not item:
            continue
        files.append(ensure_file_path(item))
    if not files:
        raise ValueError('请至少选择一个文件')
    return files


def clamp_int(value, default: int, min_value: int | None = None, max_value: int | None = None) -> int:
    """安全地解析并裁剪整数"""
    try:
        result = int(value)
    except (TypeError, ValueError):
        result = default
    if min_value is not None and result < min_value:
        result = min_value
    if max_value is not None and result > max_value:
        result = max_value
    return result

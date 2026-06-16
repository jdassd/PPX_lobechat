#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
格式转换相关函数
"""
from __future__ import annotations

import math
from datetime import timedelta
from typing import Tuple


def format_bytes(value: int | float) -> str:
    """将字节转换为可读文本"""
    try:
        num = float(value)
    except (TypeError, ValueError):
        num = 0.0
    if num <= 0:
        return '0 B'
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    idx = min(int(math.floor(math.log(num, 1024))), len(units) - 1)
    scaled = num / math.pow(1024, idx)
    return f'{scaled:.2f} {units[idx]}'


def parse_percentage(value, default: float = 100.0, minimum: float = 1.0, maximum: float = 400.0) -> float:
    """解析百分比并限制范围"""
    try:
        percent = float(value)
    except (TypeError, ValueError):
        percent = default
    percent = max(minimum, min(maximum, percent))
    return percent


def parse_timespan(value: str | int | float) -> Tuple[float, str]:
    """
    解析时间范围，返回秒以及标准 HH:MM:SS 字符串。
    输入可以是秒数或 00:00:00 格式。
    """
    if isinstance(value, (int, float)):
        seconds = float(value)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return 0.0, '00:00:00'
        if ':' in text:
            parts = [float(part) for part in text.split(':')]
            parts = [0.0] * (3 - len(parts)) + parts  # pad to 3
            hours, minutes, seconds = parts[-3], parts[-2], parts[-1]
            seconds = hours * 3600 + minutes * 60 + seconds
        else:
            try:
                seconds = float(text)
            except ValueError:
                seconds = 0.0
    else:
        seconds = 0.0
    if seconds < 0:
        seconds = 0.0
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hh = total_seconds // 3600
    mm = (total_seconds % 3600) // 60
    ss = total_seconds % 60
    return seconds, f'{hh:02}:{mm:02}:{ss:02}'


def normalize_suffix(filename: str, target_suffix: str) -> str:
    """确保文件名包含指定后缀"""
    if not target_suffix:
        return filename
    suffix = target_suffix if target_suffix.startswith('.') else f'.{target_suffix}'
    if filename.lower().endswith(suffix.lower()):
        return filename
    return f'{filename}{suffix}'

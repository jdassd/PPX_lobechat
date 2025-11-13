#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一 API 返回格式
"""
from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Dict


def api_success(message: str = '操作成功', **payload) -> Dict[str, Any]:
    response = {'code': 0, 'msg': message}
    response.update(payload)
    return response


def api_error(message: str, code: int = -1, **payload) -> Dict[str, Any]:
    response = {'code': code, 'msg': message}
    response.update(payload)
    return response


def safe_execute(func: Callable):
    """捕捉异常并转换为 API 错误"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            return api_error(str(exc))

    return wrapper

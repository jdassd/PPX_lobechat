#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的进度回调封装
"""
from __future__ import annotations

from typing import Callable, Optional


class ProgressReporter:
    """向前端报告长任务进度"""

    def __init__(self, callback: Optional[Callable[[dict], None]] = None, total: int = 0):
        self.callback = callback
        self.total = max(0, int(total))
        self.current = 0

    def step(self, message: str = ''):
        if not self.callback:
            return
        self.current += 1
        payload = {
            'current': self.current,
            'total': self.total,
            'message': message,
        }
        try:
            self.callback(payload)
        except Exception:
            # 回调异常无需影响主流程
            pass

    def reset(self, total: int = 0):
        self.total = max(0, int(total))
        self.current = 0

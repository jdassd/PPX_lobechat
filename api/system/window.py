#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: 潘高
LastEditors: 潘高
Date: 2023-03-26 20:48:26
LastEditTime: 2025-02-10 14:25:13
Description: 系统类 - 窗口控制 Mixin（最小化、调整大小、关闭窗口）
usage: 调用window.pywebview.api.<methodname>(<parameters>)从Javascript执行
'''

import threading

from webview.window import FixPoint

from api.utils.error_handler import api_success, api_error, safe_execute
from pyapp.config.config import Config


class WindowMixin():
    '''窗口控制 Mixin：最小化、调整大小、关闭窗口'''

    @safe_execute
    def minimize_window(self):
        '''最小化窗口'''
        if self._window:
            if hasattr(self._window, 'minimize'):
                self._window.minimize()
            elif hasattr(self._window, 'hide'):
                self._window.hide()
            else:
                return api_error('当前窗口不支持最小化')
            return api_success()
        return api_error('窗口对象未初始化')

    @safe_execute
    def resize_window(self, payload=None):
        '''调整窗口大小（用于无边框拖拽缩放）'''
        if not self._window:
            return api_error('窗口对象未初始化')

        if not isinstance(payload, dict):
            return api_error('参数无效')

        width = payload.get('width')
        height = payload.get('height')
        fix_point_raw = payload.get('fixPoint')

        try:
            width = int(width)
            height = int(height)
        except (TypeError, ValueError):
            return api_error('宽高无效')

        fix_point = FixPoint.NORTH | FixPoint.WEST
        if isinstance(fix_point_raw, str) and fix_point_raw:
            flags = []
            token = fix_point_raw.upper()
            if 'N' in token:
                flags.append(FixPoint.NORTH)
            if 'S' in token:
                flags.append(FixPoint.SOUTH)
            if 'E' in token:
                flags.append(FixPoint.EAST)
            if 'W' in token:
                flags.append(FixPoint.WEST)
            if flags:
                fix_point = FixPoint(0)
                for flag in flags:
                    fix_point |= flag

        self._window.resize(width, height, fix_point)
        return api_success()

    @classmethod
    def _close_window_async(cls, delay: float | None = None):
        '''异步关闭窗口，避免在 JS API 回调未返回时直接销毁 WebView 导致卡死'''
        window = cls._window
        if not window:
            return False
        if cls._close_timer and cls._close_timer.is_alive():
            return True
        if delay is None:
            delay = 0.15 if Config.appIsMacOS else 0.05

        def _close():
            try:
                if hasattr(window, 'destroy'):
                    window.destroy()
                elif hasattr(window, 'close'):
                    window.close()
            except Exception as err:
                print(f'[Window] 异步关闭失败: {err}')
            finally:
                cls._close_timer = None

        timer = threading.Timer(max(0, delay), _close)
        timer.daemon = True
        cls._close_timer = timer
        timer.start()
        return True

    @safe_execute
    def close_window(self):
        '''关闭窗口'''
        if self._window:
            if not (hasattr(self._window, 'destroy') or hasattr(self._window, 'close')):
                return api_error('当前窗口不支持关闭')
            self._close_window_async()
            return api_success()
        return api_error('窗口对象未初始化')

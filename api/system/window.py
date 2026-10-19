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

from __future__ import annotations

import threading

from webview.window import FixPoint

from api.utils.error_handler import api_error, api_success, safe_execute
from pyapp.config.config import Config


class WindowMixin():
    '''窗口控制 Mixin：最小化、调整大小、关闭窗口'''

    @safe_execute
    def configure_window_frame(self, options=None):
        """Report actual native resize support and match the border to the UI."""
        window = self._window
        if Config.appSystem != 'Windows' or not window or not getattr(window, 'frameless', False):
            return api_success(nativeResize=False)

        from api.system.window_geometry import apply_windows_maximized_bounds

        if not apply_windows_maximized_bounds(window):
            return api_error('原生窗口边框初始化失败', nativeResize=False)

        from System import Func, Type
        from System.Drawing import ColorTranslator

        theme = options.get('theme') if isinstance(options, dict) else 'light'
        color = '#20232b' if theme == 'dark' else '#f3f4f6'

        def set_color():
            window.native.BackColor = ColorTranslator.FromHtml(color)

        window.native.Invoke(Func[Type](set_color))
        return api_success(nativeResize=True)

    @safe_execute
    def begin_native_resize(self, direction=None):
        '''启动 Windows 原生窗口缩放，避免 JS 高频调用 resize_window。'''
        if not self._window:
            return api_error('窗口对象未初始化', supported=False)

        directions = {
            'n': 12,   # HTTOP
            's': 15,   # HTBOTTOM
            'e': 11,   # HTRIGHT
            'w': 10,   # HTLEFT
            'ne': 14,  # HTRIGHT
            'nw': 13,  # HTTOPLEFT
            'se': 17,  # HTBOTTOMRIGHT
            'sw': 16,  # HTBOTTOMLEFT
        }
        direction = str(direction or '').strip().lower()
        if direction not in directions:
            return api_error('调整方向无效', supported=False)

        if Config.appSystem != 'Windows':
            return api_success('当前平台请使用应用窗口调整大小', supported=False)

        native = getattr(self._window, 'native', None)
        if native is None or not hasattr(native, 'Invoke') or not hasattr(native, 'Handle'):
            return api_error('Windows 原生窗口句柄不可用', supported=False)

        # pywebview 调用 JS API 的线程不是 WinForms UI 线程。Invoke 把
        # ReleaseCapture 和 WM_NCLBUTTONDOWN 一起交给拥有窗口句柄的线程，
        # 让 Windows 自己完成后续拖动、DPI 与最小尺寸处理。
        import ctypes

        from System import Func, Type

        hwnd = native.Handle.ToInt64()
        hit_test = directions[direction]
        user32 = ctypes.windll.user32
        user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
        user32.GetAsyncKeyState.restype = ctypes.c_short
        class Point(ctypes.Structure):
            _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]

        get_cursor_pos = user32.GetCursorPos
        get_cursor_pos.argtypes = [ctypes.POINTER(Point)]
        get_cursor_pos.restype = ctypes.c_int
        release_capture = user32.ReleaseCapture
        release_capture.argtypes = []
        release_capture.restype = ctypes.c_int
        send_message = user32.SendMessageW
        send_message.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
        send_message.restype = ctypes.c_ssize_t
        VK_LBUTTON = 0x01
        resize_started = []

        def start_resize():
            # The JS bridge is asynchronous. The user may have released the
            # pointer before this delegate reaches the UI thread; sending
            # WM_NCLBUTTONDOWN then would enter a modal loop with no matching
            # physical mouse-up event.
            if not (user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000):
                resize_started.append(False)
                return
            point = Point()
            if not get_cursor_pos(ctypes.byref(point)):
                resize_started.append(False)
                return
            release_capture()
            packed_point = ((int(point.y) & 0xFFFF) << 16) | (int(point.x) & 0xFFFF)
            send_message(hwnd, 0x00A1, hit_test, packed_point)  # WM_NCLBUTTONDOWN
            resize_started.append(True)

        native.Invoke(Func[Type](start_resize))
        if resize_started and resize_started[0]:
            return api_success('已交由 Windows 原生调整大小', supported=True, started=True)
        return api_success('鼠标已释放，已取消窗口调整大小', supported=True, started=False)

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

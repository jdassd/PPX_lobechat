#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automation API powered by PyAutoGUI + pynput.
"""
from __future__ import annotations

import json
import platform
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from api.utils import api_error, api_success, clamp_int, ensure_directory, ensure_file_path


_KEY_NAME_MAP = {
    'enter': 'enter',
    'return': 'enter',
    'esc': 'esc',
    'escape': 'esc',
    'space': 'space',
    'tab': 'tab',
    'backspace': 'backspace',
    'delete': 'delete',
    'insert': 'insert',
    'home': 'home',
    'end': 'end',
    'page_up': 'pageup',
    'page_down': 'pagedown',
    'up': 'up',
    'down': 'down',
    'left': 'left',
    'right': 'right',
    'caps_lock': 'capslock',
    'shift': 'shift',
    'shift_l': 'shiftleft',
    'shift_r': 'shiftright',
    'ctrl': 'ctrl',
    'ctrl_l': 'ctrlleft',
    'ctrl_r': 'ctrlright',
    'alt': 'alt',
    'alt_l': 'altleft',
    'alt_r': 'altright',
    'alt_gr': 'altright',
    'cmd': 'win',
    'cmd_l': 'winleft',
    'cmd_r': 'winright',
    'print_screen': 'printscreen',
    'scroll_lock': 'scrolllock',
    'pause': 'pause',
    'media_volume_up': 'volumeup',
    'media_volume_down': 'volumedown',
    'media_volume_mute': 'volumemute',
}

_MOUSE_BUTTON_MAP = {
    'left': 'left',
    'right': 'right',
    'middle': 'middle',
}


class AutomationTool:
    """Automation toolkit: record/playback + image-based actions."""

    _record_lock = threading.Lock()
    _recording: Dict[str, Any] | None = None

    _playback_lock = threading.Lock()
    _playback_thread: threading.Thread | None = None
    _playback_stop = threading.Event()
    _playback_status: Dict[str, Any] = {
        'active': False,
        'jobId': '',
        'startedAt': 0,
        'endedAt': 0,
        'error': '',
    }

    def _import_pyautogui(self):
        try:
            import pyautogui
        except Exception as exc:  # pragma: no cover
            raise ImportError('缺少 pyautogui 依赖，请先运行 pnpm run init 或 pip install pyautogui') from exc
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0
        return pyautogui

    def _import_pynput(self):
        try:
            from pynput import mouse, keyboard
        except Exception as exc:  # pragma: no cover
            raise ImportError('缺少 pynput 依赖，请先运行 pnpm run init 或 pip install pynput') from exc
        return mouse, keyboard

    def _normalize_key(self, key) -> str:
        if key is None:
            return ''
        if hasattr(key, 'char') and key.char:
            char = key.char
            if isinstance(char, str) and len(char) == 1:
                return char.lower() if char.isalpha() else char
            return char
        name = getattr(key, 'name', '') or str(key)
        if name.startswith('Key.'):
            name = name[4:]
        name = name.lower()
        if name.startswith('f') and name[1:].isdigit():
            return name
        return _KEY_NAME_MAP.get(name, name)

    def _normalize_button(self, button) -> str:
        if button is None:
            return 'left'
        name = getattr(button, 'name', None)
        if not name:
            name = str(button).split('.')[-1]
        return _MOUSE_BUTTON_MAP.get(name, 'left')

    def _resolve_confidence(self, confidence: float | None) -> Tuple[float | None, str | None]:
        if confidence is None:
            return None, None
        try:
            import cv2  # noqa: F401
        except Exception:
            return None, '未检测到 OpenCV，已忽略相似度阈值'
        return confidence, None

    def _locate_image(self, pyautogui, image_path: Path, options: Dict, stop_event: threading.Event | None = None):
        confidence = options.get('confidence', None)
        confidence, warning = self._resolve_confidence(confidence)
        grayscale = bool(options.get('grayscale', True))
        timeout = float(options.get('timeout', 5) or 5)
        interval = float(options.get('interval', 0.5) or 0.5)
        region = options.get('region')
        if isinstance(region, dict):
            region = (
                int(region.get('x', 0)),
                int(region.get('y', 0)),
                int(region.get('width', 0)),
                int(region.get('height', 0)),
            )

        started_at = time.time()
        while True:
            if stop_event is not None and stop_event.is_set():
                return None, '操作已取消', warning
            try:
                location = pyautogui.locateCenterOnScreen(
                    str(image_path),
                    confidence=confidence,
                    grayscale=grayscale,
                    region=region,
                )
            except TypeError:
                location = pyautogui.locateCenterOnScreen(
                    str(image_path),
                    grayscale=grayscale,
                    region=region,
                )
            if location:
                return location, None, warning
            if time.time() - started_at >= timeout:
                return None, '未找到目标图片', warning
            time.sleep(interval)

    def automation_record_status(self):
        with self._record_lock:
            if not self._recording or not self._recording.get('active'):
                return api_success('未在录制', active=False, count=0)
            elapsed = time.monotonic() - self._recording['start']
            return api_success(
                '录制中',
                active=True,
                count=len(self._recording['events']),
                duration=round(elapsed, 3),
            )

    def automation_record_start(self, options: Dict | None = None):
        try:
            opts = options if isinstance(options, dict) else {}
            record_mouse = bool(opts.get('recordMouse', True))
            record_keyboard = bool(opts.get('recordKeyboard', True))
            capture_move = bool(opts.get('captureMove', True))
            move_interval_ms = clamp_int(opts.get('moveInterval', 80), 80, 20, 1000)
            move_interval = move_interval_ms / 1000.0

            if not record_mouse and not record_keyboard:
                return api_error('请至少选择鼠标或键盘录制')

            with self._playback_lock:
                if self._playback_status.get('active'):
                    return api_error('回放进行中，无法开始录制')

            with self._record_lock:
                if self._recording and self._recording.get('active'):
                    return api_error('当前已有录制任务')

                mouse, keyboard = self._import_pynput()
                start = time.monotonic()
                events: List[Dict[str, Any]] = []
                last_move_at = 0.0

                def stamp() -> float:
                    return round(time.monotonic() - start, 4)

                def on_move(x, y):
                    nonlocal last_move_at
                    if not capture_move:
                        return
                    now = time.monotonic() - start
                    if now - last_move_at < move_interval:
                        return
                    last_move_at = now
                    events.append({
                        'type': 'mouse_move',
                        'x': int(x),
                        'y': int(y),
                        't': round(now, 4),
                    })

                def on_click(x, y, button, pressed):
                    events.append({
                        'type': 'mouse_click',
                        'x': int(x),
                        'y': int(y),
                        'button': self._normalize_button(button),
                        'pressed': bool(pressed),
                        't': stamp(),
                    })

                def on_scroll(x, y, dx, dy):
                    events.append({
                        'type': 'mouse_scroll',
                        'x': int(x),
                        'y': int(y),
                        'dx': int(dx),
                        'dy': int(dy),
                        't': stamp(),
                    })

                def on_press(key):
                    key_name = self._normalize_key(key)
                    if not key_name:
                        return
                    events.append({
                        'type': 'key_down',
                        'key': key_name,
                        't': stamp(),
                    })

                def on_release(key):
                    key_name = self._normalize_key(key)
                    if not key_name:
                        return
                    events.append({
                        'type': 'key_up',
                        'key': key_name,
                        't': stamp(),
                    })

                mouse_listener = None
                keyboard_listener = None
                if record_mouse:
                    mouse_listener = mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
                    mouse_listener.start()
                if record_keyboard:
                    keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
                    keyboard_listener.start()

                self._recording = {
                    'active': True,
                    'start': start,
                    'events': events,
                    'mouse_listener': mouse_listener,
                    'keyboard_listener': keyboard_listener,
                    'options': {
                        'recordMouse': record_mouse,
                        'recordKeyboard': record_keyboard,
                        'captureMove': capture_move,
                        'moveInterval': move_interval_ms,
                    },
                }

            return api_success('已开始录制', options=self._recording['options'])
        except Exception as exc:
            return api_error(f'录制启动失败：{exc}')

    def automation_record_stop(self):
        with self._record_lock:
            if not self._recording or not self._recording.get('active'):
                return api_error('当前没有进行中的录制')
            record = self._recording
            record['active'] = False
            self._recording = None

        try:
            if record.get('mouse_listener'):
                record['mouse_listener'].stop()
            if record.get('keyboard_listener'):
                record['keyboard_listener'].stop()
        except Exception:
            pass

        events = record.get('events', [])
        duration = 0.0
        if events:
            duration = max(0.0, float(events[-1].get('t', 0)))

        try:
            pyautogui = self._import_pyautogui()
            screen_size = pyautogui.size()
        except Exception:
            screen_size = (0, 0)

        macro = {
            'version': 1,
            'createdAt': datetime.now().isoformat(timespec='seconds'),
            'platform': platform.system(),
            'screen': {
                'width': int(screen_size[0] or 0),
                'height': int(screen_size[1] or 0),
            },
            'duration': round(duration, 3),
            'actions': events,
        }
        return api_success('录制完成', macro=macro, actions=events, duration=round(duration, 3))

    def automation_save_macro(self, options: Dict | None = None):
        try:
            opts = options if isinstance(options, dict) else {}
            macro = opts.get('macro') or opts.get('data')
            if macro is None:
                macro = {'actions': opts.get('actions') or []}

            output_dir = opts.get('outputDir') or opts.get('directory')
            filename = opts.get('fileName') or opts.get('name') or 'macro.json'
            if not filename.endswith('.json'):
                filename = f'{filename}.json'
            if not output_dir:
                raise ValueError('请选择输出目录')
            target_dir = ensure_directory(output_dir, auto_create=True)
            target_path = target_dir / filename

            with target_path.open('w', encoding='utf-8') as handler:
                json.dump(macro, handler, ensure_ascii=False, indent=2)

            return api_success('保存成功', path=str(target_path))
        except Exception as exc:
            return api_error(f'保存失败：{exc}')

    def automation_load_macro(self, options: Dict | None = None):
        try:
            opts = options if isinstance(options, dict) else {}
            path = ensure_file_path(opts.get('path'))
            with path.open('r', encoding='utf-8') as handler:
                data = json.load(handler)
            actions = data.get('actions') if isinstance(data, dict) else data
            if not isinstance(actions, list):
                raise ValueError('脚本格式错误：actions 必须是数组')
            return api_success('加载完成', macro=data, actions=actions)
        except Exception as exc:
            return api_error(f'加载失败：{exc}')

    def automation_find_image(self, options: Dict | None = None):
        try:
            opts = options if isinstance(options, dict) else {}
            image_path = ensure_file_path(opts.get('image'))
            pyautogui = self._import_pyautogui()
            location, error_msg, warning = self._locate_image(pyautogui, image_path, opts)
            if not location:
                return api_error(error_msg or '未找到目标图片', warning=warning)
            return api_success(
                '已定位图片',
                position={'x': int(location.x), 'y': int(location.y)},
                warning=warning,
            )
        except Exception as exc:
            return api_error(f'图片识别失败：{exc}')

    def automation_click_image(self, options: Dict | None = None):
        try:
            opts = options if isinstance(options, dict) else {}
            image_path = ensure_file_path(opts.get('image'))
            pyautogui = self._import_pyautogui()
            location, error_msg, warning = self._locate_image(pyautogui, image_path, opts)
            if not location:
                return api_error(error_msg or '未找到目标图片', warning=warning)

            button = str(opts.get('button', 'left')).lower()
            clicks = clamp_int(opts.get('clicks', 1), 1, 1, 5)
            interval = float(opts.get('interval', 0.0) or 0.0)
            pyautogui.click(int(location.x), int(location.y), clicks=clicks, interval=interval, button=button)

            return api_success(
                '已点击目标',
                position={'x': int(location.x), 'y': int(location.y)},
                warning=warning,
            )
        except Exception as exc:
            return api_error(f'点击失败：{exc}')

    def automation_playback_status(self):
        with self._playback_lock:
            return api_success('回放状态', **self._playback_status)

    def automation_stop_playback(self):
        with self._playback_lock:
            if not self._playback_status.get('active'):
                return api_success('当前没有正在回放的任务', active=False)
            self._playback_stop.set()
            return api_success('已发送停止信号', active=False)

    def _compute_delay(self, action: Dict[str, Any], last_t: float) -> Tuple[float, float]:
        if 'delay' in action:
            try:
                delay = float(action.get('delay', 0))
            except (TypeError, ValueError):
                delay = 0.0
            return max(0.0, delay), last_t
        t = action.get('t', action.get('timestamp', None))
        if t is None:
            return 0.0, last_t
        try:
            t = float(t)
        except (TypeError, ValueError):
            return 0.0, last_t
        delay = max(0.0, t - last_t)
        return delay, t

    def _scale_point(self, x: int | float, y: int | float, scale_x: float, scale_y: float) -> Tuple[int, int]:
        return int(round(x * scale_x)), int(round(y * scale_y))

    def _run_action(self, pyautogui, action: Dict[str, Any], scale_x: float, scale_y: float):
        action_type = str(action.get('type', '') or '').lower()
        if not action_type:
            return

        if action_type in {'mouse_move', 'move'}:
            x, y = self._scale_point(action.get('x', 0), action.get('y', 0), scale_x, scale_y)
            pyautogui.moveTo(x, y)
            return

        if action_type in {'mouse_click', 'click'}:
            x, y = self._scale_point(action.get('x', 0), action.get('y', 0), scale_x, scale_y)
            button = str(action.get('button', 'left')).lower()
            if 'pressed' in action:
                if action.get('pressed'):
                    pyautogui.mouseDown(x, y, button=button)
                else:
                    pyautogui.mouseUp(x, y, button=button)
            else:
                clicks = clamp_int(action.get('clicks', 1), 1, 1, 10)
                interval = float(action.get('interval', 0.0) or 0.0)
                pyautogui.click(x, y, clicks=clicks, interval=interval, button=button)
            return

        if action_type in {'mouse_down'}:
            x, y = self._scale_point(action.get('x', 0), action.get('y', 0), scale_x, scale_y)
            button = str(action.get('button', 'left')).lower()
            pyautogui.mouseDown(x, y, button=button)
            return

        if action_type in {'mouse_up'}:
            x, y = self._scale_point(action.get('x', 0), action.get('y', 0), scale_x, scale_y)
            button = str(action.get('button', 'left')).lower()
            pyautogui.mouseUp(x, y, button=button)
            return

        if action_type in {'mouse_scroll', 'scroll'}:
            dy = int(action.get('dy', action.get('scroll', 0)) or 0)
            dx = int(action.get('dx', 0) or 0)
            if dy:
                pyautogui.scroll(dy)
            if dx:
                pyautogui.hscroll(dx)
            return

        if action_type in {'key_down', 'keydown'}:
            key = str(action.get('key', '') or '')
            if key:
                pyautogui.keyDown(key)
            return

        if action_type in {'key_up', 'keyup'}:
            key = str(action.get('key', '') or '')
            if key:
                pyautogui.keyUp(key)
            return

        if action_type in {'key_press', 'press'}:
            key = str(action.get('key', '') or '')
            if key:
                pyautogui.press(key)
            return

        if action_type in {'text', 'type', 'typewrite', 'write'}:
            content = str(action.get('text', action.get('content', '')) or '')
            interval = float(action.get('interval', 0.0) or 0.0)
            if content:
                pyautogui.write(content, interval=interval)
            return

        if action_type in {'wait', 'sleep'}:
            duration = float(action.get('duration', action.get('wait', 0.0)) or 0.0)
            if duration > 0:
                time.sleep(duration)
            return

        if action_type in {'image_click', 'image_find'}:
            image_path = action.get('imagePath') or action.get('image')
            if not image_path:
                raise ValueError('图像步骤缺少 imagePath')
            path = ensure_file_path(image_path)
            location, error_msg, _ = self._locate_image(pyautogui, path, action, self._playback_stop)
            if not location:
                raise RuntimeError(error_msg or '未找到目标图片')
            x, y = self._scale_point(location.x, location.y, 1.0, 1.0)
            click_enabled = action.get('click', True) or action_type == 'image_click'
            if click_enabled:
                button = str(action.get('button', 'left')).lower()
                clicks = clamp_int(action.get('clicks', 1), 1, 1, 10)
                interval = float(action.get('interval', 0.0) or 0.0)
                pyautogui.click(x, y, clicks=clicks, interval=interval, button=button)
            else:
                pyautogui.moveTo(x, y)
            return

    def _playback_worker(self, actions: List[Dict[str, Any]], options: Dict[str, Any], meta: Dict[str, Any]):
        error_msg = ''
        try:
            pyautogui = self._import_pyautogui()
            speed = float(options.get('speed', 1.0) or 1.0)
            speed = max(0.1, min(speed, 8.0))
            loop = clamp_int(options.get('loop', 1), 1, 1, 9999)
            start_delay = float(options.get('startDelay', 0.0) or 0.0)
            auto_scale = bool(options.get('autoScale', False))
            scale_x = 1.0
            scale_y = 1.0

            if auto_scale and isinstance(meta.get('screen'), dict):
                recorded_w = int(meta['screen'].get('width') or 0)
                recorded_h = int(meta['screen'].get('height') or 0)
                if recorded_w and recorded_h:
                    current_w, current_h = pyautogui.size()
                    scale_x = current_w / recorded_w
                    scale_y = current_h / recorded_h

            if start_delay > 0:
                time.sleep(start_delay)

            for _ in range(loop):
                last_t = 0.0
                for action in actions:
                    if self._playback_stop.is_set():
                        return
                    delay, last_t = self._compute_delay(action, last_t)
                    if delay > 0:
                        time.sleep(delay / speed)
                    if self._playback_stop.is_set():
                        return
                    self._run_action(pyautogui, action, scale_x, scale_y)
        except Exception as exc:
            error_msg = str(exc)
        finally:
            with self._playback_lock:
                self._playback_status['active'] = False
                self._playback_status['endedAt'] = int(time.time())
                self._playback_status['error'] = error_msg
                self._playback_stop.clear()

    def automation_play_macro(self, options: Dict | None = None):
        try:
            opts = options if isinstance(options, dict) else {}
            macro = opts.get('macro')
            actions = opts.get('actions')
            meta: Dict[str, Any] = {}
            if isinstance(macro, dict):
                meta = macro
                actions = macro.get('actions', actions)
            if not isinstance(actions, list) or not actions:
                return api_error('脚本为空，无法回放')

            with self._record_lock:
                if self._recording and self._recording.get('active'):
                    return api_error('录制进行中，无法开始回放')

            with self._playback_lock:
                if self._playback_status.get('active'):
                    return api_error('已有回放任务正在进行')
                job_id = uuid.uuid4().hex[:8]
                self._playback_stop.clear()
                self._playback_status = {
                    'active': True,
                    'jobId': job_id,
                    'startedAt': int(time.time()),
                    'endedAt': 0,
                    'error': '',
                }
                self._playback_thread = threading.Thread(
                    target=self._playback_worker,
                    args=(actions, opts, meta),
                    daemon=True,
                )
                self._playback_thread.start()

            return api_success('回放已启动', jobId=job_id)
        except Exception as exc:
            return api_error(f'回放启动失败：{exc}')

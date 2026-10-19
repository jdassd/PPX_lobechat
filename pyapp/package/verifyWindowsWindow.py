"""Run a short, isolated native pywebview sizing probe on Windows."""

from __future__ import annotations

import ctypes
import json
import sys
import tempfile
import threading
import time
from ctypes import wintypes
from pathlib import Path

import webview
from webview.window import FixPoint

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from api.system.window import WindowMixin
from api.system.window_geometry import (
    apply_windows_maximized_bounds,
    apply_windows_startup_geometry,
    calculate_window_geometry,
    ensure_windows_resize_frame,
    get_windows_scale_factor,
    get_windows_workareas,
)


def _window_rect(hwnd):
    class Rect(ctypes.Structure):
        _fields_ = [
            ('left', wintypes.LONG),
            ('top', wintypes.LONG),
            ('right', wintypes.LONG),
            ('bottom', wintypes.LONG),
        ]

    rect = Rect()
    if not ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        raise ctypes.WinError(ctypes.get_last_error())
    return {
        'x': int(rect.left),
        'y': int(rect.top),
        'width': int(rect.right - rect.left),
        'height': int(rect.bottom - rect.top),
    }


def main():
    dpi_before = int(ctypes.windll.user32.GetDpiForSystem())
    workareas = get_windows_workareas()
    if not workareas:
        raise RuntimeError('Windows monitor work areas are unavailable')
    geometry = calculate_window_geometry(workareas)
    scale_factor = get_windows_scale_factor()
    results = {
        'workareas': workareas,
        'planned': geometry,
        'webviewScaleFactor': scale_factor,
        'dpiBeforeWebViewInit': dpi_before,
        'checks': {},
        'resizeEvents': 0,
    }
    finished = threading.Event()
    geometry_ready = threading.Event()
    errors = []
    holder = {}

    class ProbeApi(WindowMixin):
        def set_window(self, window):
            self._window = window
            holder['window'] = window

    api = ProbeApi()
    window = webview.create_window(
        'PPX isolated native window probe',
        html='<html><body style="margin:0;font:24px sans-serif">Native resize probe</body></html>',
        js_api=api,
        width=geometry['width'],
        height=geometry['height'],
        x=geometry['x'],
        y=geometry['y'],
        min_size=geometry['min_size'],
        frameless=True,
        resizable=True,
    )
    api.set_window(window)

    def count_resize(*_):
        results['resizeEvents'] += 1

    window.events.resized += count_resize

    def set_maximized_bounds(*_):
        # pywebview raises these callbacks on the WinForms UI thread. Setting
        # MaximizedBounds from the probe worker deadlocks Invoke/WinForms.
        applied = apply_windows_maximized_bounds(window)
        resize_frame = ensure_windows_resize_frame(window.native.Handle.ToInt64())
        holder['maximized_bounds_applied'] = applied
        holder['resize_frame_applied'] = resize_frame
        if results.get('native') is not None:
            results['native']['maximized_bounds_applied'] = applied
            results['native']['resize_frame_applied'] = resize_frame

    def prepare_window(*_):
        try:
            holder['startup_geometry_applied'] = apply_windows_startup_geometry(window, geometry, scale_factor)
            set_maximized_bounds()
        finally:
            geometry_ready.set()

    window.events.shown += prepare_window
    window.events.moved += set_maximized_bounds

    def run_probe():
        try:
            if not window.events.shown.wait(20):
                raise RuntimeError('native pywebview test window did not become visible')
            if not geometry_ready.wait(20):
                raise RuntimeError('native window geometry was not initialized')

            native = window.native
            hwnd = native.Handle.ToInt64()
            workarea = next((area for area in workareas if area.get('primary')), workareas[0])
            physical_workareas = get_windows_workareas(physical=True)
            physical_workarea = next(
                (area for area in physical_workareas if area.get('primary')),
                physical_workareas[0] if physical_workareas else None,
            )
            initial = _window_rect(hwnd)
            dpi = int(ctypes.windll.user32.GetDpiForWindow(hwnd))
            browser_metrics = window.evaluate_js('({dpr: window.devicePixelRatio, width: window.innerWidth, height: window.innerHeight})')
            results['native'] = {
                'dpi': dpi,
                'dpiAfterWebViewInit': int(ctypes.windll.user32.GetDpiForSystem()),
                'physicalWorkareasAfterInit': physical_workareas,
                'browserMetrics': browser_metrics,
                'initialRect': initial,
                'pywebviewPosition': {'x': int(window.x), 'y': int(window.y)},
                'clientSize': {'width': int(window.width), 'height': int(window.height)},
                'formSize': {'width': int(native.Width), 'height': int(native.Height)},
                'formClientSize': {
                    'width': int(native.ClientSize.Width),
                    'height': int(native.ClientSize.Height),
                },
                'webviewControlSize': {
                    'width': int(native.browser.webview.Width),
                    'height': int(native.browser.webview.Height),
                },
                'minimumSize': {'width': int(native.MinimumSize.Width), 'height': int(native.MinimumSize.Height)},
                'maximized_bounds_applied': holder.get('maximized_bounds_applied', False),
                'resize_frame_applied': holder.get('resize_frame_applied', False),
                'maximizedBounds': {
                    'x': int(native.MaximizedBounds.X),
                    'y': int(native.MaximizedBounds.Y),
                    'width': int(native.MaximizedBounds.Width),
                    'height': int(native.MaximizedBounds.Height),
                },
            }
            results['checks']['initial_inside_physical_work_area'] = bool(
                physical_workarea
                and initial['x'] >= physical_workarea['x']
                and initial['y'] >= physical_workarea['y']
                and initial['x'] + initial['width'] <= physical_workarea['x'] + physical_workarea['width']
                and initial['y'] + initial['height'] <= physical_workarea['y'] + physical_workarea['height']
            )
            results['checks']['initial_matches_planned_physical_size'] = (
                abs(initial['width'] - round(geometry['width'] * scale_factor)) <= 2
                and abs(initial['height'] - round(geometry['height'] * scale_factor)) <= 2
            )
            results['checks']['work_area_scale_conversion'] = bool(
                physical_workarea
                and abs(physical_workarea['x'] - workarea['x'] * scale_factor) <= 2
                and abs(physical_workarea['y'] - workarea['y'] * scale_factor) <= 2
                and abs(physical_workarea['width'] - workarea['width'] * scale_factor) <= 2
                and abs(physical_workarea['height'] - workarea['height'] * scale_factor) <= 2
            )
            results['checks']['client_size_matches_css_dpr'] = (
                abs(int(native.browser.webview.Width) - int(browser_metrics['width'] * browser_metrics['dpr'])) <= 2
                and abs(int(native.browser.webview.Height) - int(browser_metrics['height'] * browser_metrics['dpr'])) <= 2
            )
            results['checks']['native_resize_frame_enabled'] = bool(
                holder.get('resize_frame_applied')
                and int(native.MinimumSize.Width) >= round(geometry['min_size'][0] * scale_factor)
                and int(native.MinimumSize.Height) >= round(geometry['min_size'][1] * scale_factor)
            )

            user32 = ctypes.windll.user32
            class Point(ctypes.Structure):
                _fields_ = [('x', wintypes.LONG), ('y', wintypes.LONG)]

            client = native.ClientRectangle
            client_width = int(client.Width)
            client_height = int(client.Height)
            client_to_screen = user32.ClientToScreen
            client_to_screen.argtypes = [wintypes.HWND, ctypes.POINTER(Point)]
            client_to_screen.restype = wintypes.BOOL
            send_message = user32.SendMessageW
            send_message.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
            send_message.restype = ctypes.c_ssize_t

            def hit_test(hwnd_value, x, y):
                point = Point(x, y)
                if not client_to_screen(hwnd, ctypes.byref(point)):
                    raise ctypes.WinError(ctypes.get_last_error())
                packed = ((point.y & 0xFFFF) << 16) | (point.x & 0xFFFF)
                return int(send_message(hwnd_value, 0x0084, 0, packed))

            native_hit_tests = {
                'formTopLeft': hit_test(hwnd, 2, 2),
                'formBottomRight': hit_test(hwnd, client_width - 2, client_height - 2),
                'formLeft': hit_test(hwnd, 2, client_height // 2),
                'formRight': hit_test(hwnd, client_width - 2, client_height // 2),
                'formTop': hit_test(hwnd, client_width // 2, 2),
                'formBottom': hit_test(hwnd, client_width // 2, client_height - 2),
            }
            results['native']['resizeHitTests'] = native_hit_tests
            results['checks']['form_hit_tests_native_resize_corners'] = (
                native_hit_tests['formTopLeft'] == 13
                and native_hit_tests['formBottomRight'] == 17
            )
            results['checks']['form_hit_tests_native_resize_edges'] = (
                [native_hit_tests[key] for key in ('formLeft', 'formRight', 'formTop', 'formBottom')]
                == [10, 11, 12, 15]
            )
            results['checks']['resize_band_is_outside_chromium'] = (
                int(native.Padding.Left) >= round(6 * dpi / 96)
                and int(native.browser.webview.Left) >= int(native.Padding.Left)
                and int(native.browser.webview.Top) >= int(native.Padding.Top)
            )

            user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
            user32.GetAsyncKeyState.restype = ctypes.c_short
            if not (user32.GetAsyncKeyState(0x01) & 0x8000):
                started_at = time.monotonic()
                native_resize_result = api.begin_native_resize('se')
                results['native']['beginNativeResizeWithoutButton'] = native_resize_result
                results['checks']['released_pointer_skips_native_modal_loop'] = (
                    native_resize_result.get('code') == 0
                    and native_resize_result.get('supported') is True
                    and native_resize_result.get('started') is False
                    and time.monotonic() - started_at < 1.0
                )
            else:
                results['checks']['released_pointer_skips_native_modal_loop'] = False
                results['native']['beginNativeResizeWithoutButton'] = 'skipped: left mouse button was already down'

            expected_width = max(int(native.MinimumSize.Width), int(geometry['width'] * scale_factor) - 200)
            expected_height = max(int(native.MinimumSize.Height), int(geometry['height'] * scale_factor) - 200)
            for offset in (40, 80, 120, 160, 200):
                window.resize(
                    max(int(native.MinimumSize.Width), int(geometry['width'] * scale_factor) - offset),
                    max(int(native.MinimumSize.Height), int(geometry['height'] * scale_factor) - offset),
                    FixPoint.NORTH | FixPoint.WEST,
                )
                time.sleep(0.08)
            repeated = _window_rect(hwnd)
            results['native']['after_repeated_resize'] = repeated
            results['checks']['repeated_resize_completed'] = (
                abs(int(native.Width) - expected_width) <= 2
                and abs(int(native.Height) - expected_height) <= 2
            )

            window.resize(200, 200, FixPoint.NORTH | FixPoint.WEST)
            time.sleep(0.15)
            small = _window_rect(hwnd)
            results['native']['after_minimum_resize_request'] = small
            results['native']['minimumBrowserMetrics'] = window.evaluate_js(
                '({dpr: window.devicePixelRatio, width: window.innerWidth, height: window.innerHeight})'
            )
            results['checks']['minimum_size_enforced'] = (
                int(native.Width) >= round(geometry['min_size'][0] * scale_factor)
                and int(native.Height) >= round(geometry['min_size'][1] * scale_factor)
            )

            window.maximize()
            results['checks']['maximize_event'] = window.events.maximized.wait(4)
            results['native']['maximizedRect'] = _window_rect(hwnd)
            results['checks']['maximized_inside_work_area'] = bool(
                physical_workarea
                and results['native']['maximizedRect']['x'] >= physical_workarea['x']
                and results['native']['maximizedRect']['y'] >= physical_workarea['y']
                and results['native']['maximizedRect']['x'] + results['native']['maximizedRect']['width'] <= physical_workarea['x'] + physical_workarea['width']
                and results['native']['maximizedRect']['y'] + results['native']['maximizedRect']['height'] <= physical_workarea['y'] + physical_workarea['height']
            )
            results['checks']['maximized_bounds_applied'] = results['native']['maximized_bounds_applied']
            window.restore()
            results['checks']['restore_event'] = window.events.restored.wait(4)
            results['native']['restoredRect'] = _window_rect(hwnd)
            results['checks']['restored_inside_work_area'] = (
                physical_workarea
                and results['native']['restoredRect']['x'] >= physical_workarea['x']
                and results['native']['restoredRect']['y'] >= physical_workarea['y']
                and results['native']['restoredRect']['x'] + results['native']['restoredRect']['width'] <= physical_workarea['x'] + physical_workarea['width']
                and results['native']['restoredRect']['y'] + results['native']['restoredRect']['height'] <= physical_workarea['y'] + physical_workarea['height']
            )
        except Exception as err:
            errors.append(f'{type(err).__name__}: {err}')
        finally:
            try:
                window.destroy()
            except Exception as err:
                errors.append(f'window cleanup: {type(err).__name__}: {err}')
            finished.set()

    def start_probe():
        threading.Thread(target=run_probe, name='windows-native-window-probe', daemon=True).start()

    with tempfile.TemporaryDirectory(prefix='ppx-window-probe-', ignore_cleanup_errors=True) as profile:
        webview.start(func=start_probe, private_mode=True, storage_path=profile, gui='edgechromium')
        finished.wait(2)

    results['errors'] = errors
    results['ok'] = not errors and all(results['checks'].values())
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if results['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

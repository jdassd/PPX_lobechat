"""Helpers for keeping the desktop window inside an available work area."""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

_WINDOW_RESIZE_SUBCLASSES = {}
_RESIZE_SUBCLASS_ID = 0x505058
_SUBCLASSPROC = getattr(ctypes, 'WINFUNCTYPE', ctypes.CFUNCTYPE)(
    ctypes.c_ssize_t,
    wintypes.HWND,
    wintypes.UINT,
    ctypes.c_size_t,
    ctypes.c_ssize_t,
    ctypes.c_size_t,
    ctypes.c_size_t,
)


def _install_windows_resize_hit_test(hwnd):
    """Handle only the Form-owned border, without hooking Chromium child HWNDs."""
    hwnd = int(hwnd)
    if hwnd in _WINDOW_RESIZE_SUBCLASSES:
        return True
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    comctl32 = ctypes.WinDLL('comctl32', use_last_error=True)
    set_subclass = comctl32.SetWindowSubclass
    set_subclass.argtypes = [wintypes.HWND, _SUBCLASSPROC, ctypes.c_size_t, ctypes.c_size_t]
    set_subclass.restype = wintypes.BOOL
    remove_subclass = comctl32.RemoveWindowSubclass
    remove_subclass.argtypes = [wintypes.HWND, _SUBCLASSPROC, ctypes.c_size_t]
    remove_subclass.restype = wintypes.BOOL
    def_subclass_proc = comctl32.DefSubclassProc
    def_subclass_proc.argtypes = [wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t]
    def_subclass_proc.restype = ctypes.c_ssize_t
    def_window_proc = user32.DefWindowProcW
    def_window_proc.argtypes = [wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t]
    def_window_proc.restype = ctypes.c_ssize_t

    class Point(ctypes.Structure):
        _fields_ = [('x', wintypes.LONG), ('y', wintypes.LONG)]

    class Rect(ctypes.Structure):
        _fields_ = [
            ('left', wintypes.LONG),
            ('top', wintypes.LONG),
            ('right', wintypes.LONG),
            ('bottom', wintypes.LONG),
        ]

    screen_to_client = user32.ScreenToClient
    screen_to_client.argtypes = [wintypes.HWND, ctypes.POINTER(Point)]
    screen_to_client.restype = wintypes.BOOL
    get_client_rect = user32.GetClientRect
    get_client_rect.argtypes = [wintypes.HWND, ctypes.POINTER(Rect)]
    get_client_rect.restype = wintypes.BOOL
    is_zoomed = user32.IsZoomed
    is_zoomed.argtypes = [wintypes.HWND]
    is_zoomed.restype = wintypes.BOOL
    get_dpi = user32.GetDpiForWindow
    get_dpi.argtypes = [wintypes.HWND]
    get_dpi.restype = wintypes.UINT

    root_hwnd = wintypes.HWND(hwnd)

    def is_on_resize_edge(lparam):
        rect = Rect()
        if not get_client_rect(root_hwnd, ctypes.byref(rect)):
            return False
        width = int(rect.right - rect.left)
        height = int(rect.bottom - rect.top)
        dpi = max(96, int(get_dpi(root_hwnd)))
        edge = max(6, round(6 * dpi / 96))
        corner = max(edge, round(12 * dpi / 96))
        point = Point(
            ctypes.c_short(lparam & 0xFFFF).value,
            ctypes.c_short((lparam >> 16) & 0xFFFF).value,
        )
        if not screen_to_client(root_hwnd, ctypes.byref(point)):
            return False
        x, y = int(point.x), int(point.y)
        if not (0 <= x < width and 0 <= y < height):
            return False
        left_corner = x < corner
        right_corner = x >= width - corner
        top_corner = y < corner
        bottom_corner = y >= height - corner
        if left_corner and top_corner:
            hit = 13  # HTTOPLEFT
        elif right_corner and top_corner:
            hit = 14  # HTTOPRIGHT
        elif left_corner and bottom_corner:
            hit = 16  # HTBOTTOMLEFT
        elif right_corner and bottom_corner:
            hit = 17  # HTBOTTOMRIGHT
        elif x < edge:
            hit = 10 if corner <= y < height - corner else None  # HTLEFT
        elif x >= width - edge:
            hit = 11 if corner <= y < height - corner else None  # HTRIGHT
        elif y < edge:
            hit = 12  # HTTOP
        elif y >= height - edge:
            hit = 15  # HTBOTTOM
        else:
            hit = None
        return hit or False

    @_SUBCLASSPROC
    def resize_hit_test(window_hwnd, message, wparam, lparam, subclass_id, ref_data):
        WM_NCHITTEST = 0x0084
        WM_NCDESTROY = 0x0082
        WM_NCLBUTTONDOWN = 0x00A1
        try:
            if message == WM_NCHITTEST and not is_zoomed(root_hwnd):
                hit = is_on_resize_edge(lparam)
                if hit:
                    return hit
            if message == WM_NCLBUTTONDOWN and 10 <= int(wparam) <= 17 and not is_zoomed(root_hwnd):
                # FormBorderStyle.None may consume client-band resize starts.
                # Let the OS process this real input synchronously instead.
                return def_window_proc(window_hwnd, message, wparam, lparam)
        except Exception:
            # An exception must never escape a native window procedure.
            pass

        result = def_subclass_proc(window_hwnd, message, wparam, lparam)
        if message == WM_NCDESTROY:
            remove_subclass(window_hwnd, resize_hit_test, subclass_id)
            _WINDOW_RESIZE_SUBCLASSES.pop(int(ctypes.c_void_p(window_hwnd).value or 0), None)
        return result

    if not set_subclass(root_hwnd, resize_hit_test, _RESIZE_SUBCLASS_ID, 0):
        raise ctypes.WinError(ctypes.get_last_error())
    _WINDOW_RESIZE_SUBCLASSES[hwnd] = resize_hit_test
    return True


def get_windows_workareas(physical=False):
    """Return Windows work areas, optionally in per-monitor physical pixels.

    Before pywebview initializes WinForms, Windows may virtualize this process's
    coordinates to 96 DPI. pywebview later switches the GUI thread to a DPI-aware
    context and scales initial WebView2 coordinates, so startup geometry should
    use the default logical coordinates. Native probes may request physical
    coordinates to compare against GetWindowRect.
    """
    if sys.platform != 'win32':
        return []

    class Rect(ctypes.Structure):
        _fields_ = [
            ('left', wintypes.LONG),
            ('top', wintypes.LONG),
            ('right', wintypes.LONG),
            ('bottom', wintypes.LONG),
        ]

    class MonitorInfo(ctypes.Structure):
        _fields_ = [
            ('cbSize', wintypes.DWORD),
            ('rcMonitor', Rect),
            ('rcWork', Rect),
            ('dwFlags', wintypes.DWORD),
        ]

    monitors = []
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    get_monitor_info = user32.GetMonitorInfoW
    get_monitor_info.argtypes = [ctypes.c_void_p, ctypes.POINTER(MonitorInfo)]
    get_monitor_info.restype = wintypes.BOOL

    monitor_callback_type = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.POINTER(Rect),
        ctypes.c_ssize_t,
    )

    def collect_monitor(monitor, _dc, _rect, _data):
        info = MonitorInfo()
        info.cbSize = ctypes.sizeof(MonitorInfo)
        if not get_monitor_info(monitor, ctypes.byref(info)):
            return True
        bounds = info.rcWork
        width = int(bounds.right - bounds.left)
        height = int(bounds.bottom - bounds.top)
        if width > 0 and height > 0:
            monitors.append({
                'x': int(bounds.left),
                'y': int(bounds.top),
                'width': width,
                'height': height,
                'primary': bool(info.dwFlags & 1),
            })
        return True

    callback = monitor_callback_type(collect_monitor)
    user32.EnumDisplayMonitors.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        monitor_callback_type,
        ctypes.c_ssize_t,
    ]
    user32.EnumDisplayMonitors.restype = wintypes.BOOL
    previous_dpi_context = None
    if physical:
        try:
            set_thread_dpi_context = user32.SetThreadDpiAwarenessContext
            set_thread_dpi_context.argtypes = [ctypes.c_void_p]
            set_thread_dpi_context.restype = ctypes.c_void_p
            # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 is the pseudo-handle -4.
            previous_dpi_context = set_thread_dpi_context(ctypes.c_void_p(-4))
        except (AttributeError, OSError):
            return []

    try:
        if not user32.EnumDisplayMonitors(None, None, callback, 0):
            return []
    finally:
        if physical and previous_dpi_context:
            set_thread_dpi_context(previous_dpi_context)
    return monitors


def get_windows_scale_factor():
    """Return the Windows scale factor used by pywebview's WebView2 backend."""
    if sys.platform != 'win32':
        return 1.0
    try:
        return max(1.0, float(ctypes.windll.shcore.GetScaleFactorForDevice(0)) / 100.0)
    except (AttributeError, OSError, TypeError, ValueError):
        try:
            return max(1.0, float(ctypes.windll.user32.GetDpiForSystem()) / 96.0)
        except (AttributeError, OSError, TypeError, ValueError):
            return 1.0


def logicalize_saved_window_state(payload, scale_factor=1.0):
    """Convert legacy saved Windows device-pixel bounds to pywebview units."""
    state = dict(payload)
    if int(state.get('schemaVersion') or 1) >= 2:
        return state

    scale = max(1.0, float(scale_factor or 1.0))
    for key in ('width', 'height', 'x', 'y'):
        if state.get(key) is not None:
            state[key] = round(int(state[key]) / scale)
    return state


def migrate_display_geometry(geometry, schema_version, constructor_adjustment, min_size=(640, 400)):
    """Translate compensated schema-3 targets back to their shown dimensions.

    Schema 3 saved constructor dimensions plus the WinForms trim. Earlier
    schemas stored the dimensions users actually saw. Schema 4 stores actual
    logical dimensions again, so only schema 3 needs this one-time adjustment.
    """
    migrated = dict(geometry)
    if int(schema_version or 1) == 3:
        trim_width, trim_height = constructor_adjustment
        migrated['width'] = max(int(min_size[0]), int(migrated['width']) - max(0, int(trim_width)))
        migrated['height'] = max(int(min_size[1]), int(migrated['height']) - max(0, int(trim_height)))
    return migrated


def logicalize_native_window_value(value, scale_factor=1.0):
    """Convert a WinForms device-pixel value to pywebview startup units."""
    scale = max(1.0, float(scale_factor or 1.0))
    return round(int(value) / scale)


def apply_windows_maximized_bounds(window):
    """Constrain a borderless WinForms maximize to the current monitor work area.

    Call from a WinForms event/UI thread after the form has been created.
    """
    native = getattr(window, 'native', None)
    if sys.platform != 'win32' or native is None:
        return False

    try:
        from System import Func, Type
        from System.Windows.Forms import Padding, Screen

        applied = []

        def update_native_window():
            ensure_windows_resize_frame(native.Handle.ToInt64())
            # WebView2 owns out-of-process child HWNDs that cannot be subclassed
            # by WinForms. Reserve a small, visible Form-owned resize band so
            # physical input reaches Windows synchronously, before Chromium.
            get_dpi = ctypes.WinDLL('user32').GetDpiForWindow
            get_dpi.argtypes = [wintypes.HWND]
            get_dpi.restype = wintypes.UINT
            dpi = get_dpi(native.Handle.ToInt64())
            band = max(6, round(6 * max(96, dpi) / 96))
            if int(native.Padding.Left) != band:
                native.Padding = Padding(band)
            work_area = Screen.FromControl(native).WorkingArea
            current = native.MaximizedBounds
            if (
                int(current.X) != int(work_area.X)
                or int(current.Y) != int(work_area.Y)
                or int(current.Width) != int(work_area.Width)
                or int(current.Height) != int(work_area.Height)
            ):
                native.MaximizedBounds = work_area
            applied.append(True)

        if hasattr(native, 'Invoke'):
            native.Invoke(Func[Type](update_native_window))
        else:
            update_native_window()
        return bool(applied)
    except Exception:
        return False


def apply_windows_startup_geometry(window, geometry, scale_factor=1.0):
    """Apply planned bounds after WinForms DPI initialization, before showing.

    pywebview creates its Form before WinForms finishes DPI scaling and before
    the app changes the form to borderless mode. Correcting the form in its
    first Shown callback (while its opacity is zero) avoids the client-area
    deductions from becoming a permanent loss in the saved bounds.
    """
    native = getattr(window, 'native', None)
    if sys.platform != 'win32' or native is None:
        return False

    try:
        from System import Func, Type
        from System.Drawing import Point, Size
        from System.Windows.Forms import FormWindowState

        scale = max(1.0, float(scale_factor or 1.0))
        bounds = (
            round(int(geometry['x']) * scale),
            round(int(geometry['y']) * scale),
            round(int(geometry['width']) * scale),
            round(int(geometry['height']) * scale),
        )
        applied = []

        def set_native_bounds():
            x, y, width, height = bounds
            native.WindowState = FormWindowState.Normal
            minimum_width, minimum_height = geometry['min_size']
            native.MinimumSize = Size(round(int(minimum_width) * scale), round(int(minimum_height) * scale))
            native.Size = Size(width, height)
            native.Location = Point(x, y)
            applied.append(True)

        if hasattr(native, 'Invoke'):
            native.Invoke(Func[Type](set_native_bounds))
        else:
            set_native_bounds()
        return bool(applied)
    except Exception:
        return False


def ensure_windows_resize_frame(hwnd):
    """Restore the native resize hit-test frame on a captionless WinForms window.

    pywebview's ``frameless=True`` removes the standard non-client area. Keeping
    ``WS_THICKFRAME`` while omitting ``WS_CAPTION`` lets Windows perform resize
    drags itself, including pointer capture and minimum-size enforcement, while
    the app keeps its custom title bar.
    """
    if sys.platform != 'win32' or not hwnd:
        return False

    user32 = ctypes.WinDLL('user32', use_last_error=True)
    get_window_long_ptr = user32.GetWindowLongPtrW
    get_window_long_ptr.argtypes = [wintypes.HWND, ctypes.c_int]
    get_window_long_ptr.restype = ctypes.c_ssize_t
    set_window_long_ptr = user32.SetWindowLongPtrW
    set_window_long_ptr.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
    set_window_long_ptr.restype = ctypes.c_ssize_t
    set_window_pos = user32.SetWindowPos
    set_window_pos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                               ctypes.c_int, ctypes.c_int, wintypes.UINT]
    set_window_pos.restype = wintypes.BOOL

    GWL_STYLE = -16
    WS_POPUP = 0x80000000
    WS_CAPTION = 0x00C00000
    WS_THICKFRAME = 0x00040000
    SWP_NOSIZE = 0x0001
    SWP_NOMOVE = 0x0002
    SWP_NOZORDER = 0x0004
    SWP_NOACTIVATE = 0x0010
    SWP_FRAMECHANGED = 0x0020

    handle = wintypes.HWND(int(hwnd))
    style = int(get_window_long_ptr(handle, GWL_STYLE))
    desired_style = (style | WS_THICKFRAME) & ~(WS_CAPTION | WS_POPUP)
    if style != desired_style:
        ctypes.set_last_error(0)
        previous = set_window_long_ptr(handle, GWL_STYLE, desired_style)
        if previous == 0 and ctypes.get_last_error():
            raise ctypes.WinError(ctypes.get_last_error())
        if not set_window_pos(
            handle, None, 0, 0, 0, 0,
            SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
        ):
            raise ctypes.WinError(ctypes.get_last_error())

    actual_style = int(get_window_long_ptr(handle, GWL_STYLE))
    style_enabled = (
        bool(actual_style & WS_THICKFRAME)
        and not bool(actual_style & WS_CAPTION)
        and not bool(actual_style & WS_POPUP)
    )
    return style_enabled and _install_windows_resize_hit_test(hwnd)


def _intersection_area(rect, area):
    left = max(rect['x'], area['x'])
    top = max(rect['y'], area['y'])
    right = min(rect['x'] + rect['width'], area['x'] + area['width'])
    bottom = min(rect['y'] + rect['height'], area['y'] + area['height'])
    return max(0, right - left) * max(0, bottom - top)


def calculate_window_geometry(
    workareas,
    saved_state=None,
    initial_size=(1280, 800),
    min_size=(640, 400),
    default_max_ratio=0.9,
):
    """Choose a clamped geometry in the saved window's monitor or primary area."""
    if not workareas:
        saved = saved_state or {}
        return {
            'width': max(min_size[0], int(saved.get('width') or initial_size[0])),
            'height': max(min_size[1], int(saved.get('height') or initial_size[1])),
            'x': saved.get('x'),
            'y': saved.get('y'),
            'min_size': min_size,
            'restored': bool(saved_state),
        }

    primary = next((area for area in workareas if area.get('primary')), workareas[0])
    saved = saved_state or {}
    saved_width = int(saved.get('width') or initial_size[0])
    saved_height = int(saved.get('height') or initial_size[1])
    has_saved_position = saved.get('x') is not None and saved.get('y') is not None
    target = primary

    if has_saved_position:
        saved_rect = {
            'x': int(saved['x']),
            'y': int(saved['y']),
            'width': saved_width,
            'height': saved_height,
        }
        target = max(workareas, key=lambda area: _intersection_area(saved_rect, area))
        if _intersection_area(saved_rect, target) == 0:
            target = primary

    available_width = max(1, int(target['width']))
    available_height = max(1, int(target['height']))
    minimum_width = min(int(min_size[0]), available_width)
    minimum_height = min(int(min_size[1]), available_height)

    if saved_state:
        width = min(available_width, max(minimum_width, saved_width))
        height = min(available_height, max(minimum_height, saved_height))
    else:
        width_cap = max(minimum_width, int(available_width * default_max_ratio))
        height_cap = max(minimum_height, int(available_height * default_max_ratio))
        width = min(available_width, max(minimum_width, min(int(initial_size[0]), width_cap)))
        height = min(available_height, max(minimum_height, min(int(initial_size[1]), height_cap)))

    if has_saved_position and _intersection_area(saved_rect, target) > 0:
        x = min(max(int(saved['x']), int(target['x'])), int(target['x']) + available_width - width)
        y = min(max(int(saved['y']), int(target['y'])), int(target['y']) + available_height - height)
    else:
        x = int(target['x']) + (available_width - width) // 2
        y = int(target['y']) + (available_height - height) // 2

    return {
        'width': width,
        'height': height,
        'x': x,
        'y': y,
        'min_size': (minimum_width, minimum_height),
        'restored': bool(saved_state),
    }

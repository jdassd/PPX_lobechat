"""Exercise the product browser picker against an isolated local fixture."""
from __future__ import annotations

import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

FIXTURE_HTML = """<!doctype html>
<html><head><title>PPX default-cache browser smoke</title></head>
<body><main id="ppx-default-smoke-fixture">default browser cache smoke</main></body></html>
"""

READY_SCRIPT = r"""
(() => {
  const notify = () => {
    if (window.__ppxDefaultSmokeReady) return;
    if (!document.querySelector('#ppx-default-smoke-fixture') || !document.querySelector('#__ppx_bar')) return;
    window.__ppxDefaultSmokeReady = true;
    try {
      window.__ppxEvent({type: 'defaultSmokeReady', title: document.title,
        marker: document.querySelector('#ppx-default-smoke-fixture').textContent,
        userAgent: navigator.userAgent});
    } catch (_) {}
  };
  new MutationObserver(notify).observe(document, {childList: true, subtree: true});
  notify();
})();
"""


class _FixtureHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        payload = FIXTURE_HTML.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, _format, *_args):
        return


def run_default_browser_smoke(service, timeout: float = 45.0) -> dict[str, Any]:
    """Start the real WebAutoTool picker without overriding its browser cache env."""
    if 'PLAYWRIGHT_BROWSERS_PATH' in os.environ:
        raise RuntimeError('PLAYWRIGHT_BROWSERS_PATH must be absent in the parent process.')

    from playwright.sync_api import BrowserType

    from api import webauto as webauto_module

    expected_cache = service._wa_browsers_dir().resolve()
    expected_executable = service._wa_chromium_executable_path()
    if expected_executable is None:
        raise FileNotFoundError(f'No Chromium executable found in default cache {expected_cache}')
    expected_executable = expected_executable.resolve()
    if not expected_executable.is_relative_to(expected_cache):
        raise AssertionError(f'Chromium executable is outside the default cache: {expected_executable}')

    captured: dict[str, Any] = {'readyEvent': None, 'launchKwargs': None}
    original_launch = BrowserType.launch_persistent_context
    original_script = webauto_module._PICK_SCRIPT
    original_event_handler = service._wa_handle_pick_event

    def headless_launch(browser_type, *args, **kwargs):
        # Keep the product-selected executable_path and all other options intact.
        captured['launchKwargs'] = dict(kwargs)
        test_kwargs = dict(kwargs)
        test_kwargs['headless'] = True
        return original_launch(browser_type, *args, **test_kwargs)

    def capture_event(payload):
        if isinstance(payload, dict) and payload.get('type') == 'defaultSmokeReady':
            captured['readyEvent'] = {key: payload.get(key) for key in ('title', 'marker', 'userAgent')}
        return original_event_handler(payload)

    server = ThreadingHTTPServer(('127.0.0.1', 0), _FixtureHandler)
    server_thread = threading.Thread(target=server.serve_forever, name='ppx-default-browser-fixture', daemon=True)
    server_thread.start()
    url = f'http://127.0.0.1:{server.server_port}/'
    try:
        BrowserType.launch_persistent_context = headless_launch
        webauto_module._PICK_SCRIPT = original_script + '\n' + READY_SCRIPT
        service._wa_handle_pick_event = capture_event
        result = service.webauto_pick_start({'url': url})
        if result.get('code') != 0:
            raise RuntimeError(f'webauto_pick_start failed: {result}')

        deadline = time.monotonic() + timeout
        last_state = {}
        while time.monotonic() < deadline:
            last_state = service.webauto_pick_state()
            if captured['readyEvent']:
                break
            if last_state.get('error') or last_state.get('done'):
                raise RuntimeError(f'Picker exited before toolbar readiness: state={last_state}')
            thread = getattr(service, '_wa_pick_thread', None)
            if thread is not None and not thread.is_alive():
                raise RuntimeError(f'Picker thread exited before toolbar readiness: state={last_state}')
            time.sleep(0.1)
        if not captured['readyEvent']:
            raise TimeoutError(f'Picker toolbar/fixture readiness timed out after {timeout}s; state={last_state}')

        kwargs = captured['launchKwargs'] or {}
        launched_executable = Path(str(kwargs.get('executable_path', ''))).resolve()
        if launched_executable != expected_executable:
            raise AssertionError(
                f'Product launch executable mismatch: launch={launched_executable}, expected={expected_executable}'
            )
        if not launched_executable.is_relative_to(expected_cache):
            raise AssertionError(f'Product launch executable is outside the default cache: {launched_executable}')

        return {
            'parentPlaywrightBrowsersPathAbsent': 'PLAYWRIGHT_BROWSERS_PATH' not in os.environ,
            'defaultCachePath': str(expected_cache),
            'launchExecutablePath': str(launched_executable),
            'launchExecutableMatchesDefaultCache': True,
            'productHeadlessWas': captured['launchKwargs'].get('headless'),
            'testOnlyHeadlessOverride': True,
            'toolbarReady': True,
            'readyEvent': captured['readyEvent'],
            'apiState': last_state,
        }
    finally:
        try:
            service.webauto_pick_cancel()
        finally:
            thread = getattr(service, '_wa_pick_thread', None)
            if thread is not None:
                thread.join(timeout=8)
            thread_stopped = thread is None or not thread.is_alive()
            service._wa_handle_pick_event = original_event_handler
            webauto_module._PICK_SCRIPT = original_script
            BrowserType.launch_persistent_context = original_launch
            server.shutdown()
            server.server_close()
            server_thread.join(timeout=3)
            if not thread_stopped:
                raise TimeoutError('The WebAutoTool picker thread did not stop after cancel/join.')

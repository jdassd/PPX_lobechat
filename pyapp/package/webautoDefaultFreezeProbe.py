"""Tiny frozen entry point for the Playwright default-cache regression probe."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path


def main() -> int:
    from api.webauto import WebAutoTool
    from pyapp.config.config import Config
    from pyapp.package.webautoDefaultSmoke import run_default_browser_smoke

    report_path = Path(sys.argv[1]).resolve()
    report = {'passed': False, 'frozen': bool(getattr(sys, 'frozen', False)),
              'playwrightBrowsersPathAbsent': 'PLAYWRIGHT_BROWSERS_PATH' not in os.environ}
    if not report['playwrightBrowsersPathAbsent']:
        report['error'] = 'PLAYWRIGHT_BROWSERS_PATH must be absent in the frozen probe process.'
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        return 1

    with tempfile.TemporaryDirectory(prefix='ppx-webauto-freeze-profile-') as temporary:
        Config.appDataDir = str(Path(temporary) / 'app-data')
        Path(Config.appDataDir).mkdir(parents=True)
        service = WebAutoTool()
        try:
            status = service.webauto_status()
            if status.get('code') != 0 or not status.get('installed'):
                raise RuntimeError(f'Default-cache Chromium is not installed: {status}')
            report['initialStatus'] = {'ready': bool(status.get('ready')), 'installed': bool(status.get('installed'))}
            report['browser'] = run_default_browser_smoke(service)
            report['passed'] = True
        except Exception as exc:
            state = service.webauto_pick_state()
            report['apiState'] = state
            report['error'] = f'{type(exc).__name__}: {exc}'
            thread = getattr(service, '_wa_pick_thread', None)
            if thread is not None and thread.is_alive():
                service.webauto_pick_cancel()
                thread.join(timeout=8)
        finally:
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

"""Check actual main-window close/reopen geometry with an isolated Windows profile."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def child(profile, output):
    os.environ['APPDATA'] = str(profile)
    sys.path.insert(0, str(ROOT))
    import main

    main._resolve_dev_server = lambda *_: str(ROOT / 'gui/dist/index.html')
    original_start = main.webview.start
    main.webview.start = lambda **kwargs: original_start(**{
        **kwargs, 'debug': False, 'private_mode': True, 'storage_path': str(profile / 'webview'),
    })
    original_create = main.webview.create_window

    def create(*args, **kwargs):
        window = original_create(*args, **kwargs)

        def check():
            try:
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    if window.evaluate_js('Boolean(document.querySelector("nav"))'):
                        break
                    time.sleep(0.1)
                else:
                    raise RuntimeError('Desktop frontend did not initialize')
                report = {
                    'width': int(window.width), 'height': int(window.height),
                    'x': int(window.x), 'y': int(window.y),
                    'constructorAdjustment': list(main._window_constructor_adjustment),
                }
                output.write_text(json.dumps(report), encoding='utf-8')
            finally:
                window.destroy()

        window.events.loaded += check
        return window

    main.webview.create_window = create
    main.WebViewApp(ifDev=True)


def run():
    if sys.platform != 'win32':
        raise RuntimeError('This probe requires a Windows desktop')
    if '--child' in sys.argv:
        child(Path(sys.argv[2]), Path(sys.argv[3]))
        return
    with tempfile.TemporaryDirectory(prefix='ppx-restore-probe-', ignore_cleanup_errors=True) as temporary:
        profile = Path(temporary)
        rounds = []
        for index in range(3):
            output = profile / f'round-{index}.json'
            subprocess.run([sys.executable, str(Path(__file__).resolve()), '--child', str(profile), str(output)],
                           cwd=ROOT, check=True, timeout=60)
            rounds.append(json.loads(output.read_text(encoding='utf-8')))
        saved = json.loads((profile / 'ppx.jdassd.tools/window-state.json').read_text(encoding='utf-8'))
        stable = all(all(abs(item[key] - rounds[0][key]) <= 2 for key in ('width', 'height', 'x', 'y')) for item in rounds[1:])
        report = {'passed': stable, 'rounds': rounds, 'finalState': saved, 'checks': ['close and reopen twice without accumulating size loss']}
        target = ROOT / 'build/verification/windows-restore.json'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report, indent=2))
        if not stable:
            raise RuntimeError('Native window bounds changed after close/reopen')


if __name__ == '__main__':
    run()

"""Check real Windows startup, legacy migration, and close/reopen geometry."""
from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import tempfile
import threading
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

        def check_after_visible():
            try:
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    if window.native.Visible and window.evaluate_js('Boolean(document.querySelector("nav"))'):
                        break
                    time.sleep(0.1)
                else:
                    raise RuntimeError('Desktop frontend did not load and become visible')
                scale = float(main._window_coordinate_scale)
                requested = kwargs
                native = window.native
                report = {
                    'constructorRequested': {
                        'width': int(requested['width']), 'height': int(requested['height']),
                        'x': int(requested['x']), 'y': int(requested['y']),
                    },
                    'appliedGeometry': dict(window._ppx_startup_geometry),
                    'expectedPhysical': {
                        'width': round(int(window._ppx_startup_geometry['width']) * scale),
                        'height': round(int(window._ppx_startup_geometry['height']) * scale),
                        'x': round(int(window._ppx_startup_geometry['x']) * scale),
                        'y': round(int(window._ppx_startup_geometry['y']) * scale),
                    },
                    'observed': {
                        'width': int(native.Width), 'height': int(native.Height),
                        'x': int(native.Left), 'y': int(native.Top),
                        'visible': bool(native.Visible),
                        'constructorAdjustment': list(main._window_constructor_adjustment),
                        'geometryApplied': bool(getattr(window, '_ppx_startup_geometry_applied', False)),
                        'minimumWidth': int(native.MinimumSize.Width),
                        'minimumHeight': int(native.MinimumSize.Height),
                    },
                }
                expected = report['expectedPhysical']
                observed = report['observed']
                report['checks'] = {
                    'shown_at_planned_size': all(
                        abs(observed[key] - expected[key]) <= 2
                        for key in ('width', 'height', 'x', 'y')
                    ),
                    'visible_after_page_load': observed['visible'],
                    'no_constructor_compensation_needed': observed['constructorAdjustment'] == [0, 0],
                    'startup_geometry_applied': observed['geometryApplied'],
                    'minimum_size_uses_physical_units': (
                        observed['minimumWidth'] == round(window.min_size[0] * scale)
                        and observed['minimumHeight'] == round(window.min_size[1] * scale)
                    ),
                }
                output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            finally:
                window.destroy()

        def schedule_check(*_):
            # Let the production loaded handler reveal the already-sized Form.
            timer = threading.Timer(0.35, check_after_visible)
            timer.daemon = True
            timer.start()

        window.events.loaded += schedule_check
        return window

    main.webview.create_window = create
    main.WebViewApp(ifDev=True)


def _run_round(profile, name):
    output = profile / f'{name}.json'
    subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), '--child', str(profile), str(output)],
        cwd=ROOT,
        check=True,
        timeout=60,
    )
    return json.loads(output.read_text(encoding='utf-8'))


def _state_path(profile):
    return profile / 'ppx.jdassd.tools' / 'window-state.json'


def _run_scenario(profile, name, seed=None, rounds=3):
    if seed is not None:
        path = _state_path(profile)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(seed), encoding='utf-8')
    observations = [_run_round(profile, f'{name}-{index}') for index in range(rounds)]
    final_state = json.loads(_state_path(profile).read_text(encoding='utf-8'))
    stable = all(
        all(abs(item['observed'][key] - observations[0]['observed'][key]) <= 2
            for key in ('width', 'height', 'x', 'y'))
        for item in observations[1:]
    )
    checks = {
        f'{name}_startup_geometry': all(all(item['checks'].values()) for item in observations),
        f'{name}_close_reopen_stable': stable,
        f'{name}_saved_schema_is_current': final_state.get('schemaVersion') == 4,
    }
    return {
        'rounds': observations,
        'finalState': final_state,
        'checks': checks,
    }


def run():
    if sys.platform != 'win32':
        raise RuntimeError('This probe requires a Windows desktop')
    if '--child' in sys.argv:
        child(Path(sys.argv[2]), Path(sys.argv[3]))
        return

    scale = max(1.0, float(ctypes.windll.shcore.GetScaleFactorForDevice(0)) / 100.0)
    physical = {'width': 2508, 'height': 1390, 'x': 160, 'y': 86}
    logical = {key: round(value / scale) for key, value in physical.items()}
    scenarios = {}
    with tempfile.TemporaryDirectory(prefix='ppx-restore-probe-', ignore_cleanup_errors=True) as temporary:
        root = Path(temporary)
        cases = [
            ('freshDefault', None),
            ('legacySchema1', {'schemaVersion': 1, **physical}),
            ('legacySchema2', {'schemaVersion': 2, **logical}),
            # v2.17.2 schema 3 stored the intended constructor size after
            # adding the 26x71 logical-unit correction, not the shown size.
            ('legacySchema3', {'schemaVersion': 3, 'width': 1280, 'height': 766, 'x': 80, 'y': 43}),
        ]
        for name, seed in cases:
            profile = root / name
            profile.mkdir()
            scenarios[name] = _run_scenario(profile, name, seed=seed)
            if name.startswith('legacy'):
                observed = scenarios[name]['rounds'][0]['observed']
                scenarios[name]['checks'][f'{name}_preserves_previous_displayed_bounds'] = all(
                    abs(observed[key] - physical[key]) <= 2
                    for key in ('width', 'height', 'x', 'y')
                )

    all_checks = {
        check: result
        for scenario in scenarios.values()
        for check, result in scenario['checks'].items()
    }
    report = {
        'scaleFactor': scale,
        'legacySchema1Seed': {'schemaVersion': 1, **physical},
        'legacyLogicalSeed': logical,
        'scenarios': scenarios,
        'checks': all_checks,
        'passed': all(all_checks.values()),
    }
    target = ROOT / 'build/verification/windows-restore.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report['passed']:
        raise RuntimeError('Native window startup, migration, or close/reopen geometry failed')


if __name__ == '__main__':
    run()

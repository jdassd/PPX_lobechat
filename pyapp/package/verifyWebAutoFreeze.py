"""Build and run a small frozen probe through the real WebAutoTool picker."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path


def _tail(path: Path, limit: int = 50) -> list[str]:
    if not path.is_file():
        return []
    return path.read_text(encoding='utf-8', errors='replace').splitlines()[-limit:]


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    report_dir = root / 'build' / 'verification'
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / 'webauto-default-freeze.json'
    build_log_path = report_dir / 'webauto-default-freeze-build.log'
    run_log_path = report_dir / 'webauto-default-freeze-run.log'
    report = {
        'passed': False,
        'platform': sys.platform,
        'python': sys.version.split()[0],
        'startedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'parentPlaywrightBrowsersPathAbsent': 'PLAYWRIGHT_BROWSERS_PATH' not in os.environ,
        'buildLog': str(build_log_path.relative_to(root)).replace('\\', '/'),
        'runLog': str(run_log_path.relative_to(root)).replace('\\', '/'),
    }
    if not report['parentPlaywrightBrowsersPathAbsent']:
        report['error'] = 'Unset PLAYWRIGHT_BROWSERS_PATH before running this default-cache freeze verifier.'
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        return 1

    try:
        import tempfile

        with tempfile.TemporaryDirectory(prefix='ppx-webauto-default-freeze-') as temporary:
            work = Path(temporary)
            dist, build, spec = work / 'dist', work / 'build', work / 'spec'
            command = [
                sys.executable, '-m', 'PyInstaller', '--clean', '--noconfirm', '--onedir',
                '--name', 'webauto_default_freeze_probe', '--distpath', str(dist),
                '--workpath', str(build), '--specpath', str(spec),
                str(Path(__file__).with_name('webautoDefaultFreezeProbe.py')),
            ]
            report['buildCommand'] = [Path(sys.executable).name, '-m', 'PyInstaller', '--onedir',
                                      'webautoDefaultFreezeProbe.py']
            with build_log_path.open('w', encoding='utf-8') as log:
                subprocess.run(command, cwd=root, stdout=log, stderr=subprocess.STDOUT,
                               check=True, timeout=600)

            executable = dist / 'webauto_default_freeze_probe' / (
                'webauto_default_freeze_probe.exe' if os.name == 'nt' else 'webauto_default_freeze_probe'
            )
            run_env = os.environ.copy()
            run_env.pop('PLAYWRIGHT_BROWSERS_PATH', None)
            probe_report = report_dir / 'webauto-default-freeze-probe.json'
            with run_log_path.open('w', encoding='utf-8') as log:
                subprocess.run([str(executable), str(probe_report)], cwd=work, env=run_env,
                               stdout=log, stderr=subprocess.STDOUT, check=True, timeout=180)
            probe_result = json.loads(probe_report.read_text(encoding='utf-8'))
            if not probe_result.get('passed'):
                raise RuntimeError(f'Frozen product picker probe failed: {probe_result}')
            if not probe_result.get('frozen'):
                raise RuntimeError('The browser probe did not execute as a frozen program.')
            if not probe_result.get('playwrightBrowsersPathAbsent'):
                raise RuntimeError('Frozen child process inherited PLAYWRIGHT_BROWSERS_PATH.')
            report.update(passed=True, childReport=str(probe_report.relative_to(root)).replace('\\', '/'),
                          browser=probe_result.get('browser'), initialStatus=probe_result.get('initialStatus'),
                          checks=['one-dir frozen Playwright driver starts under no cache override',
                                  'real WebAutoTool.webauto_pick_start opens local fixture',
                                  'injected picker toolbar and fixture DOM report readiness',
                                  'product launch executable matches the default Chromium cache',
                                  'picker session cancels and joins cleanly'])
    except Exception as exc:
        report['error'] = f'{type(exc).__name__}: {exc}'
        report['buildLogTail'] = _tail(build_log_path)
        report['runLogTail'] = _tail(run_log_path)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        # Reports can contain Chinese API messages; keep console output safe
        # for Windows CI consoles using legacy encodings such as cp1252.
        print(json.dumps(report, ensure_ascii=True, indent=2))
        return 1

    report['finishedAt'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

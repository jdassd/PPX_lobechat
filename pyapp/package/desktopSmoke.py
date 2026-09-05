"""Opt-in native desktop smoke check, using only an isolated temporary profile."""
from __future__ import annotations

import json
import platform
import sys
import tempfile
import time
from pathlib import Path


def main():
    import webview
    from PIL import Image

    from api.api import API
    from pyapp.config.config import Config
    from pyapp.db.db import DB

    index = sys.argv.index('--desktop-smoke')
    target = Path(sys.argv[index + 1]).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    report = {'passed': False, 'platform': platform.system(), 'python': platform.python_version(),
              'frozen': bool(getattr(sys, 'frozen', False))}
    with tempfile.TemporaryDirectory(prefix='ppx-desktop-check-', ignore_cleanup_errors=True) as temporary:
        root = Path(temporary)
        Config.appDataDir = str(root / 'data')
        Config.downloadDir = str(root / 'outputs')
        Path(Config.appDataDir).mkdir()
        Config.devEnv = False
        DB().init()
        source = root / 'source.png'
        Image.new('RGBA', (64, 48), (40, 80, 120, 90)).save(source)
        api = API()
        resource = Path(Config.codeDir) / ('web/index.html' if getattr(sys, 'frozen', False) else 'gui/dist/index.html')
        if not resource.is_file():
            raise FileNotFoundError(f'Build the frontend before desktop verification: {resource}')
        window = webview.create_window('PPX desktop verification', str(resource), js_api=api,
                                       hidden=True, width=1200, height=800)
        api.setWindow(window)

        def check_bridge():
            try:
                deadline = time.monotonic() + 120
                while time.monotonic() < deadline:
                    try:
                        ready = window.evaluate_js('Boolean(window.pywebview && window.pywebview.api && document.querySelector("nav"))')
                        if ready:
                            break
                    except Exception:
                        pass
                    time.sleep(0.2)
                else:
                    raise TimeoutError('Desktop frontend or Pywebview bridge did not initialize')
                options = json.dumps({'method': 'image_batch_compress', 'args': [{'files': [str(source)], 'outputDir': Config.downloadDir}]})
                window.evaluate_js('''
                    window.__ppxSmoke = {done: false};
                    (async () => {
                      try {
                        const catalog = await window.pywebview.api.operations_list();
                        const submission = await window.pywebview.api.task_submit(''' + options + ''');
                        if (submission.code !== 0) throw new Error(submission.msg);
                        let task;
                        for (let attempt = 0; attempt < 500; attempt++) {
                          task = (await window.pywebview.api.task_get(submission.taskId)).task;
                          if (!['queued', 'running', 'canceling'].includes(task.status)) break;
                          await new Promise(resolve => setTimeout(resolve, 200));
                        }
                        window.__ppxSmoke = {done: true, task, operations: catalog.operations.length,
                          text: document.body.innerText.slice(0, 2000)};
                      } catch (error) { window.__ppxSmoke = {done: true, error: String(error)}; }
                    })();
                ''')
                while time.monotonic() < deadline:
                    state = window.evaluate_js('window.__ppxSmoke')
                    if state and state.get('done'):
                        break
                    time.sleep(0.2)
                else:
                    raise TimeoutError('Desktop processing did not finish')
                if state.get('error'):
                    raise RuntimeError(state['error'])
                task = state['task']
                if task['status'] != 'success':
                    raise RuntimeError(json.dumps(task, ensure_ascii=False))
                with Image.open(task['outputs'][0]['path']) as result:
                    if result.size != (64, 48) or result.mode != 'RGBA':
                        raise ValueError('Native worker changed image geometry or transparency')
                report.update(passed=True, operations=state['operations'], checks=[
                    'bundled frontend loads', 'native Pywebview bridge', 'operation catalog resource',
                    'isolated processing child', 'SQLite task persistence', 'output dimensions and alpha'])
            except Exception as exc:
                report['error'] = str(exc)
            finally:
                api.task_shutdown()
                api.workflow_stop()
                target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
                window.destroy()

        webview.start(check_bridge, private_mode=True, storage_path=str(root / 'webview'),
                      http_server=True, gui='edgechromium' if sys.platform == 'win32' else None)
    return 0 if report['passed'] else 1

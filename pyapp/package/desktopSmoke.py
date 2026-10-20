"""Opt-in native desktop smoke check, using only an isolated temporary profile."""
from __future__ import annotations

import json
import os
import platform
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def main():
    import webview
    from PIL import Image, ImageDraw, ImageFont

    from api.api import API
    from api.webauto import (
        WebAutoTool,
        _wa_install_command,
        _wa_install_creation_options,
        _wa_install_environment,
    )
    from pyapp.config.config import Config
    from pyapp.db.db import DB
    from pyapp.package.webautoDefaultSmoke import run_default_browser_smoke

    index = sys.argv.index('--desktop-smoke')
    target = Path(sys.argv[index + 1]).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    report = {'passed': False, 'platform': platform.system(), 'python': platform.python_version(),
              'frozen': bool(getattr(sys, 'frozen', False))}
    install_browser = os.environ.get('PPX_DESKTOP_SMOKE_INSTALL_BROWSER') == '1'
    default_browser = os.environ.get('PPX_DESKTOP_SMOKE_DEFAULT_BROWSER') == '1'
    if install_browser and default_browser:
        report['error'] = 'The custom-cache and default-cache browser smoke modes are mutually exclusive.'
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        return 1
    browser_cache = None
    default_root = None
    if default_browser:
        root_value = os.environ.get('PPX_SMOKE_DEFAULT_ROOT', '').strip()
        if not root_value or not Path(root_value).is_absolute():
            report['error'] = 'Default-cache browser smoke requires an absolute PPX_SMOKE_DEFAULT_ROOT.'
            target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            return 1
        if 'PLAYWRIGHT_BROWSERS_PATH' in os.environ:
            report['error'] = 'PLAYWRIGHT_BROWSERS_PATH must be completely absent for default-cache browser smoke.'
            target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            return 1
        default_root = Path(root_value).resolve()
        local_app_data = (default_root / 'LocalAppData').resolve()
        roaming_app_data = (default_root / 'AppData').resolve()
        local_app_data.mkdir(parents=True, exist_ok=True)
        roaming_app_data.mkdir(parents=True, exist_ok=True)
        os.environ['LOCALAPPDATA'] = str(local_app_data)
        os.environ['APPDATA'] = str(roaming_app_data)
        os.environ['PPX_SMOKE_DEFAULT_ROOT'] = str(default_root)
        report['defaultBrowserEnvironment'] = {
            'root': str(default_root),
            'localAppData': str(local_app_data),
            'appData': str(roaming_app_data),
            'playwrightBrowsersPathAbsent': 'PLAYWRIGHT_BROWSERS_PATH' not in os.environ,
            'defaultCache': str(local_app_data / 'ms-playwright'),
        }
    if install_browser:
        cache_value = os.environ.get('PLAYWRIGHT_BROWSERS_PATH', '').strip()
        if not cache_value:
            report['error'] = 'Opt-in browser install requires an isolated PLAYWRIGHT_BROWSERS_PATH.'
            target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            return 1
        browser_cache = Path(cache_value)
        if not browser_cache.is_absolute():
            report['error'] = 'PLAYWRIGHT_BROWSERS_PATH must be an absolute path.'
            target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            return 1
        browser_cache = browser_cache.resolve()
        if not browser_cache.is_dir() or any(browser_cache.iterdir()):
            report['error'] = 'PLAYWRIGHT_BROWSERS_PATH must already exist and be empty.'
            target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            return 1
    with tempfile.TemporaryDirectory(prefix='ppx-desktop-check-', ignore_cleanup_errors=True) as temporary:
        root = Path(temporary)
        import fitz
        from PyPDF2 import PdfReader

        encrypted_pdf = root / 'aes-provider-check.pdf'
        with fitz.open() as source_document:
            for text in ('PDF smoke page one', 'PDF smoke page two', 'PDF smoke page three'):
                source_document.new_page().insert_text((72, 72), text)
            source_document.save(
                str(encrypted_pdf),
                encryption=fitz.PDF_ENCRYPT_AES_256,
                user_pw='ppx-smoke-password',
                owner_pw='ppx-smoke-owner',
            )
        try:
            reader = PdfReader(str(encrypted_pdf))
            decrypt_result = reader.decrypt('ppx-smoke-password')
            reader_page_texts = [page.extract_text().strip() for page in reader.pages]
            expected_page_texts = ['PDF smoke page one', 'PDF smoke page two', 'PDF smoke page three']
            if decrypt_result == 0 or reader_page_texts != expected_page_texts:
                raise RuntimeError(f'decrypt={decrypt_result!r}, pages={reader_page_texts!r}')
        except Exception as exc:
            report['error'] = f'Bundled PyPDF2 AES provider check failed: {exc}'
            target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            return 1

        # Confirm the same bundled Node driver used by the install worker can resolve
        # the matching Chromium packages without downloading the browser archives.
        try:
            install_command = _wa_install_command()
            dry_run_command = install_command[:-1] + ['--dry-run', 'chromium']
            dry_run = subprocess.run(
                dry_run_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=45,
                env=_wa_install_environment(),
                **_wa_install_creation_options(),
            )
            dry_run_output = dry_run.stdout or ''
            if dry_run.returncode != 0 or 'chromium' not in dry_run_output.lower() or 'install location' not in dry_run_output.lower():
                raise RuntimeError(f'Playwright CLI dry-run exit={dry_run.returncode}: {dry_run_output[-2000:]}')
            report['playwrightInstallDryRun'] = {
                'passed': True,
                'command': [Path(dry_run_command[0]).name, *dry_run_command[1:]],
                'downloadedBrowser': False,
            }
        except Exception as exc:
            report['error'] = f'Bundled Playwright Node CLI install dry-run failed: {exc}'
            target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            return 1

        Config.appDataDir = str(root / 'data')
        Config.downloadDir = str(root / 'outputs')
        Path(Config.appDataDir).mkdir()
        Config.devEnv = False
        DB().init()
        source = root / 'source.png'
        Image.new('RGBA', (64, 48), (40, 80, 120, 90)).save(source)
        caj_source = root / 'embedded-pdf.caj'
        with fitz.open() as caj_document:
            caj_document.new_page().insert_text((72, 72), 'CAJ frozen smoke page')
            caj_payload = caj_document.tobytes()
        caj_header = bytearray(0x100)
        caj_header[:4] = b'CAJ\0'
        struct.pack_into('<i', caj_header, 0x10, 1)
        struct.pack_into('<i', caj_header, 0x14, 0x80)
        struct.pack_into('<i', caj_header, 0x80, 0x100)
        caj_source.write_bytes(bytes(caj_header) + caj_payload)
        ocr_source = root / 'ocr-source.png'
        ocr_image = Image.new('RGB', (1600, 360), 'white')
        ImageDraw.Draw(ocr_image).text((70, 90), 'PPX OCR TEST 12345', font=ImageFont.load_default(size=80), fill='black')
        ocr_image.save(ocr_source)
        api = API()
        if install_browser:
            installer_thread = None
            browser = None
            install_status = None
            initial_installed = False
            try:
                # The cache path is supplied by the caller and checked empty above. Keep
                # the process environment and Playwright's installer on that same cache.
                os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(browser_cache)
                initial_status = api.webauto_status()
                if initial_status.get('code') != 0:
                    raise RuntimeError(f'Initial browser status failed: {initial_status.get("msg", "unknown error")}')
                initial_installed = bool(initial_status.get('installed'))
                if initial_installed:
                    raise RuntimeError('Isolated browser cache was unexpectedly reported as installed.')
                start_result = api.webauto_install_browser()
                if start_result.get('code') != 0:
                    raise RuntimeError(f'Browser install could not start: {start_result.get("msg", "unknown error")}')
                installer_thread = getattr(api._services[WebAutoTool], '_wa_install_thread', None)
                install_deadline = time.monotonic() + 900
                while time.monotonic() < install_deadline:
                    install_status = api.webauto_install_status()
                    if install_status.get('code') != 0:
                        raise RuntimeError(f'Browser install status failed: {install_status.get("msg", "unknown error")}')
                    if install_status.get('done'):
                        break
                    time.sleep(0.5)
                else:
                    raise TimeoutError('Isolated first browser install exceeded 15 minutes.')
                if not install_status.get('success'):
                    raise RuntimeError(f'Browser install failed: {install_status.get("error") or "unknown error"}')
                final_status = api.webauto_status()
                if final_status.get('code') != 0 or not final_status.get('installed'):
                    raise RuntimeError(f'Installed browser was not reported ready: {final_status.get("msg", "unknown error")}')

                webauto_service = api._services[WebAutoTool]
                executables = [
                    candidate
                    for directory_name in webauto_service._wa_expected_chromium_dirs()
                    for candidate in webauto_service._wa_chromium_executable_candidates(browser_cache / directory_name)
                    if candidate.is_file()
                ]
                if not executables:
                    raise FileNotFoundError('The installed Chromium executable was not found in the isolated cache.')
                executable = executables[0].resolve()
                page_file = browser_cache.parent / 'ppx-frozen-browser-smoke.html'
                page_file.write_text('<!doctype html><title>PPX Chromium smoke</title><main id="result">local browser ready</main>', encoding='utf-8')
                from playwright.sync_api import sync_playwright

                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.goto(page_file.as_uri(), wait_until='load', timeout=30000)
                    local_text = page.locator('#result').inner_text()
                    browser_version = browser.version
                    if local_text != 'local browser ready':
                        raise ValueError(f'Installed Chromium could not read the local smoke page: {local_text!r}')
                browser = None
                report['firstBrowserInstall'] = {
                    'initialInstalled': initial_installed,
                    'done': bool(install_status.get('done')),
                    'success': bool(install_status.get('success')),
                    'installed': bool(final_status.get('installed')),
                    'currentExecutable': str(executable),
                    'browserVersion': browser_version,
                    'downloadedBrowser': True,
                    'localPageText': local_text,
                    'cachePathIsolated': True,
                }
            except Exception as exc:
                report['firstBrowserInstall'] = {
                    'initialInstalled': initial_installed,
                    'done': bool(install_status.get('done')) if install_status else False,
                    'success': bool(install_status.get('success')) if install_status else False,
                    'installed': False,
                    'downloadedBrowser': False,
                }
                report['error'] = f'Frozen first browser install smoke failed: {exc}'
                target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
                return 1
            finally:
                if browser is not None:
                    browser.close()
                if installer_thread is not None and installer_thread.is_alive():
                    installer_thread.join(timeout=5)
                os.environ.pop('PLAYWRIGHT_BROWSERS_PATH', None)
        if default_browser:
            installer_thread = None
            install_status = None
            initial_installed = None
            webauto_service = None
            try:
                if 'PLAYWRIGHT_BROWSERS_PATH' in os.environ:
                    raise RuntimeError('PLAYWRIGHT_BROWSERS_PATH appeared before default-cache install.')
                initial_status = api.webauto_status()
                if initial_status.get('code') != 0:
                    raise RuntimeError(f'Initial browser status failed: {initial_status.get("msg", "unknown error")}')
                initial_installed = bool(initial_status.get('installed'))
                if initial_installed:
                    raise RuntimeError('Isolated default Chromium cache was unexpectedly reported as installed.')
                start_result = api.webauto_install_browser()
                if start_result.get('code') != 0:
                    raise RuntimeError(f'Browser install could not start: {start_result.get("msg", "unknown error")}')
                installer_thread = getattr(api._services[WebAutoTool], '_wa_install_thread', None)
                install_deadline = time.monotonic() + 900
                while time.monotonic() < install_deadline:
                    install_status = api.webauto_install_status()
                    if install_status.get('code') != 0:
                        raise RuntimeError(f'Browser install status failed: {install_status.get("msg", "unknown error")}')
                    if install_status.get('done'):
                        break
                    time.sleep(0.5)
                else:
                    raise TimeoutError('Default-cache first browser install exceeded 15 minutes.')
                if not install_status.get('success'):
                    raise RuntimeError(f'Browser install failed: {install_status.get("error") or "unknown error"}')
                final_status = api.webauto_status()
                if final_status.get('code') != 0 or not final_status.get('installed'):
                    raise RuntimeError(f'Installed browser was not reported ready: {final_status.get("msg", "unknown error")}')
                webauto_service = api._services[WebAutoTool]
                if webauto_service._wa_browsers_dir().resolve() != (local_app_data / 'ms-playwright').resolve():
                    raise AssertionError('WebAutoTool did not resolve Chromium to LOCALAPPDATA/ms-playwright.')
                browser_result = run_default_browser_smoke(webauto_service)
                report['defaultCacheBrowser'] = {
                    'initialInstalled': initial_installed,
                    'downloaded': True,
                    'installed': bool(final_status.get('installed')),
                    'cachePath': str(webauto_service._wa_browsers_dir().resolve()),
                    'publicApiStart': True,
                    **browser_result,
                }
            except Exception as exc:
                report['defaultCacheBrowser'] = {
                    'initialInstalled': initial_installed,
                    'downloaded': bool(install_status and install_status.get('success')),
                    'publicApiStart': False,
                    'playwrightBrowsersPathAbsent': 'PLAYWRIGHT_BROWSERS_PATH' not in os.environ,
                    'apiState': webauto_service.webauto_pick_state() if webauto_service is not None else None,
                    'installState': install_status,
                }
                report['error'] = f'Frozen default-cache browser smoke failed: {type(exc).__name__}: {exc}'
                target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
                return 1
            finally:
                if installer_thread is not None and installer_thread.is_alive():
                    installer_thread.join(timeout=5)
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
                image_options = json.dumps({
                    'method': 'image_batch_compress',
                    'args': [{'files': [str(source)], 'outputDir': Config.downloadDir}],
                })
                pdf_options = json.dumps({
                    'method': 'pdf_cut',
                    'args': [{
                        'filePath': str(encrypted_pdf),
                        'mode': 'custom',
                        'pageSpec': '3,1',
                        'password': 'ppx-smoke-password',
                        'outputPath': str(root / 'outputs' / 'pdf-cut.pdf'),
                    }],
                })
                ocr_options = json.dumps({
                    'method': 'ocr_image',
                    'args': [{'filePath': str(ocr_source), 'outputDir': Config.downloadDir}],
                })
                caj_options = json.dumps({
                    'method': 'pdf_caj_to_pdf',
                    'args': [{'files': [str(caj_source)], 'outputDir': Config.downloadDir}],
                })
                window.evaluate_js('''
                    window.__ppxSmoke = {done: false};
                    (async () => {
                      try {
                        const catalog = await window.pywebview.api.operations_list();
                        async function submitAndWait(options) {
                          const submission = await window.pywebview.api.task_submit(options);
                          if (submission.code !== 0) throw new Error(submission.msg);
                          let task;
                          for (let attempt = 0; attempt < 600; attempt++) {
                            task = (await window.pywebview.api.task_get(submission.taskId)).task;
                            if (!['queued', 'running', 'canceling'].includes(task.status)) return task;
                            await new Promise(resolve => setTimeout(resolve, 200));
                          }
                          throw new Error('Timed out waiting for ' + options.method);
                        }
                        const imageTask = await submitAndWait(''' + image_options + ''');
                        const pdfTask = await submitAndWait(''' + pdf_options + ''');
                        const cajTask = await submitAndWait(''' + caj_options + ''');
                        const ocrTask = await submitAndWait(''' + ocr_options + ''');
                        window.__ppxSmoke = {done: true, imageTask, pdfTask, cajTask, ocrTask,
                          operations: catalog.operations.length, text: document.body.innerText.slice(0, 2000)};
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
                image_task = state['imageTask']
                if image_task['status'] != 'success':
                    raise RuntimeError(json.dumps(image_task, ensure_ascii=False))
                with Image.open(image_task['outputs'][0]['path']) as result:
                    if result.size != (64, 48) or result.mode != 'RGBA':
                        raise ValueError('Native worker changed image geometry or transparency')
                pdf_task = state['pdfTask']
                if pdf_task['status'] != 'success':
                    raise RuntimeError(json.dumps(pdf_task, ensure_ascii=False))
                pdf_output = Path(pdf_task['outputs'][0]['path'])
                with fitz.open(pdf_output) as result:
                    page_texts = [page.get_text().strip() for page in result]
                if page_texts != ['PDF smoke page three', 'PDF smoke page one']:
                    raise ValueError(f'Native pdf_cut output page order/content mismatch: {page_texts!r}')
                caj_task = state['cajTask']
                if caj_task['status'] != 'success':
                    raise RuntimeError(json.dumps(caj_task, ensure_ascii=False))
                with fitz.open(caj_task['outputs'][0]['path']) as result:
                    caj_text = result[0].get_text().strip()
                if caj_text != 'CAJ frozen smoke page':
                    raise ValueError(f'Bundled CAJ conversion content mismatch: {caj_text!r}')
                ocr_task = state['ocrTask']
                if ocr_task['status'] != 'success':
                    raise RuntimeError(json.dumps(ocr_task, ensure_ascii=False))
                ocr_text = Path(ocr_task['outputs'][0]['path']).read_text(encoding='utf-8')
                if 'OCR' not in ocr_text or '12345' not in ocr_text:
                    raise ValueError(f'Bundled OCR result mismatch: {ocr_text!r}')
                report.update(passed=True, operations=state['operations'], checks=[
                    'bundled frontend loads', 'native Pywebview bridge', 'operation catalog resource',
                    'bundled PyPDF2 AES provider', 'bundled Playwright Node CLI install dry-run (no browser download)',
                    'isolated image processing child', 'SQLite task persistence',
                    'AES-256 pdf_cut task through isolated worker', 'output page order and text',
                    'CAJ container conversion through isolated worker and reopened PDF text',
                    'bundled RapidOCR/ONNX models through isolated worker',
                    'image output dimensions and alpha'])
                if install_browser:
                    report['checks'].append('isolated actual first Chromium download and local-page launch')
                if default_browser:
                    report['checks'].append('isolated default-cache Chromium download and real WebAutoTool picker toolbar')
                report['pdfCut'] = {'status': pdf_task['status'], 'pages': page_texts}
                report['cajPdf'] = {'status': caj_task['status'], 'text': caj_text}
                report['ocr'] = {'status': ocr_task['status'], 'text': ocr_text}
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

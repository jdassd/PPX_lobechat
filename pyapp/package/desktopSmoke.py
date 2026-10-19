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
    from PIL import Image, ImageDraw, ImageFont

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

        Config.appDataDir = str(root / 'data')
        Config.downloadDir = str(root / 'outputs')
        Path(Config.appDataDir).mkdir()
        Config.devEnv = False
        DB().init()
        source = root / 'source.png'
        Image.new('RGBA', (64, 48), (40, 80, 120, 90)).save(source)
        ocr_source = root / 'ocr-source.png'
        ocr_image = Image.new('RGB', (1600, 360), 'white')
        ImageDraw.Draw(ocr_image).text((70, 90), 'PPX OCR TEST 12345', font=ImageFont.load_default(size=80), fill='black')
        ocr_image.save(ocr_source)
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
                        const ocrTask = await submitAndWait(''' + ocr_options + ''');
                        window.__ppxSmoke = {done: true, imageTask, pdfTask, ocrTask,
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
                ocr_task = state['ocrTask']
                if ocr_task['status'] != 'success':
                    raise RuntimeError(json.dumps(ocr_task, ensure_ascii=False))
                ocr_text = Path(ocr_task['outputs'][0]['path']).read_text(encoding='utf-8')
                if 'OCR' not in ocr_text or '12345' not in ocr_text:
                    raise ValueError(f'Bundled OCR result mismatch: {ocr_text!r}')
                report.update(passed=True, operations=state['operations'], checks=[
                    'bundled frontend loads', 'native Pywebview bridge', 'operation catalog resource',
                    'bundled PyPDF2 AES provider', 'isolated image processing child', 'SQLite task persistence',
                    'AES-256 pdf_cut task through isolated worker', 'output page order and text',
                    'bundled RapidOCR/ONNX models through isolated worker',
                    'image output dimensions and alpha'])
                report['pdfCut'] = {'status': pdf_task['status'], 'pages': page_texts}
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

"""Optional native OCR integration check; writes only isolated fixtures and a report."""
from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw, ImageFont

from api.api import API
from pyapp.config.config import Config


def main():
    with tempfile.TemporaryDirectory(prefix='ppx-ocr-smoke-') as temporary:
        root = Path(temporary)
        Config.appDataDir = str(root / 'data')
        Config.downloadDir = str(root / 'outputs')
        root.joinpath('data').mkdir()
        source = root / 'text.png'
        image = Image.new('RGB', (1200, 220), 'white')
        ImageDraw.Draw(image).text((40, 60), 'PPX DOCUMENT 12345', font=ImageFont.load_default(size=64), fill='black')
        image.rotate(90, expand=True).save(source)
        api = API()
        try:
            queued = api.task_submit({'method': 'ocr_image', 'args': [{'filePath': str(source), 'autoRotate': True, 'outputDir': str(root / 'outputs')}]})
            assert queued['code'] == 0, queued
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                task = api.task_get(queued['taskId'])['task']
                if task['status'] not in ('queued', 'running', 'canceling'):
                    break
                time.sleep(.2)
            assert task['status'] == 'success', task
            result = task['result']
            assert '12345' in result['text'], result
            assert result['rotation'] in (90, 270), result
            assert Path(result['output']).read_text(encoding='utf-8') == result['text'], result
            report = {'passed': True, 'recognised': result['text'], 'rotation': result['rotation'], 'averageConfidence': result['averageConfidence'], 'engine': 'RapidOCR native, isolated worker, Python 3.10'}
            report_path = ROOT / 'build/verification/ocr-native.json'
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
            print(json.dumps(report))
        finally:
            api.task_shutdown()
            api.workflow_stop()


if __name__ == '__main__':
    main()

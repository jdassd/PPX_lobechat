import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from PIL import Image

from api.capabilities import CapabilitiesMixin
from api.file import FileTool
from api.ocr import OcrMixin
from api.system import System
from api.system.startup import StartupMixin


class CapabilityTests(unittest.TestCase):
    def test_reports_optional_dependencies_independently(self):
        def available(name):
            return name in {'rapidocr', 'onnxruntime', 'playwright'}

        with (
            mock.patch.object(CapabilitiesMixin, '_module_available', side_effect=available),
            mock.patch.object(CapabilitiesMixin, '_find_libreoffice', return_value=''),
            mock.patch('api.capabilities.shutil.which', return_value=None),
        ):
            result = CapabilitiesMixin().capabilities_get()

        self.assertEqual(result['code'], 0)
        self.assertTrue(result['capabilities']['ocr']['available'])
        self.assertFalse(result['capabilities']['ffmpeg']['available'])
        self.assertFalse(result['capabilities']['libreoffice']['available'])


class OcrTests(unittest.TestCase):
    def test_image_ocr_writes_utf8_text_without_overwriting(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'scan.png'
            Image.new('RGB', (40, 20), 'white').save(source)
            expected_lines = [{'box': None, 'text': '本地 OCR', 'score': 0.96}]
            with mock.patch.object(OcrMixin, '_recognize', return_value=expected_lines):
                first = OcrMixin().ocr_image({'filePath': str(source)})
                second = OcrMixin().ocr_image({'filePath': str(source)})

            self.assertEqual(first['code'], 0)
            self.assertEqual(Path(first['output']).read_text(encoding='utf-8'), '本地 OCR')
            self.assertNotEqual(first['output'], second['output'])

    def test_pdf_ocr_respects_page_selection(self):
        try:
            import fitz
        except ImportError:
            self.skipTest('PyMuPDF is not installed')

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'scan.pdf'
            document = fitz.open()
            document.new_page()
            document.new_page()
            document.save(source)
            document.close()
            lines = [{'box': [[0, 0], [20, 0], [20, 10], [0, 10]], 'text': '第二页', 'score': 0.9}]
            with mock.patch.object(OcrMixin, '_recognize', return_value=lines):
                result = OcrMixin().ocr_pdf({'filePath': str(source), 'pageSpec': '2', 'outputMode': 'text', 'dpi': 120})

            self.assertEqual(result['code'], 0)
            self.assertEqual(result['pageCount'], 1)
            self.assertIn('第二页', Path(result['textOutput']).read_text(encoding='utf-8'))


class SafetyTests(unittest.TestCase):
    def test_delete_is_recoverable_even_if_permanent_is_requested(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'remove.log'
            source.write_text('recover me', encoding='utf-8')
            result = FileTool().file_batch_delete({
                'directory': str(root),
                'extensions': ['log'],
                'deletePolicy': 'permanent',
                'dryRun': False,
            })

            self.assertEqual(result['code'], 0)
            self.assertFalse(source.exists())
            recovered = Path(result['recycleDir']) / source.name
            self.assertEqual(recovered.read_text(encoding='utf-8'), 'recover me')

    def test_arbitrary_startup_execution_is_disabled(self):
        result = StartupMixin().system_runSystemStartup({'command': 'echo unsafe'})
        self.assertNotEqual(result['code'], 0)
        self.assertIn('只读', result['msg'])

    def test_software_shred_api_is_no_longer_exposed(self):
        self.assertFalse(hasattr(System(), 'system_shredSoftwareDir'))

    def test_process_termination_api_is_no_longer_exposed(self):
        self.assertFalse(hasattr(System(), 'system_killProcess'))
        self.assertFalse(hasattr(System(), 'system_killProcesses'))

    def test_archive_extraction_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / 'unsafe.zip'
            target = root / 'output'
            escaped = root / 'escaped.txt'
            with zipfile.ZipFile(archive, 'w') as handler:
                handler.writestr('../escaped.txt', 'unsafe')

            result = FileTool().file_decompress({'archiveFile': str(archive), 'targetDir': str(target)})

            self.assertNotEqual(result['code'], 0)
            self.assertFalse(escaped.exists())

    def test_rename_never_overwrites_an_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'draft.txt'
            target = root / 'final.txt'
            source.write_text('source', encoding='utf-8')
            target.write_text('keep target', encoding='utf-8')
            result = FileTool().file_batch_rename({
                'directory': str(root),
                'keyword': 'draft',
                'rule': 'replace',
                'ruleParams': {'search': 'draft', 'replace': 'final'},
                'conflictPolicy': 'overwrite',
                'dryRun': False,
            })

            self.assertEqual(result['code'], 0)
            self.assertEqual(source.read_text(encoding='utf-8'), 'source')
            self.assertEqual(target.read_text(encoding='utf-8'), 'keep target')
            self.assertEqual(result['skipped'], [str(source)])


if __name__ == '__main__':
    unittest.main()

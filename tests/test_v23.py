import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import fitz
from PIL import Image

from api.document_index import DocumentIndexMixin
from api.file import FileTool
from api.maintenance import MaintenanceMixin
from api.ocr import OcrMixin
from api.pdf import PDF
from api.tasks import TaskMixin
from api.utils.error_handler import api_error, api_success
from api.workflow import WorkflowMixin
from pyapp.config.config import Config


class DummyTaskApi(TaskMixin):
    def text_case_transform(self, options=None):
        options = options or {}
        if options.get('fail'):
            return api_error('planned failure')
        return api_success('done', output=str(options.get('value') or '').upper())


class DummyWorkflowApi(WorkflowMixin):
    def text_case_transform(self, options=None):
        return api_success('done', output=str((options or {}).get('value') or '').upper())


class TaskQueueTests(unittest.TestCase):
    def test_persistent_queue_executes_and_records_result(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(Config, 'appDataDir', directory):
            api = DummyTaskApi()
            submitted = api.task_submit({'method': 'text_case_transform', 'args': [{'value': 'v2.3'}]})
            self.assertEqual(submitted['code'], 0)
            task_id = submitted['taskId']
            deadline = time.time() + 3
            task = None
            while time.time() < deadline:
                task = api.task_get({'id': task_id})['task']
                if task['status'] in {'success', 'failed'}:
                    break
                time.sleep(0.01)
            api.task_shutdown()

            self.assertEqual(task['status'], 'success')
            self.assertEqual(task['result']['output'], 'V2.3')
            self.assertTrue((Path(directory) / 'tasks' / 'history.json').is_file())


class WorkflowTests(unittest.TestCase):
    def test_workflow_resolves_step_outputs_and_blocks_unsafe_methods(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(Config, 'appDataDir', directory):
            api = DummyWorkflowApi()
            saved = api.workflow_save({
                'name': 'binding test',
                'steps': [
                    {'id': 'first', 'method': 'text_case_transform', 'args': {'value': '{{input.value}}'}},
                    {'id': 'second', 'method': 'text_case_transform', 'args': {'value': '{{steps.first.output}}!'}},
                ],
            })
            self.assertEqual(saved['code'], 0)
            result = api.workflow_run({'id': saved['workflow']['id'], 'input': {'value': 'hello'}})
            unsafe = api.workflow_save({'name': 'unsafe', 'steps': [{'method': 'file_batch_delete', 'args': {}}]})

            self.assertEqual(result['code'], 0)
            self.assertEqual(result['context']['steps']['second']['output'], 'HELLO!')
            self.assertNotEqual(unsafe['code'], 0)


class RecoverableFileTests(unittest.TestCase):
    def test_delete_restore_and_rename_undo_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            deleted = root / 'recover.txt'
            deleted.write_text('keep me', encoding='utf-8')
            tool = FileTool()
            removal = tool.file_batch_delete({'directory': str(root), 'extensions': ['txt'], 'dryRun': False})
            restored = tool.file_recycle_restore({'directory': str(root), 'id': removal['id']})
            self.assertEqual(restored['code'], 0)
            self.assertEqual(deleted.read_text(encoding='utf-8'), 'keep me')

            renamed = tool.file_batch_rename({
                'directory': str(root),
                'extensions': ['txt'],
                'rule': 'replace',
                'ruleParams': {'search': 'recover', 'replace': 'renamed'},
                'dryRun': False,
            })
            self.assertTrue((root / 'renamed.txt').is_file())
            undone = tool.file_batch_rename_undo({'directory': str(root), 'transactionId': renamed['transactionId']})
            self.assertEqual(undone['code'], 0)
            self.assertTrue(deleted.is_file())


class PdfWorkbenchTests(unittest.TestCase):
    @staticmethod
    def _create_pdf(path: Path):
        document = fitz.open()
        document.set_metadata({'title': 'Sensitive metadata', 'author': 'Private'})
        for index in range(1, 4):
            page = document.new_page()
            page.insert_text((72, 72), f'PAGE {index} SECRET')
        document.save(path)
        document.close()

    def test_page_reorder_and_security_redaction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.pdf'
            self._create_pdf(source)
            tool = PDF()
            preview = tool.pdf_page_preview({'filePath': str(source), 'width': 100})
            result = tool.pdf_page_workbench({
                'filePath': str(source),
                'outputDir': str(root),
                'outputName': 'reordered.pdf',
                'pageOrder': [3, 1],
                'rotations': {'3': 90},
                'addPageNumbers': True,
            })
            secure = tool.pdf_secure({
                'filePath': str(source),
                'outputDir': str(root),
                'outputName': 'secure.pdf',
                'redactText': 'SECRET',
                'watermarkText': 'CONFIDENTIAL',
                'removeMetadata': True,
            })

            self.assertEqual(preview['pageCount'], 3)
            self.assertEqual(result['code'], 0)
            with fitz.open(result['output']) as document:
                self.assertEqual(document.page_count, 2)
                self.assertIn('PAGE 3', document[0].get_text())
                self.assertEqual(document[0].rotation, 90)
            self.assertEqual(secure['code'], 0)
            with fitz.open(secure['output']) as document:
                self.assertNotIn('SECRET', ''.join(page.get_text() for page in document))
                self.assertFalse(document.metadata.get('title'))


class TableOcrTests(unittest.TestCase):
    def test_table_ocr_reconstructs_rows_and_exports_xlsx(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'table.png'
            Image.new('RGB', (400, 200), 'white').save(source)
            lines = [
                {'box': [[10, 10], [100, 10], [100, 30], [10, 30]], 'text': '姓名', 'score': 0.99},
                {'box': [[210, 10], [300, 10], [300, 30], [210, 30]], 'text': '部门', 'score': 0.99},
                {'box': [[10, 70], [100, 70], [100, 90], [10, 90]], 'text': '小王', 'score': 0.98},
                {'box': [[210, 70], [300, 70], [300, 90], [210, 90]], 'text': '研发', 'score': 0.98},
            ]
            with mock.patch.object(OcrMixin, '_recognize', return_value=lines):
                result = OcrMixin().ocr_table({'filePath': str(source), 'outputDir': str(root), 'outputFormat': 'xlsx'})
            self.assertEqual(result['code'], 0)
            self.assertEqual((result['rowCount'], result['columnCount']), (2, 2))
            self.assertTrue(Path(result['output']).is_file())


class DocumentIndexTests(unittest.TestCase):
    def test_incremental_local_index_and_search(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app_data = root / 'app-data'
            documents = root / 'documents'
            app_data.mkdir()
            documents.mkdir()
            source = documents / 'guide.txt'
            source.write_text('这是离线文档搜索的回归测试内容。', encoding='utf-8')
            with mock.patch.object(Config, 'appDataDir', str(app_data)):
                api = DocumentIndexMixin()
                built = api.document_index_build({'directories': [str(documents)]})
                searched = api.document_index_search({'query': '离线文档搜索'})
                second = api.document_index_build({'directories': [str(documents)]})
            self.assertEqual(built['code'], 0)
            self.assertEqual(searched['code'], 0)
            self.assertEqual(Path(searched['results'][0]['path']), source.resolve())
            self.assertEqual(second['skipped'], 1)


class MaintenanceTests(unittest.TestCase):
    def test_backup_validation_and_deferred_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app_data = root / 'app-data'
            backups = root / 'backups'
            app_data.mkdir()
            state = app_data / 'settings.json'
            state.write_text('{"value":"original"}', encoding='utf-8')
            with (
                mock.patch.object(Config, 'appDataDir', str(app_data)),
                mock.patch.object(Config, 'downloadDir', str(root)),
            ):
                api = MaintenanceMixin()
                created = api.maintenance_backup_create({
                    'outputDir': str(backups),
                    'frontendState': {'ppx-theme': 'dark', 'unrelated-secret': 'blocked'},
                })
                inspected = api.maintenance_backup_inspect({'filePath': created['output']})
                state.write_text('{"value":"changed"}', encoding='utf-8')
                staged = api.maintenance_backup_restore({'filePath': created['output']})
                applied = api.maintenance_apply_pending_restore()

            self.assertEqual(created['code'], 0)
            self.assertEqual(inspected['frontendState'], {'ppx-theme': 'dark'})
            self.assertTrue(staged['requiresRestart'])
            self.assertTrue(applied['restored'])
            self.assertEqual(state.read_text(encoding='utf-8'), '{"value":"original"}')


if __name__ == '__main__':
    unittest.main()

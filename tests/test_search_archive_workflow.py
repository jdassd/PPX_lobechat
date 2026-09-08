import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from api.api import API
from api.workflow import WorkflowMixin
from pyapp.config.config import Config


class SearchArchiveWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        self.output = self.source / 'delivery'
        self.patch = mock.patch.object(Config, 'appDataDir', str(self.root / 'state'))
        self.patch.start()
        self.api = API()
        self.workflow = self.api._services[WorkflowMixin]

    def tearDown(self):
        self.api.task_shutdown()
        self.api.workflow_stop()
        self.patch.stop()
        self.temp.cleanup()

    def make(self, name, text='text'):
        path = self.source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def template(self):
        return self.api.workflow_create_from_template({'templateId': 'builtin-search-archive'})['workflow']

    def inputs(self, **extra):
        return {'directory': str(self.source), 'outputDir': str(self.output), 'keyword': '',
                'extensions': ['txt'], 'recursive': True, 'limit': 50, 'archiveName': 'documents', **extra}

    def test_real_search_then_zip_preserves_scope_paths_and_does_not_ignore_sources(self):
        first, second = self.make('alpha/report.txt', 'first'), self.make('beta/report.txt', 'second')
        self.make('delivery/old.txt', 'old output')
        self.make('excluded.csv', 'not selected')
        workflow = self.template()
        options = self.inputs()
        self.assertTrue(self.api.workflow_preflight({'steps': workflow['steps'], 'input': options})['valid'])
        result = self.api.workflow_run({'id': workflow['id'], 'input': options})
        self.assertEqual(result['run']['status'], 'success', result)
        search = result['context']['steps']['search']
        self.assertTrue(search['complete'])
        self.assertEqual(search['matchedCount'], 2)
        package_path = Path(result['context']['steps']['archive']['file'])
        with zipfile.ZipFile(package_path) as package:
            self.assertEqual(set(package.namelist()), {'alpha/report.txt', 'beta/report.txt'})
            self.assertEqual(package.read('alpha/report.txt'), b'first')
            self.assertEqual(package.read('beta/report.txt'), b'second')
        self.assertNotIn(str(first.resolve()), self.workflow._workflow_generated_paths)
        self.assertNotIn(str(second.resolve()), self.workflow._workflow_generated_paths)
        self.assertIn(str(package_path.resolve()), self.workflow._workflow_generated_paths)
        again = self.api.workflow_run({'id': workflow['id'], 'input': self.inputs(extensions=[])})
        with zipfile.ZipFile(again['context']['steps']['archive']['file']) as package:
            self.assertEqual(set(package.namelist()), {'alpha/report.txt', 'beta/report.txt', 'excluded.csv'})

    def test_truncation_stops_workflow_before_archive(self):
        for index in range(51):
            self.make(f'file-{index}.txt')
        workflow = self.template()
        result = self.api.workflow_run({'id': workflow['id'], 'input': self.inputs()})
        self.assertEqual(result['run']['status'], 'partial', result)
        self.assertEqual(len(result['run']['steps']), 1)
        self.assertTrue(result['context']['steps']['search']['truncated'])
        self.assertFalse(self.output.exists())
        self.assertEqual(self.workflow._workflow_generated_paths, set())

    def test_directory_watch_still_detects_changes_to_queried_sources(self):
        source = self.make('document.txt')
        workflow = self.template()
        result = self.api.workflow_run({'id': workflow['id'], 'input': self.inputs()})
        archive = Path(result['context']['steps']['archive']['file'])
        saved = self.api.workflow_watch_save({'workflowId': workflow['id'], 'path': str(self.source),
                                               'recursive': True, 'debounceSeconds': 1})
        self.assertEqual(saved['code'], 0, saved)
        with mock.patch.object(self.workflow, '_workflow_submit') as submit:
            self.workflow._workflow_tick_watches(1000)
            source.write_text('changed source with new length', encoding='utf-8')
            archive.write_bytes(archive.read_bytes() + b'changed output')
            self.workflow._workflow_tick_watches(1001)
            self.workflow._workflow_tick_watches(1003)
        submit.assert_called_once()
        self.assertEqual(submit.call_args.args[3]['path'], str(source.resolve()))

    def test_scan_error_stops_workflow_and_explains_incomplete_scope(self):
        self.make('good.txt')
        (self.source / 'blocked').mkdir()
        original = os.scandir

        def scan(path):
            if Path(path).name == 'blocked':
                raise PermissionError('test access denied')
            return original(path)

        workflow = self.template()
        with mock.patch('api.core.file_search.os.scandir', side_effect=scan):
            result = self.api.workflow_run({'id': workflow['id'], 'input': self.inputs()})
        self.assertEqual(result['run']['status'], 'partial', result)
        self.assertEqual(len(result['run']['steps']), 1)
        self.assertEqual(result['context']['steps']['search']['errorCount'], 1)
        self.assertFalse(self.output.exists())

    def test_invalid_scope_ranges_and_missing_output_are_rejected(self):
        for options in [{'minSize': 20, 'maxSize': 10}, {'modifiedStart': 200, 'modifiedEnd': 100},
                        {'minSize': -1}, {'modifiedEnd': float('nan')}, {'excludeDirectory': str(self.source)}]:
            result = self.api.file_search({'directory': str(self.source), **options})
            self.assertNotEqual(result['code'], 0, options)
        workflow = self.template()
        checked = self.api.workflow_preflight({'steps': workflow['steps'], 'input': self.inputs(outputDir='')})
        self.assertFalse(checked['valid'])
        self.assertIn('明确选择输出目录', str(checked['errors']))

    def test_old_query_sources_are_repaired_while_real_and_unknown_outputs_remain(self):
        source = self.make('source.txt')
        rewritten = self.make('rewritten.txt')
        output = self.make('delivery/output.zip')
        unknown = str(self.root / 'old-output.zip')
        self.workflow._workflow_ensure()
        with self.workflow._workflow_lock:
            self.workflow._workflow_data['querySourceExclusionFixed'] = False
            self.workflow._workflow_data['runs'] = [{'status': 'success', 'steps': [
                {'method': 'file_search', 'result': {'outputAssets': [{'path': str(source)}, {'path': str(rewritten)}]}},
                {'method': 'file_batch_copy', 'result': {'outputAssets': [{'path': str(rewritten)}, {'path': str(output)}]}}]}]
            self.workflow._workflow_generated_paths = {str(source), str(rewritten), str(output), unknown}
            self.workflow._workflow_persist_locked()
        restored = API()
        try:
            service = restored._services[WorkflowMixin]
            service._workflow_ensure()
            self.assertEqual(service._workflow_generated_paths, {str(rewritten), str(output), unknown})
            self.assertTrue(service._workflow_data['querySourceExclusionFixed'])
        finally:
            restored.workflow_stop()
            restored.task_shutdown()


if __name__ == '__main__':
    unittest.main()

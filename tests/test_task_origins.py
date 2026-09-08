import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

from api.api import API
from api.core.input_origins import path_identity, primary_paths, validate_origins
from api.operations import OPERATIONS
from pyapp.config.config import Config


class TaskOriginTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.patch = mock.patch.object(Config, 'appDataDir', str(self.root / 'state'))
        self.patch.start()
        self.api = API()

    def tearDown(self):
        self.api.task_shutdown()
        self.api.workflow_stop()
        self.patch.stop()
        self.temporary.cleanup()

    def wait(self, identity):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            task = self.api.task_get(identity)['task']
            if task['status'] in {'success', 'partial', 'failed', 'canceled', 'interrupted'}:
                return task
            time.sleep(0.03)
        self.fail('task timed out')

    def source(self, count=1):
        files = []
        for index in range(count):
            path = self.root / f'input-{index}.png'
            Image.new('RGB', (12, 8), 'red').save(path)
            files.append(str(path))
        task = self.wait(self.api.task_submit({'method': 'image_rotate_flip', 'args': [
            {'files': files, 'operation': 'rotate90', 'outputDir': str(self.root / 'first')} ]})['taskId'])
        self.assertEqual(task['status'], 'success', task)
        return task

    @staticmethod
    def origin(source, path):
        return {'inputPath': path, 'sourceAssetPath': path, 'sourceTaskId': source['id'],
                'sourceMethod': 'forged', 'sourceCreatedAt': -1}

    def test_real_output_to_input_and_business_args_untouched(self):
        source = self.source()
        path = source['outputs'][0]['path']
        args = [{'files': [{'path': path}], 'operation': 'rotate90', 'outputDir': str(self.root / 'second')}]
        origin = self.origin(source, path)
        submitted = self.api.task_submit({'method': 'image_rotate_flip', 'args': args, 'inputOrigins': [origin, origin]})
        task = self.wait(submitted['taskId'])
        self.assertEqual(task['status'], 'success', task)
        self.assertEqual(task['args'], args)
        self.assertEqual(len(task['inputOrigins']), 1)
        verified = task['inputOrigins'][0]
        self.assertEqual(verified['sourceMethod'], source['method'])
        self.assertEqual(verified['sourceCreatedAt'], source['createdAt'])
        self.assertTrue(verified['sourceAvailable'])
        self.assertEqual(set(verified), {'inputPath', 'sourceAssetPath', 'sourceTaskId', 'sourceMethod',
                                         'sourceCreatedAt', 'validation', 'sourceAvailable'})
        self.assertTrue(Path(task['outputs'][0]['path']).is_file())

    def test_primary_intersection_and_auxiliary_exclusion(self):
        source = self.source(2)
        first, second = (asset['path'] for asset in source['outputs'])
        self.api.task_queue_pause()
        task = self.api.task_submit({'method': 'image_add_watermark', 'args': [
            {'files': [first], 'watermarkImage': second, 'fontPath': second}],
            'inputOrigins': [self.origin(source, first), self.origin(source, second)]})['task']
        self.assertEqual([item['inputPath'] for item in task['inputOrigins']], [first])
        self.assertTrue(task['inputOriginWarnings'])
        self.assertEqual(primary_paths('excel_process', [{'filePath': first, 'mergeFiles': [{'path': second}]}]),
                         {path_identity(first)})
        self.assertEqual(primary_paths('excel_merge_tables', [{'tables': [{'path': first}, {'path': second}]}]),
                         {path_identity(first), path_identity(second)})

    def test_paths_are_cross_platform_and_not_content_hashes(self):
        self.assertEqual(path_identity(r'C:\DATA\folder\..\A.PNG'), path_identity('c:/data/a.png'))
        self.assertEqual(path_identity(r'\\SERVER\Share\A.PNG'), path_identity('//server/share/a.png'))
        self.assertEqual(path_identity(str(self.root / 'a' / '..' / 'b')), path_identity(str(self.root / 'b')))
        if os.name != 'nt':
            self.assertNotEqual(path_identity('/data/A'), path_identity('/data/a'))
        self.assertIsNone(path_identity('https://example.com/a'))
        self.assertIsNone(path_identity('a\x00b'))

    def test_invalid_unknown_and_untrusted_retry_metadata(self):
        source = self.source()
        path = source['outputs'][0]['path']
        self.api.task_queue_pause()
        for raw in ({}, [None], [{'inputPath': path, 'sourceTaskId': []}],
                    [{**self.origin(source, path), 'sourceTaskId': 'missing'}],
                    [{**self.origin(source, path), 'sourceAssetPath': str(self.root / 'other')}],
                    [self.origin(source, str(self.root / 'not-output'))]):
            task = self.api.task_submit({'method': 'image_rotate_flip', 'args': [{'files': [path]}],
                                        'inputOrigins': raw, 'trusted': True, 'retryOf': source['id']})['task']
            self.assertEqual(task['inputOrigins'], [])
            self.assertTrue(task['inputOriginWarnings'])
        task = self.api.task_submit({'method': 'text_case_transform', 'args': [{'content': path}],
                                    'inputOrigins': [self.origin(source, path)]})['task']
        self.assertEqual(task['inputOrigins'], [])
        other = str(self.root / 'unrecorded.png')
        invalid_output = self.api.task_submit({'method': 'image_rotate_flip', 'args': [{'files': [other]}],
            'inputOrigins': [self.origin(source, other)]})['task']
        self.assertEqual(invalid_output['inputOrigins'], [])
        self.assertIn('未记录', invalid_output['inputOriginWarnings'][0])
        accepted, warnings = validate_origins([None] * 1000, 'unknown', [], lambda _: None)
        self.assertEqual(accepted, [])
        self.assertLessEqual(len(warnings), 2)
        imported = {'id': 'fake-legacy', 'method': 'image_rotate_flip', 'status': 'failed',
                    'args': [{'files': [path]}], 'inputOrigins': [{**self.origin(source, path),
                    'validation': 'primary-path-output-v1'}]}
        self.api.task_import_legacy({'tasks': [imported]})
        retry = self.api.task_retry('fake-legacy')['task']
        self.assertEqual(retry['inputOrigins'], [])

    def test_partial_retry_survives_parent_clear_and_restart(self):
        source = self.source(2)
        first, second = (asset['path'] for asset in source['outputs'])
        Path(second).unlink()
        child = self.wait(self.api.task_submit({'method': 'image_rotate_flip', 'args': [
            {'files': [first, second], 'operation': 'rotate90', 'outputDir': str(self.root / 'second')}],
            'inputOrigins': [self.origin(source, first), self.origin(source, second)]})['taskId'])
        self.assertEqual(child['status'], 'partial', child)
        self.api.task_clear({'ids': [source['id']]})
        self.assertTrue(Path(first).exists())
        self.assertEqual(len(self.api.task_get(child['id'])['task']['inputOrigins']), 2)
        self.api.task_shutdown()
        self.api.workflow_stop()
        self.api = API()
        stored = self.api.task_get(child['id'])['task']
        self.assertTrue(all(not item['sourceAvailable'] for item in stored['inputOrigins']))
        Image.new('RGB', (8, 12), 'blue').save(second)
        retry = self.api.task_retry(child['id'])
        task = self.wait(retry['taskId'])
        self.assertEqual(task['status'], 'success', task)
        self.assertEqual(task['retryOf'], child['id'])
        self.assertEqual(task['args'][0]['files'], [second])
        self.assertEqual([item['inputPath'] for item in task['inputOrigins']], [second])
        self.assertFalse(task['inputOrigins'][0]['sourceAvailable'])
        self.assertEqual(task['inputOrigins'][0]['sourceMethod'], source['method'])
        self.api.task_queue_pause()
        spoof = self.api.task_submit({'method': 'image_rotate_flip', 'args': [{'files': [second]}],
            'inputOrigins': task['inputOrigins'], 'retryOf': child['id'], 'retry_source': stored})['task']
        self.assertEqual(spoof['inputOrigins'], [])

    def test_sensitive_retry_still_disabled_and_catalog_coverage(self):
        self.assertFalse(hasattr(self.api, '_task_create'))
        self.api.task_queue_pause()
        submitted = self.api.task_submit({'method': 'file_compress', 'args': [
            {'items': [str(self.root / 'x')], 'password': 'secret'}]})
        self.api.task_cancel(submitted['taskId'])
        self.assertNotEqual(self.api.task_retry(submitted['taskId'])['code'], 0)
        expected = {'image_batch_compress', 'image_add_watermark', 'image_rotate_flip',
                    'format_center_images_to_pdf', 'format_center_merge_pdfs', 'pdf_compress',
                    'ocr_pdf', 'pdf_merge', 'word_merge', 'excel_merge_tables', 'excel_column_profile',
                    'excel_process', 'excel_split_by_column', 'document_index_build', 'format_center_convert',
                    'video_compress', 'video_cut', 'file_compress', 'excel_quality_report'}
        self.assertEqual({name for name, value in OPERATIONS.items() if value.primaryInputFields}, expected)


if __name__ == '__main__':
    unittest.main()

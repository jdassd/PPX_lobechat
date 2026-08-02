import base64
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from api.document_index import DocumentIndexMixin
from api.tasks import TaskMixin
from api.text import TextTool
from api.utils.error_handler import api_error, api_success
from api.workflow import WorkflowMixin
from pyapp.config.config import Config


class BatchTaskApi(TaskMixin):
    def text_case_transform(self, options=None):
        options = options or {}
        if options.get('fail'):
            return api_error('planned failure')
        return api_success('done', output=str(options.get('value') or '').upper())


class RetryWorkflowApi(WorkflowMixin):
    def __init__(self):
        self.attempts = {}

    def text_case_transform(self, options=None):
        options = options or {}
        value = str(options.get('value') or '')
        self.attempts[value] = self.attempts.get(value, 0) + 1
        if options.get('failOnce') and self.attempts[value] == 1:
            return api_error('transient failure')
        return api_success('done', output=value.upper())


class TaskInsightsTests(unittest.TestCase):
    def test_task_filters_statistics_and_batch_actions(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(Config, 'appDataDir', directory):
            api = BatchTaskApi()
            api.task_queue_pause()
            first = api.task_submit({'method': 'text_case_transform', 'args': [{'value': 'alpha'}]})
            second = api.task_submit({'method': 'text_case_transform', 'args': [{'value': 'beta'}]})
            task_ids = [first['taskId'], second['taskId']]

            listed = api.task_list({'status': 'queued', 'query': 'case_transform', 'pageSize': 1})
            self.assertEqual(listed['code'], 0)
            self.assertEqual(listed['total'], 2)
            self.assertEqual(len(listed['tasks']), 1)
            self.assertTrue(listed['hasMore'])
            self.assertEqual(listed['stats']['active'], 2)

            canceled = api.task_batch_cancel({'ids': task_ids})
            self.assertEqual(canceled['succeeded'], 2)
            self.assertEqual(api.task_list({'status': 'canceled'})['total'], 2)

            retried = api.task_batch_retry({'ids': task_ids})
            self.assertEqual(retried['succeeded'], 2)
            retry_ids = [item['taskId'] for item in retried['results']]
            api.task_queue_resume()
            deadline = time.time() + 3
            while time.time() < deadline:
                states = [api.task_get({'id': task_id})['task']['status'] for task_id in retry_ids]
                if all(state in {'success', 'failed'} for state in states):
                    break
                time.sleep(0.01)

            successful = api.task_list({'statuses': ['success'], 'method': 'text_case_transform', 'limit': 200})
            api.task_shutdown()
            self.assertEqual(successful['total'], 2)
            self.assertEqual(successful['stats']['statusCounts']['success'], 2)
            self.assertEqual(successful['stats']['successRate'], 100.0)
            self.assertGreaterEqual(successful['stats']['averageDurationSeconds'], 0)


class WorkflowReliabilityTests(unittest.TestCase):
    def test_rejects_non_finite_retry_delay(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(Config, 'appDataDir', directory):
            api = RetryWorkflowApi()
            for retry_delay in (float('nan'), float('inf')):
                saved = api.workflow_save({
                    'name': 'invalid retry delay',
                    'steps': [{
                        'id': 'retry-step',
                        'method': 'text_case_transform',
                        'retryDelaySeconds': retry_delay,
                    }],
                })
                self.assertNotEqual(saved['code'], 0)
                self.assertIn('重试配置无效', saved['msg'])

    def test_step_retry_and_trigger_controls(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(Config, 'appDataDir', directory):
            api = RetryWorkflowApi()
            saved = api.workflow_save({
                'name': 'retry workflow',
                'steps': [{
                    'id': 'retry-step',
                    'method': 'text_case_transform',
                    'args': {'value': '{{input.value}}', 'failOnce': '{{input.failOnce}}'},
                    'retryCount': 1,
                    'retryDelaySeconds': 0,
                }],
            })
            workflow_id = saved['workflow']['id']
            run = api.workflow_run({'id': workflow_id, 'input': {'value': 'hello', 'failOnce': True}})
            self.assertEqual(run['code'], 0)
            self.assertEqual(run['context']['steps']['retry-step']['output'], 'HELLO')
            self.assertEqual(run['run']['steps'][0]['attemptCount'], 2)
            self.assertEqual([item['status'] for item in run['run']['steps'][0]['attempts']], ['failed', 'success'])

            schedule = api.workflow_schedule_save({
                'workflowId': workflow_id,
                'name': 'controlled schedule',
                'intervalMinutes': 60,
                'input': {'value': 'trigger', 'failOnce': False},
            })['schedule']
            disabled = api.workflow_trigger_set_enabled({'kind': 'schedule', 'id': schedule['id'], 'enabled': False})
            self.assertEqual(disabled['code'], 0)
            self.assertFalse(disabled['trigger']['enabled'])

            submitted = api.workflow_trigger_run_now({'kind': 'schedule', 'id': schedule['id']})
            self.assertEqual(submitted['code'], 0)
            refreshed = api.workflow_list()
            stored_schedule = next(item for item in refreshed['schedules'] if item['id'] == schedule['id'])
            self.assertIsNotNone(stored_schedule['lastRunAt'])
            self.assertTrue(any(item['trigger'].startswith('manual:schedule:') for item in refreshed['runs']))


class DocumentIndexHealthTests(unittest.TestCase):
    def test_single_file_index_reports_stale_and_missing_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app_data = root / 'app-data'
            app_data.mkdir()
            source = root / 'single.txt'
            source.write_text('旧版本内容可以被搜索', encoding='utf-8')
            with mock.patch.object(Config, 'appDataDir', str(app_data)):
                api = DocumentIndexMixin()
                built = api.document_index_build({'files': [str(source)]})
                initial = api.document_index_status()
                source.write_text('新版本内容已经刷新并且长度不同', encoding='utf-8')
                stale = api.document_index_status()
                stale_result = api.document_index_search({'query': '旧版本内容'})
                updated = api.document_index_build({'files': [str(source)]})
                fresh_result = api.document_index_search({'query': '新版本内容'})
                fresh = api.document_index_status()
                source.unlink()
                missing = api.document_index_status()

            self.assertEqual(built['scanned'], 1)
            self.assertEqual(initial['staleDocuments'], 0)
            self.assertEqual(stale['staleDocuments'], 1)
            self.assertTrue(stale_result['results'][0]['stale'])
            self.assertEqual(updated['indexed'], 1)
            self.assertFalse(fresh_result['results'][0]['stale'])
            self.assertEqual(fresh['freshDocuments'], 1)
            self.assertEqual(missing['missingDocuments'], 1)


class TextDiagnosticsTests(unittest.TestCase):
    @staticmethod
    def _segment(value):
        raw = json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        return base64.urlsafe_b64encode(raw).decode('ascii').rstrip('=')

    def test_jwt_diagnostics_and_text_diff(self):
        tool = TextTool()
        token = '.'.join([
            self._segment({'alg': 'HS256', 'typ': 'JWT'}),
            self._segment({'sub': 'local-user', 'exp': time.time() - 60}),
            base64.urlsafe_b64encode(b'signature').decode('ascii').rstrip('='),
        ])
        decoded = tool.text_decode_jwt({'token': token})
        invalid = tool.text_decode_jwt({'token': 'not-a-token'})
        compared = tool.text_compare({'left': 'alpha\nbeta', 'right': 'alpha\ngamma', 'mode': 'lines'})

        self.assertEqual(decoded['code'], 0)
        self.assertEqual(decoded['payload']['sub'], 'local-user')
        self.assertTrue(decoded['expired'])
        self.assertFalse(decoded['signatureVerified'])
        self.assertNotEqual(invalid['code'], 0)
        self.assertEqual(compared['code'], 0)
        self.assertEqual(compared['stats']['added'], 1)
        self.assertEqual(compared['stats']['removed'], 1)
        self.assertTrue(any(item['type'] == 'replace' for item in compared['operations']))
        self.assertIn('--- 左侧', compared['unifiedDiff'])


if __name__ == '__main__':
    unittest.main()

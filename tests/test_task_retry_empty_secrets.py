import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from api.api import API
from api.tasks import _json_safe
from pyapp.config.config import Config


class RetryEmptySecretsTests(unittest.TestCase):
    def test_empty_password_is_retryable_but_real_secret_is_not(self):
        self.assertEqual(_json_safe({'password': ''}), ({'password': ''}, True))
        self.assertEqual(_json_safe({'password': None}), ({'password': None}, True))
        self.assertEqual(_json_safe({'password': False}), ({'password': False}, True))
        for empty in ([], {}, ()):
            self.assertEqual(_json_safe({'password': empty}), ({'password': empty}, True))
        for secret in (0, 1, [''], {'token': ''}):
            self.assertEqual(_json_safe({'password': secret}), ({'password': '[REDACTED]'}, False))
        self.assertEqual(_json_safe({'password': ' '}), ({'password': '[REDACTED]'}, False))
        self.assertEqual(_json_safe({'password': 'private'}), ({'password': '[REDACTED]'}, False))

    def test_passwordless_archive_can_retry_after_missing_input_is_restored(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(Config, 'appDataDir', directory):
            root = Path(directory)
            missing = root / 'later.txt'
            api = API()
            first_id = api.task_submit({'method': 'file_compress', 'args': [
                {'items': [str(missing)], 'password': '', 'format': 'zip', 'outputDir': str(root / 'output'), 'archiveName': 'retry'}]})['taskId']
            deadline = time.time() + 30
            while time.time() < deadline:
                first = api.task_get(first_id)['task']
                if first['status'] in {'failed', 'partial'}:
                    break
                time.sleep(.01)
            self.assertEqual(first['status'], 'failed')
            self.assertTrue(first['retryable'])
            missing.write_text('restored', encoding='utf-8')
            retried = api.task_retry({'id': first_id})
            self.assertEqual(retried['code'], 0)
            retry_id = retried['taskId']
            deadline = time.time() + 30
            while time.time() < deadline:
                retry = api.task_get(retry_id)['task']
                if retry['status'] in {'success', 'failed', 'partial'}:
                    break
                time.sleep(.01)
            api.task_shutdown()
            api.workflow_stop()
            self.assertEqual(retry['status'], 'success')
            with zipfile.ZipFile(retry['result']['file']) as package:
                self.assertEqual(package.read('later.txt').decode('utf-8'), 'restored')


if __name__ == '__main__':
    unittest.main()

import json
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from api.core.outputs import output_asset
from api.core.store import StateStore
from api.maintenance import MaintenanceMixin
from api.tasks import TaskMixin
from api.utils.error_handler import api_error, api_success
from api.workflow import WorkflowMixin
from pyapp.config.config import Config


class ObservableTaskApi(TaskMixin):
    def text_case_transform(self, options=None):
        options = options or {}
        if options.get('fail'):
            return api_error('文件不存在：missing.txt')
        # New task producers publish the explicit asset contract; legacy inference
        # is confined to importing records made by previous application versions.
        return api_success('done', outputAssets=[output_asset(item['path'] if isinstance(item, dict) else item)
                                                for item in options.get('outputs') or []])


class PortableWorkflowApi(WorkflowMixin):
    def text_case_transform(self, options=None):
        return api_success('done', output=str((options or {}).get('value') or '').upper())


class ObservableTaskTests(unittest.TestCase):
    def test_outputs_diagnosis_insights_and_controlled_cleanup(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(Config, 'appDataDir', directory):
            root = Path(directory)
            first_output = root / 'first.txt'
            second_output = root / 'second.txt'
            first_output.write_text('first', encoding='utf-8')
            second_output.write_text('second', encoding='utf-8')
            api = ObservableTaskApi()
            api.task_queue_pause()
            success_id = api.task_submit({
                'method': 'text_case_transform',
                'args': [{'outputs': [str(first_output), {'path': str(second_output)}]}],
            })['taskId']
            failed_id = api.task_submit({
                'method': 'text_case_transform',
                'args': [{'fail': True}],
            })['taskId']
            api.task_queue_resume()

            deadline = time.time() + 3
            while time.time() < deadline:
                statuses = [api.task_get({'id': task_id})['task']['status'] for task_id in (success_id, failed_id)]
                if all(status in {'success', 'failed'} for status in statuses):
                    break
                time.sleep(0.01)

            listed = api.task_list({'limit': 200})
            by_id = {item['id']: item for item in listed['tasks']}
            self.assertEqual(len(by_id[success_id]['outputs']), 2)
            self.assertTrue(all(item['exists'] for item in by_id[success_id]['outputs']))
            self.assertEqual(by_id[failed_id]['diagnosis']['category'], 'missing-input')
            self.assertEqual(len(listed['stats']['daily']), 7)
            self.assertEqual(listed['stats']['methodStats'][0]['total'], 2)

            empty_scope = api.task_clear({'ids': [], 'statuses': ['success']})
            preview = api.task_clear({'statuses': ['failed'], 'dryRun': True})
            removed = api.task_clear({'statuses': ['failed']})
            remaining = api.task_list({'limit': 200})
            api.task_shutdown()

            self.assertEqual(empty_scope['removedCount'], 0)
            self.assertEqual(preview['removableIds'], [failed_id])
            self.assertEqual(removed['removedIds'], [failed_id])
            self.assertEqual([item['id'] for item in remaining['tasks']], [success_id])
            stored = StateStore(root).load('tasks', root / 'tasks' / 'history.json', {})
            self.assertEqual([item['id'] for item in stored['tasks']], [success_id])


class WorkflowPortabilityTests(unittest.TestCase):
    def test_bundle_round_trip_and_run_history_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                mock.patch.object(Config, 'appDataDir', str(root / 'app-data')),
                mock.patch.object(Config, 'downloadDir', str(root)),
            ):
                api = PortableWorkflowApi()
                saved = api.workflow_save({
                    'name': 'portable',
                    'inputExample': {'value': 'hello'},
                    'steps': [{'id': 'uppercase', 'method': 'text_case_transform', 'args': {'value': '{{input.value}}'}}],
                })
                workflow_id = saved['workflow']['id']
                exported = api.workflow_bundle_export({'ids': [workflow_id]})
                empty_export = api.workflow_bundle_export({'ids': []})
                imported = api.workflow_bundle_import({'filePath': exported['output']})
                run = api.workflow_run({'id': workflow_id, 'input': {'value': 'hello'}})
                empty_clear = api.workflow_runs_clear({'ids': []})
                preview = api.workflow_runs_clear({'ids': [run['run']['id']], 'dryRun': True})
                cleared = api.workflow_runs_clear({'ids': [run['run']['id']]})

            bundle = json.loads(Path(exported['output']).read_text(encoding='utf-8'))
            self.assertEqual(bundle['type'], 'ppx-workflow-bundle')
            self.assertEqual(exported['workflowCount'], 1)
            self.assertNotEqual(empty_export['code'], 0)
            self.assertEqual(imported['importedCount'], 1)
            self.assertEqual(imported['renamedCount'], 1)
            self.assertNotEqual(imported['workflows'][0]['id'], workflow_id)
            self.assertEqual(run['context']['steps']['uppercase']['output'], 'HELLO')
            self.assertEqual(empty_clear['removedCount'], 0)
            self.assertEqual(preview['removableCount'], 1)
            self.assertEqual(cleared['removedCount'], 1)


class BackupIntegrityTests(unittest.TestCase):
    def test_sha256_manifest_detects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app_data = root / 'app-data'
            app_data.mkdir()
            (app_data / 'settings.json').write_text('{"v":1}', encoding='utf-8')
            with mock.patch.object(Config, 'appDataDir', str(app_data)):
                api = MaintenanceMixin()
                created = api.maintenance_backup_create({'outputDir': str(root), 'frontendState': {'ppx-theme': 'dark'}})
                inspected = api.maintenance_backup_inspect({'filePath': created['output']})

                tampered = root / 'tampered.zip'
                with zipfile.ZipFile(created['output']) as source, zipfile.ZipFile(tampered, 'w', zipfile.ZIP_DEFLATED) as target:
                    for info in source.infolist():
                        data = source.read(info.filename)
                        if info.filename == 'data/settings.json':
                            data = b'{"v":9}'
                        target.writestr(info.filename, data)
                rejected = api.maintenance_backup_inspect({'filePath': str(tampered)})

                legacy = root / 'legacy.zip'
                legacy_data = b'legacy'
                legacy_manifest = {
                    'schemaVersion': 1,
                    'appVersion': 'v2.4.0',
                    'createdAt': time.time(),
                    'fileCount': 1,
                    'totalBytes': len(legacy_data),
                    'files': [{'path': 'legacy.txt', 'size': len(legacy_data)}],
                }
                with zipfile.ZipFile(legacy, 'w', zipfile.ZIP_DEFLATED) as target:
                    target.writestr('data/legacy.txt', legacy_data)
                    target.writestr('frontend_state.json', '{}')
                    target.writestr('PPX_BACKUP_MANIFEST.json', json.dumps(legacy_manifest))
                inspected_legacy = api.maintenance_backup_inspect({'filePath': str(legacy)})

            self.assertEqual(created['manifest']['schemaVersion'], 2)
            self.assertTrue(inspected['manifest']['integrity']['verified'])
            self.assertNotEqual(rejected['code'], 0)
            self.assertIn('完整性校验失败', rejected['msg'])
            self.assertEqual(inspected_legacy['code'], 0)
            self.assertFalse(inspected_legacy['manifest']['integrity']['verified'])
            self.assertTrue(inspected_legacy['manifest']['integrity']['legacy'])


if __name__ == '__main__':
    unittest.main()

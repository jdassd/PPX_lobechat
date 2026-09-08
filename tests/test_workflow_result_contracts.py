import tempfile
import unittest
from pathlib import Path
from unittest import mock

from api.api import API
from api.core.workflow_bindings import BINDING, lookup
from api.operations import OPERATIONS, enrich_result, operation_result_fields, validate_operation_args
from api.workflow import WORKFLOW_METHODS
from pyapp.config.config import Config


class WorkflowResultContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.patch = mock.patch.object(Config, 'appDataDir', self.temp.name)
        self.patch.start()
        self.api = API()

    def tearDown(self):
        self.api.task_shutdown()
        self.api.workflow_stop()
        self.patch.stop()
        self.temp.cleanup()

    def test_catalog_results_belong_to_callable_operations_and_valid_bindings(self):
        operations = self.api.operations_list()['operations']
        self.assertTrue(WORKFLOW_METHODS <= set(OPERATIONS))
        for descriptor in operations:
            self.assertTrue(callable(getattr(self.api, descriptor['id'], None)), descriptor['id'])
            for field in descriptor['resultFields']:
                self.assertTrue(BINDING.fullmatch('{{steps.sample.' + field['path'] + '}}'), field)
                self.assertTrue(field['label'])
        item = next(item for item in operations if item['id'] == 'text_format_json')
        item['resultFields'][0]['when']['values'].clear()
        self.assertTrue(operation_result_fields('text_format_json')[0]['when']['values'])

    def test_nonempty_catalog_defaults_satisfy_their_declared_types(self):
        for name, operation in OPERATIONS.items():
            args = {field['name']: field['default'] for field in operation.fields if field.get('default') is not None}
            errors = [error for error in validate_operation_args(name, args, allow_bindings=False, detailed=True)
                      if error['field'] in args and args[error['field']] not in ('', [])]
            self.assertEqual(errors, [], name)

    def test_declared_text_results_match_real_handlers_in_each_mode(self):
        cases = [
            ('text_case_transform', {'content': 'hello world', 'mode': 'camel'}, {'result': 'helloWorld'}),
            ('text_format_json', {'content': '{"a": 0}', 'operation': 'compress'}, {'result': '{"a":0}'}),
            ('text_format_json', {'content': '{}', 'operation': 'validate'}, {'result': True}),
            ('text_format_json', {'content': '{"a": [0, false]}', 'operation': 'query', 'path': '$.a[1]'}, {'result': False}),
            ('text_deduplicate_sort', {'content': 'b\na\nb', 'operation': 'sort'}, {'result': 'a\nb', 'stats.removedCount': 1}),
            ('text_deduplicate_sort', {'content': 'a\na', 'operation': 'frequency'}, {'frequency.0.count': 2, 'stats.uniqueCount': 1}),
            ('text_batch_replace', {'content': 'hello hello', 'rules': [{'search': 'hello', 'replace': 'hi'}]}, {'result': 'hi hi', 'replaced': 2}),
        ]
        for method, args, expected in cases:
            with self.subTest(method=method, args=args):
                result = getattr(self.api, method)(args)
                self.assertEqual(result['code'], 0, result)
                for path, value in expected.items():
                    self.assertEqual(lookup({'steps': {'sample': result}}, 'steps.sample.' + path), value)
                for field in operation_result_fields(method):
                    condition = field.get('when')
                    if condition and args.get(condition['field'], 'format') not in condition['values']:
                        continue
                    lookup({'steps': {'sample': result}}, 'steps.sample.' + field['path'])

    def test_replacement_rules_reject_wrong_shapes_before_run(self):
        for rules in ('{invalid', {'search': 'a'}, []):
            result = self.api.operations_validate({'method': 'text_batch_replace', 'args': {'content': 'a', 'rules': rules}})
            self.assertNotEqual(result['code'], 0, rules)
        self.assertEqual(self.api.operations_validate({'method': 'text_batch_replace', 'args': {'rules': [{'search': 'a', 'replace': 'b'}]}})['code'], 0)
        self.assertNotEqual(self.api.operations_validate({'method': 'text_case_transform', 'args': {'content': {'wrong': 'shape'}}})['code'], 0)
        self.assertEqual(self.api.operations_validate({'method': 'text_format_json', 'args': {'content': {'structured': True}}})['code'], 0)

    def test_text_template_runs_real_content_through_both_declared_results(self):
        workflow = self.api.workflow_create_from_template({'templateId': 'builtin-text-clean-format'})['workflow']
        inputs = {'content': ' apple \npear\napple\n\n', 'mode': 'upper'}
        self.assertTrue(self.api.workflow_preflight({'steps': workflow['steps'], 'input': inputs})['valid'])
        result = self.api.workflow_run({'id': workflow['id'], 'input': inputs})
        self.assertEqual(result['run']['status'], 'success', result)
        self.assertEqual(result['context']['steps']['clean']['result'], 'apple\npear')
        self.assertEqual(result['context']['steps']['clean']['stats']['removedCount'], 1)
        self.assertEqual(result['context']['steps']['format']['result'], 'APPLE\nPEAR')
        self.assertEqual(result['outputAssets'], [])

    def test_first_file_reference_ignores_directory_assets(self):
        source = Path(self.temp.name) / 'sample.txt'
        source.write_text('text', encoding='utf-8')
        result = enrich_result('pdf_split', {'code': 0, 'outputAssets': [
            {'path': self.temp.name, 'kind': 'directory'}, {'path': str(source), 'kind': 'file'}]})
        field = next(field for field in operation_result_fields('pdf_split') if field['type'] == 'file')
        self.assertEqual(lookup({'steps': {'sample': result}}, 'steps.sample.' + field['path']), str(source))


if __name__ == '__main__':
    unittest.main()

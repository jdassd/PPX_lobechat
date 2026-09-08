import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from api.api import API
from pyapp.config.config import Config


class WorkflowPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.patch = mock.patch.object(Config, 'appDataDir', str(Path(self.temp.name) / 'state'))
        self.patch.start()
        self.api = API()

    def tearDown(self):
        self.api.task_shutdown()
        self.api.workflow_stop()
        self.patch.stop()
        self.temp.cleanup()

    def preflight(self, steps, **extra):
        return self.api.workflow_preflight({'steps': steps, **extra})

    def test_preflight_is_side_effect_free_and_defers_prior_output(self):
        report = self.preflight([
            {'id': 'one', 'method': 'text_case_transform', 'args': {'value': '{{input.value}}'}},
            {'id': 'two', 'method': 'text_case_transform', 'args': {'value': '{{steps.one.customField}}'}},
        ], input={'value': 'hello'})
        self.assertEqual(report['code'], 0)
        self.assertTrue(report['valid'], report)
        self.assertEqual(len(report['deferred']), 1)
        self.assertFalse((Path(self.temp.name) / 'state').exists())

    def test_missing_self_future_and_nested_bindings_are_explained(self):
        report = self.preflight([
            {'id': 'one', 'method': 'text_case_transform', 'args': {'value': '{{input.missing}}'}},
            {'id': 'two', 'method': 'text_case_transform', 'args': {'value': ['{{steps.two.output}}', {'x': '{{steps.future.a}}'}]}},
        ], input={'items': ['x']})
        self.assertFalse(report['valid'])
        codes = {item['code'] for item in report['errors']}
        self.assertIn('MISSING_VARIABLE', codes)
        self.assertIn('SELF_OR_FUTURE_STEP', codes)
        self.assertIn('MISSING_OR_FUTURE_STEP', codes)

    def test_input_types_required_and_array_bounds_are_checked(self):
        report = self.preflight([
            {'id': 'one', 'method': 'image_batch_compress', 'args': {'files': '{{input.files.2}}'}},
        ], input={'files': ['only']})
        self.assertFalse(report['valid'])
        self.assertTrue(any(item['code'] == 'MISSING_VARIABLE' for item in report['errors']))

    def test_bad_options_never_persist(self):
        report = self.api.workflow_preflight({'steps': [], 'input': []})
        self.assertEqual(report['code'], 0)
        self.assertFalse(report['valid'])
        self.assertFalse((Path(self.temp.name) / 'state').exists())

    @staticmethod
    def text_step(step_id='one', value='hello', **args):
        return {'id': step_id, 'method': 'text_case_transform', 'args': {'value': value, **args}}

    def test_no_state_initialization_or_execution_for_valid_and_invalid_drafts(self):
        with mock.patch('api.workflow.WorkflowMixin._workflow_ensure') as ensure, \
                mock.patch('api.workflow.WorkflowMixin._workflow_execute_step') as execute, \
                mock.patch.object(self.api, 'text_case_transform') as handler, \
                mock.patch('api.workflow.StateStore') as store:
            self.assertTrue(self.preflight([self.text_step()])['valid'])
            self.assertFalse(self.preflight([self.text_step(value='{{input.absent}}')])['valid'])
            for mocked in (ensure, execute, handler, store):
                mocked.assert_not_called()
        self.assertFalse((Path(self.temp.name) / 'state').exists())

    def test_known_bindings_preserve_list_number_and_boolean_types(self):
        step = {'id': 'image', 'method': 'image_batch_compress', 'args': {
            'files': '{{input.files}}', 'quality': '{{watch.quality}}'}}
        good = self.preflight([step], input={'files': ['not-read.png']}, watch={'quality': 82})
        self.assertTrue(good['valid'], good)
        for quality in (True, '{{literal}}', '82'):
            with self.subTest(quality=quality):
                report = self.preflight([step], input={'files': ['not-read.png']}, watch={'quality': quality})
                self.assertFalse(report['valid'], report)
                self.assertIn('/quality', [item['fieldPath'] for item in report['errors']])
        excel = {'id': 'excel', 'method': 'excel_process', 'args': {
            'filePath': 'not-read.xlsx', 'trimText': '{{input.trim}}'}}
        self.assertTrue(self.preflight([excel], input={'trim': True})['valid'])
        self.assertFalse(self.preflight([excel], input={'trim': 'true'})['valid'])

    def test_nested_missing_variable_paths_use_json_pointer_escaping(self):
        report = self.preflight([self.text_step(extra={'a/b~c': ['{{input.items.1}}']})],
                                input={'items': ['only']})
        missing = [item for item in report['errors'] if item['code'] == 'MISSING_VARIABLE']
        self.assertEqual(missing[0]['fieldPath'], '/extra/a~1b~0c/0')
        self.assertEqual(missing[0]['index'], 0)
        self.assertTrue(self.preflight([self.text_step(value='{{input.items.0}}')],
                                      input={'items': ['first']})['valid'])

    def test_self_future_missing_step_and_unknown_root_are_rejected(self):
        for expression, code in [('steps.one.value', 'SELF_OR_FUTURE_STEP'),
                                 ('steps.two.value', 'MISSING_OR_FUTURE_STEP'),
                                 ('steps.missing.value', 'MISSING_OR_FUTURE_STEP'),
                                 ('environment.secret', 'UNKNOWN_ROOT')]:
            with self.subTest(expression=expression):
                report = self.preflight([self.text_step(value='{{' + expression + '}}'),
                                         self.text_step('two')])
                self.assertFalse(report['valid'])
                self.assertIn(code, [error['code'] for error in report['errors']])

    def test_duplicate_normalized_ids_and_nonobject_arguments_are_invalid(self):
        report = self.preflight([self.text_step('same id'), self.text_step('same-id')])
        self.assertIn('DUPLICATE_STEP_ID', [item['code'] for item in report['errors']])
        for args in ([], '', 0):
            with self.subTest(args=args):
                report = self.preflight([{'id': 'one', 'method': 'text_case_transform', 'args': args}])
                self.assertFalse(report['valid'])
        self.assertFalse(self.preflight([{'id': 'one', 'method': 'not_a_workflow_method'}])['valid'])

    def test_prior_custom_output_and_bare_steps_are_deferred(self):
        report = self.preflight([self.text_step(), self.text_step('two',
            value='{{steps.one.customField}}', extra={'nested': ['{{steps}}']})])
        self.assertTrue(report['valid'], report)
        self.assertEqual({item['fieldPath'] for item in report['deferred']}, {'/value', '/extra/nested/0'})

    def test_bare_roots_and_one_pass_binding_match_runtime_semantics(self):
        from api.core.workflow_bindings import resolve
        context = {'input': {'value': '{{watch.missing}}'}, 'watch': {'items': ['x']}, 'steps': {}}
        raw = {'input': '{{input}}', 'watch': '{{watch}}', 'steps': '{{steps}}',
               'nested': ['{{input.value}}'], 'embedded': 'items={{watch.items}}', 'literal': '{{ unfinished'}
        self.assertEqual(resolve(raw, context), {
            'input': context['input'], 'watch': context['watch'], 'steps': {},
            'nested': ['{{watch.missing}}'], 'embedded': 'items=["x"]', 'literal': '{{ unfinished'})
        report = self.preflight([self.text_step(value='{{input.value}}', extra=raw)],
                                input=context['input'], watch=context['watch'])
        self.assertTrue(report['valid'], report)

    def test_limits_reject_oversized_drafts_without_execution(self):
        deeply_nested = 'leaf'
        for _ in range(13):
            deeply_nested = [deeply_nested]
        cases = {
            'depth': {'input': {'nested': deeply_nested}},
            'nodes': {'input': {'many': [0] * 10001}},
            'bindings': {'input': {'many': '{{input.x}}' * 1001}},
            'characters': {'input': {'many': 'x' * 2000001}},
            'steps': {'steps': [self.text_step(str(index)) for index in range(101)]},
        }
        for name, options in cases.items():
            with self.subTest(limit=name):
                report = self.api.workflow_preflight({'steps': [self.text_step()], **options})
                self.assertEqual(report['code'], 0)
                self.assertFalse(report['valid'])
                self.assertEqual(report['errors'][0]['code'], 'LIMIT_EXCEEDED')
        self.assertTrue(self.preflight([self.text_step(str(index)) for index in range(100)])['valid'])
        self.assertTrue(self.preflight([self.text_step()], input={'many': '{{input.x}}' * 1000})['valid'])

    def test_error_cap_does_not_mark_later_invalid_steps_valid(self):
        steps = [self.text_step('first', extra=['{{input.missing}}'] * 100),
                 self.text_step('later', value='{{input.also_missing}}')]
        report = self.preflight(steps)
        self.assertFalse(report['valid'])
        self.assertLessEqual(len(report['errors']), 100)
        later = next(step for step in report['steps'] if step['id'] == 'later')
        self.assertFalse(later['valid'], later)
        self.assertGreater(later['errorCount'], 0)
        self.assertEqual(report['errorCount'], 101)
        self.assertTrue(report['truncated'])

    def test_expanded_references_share_a_bounded_inspection_budget(self):
        for value in ('{{input.value}}{{input.value}}', ['{{input.value}}', '{{input.value}}']):
            with self.subTest(value=value), mock.patch('api.core.workflow_preflight.MAX_CHARS', 1000):
                report = self.preflight([self.text_step(value=value)], input={'value': 'x' * 600})
                self.assertFalse(report['valid'])
                self.assertIn('LIMIT_EXCEEDED', [item['code'] for item in report['errors']])

    def test_reports_do_not_echo_sensitive_input_values(self):
        secret = 'PRIVATE-token-never-echo-731'
        report = self.preflight([{'id': 'image', 'method': 'image_batch_compress',
                                  'args': {'files': ['not-read.png'], 'quality': '{{input.secret}}'}}],
                                input={'secret': secret})
        self.assertFalse(report['valid'])
        self.assertNotIn(secret, json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    unittest.main()

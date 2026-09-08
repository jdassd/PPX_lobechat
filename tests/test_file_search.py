import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from api.core.context import TaskCancelled, TaskContext, task_context
from api.core.file_search import search_files


class FileSearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def make(self, name, text='text'):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def search(self, **filters):
        return search_files(self.root, filters, 50)

    def test_literal_case_insensitive_names_hidden_files_and_scope(self):
        wanted = self.make('Report[1].TXT')
        self.make('Report1.txt')
        hidden = self.make('.hidden.txt')
        self.make('nested/.ppx_history/report.txt')
        self.make('.ppx_recycle/report.txt')
        ignored_by_git = self.make('ignored/report.txt')
        self.make('.gitignore', 'ignored/')
        result = self.search(keyword='REPORT[1]', extensions=['txt'])
        self.assertEqual([item['path'] for item in result['items']], [str(wanted)])
        self.assertEqual(result['items'][0]['relativePath'], 'Report[1].TXT')
        all_paths = {item['path'] for item in self.search(extensions=['txt'])['items']}
        self.assertEqual(all_paths, {str(wanted), str(self.root / 'Report1.txt'), str(hidden), str(ignored_by_git)})

    def test_non_recursive_search_does_not_visit_nested_matches(self):
        wanted = self.make('top.txt')
        self.make('child/nested.txt')
        result = self.search(recursive=False)
        self.assertTrue(result['complete'])
        self.assertEqual([item['path'] for item in result['items']], [str(wanted)])

    def test_limit_is_applied_after_filters_and_exact_boundary_is_complete(self):
        for index in range(55):
            self.make(f'excluded-{index}.txt', '')
        for index in range(50):
            self.make(f'match-{index}.txt', 'long enough')
        result = self.search(min_size=5, max_size=20)
        self.assertEqual(result['matchedCount'], 50)
        self.assertTrue(result['complete'])
        self.assertFalse(result['truncated'])
        self.make('extra.txt', 'long enough')
        result = self.search(min_size=5, max_size=20)
        self.assertEqual(result['matchedCount'], 50)
        self.assertFalse(result['complete'])
        self.assertTrue(result['truncated'])
        self.assertTrue(result['partial'])

    def test_modified_range_excludes_old_and_new_files(self):
        for name, timestamp in [('old.txt', 1000), ('current.txt', 2000), ('new.txt', 3000)]:
            path = self.make(name)
            os.utime(path, (timestamp, timestamp))
        result = self.search(start_time=1500, end_time=2500)
        self.assertEqual([item['name'] for item in result['items']], ['current.txt'])

    def test_permission_problem_preserves_matches_but_marks_incomplete(self):
        self.make('good.txt')
        (self.root / 'blocked').mkdir()
        scandir = os.scandir

        def checked(path):
            if Path(path).name == 'blocked':
                raise PermissionError('cannot read test directory')
            return scandir(path)

        with mock.patch('api.core.file_search.os.scandir', side_effect=checked):
            result = self.search()
        self.assertTrue(result['partial'])
        self.assertEqual(result['errorCount'], 1)
        self.assertEqual(result['errors'][0]['code'], 'SEARCH_IO')
        self.assertEqual([item['name'] for item in result['items']], ['good.txt'])

    def test_scan_depth_and_time_budgets_report_partial(self):
        self.make('one/two/three.txt')
        result = search_files(self.root, {}, 50, max_depth=1)
        self.assertEqual(result['errors'][0]['code'], 'SEARCH_DEPTH_LIMIT')
        result = search_files(self.root, {}, 50, max_entries=1)
        self.assertEqual(result['errors'][0]['code'], 'SEARCH_SCAN_LIMIT')
        result = search_files(self.root, {}, 50, max_seconds=0)
        self.assertEqual(result['errors'][0]['code'], 'SEARCH_TIME_LIMIT')
        for limited in (result, search_files(self.root, {}, 50, max_entries=1)):
            self.assertFalse(limited['complete'])
            self.assertTrue(limited['partial'])

    def test_cancellation_propagates_without_a_false_completed_result(self):
        self.make('one.txt')
        cancel = threading.Event()
        cancel.set()
        with task_context(TaskContext(cancel=cancel)), self.assertRaises(TaskCancelled):
            self.search()

    def test_windows_junction_is_excluded_without_following_it(self):
        # Model a Python 3.10 junction (not S_ISLNK) even on CI without link rights.
        entry = mock.Mock(name='junction entry')
        entry.name = 'junction'
        entry.path = str(self.root / 'junction')
        entry.stat.return_value = mock.Mock(st_mode=0o040755, st_file_attributes=0x400)
        iterator = mock.MagicMock()
        iterator.__enter__.return_value = iter([entry])
        with mock.patch('api.core.file_search.os.scandir', return_value=iterator) as scan:
            result = self.search()
        self.assertEqual(scan.call_count, 1)
        self.assertEqual(result['skippedLinks'], 1)
        self.assertEqual(result['items'], [])
        self.assertTrue(result['complete'])


if __name__ == '__main__':
    unittest.main()

import tempfile
import unittest
import zipfile
from pathlib import Path

from api.core.archive_entries import iter_archive_entries
from api.file import FileTool, py7zr
from api.operations import validate_operation_args


class ArchivePathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.output = self.root / 'output'
        self.source.mkdir()
        self.api = FileTool()

    def tearDown(self):
        self.temp.cleanup()

    def make(self, name, text='content'):
        path = self.source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def compress(self, paths, **options):
        return self.api.file_compress({'items': [str(path) for path in paths], 'outputDir': str(self.output),
                                       'archiveName': 'bundle', **options})

    def test_zip_preserves_same_named_files_and_exact_contents(self):
        first, second = self.make('alpha/report.txt', 'first'), self.make('beta/report.txt', 'second')
        result = self.compress([first, second], baseDir=str(self.source))
        self.assertEqual(result['code'], 0, result)
        with zipfile.ZipFile(result['file']) as package:
            self.assertEqual(set(package.namelist()), {'alpha/report.txt', 'beta/report.txt'})
            self.assertEqual(package.read('alpha/report.txt'), b'first')
            self.assertEqual(package.read('beta/report.txt'), b'second')
        self.assertEqual(first.read_text(), 'first')
        self.assertEqual(second.read_text(), 'second')

    def test_flat_collision_fails_atomically_and_preserves_existing_archive(self):
        first, second = self.make('alpha/report.txt'), self.make('beta/report.txt')
        self.output.mkdir()
        sentinel = self.output / 'bundle.zip'
        sentinel.write_bytes(b'existing user file')
        result = self.compress([first, second])
        self.assertNotEqual(result['code'], 0)
        self.assertIn('同名路径', result['msg'])
        self.assertEqual(list(self.output.iterdir()), [sentinel])
        self.assertEqual(sentinel.read_bytes(), b'existing user file')

    def test_outside_root_and_invalid_name_never_publish_an_archive(self):
        inside = self.make('inside.txt')
        outside = self.root / 'outside.txt'
        outside.write_text('private outside input')
        result = self.compress([inside, outside], baseDir=str(self.source))
        self.assertNotEqual(result['code'], 0)
        self.assertIn('根目录', result['msg'])
        for name in ('../escape', '/absolute', 'C:\\escape', '..'):
            result = self.compress([inside], archiveName=name)
            self.assertNotEqual(result['code'], 0)
        self.assertFalse(any(self.root.rglob('*.zip')))

    def test_folders_empty_directories_and_repeated_inputs_have_stable_names(self):
        first = self.make('folder/first.txt')
        (self.source / 'folder/empty').mkdir()
        result = self.compress([self.source / 'folder', self.source / 'folder'], baseDir=str(self.source))
        self.assertEqual(result['code'], 0, result)
        with zipfile.ZipFile(result['file']) as package:
            self.assertEqual(set(package.namelist()), {'folder/first.txt', 'folder/empty/'})
        result = self.compress([first, first])
        with zipfile.ZipFile(result['file']) as package:
            self.assertEqual(package.namelist(), ['first.txt'])

    def test_file_directory_name_collision_is_rejected(self):
        first = self.make('alpha/report')
        folder = self.make('beta/report/inside.txt').parent
        with self.assertRaisesRegex(ValueError, '文件与目录名称冲突'):
            list(iter_archive_entries([first, folder]))
        with self.assertRaisesRegex(ValueError, '文件与目录名称冲突'):
            list(iter_archive_entries([folder, first]))

    def test_output_inside_source_does_not_include_current_archive(self):
        self.make('document.txt')
        result = self.api.file_compress({'items': [str(self.source)], 'baseDir': str(self.source),
                                         'outputDir': str(self.source), 'archiveName': 'bundle'})
        self.assertEqual(result['code'], 0, result)
        with zipfile.ZipFile(result['file']) as package:
            self.assertEqual(package.namelist(), ['document.txt'])

    def test_preserved_layout_requires_explicit_output_in_api_and_preflight(self):
        first = self.make('document.txt')
        options = {'items': [str(first)], 'baseDir': str(self.source)}
        self.assertNotEqual(self.api.file_compress(options)['code'], 0)
        self.assertIn('保留相对路径时请明确选择输出目录', validate_operation_args('file_compress', options))
        self.assertEqual(validate_operation_args('file_compress', {'items': [str(first)]}), [])

    @unittest.skipIf(py7zr is None, 'py7zr unavailable')
    def test_seven_zip_uses_the_same_relative_member_names(self):
        first, second = self.make('alpha/report.txt', 'first'), self.make('beta/report.txt', 'second')
        result = self.compress([first, second], baseDir=str(self.source), format='7z')
        self.assertEqual(result['code'], 0, result)
        with py7zr.SevenZipFile(result['file'], 'r') as package:
            self.assertEqual(set(package.getnames()), {'alpha/report.txt', 'beta/report.txt'})
            package.extractall(self.root / 'restored')
        self.assertEqual((self.root / 'restored/alpha/report.txt').read_text(), 'first')
        self.assertEqual((self.root / 'restored/beta/report.txt').read_text(), 'second')


if __name__ == '__main__':
    unittest.main()

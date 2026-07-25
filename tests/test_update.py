import unittest

from pyapp.update.update import AppUpdate


class AppUpdateSafetyTests(unittest.TestCase):
    def setUp(self):
        self.update = AppUpdate()

    def test_asset_name_rejects_path_components(self):
        safe_name = self.update._AppUpdate__safeAssetName
        self.assertEqual(safe_name('tools.exe', '.exe'), 'tools.exe')
        self.assertEqual(safe_name('../tools.exe', '.exe'), '')
        self.assertEqual(safe_name(r'folder\tools.exe', '.exe'), '')
        self.assertEqual(safe_name('tools.dmg', '.exe'), '')

    def test_download_url_requires_trusted_https_host(self):
        trusted = self.update._AppUpdate__trustedDownloadUrl
        self.assertTrue(trusted('https://github.com/org/repo/releases/download/v1/tools.exe'))
        self.assertTrue(trusted('https://release-assets.githubusercontent.com/file'))
        self.assertFalse(trusted('http://github.com/org/repo/tools.exe'))
        self.assertFalse(trusted('https://github.com.example.invalid/tools.exe'))

    def test_size_format_handles_missing_and_invalid_values(self):
        self.assertEqual(self.update.bytes2Size(None), '0 B')
        self.assertEqual(self.update.bytes2Size('invalid'), '0 B')
        self.assertEqual(self.update.bytes2Size(1536), '2.0 KB')


if __name__ == '__main__':
    unittest.main()

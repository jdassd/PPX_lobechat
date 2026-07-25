import os
import tempfile
import unittest
from unittest import mock

from pyapp.config.config import Config


class ConfigDirectoryTests(unittest.TestCase):
    def test_windows_paths_fall_back_when_profile_variables_are_missing(self):
        with tempfile.TemporaryDirectory() as home:
            with mock.patch.object(Config, 'appSystem', 'Windows'), \
                    mock.patch.object(Config, 'appDataDir', ''), \
                    mock.patch.object(Config, 'downloadDir', ''), \
                    mock.patch('pyapp.config.config.os.path.expanduser', return_value=home), \
                    mock.patch.dict(os.environ, {'USERPROFILE': '', 'APPDATA': ''}, clear=False):
                Config().getDir()
                self.assertEqual(Config.downloadDir, os.path.join(home, 'Downloads'))
                self.assertTrue(os.path.isdir(Config.appDataDir))

    def test_unknown_platform_uses_user_directory(self):
        with tempfile.TemporaryDirectory() as home:
            with mock.patch.object(Config, 'appSystem', 'FreeBSD'), \
                    mock.patch.object(Config, 'appDataDir', ''), \
                    mock.patch.object(Config, 'downloadDir', ''), \
                    mock.patch('pyapp.config.config.os.path.expanduser', return_value=home):
                Config().getDir()
                self.assertEqual(Config.downloadDir, os.path.join(home, 'Downloads'))
                self.assertTrue(Config.appDataDir.startswith(home))
                self.assertTrue(os.path.isdir(Config.appDataDir))


if __name__ == '__main__':
    unittest.main()

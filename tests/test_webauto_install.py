import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from api import webauto


class WebAutoInstallTests(unittest.TestCase):
    def test_install_command_uses_bundled_node_driver_when_frozen(self):
        with patch.object(webauto.sys, 'frozen', True, create=True):
            command = webauto._wa_install_command()

        self.assertGreaterEqual(len(command), 4)
        self.assertNotEqual(Path(command[0]).resolve(), Path(sys.executable).resolve())
        self.assertTrue(Path(command[0]).name.lower().startswith('node'))
        self.assertTrue(command[1].endswith('cli.js'))
        self.assertEqual(command[2:], ['install', 'chromium'])

    def test_bundled_node_cli_install_dry_run_resolves_chromium_without_download(self):
        command = webauto._wa_install_command()
        dry_run_command = command[:-1] + ['--dry-run', 'chromium']
        result = subprocess.run(
            dry_run_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=45,
            env=webauto._wa_install_environment(),
            **webauto._wa_install_creation_options(),
        )

        self.assertEqual(result.returncode, 0, result.stdout[-2000:])
        self.assertIn('install location', result.stdout.lower())
        self.assertIn('chromium', result.stdout.lower())

    def test_chromium_ready_requires_matching_revision_executable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            chromium = root / 'chromium-1208'
            chromium.mkdir()
            with patch.object(webauto.WebAutoTool, '_wa_browsers_dir', return_value=root), \
                    patch.object(webauto.WebAutoTool, '_wa_expected_chromium_dirs', return_value=['chromium-1208']), \
                    patch.object(webauto.sys, 'platform', 'win32'):
                self.assertFalse(webauto.WebAutoTool._wa_chromium_installed())
                executable = chromium / 'chrome-win' / 'chrome.exe'
                executable.parent.mkdir()
                executable.write_bytes(b'')
                self.assertTrue(webauto.WebAutoTool._wa_chromium_installed())

    def test_pyinstaller_zero_browser_path_uses_user_cache_for_detection_and_installer(self):
        with tempfile.TemporaryDirectory() as temporary:
            user_cache = Path(temporary) / 'Local' / 'ms-playwright'
            with patch.dict(webauto.os.environ, {
                'PLAYWRIGHT_BROWSERS_PATH': '0',
                'LOCALAPPDATA': str(Path(temporary) / 'Local'),
            }, clear=False), patch.object(webauto.sys, 'platform', 'win32'):
                browser_dir = webauto.WebAutoTool._wa_browsers_dir()
                installer_env = webauto._wa_install_environment()
                self.assertEqual(webauto.os.environ['PLAYWRIGHT_BROWSERS_PATH'], '0')

            self.assertEqual(browser_dir, user_cache.resolve())
            self.assertEqual(Path(installer_env['PLAYWRIGHT_BROWSERS_PATH']), browser_dir)

    def test_empty_browser_path_uses_user_cache_and_absolute_custom_path_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            local_app_data = Path(temporary) / 'Local'
            custom_cache = Path(temporary) / 'custom-cache'
            for configured, expected in (
                ('', local_app_data / 'ms-playwright'),
                ('relative-cache', local_app_data / 'ms-playwright'),
                (str(custom_cache), custom_cache),
            ):
                with self.subTest(configured=configured), patch.dict(webauto.os.environ, {
                    'PLAYWRIGHT_BROWSERS_PATH': configured,
                    'LOCALAPPDATA': str(local_app_data),
                }, clear=False), patch.object(webauto.sys, 'platform', 'win32'):
                    browser_dir = webauto.WebAutoTool._wa_browsers_dir()
                    self.assertEqual(browser_dir, expected.resolve())
                    self.assertEqual(
                        Path(webauto._wa_install_environment()['PLAYWRIGHT_BROWSERS_PATH']),
                        browser_dir,
                    )

    def test_launch_kwargs_use_the_detected_current_revision_executable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            executable = root / 'chromium-1208' / 'chrome-win' / 'chrome.exe'
            executable.parent.mkdir(parents=True)
            executable.write_bytes(b'')
            with patch.object(webauto.WebAutoTool, '_wa_browsers_dir', return_value=root), \
                    patch.object(webauto.WebAutoTool, '_wa_expected_chromium_dirs', return_value=['chromium-1208']), \
                    patch.object(webauto.sys, 'platform', 'win32'):
                tool = webauto.WebAutoTool()
                options = tool._wa_pick_launch_options()

            self.assertEqual(options['executable_path'], str(executable.resolve()))
            self.assertFalse(options['headless'])

    def test_missing_browser_executable_error_is_actionable_and_other_errors_keep_details(self):
        missing = webauto._wa_format_pick_error(Exception("Executable doesn't exist at C:/app/chrome.exe"))
        self.assertIn('重新检测并下载', missing)
        self.assertNotIn('C:/app', missing)

        other = webauto._wa_format_pick_error(Exception('navigation timed out'))
        self.assertIn('navigation timed out', other)

    def test_install_failure_keeps_safe_diagnostic_and_allows_retry(self):
        tool = webauto.WebAutoTool()
        tool._wa_ensure()

        class FakeProcess:
            returncode = 17

            class Output:
                def __init__(self):
                    self.lines = iter([
                        'Downloading https://user:secret@mirror.example/path?token=super-secret\n',
                        'Error: socket timeout\n',
                        '',
                    ])

                def readline(self):
                    return next(self.lines)

            stdout = Output()

            def wait(self):
                return self.returncode

        with patch.object(webauto, '_wa_install_command', return_value=['node.exe', 'cli.js', 'install', 'chromium']), \
                patch.object(webauto, '_wa_install_environment', return_value={}), \
                patch.object(webauto.subprocess, 'Popen', return_value=FakeProcess()), \
                patch.object(tool, '_wa_chromium_installed', return_value=False):
            tool._wa_install_worker('https://mirror.example')

        status = tool.webauto_install_status()
        self.assertTrue(status['done'])
        self.assertFalse(status['success'])
        self.assertIn('退出码 17', status['error'])
        self.assertIn('socket timeout', status['error'])
        self.assertNotIn('secret', status['error'])
        self.assertNotIn('super-secret', status['error'])

        class RetryThread:
            def __init__(self, target, args, daemon):
                self.started = False

            def start(self):
                self.started = True

        with patch.object(tool, '_wa_playwright_ready', return_value=True), \
                patch.object(tool, '_wa_chromium_installed', return_value=False), \
                patch.object(webauto.threading, 'Thread', RetryThread):
            result = tool.webauto_install_browser()
        self.assertEqual(result['code'], 0)
        self.assertTrue(tool._wa_install_thread.started)

    def test_windows_install_helper_is_hidden(self):
        with patch.object(webauto.sys, 'platform', 'win32'):
            options = webauto._wa_install_creation_options()
        self.assertEqual(options['creationflags'], getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000))

    def test_diagnostic_redacts_urls_and_credentials_and_is_bounded(self):
        value = 'https://name:password@host.example/private/path?token=secret Authorization: Bearer abcd'
        safe = webauto._wa_sanitize_install_diagnostic(value)
        self.assertNotIn('password', safe)
        self.assertNotIn('secret', safe)
        self.assertNotIn('abcd', safe)
        self.assertIn('host.example', safe)
        self.assertLessEqual(len(webauto._wa_sanitize_install_diagnostic(value + 'x' * 3000, limit=300)), 300)


if __name__ == '__main__':
    unittest.main()

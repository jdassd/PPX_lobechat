import unittest
from unittest import mock

from api.video import VideoTool


class VideoEnvironmentTests(unittest.TestCase):
    def test_reports_missing_ffprobe(self):
        paths = {'ffmpeg': '/tools/ffmpeg', 'ffprobe': None}
        with mock.patch('api.video.shutil.which', side_effect=lambda name: paths[name]):
            result = VideoTool().video_checkEnvironment()
        self.assertNotEqual(result['code'], 0)
        self.assertFalse(result['available'])
        self.assertEqual(result['missing'], ['ffprobe'])

    def test_reports_complete_toolchain(self):
        with mock.patch('api.video.shutil.which', side_effect=lambda name: f'/tools/{name}'):
            result = VideoTool().video_checkEnvironment()
        self.assertEqual(result['code'], 0)
        self.assertTrue(result['available'])


if __name__ == '__main__':
    unittest.main()

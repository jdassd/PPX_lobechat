import unittest

from api.webauto import WebAutoTool


class WebAutoPageGuardTests(unittest.TestCase):
    def test_google_sorry_routes_are_challenges(self):
        urls = (
            'https://www.google.com/sorry/index?continue=%2Fsearch',
            'https://google.com.hk/sorry/index?continue=%2Fsearch',
            'https://www.google.co.uk/sorry/',
        )
        for url in urls:
            with self.subTest(url=url):
                self.assertIn('请在已打开浏览器完成验证后重试', WebAutoTool._wa_google_verification_error(url))

    def test_normal_google_search_and_non_google_sorry_routes_are_not_challenges(self):
        urls = (
            'https://www.google.com.hk/search?q=123',
            'https://www.google.com/search?q=sorry',
            'https://example.com/sorry/index',
            'https://notgoogle.com/sorry/index',
        )
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual('', WebAutoTool._wa_google_verification_error(url))

    def test_recaptcha_word_in_a_normal_page_url_is_not_a_challenge(self):
        self.assertEqual('', WebAutoTool._wa_google_verification_error('https://example.com/article/recaptcha-help'))

    def test_container_event_preserves_sample_and_reports_match_count_separately(self):
        tool = WebAutoTool()
        tool._wa_ensure()
        tool._wa_handle_pick_event({
            'type': 'container',
            'selector': 'article.result',
            'sample': 'Alpha result Open Alpha',
            'count': 2,
        })

        state = tool.webauto_pick_state()
        self.assertEqual(state['container'], 'article.result')
        self.assertEqual(state['containerSample'], 'Alpha result Open Alpha')
        self.assertEqual(state['containerCount'], 2)


if __name__ == '__main__':
    unittest.main()

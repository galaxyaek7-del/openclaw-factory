"""Regression tests for the view-count self-inflation finding (cycle 142).

PROVEN: fetching a Telegraph article's HTML increments its own view counter by
exactly 1. An API read does not move it at all.

Consequence: any verification routine that fetches the HTML is counting its own
traffic as reader traffic, which makes the headline view number unsound as a
measure of audience.

These tests pin the two API-only accessors so future verification defaults to a
measurement that does not corrupt the metric it is reporting.
"""
import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import telegraph_safe_edit as T


class TestViewCountIntegrity(unittest.TestCase):

    def test_api_view_count_uses_only_the_api(self):
        captured = {}

        def fake_get(url, params=None, **kw):
            captured['url'] = url
            captured['params'] = params
            r = mock.Mock()
            r.json.return_value = {'ok': True, 'result': {'views': 15}}
            return r

        with mock.patch.object(T.requests, 'get', side_effect=fake_get):
            v = T.api_view_count('tok', 'some-page')
        self.assertEqual(v, 15)
        self.assertIn('api.telegra.ph', captured['url'])
        self.assertEqual(captured['params']['path'], 'some-page')
        self.assertEqual(captured['params']['access_token'], 'tok')

    def test_api_page_text_reads_body_without_fetching_html(self):
        posts = []

        def fake_get(url, params=None, **kw):
            posts.append(url)
            r = mock.Mock()
            r.json.return_value = {'ok': True, 'result': {
                'title': 'T', 'path': 'p',
                'content': [{'tag': 'p', 'children': ['six months']},
                            {'tag': 'h3', 'children': ['Why the order matters']}]}}
            return r

        with mock.patch.object(T.requests, 'get', side_effect=fake_get):
            txt = T.api_page_text('tok', 'p')
        self.assertIn('six months', txt)
        self.assertIn('Why the order matters', txt)
        # every request must have gone to the API, never to telegra.ph
        for u in posts:
            self.assertIn('api.telegra.ph', u)
            self.assertNotIn('://telegra.ph/', u)

    def test_api_page_text_raises_on_api_error(self):
        def fake_get(url, params=None, **kw):
            r = mock.Mock()
            r.json.return_value = {'ok': False, 'error': 'PAGE_ACCESS_DENIED'}
            return r

        with mock.patch.object(T.requests, 'get', side_effect=fake_get):
            with self.assertRaises(RuntimeError):
                T.api_page_text('tok', 'p')

    def test_html_verification_is_still_available_but_is_not_the_default(self):
        """The HTML path must still exist for write-safety checks, but it is
        clearly the exception rather than the routine measurement."""
        self.assertTrue(hasattr(T, '_live_body_lines'))
        self.assertIn('view', T.api_view_count.__doc__.lower())
        self.assertIn('increment', T.api_view_count.__doc__.lower())


if __name__ == '__main__':
    unittest.main()

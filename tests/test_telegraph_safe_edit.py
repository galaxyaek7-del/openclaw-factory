"""Regression tests for the C131 Telegraph destruction bug.

The bug: editPage REPLACES the node list. getPage omits the body unless
return_content=true, so result.get('content') is None. Code doing
(result.get('content') or []) got [], mistook it for an empty page, and wrote
one paragraph over a live article's entire body.

These tests pin the fix. They make NO network calls - read_page and
_live_body_lines are injected, exactly as they must be for this to be testable
without risking real pages.
"""
import json
import os
import sys
import unittest
from unittest import mock
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import telegraph_safe_edit as T


def node(text, tag='p'):
    return {'tag': tag, 'children': [text]}


# 2026-10-22: these tests exercise the mocked live-write path; since
# channels/write_gate.py fails closed by default, they opt in explicitly.
# tests/test_platform_write_gate.py proves the default refusal.
@patch.dict(os.environ, {"FACTORY_LIVE_PUBLISH": "true"})
class TestSafeEditGuards(unittest.TestCase):

    def test_refuses_to_write_when_body_read_is_empty(self):
        """The exact C131 condition: an unread body must abort the write."""
        with mock.patch.object(T, 'read_page',
                               return_value={'path': 'p', 'title': 't', 'nodes': [],
                                             'author_name': 'a', 'url': ''}), \
             mock.patch.object(T.requests, 'post') as post:
            with self.assertRaises(T.UnsafeEdit):
                T.append_paragraph('tok', 'p', 'text')
            post.assert_not_called()

    def test_refuses_when_live_page_has_content_but_read_was_empty(self):
        """A genuinely empty read on a non-empty live page is still a refusal."""
        with mock.patch.object(T, 'read_page',
                               return_value={'path': 'p', 'title': 't', 'nodes': [],
                                             'author_name': 'a', 'url': ''}), \
             mock.patch.object(T, '_live_body_lines', return_value=40), \
             mock.patch.object(T.requests, 'post') as post:
            with self.assertRaises(T.UnsafeEdit):
                T.append_paragraph('tok', 'p', 'text')
            post.assert_not_called()

    def test_read_page_always_requests_return_content(self):
        """If this ever regresses, every read returns None and every write is a wipe."""
        captured = {}

        def fake_get(url, params=None, **kw):
            captured.update(params or {})
            r = mock.Mock()
            r.json.return_value = {'ok': True, 'result': {
                'title': 't', 'content': [node('body')]}}
            return r

        with mock.patch.object(T.requests, 'get', side_effect=fake_get):
            page = T.read_page('tok', 'some-path')
        self.assertEqual(str(captured.get('return_content')).lower(), 'true')
        self.assertEqual(len(page['nodes']), 1)

    def test_read_page_parses_string_content(self):
        def fake_get(url, params=None, **kw):
            r = mock.Mock()
            r.json.return_value = {'ok': True, 'result': {
                'title': 't', 'content': json.dumps([node('a'), node('b')])}}
            return r

        with mock.patch.object(T.requests, 'get', side_effect=fake_get):
            page = T.read_page('tok', 'p')
        self.assertEqual(len(page['nodes']), 2)

    def test_read_page_raises_on_api_error(self):
        def fake_get(url, params=None, **kw):
            r = mock.Mock()
            r.json.return_value = {'ok': False, 'error': 'PAGE_ACCESS_DENIED'}
            return r

        with mock.patch.object(T.requests, 'get', side_effect=fake_get):
            with self.assertRaises(RuntimeError) as cm:
                T.read_page('tok', 'p')
        self.assertIn('PAGE_ACCESS_DENIED', str(cm.exception))

    def test_successful_append_is_a_superset_and_verified(self):
        """A normal append must grow the list and be read back."""
        existing = [node('one'), node('two')]
        grown = existing + [node('added')]
        reads = [{'path': 'p', 'title': 't', 'nodes': existing, 'author_name': 'a', 'url': ''},
                 {'path': 'p', 'title': 't', 'nodes': grown, 'author_name': 'a', 'url': ''}]
        sent = {}

        def fake_post(url, data=None, **kw):
            sent['nodes'] = json.loads(data['content'])
            r = mock.Mock()
            r.json.return_value = {'ok': True, 'result': {'path': 'p'}}
            return r

        with mock.patch.object(T, 'read_page', side_effect=reads), \
             mock.patch.object(T.requests, 'post', side_effect=fake_post), \
             mock.patch('time.sleep'):
            out = T.append_paragraph('tok', 'p', 'added')

        self.assertEqual(len(sent['nodes']), 3)
        self.assertEqual(out['sent_nodes'], 3)
        self.assertEqual(out['readback_nodes'], 3)
        # the previously-read content must survive, not be replaced
        self.assertEqual(sent['nodes'][:2], existing)

    def test_readback_smaller_than_sent_raises(self):
        """A short read-back is treated as failure, not success."""
        reads = [{'path': 'p', 'title': 't', 'nodes': [node('one')], 'author_name': 'a', 'url': ''},
                 {'path': 'p', 'title': 't', 'nodes': [], 'author_name': 'a', 'url': ''}]

        def fake_post(url, data=None, **kw):
            r = mock.Mock()
            r.json.return_value = {'ok': True, 'result': {'path': 'p'}}
            return r

        with mock.patch.object(T, 'read_page', side_effect=reads), \
             mock.patch.object(T.requests, 'post', side_effect=fake_post), \
             mock.patch('time.sleep'):
            with self.assertRaises(T.UnsafeEdit):
                T.append_paragraph('tok', 'p', 'added')

    def test_editpage_failure_is_raised_not_swallowed(self):
        def fake_post(url, data=None, **kw):
            r = mock.Mock()
            r.json.return_value = {'ok': False, 'error': 'PAGE_ACCESS_DENIED'}
            return r

        with mock.patch.object(T, 'read_page',
                               return_value={'path': 'p', 'title': 't',
                                             'nodes': [node('x')],
                                             'author_name': 'a', 'url': ''}), \
             mock.patch.object(T.requests, 'post', side_effect=fake_post):
            with self.assertRaises(RuntimeError) as cm:
                T.append_paragraph('tok', 'p', 'added')
        self.assertIn('PAGE_ACCESS_DENIED', str(cm.exception))


if __name__ == '__main__':
    unittest.main()

"""Tests for P2/P5/P7 fast-path libs. Pure, no network, no repo mutation
outside temp dirs (state files are redirected via module STATE)."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'lib'))
import fileio
import fact_cache
import hash_gate

TMP = tempfile.mkdtemp(prefix='fastpath_')


class TestFileio(unittest.TestCase):
    def test_utf8_roundtrip(self):
        p = os.path.join(TMP, 'a.txt')
        fileio.write_text(p, 'hello wörld — test', 'utf-8')
        text, enc = fileio.read_text(p)
        self.assertEqual(text, 'hello wörld — test')
        self.assertIn(enc, ('utf-8-sig', 'utf-8'))

    def test_utf16_bom_roundtrip(self):
        p = os.path.join(TMP, 'b.html')
        fileio.write_text(p, '<html><head></head></html>', 'utf-16')
        with open(p, 'rb') as fh:
            raw = fh.read()
        self.assertTrue(raw.startswith(b'\xff\xfe'))
        text, enc = fileio.read_text(p)
        self.assertIn('<head>', text)
        self.assertEqual(enc, 'utf-16')

    def test_decode_error_is_explicit(self):
        p = os.path.join(TMP, 'c.bin')
        with open(p, 'wb') as fh:
            fh.write(b'\xff\xfe\x41')
        with self.assertRaises(Exception):
            fileio.read_text(p)


class TestHashGate(unittest.TestCase):
    def setUp(self):
        self.state = os.path.join(TMP, 'hg.json')
        hash_gate.STATE = self.state
        if os.path.exists(self.state):
            os.remove(self.state)
        self.f = os.path.join(TMP, 'watched.txt')
        with open(self.f, 'w', encoding='utf-8') as fh:
            fh.write('v1')

    def test_skip_after_pass(self):
        skip, reason = hash_gate.should_skip('k', [self.f])
        self.assertFalse(skip)
        hash_gate.record('k', [self.f], (), 'PASS')
        skip, reason = hash_gate.should_skip('k', [self.f])
        self.assertTrue(skip)
        self.assertIn('SKIPPED_BY_HASH_GATE', reason)

    def test_change_forces_revalidate(self):
        hash_gate.record('k2', [self.f], (), 'PASS')
        with open(self.f, 'w', encoding='utf-8') as fh:
            fh.write('v2')
        skip, _ = hash_gate.should_skip('k2', [self.f])
        self.assertFalse(skip)

    def test_fail_verdict_never_skips(self):
        hash_gate.record('k3', [self.f], (), 'FAIL')
        skip, _ = hash_gate.should_skip('k3', [self.f])
        self.assertFalse(skip)

    def test_missing_file_never_skips(self):
        skip, _ = hash_gate.should_skip('k4', [os.path.join(TMP, 'nope.txt')])
        self.assertFalse(skip)


class TestFactCache(unittest.TestCase):
    def setUp(self):
        self.state = os.path.join(TMP, 'fc.json')
        fact_cache.STATE = self.state
        if os.path.exists(self.state):
            os.remove(self.state)

    def test_remember_recall(self):
        fact_cache.remember('fact1', 42, 'unit-test', state_hash='abc', ttl_secs=60)
        hit, val = fact_cache.recall('fact1', state_hash='abc')
        self.assertTrue(hit)
        self.assertEqual(val, 42)

    def test_state_change_miss(self):
        fact_cache.remember('fact2', 1, 'unit-test', state_hash='abc', ttl_secs=60)
        hit, _ = fact_cache.recall('fact2', state_hash='xyz')
        self.assertFalse(hit)

    def test_expiry_miss(self):
        fact_cache.remember('fact3', 1, 'unit-test', ttl_secs=-1)
        hit, _ = fact_cache.recall('fact3')
        self.assertFalse(hit)


if __name__ == '__main__':
    unittest.main()

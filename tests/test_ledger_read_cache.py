"""Regression tests for the append-only ledger read cache.

Real defect found live 2026-10-03 while profiling
gfos.if_i_were_the_ceo_report(): both readers re-opened and re-parsed the whole
ledger on every single call. The 13.19MB / 2,309-line decisions ledger was read
and parsed 499 times inside one report -- 784,489 json.loads() calls, 90.2s of
the report's 126.7s -- all re-deriving byte-identical results, which is what
pushed that endpoint past its own declared timeout and made it return 500.

These tests pin the two properties that matter: a warm read is served from
cache, and a mutation is NEVER served stale.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from decision_engine import store as decision_store  # noqa: E402
from golden_hunter import repositioning  # noqa: E402


class _LedgerCacheContract:
    """Shared assertions, run against both ledger readers."""

    def module(self):
        raise NotImplementedError

    def make_reader(self):
        raise NotImplementedError

    def invalidate(self, path):
        raise NotImplementedError

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "ledger.jsonl")
        self.invalidate(self.path)

    def count_opens(self, fn):
        """Real count of how many times `fn` actually opened the ledger."""
        target = str(Path(self.path))
        real_open = open
        opens = []

        def counting_open(file, *a, **kw):
            try:
                if str(Path(file)) == target:
                    opens.append(1)
            except Exception:
                pass
            return real_open(file, *a, **kw)

        with mock.patch("builtins.open", counting_open):
            fn()
        return len(opens)

    def test_append_is_visible_to_the_very_next_read(self):
        self.make_reader().append_decision(
            {"niche": "A", "decided_at": "2026-01-01", "status": "DEFERRED"}, self.path
        )
        first = list(self.make_reader().read_decisions(self.path))
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0]["status"], "DEFERRED")

        self.make_reader().append_decision(
            {"niche": "A", "decided_at": "2026-02-01", "status": "ACCEPTED"}, self.path
        )
        second = list(self.make_reader().read_decisions(self.path))
        self.assertEqual(len(second), 2, "an append must never be served from a stale cache")
        self.assertEqual(second[-1]["status"], "ACCEPTED")

    def test_warm_read_equals_cold_read(self):
        self.make_reader().append_decision(
            {"niche": "B", "decided_at": "2026-01-01", "status": "ACCEPTED"}, self.path
        )
        cold = list(self.make_reader().read_decisions(self.path))
        warm = list(self.make_reader().read_decisions(self.path))
        self.assertEqual(cold, warm)

    def test_repeated_reads_do_not_reparse_the_file(self):
        """The expensive part is the full JSON parse, and it must not repeat."""
        reader = self.make_reader()
        for i in range(25):
            reader.append_decision(
                {"niche": "N%d" % i, "decided_at": "2026-01-01", "status": "DEFERRED"},
                self.path,
            )
        list(reader.read_decisions(self.path))  # warm the cache
        cache_key = str(Path(self.path))
        module = self.module()
        self.assertIn(cache_key, module._READ_CACHE, "a warm read must be cached")
        stamp_before = module._READ_CACHE[cache_key][0]

        opens = self.count_opens(lambda: [list(reader.read_decisions(self.path)) for _ in range(50)])
        self.assertEqual(opens, 0, "50 warm reads must not reopen or re-parse the file")
        self.assertEqual(module._READ_CACHE[cache_key][0], stamp_before)

    def test_same_length_rewrite_requires_explicit_invalidation(self):
        """Documents the one case the stamp cannot detect on its own.

        Both ledgers are append-only by contract, so a real write always grows
        the file and st_size changes -- which is what the stamp keys on. A
        same-length IN-PLACE rewrite is therefore a contract violation, and the
        documented escape hatch is the explicit _invalidate_read_cache() call,
        which is what this asserts. A head+tail checksum was implemented to
        detect it implicitly and then removed: it cost a file open per read and
        slowed the API contract step from 269s to 1155s, which is not worth
        paying for a mutation the data forbids.
        """
        reader = self.make_reader()
        path = Path(self.path)
        path.write_text('{"niche":"AAA","decided_at":"2026-01-01","status":"DEFERRED"}\n',
                        encoding="utf-8")
        self.invalidate(self.path)
        self.assertEqual(list(reader.read_decisions(self.path))[0]["niche"], "AAA")

        # Same byte length, different content, no invalidation -> not detected.
        path.write_text('{"niche":"BBB","decided_at":"2026-01-01","status":"DEFERRED"}\n',
                        encoding="utf-8")
        # An explicit invalidation is always sufficient, which is the contract.
        self.invalidate(self.path)
        self.assertEqual(list(reader.read_decisions(self.path))[0]["niche"], "BBB")

    def test_a_cold_read_really_does_open_the_file(self):
        reader = self.make_reader()
        reader.append_decision(
            {"niche": "cold", "decided_at": "2026-01-01", "status": "DEFERRED"}, self.path
        )
        self.invalidate(self.path)
        opens = self.count_opens(lambda: list(reader.read_decisions(self.path)))
        self.assertEqual(opens, 1, "a cold read must actually read the ledger exactly once")

    def test_out_of_band_write_is_never_served_stale(self):
        reader = self.make_reader()
        reader.append_decision(
            {"niche": "C", "decided_at": "2026-01-01", "status": "DEFERRED"}, self.path
        )
        self.assertEqual(len(list(reader.read_decisions(self.path))), 1)

        # Written directly to the file, NOT via append_decision -- the cache
        # must notice on (mtime_ns, size) alone.
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"niche": "D", "decided_at": "2026-03-01", "status": "ACCEPTED"}) + "\n")
        self.assertEqual(
            len(list(reader.read_decisions(self.path))), 2, "out-of-band append must be visible"
        )

    def test_corrupt_line_is_still_skipped_not_fatal(self):
        reader = self.make_reader()
        reader.append_decision(
            {"niche": "E", "decided_at": "2026-01-01", "status": "DEFERRED"}, self.path
        )
        with open(self.path, "a", encoding="utf-8") as f:
            f.write("this is not json\n")
        records = list(reader.read_decisions(self.path))
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["niche"], "E")

    def test_missing_file_reads_as_empty_not_an_error(self):
        missing = os.path.join(self.dir, "nope.jsonl")
        self.assertEqual(list(self.make_reader().read_decisions(missing)), [])


class TestDecisionStoreLedgerCache(_LedgerCacheContract, unittest.TestCase):
    def module(self):
        return decision_store

    def make_reader(self):
        return decision_store

    def invalidate(self, path):
        decision_store._invalidate_read_cache(path)


class TestRepositioningLedgerCache(_LedgerCacheContract, unittest.TestCase):
    """Same two properties, against golden_hunter/repositioning.py's own
    append-only attempt ledger (record_attempt / read_attempts)."""

    def module(self):
        return repositioning

    def make_reader(self):
        return _RepositioningReader()

    def invalidate(self, path):
        repositioning._invalidate_read_cache(path)


class _RepositioningReader:
    """Adapts repositioning's record_attempt/read_attempts to the shared
    contract's append_decision/read_decisions shape. Deliberately a real
    adapter over the real module functions -- not a reimplementation."""

    @staticmethod
    def append_decision(record, path):
        return repositioning.record_attempt(record, path)

    @staticmethod
    def read_decisions(path):
        return repositioning.read_attempts(path)


if __name__ == "__main__":
    unittest.main()
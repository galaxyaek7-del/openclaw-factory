"""Tests for scripts/readiness_certificate.py (ADR-011).

Runs with stdlib unittest (no test framework configured in this project —
see CLAUDE.md). Every test uses fabricated data or temp files; none of them
read or write the real data/golden_hunter_events.jsonl, factory_loop.log,
golden_opportunities.json, market_hunter_runs.log, NEEDS_ATTENTION.md, or
data/readiness_history.jsonl — except one deliberate real-data sanity check
that only reads (never writes) the actual repo files, confirming the script
doesn't crash against real production data.

    python -m unittest tests.test_readiness_certificate -v
"""

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from scripts import readiness_certificate as rc


def _write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')


def _iso_utc(dt):
    return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


class TestParseTimestamp(unittest.TestCase):
    def test_utc_z_suffix(self):
        dt = rc._parse_timestamp('2026-07-11T18:15:22.860Z')
        self.assertEqual(dt.tzinfo, timezone.utc)
        self.assertEqual(dt.year, 2026)

    def test_naive_local(self):
        dt = rc._parse_timestamp('2026-07-11T15:34:28.676953')
        self.assertIsNotNone(dt)
        self.assertEqual(dt.tzinfo, timezone.utc)  # normalized

    def test_invalid_returns_none(self):
        self.assertIsNone(rc._parse_timestamp('not-a-date'))
        self.assertIsNone(rc._parse_timestamp(None))
        self.assertIsNone(rc._parse_timestamp(123))


class TestLoadJsonl(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_missing_file(self):
        self.assertEqual(rc._load_jsonl(self.tmp / 'nope.jsonl'), [])

    def test_malformed_line_skipped(self):
        p = self.tmp / 'mixed.jsonl'
        p.write_text('{"a": 1}\nnot json\n{"a": 2}\n', encoding='utf-8')
        records = rc._load_jsonl(p)
        self.assertEqual(len(records), 2)


class TestCheckContinuousOperation(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.log_path = self.tmp / 'factory_loop.log'

    def test_no_ticks_pending(self):
        result = rc.check_continuous_operation(datetime.now(timezone.utc), log_path=self.log_path)
        self.assertEqual(result['status'], 'PENDING')

    def test_short_streak_pending(self):
        now = datetime.now(timezone.utc)
        _write_jsonl(self.log_path, [
            {'timestamp': _iso_utc(now - timedelta(minutes=20)), 'actions': []},
            {'timestamp': _iso_utc(now - timedelta(minutes=10)), 'actions': []},
            {'timestamp': _iso_utc(now), 'actions': []},
        ])
        result = rc.check_continuous_operation(now, log_path=self.log_path)
        self.assertEqual(result['status'], 'PENDING')
        self.assertEqual(result['evidence']['ticks_in_streak'], 3)

    def test_full_48h_unbroken_streak_passes(self):
        now = datetime.now(timezone.utc)
        ticks = []
        t = now - timedelta(hours=49)
        while t <= now:
            ticks.append({'timestamp': _iso_utc(t), 'actions': []})
            t += timedelta(minutes=10)
        _write_jsonl(self.log_path, ticks)
        result = rc.check_continuous_operation(now, log_path=self.log_path)
        self.assertEqual(result['status'], 'PASS')
        self.assertGreaterEqual(result['evidence']['span_hours'], 48)

    def test_old_manual_gap_before_continuous_run_does_not_count_as_a_crash(self):
        # A manual --once test 10 hours ago, then a truly continuous run
        # starting 1 hour ago -> the streak must start at the continuous
        # run, not be poisoned by the old, legitimate, isolated test tick.
        now = datetime.now(timezone.utc)
        ticks = [{'timestamp': _iso_utc(now - timedelta(hours=10)), 'actions': []}]
        t = now - timedelta(hours=1)
        while t <= now:
            ticks.append({'timestamp': _iso_utc(t), 'actions': []})
            t += timedelta(minutes=10)
        _write_jsonl(self.log_path, ticks)
        result = rc.check_continuous_operation(now, log_path=self.log_path)
        self.assertLess(result['evidence']['span_hours'], 2)
        self.assertEqual(result['status'], 'PENDING')

    def test_action_error_breaks_the_streak(self):
        now = datetime.now(timezone.utc)
        ticks = [
            {'timestamp': _iso_utc(now - timedelta(minutes=30)), 'actions': [{'step': 'tick', 'action': 'error', 'detail': 'boom'}]},
            {'timestamp': _iso_utc(now - timedelta(minutes=20)), 'actions': []},
            {'timestamp': _iso_utc(now - timedelta(minutes=10)), 'actions': []},
            {'timestamp': _iso_utc(now), 'actions': []},
        ]
        _write_jsonl(self.log_path, ticks)
        result = rc.check_continuous_operation(now, log_path=self.log_path)
        self.assertEqual(result['evidence']['ticks_in_streak'], 3)  # the error tick itself is excluded


class TestCheckDistinctNiches(unittest.TestCase):
    def test_below_threshold_pending(self):
        events = [{'action': 'attempted', 'niche': 'a'}, {'action': 'attempted', 'niche': 'a'}]
        result = rc.check_distinct_niches(events)
        self.assertEqual(result['status'], 'PENDING')
        self.assertEqual(result['evidence']['count'], 1)

    def test_meets_threshold_passes(self):
        events = [{'action': 'attempted', 'niche': n} for n in ['a', 'b', 'c']]
        result = rc.check_distinct_niches(events)
        self.assertEqual(result['status'], 'PASS')

    def test_case_and_whitespace_normalized(self):
        events = [
            {'action': 'attempted', 'niche': 'Niche A'},
            {'action': 'attempted', 'niche': '  niche a  '},
            {'action': 'attempted', 'niche': 'Niche B'},
        ]
        result = rc.check_distinct_niches(events)
        self.assertEqual(result['evidence']['count'], 2)

    def test_skipped_events_ignored(self):
        events = [{'action': 'skipped', 'reason': 'stale'}, {'action': 'attempted', 'niche': 'a'}]
        result = rc.check_distinct_niches(events)
        self.assertEqual(result['evidence']['count'], 1)


class TestCheckNeedsAttentionFree(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.log_path = self.tmp / 'factory_loop.log'
        self.attention_file = self.tmp / 'NEEDS_ATTENTION.md'

    def test_clean_history_passes(self):
        now = datetime.now(timezone.utc)
        events = [{'action': 'attempted', 'timestamp': _iso_utc(now), 'brief': {'_price_source': 'butter_price'}}]
        result = rc.check_needs_attention_free(now, events, log_path=self.log_path, attention_file=self.attention_file)
        self.assertEqual(result['status'], 'PASS')

    def test_currently_flagged_fails(self):
        now = datetime.now(timezone.utc)
        self.attention_file.write_text('x', encoding='utf-8')
        result = rc.check_needs_attention_free(now, [], log_path=self.log_path, attention_file=self.attention_file)
        self.assertEqual(result['status'], 'FAIL')
        self.assertTrue(result['evidence']['currently_flagged'])

    def test_stale_streak_in_window_fails(self):
        now = datetime.now(timezone.utc)
        events = [
            {'action': 'skipped', 'reason': 'stale', 'timestamp': _iso_utc(now - timedelta(minutes=20))},
            {'action': 'skipped', 'reason': 'missing_or_unreadable', 'timestamp': _iso_utc(now - timedelta(minutes=10))},
            {'action': 'skipped', 'reason': 'stale', 'timestamp': _iso_utc(now)},
        ]
        result = rc.check_needs_attention_free(now, events, log_path=self.log_path, attention_file=self.attention_file)
        self.assertEqual(result['status'], 'FAIL')
        self.assertTrue(result['evidence']['stale_streak_found'])

    def test_two_stale_not_three_passes(self):
        now = datetime.now(timezone.utc)
        events = [
            {'action': 'skipped', 'reason': 'stale', 'timestamp': _iso_utc(now - timedelta(minutes=10))},
            {'action': 'skipped', 'reason': 'stale', 'timestamp': _iso_utc(now)},
        ]
        result = rc.check_needs_attention_free(now, events, log_path=self.log_path, attention_file=self.attention_file)
        self.assertEqual(result['status'], 'PASS')

    def test_fallback_streak_in_window_fails(self):
        now = datetime.now(timezone.utc)
        events = [
            {'action': 'attempted', 'timestamp': _iso_utc(now - timedelta(minutes=20)), 'brief': {'_price_source': 'fallback_floor_clamped'}},
            {'action': 'attempted', 'timestamp': _iso_utc(now - timedelta(minutes=10)), 'brief': {'_price_source': 'fallback_floor_clamped'}},
            {'action': 'attempted', 'timestamp': _iso_utc(now), 'brief': {'_price_source': 'fallback_floor_clamped'}},
        ]
        result = rc.check_needs_attention_free(now, events, log_path=self.log_path, attention_file=self.attention_file)
        self.assertEqual(result['status'], 'FAIL')
        self.assertTrue(result['evidence']['fallback_streak_found'])

    def test_events_outside_window_ignored(self):
        now = datetime.now(timezone.utc)
        old = now - timedelta(hours=48)
        events = [
            {'action': 'skipped', 'reason': 'stale', 'timestamp': _iso_utc(old)},
            {'action': 'skipped', 'reason': 'stale', 'timestamp': _iso_utc(old + timedelta(minutes=1))},
            {'action': 'skipped', 'reason': 'stale', 'timestamp': _iso_utc(old + timedelta(minutes=2))},
        ]
        result = rc.check_needs_attention_free(now, events, log_path=self.log_path, attention_file=self.attention_file, window_hours=24)
        self.assertEqual(result['status'], 'PASS')

    def test_failed_tick_in_log_fails(self):
        now = datetime.now(timezone.utc)
        _write_jsonl(self.log_path, [
            {'timestamp': _iso_utc(now), 'actions': [{'step': 'golden_hunter_bridge', 'action': 'failed', 'detail': 'boom'}]},
        ])
        result = rc.check_needs_attention_free(now, [], log_path=self.log_path, attention_file=self.attention_file)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(len(result['evidence']['failed_ticks']), 1)


class TestCheckConstitutionalPricing(unittest.TestCase):
    def test_no_attempts_pending(self):
        result = rc.check_constitutional_pricing(datetime.now(timezone.utc), [])
        self.assertEqual(result['status'], 'PENDING')

    def test_all_clean_recent_passes(self):
        now = datetime.now(timezone.utc)
        events = [
            {'action': 'attempted', 'timestamp': _iso_utc(now), 'brief': {'price': 68, '_price_source': 'butter_price'}},
            {'action': 'attempted', 'timestamp': _iso_utc(now), 'brief': {'price': 45, '_price_source': 'butter_price'}},
        ]
        result = rc.check_constitutional_pricing(now, events)
        self.assertEqual(result['status'], 'PASS')

    def test_recent_sub_floor_price_fails(self):
        now = datetime.now(timezone.utc)
        events = [{'action': 'attempted', 'timestamp': _iso_utc(now), 'brief': {'price': 19, '_price_source': None}}]
        result = rc.check_constitutional_pricing(now, events)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(len(result['evidence']['violations']), 1)

    def test_recent_fallback_source_fails_even_if_price_ge_30(self):
        now = datetime.now(timezone.utc)
        events = [{'action': 'attempted', 'timestamp': _iso_utc(now), 'brief': {'price': 30, '_price_source': 'fallback_floor_clamped'}}]
        result = rc.check_constitutional_pricing(now, events)
        self.assertEqual(result['status'], 'FAIL')

    def test_old_violation_outside_window_does_not_block_pass(self):
        # The exact real-world scenario this test mirrors: a bug existed,
        # was fixed (ADR-010), and enough time has now passed that the old
        # bad entries fall outside the observation window — the criterion
        # must recover, not stay FAIL forever, while still reporting the
        # old violation honestly in evidence.
        now = datetime.now(timezone.utc)
        old_bad = now - timedelta(hours=30)
        events = [
            {'action': 'attempted', 'timestamp': _iso_utc(old_bad), 'niche': 'x', 'brief': {'price': 19, '_price_source': None}},
            {'action': 'attempted', 'timestamp': _iso_utc(now), 'brief': {'price': 68, '_price_source': 'butter_price'}},
        ]
        result = rc.check_constitutional_pricing(now, events, window_hours=24)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(len(result['evidence']['historical_violations_outside_window']), 1)

    def test_no_recent_attempts_but_old_history_exists_is_pending_not_pass(self):
        now = datetime.now(timezone.utc)
        old_bad = now - timedelta(hours=30)
        events = [{'action': 'attempted', 'timestamp': _iso_utc(old_bad), 'brief': {'price': 68, '_price_source': 'butter_price'}}]
        result = rc.check_constitutional_pricing(now, events, window_hours=24)
        self.assertEqual(result['status'], 'PENDING')


class TestCheckFreshDiscovery(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.golden_path = self.tmp / 'golden_opportunities.json'
        self.hunter_log = self.tmp / 'market_hunter_runs.log'

    def test_missing_golden_file_fails(self):
        now = datetime.now(timezone.utc)
        result = rc.check_fresh_discovery(now, golden_json_path=self.golden_path, hunter_log_path=self.hunter_log)
        self.assertEqual(result['status'], 'FAIL')

    def test_fresh_and_regular_passes(self):
        now = datetime.now(timezone.utc)
        self.golden_path.write_text(json.dumps({'generated_at': _iso_utc(now - timedelta(hours=2))}), encoding='utf-8')
        _write_jsonl(self.hunter_log, [
            {'timestamp': _iso_utc(now - timedelta(hours=30))},
            {'timestamp': _iso_utc(now - timedelta(hours=6))},
        ])
        result = rc.check_fresh_discovery(now, golden_json_path=self.golden_path, hunter_log_path=self.hunter_log)
        self.assertEqual(result['status'], 'PASS')

    def test_stale_generated_at_pending(self):
        now = datetime.now(timezone.utc)
        self.golden_path.write_text(json.dumps({'generated_at': _iso_utc(now - timedelta(hours=30))}), encoding='utf-8')
        _write_jsonl(self.hunter_log, [{'timestamp': _iso_utc(now - timedelta(hours=30))}])
        result = rc.check_fresh_discovery(now, golden_json_path=self.golden_path, hunter_log_path=self.hunter_log)
        self.assertEqual(result['status'], 'PENDING')


class TestBuildCertificateIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.events_path = self.tmp / 'golden_hunter_events.jsonl'
        self.log_path = self.tmp / 'factory_loop.log'
        self.golden_path = self.tmp / 'golden_opportunities.json'
        self.hunter_log = self.tmp / 'market_hunter_runs.log'
        self.attention_file = self.tmp / 'NEEDS_ATTENTION.md'

    def _build(self, now):
        return rc.build_certificate(
            now=now, events_path=self.events_path, log_path=self.log_path,
            golden_json_path=self.golden_path, hunter_log_path=self.hunter_log,
            attention_file=self.attention_file,
        )

    def test_all_healthy_yields_ready(self):
        now = datetime.now(timezone.utc)
        ticks = []
        t = now - timedelta(hours=49)
        while t <= now:
            ticks.append({'timestamp': _iso_utc(t), 'actions': []})
            t += timedelta(minutes=10)
        _write_jsonl(self.log_path, ticks)

        events = []
        et = now - timedelta(hours=40)
        for niche in ['a', 'b', 'c']:
            events.append({'action': 'attempted', 'dry_run': True, 'niche': niche,
                            'timestamp': _iso_utc(et), 'brief': {'price': 45, '_price_source': 'butter_price'}})
            et += timedelta(hours=10)
        _write_jsonl(self.events_path, events)

        self.golden_path.write_text(json.dumps({'generated_at': _iso_utc(now - timedelta(hours=2))}), encoding='utf-8')
        _write_jsonl(self.hunter_log, [
            {'timestamp': _iso_utc(now - timedelta(hours=30))},
            {'timestamp': _iso_utc(now - timedelta(hours=6))},
        ])

        cert = self._build(now)
        self.assertEqual(cert['verdict'], 'READY')
        self.assertIsNone(cert['eta_estimate'])

    def test_one_failure_yields_blocked_even_if_others_pass(self):
        now = datetime.now(timezone.utc)
        self.attention_file.write_text('x', encoding='utf-8')  # forces needs_attention FAIL
        cert = self._build(now)
        self.assertEqual(cert['verdict'], 'BLOCKED')

    def test_fresh_start_yields_not_ready_yet_with_eta(self):
        # "Fresh start" = not enough time/data yet, but nothing is actively
        # broken — so golden_opportunities.json must at least exist (even if
        # stale), otherwise fresh_discovery_regular correctly FAILs (a
        # missing required file is a real problem, not just "needs more
        # time") and the verdict is BLOCKED, not NOT_READY_YET. Covered
        # separately by TestCheckFreshDiscovery.test_missing_golden_file_fails.
        now = datetime.now(timezone.utc)
        self.golden_path.write_text(json.dumps({'generated_at': _iso_utc(now - timedelta(hours=1))}), encoding='utf-8')
        cert = self._build(now)
        self.assertEqual(cert['verdict'], 'NOT_READY_YET')
        self.assertIsNotNone(cert['eta_estimate'])

    def test_certificate_has_all_five_checks(self):
        now = datetime.now(timezone.utc)
        cert = self._build(now)
        names = {c['name'] for c in cert['checks']}
        self.assertEqual(names, {
            'continuous_operation_48h', 'distinct_niches_ge_3', 'needs_attention_free_24h',
            'constitutional_pricing', 'fresh_discovery_regular',
        })


class TestAppendReadinessHistory(unittest.TestCase):
    def test_appends_not_overwrites(self):
        tmp = Path(tempfile.mkdtemp()) / 'readiness_history.jsonl'
        cert1 = {'timestamp': 't1', 'verdict': 'NOT_READY_YET', 'checks': [{'name': 'a', 'status': 'PENDING'}], 'eta_estimate': None}
        cert2 = {'timestamp': 't2', 'verdict': 'READY', 'checks': [{'name': 'a', 'status': 'PASS'}], 'eta_estimate': None}
        rc.append_readiness_history(cert1, history_path=tmp)
        rc.append_readiness_history(cert2, history_path=tmp)
        lines = tmp.read_text(encoding='utf-8').strip().split('\n')
        self.assertEqual(len(lines), 2)
        self.assertEqual(json.loads(lines[0])['verdict'], 'NOT_READY_YET')
        self.assertEqual(json.loads(lines[1])['verdict'], 'READY')

    def test_missing_dir_created(self):
        tmp = Path(tempfile.mkdtemp()) / 'nested' / 'dir' / 'readiness_history.jsonl'
        cert = {'timestamp': 't1', 'verdict': 'READY', 'checks': [], 'eta_estimate': None}
        rc.append_readiness_history(cert, history_path=tmp)
        self.assertTrue(tmp.exists())


class TestRealDataSanity(unittest.TestCase):
    """Read-only against the ACTUAL repo files — confirms the script never
    crashes against real production data. Never writes anything (does not
    call append_readiness_history with the real history path)."""

    def test_build_certificate_against_real_files_does_not_crash(self):
        cert = rc.build_certificate()
        self.assertIn(cert['verdict'], ('READY', 'NOT_READY_YET', 'BLOCKED'))
        self.assertEqual(len(cert['checks']), 5)
        for c in cert['checks']:
            self.assertIn(c['status'], ('PASS', 'FAIL', 'PENDING'))

    def test_format_report_against_real_certificate_does_not_crash(self):
        cert = rc.build_certificate()
        report = rc.format_report(cert)
        self.assertIn('شهادة الجاهزية', report)


if __name__ == '__main__':
    unittest.main()

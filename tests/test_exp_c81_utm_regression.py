"""EXP-C81-001 UTM + distributor quality-gate regression tests.

Covers the two defects repaired 2026-10-15 (MASTER RECOVERY directive):

1. `fgruzn` experiment links in customer_site/products.html must carry a
   complete, well-formed UTM triple (source/medium/campaign) with the
   product slug intact — verified by parsing real URL query bounds
   (urllib.parse), not by surface text search. The referrer ids the old
   `?ref=` links carried (c89_start_here / c99_catalog) are preserved as
   utm_campaign values, so no attribution granularity is lost.
2. distributor.py's central Quality Gate wiring: an injected deny blocks
   every arm before publish and is recorded with
   protection_decision="quality_gate_blocked"; the unconfigured default
   keeps the exact pre-gate behavior pinned by tests/test_distributor.py
   (sound tracked tests are never rewritten to fit an implementation).
3. channels/ledger.py's additive `quality_gate` kwarg: omitted it leaves
   the original event shape byte-identical; given it is recorded verbatim.

Temp paths only — never production ledgers, never network, never publish.

    python -m unittest discover -s tests -p "test_exp_c81_utm_regression.py" -v
"""

import html
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock
from urllib.parse import urlparse, parse_qs

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import distributor
from channels import ledger, registry
from channels.base_arm import PublishResult
from schemas.product import Product

PRODUCTS_HTML = _FACTORY_ROOT / "customer_site" / "products.html"
FG_SLUG = "fgruzn"
REQUIRED_UTM = ("utm_source", "utm_medium", "utm_campaign")
# Referrer ids the pre-fix ?ref= links carried — must survive as campaigns.
PRESERVED_CAMPAIGNS = {"c89_start_here", "c99_catalog"}


def _temp_path(suffix=".jsonl"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


def _fgruzn_hrefs():
    import re
    text = PRODUCTS_HTML.read_text(encoding="utf-8")
    text = html.unescape(text)
    return re.findall(r'href="(https://aekraft\.gumroad\.com/l/fgruzn\?[^"]+)"', text)


def _fake_product(source_id="PROD-utm-reg-1"):
    return Product(
        title="t", subtitle="", description="d", price_usd=29.0,
        file_path="/fake/path.pdf", cover_path=None, tags=[],
        language="en", source_id=source_id, raw_price_hint=29.0,
        needs_pricing=False, price_source="profit_raw",
    )


def _deny_gate(product, arm_name=None, **kwargs):
    return {
        "allowed": False, "source_id": product.source_id,
        "gate1": {"passed": False, "code": "REVIEW"},
        "gate2": {"passed": False, "decision": None, "status": "MISSING"},
        "blocked_by": "gate1",
        "reason": "regression probe denial",
    }


class TestExpC81UtmLinks(unittest.TestCase):
    def test_product_slug_never_replaced(self):
        hrefs = _fgruzn_hrefs()
        self.assertGreaterEqual(len(hrefs), 2,
                                "expected at least the 2 experiment links")
        for href in hrefs:
            self.assertIn("/l/%s?" % FG_SLUG, href)

    def test_every_experiment_link_carries_full_utm_triple(self):
        for href in _fgruzn_hrefs():
            parsed = urlparse(href)
            self.assertEqual(parsed.query.count("?"), 0,
                             "repeated ? in %r" % href)
            qs = parse_qs(parsed.query, keep_blank_values=True)
            for key in REQUIRED_UTM:
                self.assertIn(key, qs, "%s missing in %r" % (key, href))
                self.assertEqual(len(qs[key]), 1,
                                 "duplicated %s in %r" % (key, href))
                self.assertTrue(qs[key][0],
                                "blank %s in %r" % (key, href))

    def test_no_legacy_ref_links_remain(self):
        for href in _fgruzn_hrefs():
            qs = parse_qs(urlparse(href).query)
            self.assertNotIn("ref", qs)
            self.assertNotIn("referrer", qs)

    def test_referrer_granularity_preserved_as_campaign(self):
        campaigns = set()
        for href in _fgruzn_hrefs():
            qs = parse_qs(urlparse(href).query)
            campaigns.update(qs.get("utm_campaign", []))
        self.assertTrue(PRESERVED_CAMPAIGNS <= campaigns,
                        "lost referrer ids: %s" % (PRESERVED_CAMPAIGNS - campaigns))


class TestDistributorGateRegression(unittest.TestCase):
    def setUp(self):
        self._saved = registry.all_arms()
        registry.clear()
        self.ledger = _temp_path(".jsonl")
        # Isolated protection clock: the shared default state file is
        # mutated by parallel sessions (publish spacing/caps), which would
        # make this test's outcome depend on their timing. Pin the variable
        # under test (gate behavior) by isolating the unrelated one.
        self.protection = _temp_path(".json")

    def tearDown(self):
        registry.clear()
        for a in self._saved:
            registry.register(a)
        for p in (self.ledger, self.protection):
            if os.path.exists(p):
                os.remove(p)

    def _stub(self):
        arm = MagicMock()
        arm.name = "gumroad"
        arm.supports.return_value = True
        arm.publish.return_value = PublishResult(
            ok=True, platform="gumroad", product_id="p1",
            url="http://x", error=None, dry_run=False)
        registry.register(arm)
        return arm

    def test_injected_deny_blocks_before_publish_and_records_gate(self):
        arm = self._stub()
        outcomes = distributor.distribute(
            _fake_product(), dry_run=False, ledger_path=self.ledger,
            quality_gate=_deny_gate)
        arm.publish.assert_not_called()
        self.assertFalse(outcomes[0]["attempted"])
        self.assertIsNone(outcomes[0]["ok"])
        self.assertIn("Quality Gate", outcomes[0]["skip_reason"])
        events = list(ledger.read_events(
            event_type="publish_attempt", ledger_path=self.ledger))
        self.assertEqual(len(events), 1)
        self.assertFalse(events[0]["ok"])
        self.assertEqual(events[0]["protection_decision"],
                         "quality_gate_blocked")
        self.assertFalse(events[0]["quality_gate"]["allowed"])

    def test_unconfigured_default_keeps_pregate_behavior(self):
        arm = self._stub()
        outcomes = distributor.distribute(
            _fake_product(), dry_run=False, ledger_path=self.ledger,
            protection_state_path=self.protection)
        self.assertTrue(outcomes[0]["attempted"])
        self.assertEqual(arm.publish.call_count, 1)

    def test_dry_run_never_consults_gate(self):
        arm = self._stub()
        outcomes = distributor.distribute(
            _fake_product(), dry_run=True, ledger_path=self.ledger,
            quality_gate=_deny_gate)
        self.assertTrue(outcomes[0]["attempted"])
        self.assertEqual(arm.publish.call_count, 1)

    def test_legacy_single_arg_resolver_is_called_tolerantly(self):        # A resolver predating the 4-kwarg contract (accepts only the
        # product) must still have its verdict enforced verbatim — never
        # fail-closed on a TypeError from extra kwargs, never bypassed.
        arm = self._stub()
        allow = {"allowed": True, "source_id": "PROD-utm-reg-1",
                 "blocked_by": None, "reason": "legacy allow"}
        outcomes = distributor.distribute(
            _fake_product(), dry_run=False, ledger_path=self.ledger,
            protection_state_path=self.protection,
            quality_gate=lambda product: allow)
        self.assertTrue(outcomes[0]["attempted"])
        self.assertEqual(arm.publish.call_count, 1)
        registry.clear()
        deny_arm = self._stub()
        outcomes = distributor.distribute(
            _fake_product("PROD-utm-reg-2"), dry_run=False,
            ledger_path=self.ledger,
            protection_state_path=self.protection,
            quality_gate=lambda product: dict(allow, allowed=False,
                                              reason="legacy deny"))
        deny_arm.publish.assert_not_called()
        self.assertFalse(outcomes[0]["attempted"])
        self.assertIsNone(outcomes[0]["ok"])

    def test_none_verdict_blocks_fail_closed(self):
        # A resolver returning None (misconfigured gate) must BLOCK, never
        # silently disable the gate: None is "no usable verdict", and the
        # sentinel for "not evaluated" must never collide with it.
        arm = self._stub()
        outcomes = distributor.distribute(
            _fake_product("PROD-utm-reg-3"), dry_run=False,
            ledger_path=self.ledger,
            protection_state_path=self.protection,
            quality_gate=lambda product: None)
        arm.publish.assert_not_called()
        self.assertFalse(outcomes[0]["attempted"])
        self.assertIsNone(outcomes[0]["ok"])
        self.assertIn("Quality Gate", outcomes[0]["skip_reason"])


class TestPublishSpacingBoundaries(unittest.TestCase):
    """Boundary pinning for publish_protection.py's minimum publish
    spacing (QUALITY ESCALATION V2, Phase 3). All evaluation is
    deterministic via the injectable `now` — no sleeps, no shared clock.

    Findings pinned here: UTC-aware arithmetic throughout (DST-immune);
    missing/corrupt timestamps skip the check (pre-existing precedent);
    tz-naive timestamps no longer propagate TypeError (2026-10-15 fix —
    same lenient-corrupt precedent, never a pass upgrade); the exact
    boundary (elapsed == minimum) ALLOWS; restart-safe (state is on disk,
    re-read every call); cross-process TOCTOU documented as a known,
    unexercised limitation (no concurrent real-publish path exists —
    factory_loop lock is the existing guard), not rebuilt here.
    """

    def setUp(self):
        self.state = _temp_path(".json")
        self.breaker = _temp_path(".json")

    def tearDown(self):
        for p in (self.state, self.breaker):
            if os.path.exists(p):
                os.remove(p)

    def _check(self, last_publish_at, now):
        import json as _json
        from datetime import datetime, timezone, timedelta
        from channels import publish_protection as pp
        gap = pp._profile("gumroad")["min_cooldown_minutes"]
        state = {"arms": {"gumroad": {
            "publishes_today": 0, "day_bucket": now.strftime("%Y-%m-%d"),
            "publishes_this_hour": 0, "hour_bucket": now.strftime("%Y-%m-%dT%H"),
            "cooldown_until": None, "consecutive_failures": 0,
            "last_publish_at": last_publish_at,
            "has_ever_published_successfully": True,
            "first_publish_approved": True,
            "elevated_risk_approved_at": now.isoformat()}},
            "global": {"emergency_stopped": False}}
        with open(self.state, "w", encoding="utf-8") as f:
            _json.dump(state, f)
        return pp.check_publish_allowed(
            "gumroad", state_path=self.state, now=now,
            circuit_breaker_state_path=self.breaker), gap

    def _gap(self):
        from channels import publish_protection as pp
        return pp._profile("gumroad")["min_cooldown_minutes"]

    def test_under_minimum_blocks(self):
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        gap = self._gap()
        res, _ = self._check((now - timedelta(seconds=gap * 60 - 1)).isoformat(), now)
        self.assertFalse(res["allowed"])
        self.assertIn("spacing", res["reason"])

    def test_exact_boundary_allows(self):
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        gap = self._gap()
        res, _ = self._check((now - timedelta(minutes=gap)).isoformat(), now)
        self.assertTrue(res["allowed"], res.get("reason"))

    def test_over_minimum_allows(self):
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        gap = self._gap()
        res, _ = self._check((now - timedelta(minutes=gap + 1)).isoformat(), now)
        self.assertTrue(res["allowed"], res.get("reason"))

    def test_missing_timestamp_skips_spacing(self):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        res, _ = self._check(None, now)
        self.assertTrue(res["allowed"], res.get("reason"))

    def test_corrupt_timestamp_skips_spacing(self):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        res, _ = self._check("not-a-timestamp", now)
        self.assertTrue(res["allowed"], res.get("reason"))

    def test_naive_timestamp_does_not_raise(self):
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        naive = (now - timedelta(minutes=1)).replace(tzinfo=None).isoformat()
        res, _ = self._check(naive, now)
        self.assertTrue(res["allowed"], res.get("reason"))

    def test_future_timestamp_blocks(self):
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        res, _ = self._check((now + timedelta(minutes=5)).isoformat(), now)
        self.assertFalse(res["allowed"])


class TestLedgerQualityGateKwarg(unittest.TestCase):
    def setUp(self):
        self.ledger = _temp_path(".jsonl")

    def tearDown(self):
        if os.path.exists(self.ledger):
            os.remove(self.ledger)

    def _result(self):
        return PublishResult(ok=False, platform="gumroad", product_id=None,
                             url=None, error="blocked by test", dry_run=True)

    def test_omitted_kwarg_keeps_original_shape(self):
        ev = ledger.record_publish_attempt(
            _fake_product(), self._result(), ledger_path=self.ledger)
        self.assertNotIn("quality_gate", ev)

    def test_given_kwarg_recorded_verbatim(self):
        qg = {"allowed": False, "reason": "regression probe"}
        ev = ledger.record_publish_attempt(
            _fake_product(), self._result(), ledger_path=self.ledger,
            protection_decision="quality_gate_blocked", quality_gate=qg)
        self.assertEqual(ev["quality_gate"], qg)
        self.assertEqual(ev["protection_decision"], "quality_gate_blocked")


if __name__ == "__main__":
    unittest.main()

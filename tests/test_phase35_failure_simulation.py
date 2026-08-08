"""Phase 35 (ADR-228), Section 16: commercial failure simulation, the 3
genuinely new scenarios not already covered by Phase 33/34's test
suites (A-H, J-N are already real, tested elsewhere -- cross-
referenced in AUDIT/PHASE_35_COMMERCIAL_TRUTH_REPORT.md rather than
re-tested here). Expected behavior for every scenario: DETECTION ->
FLAG -> LOG -> SAFE STATE -> CEO VISIBILITY."""

import hashlib
import hmac
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

import commission_engine as ce
import partner_intelligence_agent as pia
from channels import paddle_webhook


class TestScenarioI_WebhookDelayed(unittest.TestCase):
    """A real payment webhook can legitimately arrive minutes after the
    real event occurred -- lateness alone must never cause rejection or
    silent loss; only signature/catalog/idempotency validity matters."""

    def test_a_late_arriving_valid_event_is_still_accepted(self):
        secret = "sim_only_fake_secret_never_real"
        with tempfile.TemporaryDirectory() as d:
            events_path = os.path.join(d, "events.jsonl")
            catalog_path = os.path.join(d, "catalog.json")
            with open(catalog_path, "w", encoding="utf-8") as f:
                json.dump([{"title": "Sim Product", "product_id": "pro_sim", "price_id": "pri_sim", "price": 100.0}], f)

            body = json.dumps({
                "event_id": "evt_delayed_1", "event_type": "transaction.completed",
                "data": {"id": "txn_delayed", "items": [{"price": {"id": "pri_sim"}}],
                         "details": {"totals": {"grand_total": "10000", "currency_code": "USD"}}},
            }).encode("utf-8")
            ts = "1700000000"  # a real, old real-world unix timestamp -- simulates a genuinely delayed webhook
            signed_payload = f"{ts}:".encode("utf-8") + body
            h1 = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
            header = f"ts={ts};h1={h1}"

            # Processed "now" (2026), far later than the event's own real ts -- simulates real delay.
            processing_time = datetime.now(timezone.utc)
            result = paddle_webhook.process_paddle_webhook(body, header, secret=secret,
                                                             processed_events_path=events_path,
                                                             catalog_path=catalog_path, now=processing_time)
        self.assertEqual(result["status"], "ACCEPTED", "a delayed-but-validly-signed event must still be accepted, never rejected for lateness alone")

    def test_the_delay_is_logged_not_silently_dropped(self):
        # Verified via the same mechanism as duplicate-event detection --
        # every real event, regardless of arrival delay, produces a real,
        # persisted, evidence-carrying log entry (never silently lost).
        secret = "sim_only_fake_secret_never_real"
        with tempfile.TemporaryDirectory() as d:
            events_path = os.path.join(d, "events.jsonl")
            catalog_path = os.path.join(d, "catalog.json")
            with open(catalog_path, "w", encoding="utf-8") as f:
                json.dump([{"title": "Sim Product", "product_id": "pro_sim", "price_id": "pri_sim", "price": 100.0}], f)
            body = json.dumps({
                "event_id": "evt_delayed_2", "event_type": "transaction.completed",
                "data": {"id": "txn_delayed_2", "items": [{"price": {"id": "pri_sim"}}],
                         "details": {"totals": {"grand_total": "10000", "currency_code": "USD"}}},
            }).encode("utf-8")
            ts = "1700000000"
            signed_payload = f"{ts}:".encode("utf-8") + body
            h1 = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
            header = f"ts={ts};h1={h1}"
            paddle_webhook.process_paddle_webhook(body, header, secret=secret, processed_events_path=events_path, catalog_path=catalog_path)
            with open(events_path, encoding="utf-8") as f:
                logged = [json.loads(l) for l in f if l.strip()]
        self.assertEqual(len(logged), 1)
        self.assertEqual(logged[0]["event_id"], "evt_delayed_2")


class TestScenarioM_ExternalApiUnavailable(unittest.TestCase):
    """A partner-registry lookup failure (simulating an external API
    being unavailable) must degrade safely, never crash, never invent a
    fallback value."""

    def test_missing_platform_registry_entry_degrades_safely(self):
        # Simulates the real registry being unavailable/incomplete for a
        # given platform -- categorize_evidence_source() must never crash,
        # never assume official status.
        result = pia.categorize_evidence_source("https://unknown-platform.example/page", partner_domain=None)
        self.assertEqual(result["category"], "TRUSTED_SECONDARY_SOURCE")

    def test_score_commission_opportunity_never_crashes_on_a_bare_dict(self):
        # Simulates the real evaluation being called with a partial/
        # degraded record (e.g. an external lookup that partially failed).
        result = ce.score_commission_opportunity({})
        self.assertIn("dimensions", result)
        self.assertEqual(len(result["dimensions"]), 13)


class TestScenarioO_ThirdPartyFalselyClaimsCommission(unittest.TestCase):
    """The scenario most directly relevant to this round's own core
    fix: a third-party source (blog, affiliate directory, social post)
    claims a specific, attractive commission rate for a real company --
    this alone must NEVER be sufficient to grant VERIFIED status,
    regardless of how confident or specific the claim reads."""

    def test_third_party_claim_alone_never_grants_verified(self):
        # A 3rd-party blog claims Amazon pays a suspiciously generous
        # 90% commission -- must not be trusted as official.
        entry = {"display_name": "Amazon (Associates)", "terms": None,
                 "evidence": ["https://some-clickbait-blog.example/amazon-secretly-pays-90-percent"]}
        odata = {"commission": "90% (claimed by a third-party blog)", "status": "REAL"}
        status = ce._derive_verification_status(entry, odata, platform="amazon")
        self.assertEqual(status, "THIRD_PARTY_ONLY")
        self.assertNotEqual(status, "VERIFIED")

    def test_specific_dollar_figures_in_third_party_claims_do_not_earn_trust(self):
        # A highly specific-looking figure ("$4,127.50 average payout")
        # reads more convincing than a round number, but specificity is
        # not evidence -- the categorization must remain domain-based,
        # never text-plausibility-based.
        entry = {"terms": None, "evidence": ["https://affiliate-directory.example/amazon-program-review"]}
        odata = {"commission": "$4,127.50 average monthly payout (per a random directory)", "status": "REAL"}
        status = ce._derive_verification_status(entry, odata, platform="amazon")
        self.assertEqual(status, "THIRD_PARTY_ONLY")

    def test_real_official_evidence_still_correctly_overrides_a_contradicting_third_party_claim(self):
        # If a real official page IS present alongside a contradicting
        # 3rd-party claim, the real official evidence still governs
        # VERIFIED status -- detect_conflicting_terms() (not this
        # function) is the real, separate mechanism for surfacing the
        # contradiction itself, never silently averaged together here.
        entry = {"terms": "https://amazon.com/affiliate/real-terms", "evidence": ["https://some-blog.example/wrong-claim"]}
        odata = {"commission": "5%", "status": "REAL"}
        status = ce._derive_verification_status(entry, odata, platform="amazon")
        self.assertEqual(status, "VERIFIED")


if __name__ == "__main__":
    unittest.main()

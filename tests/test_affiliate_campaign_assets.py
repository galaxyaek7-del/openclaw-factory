"""Guards for GF-AFFILIATE-01's research record and first campaign asset.

These tests prove three things that are easy to get wrong in affiliate work:

(a) the network record keeps its verdicts tied to the evidence that produced
    them -- a free network cannot silently become "usable" without a payout
    rail, and a network that needs a deposit cannot silently become zero-spend;
(b) the campaign asset never claims a publication, a commission, or a link
    that does not exist, and never leaks a raw tracking parameter into the
    repo;
(c) every hard number printed in the asset is one of the verified systeme.io
    facts, so a later edit cannot quietly invent a limit or a price.

Run: python -m pytest tests/test_affiliate_campaign_assets.py -q
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import brand_dna

RECORD = ROOT / "reports" / "AFFILIATE-01" / "NETWORK_VERIFICATION_2026-10-20.json"
PLAN = ROOT / "reports" / "AFFILIATE-01" / "CAMPAIGN_PLAN_2026-10-20.md"
DRAFT = ROOT / "drafts" / "affiliate" / "systeme_free_plan_ceiling_2026-10-20.md"


@pytest.fixture(scope="module")
def record():
    return json.loads(RECORD.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def draft():
    return DRAFT.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def plan():
    return PLAN.read_text(encoding="utf-8")


def _by_id(record):
    return {net["id"]: net for net in record["networks"]}


# --- the research record ---------------------------------------------------


def test_record_claims_no_spend_and_no_account(record):
    assert record["cost_usd"] == 0
    assert record["accounts_created"] == 0
    assert record["applications_submitted"] == 0
    assert record["mission"] == "GF-AFFILIATE-01"


def test_every_network_carries_evidence_and_a_date(record):
    assert len(record["networks"]) >= 4
    for net in record["networks"]:
        assert net["evidence"], f"{net['id']} has no evidence list"
        assert all(url.startswith("https://") for url in net["evidence"]), net["id"]
        assert net["verified"] == "2026-10-20", net["id"]
        assert net["verdict"], net["id"]
        assert net["why"], net["id"]


def test_the_zero_spend_verdicts_are_pinned(record):
    nets = _by_id(record)
    assert nets["awin"]["verdict"] == "BLOCKED_BY_ZERO_SPEND"
    assert nets["awin"]["deposit_required"] is True
    assert nets["systeme_direct"]["verdict"] == "USABLE_NOW"
    assert nets["impact_com"]["verdict"] == "USABLE_FREE_PENDING_FOUNDER_AUTHORIZATION"
    assert nets["digistore24"]["verdict"] == "HOLD"
    assert nets["partnerstack"]["verdict"] == "HOLD"
    assert nets["amazon_associates"]["verdict"] == "BLOCKED_ON_FOUNDER_CREDENTIAL"


def test_a_held_network_is_held_for_a_payout_reason(record):
    nets = _by_id(record)
    for net_id in ("digistore24", "partnerstack"):
        reason = nets[net_id]["algeria_payout_usability"]["status"]
        assert reason in {"CONDITIONAL", "BLOCKED_ON_PUBLISHED_LISTS"}, net_id
    assert nets["digistore24"]["minimum_payout"]["international_transfer"].startswith("250")
    assert "Algeria" in nets["partnerstack"]["algeria_payout_usability"]["reason"]


def test_unverified_items_are_declared_not_implied(record):
    assert record["what_this_does_not_prove"]
    joined = " ".join(record["what_this_does_not_prove"]).lower()
    assert "unknown" in joined
    assert "not revenue" in joined or "not recorded as such" in joined


# --- the campaign asset ----------------------------------------------------


def test_asset_is_declared_unpublished_and_unauthorized(draft):
    assert "publication_status: NOT_PUBLISHED" in draft
    assert "publication_authorized: false" in draft
    assert "AFFILIATE_DISCLOSURE_PRESENT" in draft


def test_asset_has_a_real_disclosure_sentence(draft):
    lowered = draft.lower()
    assert "i'm an affiliate" in lowered
    assert "at no extra cost to you" in lowered


def test_asset_never_embeds_a_raw_tracking_parameter(draft):
    assert "?sa=" not in draft.lower()
    assert "sa=" not in draft.lower()
    assert "[TRACKED LINK" in draft


def test_asset_only_states_verified_systeme_facts(draft):
    for fact in ("2,000", "3 sales funnels", "500", "$17", "$47", "$97", "April 2026"):
        assert fact in draft, fact
    assert "unlimited emails" in draft.lower()


def test_asset_makes_no_income_promise_or_superlative(draft):
    lowered = draft.lower()
    for banned in ("guaranteed", "get rich", "#1", "best funnel software", "passive income"):
        assert banned not in lowered, banned
    assert not re.search(r"earn \$[\d,]", lowered)
    assert not re.search(r"make \$[\d,]", lowered)


def test_asset_names_what_it_did_not_verify(draft):
    assert "What I did not verify" in draft
    assert draft.index("What I did not verify") > draft.index("## The decision rule")


def test_asset_clears_the_brand_trust_scan(draft):
    result = brand_dna.validate_customer_facing_text(draft)
    assert result["passed"] is True, result["failed_checks"]


def test_plan_reports_acceptance_honestly(plan):
    assert "**0 qualified clicks" in plan or "**0.** 1 draft" in plan
    assert "| Content assets published | **0.**" in plan
    assert "| Commissions | **0.**" in plan
    assert "| Payouts received | **$0** |" in plan
    assert "NOT AUTHORIZED" in plan

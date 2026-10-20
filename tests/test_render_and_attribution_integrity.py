#!/usr/bin/env python3
"""Render and attribution-integrity tests (Cycle 107).

Two properties are under test:

1. A real tracked link cannot be written into a tracked file, and rendering
   never prints the link or its id. The source draft keeps a placeholder.
2. Revenue reads cannot inflate: TEST/SIMULATION/PROVISIONAL records never
   count as real, PENDING is never cash, REVERSED/REFUNDED never count, a
   repeated real transaction is refused, a null referrer is preserved, and a
   malformed ledger line is skipped rather than fatal.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import commission_ledger  # noqa: E402
import render_affiliate_asset as renderer  # noqa: E402
from affiliate_commerce import click_tracking  # noqa: E402

FAKE_URL = "https://systeme.io/?sa=saTESTONLY000000000000000000000000000000"

DRAFT = """---
title: "test asset"
affiliate_link: "[TRACKED LINK - not committed]"
disclosure: AFFILIATE_DISCLOSURE_PRESENT
---

# test asset

*Disclosure: I'm an affiliate for systeme.io. If you click and later pay, I earn a commission.*

Here is the link: **[systeme.io pricing - tracked link]**.
"""


def _write_draft(tmp_path, text=DRAFT, name="draft.md"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_renders_both_placeholders_into_an_allowed_directory(tmp_path):
    out = tmp_path / "out" / "asset.md"
    report = renderer.render_asset(
        _write_draft(tmp_path), out, FAKE_URL,
        allowed_dir=tmp_path / "out", require_gitignored=False)
    text = out.read_text(encoding="utf-8")
    assert report["placeholders_replaced"] == 2
    assert renderer.PLACEHOLDER_RE.search(text) is None
    assert text.count(FAKE_URL) == 2
    assert "I'm an affiliate for systeme.io" in text
    assert report["link_domain"] == "systeme.io"
    assert report["disclosure_ok"] is True


def test_refuses_output_outside_the_allowed_directory(tmp_path):
    with pytest.raises(renderer.RenderRefused):
        renderer.render_asset(
            _write_draft(tmp_path), tmp_path / "tracked" / "asset.md", FAKE_URL,
            allowed_dir=tmp_path / "out", require_gitignored=False)
    assert not (tmp_path / "tracked").exists()


def test_refuses_an_unapproved_domain(tmp_path):
    with pytest.raises(renderer.RenderRefused):
        renderer.render_asset(
            _write_draft(tmp_path), tmp_path / "out" / "asset.md",
            "https://unapproved.example/?sa=x",
            allowed_dir=tmp_path / "out", require_gitignored=False)


def test_refuses_a_link_without_disclosure(tmp_path):
    text = DRAFT.replace("*Disclosure: I'm an affiliate for systeme.io. If you click and later pay, I earn a commission.*", "")
    with pytest.raises(renderer.RenderRefused):
        renderer.render_asset(
            _write_draft(tmp_path, text), tmp_path / "out" / "asset.md", FAKE_URL,
            allowed_dir=tmp_path / "out", require_gitignored=False)


def test_refuses_a_draft_with_no_body_placeholder(tmp_path):
    text = DRAFT.replace("Here is the link: **[systeme.io pricing - tracked link]**.", "")
    with pytest.raises(renderer.RenderRefused):
        renderer.render_asset(
            _write_draft(tmp_path, text), tmp_path / "out" / "asset.md", FAKE_URL,
            allowed_dir=tmp_path / "out", require_gitignored=False)


def test_refuses_when_the_output_is_not_gitignored(tmp_path):
    with pytest.raises(renderer.RenderRefused):
        renderer.render_asset(
            _write_draft(tmp_path), tmp_path / "asset.md", FAKE_URL,
            allowed_dir=tmp_path, require_gitignored=True)


def test_default_out_directory_is_gitignored():
    done = subprocess.run(["git", "check-ignore", "-q", str(renderer.DEFAULT_OUT)],
                          cwd=str(ROOT), capture_output=True)
    assert done.returncode == 0, "drafts/affiliate/rendered/ must be gitignored"


def test_check_mode_never_prints_the_link_or_id():
    done = subprocess.run([sys.executable, str(ROOT / "scripts" / "render_affiliate_asset.py"), "--check"],
                          cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    blob = (done.stdout or "") + (done.stderr or "")
    assert done.returncode == 0, blob
    assert "sa=" not in blob
    assert "saTEST" not in blob
    assert "would render" in blob


def _record(path, **overrides):
    kwargs = dict(
        partner_id="systeme.io", opportunity_id="opp-test", commission_status="PENDING",
        gross_commission=100.0, environment="TEST", fees=0.0,
        source="test", ledger_path=path,
    )
    kwargs.update(overrides)
    return commission_ledger.record_commission(**kwargs)


def test_only_real_confirmed_or_paid_counts_and_pending_is_not_cash(tmp_path):
    path = tmp_path / "commissions.jsonl"
    _record(path, environment="TEST", commission_status="PAID", gross_commission=500.0)
    _record(path, environment="SIMULATION", commission_status="PAID", gross_commission=400.0)
    _record(path, environment="PROVISIONAL", commission_status="CONFIRMED",
            gross_commission=300.0, evidence="real referral confirmed by partner email")
    _record(path, environment="REAL", commission_status="PENDING",
            gross_commission=200.0, evidence="partner dashboard shows pending")
    _record(path, environment="REAL", commission_status="CONFIRMED",
            gross_commission=100.0, evidence="partner dashboard confirmed",
            external_transaction_id="txn-real-1")
    _record(path, environment="REAL", commission_status="PAID",
            gross_commission=50.0, evidence="payout statement",
            external_transaction_id="txn-real-2")

    summary = commission_ledger.real_commission_summary(path)
    assert summary["real_commission_records"] == 3
    assert summary["real_confirmed_or_paid_commission_usd"] == 150.0
    assert summary["real_paid_commission_usd"] == 50.0
    assert summary["test_records"] == 1
    assert summary["simulation_records"] == 1
    assert summary["provisional_records"] == 1
    assert summary["provisional_commission_usd"] == 300.0


def test_reversed_and_refunded_are_not_counted_as_revenue(tmp_path):
    path = tmp_path / "commissions.jsonl"
    _record(path, environment="REAL", commission_status="REVERSED",
            gross_commission=90.0, evidence="partner reversal notice",
            external_transaction_id="txn-rev-1")
    _record(path, environment="REAL", commission_status="REFUNDED",
            gross_commission=80.0, evidence="partner refund notice",
            external_transaction_id="txn-ref-1")
    _record(path, environment="REAL", commission_status="CONFIRMED",
            gross_commission=10.0, evidence="partner dashboard confirmed",
            external_transaction_id="txn-ok-1")
    summary = commission_ledger.real_commission_summary(path)
    assert summary["real_confirmed_or_paid_commission_usd"] == 10.0


def test_real_records_without_evidence_are_refused_before_write(tmp_path):
    path = tmp_path / "commissions.jsonl"
    with pytest.raises(commission_ledger.AntiFabricationError):
        _record(path, environment="REAL", commission_status="CONFIRMED",
                external_transaction_id="txn-fake")
    assert not path.exists()


def test_the_same_real_transaction_cannot_be_counted_twice(tmp_path):
    path = tmp_path / "commissions.jsonl"
    _record(path, environment="REAL", commission_status="CONFIRMED",
            evidence="partner dashboard confirmed", external_transaction_id="txn-dup")
    with pytest.raises(commission_ledger.DuplicateCommissionError):
        _record(path, environment="REAL", commission_status="CONFIRMED",
                evidence="partner dashboard confirmed", external_transaction_id="txn-dup")
    assert commission_ledger.real_commission_summary(path)["real_confirmed_or_paid_commission_usd"] == 100.0


def test_a_null_referrer_is_preserved_not_invented(tmp_path):
    path = tmp_path / "clicks.jsonl"
    click_tracking.record_click("prod-1", referrer=None, ledger_path=path)
    clicks = click_tracking.read_clicks(path)
    assert len(clicks) == 1
    assert "referrer" in clicks[0] and clicks[0]["referrer"] is None


def test_repeated_clicks_count_as_clicks_not_revenue(tmp_path):
    path = tmp_path / "clicks.jsonl"
    for _ in range(3):
        click_tracking.record_click("prod-1", ledger_path=path)
    summary = click_tracking.click_summary(path)
    assert summary["total_real_clicks"] == 3
    assert "revenue" not in json.dumps(summary).lower()


def test_a_malformed_ledger_line_is_skipped_not_fatal(tmp_path):
    path = tmp_path / "clicks.jsonl"
    click_tracking.record_click("prod-1", ledger_path=path)
    with open(path, "a", encoding="utf-8") as f:
        f.write("{not json\n")
    click_tracking.record_click("prod-2", ledger_path=path)
    clicks = click_tracking.read_clicks(path)
    assert [c["product_id"] for c in clicks] == ["prod-1", "prod-2"]


def test_no_affiliate_id_is_written_or_rendered_into_any_ledger(tmp_path):
    path = tmp_path / "clicks.jsonl"
    click_tracking.record_click("prod-1", referrer="https://example.com/post", ledger_path=path)
    assert "sa=" not in path.read_text(encoding="utf-8")
    out = tmp_path / "out" / "asset.md"
    renderer.render_asset(_write_draft(tmp_path), out, FAKE_URL,
                          allowed_dir=tmp_path / "out", require_gitignored=False)
    assert "saTEST" not in str(renderer.render_asset(
        _write_draft(tmp_path), tmp_path / "out" / "asset2.md", FAKE_URL,
        allowed_dir=tmp_path / "out", require_gitignored=False))

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the narrow inbound-only Customer Evidence Gate (lib/customer_evidence.py).

Pure, deterministic: uses temp ledgers so the real factory ledgers are never touched.
No network, no provenance fabrication, no MARKET/PRODUCT/TRANSACTION synthesis.
"""

import importlib.util
import json
import subprocess
import sys
import threading
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "customer_evidence", Path(__file__).resolve().parent.parent / "lib" / "customer_evidence.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


customer_evidence = _load_module()


def test_valid_signal_is_customer_classification(tmp_path):
    ledger = tmp_path / "customer_interest.jsonl"
    payload = {
        "email": "real.user@example.org",
        "message": "I am interested in an AI compliance toolkit for my small firm.",
        "name": "Jane Doe",
    }
    res = customer_evidence.record_interest_signal(payload, ledger_path=str(ledger))
    assert res["status"] == "accepted"
    assert res["classification"] == "CUSTOMER"
    assert res["signal_id"].startswith("int_")
    lines = [l for l in ledger.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["classification"] == "CUSTOMER"
    assert rec["provenance_quality"] == "direct_inbound"
    assert rec["channel"] == "customer_site"
    assert rec["source"] == "web_form"
    assert rec["received_at"].endswith("+00:00") or rec["received_at"].endswith("Z")


def test_honeypot_is_rejected_and_logged(tmp_path):
    ledger = tmp_path / "customer_interest.jsonl"
    rejected = tmp_path / "customer_interest_rejected.jsonl"
    payload = {
        "website": "http://spam.example",
        "email": "real.user@example.org",
        "message": "I am interested in an AI compliance toolkit for my small firm.",
    }
    res = customer_evidence.record_interest_signal(payload, ledger_path=str(ledger), rejected_ledger_path=str(rejected))
    assert res["status"] == "rejected"
    assert res["reason"] == "honeypot"
    assert not ledger.exists() or len([l for l in ledger.read_text().splitlines() if l.strip()]) == 0
    rej_lines = [l for l in rejected.read_text().splitlines() if l.strip()]
    assert len(rej_lines) == 1
    assert json.loads(rej_lines[0])["reason"] == "honeypot"


def test_bad_email_is_rejected(tmp_path):
    ledger = tmp_path / "customer_interest.jsonl"
    rejected = tmp_path / "customer_interest_rejected.jsonl"
    payload = {"email": "not-an-email", "message": "I am interested in an AI compliance toolkit for my small firm."}
    res = customer_evidence.record_interest_signal(payload, ledger_path=str(ledger), rejected_ledger_path=str(rejected))
    assert res["status"] == "rejected"
    assert res["reason"] == "valid email required"


def test_short_message_is_rejected(tmp_path):
    ledger = tmp_path / "customer_interest.jsonl"
    rejected = tmp_path / "customer_interest_rejected.jsonl"
    payload = {"email": "real.user@example.org", "message": "hi"}
    res = customer_evidence.record_interest_signal(payload, ledger_path=str(ledger), rejected_ledger_path=str(rejected))
    assert res["status"] == "rejected"
    assert res["reason"] == "interest message too short"


def test_non_deliverable_email_domain_is_rejected(tmp_path):
    ledger = tmp_path / "customer_interest.jsonl"
    rejected = tmp_path / "customer_interest_rejected.jsonl"
    payload = {"email": "a@test.com", "message": "I want a compliance toolkit please."}
    res = customer_evidence.record_interest_signal(payload, ledger_path=str(ledger), rejected_ledger_path=str(rejected))
    assert res["status"] == "rejected"
    assert res["reason"] == "non-deliverable email domain"


def test_non_dict_payload_is_rejected_and_logged(tmp_path):
    ledger = tmp_path / "customer_interest.jsonl"
    rejected = tmp_path / "customer_interest_rejected.jsonl"
    # A non-dict payload previously crashed the rejection-logging path; it must
    # now be rejected and logged without raising.
    res = customer_evidence.record_interest_signal("not-a-dict", ledger_path=str(ledger), rejected_ledger_path=str(rejected))
    assert res["status"] == "rejected"
    rej_lines = [l for l in rejected.read_text().splitlines() if l.strip()]
    assert len(rej_lines) == 1
    assert json.loads(rej_lines[0])["reason"] == "payload must be an object"


def test_duplicate_signal_is_logged_not_persisted(tmp_path):
    ledger = tmp_path / "customer_interest.jsonl"
    rejected = tmp_path / "customer_interest_rejected.jsonl"
    payload = {"email": "real.user@example.org", "message": "Duplicate interest message for testing."}
    assert customer_evidence.record_interest_signal(payload, ledger_path=str(ledger), rejected_ledger_path=str(rejected))["status"] == "accepted"
    dup = customer_evidence.record_interest_signal(payload, ledger_path=str(ledger), rejected_ledger_path=str(rejected))
    assert dup["status"] == "duplicate"
    lines = [l for l in ledger.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 1
    rej_lines = [l for l in rejected.read_text().splitlines() if l.strip()]
    assert len(rej_lines) == 1
    assert json.loads(rej_lines[0])["reason"] == "duplicate"


def test_message_field_alias_works(tmp_path):
    ledger = tmp_path / "customer_interest.jsonl"
    payload = {"email": "real.user@example.org", "interest": "Alias interest field used by the form instead of message."}
    res = customer_evidence.record_interest_signal(payload, ledger_path=str(ledger))
    assert res["status"] == "accepted"


def test_report_schema_matches_founder_directive(tmp_path):
    ledger = tmp_path / "customer_interest.jsonl"
    rejected = tmp_path / "customer_interest_rejected.jsonl"
    report = customer_evidence.generate_evidence_report(ledger_path=str(ledger), rejected_ledger_path=str(rejected))
    for key in ["A_genuine_inbound_signals", "B_valid_product_evidence", "C_valid_customer_evidence",
                "D_valid_transaction_evidence", "E_rejected_synthetic_duplicate", "F_provenance_quality",
                "G_reputation_status", "H_unit_economics_status", "I_current_product_status",
                "J_gate_assessment", "K_exact_founder_decision_required"]:
        assert key in report
    assert report["A_genuine_inbound_signals"] == 0
    assert report["B_valid_product_evidence"] == report["C_valid_customer_evidence"] == report["D_valid_transaction_evidence"] == 0
    assert report["E_rejected_synthetic_duplicate"] == 0
    assert report["G_reputation_status"] == "UNKNOWN"
    assert report["H_unit_economics_status"] == "UNKNOWN"


def test_report_counts_customer_signal_and_rejections(tmp_path):
    ledger = tmp_path / "customer_interest.jsonl"
    rejected = tmp_path / "customer_interest_rejected.jsonl"
    customer_evidence.record_interest_signal(
        {"email": "real.user@example.org", "message": "Genuine interest for the report counter test."},
        ledger_path=str(ledger), rejected_ledger_path=str(rejected))
    customer_evidence.record_interest_signal(
        {"website": "x", "email": "real.user@example.org", "message": "bot honeypot hit"},
        ledger_path=str(ledger), rejected_ledger_path=str(rejected))
    report = customer_evidence.generate_evidence_report(ledger_path=str(ledger), rejected_ledger_path=str(rejected))
    assert report["A_genuine_inbound_signals"] == 1
    assert report["C_valid_customer_evidence"] == 1
    assert report["B_valid_product_evidence"] == report["D_valid_transaction_evidence"] == 0
    assert report["E_rejected_synthetic_duplicate"] == 1
    assert report["F_provenance_quality"] == "1/1 direct_inbound"


def test_ledger_cap_stops_ingestion(tmp_path):
    ledger = tmp_path / "customer_interest.jsonl"
    rejected = tmp_path / "customer_interest_rejected.jsonl"
    original = customer_evidence.LEDGER_CAP
    customer_evidence.LEDGER_CAP = 1
    try:
        assert customer_evidence.record_interest_signal(
            {"email": "real.user@example.org", "message": "First genuine interest within the cap."},
            ledger_path=str(ledger), rejected_ledger_path=str(rejected))["status"] == "accepted"
        res = customer_evidence.record_interest_signal(
            {"email": "other.user@example.org", "message": "Second genuine interest that should be stopped."},
            ledger_path=str(ledger), rejected_ledger_path=str(rejected))
        assert res["status"] == "stopped"
    finally:
        customer_evidence.LEDGER_CAP = original


def test_thread_concurrency_is_lossless(tmp_path):
    """8 threads writing unique records must yield exactly N accepted lines
    (the race condition found in the 12h endurance test must not recur)."""
    ledger = tmp_path / "customer_interest.jsonl"
    rejected = tmp_path / "customer_interest_rejected.jsonl"
    threads, per = 8, 250
    n = threads * per

    def worker(wid):
        for k in range(per):
            customer_evidence.record_interest_signal(
                {"email": f"t{wid}.{k}@example.org", "message": f"thread concurrency message {wid} {k}"},
                ledger_path=str(ledger), rejected_ledger_path=str(rejected))

    ts = [threading.Thread(target=worker, args=(w,)) for w in range(threads)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()

    lines = [l for l in ledger.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == n, f"lost {n - len(lines)} writes under {threads}-thread load"
    # every line must be valid JSON and unique
    seen = set()
    for l in lines:
        rec = json.loads(l)
        assert rec["classification"] == "CUSTOMER"
        seen.add(rec["dedup_hash"])
    assert len(seen) == n


def test_multiprocess_concurrency_is_lossless(tmp_path):
    """Separate Python processes (mirrors server.js execFile per request) must
    not lose JSONL appends under concurrent load."""
    ledger = tmp_path / "customer_interest.jsonl"
    rejected = tmp_path / "customer_interest_rejected.jsonl"
    procs, per = 4, 250
    n = procs * per
    children = []
    for _ in range(procs):
        children.append(subprocess.Popen(
            [sys.executable, "lib/customer_evidence.py", "bench-append", str(ledger), str(rejected), str(per)],
            cwd=str(ROOT)))
    for p in children:
        p.wait(timeout=120)
    lines = [l for l in ledger.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == n, f"lost {n - len(lines)} writes under {procs}-process load"
    seen = set()
    for l in lines:
        rec = json.loads(l)
        seen.add(rec["dedup_hash"])
    assert len(seen) == n

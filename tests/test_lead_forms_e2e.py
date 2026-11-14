"""End-to-end proof for the three customer_site lead forms.

The forms are static HTML, so this test reads the exact lead payload each page
builds, records it through the real customer-evidence ledger under write_guard's
overlay, and asks the real demand gate to read that same ledger.

The test must never write a live ledger: write_guard redirects the default
``data/customer_interest.jsonl`` path to its per-run overlay. The live file's
hash is checked before and after.
"""

import hashlib
import importlib.util
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


customer_evidence = _load("customer_evidence", ROOT / "lib" / "customer_evidence.py")
demand_gate = _load("demand_gate", ROOT / "demand_gate.py")
import write_guard
SITE = ROOT / "customer_site"
PAGES = (
    "eu-ai-act-compliance-toolkit.html",
    "guide-etsy-suspension-appeal.html",
    "service-verified-lead-lists.html",
)
LEAD_RE = re.compile(r"var lead = \{(.*?)\};", re.S)


def _field(block, name):
    match = re.search(rf"{name}:\s*'([^']*)'", block)
    assert match, f"missing {name} in lead payload"
    return match.group(1)


def _payloads():
    payloads = []
    for page in PAGES:
        html = (SITE / page).read_text(encoding="utf-8")
        block = LEAD_RE.search(html)
        assert block, f"{page} must build a lead payload"
        source = _field(block.group(1), "source")
        campaign = _field(block.group(1), "campaign")
        message = _field(block.group(1), "message")
        payloads.append({
            "name": "SYNTHETIC E2E lead",
            "email": f"e2e+{source}@galaxyforge.dev",
            "message": message,
            "source": source,
            "campaign": campaign,
            "synthetic": True,
            "test_label": "SYNTHETIC_E2E_2026-11-14",
        })
    return payloads


def _live_sha(path):
    try:
        with write_guard._real["open"](path, "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()
    except OSError:
        return None


def test_three_lead_forms_record_but_do_not_count_as_real_demand():
    assert os.environ.get("GF_WRITE_GUARD_OVERLAY"), "this proof requires the write overlay"
    live_ledger = ROOT / "data" / "customer_interest.jsonl"
    before_hash = _live_sha(live_ledger)
    before_demand = demand_gate.buyer_interest_signal(ROOT)

    results = [
        customer_evidence.record_interest_signal(payload)
        for payload in _payloads()
    ]
    assert [r["status"] for r in results] == ["accepted", "accepted", "accepted"]

    rows = customer_evidence.read_signals()
    test_rows = [r for r in rows if r.get("test_label") == "SYNTHETIC_E2E_2026-11-14"]
    assert len(test_rows) == 3
    assert all(r.get("synthetic") is True for r in test_rows)
    assert all(r.get("provenance_quality") == "synthetic_test" for r in test_rows)
    assert {r.get("product_interest") for r in test_rows} == {None}

    after_demand = demand_gate.buyer_interest_signal(ROOT)
    assert after_demand == before_demand, "synthetic test leads changed real demand"
    assert _live_sha(live_ledger) == before_hash, "the live customer_interest ledger was modified"

"""ARM 8 — Distribution Guardian (verification-only).

Read-only verification of the Distribution commercial arm:
  - distributor.py (distribute, dry_run safety, publish-protection gate)
  - channels/publish_protection.py (operation limits, cooldown, emergency
    stop, first-real-publish founder gate)
  - channels/ledger.py (append-only event writer, no real-ledger mutation)

This test NEVER publishes, NEVER touches finance_data.json /
config/reality.json / data/sales_ledger.jsonl, and uses temp state + ledger
paths so the real Distribution state stays pristine.

It also asserts the three PROTECTED files keep their known baseline hashes —
a hard guarantee that ARM 8 verification changed nothing. The real sales
ledger lives at data/sales_ledger.jsonl (NOT the repo-root stray), and it
must contain zero "sale" events (commercial distribution is NOT_READY).
"""

import hashlib
import importlib
import json
import os
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from schemas.product import Product
from channels.base_arm import PublishResult

FACTORY_ROOT = Path(__file__).resolve().parent.parent

# Protected-file baseline hashes. NOTE: the real sales ledger is
# data/sales_ledger.jsonl (a stray empty sales_ledger.jsonl also exists at
# repo root and is intentionally NOT the protected file).
PROTECTED = {
    "finance_data.json": "CD297D2FC5C6E98945DFBAAE7025E44568ABE53817931CEEB811D5DAA84E7122",
    "config/reality.json": "EA3177773F63A39126B1DB02AB7BF9D307A6121A4AC0FAD257B47467DEC8E04E",
    "data/sales_ledger.jsonl": "3D2E418D09D2E037D5581A529F15108571FAD51153ABFEDFBDEE291F568D0155",
}


def _sha256(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest().upper()


def _protected_hashes():
    return {k: _sha256(FACTORY_ROOT / k) for k in PROTECTED}


def test_protected_files_unchanged_baseline():
    """The three protected financial files must keep their baseline hashes."""
    actual = _protected_hashes()
    for name, expected in PROTECTED.items():
        assert actual[name] == expected, f"{name} hash changed: {actual[name]} != {expected}"


def test_modules_import_safely():
    dist = importlib.import_module("distributor")
    pp = importlib.import_module("channels.publish_protection")
    ledger = importlib.import_module("channels.ledger")

    # Key public APIs exist.
    assert hasattr(dist, "distribute")
    assert hasattr(pp, "check_publish_allowed")
    assert hasattr(pp, "trigger_emergency_stop")
    assert hasattr(pp, "clear_emergency_stop")
    assert hasattr(pp, "note_publish_outcome")
    assert hasattr(ledger, "record_publish_attempt")
    assert hasattr(ledger, "read_events")
    # reconcile_ledger_to_finance WRITES finance_data.json — it must exist but
    # must NEVER be called by verification.
    assert hasattr(ledger, "reconcile_ledger_to_finance")


def test_modules_no_banned_external_actions():
    """Static scan: the three modules must not import / call external
    payment, messaging, or subprocess machinery directly."""
    banned = (
        "import paddle", "import requests", "import smtplib", "import subprocess",
        "os.system", "send_telegram", "activate_checkout", "import stripe",
        "import telegram", "import urllib",
    )
    files = [
        FACTORY_ROOT / "distributor.py",
        FACTORY_ROOT / "channels" / "publish_protection.py",
        FACTORY_ROOT / "channels" / "ledger.py",
    ]
    for f in files:
        text = f.read_text(encoding="utf-8")
        for token in banned:
            assert token not in text, f"{f.name} contains banned token: {token}"


def test_publish_protection_blocks_new_unproven_arm(tmp_path):
    state = tmp_path / "pp_state.json"
    pp = importlib.import_module("channels.publish_protection")
    gate = pp.check_publish_allowed("kdp", state_path=state)
    assert gate["allowed"] is False
    assert "founder approval" in gate["reason"].lower() or "first" in gate["reason"].lower()


def test_publish_protection_emergency_stop_blocks_all(tmp_path):
    state = tmp_path / "pp_state.json"
    pp = importlib.import_module("channels.publish_protection")
    pp.trigger_emergency_stop("ARM8 test", state_path=state)
    try:
        gate = pp.check_publish_allowed("gumroad", state_path=state)
        assert gate["allowed"] is False
        assert "emergency" in gate["reason"].lower()
    finally:
        pp.clear_emergency_stop(state_path=state)
    # After clearing, a proven arm is allowed again (fresh state).
    gate = pp.check_publish_allowed("gumroad", state_path=state)
    assert gate["allowed"] is True


def test_publish_protection_daily_cap(tmp_path):
    state = tmp_path / "pp_state.json"
    pp = importlib.import_module("channels.publish_protection")
    for _ in range(20):
        pp.note_publish_outcome("gumroad", True, state_path=state)
    gate = pp.check_publish_allowed("gumroad", state_path=state)
    assert gate["allowed"] is False
    assert "daily" in gate["reason"].lower() or "cap" in gate["reason"].lower()


def test_distribute_dry_run_is_safe(tmp_path):
    """distribute() with dry_run=True must never perform a real publish."""
    import distributor as dist
    ledger = importlib.import_module("channels.ledger")

    product = Product.from_jsonl_record({
        "source_id": "PROD-ARM8-TEST", "title": "ARM8 Verification",
        "product_type": "book", "price": 0,
    })
    tmp_ledger = tmp_path / "sales_ledger.jsonl"
    outcomes = dist.distribute(
        product, arm_names=["gumroad"], dry_run=True, ledger_path=tmp_ledger,
    )
    assert isinstance(outcomes, list)
    for o in outcomes:
        assert "attempted" in o and "ok" in o and "skip_reason" in o
        if o["attempted"]:
            assert o["result"] is not None
            assert o["result"].dry_run is True
    # Real ledger untouched (we wrote to a temp path).
    assert _protected_hashes()["data/sales_ledger.jsonl"] == PROTECTED["data/sales_ledger.jsonl"]


def test_ledger_records_to_temp_not_real(tmp_path):
    ledger = importlib.import_module("channels.ledger")
    product = Product.from_jsonl_record({
        "source_id": "PROD-ARM8-LEDGER", "title": "ARM8 Ledger",
        "product_type": "book", "price": 0,
    })
    result = PublishResult(ok=False, platform="gumroad", product_id=None,
                           url=None, error="blocked by test", dry_run=True)
    tmp_ledger = tmp_path / "sales_ledger.jsonl"
    ledger.record_publish_attempt(product, result, ledger_path=tmp_ledger,
                                  risk_score=0.0, protection_decision="blocked")
    events = list(ledger.read_events(ledger_path=tmp_ledger))
    assert len(events) == 1
    assert events[0]["event_type"] == "publish_attempt"
    # Real ledger must still be empty / unchanged.
    assert _protected_hashes()["data/sales_ledger.jsonl"] == PROTECTED["data/sales_ledger.jsonl"]


def test_published_books_state_intact():
    """config/reality.json published_books must remain [] (no real publish)."""
    reality = json.loads((FACTORY_ROOT / "config" / "reality.json").read_text(encoding="utf-8"))
    assert reality.get("published_books") == []


def test_real_ledger_has_no_sales():
    """Commercial distribution is NOT_READY: the real ledger must contain
    zero real 'sale' events (only append-only publish_attempt audits)."""
    ledger = importlib.import_module("channels.ledger")
    real = FACTORY_ROOT / "data" / "sales_ledger.jsonl"
    if not real.exists():
        return
    events = list(ledger.read_events(ledger_path=real))
    sale_events = [e for e in events if e.get("event_type") == "sale"]
    assert sale_events == [], f"real ledger contains {len(sale_events)} sale events"


def test_verification_leaves_protected_files_untouched(tmp_path):
    """Running the real publish-protection operations (on temp state) must
    not mutate any protected financial file."""
    before = _protected_hashes()
    pp = importlib.import_module("channels.publish_protection")
    state = tmp_path / "pp_state.json"
    pp.check_publish_allowed("gumroad", state_path=state)
    pp.note_publish_outcome("gumroad", True, state_path=state)
    pp.trigger_emergency_stop("x", state_path=state)
    pp.clear_emergency_stop(state_path=state)
    after = _protected_hashes()
    assert after == before

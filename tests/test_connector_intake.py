import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import connector_intake as ci  # noqa: E402

REG = ci.registry()
NOW = "2026-11-06T13:00:00+00:00"


def pins(*rows, measured=True):
    return {"kind": "pin_metrics", "source": "metricool", "fetched_at": NOW, "period": {"from": "2026-11-01", "to": "2026-11-06"},
            "payload": {"measured": measured, "pins": [dict(pin_id=i, title="T", impressions=10, saves=1, pin_clicks=2, outbound_clicks=o) for i, o in rows]}}


def test_a_real_pin_record_is_accepted_and_a_duplicate_is_not_written_twice(tmp_path):
    led = tmp_path / "l.jsonl"
    assert ci.add(pins(("p1", 3)), led)["accepted"] is True
    assert ci.add(pins(("p1", 3)), led).get("duplicate") is True
    assert len(ci.read(led)) == 1


def test_unregistered_source_wrong_kind_and_bad_numbers_are_refused(tmp_path):
    led = tmp_path / "l.jsonl"
    bad_source = pins(("p1", 1)); bad_source["source"] = "madeup"
    wrong_kind = pins(("p1", 1)); wrong_kind["source"] = "gmail"
    neg = pins(("p1", -1))
    nint = pins(("p1", 1)); nint["payload"]["pins"][0]["pin_clicks"] = "2"
    for r in (bad_source, wrong_kind, neg, nint):
        assert ci.add(r, led)["accepted"] is False
    assert ci.read(led) == []


def test_not_measured_cannot_carry_numbers_and_counts_as_no_clicks_not_zero_clicks(tmp_path):
    led = tmp_path / "l.jsonl"
    assert ci.add(pins(("p1", 5), measured=False), led)["accepted"] is False
    assert ci.add(pins(measured=False), led)["accepted"] is True
    assert ci.pin_outbound_clicks(led) == (0, 0)


def test_personal_data_and_secrets_are_refused(tmp_path):
    led = tmp_path / "l.jsonl"
    r = {"kind": "connector_status", "source": "gmail", "fetched_at": NOW, "payload": {"state": "AUTHENTICATED", "detail": "user a.b@example.com"}}
    assert ci.add(r, led)["accepted"] is False
    r["payload"]["detail"] = "bot123456789:" + "A" * 35
    assert ci.add(r, led)["accepted"] is False
    r["payload"]["detail"] = "x" * 400
    assert ci.add(r, led)["accepted"] is False


def test_outbound_clicks_use_the_highest_figure_per_pin(tmp_path):
    led = tmp_path / "l.jsonl"
    ci.add(pins(("p1", 2), ("p2", 1)), led)
    r2 = pins(("p1", 5)); r2["fetched_at"] = "2026-11-07T13:00:00+00:00"
    ci.add(r2, led)
    assert ci.pin_outbound_clicks(led) == (6, 2)


def test_summary_reports_age(tmp_path):
    led = tmp_path / "l.jsonl"
    ci.add(pins(("p1", 1)), led)
    s = ci.summary(led, now=datetime(2026, 11, 6, 19, 0, tzinfo=timezone.utc))
    assert s["last_intake"][0]["age_hours"] == 6.0 and s["pin_outbound_clicks"] == 1


def test_registry_has_no_connector_without_a_permission_class():
    assert REG and all(v.get("permission_class") in ("READ_INTAKE", "PERSONAL_WRITE", "OUTBOUND", "FINANCIAL") for v in REG.values())

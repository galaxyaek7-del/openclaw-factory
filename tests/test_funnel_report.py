import json, sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import funnel_report as f

CRIT = {"checkpoints": [
    {"id": "C1", "date": "2026-11-27", "min_pin_clicks": 5, "min_sales": 0, "if_missed": "x"},
    {"id": "C2", "date": "2026-12-11", "min_pin_clicks": 25, "min_sales": 1, "either": True, "if_missed": "y"},
]}


def v(today, clicks, sales, measured):
    return {c["id"]: c["verdict"] for c in f.judge(CRIT, date.fromisoformat(today), clicks, sales, measured)}


def test_before_the_date_is_waiting():
    assert v("2026-11-10", 0, 0, False) == {"C1": "WAITING", "C2": "WAITING"}


def test_unmeasured_clicks_are_unknown_never_a_miss():
    assert v("2026-11-28", 0, 0, False)["C1"] == "UNKNOWN"


def test_measured_zero_clicks_after_the_date_is_triggered():
    assert v("2026-11-28", 0, 0, True)["C1"] == "TRIGGERED"


def test_met_thresholds_and_either_rule():
    assert v("2026-11-28", 5, 0, True)["C1"] == "OK"
    assert v("2026-12-12", 3, 1, True)["C2"] == "OK"  # a sale satisfies the either-rule
    assert v("2026-12-12", 30, 0, True)["C2"] == "OK"  # so do clicks
    assert v("2026-12-12", 3, 0, True)["C2"] == "TRIGGERED"


def test_pin_counts_counts_due_rows(tmp_path):
    p = tmp_path / "l.jsonl"
    p.write_text("\n".join(json.dumps({"scheduled_for": d + " 12:00"}) for d in ("2026-11-06", "2026-11-07", "2026-11-09")), encoding="utf-8")
    assert f.pin_counts(p, today=date(2026, 11, 7)) == (3, 2)

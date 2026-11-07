import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import subtle_audit as a  # noqa: E402


def test_empty_drift_is_not_a_finding(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "product_registry.json").write_text(json.dumps(
        {"drift": {"live_missing_from_catalog": [], "duplicate_live_titles": ["X"]}, "products": []}), encoding="utf-8")
    f = a.check_registry(tmp_path)
    assert len(f) == 1 and "duplicate_live_titles" in f[0]["what"]


def test_double_scheduled_pin_and_over_cap_day_are_high(tmp_path):
    (tmp_path / "data").mkdir()
    rows = [{"offer_id": "A", "scheduled_for": "2026-11-20"}] * 2 + [{"offer_id": f"P{i}", "scheduled_for": "2026-11-21"} for i in range(6)]
    (tmp_path / "data" / "pinterest_manual_posts.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    sev = [x["severity"] for x in a.check_pinterest(tmp_path, today=date(2026, 11, 7))]
    assert sev.count("HIGH") == 2


def test_dead_flag_is_reported(tmp_path):
    (tmp_path / ".env").write_text("GF_DEMAND_GATED=true\nGF_FREEZE_NEW_PRODUCTS=false\n", encoding="utf-8")
    assert any("no effect" in x["what"] for x in a.check_flags(tmp_path))


def test_missing_state_file_is_flagged(tmp_path):
    assert all(x["severity"] == "MEDIUM" for x in a.check_stale_state(tmp_path))


def test_daily_registry_syncs_the_catalog_before_rebuilding(tmp_path):
    import registry_daily as rd
    order = []
    summary = {"products": 1, "states": {}, "sales_total": 0, "drift_counts": {}}
    r = rd.run_once(today="2026-11-07", state_path=tmp_path / "s.json", catalog_sync=lambda: order.append("sync") or "added=2",
                    runner=lambda: order.append("registry") or (summary, {}))
    assert order == ["sync", "registry"] and "added=2" in r["detail"]

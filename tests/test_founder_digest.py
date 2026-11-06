import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import founder_digest as fd  # noqa: E402

REG = {"generated_at": "2026-11-06T00:03:00", "products": [{"published": True, "sales_count": 2}, {"published": True, "sales_count": 0}, {"published": False, "sales_count": 9}]}
STAGES = [{"stage": 1, "name": "loop", "status": "OK", "owner": "x"}, {"stage": "A1", "name": "Amazon affiliate", "status": "BLOCKED", "owner": "english"},
          {"stage": 8, "name": "money", "status": "WAITING", "owner": "y"}]


def msg(**kw):
    base = dict(today="2026-11-06", stages=STAGES, tools_counts={"tools OK": 70, "tools DEGRADED": 2}, regressions=[], registry=REG,
                demand={"open": False, "signals": {"SALE": 0}}, pins={"due": 1, "later": 4, "next": ("2026-11-07", "T")}, tool_names=["loop:x"])
    base.update(kw)
    return fd.build_message(**base)


def test_numbers_come_from_the_data_and_unpublished_sales_are_not_counted():
    m = msg()
    assert "2 منتجاً منشوراً، 2 مبيعة" in m and "9 مبيعة" not in m
    assert "مغلقة" in m and "SALE=0" in m and "يلزم حساب Amazon Associates" in m and "2 متدهورة" in m


def test_missing_registry_is_unknown_not_zero():
    assert "UNKNOWN منتجاً منشوراً، UNKNOWN مبيعة" in msg(registry=None)


def test_regression_is_named():
    assert "تراجع منذ آخر لقطة: loop" in msg(regressions=[{"name": "loop"}])


def test_pinterest_summary_counts_due_and_next():
    rows = [{"offer_id": "a", "scheduled_for": "2026-11-06 12:00 (x)", "title": "A"}, {"offer_id": "a", "scheduled_for": "2026-11-06 12:00", "title": "A"},
            {"offer_id": "b", "scheduled_for": "2026-11-08 12:00 (x)", "title": "B"}, {"offer_id": "c", "scheduled_for": "2026-11-07 12:00", "title": "C"}]
    s = fd.pinterest_summary(rows, "2026-11-06")
    assert s["due"] == 1 and s["later"] == 2 and s["next"] == ("2026-11-07", "C")


def test_sends_once_a_day_not_before_7_and_retries_a_failed_send(tmp_path):
    st = tmp_path / "s.json"
    calls = []
    g = lambda today: dict(today=today, stages=STAGES, tools_counts={}, regressions=[], registry=REG, demand=None, pins=None)  # noqa: E731
    early = datetime(2026, 11, 6, 5, 0, tzinfo=timezone.utc)
    assert fd.run_once(early, st, g, lambda s, b: calls.append(1) or {"delivered": True})["action"] == "none" and not calls
    t = datetime(2026, 11, 6, 8, 0, tzinfo=timezone.utc)
    assert fd.run_once(t, st, g, lambda s, b: {"delivered": False, "channel": "local_fallback"})["action"] == "retry"
    assert fd.run_once(t, st, g, lambda s, b: calls.append(1) or {"delivered": True})["action"] == "sent"
    assert fd.run_once(t, st, g, lambda s, b: calls.append(1) or {"delivered": True})["action"] == "none" and len(calls) == 1


def test_gives_up_after_the_attempt_cap(tmp_path):
    st = tmp_path / "s.json"
    g = lambda today: dict(today=today, stages=STAGES, tools_counts={}, regressions=[], registry=REG, demand=None, pins=None)  # noqa: E731
    t = datetime(2026, 11, 6, 9, 0, tzinfo=timezone.utc)
    for _ in range(fd.MAX_ATTEMPTS):
        fd.run_once(t, st, g, lambda s, b: {"delivered": False, "channel": "local_fallback"})
    assert "gave up" in fd.run_once(t, st, g, lambda s, b: {"delivered": True})["detail"]


def test_connector_line_shows_age_clicks_and_overdue():
    fresh = {"last_intake": [{"age_hours": 3.2}, {"age_hours": 20}], "pin_outbound_clicks": 4, "pins_measured": 2}
    assert "آخر جولة قبل 3 ساعة" in msg(connectors=fresh) and "نقرات Pinterest الخارجة: 4" in msg(connectors=fresh)
    stale = {"last_intake": [{"age_hours": 70}], "pin_outbound_clicks": 0, "pins_measured": 0}
    assert "الجولة متأخرة" in msg(connectors=stale)
    assert "لم تُسجَّل جولة بعد" in msg(connectors={"last_intake": []})


def test_automation_line_is_shown_when_known():
    m = msg(automation={"automatic_or_gated": 10, "capabilities": 16, "percent": 62})
    assert "10 من 16 قدرة آلية أو مشروطة (62%)" in m
    assert "الآلية:" not in msg()

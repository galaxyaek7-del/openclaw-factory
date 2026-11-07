import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import galaxy_analytics as ga  # noqa: E402

NOW = datetime(2026, 11, 8, 12, tzinfo=timezone.utc)


def fake_http(url, token):
    assert token == "tok-SECRET-123"
    if "/stats/total" in url:
        return {"total": 120, "total_unique": 80}
    if "/stats/hits" in url:
        return {"hits": [{"path": "/tool-a.html", "count": 50}, {"path": "/index.html", "count": 40},
                         {"path": "outbound/gumroad/a", "count": 3}, {"path": "/products.html", "count": 10}]}
    if "/stats/toprefs" in url:
        return {"stats": [{"name": "pinterest.com", "count": 30}, {"name": "", "count": 90}]}
    if "/stats/locations" in url:
        return {"stats": [{"name": "United States", "count": 40}]}
    raise AssertionError(url)


def test_not_configured_is_unknown_everywhere_never_zero():
    s = ga.build_snapshot(now=NOW, env={}, code="")
    assert s["status"] == "NOT_CONFIGURED"
    assert all(v["class"] == "UNKNOWN" and v["value"] is None for v in s["metrics"].values())
    assert "not sales" in s["separation"]


def test_code_without_token_is_unknown_and_says_why():
    s = ga.build_snapshot(now=NOW, env={}, code="galaxyforge")
    assert s["status"] == "NO_TOKEN" and s["deployment"]["counter_code_set"]["value"] is True
    assert "GOATCOUNTER_API_TOKEN" in s["metrics"]["pageviews"]["note"]


def test_full_read_classifies_each_figure_and_keeps_outbound_clicks_out_of_pages():
    s = ga.build_snapshot(now=NOW, env={"GOATCOUNTER_API_TOKEN": "tok-SECRET-123"}, http=fake_http, code="galaxyforge")
    mt = s["metrics"]
    assert s["status"] == "READ_OK"
    assert mt["pageviews"]["value"] == 120 and mt["pageviews"]["class"] == "OBSERVED"
    assert mt["unique_visitors"]["value"] == 80
    assert mt["product_page_views"] == {**mt["product_page_views"], "value": 60, "class": "DERIVED"}
    assert mt["outbound_clicks"]["value"] == 3 and "not a sale" in mt["outbound_clicks"]["note"]
    assert all(p["name"] != "outbound/gumroad/a" for p in mt["landing_pages"]["value"])
    assert "tok-SECRET-123" not in json.dumps(s)


def test_missing_unique_field_and_http_errors_fail_closed():
    def partial(url, token):
        if "/stats/total" in url:
            return {"total": 5}
        raise RuntimeError("boom secret-token-value")
    s = ga.build_snapshot(now=NOW, env={"GOATCOUNTER_API_TOKEN": "secret-token-value"}, http=partial, code="galaxyforge")
    assert s["metrics"]["unique_visitors"]["class"] == "UNKNOWN"
    assert s["metrics"]["traffic_sources"]["class"] == "UNKNOWN"
    assert s["status"] == "READ_PARTIAL"
    assert "secret-token-value" not in json.dumps(s)


def test_dashboard_section_is_unknown_when_missing_or_stale(tmp_path):
    assert ga.founder_section(tmp_path / "none.json", NOW)["state"] == "UNKNOWN"
    snap = ga.build_snapshot(now=NOW - timedelta(hours=5), env={}, code="")
    p = tmp_path / "s.json"
    ga.write_snapshot(snap, p)
    assert ga.founder_section(p, NOW)["state"] == "UNKNOWN"
    assert ga.founder_section(p, NOW - timedelta(hours=4))["state"] == "NOT_CONFIGURED"


def test_loop_step_refreshes_at_most_hourly(tmp_path):
    import analytics_snapshot as step
    p = tmp_path / "s.json"
    build = lambda: ga.build_snapshot(now=NOW, env={}, code="")  # noqa: E731
    assert step.run_once(NOW, p, build)["action"] == "ran"
    assert step.run_once(NOW + timedelta(minutes=20), p, build)["action"] == "none"
    assert step.run_once(NOW + timedelta(minutes=60), p, build)["action"] == "ran"


def test_counter_code_reader_accepts_only_plain_names(tmp_path):
    f = tmp_path / "gf.js"
    f.write_text("var GF_COUNTER_CODE = 'galaxyforge';", encoding="utf-8")
    assert ga.counter_code(f) == "galaxyforge"
    f.write_text("var GF_COUNTER_CODE = '';", encoding="utf-8")
    assert ga.counter_code(f) is None
    f.write_text("var GF_COUNTER_CODE = 'Bad Name';", encoding="utf-8")
    assert ga.counter_code(f) is None

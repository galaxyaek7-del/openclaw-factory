import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import verify_counter_production as v  # noqa: E402

JS_ON = "var GF_COUNTER_CODE = 'aek';"
JS_OFF = "var GF_COUNTER_CODE = '';"


def fake(js, pages_ok=True, count_status=200):
    def f(url, timeout=20):
        if url.endswith("gf-pageview.js"):
            return 200, js
        if "gc.zgo.at" in url:
            return count_status, ""
        return 200, "<script src=\"assets/gf-pageview.js\"></script>" if pages_ok else "<html></html>"
    return f


def test_deployed_and_loadable_but_event_and_dashboard_stay_unknown():
    r = v.check(fake(JS_ON), ["customer_site/a.html"])
    assert r["deployment"]["status"] == "DEPLOYED" and r["script_loading"]["status"] == "LOADABLE"
    assert r["tracking_event"]["status"] == "UNKNOWN" and r["dashboard"]["status"] == "UNKNOWN"


def test_counter_off_in_production_is_reported_not_deployed():
    r = v.check(fake(JS_OFF), ["customer_site/a.html"])
    assert r["deployment"]["status"] == "NOT_DEPLOYED" and r["script_loading"]["status"] == "PAGES_OK_COUNTER_OFF"


def test_network_failure_is_unknown_never_ok():
    def boom(url, timeout=20):
        raise OSError("down")
    r = v.check(boom, ["customer_site/a.html"])
    assert r["deployment"]["status"] == "UNKNOWN" and r["script_loading"]["status"] == "UNKNOWN"


def test_missing_loader_or_dead_counter_script_is_a_problem():
    assert v.check(fake(JS_ON, pages_ok=False), ["customer_site/a.html"])["script_loading"]["status"] == "PROBLEM"
    assert v.check(fake(JS_ON, count_status=500), ["customer_site/a.html"])["script_loading"]["status"] == "PROBLEM"

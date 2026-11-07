import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import pin_destination_audit as pa  # noqa: E402

TODAY = date(2026, 11, 7)
NOSLEEP = lambda s: None  # noqa: E731


def row(oid="P1", day="2026-11-08", link=None):
    return {"offer_id": oid, "scheduled_for": f"{day} 18:00 (Pinterest account time)",
            "link": link or f"https://x.gumroad.com/l/a?utm_source=pinterest&utm_content={oid.lower()}-pinterest-v1"}


def ledger(tmp_path, rs):
    p = tmp_path / "l.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rs), encoding="utf-8")
    c = tmp_path / "c.json"
    c.write_text(json.dumps({"data": {"products": [{"id": "P1", "price_cents": 2900}]}}), encoding="utf-8")
    return p, c


def run(tmp_path, rs, fetch):
    p, c = ledger(tmp_path, rs)
    return pa.audit(14, TODAY, fetch, p, c, pause=0, sleep=NOSLEEP)


def test_ok_needs_200_instock_and_the_catalog_price(tmp_path):
    ok = lambda url: (200, '{"price": "29"} InStock')  # noqa: E731
    assert [r["status"] for r in run(tmp_path, [row()], ok)] == ["OK"]
    wrong = lambda url: (200, '{"price": "39"} InStock')  # noqa: E731
    assert [r["status"] for r in run(tmp_path, [row()], wrong)] == ["BROKEN"]
    gone = lambda url: (200, "<html>sold out</html>")  # noqa: E731
    assert [r["status"] for r in run(tmp_path, [row()], gone)] == ["BROKEN"]


def test_rate_limit_is_unknown_not_a_dead_listing_and_old_or_far_pins_are_skipped(tmp_path):
    limited = lambda url: (429, "")  # noqa: E731
    assert [r["status"] for r in run(tmp_path, [row()], limited)] == ["UNKNOWN"]
    rs = [row(day="2026-11-01"), row(day="2026-12-30"), row(day="2026-11-09")]
    assert len(run(tmp_path, rs, lambda url: (200, '{"price": "29"} InStock'))) == 1


def test_untagged_link_is_a_warning(tmp_path):
    r = run(tmp_path, [row(link="https://x.gumroad.com/l/a")], lambda url: (200, '{"price": "29"} InStock'))[0]
    assert r["status"] == "WARN" and "utm_content" in r["detail"]

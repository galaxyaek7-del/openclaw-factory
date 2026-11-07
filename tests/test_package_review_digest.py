import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import package_review_digest as d  # noqa: E402


def pkg(status="AWAITING_FOUNDER_REVIEW", brief_price=29, final=39):
    return {"status": status, "created_at": "2026-11-07T01:00:00Z", "brief": {"title": "T", "audience": "A", "price": brief_price, "topic": "x"},
            "pricing": {"price_usd": final}, "listing": {"title": "Cost Calculator"}, "qa": {"verdict": "PASS"}}


def test_only_packages_awaiting_review_are_loaded(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps(pkg()), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps(pkg(status="PUBLISHED")), encoding="utf-8")
    (tmp_path / "c.json").write_text("{broken", encoding="utf-8")
    assert [p["_file"] for p in d.load_packages(tmp_path)] == ["a.json"]


def test_price_disagreement_and_overlap_are_shown_not_hidden():
    p = pkg(); p["_file"] = "a.json"
    row = d.describe(p, ["Cost Calculator Pro"], lambda c: "strong", lambda t, titles: (titles[0], 0.7))
    assert row["final_price"] == 39 and row["price_note"] == "brief said 29" and "70%" in row["overlap"]
    md = d.render([row])
    assert "$39 (brief said 29)" in md and "Nothing here is approved" in md

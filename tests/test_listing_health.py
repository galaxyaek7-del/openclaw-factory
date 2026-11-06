import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import listing_health as lh  # noqa: E402


def prod(slug="a", name="Good Title", price=1900, desc=None, tags=("x", "y", "z"), cover="https://c/x.png", published=True):
    return {"short_url": f"https://s/l/{slug}", "name": name, "price": price, "published": published,
            "description": desc if desc is not None else "A real description. " * 20, "tags": list(tags), "preview_url": cover}


def kinds(*products):
    return sorted((f["kind"], f["slug"]) for f in lh.assess(list(products)))


def test_a_healthy_listing_has_no_findings():
    assert kinds(prod()) == []


def test_each_defect_found_manually_on_2026_11_06_is_caught():
    moji = "incident " + "—".encode("utf-8").decode("cp1252") + " every template"
    assert ("MOJIBAKE", "m") in kinds(prod("m", desc=moji + " x" * 150))
    assert ("PAYABLE_ZERO", "z") in kinds(prod("z", price=0))
    assert ("TEST_OR_WITHDRAWN_NAME", "t") in kinds(prod("t", name="[Unavailable] AI Workflow QA"), prod("t2", name="GALAXY FORGE API TEST - DO NOT BUY - DELETE ME"))
    both = kinds(prod("d1", name="The 5-Minute Reset"), prod("d2", name="the 5-minute reset"))
    assert ("DUPLICATE_TITLE", "d1") in both and ("DUPLICATE_TITLE", "d2") in both


def test_other_defects_and_severities():
    f = {(x["kind"], x["severity"]) for x in lh.assess([prod("a", desc="short", cover="", tags=("x",)),
                                                         prod("b", desc="Ready [FOUNDER INPUT REQUIRED] " + "x" * 300)])}
    assert {("SHORT_DESCRIPTION", "MEDIUM"), ("NO_COVER", "MEDIUM"), ("FEW_TAGS", "LOW"), ("PLACEHOLDER_TEXT", "HIGH")} <= f


def test_unpublished_and_deleted_listings_are_ignored_and_file_presence_is_not_judged():
    p = prod("u", price=0, published=False)
    q = prod("w"); q["file_info"] = {}  # multi-file product: an empty list-level file_info is normal
    assert kinds(p, q) == []


def test_run_once_writes_the_report_once_a_day(tmp_path):
    out, st = tmp_path / "o.json", tmp_path / "s.json"
    r = lh.run_once("2026-11-06", products=[prod(price=0)], out=out, state=st)
    assert r["action"] == "findings" and json.loads(out.read_text())["summary"]["by_severity"] == {"CRITICAL": 1}
    assert lh.run_once("2026-11-06", products=[prod()], out=out, state=st)["action"] == "none"
    assert lh.run_once("2026-11-06", products=[prod()], out=out, state=st, force=True)["action"] == "ok"

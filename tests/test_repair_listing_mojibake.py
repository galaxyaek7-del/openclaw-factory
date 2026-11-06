import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import repair_listing_mojibake as rm  # noqa: E402


def mojibake(s):
    return s.encode("utf-8").decode("cp1252")


def test_em_dash_en_dash_and_pound_are_restored():
    src = "incident " + mojibake("—") + " every template $39" + mojibake("–") + "$99 around " + mojibake("£") + "200/month"
    fixed, changes = rm.fix_text(src)
    assert fixed == "incident — every template $39–$99 around £200/month" and len(changes) == 3


def test_correct_text_and_other_scripts_are_never_touched():
    for ok in ("plain ascii", "already — right £200", "مرحبا بالعالم", "café résumé", "â lone letter"):
        assert rm.fix_text(ok) == (ok, [])


def test_second_pass_changes_nothing():
    once, _ = rm.fix_text("a " + mojibake("—") + " b " + mojibake("’"))
    assert rm.fix_text(once) == (once, [])


def test_the_corrupted_char_followed_by_ordinary_text_keeps_the_text():
    fixed, ch = rm.fix_text(mojibake("—") + "x")
    assert fixed == "—x" and ch == [(mojibake("—"), "—")]


def test_plan_reports_only_listings_with_a_defect_and_never_a_new_description_in_the_report():
    class GP:
        def list_products(self, t):
            return [{"id": "1", "short_url": "https://s/l/aaa"}, {"id": "2", "short_url": "https://s/l/bbb"}]

        def get_product(self, t, pid):
            return {"name": "N", "published": True, "description": ("x " + mojibake("—")) if pid == "1" else "fine"}
    acts = rm.plan("t", GP())
    assert [a["slug"] for a in acts] == ["aaa"] and acts[0]["new_description"] == "x —" and acts[0]["result"] == "PLANNED"

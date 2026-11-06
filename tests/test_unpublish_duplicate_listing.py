import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import unpublish_duplicate_listing as ud  # noqa: E402


class GP:
    def __init__(self, items):
        self.items = items
        self.disabled = []

    def list_products(self, t):
        return [{"id": k, "short_url": "https://s/l/" + v["slug"]} for k, v in self.items.items()]

    def get_product(self, t, pid):
        return dict(self.items[pid])

    def disable_product(self, t, pid):
        self.disabled.append(pid)
        self.items[pid]["published"] = False


def item(slug, name="Same Title", published=True, sales=0):
    return {"slug": slug, "name": name, "published": published, "sales_count": sales}


def test_a_true_duplicate_with_no_sales_is_planned_and_applied_with_readback():
    gp = GP({"a": item("old"), "b": item("keep")})
    p = ud.plan("t", gp, "old", "keep")
    assert p["result"] == "PLANNED"
    r = ud.apply("t", gp, p)
    assert r["result"] == "PASS" and gp.disabled == ["a"] and r["keep_published"] is True


def test_refusals():
    for items, args, why in [
        ({"a": item("old", sales=1), "b": item("keep")}, ("old", "keep"), "sales"),
        ({"a": item("old", name="X"), "b": item("keep", name="Y")}, ("old", "keep"), "titles differ"),
        ({"a": item("old"), "b": item("keep", published=False)}, ("old", "keep"), "nothing would remain"),
        ({"a": item("old")}, ("old", "keep"), "not found"),
        ({"a": item("old"), "b": item("keep")}, ("old", "old"), "same"),
    ]:
        gp = GP(items)
        r = ud.plan("t", gp, *args)
        assert r["result"] == "REFUSED" and why in r["reason"], (r, why)
        assert gp.disabled == []


def test_an_already_unpublished_listing_is_left_alone():
    gp = GP({"a": item("old", published=False), "b": item("keep")})
    assert ud.plan("t", gp, "old", "keep")["result"] == "ALREADY_UNPUBLISHED"

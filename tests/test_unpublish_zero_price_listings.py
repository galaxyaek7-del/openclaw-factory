import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import unpublish_zero_price_listings as up  # noqa: E402


class FakeGP:
    def __init__(self, products, fail_to_unpublish=False):
        self.p = products
        self.disabled = []
        self.fail = fail_to_unpublish

    def list_products(self, token):
        return [{"id": k, "short_url": "https://x.gumroad.com/l/" + v["slug"]} for k, v in self.p.items()]

    def get_product(self, token, pid):
        return dict(self.p[pid])

    def disable_product(self, token, pid):
        self.disabled.append(pid)
        if not self.fail:
            self.p[pid]["published"] = False


def prod(slug, published=True, price=0, sales=0):
    return {"slug": slug, "name": slug, "published": published, "price": price, "sales_count": sales}


def test_only_the_three_zero_price_listings_are_planned():
    gp = FakeGP({"a": prod("iaiyt"), "b": prod("wteork"), "c": prod("owtmpe"), "d": prod("othr", price=1900)})
    plan = up.plan("t", gp)
    assert [a["slug"] for a in plan] == ["iaiyt", "wteork", "owtmpe"] and all(a["result"] == "PLANNED" for a in plan)


def test_a_listing_with_sales_or_a_price_is_left_untouched():
    gp = FakeGP({"a": prod("iaiyt", sales=1), "b": prod("wteork", price=500), "c": prod("owtmpe", published=False)})
    assert [a["result"] for a in up.plan("t", gp)] == ["SKIPPED", "SKIPPED", "ALREADY_UNPUBLISHED"]


def test_apply_reads_back_and_passes():
    gp = FakeGP({"a": prod("iaiyt"), "b": prod("wteork"), "c": prod("owtmpe")})
    done = up.apply("t", gp, up.plan("t", gp))
    assert [a["result"] for a in done] == ["PASS"] * 3 and gp.disabled == ["a", "b", "c"]


def test_a_failed_readback_stops_the_run():
    gp = FakeGP({"a": prod("iaiyt"), "b": prod("wteork"), "c": prod("owtmpe")}, fail_to_unpublish=True)
    done = up.apply("t", gp, up.plan("t", gp))
    assert done[0]["result"] == "FAILED" and gp.disabled == ["a"] and len(done) == 1


def test_disable_product_is_behind_the_write_gate(monkeypatch):
    from channels import gumroad_publisher as gp, write_gate
    monkeypatch.delenv("FACTORY_LIVE_PUBLISH", raising=False)
    try:
        gp.disable_product("tok", "abc")
        raise AssertionError("must be blocked")
    except write_gate.WriteNotAuthorized:
        pass

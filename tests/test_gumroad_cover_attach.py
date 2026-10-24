"""Listing covers: which products get one, what the cover may show, and the
attach plan that runs before any live write. No network, no Gumroad call."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import attach_listing_covers as alc  # noqa: E402
import build_listing_covers as blc  # noqa: E402


def product(pid, **kw):
    p = {"id": pid, "name": f"Product {pid}", "published": True, "deleted": False, "covers": [],
         "description": "<p>Does one useful thing. More detail.</p>", "short_url": f"https://x.gumroad.com/l/{pid}",
         "category_label": "Other"}
    p.update(kw)
    return p


class TestBuild(unittest.TestCase):
    def test_only_published_coverless_non_withdrawn_listings(self):
        catalog = [product("a"), product("b", covers=[{"url": "u"}]), product("c", published=False),
                   product("d", name="[Unavailable] Old thing"), product("e", description="<p>WITHDRAWN</p>"),
                   product("f", name="API TEST - DO NOT BUY - DELETE ME")]
        with tempfile.TemporaryDirectory() as d:
            m = blc.build(catalog, out_dir=Path(d))
            self.assertEqual(sorted(m["covers"]), ["a"])
            self.assertTrue((Path(d) / "a.png").is_file())
        self.assertEqual(m["size"], [1280, 720])

    def test_cover_carries_no_price(self):
        # the cover is drawn from name, first sentence and category only
        import inspect
        self.assertNotIn("price", inspect.signature(blc.render).parameters)
        self.assertEqual(blc._first_sentence("One. Two."), "One.")


class TestAttachPlan(unittest.TestCase):
    def test_plan_skips_everything_that_changed(self):
        covers = {k: {"name": k, "public_url": f"https://site/{k}.png"} for k in ("a", "b", "c", "gone")}
        live = {"a": product("a"), "b": product("b", covers=[{"url": "u"}]), "c": product("c", published=False)}
        got = {t["id"]: (t["action"], t.get("why")) for t in alc.plan(covers, live)}
        self.assertEqual(got["a"], ("ATTACH", None))
        self.assertEqual(got["b"], ("SKIP", "already has a cover"))
        self.assertEqual(got["c"], ("SKIP", "not published"))
        self.assertEqual(got["gone"], ("SKIP", "not in the live catalog"))

    def test_second_image_only_over_our_own_single_cover(self):
        audit = {"items": [
            {"product_id": "a", "title": "A", "cover_file": "reports/covers/gumroad/a.png", "matched_book_cover": "books/covers/a.png"},
            {"product_id": "b", "title": "B", "cover_file": "reports/covers/gumroad/b.png", "matched_book_cover": "books/covers/b.png"},
            {"product_id": "c", "title": "C", "cover_file": "reports/covers/gumroad/c.png", "matched_book_cover": "books/covers/c.png"},
            {"product_id": "d", "title": "D", "cover_file": "reports/covers/gumroad/d.png", "matched_book_cover": None}]}
        live = {"a": product("a", covers=[{"url": "ours"}]), "b": product("b", covers=[{"url": "x"}, {"url": "y"}]),
                "c": product("c", covers=[{"url": "someone else's"}]), "d": product("d", covers=[{"url": "ours"}])}
        got = {t["id"]: (t["action"], t.get("why")) for t in alc.plan_second(audit, live, ours={"a", "b"})}
        self.assertEqual(got["a"], ("ATTACH", None))
        self.assertEqual(got["b"][0], "SKIP")                      # two covers already
        self.assertEqual(got["c"], ("SKIP", "its cover was not attached by this script"))
        self.assertNotIn("d", got)                                 # no real book cover matched
        a = [t for t in alc.plan_second(audit, live, ours={"a"}) if t["action"] == "ATTACH"][0]
        self.assertEqual((a["expected"], a["cover"]), (1, alc.PAGES_ROOT + "reports/covers/gumroad/a.png"))

    def test_authorization_is_recorded_and_scoped(self):
        self.assertIn("2026-10-24", alc.AUTHORIZATION)
        self.assertIn("covers only", alc.AUTHORIZATION)


if __name__ == "__main__":
    unittest.main()

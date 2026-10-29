"""Every product landing page must describe itself the way it really is.

Cycle 88: two tool pages (food truck cost estimator, SaaS waste estimator)
shipped with no Product structured data while their eleven siblings had it.
Nothing in the suite noticed -- the pages looked fine to a reader, and the
only way to see the gap was to walk every JSON-LD block and compare it with
catalog.json. The other half of the same audit is a truth check: a price in
markup is a claim. A block that says $12 for a product the catalog sells for
$15 is a fabricated claim, not decoration.

So this file locks in both directions -- the blocks that exist must state the
real price, and the landing pages that carry them must not silently lose
theirs -- and proves the check itself fails on a bad fixture, because a guard
that has never been seen to fail is not known to work.
"""

from __future__ import annotations

import glob
import json
import os
import re
import tempfile
import unittest

SITE = os.path.join("customer_site")
REPO = os.path.abspath(".")
CATALOG = os.path.join(SITE, "catalog.json")
PADDLE = os.path.join("data", "paddle_products.json")
SITE_BASE = "https://galaxyaek7-del.github.io/openclaw-factory/"
LD_PATTERN = re.compile(
    r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.S | re.I
)
GUMROAD = re.compile(r"https://[a-z0-9.-]*gumroad\.com/l/[A-Za-z0-9_-]+")


def load_catalog(path=CATALOG):
    """catalog.json -> {normalized gumroad url: product}."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)["data"]
    return {normalize_url(p["url"]): p for p in data["products"]}


def load_paddle(path=PADDLE):
    """data/paddle_products.json -> {product_id: real price in USD}.

    Products sold through Paddle carry a `pro_...` id and no gumroad link, so
    their price can only be checked against this record -- the same record
    that created the live product.
    """
    with open(path, encoding="utf-8") as fh:
        rows = json.load(fh)
    return {r["product_id"]: r["price"] for r in rows if r.get("product_id") and r.get("price")}


def normalize_url(url):
    return url.split("?")[0].rstrip("/")


def parse_blocks(html):
    """Return (products, problems) for every JSON-LD block on one page."""
    products, problems = [], []
    for raw in LD_PATTERN.findall(html):
        try:
            data = json.loads(raw)
        except ValueError as exc:
            problems.append("unparseable JSON-LD: %s" % exc)
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and item.get("@type") == "Product":
                products.append(item)
    return products, problems


def check_site(site_dir, catalog, paddle=None, repo_root=None):
    """Return a list of human-readable problems; empty means the site is honest."""
    problems = []
    paddle = paddle or {}
    repo_root = repo_root or os.path.dirname(os.path.abspath(site_dir))
    for path in sorted(glob.glob(os.path.join(site_dir, "**", "*.html"), recursive=True)):
        name = os.path.relpath(path, site_dir)
        with open(path, encoding="utf-8") as fh:
            html = fh.read()
        products, block_problems = parse_blocks(html)
        problems.extend("%s: %s" % (name, p) for p in block_problems)

        for product in products:
            problems.extend(
                "%s: %s" % (name, p)
                for p in _check_product(product, repo_root, catalog, paddle)
            )

        if _is_landing_page(name):
            links = {normalize_url(u) for u in GUMROAD.findall(html)}
            sells_catalog_product = links & set(catalog)
            if sells_catalog_product and not products:
                problems.append(
                    "%s: sells %s but declares no Product structured data"
                    % (name, ", ".join(sorted(sells_catalog_product)))
                )
    return problems


def _is_landing_page(name):
    """The one-page-per-product family that carries Product markup."""
    base = os.path.basename(name)
    return base.startswith("tool-") or base.startswith("turo-")


def _check_product(product, repo_root, catalog, paddle):
    problems = []
    for field in ("name", "description", "image", "url", "sku", "offers"):
        if not product.get(field):
            problems.append("Product block is missing %r" % field)
    offers = product.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    if not offers.get("availability"):
        problems.append("Product offer is missing 'availability'")
    # A buyable offer has to state a price and where to buy it. An unavailable
    # one must not invent either: the honest state for a held product is "no
    # price claim, no checkout url", not a number nobody can act on.
    in_stock = str(offers.get("availability") or "").endswith("InStock")
    if in_stock:
        for field in ("price", "priceCurrency", "url"):
            if offers.get(field) in (None, ""):
                problems.append("in-stock Product offer is missing %r" % field)
    elif offers.get("price") not in (None, "") and not offers.get("priceCurrency"):
        problems.append("Product offer states a price but no 'priceCurrency'")

    offer_url = normalize_url(str(offers.get("url") or ""))
    known = catalog.get(offer_url)
    if offers.get("url") and not known:
        problems.append("offer url %s is not a catalog product" % offers.get("url"))
    real_price = None
    if known:
        real_price = known["price_cents"] / 100.0
    elif product.get("sku") in paddle:
        real_price = paddle[product["sku"]]
    if real_price is not None and offers.get("price") is not None:
        try:
            stated = float(offers["price"])
        except (TypeError, ValueError):
            problems.append("offer price %r is not a number" % offers.get("price"))
        else:
            if abs(stated - real_price) > 0.005:
                problems.append(
                    "offer price %s does not match the recorded price %.2f for %s"
                    % (offers["price"], real_price, product.get("sku") or offer_url)
                )

    image = str(product.get("image") or "")
    if image.startswith(SITE_BASE):
        local = os.path.join(repo_root, image[len(SITE_BASE):])
        if not os.path.exists(local):
            problems.append("image %s does not exist in the repository" % image)
    elif image and not image.startswith("http"):
        problems.append("image %r is not an absolute url" % image)
    return problems


class TestToolStructuredData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()
        cls.paddle = load_paddle()

    def test_the_real_site_is_consistent(self):
        self.assertEqual(check_site(SITE, self.catalog, self.paddle, REPO), [])

    def test_landing_pages_all_declare_a_product(self):
        for path in sorted(glob.glob(os.path.join(SITE, "tool-*.html"))
                           + glob.glob(os.path.join(SITE, "turo-*.html"))):
            with open(path, encoding="utf-8") as fh:
                products, _ = parse_blocks(fh.read())
            self.assertTrue(products, "%s declares no Product block" % path)

    def test_a_fabricated_price_is_rejected(self):
        product = self.catalog[normalize_url(
            "https://aekraft.gumroad.com/l/cdfdcy")]
        site = self._fixture({
            "tool-x.html": self._page(
                "https://aekraft.gumroad.com/l/cdfdcy",
                price="%.2f" % ((product["price_cents"] / 100.0) - 20),
            )
        })
        problems = check_site(site, self.catalog)
        self.assertTrue(any("does not match the recorded price" in p for p in problems), problems)

    def test_a_landing_page_that_lost_its_block_is_rejected(self):
        site = self._fixture({
            "tool-y.html": '<html><head><title>y</title></head><body>'
                           '<a href="https://aekraft.gumroad.com/l/cdfdcy">buy</a></body></html>'
        })
        problems = check_site(site, self.catalog)
        self.assertTrue(any("declares no Product structured data" in p for p in problems), problems)

    def test_an_unparseable_block_is_rejected(self):
        site = self._fixture({
            "tool-z.html": '<script type="application/ld+json">{not json}</script>'
        })
        problems = check_site(site, self.catalog)
        self.assertTrue(any("unparseable JSON-LD" in p for p in problems), problems)

    def test_an_image_that_is_not_in_the_repository_is_rejected(self):
        block = self._page("https://aekraft.gumroad.com/l/cdfdcy", price="59.00")
        broken = block.replace("assets/og-default.png", "assets/does-not-exist.png")
        site = self._fixture({"tool-v.html": broken})
        problems = check_site(site, self.catalog)
        self.assertTrue(any("does not exist in the repository" in p for p in problems), problems)

    def test_an_offer_for_an_unknown_product_is_rejected(self):
        site = self._fixture({
            "tool-w.html": self._page("https://aekraft.gumroad.com/l/doesnotexist", price="9.00")
        })
        problems = check_site(site, self.catalog)
        self.assertTrue(any("is not a catalog product" in p for p in problems), problems)

    def _fixture(self, pages):
        root = tempfile.mkdtemp()
        for name, html in pages.items():
            with open(os.path.join(root, name), "w", encoding="utf-8") as fh:
                fh.write(html)
        return root

    def _page(self, offer_url, price):
        block = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "x",
            "description": "x",
            "image": "https://galaxyaek7-del.github.io/openclaw-factory/customer_site/assets/og-default.png",
            "url": "https://galaxyaek7-del.github.io/openclaw-factory/customer_site/tool-x.html",
            "sku": "X-1",
            "offers": {
                "@type": "Offer",
                "price": price,
                "priceCurrency": "USD",
                "availability": "https://schema.org/InStock",
                "url": offer_url,
            },
        }
        return ('<script type="application/ld+json">%s</script>'
                % json.dumps(block, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()

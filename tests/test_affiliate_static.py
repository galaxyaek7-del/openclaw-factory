"""GF-19: static affiliate catalog must be valid, honest, and Pages-safe."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from affiliate_commerce.static_catalog import StaticCatalogError, build_static_catalog


def test_catalog_schema_and_ranking():
    c = build_static_catalog()
    assert c["category"] == "standing_desk_converters"
    assert c["count"] == len(c["products"]) == 4
    for p in c["products"]:
        for f in ("id", "name", "description", "price_usd", "rating",
                  "rating_count", "url", "affiliate_attributed"):
            assert f in p, f
        assert p["url"].startswith("https://www.amazon.com/dp/")
        assert isinstance(p["price_usd"], (int, float))
    scores = [p["rating"] * __import__("math").log10(p["rating_count"] + 1)
              for p in c["products"]]
    assert scores == sorted(scores, reverse=True), "ranking order must match weighted formula"


def test_no_tag_invented_while_unset(monkeypatch):
    monkeypatch.delenv("AMAZON_ASSOCIATE_TAG", raising=False)
    c = build_static_catalog()
    assert c["tag_configured"] is False
    for p in c["products"]:
        assert "tag=" not in p["url"]
        assert p["affiliate_attributed"] is False


def test_empty_category_yields_empty_not_error():
    c = build_static_catalog(category="no_such_category")
    assert c["products"] == [] and c["count"] == 0


def test_malformed_product_raises(monkeypatch):
    import affiliate_commerce.products as prod
    bad = {"id": "X", "name": "Bad"}  # missing price/rating/etc.
    monkeypatch.setattr(prod, "PRODUCTS", [dict(bad, category="standing_desk_converters")])
    with pytest.raises(StaticCatalogError):
        build_static_catalog()


def test_page_contract_fields_present():
    """Every field the page JS reads must exist in the static payload."""
    c = build_static_catalog()
    assert c["ranking_method"] and c["source"] and c["verified_at"]
    for p in c["products"]:
        assert isinstance(p["list_price_usd"], (int, float)) or p["list_price_usd"] is None


def test_page_has_no_server_product_dependency():
    text = (ROOT / "customer_site" / "affiliate-standing-desks.html").read_text(encoding="utf-8")
    # No live fetch of server routes (comments may still name them).
    assert "fetch('/api/affiliate" not in text
    assert 'fetch("/api/affiliate' not in text
    assert "'/api/affiliate/click/' +" not in text
    assert "affiliate-products.json" in text

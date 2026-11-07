import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from channels import registry, shopify_arm, shopify_publisher as sp  # noqa: E402
from channels.base_arm import ArmStatus  # noqa: E402
from channels.write_gate import WriteNotAuthorized  # noqa: E402

SPEC = {"title": "ADU Feasibility Calculator", "description": "Line one.\nLine <two>.", "price_cents": 2900, "tags": ["adu", "calculator"], "file_path": "x.xlsx"}
PRODUCT = SimpleNamespace(title="ADU Feasibility Calculator", description="Line one.", price_usd=29.0, file_path="x.xlsx", needs_pricing=False, tags=["adu"])


def env_file(tmp_path, domain="shop-one.myshopify.com", token="shpat_SECRET_123"):
    p = tmp_path / ".env"
    p.write_text(f"SHOPIFY_STORE_DOMAIN={domain}\nSHOPIFY_ADMIN_TOKEN={token}\n", encoding="utf-8")
    return p


class Fake:
    def __init__(self, status="DRAFT", user_errors=None):
        self.calls, self.status, self.user_errors = [], status, user_errors

    def __call__(self, url, headers, payload, timeout=30):
        self.calls.append((url, headers, payload))
        if "productCreate" in payload["query"]:
            return {"data": {"productCreate": {"product": {"id": "gid://shopify/Product/1", "title": "t", "status": self.status,
                                                          "variants": {"nodes": [{"id": "gid://shopify/ProductVariant/9"}]}},
                                               "userErrors": self.user_errors or []}}}
        return {"data": {"productVariantsBulkUpdate": {"productVariants": [{"id": "v", "price": "29.00"}], "userErrors": []}}}


def test_registered_and_registered_arm_is_unavailable_without_credentials(monkeypatch):
    monkeypatch.delenv("SHOPIFY_STORE_DOMAIN", raising=False)
    monkeypatch.delenv("SHOPIFY_ADMIN_TOKEN", raising=False)
    monkeypatch.setattr(sp, "load_config", lambda env_path=None: (_ for _ in ()).throw(sp.ConfigError("none")))
    assert registry.get("shopify").name == "shopify"
    assert shopify_arm.ShopifyArm().status() is ArmStatus.UNAVAILABLE


def test_product_input_is_a_draft_escapes_html_and_rejects_unpriced():
    i = sp.build_product_input(SPEC)
    assert i["status"] == "DRAFT" and "&lt;two&gt;" in i["descriptionHtml"] and i["tags"] == ["adu", "calculator"]
    for bad in ({**SPEC, "price_cents": 0}, {**SPEC, "price_cents": None}, {**SPEC, "title": " "}):
        with pytest.raises(sp.ConfigError):
            sp.build_product_input(bad)


def test_domain_must_be_a_myshopify_host(tmp_path):
    with pytest.raises(sp.ConfigError):
        sp.load_config(env_file(tmp_path, domain="evil.example.com"))
    assert sp.load_config(env_file(tmp_path))[0] == "shop-one.myshopify.com"


def test_dry_run_never_touches_the_network_and_validates_shape():
    boom = Fake()
    r = shopify_arm.ShopifyArm().publish(PRODUCT, dry_run=True, transport=boom)
    assert r.ok and r.dry_run and boom.calls == []
    bad = SimpleNamespace(**{**PRODUCT.__dict__, "title": ""})
    assert not shopify_arm.ShopifyArm().publish(bad, dry_run=True).ok


def test_live_is_blocked_by_the_write_gate_first_then_by_clearance(monkeypatch, tmp_path):
    monkeypatch.delenv("FACTORY_LIVE_PUBLISH", raising=False)
    fake = Fake()
    with pytest.raises(WriteNotAuthorized):
        sp.create_draft_product(SPEC, publication_clearance={"kind": "founder_approval"}, transport=fake, env_path=env_file(tmp_path))
    assert fake.calls == []
    monkeypatch.setenv("FACTORY_LIVE_PUBLISH", "true")
    from channels.publication_clearance import PublicationNotCleared
    with pytest.raises(PublicationNotCleared):
        sp.create_draft_product(SPEC, publication_clearance=None, transport=fake, env_path=env_file(tmp_path))
    assert fake.calls == []


def test_live_creates_a_draft_with_price_and_never_attaches_a_file_or_activates(monkeypatch, tmp_path):
    monkeypatch.setenv("FACTORY_LIVE_PUBLISH", "true")
    monkeypatch.setattr("channels.publication_clearance.require_clearance", lambda c, s: {"kind": "test"})
    fake = Fake()
    out = sp.create_draft_product(SPEC, publication_clearance={"kind": "x"}, transport=fake, env_path=env_file(tmp_path))
    assert out["status"] == "DRAFT" and out["price"] == "29.00" and out["delivery_file_attached"] is False
    assert len(fake.calls) == 2 and fake.calls[0][1]["X-Shopify-Access-Token"] == "shpat_SECRET_123"
    assert "ACTIVE" not in str(fake.calls)


def test_a_non_draft_reply_or_user_errors_fail_closed_without_leaking_the_token(monkeypatch, tmp_path):
    monkeypatch.setenv("FACTORY_LIVE_PUBLISH", "true")
    monkeypatch.setattr("channels.publication_clearance.require_clearance", lambda c, s: {"kind": "test"})
    with pytest.raises(sp.ShopifyApiError):
        sp.create_draft_product(SPEC, publication_clearance={"kind": "x"}, transport=Fake(status="ACTIVE"), env_path=env_file(tmp_path))
    with pytest.raises(sp.ShopifyApiError) as e:
        sp.create_draft_product(SPEC, publication_clearance={"kind": "x"}, transport=Fake(user_errors=[{"message": "bad"}]), env_path=env_file(tmp_path))
    assert "shpat_SECRET_123" not in str(e.value)

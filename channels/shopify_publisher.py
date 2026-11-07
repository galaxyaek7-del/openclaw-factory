# -*- coding: utf-8 -*-
"""Galaxy Forge: Shopify publisher (2026-11-07). Standalone, injectable transport, fail-closed.

What it does: creates ONE product on a Shopify store as a DRAFT through the Admin GraphQL API (productCreate, then the variant price).
What it deliberately does NOT do:
  * it never activates (publishes to the storefront): a draft is invisible to buyers; activation stays a separate, human-approved step;
  * it does not attach the downloadable file: Shopify delivers digital files through the free "Digital Downloads" app, which has no
    documented public API for attaching a file. File delivery: NOT IMPLEMENTED. The result says so, and a draft without a file must not
    be activated;
  * it spends nothing: Shopify itself is NOT free (3 days trial, then roughly $1/month for 3 months, then plan pricing: SECONDARY
    sources, verify on shopify.com/pricing). Starting the paid plan is a founder decision, never this code.

Credentials (names only here): SHOPIFY_STORE_DOMAIN (<shop>.myshopify.com), SHOPIFY_ADMIN_TOKEN (Admin API access token of a custom
app with write_products). Both come from the environment or .env; the token is sent as X-Shopify-Access-Token, never logged.

Every live call passes channels/write_gate (FACTORY_LIVE_PUBLISH) and channels/publication_clearance (per-product founder approval
or the central Quality Gate) BEFORE any network I/O. No override.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

try:
    from .env_config import read_env_value
except ImportError:  # run as a script
    from env_config import read_env_value

API_VERSION = "2025-01"  # SECONDARY: pin and re-verify when the live call is first made
DOMAIN_RE = re.compile(r"^[a-z0-9][a-z0-9-]*\.myshopify\.com$")
MAX_TITLE, MAX_TAGS, MAX_TAG_LEN = 255, 250, 255  # Shopify's documented product limits (secondary; conservative use below)
VENDOR = "Galaxy Forge"
PRODUCT_TYPE = "Digital product"


class ConfigError(Exception):
    """Missing or invalid local configuration: never a Shopify API error."""


class ShopifyApiError(RuntimeError):
    """The API answered with errors or an unexpected shape."""


def load_config(env_path=None):
    domain = (read_env_value("SHOPIFY_STORE_DOMAIN", env_path) if env_path else read_env_value("SHOPIFY_STORE_DOMAIN")) or ""
    token = (read_env_value("SHOPIFY_ADMIN_TOKEN", env_path) if env_path else read_env_value("SHOPIFY_ADMIN_TOKEN")) or ""
    domain, token = domain.strip().lower(), token.strip()
    if not domain or not token:
        raise ConfigError("SHOPIFY_STORE_DOMAIN and SHOPIFY_ADMIN_TOKEN are not both set")
    if not DOMAIN_RE.match(domain):
        raise ConfigError("SHOPIFY_STORE_DOMAIN must look like <shop>.myshopify.com")
    return domain, token


def build_product_input(spec):
    """The productCreate input for a DRAFT product. Validates before anything leaves the machine."""
    title = (spec.get("title") or "").strip()
    if not title or len(title) > MAX_TITLE:
        raise ConfigError(f"title must be 1-{MAX_TITLE} characters")
    try:
        price_cents = int(spec.get("price_cents"))
    except (TypeError, ValueError):
        raise ConfigError("price_cents must be an integer")
    if price_cents <= 0:
        raise ConfigError("price_cents must be > 0 (no free or unpriced listing)")
    tags = [t.strip()[:MAX_TAG_LEN] for t in (spec.get("tags") or []) if str(t).strip()][:MAX_TAGS]
    desc = (spec.get("description") or "").strip()
    body = "".join(f"<p>{html.escape(p)}</p>" for p in desc.split("\n") if p.strip())
    return {"title": title, "descriptionHtml": body, "vendor": VENDOR, "productType": PRODUCT_TYPE, "tags": tags, "status": "DRAFT"}


PRODUCT_CREATE = """mutation($product: ProductCreateInput!) {
  productCreate(product: $product) { product { id title status variants(first: 1) { nodes { id } } } userErrors { field message } }
}"""
VARIANT_PRICE = """mutation($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkUpdate(productId: $productId, variants: $variants) { productVariants { id price } userErrors { field message } }
}"""


def default_transport(url, headers, payload, timeout=30):
    import requests
    r = requests.post(url, headers=headers, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _graphql(transport, domain, token, query, variables):
    url = f"https://{domain}/admin/api/{API_VERSION}/graphql.json"
    reply = transport(url, {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}, {"query": query, "variables": variables})
    if not isinstance(reply, dict) or reply.get("errors"):
        raise ShopifyApiError("Shopify GraphQL returned errors")  # the error text is not echoed: it can quote request data
    return reply.get("data") or {}


def create_draft_product(spec, *, publication_clearance=None, transport=default_transport, env_path=None):
    """Create a DRAFT product with its price. Returns {product_id, status, delivery_file_attached}. Raises on any problem."""
    from channels.write_gate import require_platform_write
    require_platform_write("shopify", "product_create")  # FIRST: no write without authorization
    from channels.publication_clearance import require_clearance
    require_clearance(publication_clearance, spec or {})
    domain, token = load_config(env_path)
    product_input = build_product_input(spec)
    price = f"{int(spec['price_cents']) / 100:.2f}"
    data = _graphql(transport, domain, token, PRODUCT_CREATE, {"product": product_input})
    pc = data.get("productCreate") or {}
    if pc.get("userErrors"):
        raise ShopifyApiError("productCreate refused: " + "; ".join(str(e.get("message"))[:80] for e in pc["userErrors"][:3]))
    prod = pc.get("product") or {}
    pid = prod.get("id")
    nodes = ((prod.get("variants") or {}).get("nodes")) or []
    if not pid or not nodes or prod.get("status") != "DRAFT":
        raise ShopifyApiError("productCreate did not return a DRAFT product with a variant")
    vd = _graphql(transport, domain, token, VARIANT_PRICE, {"productId": pid, "variants": [{"id": nodes[0]["id"], "price": price}]})
    errs = (vd.get("productVariantsBulkUpdate") or {}).get("userErrors")
    if errs:
        raise ShopifyApiError("variant price refused: " + "; ".join(str(e.get("message"))[:80] for e in errs[:3]))
    return {"product_id": pid, "status": "DRAFT", "price": price, "delivery_file_attached": False,
            "note": "DRAFT only. Digital file delivery NOT IMPLEMENTED (attach the file in the Digital Downloads app). Do not activate without it."}

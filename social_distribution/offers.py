"""Cross-arm offer registry: every distributable thing, with an evidence-based state.

A derived view, not a new source of truth. It joins:
  data/product_registry.json      Gumroad products (stable ids, verified listing states)
  Gumroad GET /v2/products        description and tags (read-only; injected in tests)
  customer_site/*.html on origin/main   the public site (GitHub Pages)
  affiliate.registry              affiliate programs and approvals
  video_studio/projects           rendered media and their rights manifests

Eligibility for a campaign is ELIGIBLE only when the destination is verified
live and nothing (rights, approval, availability) blocks it; everything else
says exactly why not.
"""
from __future__ import annotations

import html
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import sys

_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
import hold_policy  # noqa: E402  (the one source of truth for products that must not be promoted)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "distribution_offers.json"
SITE_BASE = "https://galaxyaek7-del.github.io/openclaw-factory/customer_site/"

ELIGIBLE, NOT_ELIGIBLE, NEEDS_REVIEW = "ELIGIBLE", "NOT_ELIGIBLE", "NEEDS_REVIEW"

PROHIBITED_CLAIMS = [
    "income or earnings promises", "guaranteed results", "invented testimonials or reviews",
    "invented statistics or customer counts", "best-selling / #1 / trusted-by claims",
    "fake scarcity or deadlines", "legal, tax or financial advice framed as personal advice",
]

PLATFORMS_BY_TYPE = {
    "digital_product": ["linkedin", "x", "instagram", "tiktok"],
    "content_asset": ["linkedin", "x"],
    "service": ["linkedin"],
    "affiliate_offer": ["linkedin", "x"],
    "media_asset": ["tiktok", "instagram"],
}


def plain(text_html: str) -> str:
    """HTML to text, keeping paragraphs and list items on their own lines."""
    t = re.sub(r"(?i)<li[^>]*>", "\n- ", text_html or "")
    t = re.sub(r"(?i)</p>|<br\s*/?>|</h[1-6]>|</li>|</ul>|</ol>", "\n", t)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in t.splitlines()]
    return "\n".join(ln for ln in lines if ln).strip()


def first_sentence(text: str, limit=220) -> str:
    s = re.split(r"(?<=[.!?])\s", text.strip(), maxsplit=1)[0].splitlines()[0] if text and text.strip() else ""
    return s if len(s) <= limit else s[: limit - 1].rstrip() + "…"


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _eligibility(reasons_block, reasons_review=()):
    if reasons_block:
        return {"status": NOT_ELIGIBLE, "reasons": list(reasons_block)}
    if reasons_review:
        return {"status": NEEDS_REVIEW, "reasons": list(reasons_review)}
    return {"status": ELIGIBLE, "reasons": []}


# ---- digital products (Gumroad) -------------------------------------------
# Delivery-audit issues that mean the buyer receives less than the listing
# promises: such a listing must be repaired before it is promoted. ZIP contents
# not yet opened and a short deliverable are not, by themselves, a broken promise.
DELIVERY_BLOCKING = ("PUBLISHED_WITHOUT_DELIVERABLE", "PROMISES_SPREADSHEET_NOT_ATTACHED",
                     "PROMISES_MORE_FILES_THAN_ATTACHED", "PREVIEW_FILE_DELIVERED")


def delivery_issues(root=ROOT) -> dict:
    """slug -> blocking issues, from the newest reports/GUMROAD_DELIVERY_AUDIT_<date>.json."""
    reports = sorted(Path(root, "reports").glob("GUMROAD_DELIVERY_AUDIT_*.json"))
    if not reports:
        return {}
    doc = _read(reports[-1], {})
    out = {}
    for r in doc.get("rows") or []:
        bad = [i for i in r.get("issues") or [] if i in DELIVERY_BLOCKING]
        if bad and r.get("slug"):
            out[r["slug"]] = {"issues": bad, "report": reports[-1].name}
    return out


def product_offers(registry: dict, live: list, delivery: dict | None = None) -> list:
    by_gid = {p["id"]: p for p in live or []}
    titles = {}
    for r in registry.get("products", []):
        titles.setdefault(r["title"].strip().lower(), []).append(r["internal_id"])
    out = []
    for r in registry.get("products", []):
        gid = (r.get("external_ids") or {}).get("gumroad")
        lp = by_gid.get(gid, {})
        desc = plain(lp.get("description", ""))
        block, review = [], []
        if r.get("primary_state") != "PUBLIC_LISTING_VERIFIED":
            block.append(f"listing state is {r.get('primary_state')}, not PUBLIC_LISTING_VERIFIED")
        if not desc:
            block.append("no listing description available to draw facts from")
        slug = (r.get("url") or "").rstrip("/").rsplit("/", 1)[-1]
        if slug and hold_policy.is_on_hold(slug):
            # A held product must never be promoted, whatever its listing state
            # (2026-10-31: both held listings were ELIGIBLE and queued as pins).
            block.append(f"on HOLD (hold_policy.py): {hold_policy.hold_reason(slug)}")
        if slug and slug in (delivery or {}):
            d = delivery[slug]
            block.append(f"delivery audit ({d['report']}): {', '.join(d['issues'])}; repair before promoting")
        if len(titles[r["title"].strip().lower()]) > 1:
            review.append(f"duplicate live title shared with {sorted(titles[r['title'].strip().lower()])}")
        out.append({
            "offer_id": r["internal_id"], "arm": "digital_products", "type": "digital_product",
            "subtype": "spreadsheet_tool" if str(r.get("manifest", "")).startswith("books/batch14") else "digital_download",
            "title": r["title"], "problem": first_sentence(desc), "audience": ", ".join((lp.get("tags") or [])[:3]) or "UNKNOWN",
            "url": r.get("url"), "price_cents": r.get("price_cents"), "currency": (lp.get("currency") or "usd").upper(),
            "availability": "LIVE" if r.get("published") else "UNPUBLISHED", "primary_state": r.get("primary_state"),
            "qa_status": "QA_PASS" if r.get("manifest") else "UNKNOWN", "rights_status": "OWNED_ORIGINAL",
            "description": desc, "tags": lp.get("tags") or [], "sales_count": r.get("sales_count", 0),
            # the listing's own public cover image, when it has one (14 of 92 on 2026-10-23; 88 of 89 published after the 2026-10-24 cover run)
            "cover_url": lp.get("preview_url") or next((c.get("url") for c in lp.get("covers") or [] if c.get("url")), None),
            "measurement": {"destination": "gumroad", "sales_referrer": "OBSERVED per sale via Gumroad sales API",
                            "page_views": "UNKNOWN (no read API used)"},
            "eligibility": _eligibility(block, review),
            "evidence": {"source": "data/product_registry.json + Gumroad GET /v2/products", "verified_at": registry.get("generated_at")},
        })
    return out


# ---- public site pages -----------------------------------------------------
SITE_TYPES = [("service-", "service", "services"), ("tool-", "content_asset", "digital_products"),
              ("guide-", "content_asset", "education_content"), ("blog-", "content_asset", "education_content"),
              ("affiliate-", "content_asset", "affiliate"), ("b12-", "content_asset", "digital_products")]


def published_site_files(ref="origin/main", root=ROOT) -> set:
    try:
        out = subprocess.run(["git", "ls-tree", "-r", "--name-only", ref, "customer_site/"], cwd=root,
                             capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return set()
    return {Path(p).name for p in out.splitlines() if p.endswith(".html")}


NOT_ON_SALE = re.compile(r"\((?:approved, not yet listed|proposed[^)]*)\)", re.I)


def _norm(title):
    return re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()


def _live_product_for(page_title, registry):
    """The verified live Gumroad product a b12 product page describes, by name."""
    name = _norm(re.split(r"\s+[—|-]\s+\$|\s+\|\s+", page_title)[0])
    for r in (registry or {}).get("products", []):
        if r.get("primary_state") == "PUBLIC_LISTING_VERIFIED" and _norm(r["title"]) == name:
            return r
    return None


def site_offers(root=ROOT, published=None, registry=None) -> list:
    published = published_site_files(root=root) if published is None else published
    out = []
    for f in sorted((Path(root) / "customer_site").glob("*.html")):
        typ, arm = next(((t, a) for pre, t, a in SITE_TYPES if f.name.startswith(pre)), (None, None))
        if not typ:
            continue  # index, about, contact, legal pages are not offers
        text = f.read_text(encoding="utf-8", errors="replace")
        title = plain((re.search(r"<title>(.*?)</title>", text, re.S | re.I) or [None, f.stem])[1])
        title = re.sub(r"\s*[|—-]\s*Galaxy Forge\s*$", "", title)  # the site name is not part of the offer
        meta = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', text, re.I)
        desc = plain(meta.group(1)) if meta else ""
        block, review = [], []
        if f.name not in published:
            block.append("page is not on origin/main, so it is not public")
        if not desc:
            block.append("page has no meta description to draw facts from")
        if typ == "service":
            review.append("service: delivery capacity and terms need founder confirmation before promotion")
        live = None
        if f.name.startswith("b12-"):
            # a product page: promote it only if its product is really on sale
            live = _live_product_for(title, registry)
            if live is None:
                block.append("product page for a product that is not on sale"
                             + (f" (page says {NOT_ON_SALE.search(title).group(0)})" if NOT_ON_SALE.search(title) else ""))
            elif NOT_ON_SALE.search(title):
                review.append(f"page is stale: it says {NOT_ON_SALE.search(title).group(0)} but {live['internal_id']} "
                              f"is live at {live['url']}")
        out.append({
            "offer_id": "SITE-" + f.stem, "arm": arm, "type": typ, "subtype": f.name.split("-")[0],
            "title": title, "problem": first_sentence(desc), "audience": "UNKNOWN", "url": SITE_BASE + f.name,
            # a product page carries its live product's real price (and names it)
            "price_cents": live["price_cents"] if live else None, "currency": "USD" if live else None,
            "linked_product": live["internal_id"] if live else None,
            "availability": "LIVE" if f.name in published else "UNPUBLISHED",
            "primary_state": "PUBLISHED_ON_MAIN" if f.name in published else "LOCAL_ONLY",
            "qa_status": "SITE_TESTS", "rights_status": "OWNED_ORIGINAL", "description": desc, "tags": [],
            "measurement": {"destination": "github_pages", "page_views": "UNMEASURED (no receiver for the beacon)"},
            "eligibility": _eligibility(block, review),
            "evidence": {"source": f"customer_site/{f.name} + git ls-tree origin/main", "verified_at": _now()},
        })
    return out


# ---- affiliate programs ----------------------------------------------------
def affiliate_offers(records=None) -> list:
    if records is None:
        try:
            from affiliate import registry
            records = registry.registry_summary().get("records", [])
        except Exception:  # noqa: BLE001
            records = []
    out = []
    for i, r in enumerate(records):
        approved = r.get("approval_status") == "APPROVED"
        block = [] if approved else [f"program approval is {r.get('approval_status') or 'UNKNOWN'}; no approved affiliate link"]
        out.append({
            "offer_id": "AFF-" + re.sub(r"[^a-z0-9]+", "-", (r.get("program_name") or str(i)).lower()).strip("-"),
            "arm": "affiliate", "type": "affiliate_offer", "subtype": r.get("commission_model"),
            "title": r.get("program_name"), "problem": "UNKNOWN", "audience": "UNKNOWN", "url": None,
            "price_cents": None, "currency": None, "availability": "NOT_APPROVED" if not approved else "APPROVED",
            "primary_state": r.get("affiliate_status"), "qa_status": "UNKNOWN", "rights_status": "PARTNER_TERMS",
            "description": "", "tags": [], "measurement": {"destination": "network", "commissions": "network statement only"},
            "eligibility": _eligibility(block),
            "evidence": {"source": "affiliate.registry (data/commission_opportunities.jsonl)", "verified_at": _now()},
        })
    return out


# ---- media assets ----------------------------------------------------------
def media_offers(root=ROOT) -> list:
    out = []
    for m in sorted((Path(root) / "video_studio" / "projects").glob("*.json")):
        if m.name.endswith(".rights.json"):
            continue
        man = _read(m, {})
        rights = _read(m.with_name(m.stem + ".rights.json"), {})
        vid = Path(root) / "video_studio" / "output" / man.get("id", "") / f"{man.get('id', '')}.mp4"
        block = []
        if rights.get("status") != "CLEARED":
            block.append(f"rights {rights.get('status', 'UNKNOWN')}")
        if not vid.exists():
            block.append("video not rendered on this machine")
        out.append({
            "offer_id": "VID-" + man.get("id", m.stem), "arm": "video", "type": "media_asset",
            "subtype": man.get("format"), "title": man.get("title"), "problem": "", "audience": man.get("audience", "UNKNOWN"),
            "url": None, "price_cents": None, "currency": None, "availability": "LOCAL_RENDER" if vid.exists() else "NOT_RENDERED",
            "primary_state": "LOCAL_READY" if vid.exists() else "NOT_RENDERED", "qa_status": "VERIFIED_LOCAL" if vid.exists() else "UNKNOWN",
            "rights_status": rights.get("status", "UNKNOWN"), "description": man.get("purpose", ""), "tags": [],
            "media_path": str(vid.relative_to(root)) if vid.exists() else None,
            "measurement": {"destination": "platform-native", "views": "UNKNOWN"},
            "eligibility": _eligibility(block),
            "evidence": {"source": f"{m.relative_to(root).as_posix()} + rights manifest", "verified_at": _now()},
        })
    return out


def build(registry=None, live=None, root=ROOT, published=None, affiliate_records=None) -> dict:
    registry = _read(Path(root) / "data" / "product_registry.json", {"products": []}) if registry is None else registry
    if live is None:
        import product_registry
        live = product_registry.fetch_live()  # read-only GET
    offers = (product_offers(registry, live, delivery_issues(root)) + site_offers(root, published, registry) + affiliate_offers(affiliate_records)
              + media_offers(root))
    for o in offers:
        o["platforms"] = PLATFORMS_BY_TYPE.get(o["type"], [])
        o["prohibited_claims"] = PROHIBITED_CLAIMS
        o["language"] = "en"
    return {"schema": 1, "generated_at": _now(), "offers": offers, "summary": summary(offers)}


def summary(offers) -> dict:
    from collections import Counter
    return {"total": len(offers),
            "by_arm": dict(Counter(o["arm"] for o in offers)),
            "by_type": dict(Counter(o["type"] for o in offers)),
            "by_eligibility": dict(Counter(o["eligibility"]["status"] for o in offers)),
            "eligible_by_arm": dict(Counter(o["arm"] for o in offers if o["eligibility"]["status"] == ELIGIBLE))}


def write(doc, path=OUT):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

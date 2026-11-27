"""Storefront commercial consistency check (read-only, no network).

Answers one question before sending traffic to the public storefront: does
the page a buyer actually sees agree with the recorded commercial truth?

Sources, all local:
  * customer_site/products.html  the public storefront page
  * data/catalog.json            published state, price, withdrawal state

The check catches contradictions that cost real sales or create false
commercial claims:
  * a page-wide "not for sale" banner on a page with live checkout links
  * a buy button that goes nowhere
  * a buy link for an unknown, unpublished, or withdrawn product
  * a card price that disagrees with the catalog price
  * a held card with no visible hold explanation
  * two live links to the same duplicate-listing group

Every finding carries an evidence class:
  OBSERVED  read directly from a source file
  DERIVED   computed from observed values
  UNKNOWN   cannot be decided from local data (never guessed)

Exit codes: 0 = no ERROR findings, 1 = at least one ERROR finding.
Nothing is written unless --write is passed.

    python -X utf8 scripts/storefront_commercial_check.py
    python -X utf8 scripts/storefront_commercial_check.py --json --write
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

OBSERVED = "OBSERVED"
DERIVED = "DERIVED"
UNKNOWN = "UNKNOWN"

ERROR = "ERROR"
WARNING = "WARNING"
NOTE = "NOTE"

CARD_RE = re.compile(r'<div class="card"[^>]*>(.*?)</div>', re.S)
H2_RE = re.compile(r"<h2[^>]*>(.*?)</h2>", re.S | re.I)
PRICE_RE = re.compile(r'<span class="price"[^>]*>(.*?)</span>', re.S | re.I)
ANCHOR_RE = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")
SLUG_RE = re.compile(r"/l/([A-Za-z0-9_-]+)")
MONEY_RE = re.compile(r"\$\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)")

HOLD_PHRASES = ("currently on hold", "withdrawn from promotion")
HELD_NOTICE_PHRASES = ("on hold", "not for sale", "under review")
HELD_ACTIVE_OFFER_RE = re.compile(
    r"\bemail us\b|\bget\b.{0,60}\bfree\b|\bfree copy\b|\bfirst buyer\b", re.I)
HELD_DELIVERY_CLAIM_RE = re.compile(
    r"\bdownloads? instantly\b|\bdownload immediately\b|\binstant download\b|"
    r"\bdelivered instantly\b|\bdelivered immediately\b|\bdownload after purchase\b|"
    r"\bdownloads? after purchase\b", re.I)
PAGE_FREE_SCOPE_RE = re.compile(
    r"first buyer of (?:each|any) kit|any kit free|each kit below", re.I)


def _finding(code, severity, subject, detail, evidence=OBSERVED):
    return {"code": code, "severity": severity, "subject": subject,
            "detail": detail, "evidence": evidence}


def _text(fragment):
    return html.unescape(TAG_RE.sub(" ", fragment or "")).replace("\xa0", " ")


def _squash(value):
    return " ".join(_text(value).split())


def _attrs(raw):
    attrs = {}
    pattern = r'([A-Za-z0-9_-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\')'
    for match in re.finditer(pattern, raw):
        value = match.group(2) if match.group(2) is not None else match.group(3)
        attrs[match.group(1).lower()] = html.unescape(value or "")
    return attrs


def _money(value):
    match = MONEY_RE.search(_text(value))
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", ""))
    except ValueError:
        return None


def _slug(url):
    match = SLUG_RE.search(url or "")
    return match.group(1) if match else None


def _is_truthy(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes")


def _is_withdrawn(product):
    state = str(product.get("commercial_state") or "").upper()
    flags = {str(f).upper() for f in (product.get("manual_listing_flags") or [])}
    return state == "WITHDRAWN_NOT_FOR_SALE" or "WITHDRAWN_NOT_FOR_SALE" in flags


def _load_catalog(root):
    path = root / "data" / "catalog.json"
    try:
        catalog = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, "file not found"
    except (ValueError, OSError) as exc:
        return None, "%s: %s" % (type(exc).__name__, exc)
    if not isinstance(catalog, dict) or not isinstance(catalog.get("products"), list):
        return None, "catalog has no products list"
    return catalog, None


def parse_cards(page_html):
    cards = []
    for index, block in enumerate(CARD_RE.findall(page_html)):
        title_match = H2_RE.search(block)
        price_match = PRICE_RE.search(block)
        title = _squash(title_match.group(1)) if title_match else "card[%d]" % index
        if price_match:
            price_usd = _money(price_match.group(1))
        elif title_match:
            price_usd = _money(title_match.group(1))
        else:
            price_usd = _money(block)
        anchors = []
        for raw_attrs, label in ANCHOR_RE.findall(block):
            attrs = _attrs(raw_attrs)
            classes = attrs.get("class", "").split()
            if "buy" not in classes:
                continue
            anchors.append({
                "href": (attrs.get("href") or "").strip(),
                "held": (attrs.get("data-held-product") or "").strip() or None,
                "label": _squash(label),
            })
        cards.append({
            "index": index,
            "title": title,
            "price_usd": price_usd,
            "text": _squash(block),
            "anchors": anchors,
        })
    return cards


def analyze(page_html, catalog):
    findings = []
    cards = parse_cards(page_html)
    outside_cards = _squash(CARD_RE.sub(" ", page_html)).lower()
    is_global_hold = any(phrase in outside_cards for phrase in HOLD_PHRASES)

    products = [p for p in catalog.get("products") or [] if isinstance(p, dict)]
    by_slug = {p.get("gumroad_slug"): p for p in products if p.get("gumroad_slug")}

    active = []
    held = []
    for card in cards:
        for anchor in card["anchors"]:
            if anchor["held"]:
                if anchor["href"]:
                    findings.append(_finding(
                        "STOREFRONT_HELD_LINK_ACTIVE", ERROR, anchor["held"],
                        "%r is marked held but still carries a live checkout href"
                        % card["title"]))
                held.append((card, anchor))
            elif anchor["href"]:
                active.append((card, anchor))
            else:
                findings.append(_finding(
                    "STOREFRONT_BUY_BUTTON_DEAD", ERROR, card["title"],
                    "buy button has neither an href nor a held-product marker"))

    if is_global_hold and active:
        findings.append(_finding(
            "STOREFRONT_GLOBAL_HOLD_BANNER", ERROR, "customer_site/products.html",
            "a page-wide 'on hold / not for sale' notice appears while %d active "
            "checkout link(s) are present; buyers are told the opposite of the "
            "page's real commercial state" % len(active)))

    active_slugs = []
    for card, anchor in active:
        slug = _slug(anchor["href"])
        if not slug:
            findings.append(_finding(
                "STOREFRONT_CHECKOUT_NOT_GUMROAD", WARNING, card["title"],
                "buy link %r is not a recognizable Gumroad /l/<slug> URL"
                % anchor["href"]))
            continue
        active_slugs.append(slug)
        product = by_slug.get(slug)
        if product is None:
            findings.append(_finding(
                "STOREFRONT_UNKNOWN_PRODUCT", ERROR, slug,
                "%r links to a slug absent from data/catalog.json" % card["title"]))
            continue
        if not _is_truthy(product.get("published")):
            findings.append(_finding(
                "STOREFRONT_UNPUBLISHED_PRODUCT", ERROR, slug,
                "%r links to a product the catalog says is not published" % card["title"]))
        if _is_withdrawn(product):
            findings.append(_finding(
                "STOREFRONT_WITHDRAWN_PRODUCT", ERROR, slug,
                "%r links to a deliberately withdrawn product (price_usd=%r)"
                % (card["title"], product.get("price_usd"))))
        catalog_price = product.get("price_usd")
        if isinstance(catalog_price, (int, float)) and not isinstance(catalog_price, bool):
            if card["price_usd"] is None:
                findings.append(_finding(
                    "STOREFRONT_PRICE_UNVERIFIED", WARNING, slug,
                    "%r shows no parseable price; catalog price is %s"
                    % (card["title"], catalog_price)))
            elif abs(card["price_usd"] - float(catalog_price)) > 0.005:
                findings.append(_finding(
                    "STOREFRONT_PRICE_MISMATCH", ERROR, slug,
                    "%r shows $%.2f, catalog records $%.2f"
                    % (card["title"], card["price_usd"], float(catalog_price)),
                    DERIVED))

    duplicate_groups = {}
    for product in products:
        group = product.get("duplicate_group")
        slug = product.get("gumroad_slug")
        if group and slug:
            duplicate_groups.setdefault(str(group), set()).add(slug)
    for group, slugs in duplicate_groups.items():
        live = sorted(set(active_slugs) & slugs)
        if len(live) > 1:
            findings.append(_finding(
                "STOREFRONT_DUPLICATE_LISTING_LINKS", WARNING, group,
                "the page links %d live listings in the same duplicate group: %s"
                % (len(live), ", ".join(live)), DERIVED))

    for card, anchor in held:
        text = card["text"].lower()
        if not any(phrase in text for phrase in HELD_NOTICE_PHRASES):
            findings.append(_finding(
                "STOREFRONT_HELD_CARD_UNEXPLAINED", WARNING, card["title"],
                "card is marked held but never says 'on hold' or 'not for sale'"))
        if HELD_ACTIVE_OFFER_RE.search(text):
            findings.append(_finding(
                "STOREFRONT_HELD_CARD_ACTIVE_OFFER", ERROR, card["title"],
                "card is marked held but still advertises an active free/email offer"))
        if HELD_DELIVERY_CLAIM_RE.search(text):
            findings.append(_finding(
                "STOREFRONT_HELD_CARD_DELIVERY_CLAIM", ERROR, card["title"],
                "card is marked held but still claims the file is delivered/downloadable"))
        slug = anchor["held"]
        if slug and slug not in by_slug:
            findings.append(_finding(
                "STOREFRONT_HELD_PRODUCT_UNKNOWN", WARNING, slug,
                "held marker %r is absent from data/catalog.json" % slug))

    if held and PAGE_FREE_SCOPE_RE.search(_squash(page_html)):
        findings.append(_finding(
            "STOREFRONT_FREE_OFFER_MAY_COVER_HELD", WARNING,
            "customer_site/products.html",
            "a page-wide 'first buyer / each kit' free offer does not exclude the "
            "%d held card(s); scope it to available kits" % len(held)))

    counts = {severity: sum(1 for f in findings if f["severity"] == severity)
              for severity in (ERROR, WARNING, NOTE)}
    return {
        "probe": "storefront_commercial_check",
        "read_only": True,
        "network": "not used",
        "sources": ["customer_site/products.html", "data/catalog.json"],
        "summary": {
            "cards": len(cards),
            "active_buy_links": len(active),
            "held_buy_links": len(held),
            "distinct_active_slugs": len(set(active_slugs)),
            "global_hold_banner": is_global_hold,
        },
        "counts": counts,
        "status": ERROR if counts[ERROR] else "PASS",
        "findings": findings,
    }


def build_report(root=ROOT, now=None):
    report = analyze("", {"products": []})
    report["generated_at"] = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")

    page_path = Path(root) / "customer_site" / "products.html"
    try:
        page_html = page_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return _with_source_error(report, "customer_site/products.html", "file not found")
    except OSError as exc:
        return _with_source_error(report, "customer_site/products.html",
                                  "%s: %s" % (type(exc).__name__, exc))

    catalog, error = _load_catalog(Path(root))
    if error:
        return _with_source_error(report, "data/catalog.json", error)

    report.update(analyze(page_html, catalog))
    report["generated_at"] = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    return report


def _with_source_error(report, subject, detail):
    report["findings"] = [_finding("STOREFRONT_SOURCE_UNREADABLE", ERROR, subject, detail)]
    report["counts"] = {ERROR: 1, WARNING: 0, NOTE: 0}
    report["status"] = ERROR
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    parser.add_argument("--write", action="store_true",
                        help="write reports/storefront_commercial_check_<date>.json")
    args = parser.parse_args(argv)

    report = build_report()
    if args.write:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        target = ROOT / "reports" / ("storefront_commercial_check_%s.json" % stamp)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print("written: %s" % target)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        counts = report["counts"]
        print("storefront_commercial_check: %s (ERROR=%d WARNING=%d NOTE=%d)"
              % (report["status"], counts[ERROR], counts[WARNING], counts[NOTE]))
        for finding in report["findings"]:
            print("  [%s] %s %s: %s" % (finding["severity"], finding["code"],
                                        finding["subject"], finding["detail"]))
    return 1 if report["counts"][ERROR] else 0


if __name__ == "__main__":
    sys.exit(main())

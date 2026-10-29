# -*- coding: utf-8 -*-
"""Galaxy Forge -- product identity registry and drift check (2026-10-23).

WHY
---
On 2026-10-23 a live reconciliation found 92 Gumroad listings, a catalog
(data/catalog.json) keyed by the Gumroad id itself, and a "canonical"
inventory (reports/CYCLE104/DIGITAL_PRODUCT_INVENTORY.json) whose 21 ids
matched none of the live listings. Nothing linked one product's files, QA,
listing and sales. See docs/factory/FACTORY_GAP_AND_RISK_REGISTER.md R3.

WHAT
----
data/product_registry.json holds one record per product:
  internal_id   stable, never reused. A product that already has a factory id
                (a batch manifest, e.g. B14-003) keeps it; any other live
                listing gets "GR-" + 10 hex characters of sha256(gumroad id),
                so rebuilding from the same inputs gives the same ids.
  external_ids  {"gumroad": id}
  title, price_cents, published, url, sales_count   from the live platform
  manifest      path of the QA manifest, when the factory built it
  first_published_at  earliest real, successful, non-dry-run publish attempt
                for this product, read from data/sales_ledger.jsonl (written by
                channels/ledger.py on every real distribute()). None when the
                factory has no such evidence -- never guessed from the platform,
                because Gumroad's API returns no dates at all. This is what makes
                config/reality.json's critical_if_sales_zero_after_days=30
                computable: before 2026-10-28 nothing recorded when a listing
                went live, so "30 days with zero sales" could not be evaluated.
  primary_state one of the doctrine's release states (PERMANENT_OPERATING_
                DOCTRINE.md section 10), from evidence only:
                  FIRST_SALE_VERIFIED      platform sales_count > 0
                  PUBLIC_LISTING_VERIFIED  published AND a recorded public-page
                                           check (publish results file)
                  UPLOAD_COMPLETED         listing exists on the platform
                  READY_FOR_AUTHORIZATION  manifest qa.ok, not on the platform
                  BUILD_COMPLETE           manifest, qa not ok
  flags         published_on_platform, in_catalog

drift(): differences between the registry inputs, for a human to act on:
live listings missing from data/catalog.json, catalog rows no longer live,
manifest title/price differing from the live listing, duplicate live titles,
QA-passed manifests never listed, and listings live for
ZERO_SALES_ALERT_DAYS or more with zero sales (the real signal behind
config/reality.json's critical_if_sales_zero_after_days threshold).
It reports; it never changes the platform.

    python product_registry.py --rebuild   # read live Gumroad, write registry
    python product_registry.py --check     # same, print drift, write nothing
    python product_registry.py --rebuild --verify-pages   # also GET each listing page
"""
from __future__ import annotations

import argparse
import collections
import glob
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / "data" / "product_registry.json"
CATALOG = ROOT / "data" / "catalog.json"
MANIFEST_GLOBS = ["books/batch13/B13-*.manifest.json", "books/batch14/*/manifest.json", "books/batch15/*/manifest.json",
                  "books/batch16/*/manifest.json"]
PUBLISH_RESULTS = [ROOT / "data" / "batch13_publish_results.json",
                   ROOT / "data" / "batch14_publish_results.json",
                   ROOT / "data" / "batch15_publish_results.json",
                   ROOT / "data" / "batch16_publish_results.json"]
PAGE_CHECKS = ROOT / "data" / "listing_page_checks.json"
PAGE_CHECK_MAX_AGE_DAYS = 7
SALES_LEDGER = ROOT / "data" / "sales_ledger.jsonl"
ZERO_SALES_ALERT_DAYS = 30


def derived_id(gumroad_id: str) -> str:
    return "GR-" + hashlib.sha256(gumroad_id.encode("utf-8")).hexdigest()[:10]


def _read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def load_manifests(root=ROOT, globs=MANIFEST_GLOBS):
    out = []
    for g in globs:
        for p in sorted(glob.glob(str(root / g))):
            m = _read_json(p, None)
            if isinstance(m, dict) and m.get("id"):
                m["_path"] = str(Path(p).relative_to(root)).replace("\\", "/")
                out.append(m)
    return out


def load_publish_results(paths=PUBLISH_RESULTS):
    """{gumroad_id: {"internal_id", "public_page"}} from publish run records."""
    out = {}
    for p in paths:
        for run in _read_json(p, []) or []:
            for r in run.get("results", []):
                if r.get("product_id"):
                    prev = out.get(r["product_id"], {})
                    out[r["product_id"]] = {"internal_id": r.get("id") or prev.get("internal_id"),
                                            "public_page": bool((r.get("steps") or {}).get("public_page")) or prev.get("public_page", False)}
    return out


def load_publish_history(path=SALES_LEDGER):
    """Real first successful, non-dry-run publish time per product.

    Evidence only: data/sales_ledger.jsonl's own publish_attempt events, which
    channels/ledger.py::record_publish_attempt() appends on every real
    distribute() call. A dry run never published anything, and a failed attempt
    is not publication, so neither sets a date. Indexed by both the factory id
    (product_source_id) and the platform id (product_id) because a row may
    carry only one of them. Missing or unreadable ledger -> empty history, never
    an exception: this is observability, not a gate.
    """
    by_internal, by_gumroad = {}, {}
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return {"by_internal": {}, "by_gumroad": {}}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if (not isinstance(ev, dict) or ev.get("event_type") != "publish_attempt"
                or ev.get("dry_run") is not False or not ev.get("ok")):
            continue
        ts = ev.get("timestamp")
        if not isinstance(ts, str) or not ts:
            continue
        for key, table in ((ev.get("product_source_id"), by_internal),
                           (ev.get("product_id"), by_gumroad)):
            if key and (key not in table or ts < table[key]):
                table[key] = ts
    return {"by_internal": by_internal, "by_gumroad": by_gumroad}


def first_publish_for(gumroad_id, internal_id, history):
    """The earliest recorded real publish time for one product, or None."""
    history = history or {}
    return ((history.get("by_gumroad") or {}).get(gumroad_id)
            or (history.get("by_internal") or {}).get(internal_id))


def days_live(record, now=None):
    """Whole days since the first real publish, or None without evidence."""
    ts = (record or {}).get("first_published_at")
    if not ts:
        return None
    try:
        then = datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return None
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    return int(((now or datetime.now(timezone.utc)) - then).total_seconds() // 86400)


def fresh_page_checks(checks, now=None, max_age_days=PAGE_CHECK_MAX_AGE_DAYS):
    """{gumroad_id: True} for page checks that passed within max_age_days."""
    now = now or datetime.now(timezone.utc)
    out = {}
    for gid, c in (checks or {}).items():
        try:
            age = (now - datetime.fromisoformat(c["checked_at"])).total_seconds() / 86400
        except (KeyError, ValueError, TypeError):
            continue
        if c.get("ok") and 0 <= age <= max_age_days:
            out[gid] = True
    return out


def verify_pages(live, opener=None, timeout=20, retry_wait=10):
    """Read-only: GET each published listing URL; ok when HTTP 200 and the
    title appears in the (HTML-unescaped) page. Returns {gumroad_id: check}."""
    import urllib.request
    from concurrent.futures import ThreadPoolExecutor
    from html import unescape
    opener = opener or urllib.request.urlopen
    now = datetime.now(timezone.utc).isoformat()

    import time
    import urllib.error

    def one(p):
        for attempt in range(2):
            try:
                req = urllib.request.Request(p["short_url"], headers={"User-Agent": "Mozilla/5.0 GalaxyForge-verify"})
                r = opener(req, timeout=timeout)
                body = unescape(r.read().decode("utf-8", "replace"))
                ok = r.status == 200 and (p.get("name") or "").lower() in body.lower()
                return p["id"], {"checked_at": now, "ok": ok, "status": r.status, "title_found": ok}
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt == 0:
                    time.sleep(retry_wait)
                    continue
                # 429 again is the platform throttling us, not evidence about the page
                return p["id"], {"checked_at": now, "ok": False, "status": e.code, "transient": e.code == 429}
            except Exception as e:  # network failure: says nothing about the page
                return p["id"], {"checked_at": now, "ok": False, "transient": True, "error": f"{type(e).__name__}: {str(e)[:80]}"}
    targets = [p for p in live if p.get("published") and p.get("short_url")]
    with ThreadPoolExecutor(max_workers=3) as pool:
        return dict(pool.map(one, targets))


def build(live, catalog_rows, manifests, publish_results, previous=None, page_checks=None,
          publish_history=None):
    """Pure: inputs -> registry dict. `previous` keeps earlier id assignments;
    `page_checks` ({gumroad_id: True}) is fresh public-page evidence;
    `publish_history` (load_publish_history()) dates each real publication."""
    page_checks = page_checks or {}
    prev_by_gid = {}
    for rec in (previous or {}).get("products", []):
        gid = (rec.get("external_ids") or {}).get("gumroad")
        if gid:
            prev_by_gid[gid] = rec["internal_id"]
    man_by_title = {m["title"]: m for m in manifests}
    catalog_ids = {r.get("id") for r in catalog_rows}
    products, used = [], set()
    for p in sorted(live, key=lambda x: x["id"]):
        gid = p["id"]
        pub = publish_results.get(gid, {})
        man = None
        if pub.get("internal_id"):
            man = next((m for m in manifests if m["id"] == pub["internal_id"]), None)
        man = man or man_by_title.get(p.get("name"))
        iid = prev_by_gid.get(gid) or (man["id"] if man else None) or derived_id(gid)
        if iid in used:  # a second listing claims the same factory id (e.g. a duplicate)
            iid = derived_id(gid)
        used.add(iid)
        published = bool(p.get("published"))
        sales = int(p.get("sales_count") or 0)
        if sales > 0:
            state = "FIRST_SALE_VERIFIED"
        elif published and (pub.get("public_page") or page_checks.get(gid)):
            state = "PUBLIC_LISTING_VERIFIED"
        else:
            state = "UPLOAD_COMPLETED"
        products.append({
            "internal_id": iid, "external_ids": {"gumroad": gid}, "title": p.get("name"),
            "price_cents": p.get("price"), "published": published, "url": p.get("short_url"),
            "sales_count": sales, "sales_usd_cents": int(p.get("sales_usd_cents") or 0),  # as Gumroad reports it (gross)
            "first_published_at": first_publish_for(gid, iid, publish_history),
            "manifest": man["_path"] if man else None, "primary_state": state,
            "flags": {"published_on_platform": published, "in_catalog": gid in catalog_ids},
        })
    listed_titles = {p.get("name") for p in live}
    for m in manifests:
        if m["title"] in listed_titles or m["id"] in used:
            continue
        products.append({
            "internal_id": m["id"], "external_ids": {}, "title": m["title"], "price_cents": m.get("price_cents"),
            "published": False, "url": None, "sales_count": 0, "sales_usd_cents": 0,
            "first_published_at": None, "manifest": m["_path"],
            "primary_state": "READY_FOR_AUTHORIZATION" if (m.get("qa") or {}).get("ok") else "BUILD_COMPLETE",
            "flags": {"published_on_platform": False, "in_catalog": False},
        })
    return {"schema": 1, "products": sorted(products, key=lambda r: r["internal_id"])}


def drift(registry, live, catalog_rows, manifests, now=None):
    live_ids = {p["id"] for p in live}
    cat_ids = {r.get("id") for r in catalog_rows if r.get("channel", "Gumroad") == "Gumroad"}
    by_gid = {p["id"]: p for p in live}
    titles = collections.Counter(p.get("name") for p in live)
    mismatches = []
    for rec in registry["products"]:
        gid = rec["external_ids"].get("gumroad")
        man = next((m for m in manifests if m["_path"] == rec.get("manifest")), None)
        if gid and man:
            lp = by_gid.get(gid, {})
            if lp.get("name") != man["title"] or int(lp.get("price") or -1) != int(man.get("price_cents") or -2):
                mismatches.append({"internal_id": rec["internal_id"], "live": [lp.get("name"), lp.get("price")],
                                   "manifest": [man["title"], man.get("price_cents")]})
    return {
        "live_missing_from_catalog": sorted(rec["internal_id"] for rec in registry["products"]
                                            if rec["external_ids"].get("gumroad") in (live_ids - cat_ids)),
        "catalog_rows_not_live": sorted(cat_ids - live_ids - {None}),
        "manifest_live_mismatch": mismatches,
        "duplicate_live_titles": sorted(t for t, c in titles.items() if c > 1),
        "qa_passed_not_listed": sorted(r["internal_id"] for r in registry["products"] if r["primary_state"] == "READY_FOR_AUTHORIZATION"),
        "unpublished_on_platform": sorted(r["internal_id"] for r in registry["products"] if r["external_ids"].get("gumroad") and not r["published"]),
        # The real signal behind config/reality.json's
        # critical_if_sales_zero_after_days: published, no sale, and enough
        # elapsed time that the silence is evidence rather than impatience.
        "published_zero_sales_past_threshold": sorted(
            r["internal_id"] for r in registry["products"]
            if r["published"] and not r["sales_count"] and (days_live(r, now) or 0) >= ZERO_SALES_ALERT_DAYS),
    }


def summary(registry, d):
    states = collections.Counter(r["primary_state"] for r in registry["products"])
    return {"products": len(registry["products"]), "states": dict(sorted(states.items())),
            "sales_total": sum(r["sales_count"] for r in registry["products"]),
            "drift_counts": {k: len(v) for k, v in d.items()}}


def fetch_live():
    sys.path.insert(0, str(ROOT / "channels"))
    import gumroad_publisher as gp  # read-only: GET /v2/products
    return gp.list_products(gp.load_token())


def run(write=True, live=None, registry_path=REGISTRY, catalog_path=CATALOG, now=None, check_pages=False,
        page_checks_path=PAGE_CHECKS, opener=None, sales_ledger_path=SALES_LEDGER):
    live = live if live is not None else fetch_live()
    checks = _read_json(page_checks_path, {}) or {}
    if check_pages:
        for gid, c in verify_pages(live, opener=opener).items():
            # a transient error (throttling, network) never replaces an earlier passing check
            if c.get("transient") and (checks.get(gid) or {}).get("ok"):
                continue
            checks[gid] = c
        if write:
            tmp = Path(str(page_checks_path) + ".tmp")
            tmp.write_text(json.dumps(checks, indent=1), encoding="utf-8")
            os.replace(tmp, page_checks_path)
    catalog_rows = (_read_json(catalog_path, {}) or {}).get("products", [])
    manifests = load_manifests()
    previous = _read_json(registry_path, None)
    history = load_publish_history(sales_ledger_path)
    reg = build(live, catalog_rows, manifests, load_publish_results(), previous,
                fresh_page_checks(checks, now), history)
    d = drift(reg, live, catalog_rows, manifests, now)
    reg["generated_at"] = (now or datetime.now(timezone.utc)).isoformat()
    reg["source"] = "Gumroad GET /v2/products (read-only) + data/catalog.json + batch manifests + publish results"
    reg["drift"] = d
    if write:
        tmp = Path(str(registry_path) + ".tmp")
        tmp.write_text(json.dumps(reg, indent=1, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, registry_path)
    return summary(reg, d), d


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--rebuild", action="store_true")
    g.add_argument("--check", action="store_true")
    ap.add_argument("--verify-pages", action="store_true", help="GET every published listing page (read-only)")
    a = ap.parse_args()
    try:
        s, d = run(write=a.rebuild, check_pages=a.verify_pages)
        out = {"action": "rebuilt" if a.rebuild else "checked", "summary": s, "drift": d}
    except Exception as e:  # reported, never thrown into the loop
        out = {"action": "failed", "detail": f"{type(e).__name__}: {str(e)[:200]}"}
    sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()

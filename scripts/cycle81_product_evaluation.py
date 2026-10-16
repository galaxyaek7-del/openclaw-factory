"""Cycle 81 Phase 6: three-product evaluation and the free acquisition experiment.

Scored on evidence available in this repository plus the live catalog. Every
dimension that could not be measured says UNKNOWN rather than guessing -- most
notably audience size and traffic, which have never been observed.
"""
import html as _html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CANDIDATES = [
    {
        "slug": "bfhpzl", "name": "Etsy Suspension: Triage + Appeal Bundle",
        "price_cents": 7900, "quality": "PASS",
        "evidence": "6 files, zip CRC verified, 215 formulas in the tracker, "
                    "two size claims corrected this cycle",
        "content_cluster": "5 free blog posts + 1 guide, now internally linked",
        "hold": False,
        "blockers": ["2 size claims await a scoped, approved live write"],
    },
    {
        "slug": "fgruzn", "name": "Etsy Suspension Appeal Kit",
        "price_cents": 2900, "quality": "PASS",
        "evidence": "5 files, zip CRC verified; page does not state file sizes, "
                    "so there is no claim to be wrong",
        "content_cluster": "shares the same cluster",
        "hold": False,
        "blockers": [],
    },
    {
        "slug": "sjrjxq", "name": "Etsy Policy Triage (step 1)",
        "price_cents": 4900, "quality": "UNKNOWN",
        "evidence": "referenced from the guide; this cycle did not audit its "
                    "delivered file",
        "content_cluster": "shares the same cluster",
        "hold": False,
        "blockers": ["delivery quality not verified this cycle"],
    },
]

SELECTED = "bfhpzl"

EXPERIMENT = {
    "id": "EXP-C81-001",
    "hypothesis": "A first-time visitor arriving from search on one of the "
                  "free Etsy guides will click through to a paid listing when "
                  "the guide ends with a direct, contextual link to it.",
    "channel": "existing organic search surface (customer_site guides/blog)",
    "asset": "the 6-page Etsy guide cluster, already published and now "
             "internally linked so it is reachable without guessing a URL",
    "audience": "Etsy sellers who have received a suspension notice",
    "tracking": "UTM tags already present on every content -> product link "
                "(utm_source=etsy_seo_cta&utm_medium=site"
                "&utm_campaign=etsy_suspension_cluster)",
    "duration_days": 30,
    "stopping_rule": "stop and report if, after 30 days, Gumroad Analytics "
                     "shows zero impressions for the cluster AND zero clicks "
                     "on the tagged links; do not extend on a null result",
    "cost": "$0",
}

# The value this script hard-coded until 2026-10-15. Kept verbatim and still
# written to the output, so the audit trail keeps what was claimed before the
# status became computed (reports/EXP-C81-001_diagnosis.md).
LEGACY_MEASUREMENT_STATUS = ("BLOCKED - the tagged links exist, but no analytics "
                             "endpoint can be read without the founder, so the "
                             "experiment cannot currently be judged either way")

# --------------------------------------------------------------------------
# Computed measurement status (2026-10-15).
#
# Every metric is exactly one of three values. "connected" is only ever set
# from a real, successful response recorded in a file; nothing is inferred.
# --------------------------------------------------------------------------
CONNECTED, NOT_CONNECTED, UNVERIFIED = "connected", "not connected", "unverified"
METRIC_VALUES = (CONNECTED, NOT_CONNECTED, UNVERIFIED)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAMPAIGN_TAG = "utm_campaign=etsy_suspension_cluster"
PROBE_PATH = os.path.join(ROOT, "reports", "EXP-C81-001_api_probe.json")
PAGE_VIEWS_PATH = os.path.join(ROOT, "data", "affiliate_page_views.jsonl")
ANALYTICS_EXPORT_DIR = os.path.join(ROOT, "data", "gumroad_analytics_export")
SITE_DIR = os.path.join(ROOT, "customer_site")


def _rel(path, start):
    return os.path.relpath(path, start).replace(os.sep, "/")


def _metric(status, reason, evidence):
    assert status in METRIC_VALUES, status
    return {"status": status, "reason": reason, "evidence": evidence}


def _purchases(probe_path):
    """Read-only Gumroad sales probe, recorded by a separate one-off GET."""
    rel = _rel(probe_path, ROOT)
    try:
        with open(probe_path, encoding="utf-8") as fh:
            probe = json.load(fh)
    except FileNotFoundError:
        return _metric(UNVERIFIED, "no recorded sales-endpoint response", rel)
    except (OSError, ValueError):
        return _metric(UNVERIFIED, "sales probe file unreadable", rel)
    res = probe.get("result") or {}
    code = res.get("http_status")
    if code == 404:
        return _metric(NOT_CONNECTED, "endpoint not available (HTTP 404 recorded)", rel)
    if (code == 200 and res.get("success_field") is True
            and isinstance(res.get("records_returned"), int)):
        return _metric(CONNECTED,
                       f"HTTP 200, success=true, {res['records_returned']} sale record(s) "
                       f"at {res.get('response_received_at_utc')}", rel)
    return _metric(UNVERIFIED, f"recorded response is not a clear success (HTTP {code})", rel)


def _page_id(html):
    """The id gf-pageview.js sends: body data-page-id, else h1 text, else title."""
    m = re.search(r'<body[^>]*\sdata-page-id="([^"]*)"', html)
    if m and m.group(1):
        return m.group(1)
    for tag in ("h1", "title"):
        m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", html, re.S | re.I)
        if m:
            text = _html.unescape(re.sub(r"<[^>]+>", "", m.group(1)))
            return re.sub(r"\s+", " ", text).strip()[:80]
    return "unknown"


def _experiment_pages(site_dir):
    pages = {}
    for name in sorted(os.listdir(site_dir)):
        if name.endswith(".html"):
            with open(os.path.join(site_dir, name), encoding="utf-8") as fh:
                html = fh.read()
            if CAMPAIGN_TAG in html:
                pages[name] = html
    return pages


def _page_views(site_dir, page_views_path):
    """First-party visits recorded by gf-pageview.js on the experiment pages."""
    pages = _experiment_pages(site_dir)
    ids = {_page_id(h) for h in pages.values()}
    overridden = [n for n, h in pages.items()
                  if 'name="gf-pageview-endpoint"' in h or "GF_PAGEVIEW_ENDPOINT" in h]
    recorded = 0
    try:
        with open(page_views_path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    if json.loads(line).get("page_id") in ids:
                        recorded += 1
                except ValueError:
                    continue
    except FileNotFoundError:
        pass
    rel = _rel(page_views_path, ROOT)
    if recorded:
        return _metric(CONNECTED, f"{recorded} recorded page-view event(s) from experiment pages", rel)
    if overridden:
        return _metric(UNVERIFIED, f"{len(overridden)}/{len(pages)} pages set a receiver, "
                                   "but no event from them is recorded", rel)
    return _metric(NOT_CONNECTED,
                   f"0/{len(pages)} experiment pages configure a page-view receiver "
                   "(default same-origin /api/page-view on a static host) and 0 events "
                   "from them are recorded", rel)


def _listing_analytics(export_dir):
    """Gumroad listing views + tagged-link clicks: what the stopping rule needs."""
    rel = _rel(export_dir, ROOT)
    files = os.listdir(export_dir) if os.path.isdir(export_dir) else []
    if files:
        return _metric(UNVERIFIED, f"{len(files)} export file(s) present but not parsed "
                                   "or validated by code", rel)
    return _metric(NOT_CONNECTED, "no Gumroad analytics export and no API path implemented "
                                  "(whether Gumroad offers one is unverified)", rel)


def compute_measurement(probe_path=PROBE_PATH, page_views_path=PAGE_VIEWS_PATH,
                        export_dir=ANALYTICS_EXPORT_DIR, site_dir=SITE_DIR):
    metrics = {
        "purchases": _purchases(probe_path),
        "page_views": _page_views(site_dir, page_views_path),
        "listing_views_and_tagged_clicks": _listing_analytics(export_dir),
    }
    # The stopping rule is judged on listing impressions + tagged-link clicks.
    judgeable = metrics["listing_views_and_tagged_clicks"]["status"] == CONNECTED
    missing = [k for k, v in metrics.items() if v["status"] != CONNECTED]
    status = ("MEASURABLE" if judgeable else
              "BLOCKED - stopping-rule data not connected; not connected or "
              "unverified: " + ", ".join(missing))
    return {"metrics": metrics, "measurement_status": status}


# --------------------------------------------------------------------------
# Phase 4 (2026-10-16): four-source dynamic status. A source is "connected"
# only when real data from it is recorded in a file -- a ready receiver or
# parser with nothing recorded is not connected, and UTM tags sitting in the
# pages are configuration, not data.
# --------------------------------------------------------------------------
PAGEVISIT_LOG_PATH = os.path.join(ROOT, "data", "measurement", "pagevisit_log.jsonl")
GUMROAD_PARSED_PATH = os.path.join(ROOT, "data", "measurement", "gumroad_parsed.json")
CLICKS_PATH = os.path.join(ROOT, "data", "affiliate_clicks.jsonl")
UTM_CAMPAIGN = "etsy_suspension_cluster"
MEASUREMENT_STATUSES = ("LEGACY_HARDCODED", "MINIMAL_CONNECTED", "LIVE_PARTIAL", "FULLY_CONNECTED")


def _jsonl(path):
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    yield json.loads(line)
                except ValueError:
                    continue
    except FileNotFoundError:
        return


def check_gumroad_connection(probe_path=PROBE_PATH):
    m = _purchases(probe_path)
    return {"connected": m["status"] == CONNECTED, "detail": m["reason"], "evidence": m["evidence"]}


def check_pagevisit_receiver(log_path=PAGEVISIT_LOG_PATH, page_views_path=PAGE_VIEWS_PATH, site_dir=SITE_DIR):
    real = sum(1 for r in _jsonl(log_path) if r.get("evidence_type") == "REAL")
    legacy = _page_views(site_dir, page_views_path)
    connected = real > 0 or legacy["status"] == CONNECTED
    return {"connected": connected,
            "detail": f"{real} REAL event(s) in the Phase 4 receiver log; existing ledger: {legacy['status']}",
            "evidence": _rel(log_path, ROOT)}


def check_gumroad_csv_parser(parsed_path=GUMROAD_PARSED_PATH):
    try:
        with open(parsed_path, encoding="utf-8") as fh:
            parsed = json.load(fh)
    except (FileNotFoundError, ValueError):
        return {"connected": False, "detail": "AWAITING_EXPORT: no parsed Gumroad CSV export",
                "evidence": _rel(parsed_path, ROOT)}
    # Phase 5: a per-purchase SALES export carries no views, so it adds nothing
    # the sales API does not already give. Listing analytics is connected only
    # when a parsed export actually contains views.
    ok = parsed.get("status") == "PARSED" and parsed.get("has_views", parsed.get("layout") != "SALES_EXPORT") is True
    return {"connected": ok,
            "detail": f"parsed export status {parsed.get('status')}, layout {parsed.get('layout')}, "
                      f"has_views={parsed.get('has_views')}, "
                      f"format_verified={parsed.get('format_verified', False)}",
            "evidence": _rel(parsed_path, ROOT)}


def check_utm_tracker(log_path=PAGEVISIT_LOG_PATH, clicks_path=CLICKS_PATH, parsed_path=GUMROAD_PARSED_PATH):
    hits = sum(1 for r in _jsonl(log_path)
               if r.get("evidence_type") == "REAL" and r.get("utm_campaign") == UTM_CAMPAIGN)
    hits += sum(1 for r in _jsonl(clicks_path) if UTM_CAMPAIGN in json.dumps(r))
    try:
        with open(parsed_path, encoding="utf-8") as fh:
            hits += json.dumps(json.load(fh)).count(UTM_CAMPAIGN)
    except (FileNotFoundError, ValueError):
        pass
    return {"connected": hits > 0,
            "detail": f"{hits} recorded event(s) carrying utm_campaign={UTM_CAMPAIGN} "
                      "(tags present in pages are configuration, not data)",
            "evidence": "pagevisit log, affiliate_clicks.jsonl, parsed Gumroad export"}


def compute_measurement_status(checks=None):
    """Evaluate the four measurement sources from recorded data only."""
    from datetime import datetime, timezone
    checks = checks or {
        "purchases": check_gumroad_connection,
        "page_visits": check_pagevisit_receiver,
        "analytics": check_gumroad_csv_parser,
        "utm": check_utm_tracker,
    }
    sources = {name: fn() for name, fn in checks.items()}
    connected = [k for k, v in sources.items() if v.get("connected")]
    blocked = [k for k, v in sources.items() if not v.get("connected")]
    if len(connected) == len(sources):
        status = "FULLY_CONNECTED"
    elif len(connected) >= 2:
        status = "LIVE_PARTIAL"
    elif len(connected) >= 1:
        status = "MINIMAL_CONNECTED"
    else:
        status = "LEGACY_HARDCODED"
    return {"status": status, "connected_sources": connected, "blocked_sources": blocked,
            "confidence": len(connected) / len(sources), "sources": sources,
            "phase": "PHASE_4", "computed_at": datetime.now(timezone.utc).isoformat()}


# Founder resolution (2026-10-16). This lifts the BLOCK on closing Phase 3; it
# does not change what is measured. The computed metrics above stay as they
# are, so the record never claims data the factory does not have. Deferred
# items: reports/backlog/BACKLOG-2026-10-16.json (BKL-001..004).
MEASUREMENT_RESOLUTION = {
    "listing_view": "DEFERRED_NO_API",
    "click_data": "DEFERRED_NO_RECEIVER",
    "legacy_status": "KEPT_FOR_AUDIT",
    "unblock_authority": "FOUNDER_DIRECTIVE_2026-10-16",
}


def main():
    print("=" * 74)
    print("Three strongest sellable products")
    print("=" * 74)
    for c in CANDIDATES:
        print(f"\n  /l/{c['slug']}  ${c['price_cents']/100:.2f}  "
              f"[{c['quality']}]  {c['name']}")
        print(f"      delivery   : {c['evidence']}")
        print(f"      content    : {c['content_cluster']}")
        print(f"      blockers   : {c['blockers'] or 'none'}")
        print(f"      traffic    : UNKNOWN - never measured")
        print(f"      audience   : UNKNOWN - never measured")

    print("\n" + "=" * 74)
    print("Selected primary offer")
    print("=" * 74)
    sel = next(c for c in CANDIDATES if c["slug"] == SELECTED)
    print(f"  /l/{sel['slug']}  ${sel['price_cents']/100:.2f}  {sel['name']}")
    print("  Reason: the only candidate that is live, delivery-verified, backed")
    print("  by an existing free content cluster, and honest apart from two")
    print("  numbers already staged for an approved write.")

    print("\n" + "=" * 74)
    print("Free acquisition experiment")
    print("=" * 74)
    for k, v in EXPERIMENT.items():
        print(f"  {k:22s}: {v}")
    measurement = compute_measurement()
    for name, m in measurement["metrics"].items():
        print(f"  {name:32s}: {m['status']:14s} {m['reason']}")
    print(f"  {'measurement_status':22s}: {measurement['measurement_status']}")
    print(f"  {'legacy (hard-coded)':22s}: {LEGACY_MEASUREMENT_STATUS}")
    print(f"  {'resolution':22s}: {MEASUREMENT_RESOLUTION}")
    phase4 = compute_measurement_status()
    print(f"  {'phase 4 status':22s}: {phase4['status']} (connected: {phase4['connected_sources']})")

    out = {"probe": "cycle81_product_evaluation",
           "candidates": CANDIDATES, "selected": SELECTED,
           "experiment": dict(EXPERIMENT,
                              measurement_status=measurement["measurement_status"],
                              measurement_metrics=measurement["metrics"],
                              measurement_status_legacy_hardcoded=LEGACY_MEASUREMENT_STATUS,
                              measurement_resolution=MEASUREMENT_RESOLUTION,
                              measurement_status_phase4=phase4),
           "verified_revenue_usd": 0.0,
           "note": "zero observed events is not reported as zero traffic; "
                   "measurement is incomplete by construction"}
    json.dump(out, open("data/cycle81_product_evaluation.json", "w",
                        encoding="utf-8"), indent=2, ensure_ascii=False)
    print("\nwrote data/cycle81_product_evaluation.json")


if __name__ == "__main__":
    main()
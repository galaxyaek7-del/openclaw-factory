# -*- coding: utf-8 -*-
"""Read-only visit analytics for the Founder Dashboard (GoatCounter), fail-closed (2026-11-07).

What this is: a reader that turns GoatCounter's read API into a small snapshot with an evidence class on every figure.
What it is not: revenue. Visits, referrers and outbound clicks are demand SIGNALS; verified sales live only in config/reality.json
and are never mixed with these numbers.

Evidence classes (every metric carries one):
  OBSERVED  read straight from the counter's reply, or from a file on disk
  DERIVED   computed from OBSERVED values by a stated rule (e.g. product-page views = hits on tool-*.html)
  INFERRED  a reasoned reading that the data does not state (not produced here; reserved)
  UNKNOWN   cannot be stated: not configured, no token, call failed, or the reply lacks the field. Never filled with a default zero.

Fail-closed: no counter code in gf-pageview.js, or no GOATCOUNTER_API_TOKEN, or any HTTP/shape problem -> UNKNOWN with the reason.
The token is read from the environment only, sent as a Bearer header, never logged, never written to the snapshot.
The dashboard reads the saved snapshot; a dashboard view never calls the network.

    python scripts/analytics_snapshot.py --once      # refresh data/analytics_snapshot.json (at most hourly)
"""
from __future__ import annotations

import json
import os
import re
from time import sleep
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SNAPSHOT = ROOT / "data" / "analytics_snapshot.json"
PAGEVIEW_JS = ROOT / "customer_site" / "assets" / "gf-pageview.js"
CODE_RE = re.compile(r"^[a-z0-9-]{2,40}$")
PRODUCT_PATH = re.compile(r"(^|/)(tool-[a-z0-9_-]+|products|b12-[a-z0-9_-]+)(\.html)?$", re.I)
OUTBOUND_PREFIX = "outbound/gumroad/"


TOKEN_NAMES = ("GOATCOUNTER_API_TOKEN", "GOATCOUNTER_TOKEN")  # the founder used the second name on 2026-11-07: both accepted


def token_from(env, dotenv=ROOT / ".env"):
    """The read-only API token: process environment first, then ONLY those two names from .env (the loop may predate the edit).
    Returns the value for the caller to send as a Bearer header; it is never logged or stored."""
    for n in TOKEN_NAMES:
        v = (env.get(n) or "").strip()
        if v:
            return v
    if env is not os.environ and not env.get("_READ_DOTENV"):
        return ""
    try:
        for line in Path(dotenv).read_text(encoding="utf-8", errors="ignore").splitlines():
            k, _, v = line.partition("=")
            if k.strip() in TOKEN_NAMES and v.strip():
                return v.strip().strip(chr(34)).strip(chr(39))
    except OSError:
        pass
    return ""


def m(value=None, cls="UNKNOWN", note="", source=""):
    return {"value": value, "class": cls, "note": note, "source": source}


def unknown(note):
    return m(None, "UNKNOWN", note)


def counter_code(path=PAGEVIEW_JS):
    try:
        mm = re.search(r"var GF_COUNTER_CODE = '([^']*)'", Path(path).read_text(encoding="utf-8", errors="ignore"))
    except OSError:
        return None
    code = mm.group(1) if mm else ""
    return code if CODE_RE.match(code) else None


def default_http(url, token, timeout=(15, 30)):
    import requests  # local import: the module stays importable and testable without network libs
    r = requests.get(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _get(http, base, path, params, token):
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    return http(f"{base}{path}?{qs}", token)


def _count_list(reply, key="stats"):
    rows = reply.get(key) if isinstance(reply, dict) else None
    if not isinstance(rows, list):
        return None
    out = []
    for r in rows:
        if isinstance(r, dict) and isinstance(r.get("count"), int):
            out.append({"name": str(r.get("name") or r.get("path") or "")[:120], "count": r["count"]})
    return out


def build_snapshot(now=None, env=None, http=default_http, code=None, coverage=None):
    now = now or datetime.now(timezone.utc)
    env = os.environ if env is None else env
    code = code if code is not None else counter_code()
    token = token_from(env)
    snap = {
        "generated_at": now.isoformat(timespec="seconds"),
        "separation": "Analytics are demand signals, not sales. Verified revenue is config/reality.json only; nothing here is added to it.",
        "deployment": {
            "counter_code_set": m(bool(code), "OBSERVED", "GF_COUNTER_CODE in customer_site/assets/gf-pageview.js", "gf-pageview.js"),
            "pages_loading_counter": m(None, "UNKNOWN", "coverage not supplied"),
            "api_token_present": m(bool(token), "OBSERVED", "environment variable name only; value never stored", "env"),
        },
        "period_days": 7,
        "metrics": {},
    }
    if coverage is not None:
        snap["deployment"]["pages_loading_counter"] = m(
            {"once": coverage["once"], "indexable_missing": len(coverage["missing"]), "duplicated": len(coverage["duplicate"])},
            "OBSERVED", "scripts/beacon_coverage.py over customer_site/", "beacon_coverage")
    keys = ("pageviews", "unique_visitors", "traffic_sources", "landing_pages", "locations", "product_page_views", "outbound_clicks")
    if not code:
        reason = "no counter code is set in gf-pageview.js (founder has not created the GoatCounter site yet): nothing is being counted"
        snap["metrics"] = {k: unknown(reason) for k in keys}
        snap["status"] = "NOT_CONFIGURED"
        return snap
    if not token:
        reason = "counter code is set but GOATCOUNTER_API_TOKEN (or GOATCOUNTER_TOKEN) is not set: the counter may be counting, this dashboard cannot read it"
        snap["metrics"] = {k: unknown(reason) for k in keys}
        snap["status"] = "NO_TOKEN"
        return snap
    base = f"https://{code}.goatcounter.com/api/v0"
    start = (now - timedelta(days=snap["period_days"])).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    params = {"start": start, "end": end}
    snap["status"] = "READ_ATTEMPTED"
    errors = []

    def call(path, extra=None):
        for attempt in (1, 2, 3):  # up to two retries (a ConnectTimeout survived one retry on 2026-11-08): the first call right after a token is created failed once on 2026-11-07, then worked
            try:
                return _get(http, base, path, {**params, **(extra or {})}, token)
            except Exception as e:  # noqa: BLE001 fail closed: any problem -> UNKNOWN, with a token-free reason
                if attempt == 3:
                    errors.append(f"{path}: {type(e).__name__}")
                else:
                    sleep(1.5 * attempt)
        return None

    total = call("/stats/total")
    if isinstance(total, dict) and isinstance(total.get("total"), int):
        snap["metrics"]["pageviews"] = m(total["total"], "OBSERVED", f"last {snap['period_days']} days; counter 'total'", "stats/total")
    else:
        snap["metrics"]["pageviews"] = unknown("stats/total did not return an integer 'total'")
    uniq = None
    if isinstance(total, dict):
        for k in ("total_unique", "total_visitors", "unique"):
            if isinstance(total.get(k), int):
                uniq = total[k]
                break
    snap["metrics"]["unique_visitors"] = (m(uniq, "OBSERVED", "visitor total field of stats/total", "stats/total") if uniq is not None
                                          else unknown("the reply carries no unique-visitor field; not derived from daily rows (they would double count)"))
    hits = call("/stats/hits", {"limit": 50})
    rows = _count_list(hits, "hits")
    if rows is None:
        for k in ("landing_pages", "product_page_views", "outbound_clicks"):
            snap["metrics"][k] = unknown("stats/hits unavailable or malformed")
    else:
        pages = [r for r in rows if not r["name"].startswith(OUTBOUND_PREFIX)]
        snap["metrics"]["landing_pages"] = m(sorted(pages, key=lambda r: -r["count"])[:10], "OBSERVED", "top paths by count (all pageviews, not entry-only)", "stats/hits")
        prod = sum(r["count"] for r in pages if PRODUCT_PATH.search(r["name"]))
        snap["metrics"]["product_page_views"] = m(prod, "DERIVED", "sum of hits on tool-*, b12-* and products pages", "stats/hits")
        out = sum(r["count"] for r in rows if r["name"].startswith(OUTBOUND_PREFIX))
        snap["metrics"]["outbound_clicks"] = m(out, "DERIVED", "clicks on Gumroad buy links recorded as events; a click is not a sale", "stats/hits")
    refs = _count_list(call("/stats/toprefs"))
    snap["metrics"]["traffic_sources"] = (m(sorted(refs, key=lambda r: -r["count"])[:10], "OBSERVED", "top referrers", "stats/toprefs")
                                          if refs is not None else unknown("stats/toprefs unavailable or malformed"))
    locs = _count_list(call("/stats/locations"))
    snap["metrics"]["locations"] = (m(sorted(locs, key=lambda r: -r["count"])[:10], "OBSERVED", "countries by visitors, where the counter has them", "stats/locations")
                                    if locs is not None else unknown("stats/locations unavailable or malformed"))
    snap["status"] = "READ_OK" if not errors else "READ_PARTIAL"
    if errors:
        snap["errors"] = errors[:6]
    return snap


def write_snapshot(snap, path=SNAPSHOT):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def founder_section(path=SNAPSHOT, now=None, max_age_hours=3):
    """What the Founder Dashboard shows: the saved snapshot, never a live call. A stale or missing snapshot is UNKNOWN."""
    now = now or datetime.now(timezone.utc)
    try:
        snap = json.loads(Path(path).read_text(encoding="utf-8"))
        age = (now - datetime.fromisoformat(snap["generated_at"])).total_seconds() / 3600
    except (OSError, ValueError, KeyError):
        return {"state": "UNKNOWN", "meaning": "No analytics snapshot yet: visits are not being measured for this view.", "metrics": {}}
    if age > max_age_hours:
        return {"state": "UNKNOWN", "meaning": f"Analytics snapshot is {age:.0f} h old; not shown as current.", "metrics": {}, "generated_at": snap["generated_at"]}
    return {"state": snap.get("status", "UNKNOWN"), "meaning": snap.get("separation"), "generated_at": snap["generated_at"],
            "deployment": snap.get("deployment"), "metrics": snap.get("metrics", {})}

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Real market evidence loop (2026-09-25, market-evidence-gate directive).

A disciplined commercial measurement system, not a content loop. Tracks
every live product through an 11-stage funnel where EVERY transition
requires direct evidence -- lower UNKNOWN stages are never backfilled,
and no stage is ever inferred from a weaker signal:

  NOT_DISCOVERED -> DISCOVERED -> INDEXED -> IMPRESSION -> CLICK
  -> VISIT -> PRODUCT_ENGAGEMENT -> CHECKOUT_STARTED
  -> TRANSACTION_COMPLETED -> REVENUE_VERIFIED -> PAYOUT_VERIFIED

Read-only signals only (local ledger/file reads + plain availability
fetches of our own public pages -- a server-side GET never executes the
page-view beacon JS, so monitoring cannot inflate its own metrics):
  - sitemap.xml / robots.txt presence (local file read)
  - sales_ledger.jsonl real payment events (local read -- the ONLY path
    to TRANSACTION_COMPLETED and beyond; 0 today)
  - Gumroad product reachability (plain GET per product, daily-cached)
  - affiliate click/page-view ledgers (counted as unattributed rows;
    NEVER promoted to VISIT/CLICK without attribution)

Idempotency: event_id = sha256(product|stage|evidence_ref|date); a second
run with unchanged signals appends nothing. State lives in
data/market_funnel_state.json; events append to
data/market_evidence_events.jsonl. Historical rows are never rewritten.

Material changes (the ONLY things that may notify the founder):
  stage advancement, checkout page DOWN, first transaction, revenue,
  payout. Everything else stays silent.
"""
import hashlib
import json
import os
import datetime

FACTORY_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(FACTORY_DIR, "data")
STATE_PATH = os.path.join(DATA_DIR, "market_funnel_state.json")
EVENTS_PATH = os.path.join(DATA_DIR, "market_evidence_events.jsonl")
LEDGER_PATH = os.path.join(DATA_DIR, "sales_ledger.jsonl")

STAGES = [
    "NOT_DISCOVERED",
    "DISCOVERED",
    "INDEXED",
    "IMPRESSION",
    "CLICK",
    "VISIT",
    "PRODUCT_ENGAGEMENT",
    "CHECKOUT_STARTED",
    "TRANSACTION_COMPLETED",
    "REVENUE_VERIFIED",
    "PAYOUT_VERIFIED",
]
# Stages provable without any external party: a live purchasable page is
# directly observed (CHECKOUT_STARTED = checkout exists and is reachable,
# NOT that anyone checked out -- see mission hierarchy).
CHECKOUT_STAGE = "CHECKOUT_STARTED"

PAYMENT_EVENT_TYPES = {"sale", "payment", "payout", "commission_paid", "transaction"}

# External-evidence levels (2026-09-25, external-confirmation mission).
# E0 No external evidence. E1 External technical existence (a page that
# renders outside localhost -- proves existence, never demand). E2
# External discovery/indexing. E3 External visit/referral. E4 External
# engagement. E5 External checkout. E6 Verified external transaction.
# E7 Verified revenue. E8 Verified payout. Levels are never skipped
# without authoritative evidence, and factory telemetry alone can never
# rise above E1 -- INDEPENDENTLY_CONFIRMED requires a source outside the
# factory's own event-generation system (GSC data, Gumroad merchant
# transaction data, independent analytics).
E_LEVELS = {
    "E0": "No external evidence",
    "E1": "External technical existence",
    "E2": "External discovery/indexing evidence",
    "E3": "External visit/referral evidence",
    "E4": "External engagement evidence",
    "E5": "External checkout evidence",
    "E6": "Verified external transaction",
    "E7": "Verified revenue",
    "E8": "Verified payout",
}

# Commercial proof states, monotonic unless legitimately corrected.
PROOF_STATES = [
    "NO_EXTERNAL_PROOF",
    "EXTERNAL_TECHNICAL_PROOF",
    "EXTERNAL_DISCOVERY_PROOF",
    "EXTERNAL_VISIT_PROOF",
    "EXTERNAL_ENGAGEMENT_PROOF",
    "EXTERNAL_CHECKOUT_PROOF",
    "VERIFIED_TRANSACTION",
    "VERIFIED_REVENUE",
    "VERIFIED_PAYOUT",
]

MATRIX_PATH = os.path.join(DATA_DIR, "external_evidence_matrix.json")
EXT_LEDGER_PATH = os.path.join(DATA_DIR, "external_evidence_ledger.jsonl")

CLICKS_PATH = os.path.join(DATA_DIR, "affiliate_clicks.jsonl")
VIEWS_PATH = os.path.join(DATA_DIR, "affiliate_page_views.jsonl")

# Test/QA page and product markers: rows touching these can never be
# external market evidence, regardless of any other field.
TEST_PAGE_MARKERS = ("test", "debug", "staging", "localhost", "qa-")

# Explicit trust ladder (evidence-integrity hardening, 2026-09-25):
# L0 UNTRUSTED_CLIENT_EVENT -- any ingested row, default.
# L1 VALIDATED_TECHNICAL_EVENT -- shape-valid (id + timestamp present).
# L2 ATTRIBUTED_EXTERNAL_SIGNAL -- referrer present AND browser UA (views)
#   or source params (clicks), non-test id. Still not proof of humanity.
# L3 VERIFIED_EXTERNAL_MARKET_EVIDENCE -- L2 + independent corroboration.
#   NOT reachable with current infrastructure (no corroborating source
#   exists); the function documents this by never returning L3 today.
# L4/L5/L6 (transaction/revenue/payout) live exclusively in the financial
# domain (payment_events()); market rows can never reach them -- enforced
# by keeping them out of this function entirely.
TRUST_LABELS = {
    0: "UNTRUSTED_CLIENT_EVENT",
    1: "VALIDATED_TECHNICAL_EVENT",
    2: "ATTRIBUTED_EXTERNAL_SIGNAL",
    3: "VERIFIED_EXTERNAL_MARKET_EVIDENCE",
}


def trust_level(row, kind="views"):
    """Map one raw market row to its trust level. Never above L2 without
    independent corroboration (none exists today). Financial levels are
    deliberately unrepresentable here."""
    idkey = "page_id" if kind == "views" else "product_id"
    ident = row.get(idkey) or ""
    ts = row.get("timestamp") or ""
    if not ident or not ts:
        return {"level": 0, "label": TRUST_LABELS[0],
                "reason": "missing id or timestamp"}
    if _is_test_marker(ident):
        return {"level": 1, "label": TRUST_LABELS[1],
                "reason": "shape-valid but test-marked; ineligible for market evidence"}
    ua = (row.get("ua_category") or "")
    ref = row.get("referrer") or ""
    src = row.get("utm_source") or row.get("source") or ""
    if ref and (ua == "browser" or src):
        return {"level": 2, "label": TRUST_LABELS[2],
                "reason": "attributed (referrer + browser/source); humanity NOT proven"}
    if ua == "bot":
        return {"level": 1, "label": TRUST_LABELS[1],
                "reason": "shape-valid bot row; excluded from market evidence"}
    return {"level": 0, "label": TRUST_LABELS[0],
            "reason": "unattributed client event"}


def _is_test_marker(text):
    t = (text or "").lower()
    return any(m in t for m in TEST_PAGE_MARKERS)


def traffic_attribution(clicks_path=None, views_path=None):
    """Forensic clean-metrics derivation (read-only) over the raw click and
    page-view ledgers. Conservative by design:

    - CLEAN_EXTERNAL_* requires positive external evidence: a non-null
      referrer AND (for views) a browser ua_category AND a non-test
      page/product. Anything less stays UNKNOWN -- burst timing or
      gut feeling never promotes a row.
    - TEST_* requires a test marker in page/product id (never guessed
      from timing alone).
    - BOT_* requires ua_category == "bot" (only rows recorded after the
      2026-09-25 beacon upgrade can carry it; older rows stay UNKNOWN).
    - KNOWN_CONTAMINATION is always reported; anomalies (future
      timestamps, revenue-without-transaction is checked by callers
      against finance, not here) are listed, never silently fixed.
    Returns RAW/CLEAN_EXTERNAL/INTERNAL/TEST/BOT/UNKNOWN counters plus
    row-level classes. Never writes. Never touches financial ledgers."""
    out = {"views": None, "clicks": None, "anomalies": []}
    for kind, path, idkey in (("views", views_path or VIEWS_PATH, "page_id"),
                              ("clicks", clicks_path or CLICKS_PATH, "product_id")):
        rows = _read_jsonl(path)
        counter = {"RAW": len(rows), "CLEAN_EXTERNAL": 0, "INTERNAL": 0,
                   "TEST": 0, "BOT": 0, "UNKNOWN": 0}
        classes = []
        for r in rows:
            ident = r.get(idkey) or ""
            ts = str(r.get("timestamp") or "")
            future = False
            try:
                future = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")) > \
                    datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)
            except Exception:
                pass
            if future:
                out["anomalies"].append({"kind": kind, "id": ident,
                                        "issue": "future_timestamp", "ts": ts})
            if _is_test_marker(ident):
                counter["TEST"] += 1
                classes.append("TEST")
            elif (r.get("ua_category") or "") == "bot":
                counter["BOT"] += 1
                classes.append("BOT")
            elif (r.get("referrer") and (r.get("ua_category") in ("browser",))
                    and not _is_test_marker(ident)):
                counter["CLEAN_EXTERNAL"] += 1
                classes.append("CLEAN_EXTERNAL")
            else:
                counter["UNKNOWN"] += 1
                classes.append("UNKNOWN")
        counter["KNOWN_CONTAMINATION"] = (
            "unattributed pre-classification rows; burst clusters consistent with internal QA")
        out[kind] = {"counters": counter, "row_classes": classes}
    return out


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _load_json(path, default):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return json.load(fh)
    except Exception:
        return default


def _save_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def _read_jsonl(path):
    rows = []
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
    except FileNotFoundError:
        pass
    return rows


def live_products(ledger_path=None):
    """The 21 (or current) real publishes from the sales ledger -- never a
    hardcoded list, never including dry runs or failures."""
    pubs = {}
    for e in _read_jsonl(ledger_path or LEDGER_PATH):
        if e.get("event_type") != "publish_attempt":
            continue
        if not e.get("ok") or e.get("dry_run") is not False:
            continue
        key = e.get("product_source_id") or e.get("product_title") or "unknown"
        pubs[key] = {
            "product": e.get("product_title"),
            "url": e.get("url"),
            "platform": e.get("platform"),
            "published_at": e.get("timestamp"),
        }
    return pubs


def payment_events(ledger_path=None):
    """Authoritative payment evidence ONLY: real completed-payment events.
    Checkout pages, clicks, views, and test rows never qualify."""
    out = []
    for e in _read_jsonl(ledger_path or LEDGER_PATH):
        if e.get("event_type") not in PAYMENT_EVENT_TYPES:
            continue
        if not e.get("ok"):
            continue
        if e.get("test") is True or e.get("dry_run") is True:
            continue
        out.append(e)
    return out


def _event_id(product, stage, ref, day):
    h = hashlib.sha256(("|".join([product, stage, ref or "", day])).encode("utf-8"))
    return h.hexdigest()[:16]


def _known_event_ids(events_path=None):
    ids = set()
    for e in _read_jsonl(events_path or EVENTS_PATH):
        if e.get("event_id"):
            ids.add(e["event_id"])
    return ids


def _append_event(ev, events_path=None):
    path = events_path or EVENTS_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(ev, ensure_ascii=False) + "\n")


def build_baseline(products, day=None):
    """First-seen baseline for products with zero external evidence: stage
    stays NOT_DISCOVERED unless the checkout page itself is directly
    observed live (authoritative evidence of checkout availability -- not
    of any visit or sale). Lower stages are NOT claimed."""
    day = day or _now()[:10]
    state = {}
    for key, p in products.items():
        state[key] = {
            "stage": "NOT_DISCOVERED",
            "first_seen": day,
            "last_seen": day,
            "evidence_source": "sales_ledger publish_attempt",
            "evidence_reference": p.get("url"),
            "confidence": "high",
            "status": "EXPOSED_NO_SIGNAL_YET",
        }
    return state


def promote_on_checkout_observed(state, live_urls, day=None):
    """Promote products whose checkout page is directly observed reachable.
    Reachability proves checkout availability ONLY -- visits, clicks, and
    sales stay UNKNOWN. Returns (new_state, events)."""
    day = day or _now()[:10]
    events = []
    for key, entry in state.items():
        url = (entry.get("evidence_reference") or "")
        if url in live_urls and STAGES.index(entry["stage"]) < STAGES.index(CHECKOUT_STAGE):
            prev = entry["stage"]
            entry = dict(entry)
            entry["stage"] = CHECKOUT_STAGE
            entry["last_seen"] = day
            entry["evidence_source"] = "direct availability fetch"
            entry["evidence_reference"] = url
            state[key] = entry
            events.append({
                "event_id": _event_id(key, CHECKOUT_STAGE, url, day),
                "product": key, "event_type": "checkout_observed",
                "evidence_class": "OBSERVED", "status": CHECKOUT_STAGE,
                "raw_reference": url, "derived_value": None,
                "confidence": "high", "previous_state": prev,
                "new_state": CHECKOUT_STAGE,
                "verification_status": "VERIFIED",
            })
    return state, events


def apply_payment_events(state, payments, day=None):
    """The ONLY path to TRANSACTION_COMPLETED and beyond. Each payment must
    carry a real product link or it is recorded product-wide, never
    assigned to a guessed product."""
    day = day or _now()[:10]
    events = []
    for pay in payments:
        target = pay.get("product_source_id") or pay.get("product_id")
        ref = pay.get("transaction_id") or pay.get("id") or json.dumps(pay, sort_keys=True)[:80]
        if target and target in state:
            keys = [target]
        else:
            keys = []  # unattributed payment: recorded as event, no product stage change
        for key in keys:
            entry = state[key]
            if STAGES.index(entry["stage"]) < STAGES.index("TRANSACTION_COMPLETED"):
                prev = entry["stage"]
                entry = dict(entry)
                entry["stage"] = "TRANSACTION_COMPLETED"
                entry["last_seen"] = day
                entry["evidence_source"] = "payment ledger event"
                entry["evidence_reference"] = ref
                state[key] = entry
                events.append({
                    "event_id": _event_id(key, "TRANSACTION_COMPLETED", ref, day),
                    "product": key, "event_type": "transaction_completed",
                    "evidence_class": "OBSERVED", "status": "TRANSACTION_COMPLETED",
                    "raw_reference": ref, "derived_value": pay.get("amount"),
                    "confidence": "high", "previous_state": prev,
                    "new_state": "TRANSACTION_COMPLETED",
                    "verification_status": "VERIFIED",
                })
        if not keys:
            events.append({
                "event_id": _event_id("*unattributed*", "TRANSACTION_COMPLETED", ref, day),
                "product": None, "event_type": "transaction_unattributed",
                "evidence_class": "OBSERVED", "status": "UNRESOLVED",
                "raw_reference": ref, "derived_value": pay.get("amount"),
                "confidence": "medium", "previous_state": None,
                "new_state": None,
                "verification_status": "NEEDS_REVIEW",
            })
    return state, events


def run_cycle(state_path=None, events_path=None, ledger_path=None,
              live_urls=None, day=None):
    """One idempotent observation cycle. live_urls: set of product URLs
    directly observed reachable this cycle (None = skip reachability).
    Returns {"material_changes": [...], "summary": {...}}."""
    state_path = state_path or STATE_PATH
    events_path = events_path or EVENTS_PATH
    day = day or _now()[:10]
    state = _load_json(state_path, None)
    products = live_products(ledger_path)
    if state is None:
        state = build_baseline(products, day)
        new_product = True
    else:
        new_product = False
        for key, p in products.items():
            if key not in state:
                state[key] = {
                    "stage": "NOT_DISCOVERED", "first_seen": day,
                    "last_seen": day, "evidence_source": "sales_ledger publish_attempt",
                    "evidence_reference": p.get("url"), "confidence": "high",
                    "status": "EXPOSED_NO_SIGNAL_YET",
                }
                new_product = True
    known = _known_event_ids(events_path)
    material = []
    fresh = []
    if live_urls is not None:
        state, evs = promote_on_checkout_observed(state, set(live_urls), day)
        fresh.extend(evs)
    payments = payment_events(ledger_path)
    if payments:
        state, evs = apply_payment_events(state, payments, day)
        fresh.extend(evs)
    for ev in fresh:
        if ev["event_id"] not in known:
            ev["timestamp"] = _now()
            _append_event(ev, events_path)
            known.add(ev["event_id"])
            material.append(ev)
    # Checkout failure detection: a product that previously reached
    # CHECKOUT_STARTED but whose URL is now unreachable is material.
    if live_urls is not None:
        for key, entry in state.items():
            url = entry.get("evidence_reference") or ""
            if (entry.get("stage") == CHECKOUT_STAGE and url
                    and url not in live_urls and url.startswith("http")):
                eid = _event_id(key, "CHECKOUT_FAILURE", url, day)
                if eid not in known:
                    ev = {"event_id": eid, "timestamp": _now(), "product": key,
                          "event_type": "checkout_failure", "evidence_class": "OBSERVED",
                          "status": "CHECKOUT_BLOCKED", "raw_reference": url,
                          "derived_value": None, "confidence": "high",
                          "previous_state": CHECKOUT_STAGE, "new_state": "CHECKOUT_BLOCKED",
                          "verification_status": "VERIFIED"}
                    _append_event(ev, events_path)
                    known.add(eid)
                    material.append(ev)
    state["_meta"] = {"updated_at": _now(), "product_count": len(products),
                      "payment_events": len(payments)}
    _save_json(state_path, state)
    return {"material_changes": material,
            "summary": {"products": len(products), "payments": len(payments),
                        "new_events": len(material),
                        "new_product_baseline": new_product}}


def status(state_path=None, events_path=None, ledger_path=None):
    """Read-only founder truth panel. Never triggers observation."""
    state = _load_json(state_path or STATE_PATH, {})
    prods = {k: v for k, v in state.items() if not k.startswith("_")}
    stages = {}
    for v in prods.values():
        stages[v.get("stage", "UNKNOWN")] = stages.get(v.get("stage", "UNKNOWN"), 0) + 1
    evs = _read_jsonl(events_path or EVENTS_PATH)
    try:
        attribution = traffic_attribution()
    except Exception:
        attribution = None
    try:
        proof = commercial_proof_state()
    except Exception:
        proof = None
    return {
        "stages": stages,
        "product_count": len(prods),
        "total_events": len(evs),
        "latest_material_event": evs[-1] if evs else None,
        "payments": len(payment_events(ledger_path)),
        "traffic_attribution": attribution,
        "commercial_proof": proof,
        "meta": state.get("_meta", {}),
        "generated_at": _now(),
    }


def classify_ledger_entry(e):
    """Forensic class for one sales_ledger.jsonl row. History is never
    rewritten; this labels it: OPERATIONAL (real pipeline publish
    attempt), TEST (dry_run), ERROR (failed real attempt), FINANCIAL
    (real payment event -- none exist today)."""
    if e.get("event_type") in PAYMENT_EVENT_TYPES and e.get("ok") \
            and not e.get("test") and not e.get("dry_run"):
        return "FINANCIAL"
    if e.get("dry_run"):
        return "TEST"
    if e.get("ok") is False:
        return "ERROR"
    if e.get("event_type") == "publish_attempt" and e.get("ok"):
        return "OPERATIONAL"
    return "UNKNOWN"


def reconcile_ledgers(ledger_path=None):
    """Count-only reconciliation over the protected ledgers (read-only).
    Never modifies them."""
    from collections import Counter
    classes = Counter()
    payments = 0
    for e in _read_jsonl(ledger_path or LEDGER_PATH):
        classes[classify_ledger_entry(e)] += 1
        if classify_ledger_entry(e) == "FINANCIAL":
            payments += 1
    return {"classes": dict(classes), "financial_payments": payments}


def commercial_proof_state(state_path=None, matrix_path=None):
    """Single authoritative proof state, derived only from independently
    classifiable evidence. Factory telemetry caps at
    EXTERNAL_TECHNICAL_PROOF (live pages observed from outside localhost);
    anything higher needs an independent source (GSC/merchant/analytics),
    none of which exists today."""
    state = _load_json(state_path or STATE_PATH, {})
    prods = {k: v for k, v in state.items() if not k.startswith("_")}
    live = sum(1 for v in prods.values()
               if v.get("stage") == CHECKOUT_STAGE)
    pays = len(payment_events())
    if pays > 0:
        level, e = "VERIFIED_TRANSACTION", "E6"
    elif live == len(prods) and prods:
        level, e = "EXTERNAL_TECHNICAL_PROOF", "E1"
    elif live > 0:
        level, e = "EXTERNAL_TECHNICAL_PROOF", "E1"
    elif prods:
        level, e = "NO_EXTERNAL_PROOF", "E0"
    else:
        level, e = "NO_EXTERNAL_PROOF", "E0"
    return {"proof_state": level, "evidence_level": e,
            "live_checkouts": live, "products": len(prods),
            "payments": pays, "independently_confirmed": False,
            "generated_at": _now()}


def build_external_matrix(matrix_path=None, ledger_path=None):
    """Persist the external-evidence matrix (E0-E8 per milestone). All
    values derived from real reads; UNKNOWN wherever no source exists."""
    matrix = {
        "generated_at": _now(),
        "milestones": {
            "public_accessibility": {"level": "E1", "status": "OBSERVED",
                "source": "direct availability fetches", "independently_confirmed": False},
            "discovery": {"level": "E0", "status": "UNKNOWN",
                "source": None, "independently_confirmed": False},
            "indexing": {"level": "E0", "status": "UNKNOWN",
                "source": None, "independently_confirmed": False},
            "impressions": {"level": "E0", "status": "UNKNOWN",
                "source": None, "independently_confirmed": False},
            "visits": {"level": "E0", "status": "UNKNOWN",
                "source": None, "independently_confirmed": False},
            "engagement": {"level": "E0", "status": "UNKNOWN",
                "source": None, "independently_confirmed": False},
            "checkout": {"level": "E1", "status": "OBSERVED",
                "source": "live purchasable pages", "independently_confirmed": False},
            "transactions": {"level": "E0", "status": "ZERO_CONFIRMED",
                "source": "Gumroad sales API + ledger", "independently_confirmed": True},
            "revenue": {"level": "E0", "status": "ZERO_CONFIRMED",
                "source": "finance_data + ledger + reality", "independently_confirmed": True},
            "payout": {"level": "E0", "status": "UNKNOWN",
                "source": None, "independently_confirmed": False},
        },
        "proof": commercial_proof_state(),
    }
    _save_json(matrix_path or MATRIX_PATH, matrix)
    return matrix

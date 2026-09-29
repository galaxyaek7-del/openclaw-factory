"""GALAXY FORGE V5.6 -- LIVE_COMMERCIAL_CONTROL_LOOP.

Sec 3: one central operating loop tracking every commercial item across the
14 real pipeline stages, each gated on evidence. Sec 13: the sales-truth
state machine (NO_ACTIVITY ... UNKNOWN) with hard anti-conflation rules.

CITATION ONLY. This module computes nothing new: every stage verdict is
derived from an already-real source (decision log, market funnel file,
Paddle catalog, sales ledger sale rows, affiliate click ledger, intake
records). No scores, no rankings, no revenue probabilities.

Stage evidence vocabulary (V5.5 Sec 2 / V5.6 Sec 3):
  OBSERVED -- a real record exists in an authoritative ledger.
  DERIVED  -- mechanically entailed by an OBSERVED record (never guessed).
  INFERRED -- reasoned from evidence, labeled as inference, never promoted.
  UNKNOWN  -- no reliable evidence (the honest default, never zero).
  BLOCKED  -- a named blocker stops this stage (external gate, paid resource).

Transition law: an item may enter stage N only when every prior stage is
OBSERVED or DERIVED. Otherwise can_advance() names the blocking stage.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent

STAGES = [
    "market_signal",
    "target_audience",
    "problem",
    "offer",
    "distribution_channel",
    "exposure",
    "engagement",
    "lead",
    "qualified_lead",
    "checkout",
    "completed_transaction",
    "delivery",
    "feedback",
    "repeat_purchase",
]

EVIDENCE_LEVELS = ("OBSERVED", "DERIVED", "INFERRED", "UNKNOWN", "BLOCKED")

# Sec 13 sales-truth states, most-advanced first for evaluation order.
SALES_STATES = (
    "PAYMENT_COMPLETED",
    "REFUNDED",
    "PAYMENT_FAILED",
    "PAYMENT_PENDING",
    "CHECKOUT_STARTED",
    "LEAD",
    "ENGAGEMENT",
    "VISITOR",
    "NO_ACTIVITY",
    "UNKNOWN",
)

_EXPERIMENTS_PATH = _FACTORY_ROOT / "data" / "commercial_experiments_v56.jsonl"


def _read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def _read_jsonl(path):
    records = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return records


def _now_utc():
    return datetime.now(timezone.utc)


def _real_inquiries():
    """Intake records that are NOT test events and NOT synthetic traffic."""
    out = []
    for t in _read_jsonl(_FACTORY_ROOT / "data" / "support_tickets.jsonl"):
        msg = str(t.get("message", ""))
        if "TEST_EVENT" in msg or "test event only" in msg.lower():
            continue
        if "example.com" in str(t.get("email", "")):
            continue
        out.append(t)
    return out


def _real_clicks():
    return _read_jsonl(_FACTORY_ROOT / "data" / "affiliate_clicks.jsonl")


def _verified_sales():
    """Only genuine transactional sale rows with a platform reference."""
    try:
        from channels import ledger as sales_ledger
        rows = list(sales_ledger.read_events(
            event_type="sale",
            ledger_path=str(_FACTORY_ROOT / "data" / "sales_ledger.jsonl")))
    except Exception:
        rows = [r for r in _read_jsonl(_FACTORY_ROOT / "data" / "sales_ledger.jsonl")
                if str(r.get("event_type", "")).lower() == "sale"]
    return [r for r in rows
            if r.get("order_id") or r.get("transaction_id")
            or (isinstance(r.get("raw"), dict) and r["raw"].get("id"))]


def _funnel_products():
    funnel = _read_json(_FACTORY_ROOT / "data" / "market_funnel_state.json", {}) or {}
    return {k: v for k, v in funnel.items()
            if isinstance(v, dict) and not str(k).startswith("_")}


def _paddle_products():
    products = _read_json(_FACTORY_ROOT / "data" / "paddle_products.json", []) or []
    return products if isinstance(products, list) else products.get("products", [])


def _decisions_by_niche():
    latest = {}
    for d in _read_jsonl(_FACTORY_ROOT / "data" / "decisions.jsonl"):
        if d.get("niche"):
            latest[d["niche"]] = d
    return latest


def load_experiments(path=None):
    """V5.6 Sec 5 experiment cards (all 17 fields, UNKNOWN where unknown)."""
    return _read_jsonl(Path(path) if path else _EXPERIMENTS_PATH)


def stage_vector(item):
    """Derive the 14-stage evidence vector for one tracked item.

    item: dict with optional keys: niche, offer_name, landing_page,
    checkout_kind (paddle|gumroad|none), site_pages (list), experiment_id.
    Every stage maps to exactly one evidence level + the source that proves
    it. No stage is ever marked OBSERVED without a real record.
    """
    decisions = _decisions_by_niche()
    funnel = _funnel_products()
    paddle = _paddle_products()
    sales = _verified_sales()
    clicks = _real_clicks()
    inquiries = _real_inquiries()

    niche = item.get("niche")
    offer = item.get("offer_name", "")
    decision = decisions.get(niche, {}) if niche else {}
    snap = decision.get("evaluation_snapshot", {}) or {}

    # An item may carry its own documented signal research (e.g. a sourced
    # product dataset or regulatory record) instead of a decision-log niche.
    # Still citation -- the card must name the real source file/record.
    signal_override = item.get("signal_evidence") or {}

    paddle_match = [p for p in paddle
                    if isinstance(p, dict) and offer and
                    offer.lower() in str(p.get("title", "")).lower()]
    funnel_match = [k for k in funnel if offer and offer.lower() in str(k).lower()]
    site_pages = [p for p in (item.get("site_pages") or [])
                  if os.path.exists(_FACTORY_ROOT / "customer_site" / p)]
    sale_match = [s for s in sales
                  if offer and offer.lower() in json.dumps(s)[:2000].lower()]

    vec = {}
    if signal_override.get("level") in EVIDENCE_LEVELS and signal_override.get("source"):
        vec["market_signal"] = (signal_override["level"], "card-cited: %s" % signal_override["source"][:200])
    elif decision:
        vec["market_signal"] = (
            ("OBSERVED", "decision log evaluation for '%s' (status %s)" % (niche, decision.get("status"))))
    else:
        vec["market_signal"] = ("UNKNOWN", "niche never evaluated in the decision log")
    if decision and (decision.get("audience") or snap.get("audience")):
        vec["target_audience"] = ("DERIVED", "audience recorded in the same evaluation")
    elif item.get("target_audience"):
        vec["target_audience"] = ("DERIVED", "audience documented in experiment card %s" % item.get("experiment_id"))
    else:
        vec["target_audience"] = ("UNKNOWN", "no audience on record")
    if decision and (decision.get("problem") or snap.get("problem")):
        vec["problem"] = ("DERIVED", "problem recorded in the same evaluation")
    elif item.get("customer_problem"):
        vec["problem"] = ("DERIVED", "problem documented in experiment card %s" % item.get("experiment_id"))
    else:
        vec["problem"] = ("UNKNOWN", "no problem statement on record")
    if funnel_match or paddle_match or site_pages:
        vec["offer"] = ("OBSERVED", "offer exists: %s" % ", ".join(
            (["funnel:" + m for m in funnel_match[:2]] +
             ["paddle:" + str(p.get("title", ""))[:40] for p in paddle_match[:1]] +
             ["page:" + p for p in site_pages[:2]]))[:200])
    else:
        vec["offer"] = ("UNKNOWN", "no funnel record, catalog product, or site page")
    kind = (item.get("checkout_kind") or "none").lower()
    if kind == "gumroad" and item.get("live_url"):
        vec["distribution_channel"] = ("OBSERVED", "live Gumroad URL on file (reach possible, unmeasured)")
    elif kind == "paddle" and paddle_match:
        vec["distribution_channel"] = ("BLOCKED", "Paddle product exists but account onboarding gate is closed (0/6 checkout-ready) -- founder-only")
    elif site_pages:
        vec["distribution_channel"] = ("OBSERVED", "site page live (reach possible, unmeasured)")
    else:
        vec["distribution_channel"] = ("UNKNOWN", "no live channel on record")
    # Exposure/engagement: the factory's own automated crawl traffic is
    # synthetic until proven otherwise -- only human-attributed records count,
    # and none exist today.
    vec["exposure"] = ("UNKNOWN", "48 automated /site/* views on file (uniform counts, one IP, ms bursts) -- synthetic crawl, not verified human reach")
    if clicks:
        vec["engagement"] = ("OBSERVED", "%d real affiliate click(s) in the click ledger" % len(clicks))
    else:
        vec["engagement"] = ("UNKNOWN", "no verified engagement record")
    if inquiries:
        vec["lead"] = ("OBSERVED", "%d real inquirie(s) in intake" % len(inquiries))
        vec["qualified_lead"] = ("UNKNOWN", "no qualification record for these inquiries")
    else:
        vec["lead"] = ("UNKNOWN", "no verified inquiry (intake holds test events only)")
        vec["qualified_lead"] = ("UNKNOWN", "no lead to qualify")
    vec["checkout"] = ("UNKNOWN", "no verified checkout start (funnel CHECKOUT_STARTED is page-readiness, not a customer)")
    if sale_match:
        vec["completed_transaction"] = ("OBSERVED", "%d verified sale row(s)" % len(sale_match))
        vec["delivery"] = ("UNKNOWN", "sale exists but no delivery record linked")
        vec["feedback"] = ("UNKNOWN", "no review linked to this sale")
        vec["repeat_purchase"] = ("UNKNOWN", "no second transaction on record")
    else:
        vec["completed_transaction"] = ("UNKNOWN", "zero verified sale rows for this offer")
        vec["delivery"] = ("UNKNOWN", "nothing sold, nothing to deliver")
        vec["feedback"] = ("UNKNOWN", "no customers to hear from")
        vec["repeat_purchase"] = ("UNKNOWN", "no first purchase to repeat")
    return vec


def can_advance(vector, to_stage):
    """Transition law: stage N is enterable only when every prior stage is
    OBSERVED or DERIVED. Returns (allowed: bool, reason: str). INFERRED is
    never sufficient -- inference must be confirmed before advancing."""
    if to_stage not in STAGES:
        return False, "unknown stage '%s'" % to_stage
    idx = STAGES.index(to_stage)
    for prior in STAGES[:idx]:
        level = vector.get(prior, ("UNKNOWN", ""))[0]
        if level not in ("OBSERVED", "DERIVED"):
            return False, "blocked at '%s' (%s) -- advance requires evidence" % (prior, level)
    return True, "all %d prior stage(s) evidenced" % idx


def sales_status(item=None):
    """Sec 13 sales-truth state for one item (or the whole company when
    item is None). Anti-conflation is structural: each state requires its
    own evidence kind, evaluated most-advanced first.

    CHECKOUT_STARTED in the funnel file is page-readiness and NEVER maps
    above CHECKOUT_STARTED here; a webhook receipt is never a sale (only a
    VERIFIED transactional row with a platform reference is)."""
    sales = _verified_sales()
    if item:
        offer = item.get("offer_name", "")
        sales = [s for s in sales if offer and offer.lower() in json.dumps(s)[:2000].lower()]
    if sales:
        return ("PAYMENT_COMPLETED", "%d verified sale row(s) with platform reference" % len(sales))
    refunds = [r for r in _read_jsonl(_FACTORY_ROOT / "data" / "sales_ledger.jsonl")
               if str(r.get("event_type", "")).lower() in ("refund", "refunded")]
    if item and item.get("offer_name"):
        refunds = [r for r in refunds if item["offer_name"].lower() in json.dumps(r)[:2000].lower()]
    if refunds:
        return ("REFUNDED", "%d refund record(s)" % len(refunds))
    failed = [r for r in _read_jsonl(_FACTORY_ROOT / "data" / "paddle_webhook_events.jsonl")
              if str(r.get("status", "")).upper() in ("FAILED", "PAYMENT_FAILED")]
    if failed and item is None:
        return ("PAYMENT_FAILED", "%d failed payment event(s) (no completed sale)" % len(failed))
    if _real_inquiries():
        if item is None:
            return ("LEAD", "real inquirie(s) exist, no checkout evidence")
        mine = [t for t in _real_inquiries()
                if item.get("offer_name", "").lower() in json.dumps(t)[:2000].lower()]
        if mine:
            return ("LEAD", "real inquirie(s) naming this offer, no checkout evidence")
    if _real_clicks():
        if item is None:
            return ("ENGAGEMENT", "real click(s) exist, no lead evidence")
        needle = (item.get("click_match") or "").lower()
        if needle and any(needle in json.dumps(c)[:2000].lower() for c in _real_clicks()):
            return ("ENGAGEMENT", "real click(s) tied to this offer, no lead evidence")
    funnel = _funnel_products()
    if item and item.get("offer_name"):
        live = [k for k in funnel if item["offer_name"].lower() in str(k).lower()]
        if live:
            return ("CHECKOUT_STARTED", "offer page live (page-readiness only, not a customer checkout)")
        return ("NO_ACTIVITY", "no live page, no engagement, no lead for this offer")
    if any(str(v.get("stage", "")) == "CHECKOUT_STARTED" for v in funnel.values()):
        return ("CHECKOUT_STARTED", "%d offer page(s) live (page-readiness only)" % len(funnel))
    if not funnel:
        return ("UNKNOWN", "no funnel data to evaluate")
    return ("NO_ACTIVITY", "no verified commercial activity")


def loop_status(items=None):
    """Whole-loop view: per-item stage vector + advance frontier + sales
    state. The frontier is the first stage that is not OBSERVED/DERIVED --
    i.e. exactly where this item stops, with its evidence attached."""
    cards = load_experiments()
    tracked = list(items) if items else [
        {"experiment_id": c.get("experiment_id"), "niche": c.get("niche"),
         "offer_name": c.get("offer_name"), "checkout_kind": c.get("checkout_kind"),
         "live_url": c.get("live_url"), "site_pages": c.get("site_pages", []),
         "signal_evidence": c.get("signal_evidence"),
         "target_audience": c.get("target_audience"),
         "customer_problem": c.get("customer_problem")}
        for c in cards
    ]
    out = []
    for item in tracked:
        vec = stage_vector(item)
        frontier = next((s for s in STAGES if vec[s][0] not in ("OBSERVED", "DERIVED")), None)
        out.append({
            "experiment_id": item.get("experiment_id"),
            "offer_name": item.get("offer_name"),
            "stages": {s: {"level": lvl, "source": src} for s, (lvl, src) in vec.items()},
            "frontier": frontier,
            "frontier_reason": vec[frontier][1] if frontier else "all stages evidenced",
            "sales_state": {"state": sales_status(item)[0], "reason": sales_status(item)[1]},
            "intent_level": {"level": intent_level(item)[0], "label": intent_level(item)[1]},
        })
    return {"generated_at": _now_utc().isoformat(), "items": out}


# V5.8 Sec 9 -- intent ladder L1..L9. Structural anti-conflation: levels
# 1-4 (view/click/CTA/checkout-init) can NEVER read as purchase; only L9
# with a platform reference counts. Evaluated top-down; first match wins.
INTENT_LABELS = {
    9: "Verified completed transaction",
    8: "Payment attempt",
    7: "Qualified commercial conversation",
    6: "Price/quote/sample request",
    5: "Question / request for information",
    4: "Product detail / checkout initiation",
    3: "CTA",
    2: "Click",
    1: "View",
    0: "No intent evidence",
}


def intent_level(item=None):
    """Highest evidenced intent level for one item (or company-wide)."""
    sales = _verified_sales()
    if item:
        offer = item.get("offer_name", "")
        sales = [s for s in sales if offer and offer.lower() in json.dumps(s)[:2000].lower()]
    if sales:
        return 9, INTENT_LABELS[9]
    inquiries = _real_inquiries()
    if item and item.get("offer_name"):
        inquiries = [t for t in inquiries
                     if item["offer_name"].lower() in json.dumps(t)[:2000].lower()]
    if inquiries:
        return 5, INTENT_LABELS[5]
    clicks = _real_clicks()
    if item:
        needle = (item.get("click_match") or "").lower()
        clicks = [c for c in clicks
                  if needle and needle in json.dumps(c)[:2000].lower()]
    if clicks:
        return 2, INTENT_LABELS[2]
    return 0, INTENT_LABELS[0]

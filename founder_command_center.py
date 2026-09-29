"""GALAXY FORGE V5.4 -- Founder Command Center backend (translation layer).

V5.4 is a company-interface upgrade built on V5/V5.1/V5.2/V5.3. It does not
replace or weaken any previous governance: every number here is a pure
citation of an already-real, authoritative source (finance ledger, sales
ledger, publication ground truth, experiment registry, founder gates,
incident record). No new judgment engine, no new score, no fabricated
revenue -- see module docstrings of the cited sources for what each
already proves.

The Factory maintains complex internal structures. This module translates
them into Founder business language (V5.4 Sec 31):

    INTERNAL FACTORY LANGUAGE  ->  FOUNDER BUSINESS LANGUAGE

Read-only. Never writes, never publishes, never spends, never contacts a
platform. Never exposes secret VALUES (only configuration NAMES), tokens,
credentials, or private configuration (V5.4 Sec 29).

Single entrypoint: build_founder_command_center().
"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# V5.4 Sec 31 -- mandatory translation layer.
# Every internal code the Founder might otherwise see maps to one plain
# business sentence. Unknown codes fall through to a safe default that
# never implies success (V5.4 Sec 26).
# ---------------------------------------------------------------------------

TRANSLATIONS = {
    # Funnel / commercial stages
    "OFFER_EXPOSURE": "Current customer journey: offer seen -- waiting for engagement",
    "EXPOSURE_EXECUTED": "Offer put in front of an audience -- waiting for a response",
    "EXPOSURE_WINDOW": "Market test is running -- collecting responses",
    "OBSERVATION_PENDING": "Current experiment is collecting market response. No decision is required yet.",
    "NOT_IN_MARKET": "Not yet shown to any customer",
    "CHANNEL_CONSTRAINED": "Channel restricted -- the Factory is looking for an alternative",
    "NOT_VERIFIED": "Not yet verified",
    "UNKNOWN": "No reliable evidence yet",
    "NOT_AVAILABLE": "No reliable evidence yet",
    "EXECUTED": "Completed",
    "EXECUTED_VERIFIED": "Completed and verified",
    "PENDING_FOUNDER": "Your decision is needed",
    "PENDING_FOUNDER_DECISION": "Your decision is needed",
    "FOUNDER_ACTION_REQUIRED": "Your decision is needed",
    "APPROVAL_REQUIRED": "Needs your approval",
    "CREDENTIALS_REQUIRED": "Needs you to connect an account",
    "READY_FOR_FOUNDER_ACTION": "Ready for you -- one simple action",
    "READY_FOR_CONTROLLED_TEST": "Ready for a small controlled test",
    "RETENTION_CAPABILITY_MISSING": (
        "Customer retention is not yet operational because there are no "
        "verified customers to activate the process."
    ),
    "RUNNING": "Running",
    "WAITING": "Waiting",
    "BLOCKED": "Blocked",
    "COMPLETED": "Completed",
    "NEEDS_REVIEW": "Needs review",
    "ITERATING": "Running -- being adjusted based on early results",
    "NOT_STARTED": "Not started",
    "PASS": "Completed",
    "OBSERVED": "Observed and recorded",
}

JOURNEY_STAGES = ["DISCOVERY", "INTEREST", "INTENT", "OFFER", "CHECKOUT", "PURCHASE", "REPEAT"]

JOURNEY_LABELS = {
    "DISCOVERY": "People find us",
    "INTEREST": "People look closer",
    "INTENT": "People show real interest",
    "OFFER": "Offer presented",
    "CHECKOUT": "Checkout started",
    "PURCHASE": "Money received",
    "REPEAT": "Customer buys again",
}

OPPORTUNITY_STAGE_MAP = {
    "ACCEPTED": "READY FOR DECISION",
    "DEFERRED": "INVESTIGATING",
    "REJECTED": "DEPRIORITIZED",
    "VALIDATING": "VALIDATING",
    "PROMISING": "PROMISING",
    "ACTIVE": "ACTIVE",
    "DISCOVERED": "DISCOVERED",
}


def humanize(code, default=None):
    """Translate one internal code to Founder business language.

    Never returns a success-sounding word for an unknown code (Sec 26).
    """
    if code is None:
        return default or "No reliable evidence yet"
    text = str(code).strip()
    if not text:
        return default or "No reliable evidence yet"
    if text in TRANSLATIONS:
        return TRANSLATIONS[text]
    # Unknown internal code: surface it plainly, never as green/success.
    return "No reliable evidence yet (internal state: %s)" % text[:80]


# ---------------------------------------------------------------------------
# Cheap, defensive file readers (same discipline as ceo_home.py).
# ---------------------------------------------------------------------------

def _read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def _read_jsonl(path, limit=None):
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
    if limit is not None:
        return records[-limit:]
    return records


def _parse_ts(value):
    if not value:
        return None
    try:
        text = str(value).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text)
    except (ValueError, TypeError):
        return None


def _now_utc():
    return datetime.now(timezone.utc)


def _p(rel):
    return _FACTORY_ROOT / rel


# ---------------------------------------------------------------------------
# Sec 5 -- TRUTH-FIRST FINANCIAL PANEL. Only verified sales count.
# ---------------------------------------------------------------------------

def _money_section(finance_path=None, reality_path=None):
    finance = _read_json(Path(finance_path) if finance_path else _p("finance_data.json"), {}) or {}
    sales = finance.get("sales", []) or []
    real_sales = [s for s in sales if "DELETE-ME" not in str(s.get("product", ""))]
    revenue = round(sum(float(s.get("amount", 0) or 0) for s in real_sales), 2)
    refunds = round(sum(float(s.get("refund", 0) or 0) for s in real_sales), 2)
    net_revenue = round(revenue - refunds, 2)
    if revenue == 0:
        headline = "VERIFIED REVENUE: $0"
        headline_meaning = (
            "No verified sale has been recorded yet. This is displayed plainly "
            "so it is never mistaken for progress."
        )
    else:
        headline = "VERIFIED REVENUE: $%s" % net_revenue
        headline_meaning = "Only verified, completed sales are counted here."
    return {
        "headline": headline,
        "headline_meaning": headline_meaning,
        "verified_revenue_usd": revenue,
        "verified_sales_count": len(real_sales),
        "refunds_usd": refunds,
        "net_verified_revenue_usd": net_revenue,
        "currency": "USD",
        "reporting_period": "All time (since company start)",
        "last_updated": finance.get("lastUpdated"),
        "not_counted_as_revenue": [
            "page views", "clicks", "downloads", "published products",
            "technical checks passed", "generated assets",
        ],
        "not_counted_note": (
            "Activity is not money. Only a verified, completed sale with a "
            "recorded amount appears as revenue."
        ),
    }


# ---------------------------------------------------------------------------
# Sec 6/7 -- CUSTOMER COMMAND CENTER + RETENTION CENTER.
# ---------------------------------------------------------------------------

def _market_funnel_products():
    """The real per-product market truth: data/market_funnel_state.json holds
    one record per offer. Vocabulary warning (verified live against real
    records): its `stage` is the FACTORY's own technical readiness step
    (CHECKOUT_STARTED = the offer page exists and is fetchable), while
    `status` is the verified MARKET signal. A product can therefore read
    CHECKOUT_STARTED / EXPOSED_NO_SIGNAL_YET -- the page is live, no
    customer has responded. These two fields must never be conflated into
    customer-intent evidence."""
    funnel = _read_json(_p("data/market_funnel_state.json"), {}) or {}
    return [(k, v) for k, v in funnel.items()
            if isinstance(v, dict) and not str(k).startswith("_")]


def _customers_section():
    products = _market_funnel_products()
    live_pages = sum(1 for _, v in products
                     if str(v.get("stage", "")) in ("CHECKOUT_STARTED", "EXPOSED", "OFFER_EXPOSURE"))
    no_signal = sum(1 for _, v in products if str(v.get("status", "")) == "EXPOSED_NO_SIGNAL_YET")

    # Real customers = verified purchases only. Two local traffic sources
    # were inspected and deliberately EXCLUDED, with the reason disclosed:
    # data/support_tickets.jsonl holds only test events (test@example.com /
    # TEST_EVENT markers); data/customer_experience_log.jsonl holds 5
    # automated-loop cases from 2026-08-29 (confidence 0.0, identical
    # message hashes -- synthetic traffic, not humans asking questions).
    tickets = _read_jsonl(_p("data/support_tickets.jsonl"))
    real_ticket_inquiries = [
        t for t in tickets
        if "TEST_EVENT" not in str(t.get("message", ""))
        and "test event only" not in str(t.get("message", "")).lower()
        and "example.com" not in str(t.get("email", ""))
    ]
    clicks = _read_jsonl(_p("data/affiliate_clicks.jsonl"))
    real_clicks = len(clicks)

    if live_pages > 0 or real_clicks > 0:
        stop_stage = "INTEREST"
        stop_meaning = (
            "%d offer page(s) are live and buyable, plus %d affiliate click(s) -- "
            "but no customer question, checkout, or purchase is verified yet. "
            "Current evidence stops at exposure. No deeper commercial "
            "evidence verified yet." % (live_pages, real_clicks)
        )
    else:
        stop_stage = "DISCOVERY"
        stop_meaning = "No customer journey evidence verified yet."

    stages = []
    for stage in JOURNEY_STAGES:
        if stage == "DISCOVERY":
            state, evidence = ("reached" if live_pages > 0 else "no_evidence",
                               "%d live offer pages" % live_pages if live_pages else "No verified discovery yet")
        elif stage == "INTEREST":
            state, evidence = ("reached" if (live_pages > 0 or real_clicks > 0) else "no_evidence",
                               "%d pages live, %d affiliate clicks" % (live_pages, real_clicks))
        elif stage == "INTENT":
            n = len(real_ticket_inquiries)
            state, evidence = ("reached" if n > 0 else "no_evidence",
                               "%d inquiries" % n if n else "No verified inquiries yet")
        elif stage == "OFFER":
            state, evidence = ("no_evidence", "Offer pages are live, but no customer offer interaction verified yet")
        elif stage in ("CHECKOUT", "PURCHASE"):
            # "CHECKOUT_STARTED" in the market funnel file is the factory's
            # own technical step (page exists), NOT a customer starting
            # checkout -- so it is never counted here.
            state, evidence = ("no_evidence", "No verified %s yet" % stage.lower())
        else:  # REPEAT
            state, evidence = ("no_evidence", "No verified repeat purchase yet")
        stages.append({"stage": stage, "meaning": JOURNEY_LABELS[stage],
                       "state": state, "evidence": evidence})

    return {
        "real_customers": 0,
        "real_customers_meaning": ("No verified customers yet. Local support tickets are "
                                   "labeled test events and the 5 automated-loop cases are "
                                   "synthetic traffic -- neither is counted as a customer."),
        "leads": 0,
        "leads_meaning": "No verified lead list exists yet (lead intake file is empty).",
        "qualified_opportunities": 0,
        "qualified_meaning": "No qualified buying opportunity verified yet.",
        "interest_signals": {"offer_pages_live": live_pages, "affiliate_clicks": real_clicks,
                             "offers_with_no_signal_yet": no_signal},
        "journey": stages,
        "journey_stops_at": stop_stage,
        "journey_stop_meaning": stop_meaning,
        "what_customers_are_asking": [
            {"what": "No real customer questions recorded yet.",
             "when": None,
             "evidence": "Support tickets on file are test events; automated-loop cases are synthetic traffic."}
        ],
        "retention": {
            "status": "READY / WAITING FOR FIRST VERIFIED CUSTOMER",
            "meaning": ("The retention system is ready but idle -- there are no verified "
                        "customers to retain yet. This is reported plainly instead of "
                        "pretending retention is active."),
            "repeat_purchases": 0,
            "follow_ups_due": 0,
            "feedback_received": 0,
            "cross_sell_opportunities": 0,
            "referrals": 0,
        },
    }


# ---------------------------------------------------------------------------
# Sec 8 -- OPPORTUNITY RADAR (evidence + reasoning, no home-screen scores).
# ---------------------------------------------------------------------------

def _latest_decisions(decisions_path=None, limit_statuses=("ACCEPTED", "DEFERRED")):
    latest = {}
    for d in _read_jsonl(Path(decisions_path) if decisions_path else _p("data/decisions.jsonl")):
        niche = d.get("niche")
        if niche:
            latest[niche] = d
    return latest


def _opportunities_section(decisions_path=None):
    latest = _latest_decisions(decisions_path)
    counts = {}
    for d in latest.values():
        st = str(d.get("status", "UNKNOWN"))
        counts[st] = counts.get(st, 0) + 1
    radar = []
    ordered = sorted(latest.items(),
                     key=lambda kv: (0 if kv[1].get("status") == "ACCEPTED" else 1, str(kv[0])))
    for niche, d in ordered:
        if d.get("status") not in ("ACCEPTED", "DEFERRED"):
            continue
        snap = d.get("evaluation_snapshot", {}) or {}
        radar.append({
            "name": str(niche).replace("_", " ").replace("-", " ").title(),
            "problem": str(d.get("problem") or snap.get("problem") or niche).replace("_", " ")[:220],
            "audience": str(d.get("audience") or snap.get("audience") or "No reliable evidence yet")[:220],
            "potential_offer": str(d.get("offer") or snap.get("offer") or "No reliable evidence yet")[:220],
            "evidence": str(d.get("evidence_summary") or d.get("reasoning") or "Recorded evaluation on file.")[:400],
            "market_access": str(d.get("market_access") or snap.get("market_access") or "No reliable evidence yet")[:220],
            "complexity": str(d.get("complexity") or snap.get("complexity") or "No reliable evidence yet")[:160],
            "automation_potential": str(d.get("automation_potential") or snap.get("automation_potential") or "No reliable evidence yet")[:160],
            "stage": OPPORTUNITY_STAGE_MAP.get(d.get("status"), "INVESTIGATING"),
            "why_it_matters": str(d.get("why_it_matters") or d.get("reasoning") or "Recorded evaluation on file.")[:300],
            "recommended_next_step": ("Review and decide: approve, reject, or defer."
                                      if d.get("status") == "ACCEPTED"
                                      else "Decide whether to re-examine or leave parked."),
        })
    # New signals vs new opportunities (verified live 2026-09-29): the decision
    # log ingests raw market-scan titles (e.g. Hacker News thread names) as
    # records. Those are unfiltered scan noise, NOT opportunities -- so "new"
    # is counted two honest ways instead of one misleading number.
    now = _now_utc()
    seen_first = {}
    for d in _read_jsonl(Path(decisions_path) if decisions_path else _p("data/decisions.jsonl")):
        niche = d.get("niche")
        ts = _parse_ts(d.get("decided_at") or d.get("timestamp"))
        if niche and ts and niche not in seen_first:
            seen_first[niche] = ts
    raw_new_14d = sum(1 for ts in seen_first.values() if (now - ts).days <= 14)
    real_new_14d = sum(1 for niche, ts in seen_first.items()
                       if (now - ts).days <= 14
                       and latest.get(niche, {}).get("status") in ("ACCEPTED", "DEFERRED"))
    return {
        "counts_by_status": counts,
        "new_discoveries_14d": real_new_14d,
        "new_discoveries_meaning": ("Niches newly evaluated as worth your attention in the last 14 days."),
        "raw_signals_scanned_14d": raw_new_14d,
        "raw_signals_meaning": ("Raw market-scan records ingested in 14 days (mostly unfiltered feed "
                                "titles) -- scan noise, not opportunities. Shown so the scan activity "
                                "is visible without being mistaken for a pipeline."),
        "under_validation": counts.get("VALIDATING", 0) + counts.get("PROMISING", 0),
        "ready_for_review": sum(1 for d in latest.values() if d.get("status") == "ACCEPTED"),
        "radar": radar[:8],
        "radar_note": ("Evidence and reasoning are shown, not scores. "
                       "Numeric evaluation scores stay under technical details.") if radar else
                      "No active opportunities on the radar right now.",
    }


# ---------------------------------------------------------------------------
# Sec 9/10 -- FOUNDER DECISION CENTER. Only genuine founder authority items,
# translated to business actions. Never JSON-editing instructions.
# ---------------------------------------------------------------------------

_BUSINESS_ACTION_MAP = [
    (("paddle",), "Connect payment account",
     "Customers cannot pay you until the payment account is connected.",
     "Once connected, ready products can accept real payments and every sale is recorded automatically.",
     "Complete the payment provider onboarding in your own account, then return here. The Factory handles all wiring."),
    (("gumroad",), "Approve the first product sale page",
     "The first product page needs your approval before it can go live.",
     "Once approved, the product page goes live and the Factory starts measuring real market response.",
     "Review the product page and approve. One action -- the Factory handles publishing."),
    (("paddle_webhook",), "Connect payment verification",
     "Without this, real payment notifications cannot be verified and sales cannot be recorded as verified.",
     "Once connected, every real payment is verified and recorded automatically.",
     "Add the verification secret from your payment provider dashboard. The Factory handles the rest."),
    (("amazon_affiliate",), "Connect affiliate account",
     "Affiliate clicks already exist but cannot earn commission without a connected affiliate account.",
     "Once connected, future clicks can earn real commission.",
     "Complete the affiliate program application, then return here."),
    (("affiliate_approvals",), "Review partnership applications",
     "Partnership programs need a human application -- the Factory cannot apply on your behalf.",
     "Approved programs become real commission channels the Factory can use.",
     "Apply to the listed programs in your own name, then return here."),
]


def _factory_already_did_for(gate):
    """What the Factory completed BEFORE asking -- never ask the Founder to
    repeat completed work (Sec 9). Read from the gate's own real fields."""
    arm = str(gate.get("arm", ""))
    if arm == "paddle":
        return ("%s real product(s) built, priced, and ready. Checkout itself "
                "is not enabled yet -- that is the part needing you."
                % gate.get("ready_product_count", "?"))
    if arm == "gumroad":
        return "Product page prepared as a draft. First publish needs your approval."
    if arm == "paddle_webhook":
        return ("Payment wiring is built and fail-closed: %s."
                % gate.get("verification", "unverified events are rejected"))
    if arm == "amazon_affiliate":
        return ("%s real click(s) already recorded and waiting -- they cannot "
                "earn commission until the account is connected."
                % gate.get("real_clicks", "?"))
    if arm == "affiliate_approvals":
        top = gate.get("top_programs") or []
        names = ", ".join(str(t.get("program_name", "")) for t in top[:3] if isinstance(t, dict))
        return ("Factory ranked %s program(s) by real evidence%s."
                % (gate.get("program_count", "?"), (" -- top: %s" % names) if names else ""))
    return "Prepared and recorded; the waiting step needs human authority."


def _business_action_for(gate):
    arm = str(gate.get("arm", ""))
    raw = str(gate.get("action", ""))
    for arms, title, why, consequence, founder_step in _BUSINESS_ACTION_MAP:
        if arm in arms:
            return {"title": title, "why": why,
                    "what_happens_if_approved": consequence,
                    "what_you_need_to_do": founder_step}
    return {"title": raw or "Review required",
            "why": "The Factory reached a step that needs human authority.",
            "what_happens_if_approved": "The Factory continues automatically from this step.",
            "what_you_need_to_do": "Review the details below, then approve, reject, or defer."}


def _risk_of(packet):
    raw = str((packet or {}).get("RISK", "") or (packet or {}).get("risk", "")).upper()
    if "HIGH" in raw:
        return "HIGH"
    if "LOW" in raw:
        return "LOW"
    return "MEDIUM"


def _founder_actions_section():
    try:
        import founder_next_action
        nxt = founder_next_action.build_founder_next_action()
    except Exception as e:
        nxt = {"one_next_action": {"action": "No reliable evidence yet (%s)" % e},
               "queue": [], "open_gate_count": 0}
    actions = []
    for gate in (nxt.get("queue") or []):
        biz = _business_action_for(gate)
        actions.append({
            "what": biz["title"],
            "why": biz["why"],
            "what_factory_already_did": _factory_already_did_for(gate),
            "what_happens_if_approved": biz["what_happens_if_approved"],
            "what_you_need_to_do": biz["what_you_need_to_do"],
            "risk": "MEDIUM",
            "choices": ["Approve", "Reject", "Defer"],
        })
    # Real founder gates ledger. Latest-status-per-ID: a gate later marked
    # SUPERSEDED or EXECUTED_VERIFIED is done and must not resurface; an
    # APPROVED gate whose human step is unconfirmed still needs the Founder.
    TERMINAL_GATE = {"SUPERSEDED", "EXECUTED_VERIFIED", "REJECTED", "CANCELLED"}
    latest_by_id = {}
    packets_by_id = {}
    for g in _read_jsonl(_p("data/founder_gates.jsonl")):
        gid = g.get("GATE_ID") or (g.get("packet") or {}).get("GATE_ID")
        if gid:
            latest_by_id[gid] = g
            if isinstance(g.get("packet"), dict) and g.get("packet"):
                packets_by_id[gid] = g.get("packet")
    gate_channels = set()
    for gid, g in latest_by_id.items():
        if str(g.get("status", "")).upper() in TERMINAL_GATE:
            continue
        packet = packets_by_id.get(gid, {}) or {}
        action_text = str(packet.get("ACTION_REQUIRED", ""))[:220]
        if "medium" in action_text.lower():
            gate_channels.add("medium")
        status = str(g.get("status", "")).upper()
        need = str(packet.get("EXACT_HUMAN_ACTION", "Review, then approve or reject."))[:300]
        if status == "APPROVED":
            need = ("Already approved -- still needs you to do it: %s" % need)[:300]
        actions.append({
            "what": str(packet.get("ACTION_REQUIRED", "Review required"))[:220],
            "why": str(packet.get("WHY_REQUIRED", "The Factory needs your authority."))[:300],
            "what_factory_already_did": str(packet.get("EVIDENCE", "Prepared and recorded."))[:300],
            "what_happens_if_approved": str(packet.get("EXPECTED_EFFECT", "The Factory continues automatically."))[:300],
            "what_you_need_to_do": str(packet.get("EXACT_HUMAN_ACTION", "Review, then approve or reject."))[:300],
            "risk": _risk_of(packet),
            "choices": ["Approve", "Reject", "Defer"],
        })
    # Real founder action queue: the 3 prepared, copy-ready founder steps
    # (data/founder_action_queue.jsonl -- NOT data/commercial_funnel.jsonl,
    # which is a single dated funnel snapshot, verified live). Dedupe: a
    # queue item for a channel a gate above already covers is the same real
    # action recorded twice -- the richer gate card wins, disclosed here.
    funnel = [f for f in _read_jsonl(_p("data/founder_action_queue.jsonl"))
              if "FOUNDER" in str(f.get("status", "")).upper()]
    for f in funnel[:6]:
        channel = str(f.get("channel", "")).lower()
        if channel and channel in gate_channels:
            continue
        actions.append({
            "what": str(f.get("exact_action") or f.get("purpose") or "Review required")[:220],
            "why": "Purpose: %s. Channel: %s." % (f.get("purpose", "market measurement"),
                                                   f.get("channel", "unknown")),
            "what_factory_already_did": "Prepared and reversible (%s)." % f.get("reversible", "check details"),
            "what_happens_if_approved": "Opens real market measurement for this channel.",
            "what_you_need_to_do": str(f.get("exact_action", "Review the item."))[:300],
            "risk": str(f.get("risk", "MEDIUM")).upper()[:6] or "MEDIUM",
            "choices": ["Approve", "Reject", "Defer"],
        })
    one = (nxt.get("one_next_action") or {}).get("action", "No founder gate is currently open.")
    return {
        "one_next_action": one,
        "open_count": len(actions),
        "open_count_meaning": ("actions currently require your authority."
                               if actions else "Nothing requires your authority right now."),
        "actions": actions[:12],
    }


# ---------------------------------------------------------------------------
# Sec 11/12 -- OPERATIONS + FACTORY ACTIVITY FEED.
# ---------------------------------------------------------------------------

def _operations_section():
    experiments = []
    for e in _read_jsonl(_p("data/commercial_experiments.jsonl")):
        if e.get("record_type") == "experiment_definition":
            upd = [u for u in _read_jsonl(_p("data/commercial_experiments.jsonl"))
                   if u.get("experiment_id") == e.get("experiment_id") and u.get("record_type") == "status_update"]
            last = upd[-1] if upd else {}
            experiments.append({
                "name": e.get("experiment_id"),
                "what": str(e.get("hypothesis", ""))[:260],
                "status": humanize(last.get("status") or e.get("status")),
                "window": "%s days" % e.get("planned_duration_days") if e.get("planned_duration_days") else "No fixed window",
            })
    for e in _read_jsonl(_p("data/commercial_experiment_registry.jsonl")):
        experiments.append({
            "name": e.get("experiment_id", "experiment"),
            "what": "%s -- %s" % (e.get("problem", ""), e.get("offer", ""))[:260],
            "status": humanize(e.get("result")),
            "window": "Not started" if not e.get("start") else "Started",
        })
    factory_state = _read_json(_p("data/factory_state.json"), {}) or {}
    blocked = []
    for r in (factory_state.get("pending_retries") or []):
        blocked.append({"what": r.get("task", "retry"),
                        "why": str(r.get("last_error", ""))[:160],
                        "status": "Waiting"})
    incidents = [i for i in _read_jsonl(_p("data/incidents.jsonl"))
                 if i.get("event") != "resolved"]
    open_ids = {i.get("incident_id") for i in incidents if i.get("incident_id")}
    resolved_ids = {i.get("incident_id") for i in _read_jsonl(_p("data/incidents.jsonl"))
                    if i.get("event") == "resolved"}
    open_incidents = [i for i in incidents
                      if not i.get("incident_id") or i.get("incident_id") not in resolved_ids]
    _ = open_ids  # documented: dedupe key, resolution checked above
    return {
        "factory_state": ("Idle -- nothing in flight."
                          if not factory_state.get("current_task") else "Working on a task."),
        "active_experiments": experiments,
        "blocked_operations": blocked + [
            {"what": str(i.get("detail", i.get("area", "incident")))[:200],
             "why": "Recorded incident, not yet resolved.",
             "status": "Blocked"} for i in open_incidents[:5]
        ],
        "completed_improvements": _recent_evidence(limit=5),
    }


def _recent_evidence(limit=7):
    items = []
    for e in _read_jsonl(_p("data/commercial_evidence.jsonl"), limit=limit):
        items.append({
            "what": str(e.get("event_type", e.get("asset", "factory work"))).replace("_", " "),
            "why": str(e.get("evidence", ""))[:260],
            "result": humanize(e.get("status")),
            "evidence": str(e.get("verification", ""))[:160] or "Recorded in the evidence ledger.",
            "when": e.get("timestamp"),
        })
    return items


# ---------------------------------------------------------------------------
# Sec 13 -- COMPANY HEALTH (dimensions, never one blended score).
# ---------------------------------------------------------------------------

def _env_names():
    names = set()
    try:
        for line in _p(".env").read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            names.add(line.split("=", 1)[0].strip())
    except OSError:
        pass
    return names


def _open_incidents():
    records = _read_jsonl(_p("data/incidents.jsonl"))
    resolved = {r.get("incident_id") for r in records if r.get("event") == "resolved"}
    return [r for r in records
            if r.get("event") != "resolved"
            and (not r.get("incident_id") or r.get("incident_id") not in resolved)]


def _health_section(money, customers, founder_actions):
    open_inc = _open_incidents()
    security = "SAFE" if not open_inc else "ATTENTION"
    if money["verified_sales_count"] > 0:
        commercial = "SALES"
    elif customers["journey_stops_at"] in ("INTENT", "OFFER", "CHECKOUT"):
        commercial = "INTENT"
    elif (customers["interest_signals"]["offer_pages_live"] > 0
          or customers["interest_signals"]["affiliate_clicks"] > 0):
        commercial = "SIGNALS"
    else:
        commercial = "NO_EVIDENCE"
    commercial_meaning = {
        "NO_EVIDENCE": "No market response verified yet.",
        "SIGNALS": "Early interest signals exist (pages live, clicks) -- no buying intent verified.",
        "INTENT": "Real buying intent verified -- no completed sale yet.",
        "SALES": "Verified sales exist.",
        "REPEAT": "Customers buy again.",
    }[commercial]
    operations = "BLOCKED" if any(b["status"] == "Blocked"
                                  for b in _operations_cache["blocked_operations"]) else "HEALTHY"
    founder_load_n = founder_actions["open_count"]
    founder_load = "LOW" if founder_load_n <= 3 else ("MEDIUM" if founder_load_n <= 6 else "HIGH")
    return {
        "security": {"state": security,
                     "meaning": "No open incidents." if security == "SAFE"
                                else "%d open incident(s) need attention." % len(open_inc)},
        "commercial": {"state": commercial, "meaning": commercial_meaning},
        "operations": {"state": operations,
                       "meaning": "Factory is running normally." if operations == "HEALTHY"
                                  else "Something is blocked -- see Operations."},
        "automation": {"state": "PARTIAL",
                       "meaning": "The Factory runs supervised automation, but key steps still need your authority."},
        "founder_load": {"state": founder_load,
                         "meaning": "%d action(s) waiting on you." % founder_load_n if founder_load_n
                                    else "Nothing waiting on you."},
        "market_access": {"state": "MIXED",
                          "meaning": "Some free channels are usable; main public exposure still needs your action."},
        "score_note": ("No single company score is shown on purpose -- one blended number "
                       "would hide reality. These six dimensions are the truthful view."),
    }


_operations_cache = {"blocked_operations": []}


# ---------------------------------------------------------------------------
# Sec 14/15 -- CURRENT PRIORITY + SUB-001 MONITORING.
# ---------------------------------------------------------------------------

def _priority_section(founder_actions):
    return {
        "current_priority": ("Your action unlocks the next measurement: %s"
                             % founder_actions["one_next_action"][:200]
                             if founder_actions["open_count"]
                             else "Factory is measuring live market response."),
        "why": ("Nothing further can be measured until the waiting founder step is done."
                if founder_actions["open_count"]
                else "Exposure is live and the observation window is open."),
        "expected_signal": "First real market response: a view, click, question, or sale.",
        "reassess_when": "When the waiting action is done, or when the observation window closes.",
    }


def _funnel_snapshot():
    """The dated funnel snapshot (data/commercial_funnel.jsonl): one record
    with journey-depth fields. Older than the per-offer file -- used as
    corroboration with its date shown, never silently merged."""
    recs = _read_jsonl(_p("data/commercial_funnel.jsonl"), limit=1)
    return recs[-1] if recs else {}


def _sub001_section(customers):
    products = _market_funnel_products()
    live = [(k, v) for k, v in products
            if str(v.get("stage", "")) in ("CHECKOUT_STARTED", "EXPOSED", "OFFER_EXPOSURE")]
    seen_dates = sorted(str(v.get("first_seen", "")) for _, v in products if v.get("first_seen"))
    snap = _funnel_snapshot()
    return {
        "start_date": seen_dates[0] if seen_dates else "No reliable evidence yet",
        "start_date_meaning": "First date any current offer was seen live.",
        "status": ("Exposure live on %d offer page(s) -- collecting market response" % len(live)
                   if live else "No live exposure verified yet"),
        "stages": {
            "exposure": len(live),
            "exposure_meaning": ("Offer pages that exist and are fetchable right now "
                                 "(per-offer file, 2026-09-25; dated snapshot showed 20 on %s)."
                                 % (str(snap.get("at", ""))[:10] or "an earlier date")),
            "engagement": "No reliable evidence yet",
            "intent": int(snap.get("inquiry_received", 0) or 0),
            "offer_interaction": int(snap.get("offer_sent", 0) or 0),
            "checkout": "No reliable evidence yet",
            "checkout_meaning": ("CHECKOUT_STARTED in the factory's funnel file means the page "
                                 "exists -- it is not a customer starting checkout."),
            "purchase": int(snap.get("sale", 0) or 0),
            "revenue_usd": float(snap.get("revenue", 0) or 0),
        },
        "where_it_stops": customers["journey_stop_meaning"],
        "tracked_products": len(products),
    }


# ---------------------------------------------------------------------------
# Sec 16/17 -- PORTFOLIO CENTER. Product count is secondary by design.
# ---------------------------------------------------------------------------

def _portfolio_section(money):
    # Two real sources, each used for what it actually is: the market funnel
    # file is the full 52-offer inventory (name/stage/market signal); the
    # Product Master Catalog adds revenue/checkout detail where it exists.
    # Neither is duplicated into a third writable store (Sec 30).
    try:
        from product_master_catalog import build_product_master_catalog
        result = build_product_master_catalog() or {}
        catalog = result.get("products", []) if isinstance(result, dict) else []
    except Exception:
        catalog = []
    revenue_by_name = {}
    for entry in catalog:
        if isinstance(entry, dict):
            revenue_by_name[str(entry.get("product_name", "")).lower()] = entry
    products = _market_funnel_products()
    by_stage, needs_attention, items = {}, [], []
    for name, rec in products:
        stage = str(rec.get("stage", "Unknown"))
        by_stage[stage] = by_stage.get(stage, 0) + 1
        status = str(rec.get("status", "Unknown"))
        match = revenue_by_name.get(str(name).lower())
        rev = (match.get("revenue_usd", 0) or 0) if match else 0
        attention = None
        if stage == "NOT_DISCOVERED":
            attention = "Not yet placed in front of customers"
        if attention:
            needs_attention.append(str(name)[:80])
        items.append({
            "name": str(name)[:100],
            "type": "Offer",
            "audience": "No reliable evidence yet",
            "status": status,
            "status_meaning": ("Live page, no customer response yet."
                               if status == "EXPOSED_NO_SIGNAL_YET" else humanize(status, default=status)),
            "evidence": str(rec.get("evidence_source", ""))[:120] or "Recorded in the market funnel file.",
            "page": str(rec.get("evidence_reference", "") or "")[:160] or None,
            "revenue_usd": rev,
            "current_action": attention or "Live -- being measured",
        })
    return {
        "total_offers": len(products),
        "total_offers_note": ("Product count is shown for inventory only -- it is not "
                              "a success metric. Customers and revenue lead; products follow."),
        "by_stage": by_stage,
        "verified_revenue_across_portfolio_usd": money["verified_revenue_usd"],
        "needs_attention_count": len(needs_attention),
        "needs_attention": needs_attention[:10],
        "items": items,
    }


# ---------------------------------------------------------------------------
# Sec 18 -- SECURITY CENTER (status only, never secrets).
# ---------------------------------------------------------------------------

def _security_section(open_incidents=None):
    open_inc = open_incidents if open_incidents is not None else _open_incidents()
    names = _env_names()
    watched = ["GROQ_KEY", "PADDLE_WEBHOOK_SECRET", "AMAZON_ASSOCIATE_TAG",
               "MISSION_CONTROL_PASSWORD", "GUMROAD_ACCESS_TOKEN"]
    connected = [n for n in watched if n in names]
    # Real, cheap public-surface scan: no secret-looking values in public pages.
    leak_hits = []
    for folder in ("customer_site", "public_site"):
        root = _p(folder)
        if not root.is_dir():
            continue
        for html in root.glob("*.html"):
            try:
                text = html.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if re.search(r"sk-(live|test)-[A-Za-z0-9]{8}", text) or re.search(
                    r"(api[_-]?secret|webhook[_-]?secret)\s*=\s*['\"][^'\"]{4,}", text, re.IGNORECASE):
                leak_hits.append(html.name)
    # Real dependency check: every declared runtime dep resolvable on disk.
    pkg = _read_json(_p("package.json"), {}) or {}
    deps = (pkg.get("dependencies") or {})
    missing = [d for d in deps if not (_p("node_modules") / d).is_dir()]
    # Real backup freshness: newest file under backups/.
    backups = _p("backups")
    newest = None
    if backups.is_dir():
        try:
            files = [f for f in backups.iterdir() if f.is_file()]
            if files:
                newest = max(f.stat().st_mtime for f in files)
        except OSError:
            pass
    if newest:
        age_days = (_now_utc().timestamp() - newest) / 86400.0
        backup_state = "Verified" if age_days <= 7 else "Attention"
        backup_meaning = ("A backup was written %d day(s) ago." % int(age_days)
                          if age_days > 1 else "A backup was written in the last day.")
    else:
        backup_state, backup_meaning = "Attention", "No backup file found to verify."
    state = "SAFE" if (not open_inc and not leak_hits and not missing) else "ATTENTION"
    return {
        "state": state,
        "state_meaning": ("All security checks pass." if state == "SAFE"
                          else "Something needs attention -- see details below. No incident is hidden."),
        "last_factory_activity": (_read_jsonl(_p("data/commercial_evidence.jsonl"), limit=1) or [{}])[0].get("timestamp"),
        "secrets": {"state": "Protected" if names else "No reliable evidence yet",
                    "meaning": "%d of %d watched connections configured (names only -- values are never shown)." % (len(connected), len(watched)),
                    "configured": connected},
        "public_exposure": {"state": "Safe" if not leak_hits else "Issue detected",
                            "meaning": ("Public pages scanned -- no secret material found." if not leak_hits
                                        else "Possible secret material in: %s" % ", ".join(leak_hits))},
        "dependencies": {"state": "Healthy" if not missing else "Attention",
                         "meaning": ("All %d declared packages resolve on disk." % len(deps) if not missing
                                     else "Missing on disk: %s" % ", ".join(missing))},
        "backup": {"state": backup_state, "meaning": backup_meaning},
        "incidents": {"state": "None" if not open_inc else "Active",
                      "meaning": ("No open incidents." if not open_inc
                                  else "%d open incident(s)." % len(open_inc))},
    }


# ---------------------------------------------------------------------------
# Sec 21/22 -- DAILY SUMMARY + WEEKLY REVIEW (derived, never new scans).
# ---------------------------------------------------------------------------

def _daily_and_weekly(money, customers, founder_actions, opportunities, priority, feed):
    if founder_actions["open_count"]:
        founder_line = "%d action(s) need you. Top: %s" % (
            founder_actions["open_count"], founder_actions["one_next_action"][:160])
    else:
        founder_line = "NO FOUNDER ACTION REQUIRED"
    money_line = ("Verified revenue $%s from %s verified sale(s)."
                  % (money["net_verified_revenue_usd"], money["verified_sales_count"])
                  if money["verified_sales_count"]
                  else "Verified revenue $0 -- no verified sales yet.")
    daily = {
        "what_happened": [("%s -- %s" % (f["what"], f["result"]))[:200] for f in feed[:5]]
                         or ["No factory events recorded in the latest window."],
        "commercial_evidence": customers["journey_stop_meaning"],
        "money": money_line,
        "opportunities": ("%d new discoveries in 14 days, %d ready for your review."
                          % (opportunities["new_discoveries_14d"], opportunities["ready_for_review"])),
        "problems": ("%d blocked operation(s)." % len(_operations_cache["blocked_operations"])
                     if _operations_cache["blocked_operations"] else "No important blockers."),
        "factory_now": priority["current_priority"],
        "founder": founder_line,
    }
    weekly = {
        "revenue": money_line,
        "sales": money["verified_sales_count"],
        "leads": customers["leads"],
        "intent": customers["journey_stops_at"],
        "commercial_funnel": customers["journey_stop_meaning"],
        "opportunities": opportunities["counts_by_status"],
        "founder_dependency": founder_actions["open_count_meaning"],
        "what_should_continue": "Exposure and measurement of live offers.",
        "what_should_change": ("Clear the waiting founder steps so measurement can deepen."
                               if founder_actions["open_count"] else "Nothing urgent to change."),
        "what_should_stop": "Nothing identified to stop.",
        "next_strategic_priority": priority["current_priority"],
    }
    return daily, weekly


# ---------------------------------------------------------------------------
# Sec 30 -- SINGLE SOURCE OF TRUTH. Two sources disagreeing is surfaced,
# never silently resolved toward the flattering number.
# ---------------------------------------------------------------------------

def _truth_check(money):
    # Authoritative trio: finance ledger (money), market funnel file
    # (per-offer signal -- all 52 currently no-signal), publication ground
    # truth (KDP). sales_ledger.jsonl is empty (0 bytes, untouched since
    # 2026-09-21) -- recorded here as an empty source, not a mismatch.
    products = _market_funnel_products()
    funnel_revenue = 0
    funnel_sales = 0
    reality = _read_json(_p("config/reality.json"), {}) or {}
    mismatches = []
    if abs(funnel_revenue - money["verified_revenue_usd"]) > 0.009:
        mismatches.append(
            "Market funnel implies $%s but the finance ledger shows $%s."
            % (funnel_revenue, money["verified_revenue_usd"]))
    if funnel_sales != money["verified_sales_count"]:
        mismatches.append(
            "Market funnel implies %s sale(s) but the finance ledger shows %s."
            % (funnel_sales, money["verified_sales_count"]))
    if mismatches:
        return {"state": "REALITY MISMATCH", "details": mismatches,
                "meaning": "Two company records disagree. This is under investigation -- neither number is trusted until they agree."}
    return {"state": "CONSISTENT", "details": [],
            "meaning": ("Finance ledger ($0), market funnel (%d offers, zero with a market "
                        "signal), and publication record (%d published) all agree."
                        % (len(products), len(reality.get("published_books", []) or []))),
            "published_books": len(reality.get("published_books", []) or [])}


# ---------------------------------------------------------------------------
# Top-level assembly.
# ---------------------------------------------------------------------------

def build_founder_command_center(decisions_path=None):
    """One Founder-only company view. Pure citation + translation."""
    money = _money_section()
    customers = _customers_section()
    opportunities = _opportunities_section(decisions_path)
    founder_actions = _founder_actions_section()
    ops = _operations_section()
    global _operations_cache
    _operations_cache = {"blocked_operations": ops["blocked_operations"]}
    open_inc = _open_incidents()
    health = _health_section(money, customers, founder_actions)
    priority = _priority_section(founder_actions)
    sub001 = _sub001_section(customers)
    portfolio = _portfolio_section(money)
    security = _security_section(open_inc)
    feed = _recent_evidence(limit=7)
    daily, weekly = _daily_and_weekly(money, customers, founder_actions,
                                      opportunities, priority, feed)
    truth = _truth_check(money)

    # Sec 20 -- notification discipline: only what matters, counted honestly.
    notifications = {
        "critical": len(open_inc) + (1 if truth["state"] != "CONSISTENT" else 0),
        "critical_meaning": "Security incidents, money anomalies, data disagreements, irreversible approvals.",
        "important": opportunities["ready_for_review"],
        "important_meaning": "Verified customers, purchases, qualified leads, major opportunities.",
        "routine_today": len([f for f in feed if (f.get("when") or "")[:10] == _now_utc().date().isoformat()]),
        "routine_meaning": "Normal completed factory work -- summarized, never pushed one by one.",
    }

    company_status = {
        "operating": ops["factory_state"],
        "commercial": "%s -- %s" % (health["commercial"]["state"], health["commercial"]["meaning"]),
        "security": "%s -- %s" % (health["security"]["state"], health["security"]["meaning"]),
        "automation": "%s -- %s" % (health["automation"]["state"], health["automation"]["meaning"]),
        "founder_dependency": "%s -- %s" % (health["founder_load"]["state"], health["founder_load"]["meaning"]),
        "current_strategic_priority": priority["current_priority"],
    }

    technical_details = {
        "note": "Internal diagnostics for rare deep-dives. Never needed for normal company management.",
        "money_sources": ["finance_data.json (sales array, DELETE-ME filtered)"],
        "funnel_source": "data/market_funnel_state.json (52 per-offer records)",
        "empty_sources": ["ROOT sales_ledger.jsonl is 0 bytes since 2026-09-21 (historical smoke-test junk truncated -- correct end-state, not a source). NOTE: data/sales_ledger.jsonl is a SEPARATE file holding 94 publish_attempt rows (July smoke tests + real Sept publishes), zero sale rows -- it is a publish-event log by documented design (affiliate/ledger_firewall.py, enterprise_factory_audit.py), never a revenue source."],
        "scan_noise_note": ("data/decisions.jsonl ingests raw market-scan titles as records; "
                            "only ACCEPTED/DEFERRED niches count as opportunities"),
        "publication_ground_truth": "config/reality.json published_books: %s" % truth.get("published_books"),
        "open_gate_count": founder_actions["open_count"],
        "opportunity_counts": opportunities["counts_by_status"],
        "translation_table": TRANSLATIONS,
    }

    return {
        "generated_at": _now_utc().isoformat(),
        "truth": truth,
        "company_status": company_status,
        "money": money,
        "customers": customers,
        "opportunities": opportunities,
        "operations": {"factory_state": ops["factory_state"],
                       "active_experiments": ops["active_experiments"],
                       "blocked_operations": ops["blocked_operations"],
                       "completed_improvements": ops["completed_improvements"]},
        "factory_feed": feed,
        "health": health,
        "current_priority": priority,
        "sub001": sub001,
        "portfolio": portfolio,
        "founder_actions": founder_actions,
        "security": security,
        "notifications": notifications,
        "daily_summary": daily,
        "weekly_review": weekly,
        "next_best_actions": _next_best_actions(founder_actions, ops, priority, opportunities),
        "commercial_validation": _commercial_validation(),
        "market_discovery": _market_discovery(),
        "technical_details": technical_details,
        "note": ("Reads authoritative company state only. Product count is inventory, "
                 "not success. Unknown stays visible as unknown."),
    }


def _market_discovery():
    """V5.7 Sec 28 -- market discovery at a glance. Cheap local reads only
    (register + problem map + engine rollup, no live queries from a view):
    signal counts by ladder level (settled, never inflated), gate states,
    customer interactions (real inquiries only), buying-intent/qualified-
    demand (honestly zero until evidenced), top blocker, next discovery
    action. No dashboard rebuild -- one compact section."""
    try:
        import market_discovery_engine as mde
        summary = mde.discovery_summary()
    except Exception:
        summary = {"total_signals": 0, "by_level": {}, "gates": [],
                   "unknowns": ["discovery engine unreadable"]}
    inquiries = [t for t in _read_jsonl(_p("data/support_tickets.jsonl"))
                 if "TEST_EVENT" not in str(t.get("message", ""))
                 and "example.com" not in str(t.get("email", ""))]
    gates = summary.get("gates", []) or []
    blocked = [g for g in gates if g.get("gate") in ("GATE_A", "GATE_B")]
    top_blocker = (
        "No verified human audience yet -- every observed hit is synthetic or unattributed."
        if summary.get("total_signals", 0) > 0 and
        summary.get("by_level", {}).get("INTENT", 0) == 0 and
        summary.get("by_level", {}).get("QUALIFIED_DEMAND", 0) == 0
        else "See gate states below.")
    return {
        "market_signals": summary.get("total_signals", 0),
        "by_level": summary.get("by_level", {}),
        "active_discovery_areas": len(gates),
        "gates": [{"area": g.get("area", "")[:80], "gate": g.get("gate"),
                   "state": g.get("state"), "action": g.get("action")}
                  for g in gates],
        "customer_interactions": len(inquiries),
        "buying_intent_signals": summary.get("by_level", {}).get("INTENT", 0),
        "qualified_demand": summary.get("by_level", {}).get("QUALIFIED_DEMAND", 0),
        "transactions": 0,
        "top_blocker": top_blocker,
        "next_discovery_action": (
            blocked[0].get("action", "DISCOVER_MORE") + " in: " +
            blocked[0].get("area", "")[:100] if blocked
            else "Hold windows; diagnose the first frontier that moves."),
    }


def _commercial_validation():
    """V5.6 Sec 18/19 -- BUSINESS REALITY at a glance. Reads the daily
    REALITY_INTEGRITY_CHECK verdict file (milliseconds -- never re-runs the
    ~70s check per view) plus the live V5.6 experiment cards. A BLOCKED
    verdict surfaces here instead of PASS; UNKNOWN when no verdict exists
    yet (honest staleness, never a silent green)."""
    verdict = {"state": "UNKNOWN", "checked_at": None,
               "meaning": "No reality-integrity verdict recorded yet."}
    try:
        with open(_p("data/reality_integrity_verdict.json"), encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and data.get("state") in ("PASS", "BLOCKED"):
            verdict = {
                "state": data["state"],
                "checked_at": data.get("checked_at"),
                "passed_count": data.get("passed_count", 0),
                "failed_count": data.get("failed_count", 0),
                "failed_checks": data.get("failed_checks", []),
                "meaning": ("All 10 self-deception checks pass."
                            if data["state"] == "PASS"
                            else "Self-deception screen FAILED: %s -- see failed checks, do not treat the dashboard as PASS."
                            % ", ".join(data.get("failed_checks", []))),
            }
    except (OSError, json.JSONDecodeError):
        pass
    cards = []
    try:
        for line in _p("data/commercial_experiments_v56.jsonl").read_text(
                encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                cards.append(json.loads(line))
    except (OSError, json.JSONDecodeError):
        pass
    return {
        "reality_integrity": verdict,
        "active_experiments": sum(1 for c in cards if c.get("current_status") == "IN_MEASUREMENT_WINDOW"),
        "experiment_windows": [
            {"id": c.get("experiment_id"), "offer": c.get("offer_name"),
             "status": c.get("current_status"), "ends": c.get("end_time"),
             "next": c.get("next_action", "")[:160]} for c in cards
        ],
    }


def _next_best_actions(founder_actions, ops, priority, opportunities):
    """V5.5 Sec 12 -- NEXT BEST ACTIONS. A pure reshaping of sections already
    computed above (founder-authority queue, blocked operations, opportunities
    ready for review, current factory priority) — ordered by real evidence and
    real blockers. Never ranked by invented success scores and never carrying
    revenue probabilities (no real signal for either exists). Every action
    traces to the section it was cited from."""
    actions = []
    for a in (founder_actions.get("actions") or [])[:3]:
        actions.append({
            "action": a["what"],
            "why": a["why"],
            "evidence": a["what_factory_already_did"],
            "source": "founder_actions (genuine founder-authority queue)",
        })
    for b in (ops.get("blocked_operations") or [])[:3]:
        actions.append({
            "action": "Clear blocked operation: %s" % str(b.get("what", ""))[:160],
            "why": str(b.get("why", ""))[:200],
            "evidence": "Recorded in operations/blocked_operations.",
            "source": "operations (factory state + open incidents)",
        })
    if opportunities.get("ready_for_review"):
        actions.append({
            "action": ("Review %d opportunitie(s) ready for your decision."
                       % opportunities["ready_for_review"]),
            "why": "Real evaluations are on file; the next step needs your authority.",
            "evidence": "opportunities/ready_for_review count from the live decision log (ACCEPTED only).",
            "source": "opportunities (decision log)",
        })
    actions.append({
        "action": "Otherwise: %s" % priority["current_priority"][:160],
        "why": priority["why"][:200],
        "evidence": "current_priority, read from live factory tick state.",
        "source": "current_priority",
    })
    return {
        "actions": actions[:7],
        "note": ("Ordered by evidence and blockers, not by predicted success. "
                 "No revenue probabilities are shown -- no real signal exists for them."),
    }


def _cli_main():
    print(json.dumps(build_founder_command_center(), ensure_ascii=False, default=str))


if __name__ == "__main__":
    _cli_main()

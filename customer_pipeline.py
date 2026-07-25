#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge Customer Pipeline (ADR-130, 2026-07-25).

Real Qualification -> Opportunity Evaluation -> Price Generation ->
Proposal -> Customer Approval -> Payment Verification for a real customer
request (data/customer_requests.jsonl, ADR-129). Every stage reuses the
SAME real engine every internally-discovered opportunity already goes
through -- a customer request is never scored by a separate, second-class
path:

  Qualification + Opportunity Evaluation -> decision_engine.evaluate_and_decide()
    (the exact real evidence gate advertised on the landing page itself --
    live Groq market research + profit_oracle.opportunity_score())
  Price Generation                       -> profit_oracle.butter_price()
    (the same constitutional $30-floor pricing engine, "premium" band --
    HIGH_VALUE_STRATEGY.md's $50-$300 custom-build tier)
  Payment Verification                   -> channels.paddle_publisher.create_checkout_transaction()
    (the same real Paddle integration ADR-074/085/086 already proved live)

Production / Quality Inspection / Packaging / Secure Delivery / Follow-up
are deliberately NOT wired here: every one of them requires Payment
Verification to actually succeed first, and Paddle's account-onboarding
gate (transaction_checkout_not_enabled) means no real request can reach
that state today (confirmed live, scripts/check_paddle_checkout_status.py).
Building them against a trigger that cannot fire would mean testing them
only against a mock, never a real live signal -- deferred to the round
Payment Verification first goes real. See ADR-129/ADR-130.

Resumability: every request's mutable pipeline state is one JSON record
in data/customer_pipeline_state.json, keyed by request_id -- separate
from the append-only data/customer_requests.jsonl intake ledger, same
"ledger vs mutable state" split this factory already uses for
decisions.jsonl vs factory_state.json. advance_request()/approve_request()/
reject_request() are idempotent and re-entrant: state is saved after every
real stage transition, so a crash/restart mid-pipeline loses no work and
never silently re-runs (or re-charges) a completed stage.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

DEFAULT_REQUESTS_PATH = _FACTORY_ROOT / "data" / "customer_requests.jsonl"
DEFAULT_STATE_PATH = _FACTORY_ROOT / "data" / "customer_pipeline_state.json"
DEFAULT_PADDLE_PRODUCTS_PATH = _FACTORY_ROOT / "data" / "paddle_products.json"

# Real product-price matching tolerance for reusing an existing Paddle
# price_id -- Payment Verification below only ever attempts a REAL
# checkout against a price Paddle already knows about (never invents a
# new product/price per customer; that automation doesn't exist yet).
_PRICE_MATCH_TOLERANCE = 1.0

# Informational only -- total stage count includes the honestly-not-yet-
# wired tail (Production..Follow-up) so a Mission Control progress bar
# reflects the REAL full pipeline length, not just what's implemented.
STAGE_ORDER = [
    "NEW", "QUALIFIED", "PROPOSED", "APPROVED", "AWAITING_PAYMENT",
    "PAID", "PRODUCTION", "QUALITY_INSPECTION", "PACKAGING", "DELIVERED", "FOLLOWED_UP",
]

# Fail-safe visibility (directive requirement 9): the real post-intake
# automation trigger (server.js fires customer_pipeline.py 'advance' as a
# fire-and-forget spawn right after intake) can fail silently -- a killed
# process, a Python import error, a machine restart mid-call. Past this
# many real minutes since submission with no state ever recorded, a
# request is flagged for a real founder look rather than staying
# invisibly stuck forever.
_STUCK_NEW_MINUTES = 10

# Terminal/side states a request can also land in -- not part of the
# "happy path" STAGE_ORDER progress bar, but real, honest, valid outcomes.
_SIDE_STATES = {
    "REJECTED_AT_QUALIFICATION", "PENDING_FOUNDER_REVIEW", "RESEARCH_REQUIRED",
    "REJECTED_BY_CUSTOMER", "PAYMENT_BLOCKED_PADDLE_ONBOARDING",
    "PENDING_CUSTOM_PRODUCT_SETUP", "FAILED",
}

_RECOVERY_HINTS = {
    "NEW": "Waiting for advance_request() to run real qualification -- automatic, no human action needed.",
    "QUALIFIED": "Internal state only (pricing runs immediately after) -- should never be seen at rest.",
    "PROPOSED": "Waiting on the customer to approve or decline the real proposal at their status link.",
    "APPROVED": "Internal state only (payment verification runs immediately after) -- should never be seen at rest.",
    "AWAITING_PAYMENT": "A real Paddle checkout link exists -- waiting on the customer to complete payment.",
    "REJECTED_AT_QUALIFICATION": "Terminal -- the real evidence gate did not accept this request. See reasoning.",
    "PENDING_FOUNDER_REVIEW": "The real evidence gate returned WAIT/IMPROVE (not a clear accept or reject) -- needs a human judgment call, same as any internally-discovered opportunity in this state.",
    "RESEARCH_REQUIRED": "Evidence coverage was too thin to honestly finalize a verdict (ADR-127) -- re-run evidence acquisition, same as any internal opportunity in this state.",
    "REJECTED_BY_CUSTOMER": "Terminal -- the customer declined the real proposal.",
    "PAYMENT_BLOCKED_PADDLE_ONBOARDING": "Blocked on Paddle's real account-onboarding gate (transaction_checkout_not_enabled) -- founder action required at vendors.paddle.com. Re-attempt via retry_payment_verification() once cleared.",
    "PENDING_CUSTOM_PRODUCT_SETUP": "This proposal's price has no matching real Paddle product/price yet -- creating a bespoke Paddle product per custom request isn't automated (real, disclosed gap). Founder can create one manually in vendors.paddle.com, then re-run retry_payment_verification().",
    "FAILED": "A real error interrupted this request's pipeline -- see the error field. Safe to retry via advance_request()/retry_payment_verification(), state was saved before the failure.",
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load_state(state_path=None):
    path = Path(state_path) if state_path else DEFAULT_STATE_PATH
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state(state, state_path=None):
    path = Path(state_path) if state_path else DEFAULT_STATE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _load_requests(requests_path=None):
    """Real, append-only intake ledger -- never mutated here. Returns a
    dict keyed by request_id, last write wins if a request_id somehow
    repeats (it can't today; crypto.randomBytes(8) in server.js)."""
    path = Path(requests_path) if requests_path else DEFAULT_REQUESTS_PATH
    if not path.exists():
        return {}
    records = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("request_id"):
                records[rec["request_id"]] = rec
    return records


def _load_paddle_products(paddle_products_path=None):
    path = Path(paddle_products_path) if paddle_products_path else DEFAULT_PADDLE_PRODUCTS_PATH
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _notify_founder(text):
    """Best-effort, never raises -- same real Telegram channel every
    other real factory event already uses (channels.telegram_direct),
    called directly since this module has no Express/Node dependency.
    Direct customer-facing notification (email/SMS) is NOT built --
    honestly disclosed in ADR-130, not simulated here."""
    try:
        from channels import telegram_direct
        telegram_direct.send_telegram_message(text)
    except Exception:
        pass


def _record_history(record, stage, detail=None):
    record["stage"] = stage
    record["updated_at"] = _now()
    record.setdefault("stage_history", []).append({"stage": stage, "at": record["updated_at"], "detail": detail})


def _new_record(request_id):
    now = _now()
    return {
        "request_id": request_id,
        "stage": "NEW",
        "stage_history": [{"stage": "NEW", "at": now, "detail": "intake recorded"}],
        "created_at": now,
        "updated_at": now,
        "decision_id": None,
        "evaluation_summary": None,
        "proposal": None,
        "payment": None,
        "error": None,
    }


def _run_qualification_and_pricing(record, request, decisions_path=None, analysis_db_file=None, evaluate_fn=None, price_fn=None):
    """Real Qualification + Opportunity Evaluation + Price Generation +
    Proposal, chained -- these four directive stages have no human
    decision point between them, so running them together in one
    resumable call matches the "end-to-end automation" requirement
    without inventing a separate manual gate that doesn't exist anywhere
    else in this factory's own opportunity pipeline."""
    from decision_engine import engine as decision_engine

    description = (request.get("description") or "").strip()
    evaluate = evaluate_fn or decision_engine.evaluate_and_decide
    decision = evaluate(
        description, tier="tier1", decisions_path=decisions_path, analysis_db_file=analysis_db_file,
    )
    # decision may be a Decision dataclass (real evaluate_and_decide) or a
    # plain dict (test doubles) -- normalize once, here.
    decision_dict = decision.to_dict() if hasattr(decision, "to_dict") else dict(decision)

    record["decision_id"] = decision_dict.get("decision_id")
    record["evaluation_summary"] = {
        "status": decision_dict.get("status"),
        "ai_ceo_decision": decision_dict.get("ai_ceo_decision"),
        "opportunity_score": decision_dict.get("opportunity_score"),
        "reasoning": decision_dict.get("reasoning", [])[:5],
    }

    status = decision_dict.get("status")
    if status == "REJECTED":
        _record_history(record, "REJECTED_AT_QUALIFICATION", "the real evidence gate did not accept this request")
        _notify_founder(f"❌ طلب عميل مرفوض عند التقييم\nطلب: {request.get('request_id')}\nالسبب: {'; '.join(record['evaluation_summary']['reasoning'][:2])}")
        return record
    if status == "RESEARCH_REQUIRED":
        _record_history(record, "RESEARCH_REQUIRED", "evidence coverage too thin to finalize honestly (ADR-127)")
        return record
    if status == "DEFERRED":
        _record_history(record, "PENDING_FOUNDER_REVIEW", "real gate returned WAIT/IMPROVE -- needs human judgment")
        _notify_founder(f"⏸️ طلب عميل يحتاج مراجعة بشرية\nطلب: {request.get('request_id')}")
        return record

    # status == ACCEPTED
    _record_history(record, "QUALIFIED", f"decision {decision_dict.get('decision_id')} ACCEPTED")

    from profit_oracle import butter_price
    price = (price_fn or butter_price)(description, product_type="premium")
    proposal = {
        "price": round(float(price), 2),
        "currency": "USD",
        "price_basis": "Galaxy Forge Butter Pricing (profit_oracle.butter_price, premium custom-build band)",
        "opportunity_score": decision_dict.get("opportunity_score"),
        "evidence_summary": record["evaluation_summary"]["reasoning"],
        "proposed_at": _now(),
    }
    record["proposal"] = proposal
    _record_history(record, "PROPOSED", f"${proposal['price']:.2f}")
    _notify_founder(
        f"\U0001F4C4 اقتراح عرض جاهز لعميل\nطلب: {request.get('request_id')}\nالسعر: ${proposal['price']:.2f}\n"
        f"الوصف: {(request.get('description') or '')[:200]}"
    )
    return record


def advance_request(request_id, requests_path=None, state_path=None, decisions_path=None,
                     analysis_db_file=None, evaluate_fn=None, price_fn=None):
    """Idempotent entry point: safe to call repeatedly (retries after a
    crash, a manual re-trigger, a batch sweep). A request already past
    NEW is returned unchanged -- never re-evaluated, never re-priced."""
    requests = _load_requests(requests_path)
    request = requests.get(request_id)
    if request is None:
        return {"success": False, "error": f"no such customer request: {request_id!r}"}

    state = _load_state(state_path)
    record = state.get(request_id) or _new_record(request_id)

    if record["stage"] != "NEW":
        state[request_id] = record
        _save_state(state, state_path)
        return {"success": True, "already_advanced": True, **record}

    try:
        record = _run_qualification_and_pricing(
            record, request, decisions_path=decisions_path, analysis_db_file=analysis_db_file,
            evaluate_fn=evaluate_fn, price_fn=price_fn,
        )
    except Exception as e:
        record["error"] = str(e)
        _record_history(record, "FAILED", str(e))

    state[request_id] = record
    _save_state(state, state_path)
    return {"success": True, "already_advanced": False, **record}


def _attempt_payment_verification(record, paddle_products_path=None, checkout_fn=None, api_key_loader=None):
    """Real Paddle checkout attempt, same classification discipline as
    scripts/check_paddle_checkout_status.py's check_and_notify() -- never
    fabricates a checkout_url, never silently swallows a real error."""
    from channels import paddle_publisher

    proposal = record.get("proposal") or {}
    price = proposal.get("price")
    products = _load_paddle_products(paddle_products_path)
    match = next((p for p in products if abs(float(p.get("price", -1e9)) - float(price or -1e9)) <= _PRICE_MATCH_TOLERANCE), None)

    if match is None:
        _record_history(record, "PENDING_CUSTOM_PRODUCT_SETUP", f"no existing Paddle price within ${_PRICE_MATCH_TOLERANCE} of ${price}")
        return record

    try:
        api_key = (api_key_loader or paddle_publisher.load_api_key)()
    except paddle_publisher.ConfigError as e:
        record["error"] = str(e)
        _record_history(record, "FAILED", str(e))
        return record

    create_checkout = checkout_fn or paddle_publisher.create_checkout_transaction
    try:
        _txn, checkout_url = create_checkout(api_key, match["price_id"])
    except RuntimeError as e:
        msg = str(e).lower()
        if "checkout" in msg and "enabled" in msg and "account" in msg:
            _record_history(record, "PAYMENT_BLOCKED_PADDLE_ONBOARDING", "Paddle onboarding still incomplete (transaction_checkout_not_enabled)")
            return record
        record["error"] = str(e)
        _record_history(record, "FAILED", str(e))
        return record

    if not checkout_url:
        record["error"] = "Paddle returned no checkout.url despite a successful transaction response"
        _record_history(record, "FAILED", record["error"])
        return record

    record["payment"] = {"checkout_url": checkout_url, "price_id": match["price_id"], "matched_product": match["title"]}
    _record_history(record, "AWAITING_PAYMENT", "real Paddle checkout link created")
    _notify_founder(f"\U0001F4B0 رابط دفع حقيقي جاهز لعميل\nطلب: {record['request_id']}\nالرابط: {checkout_url}")
    return record


def approve_request(request_id, requests_path=None, state_path=None, paddle_products_path=None,
                     checkout_fn=None, api_key_loader=None):
    """The customer's own real action -- only valid from PROPOSED.
    Immediately attempts real Payment Verification in the same call
    (no separate human gate exists between approval and payment for an
    already-accepted, already-priced request)."""
    state = _load_state(state_path)
    record = state.get(request_id)
    if record is None:
        return {"success": False, "error": f"no pipeline state for request {request_id!r} -- has it been qualified yet?"}
    if record["stage"] != "PROPOSED":
        return {"success": False, "error": f"cannot approve from stage {record['stage']!r} -- only PROPOSED accepts approval"}

    _record_history(record, "APPROVED", "customer approved the real proposal")
    try:
        record = _attempt_payment_verification(record, paddle_products_path=paddle_products_path, checkout_fn=checkout_fn, api_key_loader=api_key_loader)
    except Exception as e:
        record["error"] = str(e)
        _record_history(record, "FAILED", str(e))

    state[request_id] = record
    _save_state(state, state_path)
    return {"success": True, **record}


def reject_request(request_id, reason=None, state_path=None):
    """The customer's own real action -- only valid from PROPOSED."""
    state = _load_state(state_path)
    record = state.get(request_id)
    if record is None:
        return {"success": False, "error": f"no pipeline state for request {request_id!r}"}
    if record["stage"] != "PROPOSED":
        return {"success": False, "error": f"cannot reject from stage {record['stage']!r} -- only PROPOSED accepts rejection"}

    _record_history(record, "REJECTED_BY_CUSTOMER", (reason or "").strip()[:300] or "no reason given")
    state[request_id] = record
    _save_state(state, state_path)
    return {"success": True, **record}


def retry_payment_verification(request_id, state_path=None, paddle_products_path=None, checkout_fn=None, api_key_loader=None):
    """Re-attempts Payment Verification for a request currently blocked
    on Paddle onboarding, a missing custom product, or a prior failure --
    same real re-attempt discipline as check-paddle-checkout-status.
    Never fires for a request that was never approved."""
    state = _load_state(state_path)
    record = state.get(request_id)
    if record is None:
        return {"success": False, "error": f"no pipeline state for request {request_id!r}"}
    if record["stage"] not in ("PAYMENT_BLOCKED_PADDLE_ONBOARDING", "PENDING_CUSTOM_PRODUCT_SETUP", "FAILED"):
        return {"success": False, "error": f"cannot retry payment from stage {record['stage']!r}"}

    try:
        record = _attempt_payment_verification(record, paddle_products_path=paddle_products_path, checkout_fn=checkout_fn, api_key_loader=api_key_loader)
    except Exception as e:
        record["error"] = str(e)
        _record_history(record, "FAILED", str(e))

    state[request_id] = record
    _save_state(state, state_path)
    return {"success": True, **record}


def _progress(stage):
    if stage in STAGE_ORDER:
        idx = STAGE_ORDER.index(stage)
        return {"stage_index": idx, "total_stages": len(STAGE_ORDER), "percent": round(100 * idx / (len(STAGE_ORDER) - 1), 1)}
    return {"stage_index": None, "total_stages": len(STAGE_ORDER), "percent": None}


def _supervision_view(record):
    """The exact 6 fields the directive requires every workflow to
    expose: Status, Progress, Logs, Failures, Recovery, Estimated
    completion. estimated_completion is honestly null -- zero real
    completions exist yet to derive a real estimate from (no fabricated
    ETA)."""
    return {
        "request_id": record["request_id"],
        "status": record["stage"],
        "progress": _progress(record["stage"]),
        "logs": record.get("stage_history", []),
        "failures": record.get("error"),
        "recovery": _RECOVERY_HINTS.get(record["stage"], "no recovery guidance defined for this stage"),
        "estimated_completion": None,
        "proposal": record.get("proposal"),
        "payment": record.get("payment"),
        "updated_at": record.get("updated_at"),
    }


def get_pipeline_status(request_id, requests_path=None, state_path=None):
    requests = _load_requests(requests_path)
    request = requests.get(request_id)
    if request is None:
        return {"success": False, "error": f"no such customer request: {request_id!r}"}
    state = _load_state(state_path)
    record = state.get(request_id) or _new_record(request_id)
    return {"success": True, "request": {k: v for k, v in request.items() if k != "email"}, **_supervision_view(record)}


def list_pipeline_overview(requests_path=None, state_path=None):
    """Mission Control aggregate view -- real stage distribution across
    every real request, plus which ones need a real founder action
    (blocked on Paddle, needs a custom product, or failed)."""
    requests = _load_requests(requests_path)
    state = _load_state(state_path)
    entries = []
    stage_counts = {}
    needs_attention = []
    now = datetime.now(timezone.utc)
    for request_id, request in requests.items():
        ever_advanced = request_id in state
        record = state.get(request_id) or _new_record(request_id)
        stage = record["stage"]
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
        entry = {
            "request_id": request_id,
            "name": request.get("name"),
            "company": request.get("company"),
            "submitted_at": request.get("submitted_at"),
            **_supervision_view(record),
        }
        entries.append(entry)
        if stage in ("PAYMENT_BLOCKED_PADDLE_ONBOARDING", "PENDING_CUSTOM_PRODUCT_SETUP", "FAILED", "PENDING_FOUNDER_REVIEW"):
            needs_attention.append({"request_id": request_id, "stage": stage, "recovery": entry["recovery"]})
        elif not ever_advanced:
            try:
                submitted_at = datetime.fromisoformat((request.get("submitted_at") or "").replace("Z", "+00:00"))
                stale = now - submitted_at > timedelta(minutes=_STUCK_NEW_MINUTES)
            except ValueError:
                stale = False
            if stale:
                needs_attention.append({
                    "request_id": request_id, "stage": "NEW",
                    "recovery": f"still NEW after {_STUCK_NEW_MINUTES}+ minutes -- the automatic post-intake trigger may have failed; run 'Advance Customer Pipeline' in Mission Control.",
                })

    entries.sort(key=lambda e: e.get("updated_at") or e.get("submitted_at") or "", reverse=True)
    return {
        "total_requests": len(requests),
        "stage_distribution": stage_counts,
        "needs_attention": needs_attention,
        "requests": entries,
    }


def advance_all_new_requests(requests_path=None, state_path=None, decisions_path=None, analysis_db_file=None):
    """Batch sweep -- this factory has no scheduler (CLAUDE.md), so
    'automatic' means zero further code changes, one Mission Control
    click away, same convention as check-paddle-checkout-status /
    process_approved_drafts.py."""
    requests = _load_requests(requests_path)
    state = _load_state(state_path)
    advanced = []
    for request_id in requests:
        record = state.get(request_id)
        if record is None or record["stage"] == "NEW":
            result = advance_request(request_id, requests_path=requests_path, state_path=state_path,
                                      decisions_path=decisions_path, analysis_db_file=analysis_db_file)
            advanced.append({"request_id": request_id, "stage": result.get("stage")})
    return {"advanced_count": len(advanced), "advanced": advanced}


def main():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "usage: customer_pipeline.py <command> [json_payload]"}))
        sys.exit(1)
    command = sys.argv[1]
    payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    try:
        if command == "advance":
            result = advance_request(payload["request_id"])
        elif command == "approve":
            result = approve_request(payload["request_id"])
        elif command == "reject":
            result = reject_request(payload["request_id"], reason=payload.get("reason"))
        elif command == "retry_payment":
            result = retry_payment_verification(payload["request_id"])
        elif command == "status":
            result = get_pipeline_status(payload["request_id"])
        elif command == "overview":
            result = {"success": True, **list_pipeline_overview()}
        elif command == "advance_all":
            result = {"success": True, **advance_all_new_requests()}
        else:
            result = {"success": False, "error": f"unknown command: {command!r}"}
        print(json.dumps(result, ensure_ascii=False, default=str))
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()

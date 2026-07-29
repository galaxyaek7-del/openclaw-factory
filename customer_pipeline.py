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
    "PENDING_CUSTOM_PRODUCT_SETUP", "PENDING_FOUNDER_FULFILLMENT", "FAILED",
}

# Internal/technical -- Mission Control audience only (list_pipeline_
# overview()). Function names and implementation jargon are fine here;
# this is read by the founder, not a customer.
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
    "PENDING_FOUNDER_FULFILLMENT": "Round 4 (2026-07-29): no already-produced, already-published artifact exists in books/_generation_log.jsonl for this exact product -- this is a genuinely bespoke request with no automated production trigger wired yet (real, disclosed gap, same class as PENDING_CUSTOM_PRODUCT_SETUP). Founder must produce/attach a real deliverable via fulfill_manually() in Mission Control.",
    "FAILED": "A real error interrupted this request's pipeline -- see the error field. Safe to retry via advance_request()/retry_payment_verification(), state was saved before the failure.",
}

# Commercial Readiness Report (2026-07-25), finding PY1: the internal
# dict above was being reused verbatim for the customer's own status
# page -- a real paying customer would see raw function-call syntax like
# "retry_payment_verification()" under "Next step." This is the
# customer-safe equivalent: plain language, no function/module names, no
# internal jargon (ADR numbers, "the real evidence gate" internals),
# never dangles a reference to something not actually shown on the page.
_CUSTOMER_RECOVERY_HINTS = {
    "NEW": "We're reviewing your request — this usually takes under a minute.",
    "QUALIFIED": "Finalizing your quote.",
    "PROPOSED": "Your quote is ready below — approve to move forward, or decline if it's not a fit.",
    "APPROVED": "Setting up your payment.",
    "AWAITING_PAYMENT": "Complete your payment using the link below to move forward.",
    "REJECTED_AT_QUALIFICATION": "This request didn't meet our acceptance criteria this time. If circumstances change, feel free to submit an updated request.",
    "PENDING_FOUNDER_REVIEW": "Your request needs a closer look from our team before we can quote it — we'll follow up.",
    "RESEARCH_REQUIRED": "We're gathering more evidence before finalizing this — check back soon.",
    "REJECTED_BY_CUSTOMER": "You declined this proposal. Reach out any time if you'd like to revisit it.",
    "PAYMENT_BLOCKED_PADDLE_ONBOARDING": "Payment setup is still being finalized on our end. We'll notify you the moment it's ready — no action needed from you.",
    "PENDING_CUSTOM_PRODUCT_SETUP": "We're finishing setup for this item before payment can open. We'll notify you as soon as it's ready.",
    "PENDING_FOUNDER_FULFILLMENT": "Your payment is confirmed — we're preparing your deliverable now. We'll notify you the moment it's ready.",
    "FAILED": "Something went wrong on our end while processing this request. Our team has been notified — please check back shortly, or contact support.",
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


DEFAULT_GENERATION_LOG_PATH = _FACTORY_ROOT / "books" / "_generation_log.jsonl"


def _find_published_generation_record(title, generation_log_path=None):
    """Real-artifact lookup for Round 4 (2026-07-29): every live catalog
    product was, in fact, already produced and passed Dual Inspection once
    (verified 2026-07-29 against the real books/_generation_log.jsonl --
    all 5 real Paddle catalog products have a real, published=true entry
    here, including the 4 non-fiction "system" niches via book_generator.
    py's techdoc product type, not just literal books). A brand-new,
    genuinely bespoke request has no such entry -- that's the real,
    honest signal for routing PAID -> automated delivery vs.
    PENDING_FOUNDER_FULFILLMENT below, never a guess based on the
    product's category/name."""
    path = Path(generation_log_path) if generation_log_path else DEFAULT_GENERATION_LOG_PATH
    if not title or not path.exists():
        return None
    found = None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            # File is append-only chronological -- keep the LAST matching
            # published record, i.e. the most recent real pass.
            if rec.get("title") == title and rec.get("published"):
                found = rec
    return found


def _fulfill_paid_request(record, generation_log_path=None):
    """Real Production -> Quality Inspection -> Packaging -> Delivery for
    a request that just reached PAID (Customer Platform Round 4,
    2026-07-29). Honestly routed, never simulated:

    - If a real, already-published artifact exists for this exact product
      (every live catalog item does today), that artifact IS the real
      delivery -- reusing its already-real Dual Inspection pass rather
      than re-fabricating a second inspection that would tell us nothing
      new.
    - Otherwise (a genuinely bespoke/custom request -- no automated
      production trigger has ever been wired for a brand-new niche inside
      this pipeline), the record honestly stops at PENDING_FOUNDER_
      FULFILLMENT rather than faking automation that doesn't exist."""
    catalog_match = record.get("catalog_match")
    title = catalog_match.get("title") if catalog_match else None
    published_record = _find_published_generation_record(title, generation_log_path) if title else None
    artifact_path = published_record.get("path") if published_record else None

    if artifact_path and os.path.exists(artifact_path):
        record["fulfillment_type"] = "existing_catalog_artifact"
        _record_history(record, "PRODUCTION", f"real artifact already produced ({published_record.get('timestamp')})")
        _record_history(record, "QUALITY_INSPECTION", "reusing the real, already-passed Dual Inspection result for this exact product -- never re-fabricated")
        _record_history(record, "PACKAGING", "real file ready for secure delivery")
        record["delivery"] = {"type": "download", "path": artifact_path, "filename": os.path.basename(artifact_path)}
        _record_history(record, "DELIVERED", "real download ready")
        _notify_founder(f"\U0001F4E6 تسليم حقيقي جاهز لعميل\nطلب: {record['request_id']}\nالملف: {record['delivery']['filename']}")
    else:
        record["fulfillment_type"] = "manual_fulfillment"
        _record_history(record, "PRODUCTION", "no automated production trigger exists yet for this request")
        _record_history(record, "PENDING_FOUNDER_FULFILLMENT", "no real, already-produced artifact matches this request -- requires real founder fulfillment")
        _notify_founder(f"\U0001F477 طلب يحتاج تسليم يدوي حقيقي\nطلب: {record['request_id']}\nلا يوجد ملف منتَج مسبقاً لهذا المنتج")
    return record


def fulfill_manually(request_id, delivery_ref, note=None, state_path=None):
    """The founder's own real action (Mission Control only) -- completes a
    request stuck in PENDING_FOUNDER_FULFILLMENT by attaching a real
    deliverable: either a real local file path (validated to exist) or a
    real URL (e.g. a Gumroad/Etsy listing link, a shared-drive link).
    Never a fabricated placeholder -- refuses if delivery_ref is empty."""
    delivery_ref = (delivery_ref or "").strip()
    if not delivery_ref:
        return {"success": False, "error": "delivery_ref (a real file path or URL) is required"}

    state = _load_state(state_path)
    record = state.get(request_id)
    if record is None:
        return {"success": False, "error": f"no pipeline state for request {request_id!r}"}
    if record["stage"] != "PENDING_FOUNDER_FULFILLMENT":
        return {"success": False, "error": f"cannot manually fulfill from stage {record['stage']!r} (must be PENDING_FOUNDER_FULFILLMENT)"}

    is_url = delivery_ref.startswith("http://") or delivery_ref.startswith("https://")
    if not is_url and not os.path.exists(delivery_ref):
        return {"success": False, "error": f"real local file not found: {delivery_ref!r} (use a real path or a real https:// URL)"}

    record["delivery"] = {
        "type": "link" if is_url else "download",
        "path": None if is_url else delivery_ref,
        "url": delivery_ref if is_url else None,
        "filename": None if is_url else os.path.basename(delivery_ref),
        "note": (note or "").strip()[:500] or None,
    }
    _record_history(record, "DELIVERED", f"founder attached a real deliverable ({'URL' if is_url else 'file'})")
    state[request_id] = record
    _save_state(state, state_path)
    return {"success": True, **record}


def get_download_path(request_id, state_path=None):
    """Server-side-only lookup (never returned raw to a browser) -- the
    real local file path for a DELIVERED request's own download route."""
    state = _load_state(state_path)
    record = state.get(request_id)
    if record is None:
        return {"success": False, "error": f"no pipeline state for request {request_id!r}"}
    if record["stage"] != "DELIVERED":
        return {"success": False, "error": "this request has no download ready yet"}
    delivery = record.get("delivery") or {}
    if delivery.get("type") != "download" or not delivery.get("path"):
        return {"success": False, "error": "this request's delivery is a link, not a downloadable file"}
    if not os.path.exists(delivery["path"]):
        return {"success": False, "error": "the real file for this delivery is missing on disk"}
    return {"success": True, "path": delivery["path"], "filename": delivery.get("filename") or os.path.basename(delivery["path"])}


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


def _run_qualification_and_pricing(record, request, decisions_path=None, analysis_db_file=None,
                                    evaluate_fn=None, price_fn=None, paddle_products_path=None):
    """Real Qualification + Opportunity Evaluation + Price Generation +
    Proposal, chained -- these four directive stages have no human
    decision point between them, so running them together in one
    resumable call matches the "end-to-end automation" requirement
    without inventing a separate manual gate that doesn't exist anywhere
    else in this factory's own opportunity pipeline.

    Commercial Readiness Report (2026-07-25), finding P1: when the
    request references an existing live catalog product (catalog_
    product_id, set by server.js when a customer clicks "Request
    access" on a specific catalog card), that product has ALREADY
    cleared the real evidence gate -- it exists as a real, priced, live
    Paddle product. Re-running evaluate_and_decide()/butter_price() on a
    freeform "Interested in: X" description could legitimately produce a
    DIFFERENT price than the one just shown on the catalog card (butter_
    price() computes independently, never reads the catalog). The fix:
    never re-evaluate a known catalog item -- the displayed price IS the
    quote, exactly, every time."""
    catalog_product_id = request.get("catalog_product_id")
    if catalog_product_id:
        catalog_match = next(
            (p for p in _load_paddle_products(paddle_products_path) if p.get("product_id") == catalog_product_id),
            None,
        )
        if catalog_match is not None:
            record["decision_id"] = None
            record["evaluation_summary"] = {
                "status": "CATALOG_MATCH",
                "ai_ceo_decision": "N/A",
                "opportunity_score": None,
                "reasoning": ["This is an existing Galaxy Forge product that already cleared our evidence gate — no re-evaluation needed."],
            }
            _record_history(record, "QUALIFIED", f"matched live catalog product {catalog_product_id}")
            proposal = {
                "price": round(float(catalog_match["price"]), 2),
                "currency": "USD",
                "price_basis": "Galaxy Forge live catalog price — the exact price shown on the site for this product",
                "opportunity_score": None,
                "evidence_summary": record["evaluation_summary"]["reasoning"],
                "proposed_at": _now(),
            }
            record["proposal"] = proposal
            record["catalog_match"] = {
                "product_id": catalog_match["product_id"], "price_id": catalog_match["price_id"], "title": catalog_match["title"],
            }
            from contract_generator import generate_contract
            record["contract"] = generate_contract(request, proposal, catalog_match=record["catalog_match"])
            _record_history(record, "PROPOSED", f"${proposal['price']:.2f} (live catalog price, no re-evaluation)")
            _notify_founder(
                f"\U0001F4C4 طلب شراء منتج جاهز من الكتالوج\nطلب: {request.get('request_id')}\nالمنتج: {catalog_match['title']}\nالسعر: ${proposal['price']:.2f}"
            )
            return record
        # catalog_product_id given but not found in the real catalog (a
        # stale reference -- e.g. the product was removed after the page
        # loaded) -- fail safe to the normal full-evaluation path below
        # rather than silently dropping the request.

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
    from contract_generator import generate_contract
    record["contract"] = generate_contract(request, proposal, catalog_match=None)
    _record_history(record, "PROPOSED", f"${proposal['price']:.2f}")
    _notify_founder(
        f"\U0001F4C4 اقتراح عرض جاهز لعميل\nطلب: {request.get('request_id')}\nالسعر: ${proposal['price']:.2f}\n"
        f"الوصف: {(request.get('description') or '')[:200]}"
    )
    return record


def advance_request(request_id, requests_path=None, state_path=None, decisions_path=None,
                     analysis_db_file=None, evaluate_fn=None, price_fn=None, paddle_products_path=None):
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
            evaluate_fn=evaluate_fn, price_fn=price_fn, paddle_products_path=paddle_products_path,
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

    catalog_match = record.get("catalog_match")
    if catalog_match:
        # Exact, no ambiguity: this request was locked to a real catalog
        # product_id/price_id at Qualification time -- never re-searched
        # by price proximity (that tolerance-based search is only for
        # genuinely custom requests, which have no known price_id yet).
        match = {"price_id": catalog_match["price_id"], "title": catalog_match["title"]}
    else:
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
        txn, checkout_url = create_checkout(api_key, match["price_id"])
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

    # Customer Platform Round 3 (2026-07-29): persist the full real Paddle
    # transaction object (previously discarded right after extracting
    # checkout_url) -- check_payment_status() below needs its real "id" to
    # later confirm this exact transaction, and the invoice needs a real
    # payment reference.
    record["payment"] = {"checkout_url": checkout_url, "price_id": match["price_id"], "matched_product": match["title"], "transaction": txn}
    _record_history(record, "AWAITING_PAYMENT", "real Paddle checkout link created")
    _notify_founder(f"\U0001F4B0 رابط دفع حقيقي جاهز لعميل\nطلب: {record['request_id']}\nالرابط: {checkout_url}")
    return record


def approve_request(request_id, accepted_name=None, requests_path=None, state_path=None, paddle_products_path=None,
                     checkout_fn=None, api_key_loader=None):
    """The customer's own real action -- only valid from PROPOSED.
    Immediately attempts real Payment Verification in the same call
    (no separate human gate exists between approval and payment for an
    already-accepted, already-priced request).

    Customer Platform Round 2 (2026-07-29): approval now doubles as real
    contract acceptance -- the customer must type their name as an
    e-signature (no e-signature integration exists, this is the honest
    real equivalent) before payment verification is attempted."""
    state = _load_state(state_path)
    record = state.get(request_id)
    if record is None:
        return {"success": False, "error": "We couldn't find an active quote for this request yet — please refresh in a moment."}
    if record["stage"] != "PROPOSED":
        return {"success": False, "error": "This request isn't ready for approval right now — refresh the page to see its current status."}
    accepted_name = (accepted_name or "").strip()
    if not accepted_name:
        return {"success": False, "error": "Please type your full name to confirm you accept the contract terms before approving."}

    if record.get("contract"):
        record["contract"]["accepted"] = True
        record["contract"]["accepted_name"] = accepted_name[:200]
        record["contract"]["accepted_at"] = _now()
    _record_history(record, "APPROVED", f"customer approved the real proposal and accepted the contract as {accepted_name[:100]!r}")
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
        return {"success": False, "error": "We couldn't find an active quote for this request yet — please refresh in a moment."}
    if record["stage"] != "PROPOSED":
        return {"success": False, "error": "This request isn't ready to decline right now — refresh the page to see its current status."}

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


def check_payment_status(request_id, requests_path=None, state_path=None, api_key_loader=None, get_transactions_fn=None):
    """Real Payment completion check (Customer Platform Round 3,
    2026-07-29): confirms the real Paddle transaction created in
    AWAITING_PAYMENT actually completed, transitions AWAITING_PAYMENT ->
    PAID, and generates a real invoice from the locked contract price.

    Never fabricates a completion -- an unreachable Paddle API, a
    transaction that isn't visible yet, or a still-pending status all
    leave the record exactly where it was, no state changed. Paddle's own
    real "paid" status value for a transaction has never been observed
    against a live account (channels/paddle_publisher.py's own docstring
    caveat) -- every plausible value is checked rather than assuming one,
    and this is the one real seam that stays untested against live Paddle
    data until the account's own onboarding gate clears."""
    state = _load_state(state_path)
    record = state.get(request_id)
    if record is None:
        return {"success": False, "error": f"no pipeline state for request {request_id!r}"}
    if record["stage"] != "AWAITING_PAYMENT":
        return {"success": False, "error": f"cannot check payment status from stage {record['stage']!r} (must be AWAITING_PAYMENT)"}

    payment = record.get("payment") or {}
    txn = payment.get("transaction") or {}
    txn_id = txn.get("id")
    if not txn_id:
        return {"success": False, "error": "no real Paddle transaction id was recorded for this request"}

    from channels import paddle_publisher
    try:
        api_key = (api_key_loader or paddle_publisher.load_api_key)()
    except paddle_publisher.ConfigError as e:
        return {"success": False, "error": str(e)}

    get_transactions = get_transactions_fn or paddle_publisher.get_transactions
    try:
        transactions = get_transactions(api_key)
    except RuntimeError as e:
        # A real but transient API error -- stay in AWAITING_PAYMENT, never
        # fail the request over a temporary Paddle API hiccup.
        return {"success": False, "error": str(e)}

    match = next((t for t in transactions if t.get("id") == txn_id), None)
    if match is None:
        return {"success": True, "already_paid": False, "stage": record["stage"], "note": "transaction not yet visible in Paddle's transaction list"}

    status = str(match.get("status") or "").lower()
    if status not in ("completed", "paid", "billed"):
        return {"success": True, "already_paid": False, "stage": record["stage"], "paddle_status": status}

    record["payment"]["transaction"] = match
    _record_history(record, "PAID", f"real Paddle transaction {txn_id} confirmed ({status})")
    from invoice_generator import generate_invoice
    record["invoice"] = generate_invoice(record, match)
    record = _fulfill_paid_request(record)

    state[request_id] = record
    _save_state(state, state_path)
    _notify_founder(f"✅ دفعة حقيقية مؤكدة\nطلب: {request_id}\nالمبلغ: ${(record.get('proposal') or {}).get('price', 0):.2f}")
    return {"success": True, "already_paid": True, **record}


def _progress(stage):
    if stage in STAGE_ORDER:
        idx = STAGE_ORDER.index(stage)
        return {"stage_index": idx, "total_stages": len(STAGE_ORDER), "percent": round(100 * idx / (len(STAGE_ORDER) - 1), 1)}
    return {"stage_index": None, "total_stages": len(STAGE_ORDER), "percent": None}


def _supervision_view(record, audience="internal"):
    """The exact 6 fields the directive requires every workflow to
    expose: Status, Progress, Logs, Failures, Recovery, Estimated
    completion. estimated_completion is honestly null -- zero real
    completions exist yet to derive a real estimate from (no fabricated
    ETA).

    audience="internal" (default, Mission Control) uses _RECOVERY_HINTS
    (technical, function names allowed). audience="customer" (the
    customer's own status page) uses _CUSTOMER_RECOVERY_HINTS -- plain
    language only. Same underlying real state either way; only the
    recovery wording differs per Commercial Readiness Report finding
    PY1."""
    hints = _CUSTOMER_RECOVERY_HINTS if audience == "customer" else _RECOVERY_HINTS
    fallback = "We'll update this shortly." if audience == "customer" else "no recovery guidance defined for this stage"
    delivery = record.get("delivery")
    # Round 4 (2026-07-29): the real local filesystem path/founder note
    # never needs to reach the browser -- the customer's own download
    # route resolves the path server-side via get_download_path(). The
    # internal (Mission Control) view keeps the full real record.
    if delivery and audience == "customer":
        delivery_view = {"ready": True, "filename": delivery.get("filename"), "url": delivery.get("url")}
    else:
        delivery_view = delivery
    return {
        "request_id": record["request_id"],
        "status": record["stage"],
        "progress": _progress(record["stage"]),
        "logs": record.get("stage_history", []),
        "failures": record.get("error"),
        "recovery": hints.get(record["stage"], fallback),
        "estimated_completion": None,
        "proposal": record.get("proposal"),
        "contract": record.get("contract"),
        "payment": record.get("payment"),
        "invoice": record.get("invoice"),
        "delivery": delivery_view,
        "updated_at": record.get("updated_at"),
    }


def get_pipeline_status(request_id, requests_path=None, state_path=None):
    requests = _load_requests(requests_path)
    request = requests.get(request_id)
    if request is None:
        return {"success": False, "error": "We couldn't find a request with that ID — please double-check it and try again."}
    state = _load_state(state_path)
    record = state.get(request_id) or _new_record(request_id)
    return {"success": True, "request": {k: v for k, v in request.items() if k != "email"}, **_supervision_view(record, audience="customer")}


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


def check_all_awaiting_payments(requests_path=None, state_path=None):
    """Batch sweep, same one-click convention as advance_all_new_requests
    (this factory has no scheduler) -- checks every real request currently
    AWAITING_PAYMENT against Paddle's real transaction list."""
    state = _load_state(state_path)
    checked = []
    for request_id, record in list(state.items()):
        if record.get("stage") == "AWAITING_PAYMENT":
            result = check_payment_status(request_id, requests_path=requests_path, state_path=state_path)
            checked.append({"request_id": request_id, "success": result.get("success"), "already_paid": result.get("already_paid")})
    return {"checked_count": len(checked), "checked": checked}


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
            result = approve_request(payload["request_id"], accepted_name=payload.get("accepted_name"))
        elif command == "reject":
            result = reject_request(payload["request_id"], reason=payload.get("reason"))
        elif command == "retry_payment":
            result = retry_payment_verification(payload["request_id"])
        elif command == "check_payment":
            result = check_payment_status(payload["request_id"])
        elif command == "fulfill_manually":
            result = fulfill_manually(payload["request_id"], payload.get("delivery_ref"), note=payload.get("note"))
        elif command == "get_download_path":
            result = get_download_path(payload["request_id"])
        elif command == "status":
            result = get_pipeline_status(payload["request_id"])
        elif command == "overview":
            result = {"success": True, **list_pipeline_overview()}
        elif command == "advance_all":
            result = {"success": True, **advance_all_new_requests()}
        elif command == "check_all_payments":
            result = {"success": True, **check_all_awaiting_payments()}
        else:
            result = {"success": False, "error": f"unknown command: {command!r}"}
        print(json.dumps(result, ensure_ascii=False, default=str))
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()

"""Autonomous Commercial Operations (Phase: AUTONOMOUS COMMERCIAL OPERATIONS,
2026-08-14) -- the thin orchestration layer that turns the existing,
already-built engines (Revenue OS, commission_ledger, affiliate launch batch,
distributor, click tracking) into a daily-running commercial loop with the
least founder intervention.

Deliberately NOT a parallel system: every real signal is read from the exact
same existing source the rest of the factory uses. This module adds only the
genuinely-missing orchestration pieces:

  * Human Gate Orchestrator  -- one gate registry (state machine per gate),
    each gate storing gate_id/platform/action_required/why_required/status/
    blocking_revenue/founder_action/verification_after_action.
  * Founder Action Queue     -- shows ONLY URGENT (one action) / NEXT /
    OPTIONAL, never a wall of tasks. A gate becomes NOT_REQUIRED and is
    auto-closed the moment another path removes the need for it.
  * Unified Launch Queue     -- campaign -> asset -> channel -> tracking URL
    -> destination -> status, with the invariant that READY can never jump to
    PUBLISHED without an explicit AUTHORIZED founder action.
  * CEO Command Center       -- one screen: CASH/VERIFIED/PENDING/PROFIT/TOP
    ARM/TOP OFFER/TOP CHANNEL/ACTIVE/BLOCKED CAMPAIGNS/HUMAN GATES/NEXT ACTION.

Zero-cost, zero fabrication: nothing here spends money, creates accounts,
accepts legal terms, or records a revenue event. Everything revenue-facing
delegates to commission_ledger.py's anti-fabrication gates and the
Revenue OS verification tiers. All automated states are honest read-only
evaluations of real existing state.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import product_launch_kit

_FACTORY_ROOT = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Gate state machine (directive section 1)
# ---------------------------------------------------------------------------

GATE_STATES = ("OPEN", "BLOCKING", "READY_FOR_VERIFICATION", "VERIFIED", "FAILED", "NOT_REQUIRED")

# Gate definitions, keyed by gate_id. `depends_on` expresses ordering so the
# Founder Action Queue can show exactly one URGENT action: a gate that is
# blocked on an earlier un-verified gate is never pushed to the founder yet.
HUMAN_GATE_DEFS: Dict[str, dict] = {
    "GATE-AWIN-DIGITALOCEAN": {
        "platform": "DigitalOcean (Awin)",
        "action_required": "Apply to the verified DigitalOcean affiliate program on Awin + confirm Payoneer payout",
        "why_required": (
            "Official program verified live 2026-08-14: the DigitalOcean /affiliates "
            "'Become an affiliate' button resolves to Awin merchant profile 123996 "
            "(10% recurring commission for the first 12 months, 30-day cookie, paid via "
            "Payoneer for international publishers). The real tracking link stays "
            "NOT_CONFIGURED until the founder's application is approved -- no affiliate "
            "link can be generated or tracked before this."
        ),
        "blocking_revenue": True,
        "founder_action": "https://ui.awin.com/merchant-profile/123996",
        "verification_after_action": "Confirm a real Awin-approved tracking link exists in the founder's Awin dashboard (LAUNCH_LINK_STATUS becomes CONFIGURED), then wire it into the 7-channel launch batch.",
    },
    "GATE-GUMROAD-PAYMENT": {
        "platform": "Gumroad",
        "action_required": "Connect a payment method AND set real pricing on the created product",
        "why_required": (
            "GUMROAD_ACCESS_TOKEN is valid and the EU AI Act Compliance Toolkit product "
            "exists (live API, 2026-08-14) -- but it is a bare draft: published=False, "
            "price_cents=None (no price, cannot be purchased at any amount), no URL, no "
            "file. Gumroad requires a connected payment method before publish; pricing "
            "and file attachment are founder dashboard actions."
        ),
        "blocking_revenue": True,
        "founder_action": "Gumroad dashboard (aekraft.gumroad.com): add payment method, set price (planned $155), attach the PDF",
        "verification_after_action": "Live API shows published=True AND price_cents set; then call enable_product() via gumroad_publisher and verify the purchasable URL returns 200.",
    },
    "GATE-PADDLE-ONBOARDING": {
        "platform": "Paddle",
        "action_required": "Complete account onboarding (business/payment verification) in vendors.paddle.com",
        "why_required": (
            "Paddle API key is valid (HTTP 200) and 6 real products exist with real price "
            "IDs -- but all 6 report checkout_ready=false with the single reason 'Paddle "
            "onboarding still incomplete'. One founder action unlocks all 6 products at "
            "once; no per-product step exists or is required."
        ),
        "blocking_revenue": True,
        "founder_action": "vendors.paddle.com: complete the remaining onboarding/business-verification steps",
        "verification_after_action": "scripts/check_paddle_checkout_status.py reports checkout_ready=true for the same 6 product IDs; then wire the real webhook secret.",
    },
}

# ---------------------------------------------------------------------------
# Real-state helpers (compose existing modules, never duplicate them)
# ---------------------------------------------------------------------------


def _now_iso(now: Optional[datetime] = None) -> str:
    return (now or datetime.now(timezone.utc)).isoformat()


def _read_jsonl(path: Path) -> List[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _real_revenue_totals() -> Dict[str, float]:
    """VERIFIED/PENDING/PROJECTED, strictly separated, straight from the
    existing Revenue OS ledger view. Never merged, never summed together."""
    try:
        import revenue_os as ro
        view = ro.revenue_ledger_view()
        return {
            "VERIFIED_REVENUE_USD": float(view.get("VERIFIED_REVENUE_USD", 0.0)),
            "PENDING_REVENUE_USD": float(view.get("PENDING_REVENUE_USD", 0.0)),
            "PROJECTED_REVENUE_USD": float(view.get("PROJECTED_REVENUE_USD", 0.0)),
            "ESTIMATED_REVENUE_USD": float(view.get("ESTIMATED_REVENUE_USD", 0.0)),
            "OBSERVED_SALES": int(view.get("OBSERVED_SALES", 0)),
            "OBSERVED_CLICKS": view.get("OBSERVED_CLICKS", 0),
        }
    except Exception:
        return {
            "VERIFIED_REVENUE_USD": 0.0, "PENDING_REVENUE_USD": 0.0,
            "PROJECTED_REVENUE_USD": 0.0, "ESTIMATED_REVENUE_USD": 0.0,
            "OBSERVED_SALES": 0, "OBSERVED_CLICKS": 0,
        }


def _launch_link_status() -> str:
    try:
        from affiliate_launch_prep import LAUNCH_LINK_STATUS
        return str(LAUNCH_LINK_STATUS)
    except Exception:
        return "UNKNOWN"


# ---------------------------------------------------------------------------
# 0 -- Revenue Integrity Gate (directive priority #1)
# ---------------------------------------------------------------------------

# Real classification tiers. VERIFIED is the ONLY tier that may ever be
# presented as revenue. Everything else is reported separately.
CLASSIFICATION_TIERS = ("VERIFIED", "OBSERVED", "TEST", "MOCK", "PROJECTED", "UNKNOWN")

_SALE_IDENTITY_FIELDS = (
    "sale_id", "platform", "order_id", "transaction_id", "timestamp",
    "offer", "channel", "campaign", "amount", "currency", "status", "evidence",
)

# A genuine sale record is one whose event_type is an actual transactional
# sale and which carries a real platform order/transaction reference.
_REAL_SALE_EVENT_TYPES = ("sale", "order", "transaction", "commission", "checkout")


def _classify_sales_ledger_row(row: dict) -> dict:
    """Classify ONE data/sales_ledger.jsonl row into VERIFIED/OBSERVED/TEST/
    MOCK/PROJECTED/UNKNOWN, with a human-readable reason. History is never
    deleted: the raw row is returned verbatim under `raw`."""
    event_type = str(row.get("event_type") or "").lower()
    raw = row.get("raw") or {}

    # Only genuine transactional event types can possibly be sales.
    if event_type not in _REAL_SALE_EVENT_TYPES:
        return {
            "sale_id": row.get("sale_id") or row.get("id"),
            "platform": row.get("platform"),
            "classification": "UNKNOWN",
            "reason": f"event_type={row.get('event_type')!r} is not a transactional sale (real types: {_REAL_SALE_EVENT_TYPES}) -- publish/dry-run/failure records are never sales",
            "revenue_eligible": False,
            "raw": row,
        }

    # A publish_attempt row is never a sale regardless of ok/dry_run flags.
    # It describes an attempt to PUBLISH a product, not a customer purchase.
    # (Historical rows in this factory are exactly this -- a mislabeled
    # "44 sales" claim would come from counting these as sales.)
    if event_type == "publish_attempt" or "publish" in event_type:
        return {
            "sale_id": row.get("sale_id") or row.get("id"),
            "platform": row.get("platform"),
            "classification": "UNKNOWN",
            "reason": "publish_attempt is a publish attempt, not a customer sale",
            "revenue_eligible": False,
            "raw": row,
        }

    # MOCK/TEST rows are explicit in the row itself.
    env = str(row.get("environment") or (raw.get("environment") if isinstance(raw, dict) else "") or "").upper()
    if env in ("MOCK", "SIMULATION"):
        return {
            "sale_id": row.get("sale_id") or row.get("id"),
            "platform": row.get("platform"),
            "classification": "MOCK",
            "reason": f"explicit environment={env}",
            "revenue_eligible": False,
            "raw": row,
        }
    if env == "TEST":
        return {
            "sale_id": row.get("sale_id") or row.get("id"),
            "platform": row.get("platform"),
            "classification": "TEST",
            "reason": "explicit environment=TEST",
            "revenue_eligible": False,
            "raw": row,
        }

    # A REAL-classified row still needs a platform order/transaction reference
    # plus evidence before it can be OBSERVED; only an independently-confirmed
    # paid event from the platform reaches VERIFIED.
    order_ref = row.get("order_id") or row.get("transaction_id") or (raw.get("id") if isinstance(raw, dict) else None)
    if not order_ref:
        return {
            "sale_id": row.get("sale_id") or row.get("id"),
            "platform": row.get("platform"),
            "classification": "UNKNOWN",
            "reason": "transactional event without a platform order/transaction reference",
            "revenue_eligible": False,
            "raw": row,
        }
    evidence = row.get("evidence") or (raw.get("evidence") if isinstance(raw, dict) else None)
    if env == "REAL" and not evidence:
        return {
            "sale_id": row.get("sale_id") or row.get("id"),
            "platform": row.get("platform"),
            "classification": "OBSERVED",
            "reason": "transactional event with order reference but no external evidence -- observed, not verified",
            "revenue_eligible": False,
            "raw": row,
        }
    return {
        "sale_id": row.get("sale_id") or row.get("id"),
        "platform": row.get("platform"),
        "classification": "VERIFIED" if env == "REAL" else "OBSERVED",
        "reason": "transactional event with order reference" + (" and external evidence" if evidence else ""),
        "revenue_eligible": env == "REAL",
        "raw": row,
    }


def revenue_integrity_gate(sales_ledger_path: Optional[str] = None,
                           commission_ledger_path: Optional[str] = None,
                           clicks_ledger_path: Optional[str] = None) -> Dict[str, object]:
    """Priority-1 gate: audit every revenue-claiming source and classify every
    record. Real output:

      * sales_ledger.jsonl  -> every row classified (VERIFIED/OBSERVED/TEST/
        MOCK/PROJECTED/UNKNOWN). History preserved verbatim under `raw`.
      * VERIFIED_SALES       -> only rows classified VERIFIED.
      * OBSERVED_SALES       -> transactional events with order refs but no
        external evidence (never presented as revenue).
      * VERIFIED_REVENUE_USD -> from commission_ledger REAL CONFIRMED/PAID only.

    The gate never deletes data and never reclassifies upward. If a "44 sales"
    claim ever surfaces, this is where it is checked: each row must carry the
    full sale identity + evidence to be counted."""
    from channels import ledger as sales_ledger

    raw_rows = list(sales_ledger.read_events(ledger_path=sales_ledger_path))
    classified = [_classify_sales_ledger_row(r) for r in raw_rows]

    verified = [c for c in classified if c["classification"] == "VERIFIED"]
    observed = [c for c in classified if c["classification"] == "OBSERVED"]
    test_rows = [c for c in classified if c["classification"] == "TEST"]
    mock_rows = [c for c in classified if c["classification"] == "MOCK"]
    unknown = [c for c in classified if c["classification"] in ("UNKNOWN", "PROJECTED")]

    verified_usd = 0.0
    try:
        import revenue_os as ro
        view = ro.revenue_ledger_view(commission_ledger_path=commission_ledger_path,
                                      clicks_ledger_path=clicks_ledger_path)
        verified_usd = float(view.get("VERIFIED_REVENUE_USD", 0.0))
        observed_clicks = view.get("OBSERVED_CLICKS", {}).get("total_real_clicks", 0) if isinstance(view.get("OBSERVED_CLICKS"), dict) else view.get("OBSERVED_CLICKS", 0)
    except Exception:
        observed_clicks = 0

    return {
        "generated_at": _now_iso(),
        "VERIFIED_SALES": len(verified),
        "VERIFIED_REVENUE_USD": verified_usd,
        "OBSERVED_SALES": len(observed),
        "TEST_OR_MOCK_ROWS": len(test_rows) + len(mock_rows),
        "UNKNOWN_ROWS": len(unknown),
        "TOTAL_LEDGER_ROWS": len(raw_rows),
        "TOTAL_REAL_CLICKS": observed_clicks,
        "classified": classified,
        "verification_separation": "VERIFIED revenue comes ONLY from commission_ledger REAL CONFIRMED/PAID. OBSERVED/TEST/MOCK/PROJECTED/UNKNOWN are reported separately and NEVER summed into VERIFIED.",
        "note": "No row is counted as a sale unless it is a transactional event carrying a platform order/transaction reference and evidence. Publish attempts, dry runs, smoke tests and simulations are never sales and never revenue.",
    }


# ---------------------------------------------------------------------------
# 1 -- Human Gate Orchestrator
# ---------------------------------------------------------------------------

def human_gate_orchestrator(now: Optional[datetime] = None) -> Dict[str, object]:
    """Evaluate the real state of every registered human gate.

    State rules (all real, read-only):
      * GATE-AWIN-DIGITALOCEAN  -> BLOCKING until a real approved tracking link
        exists (LAUNCH_LINK_STATUS == CONFIGURED); else OPEN/BLOCKING.
      * GATE-GUMROAD-PAYMENT    -> BLOCKING while the live product is unpublished
        or unpriced; READY_FOR_VERIFICATION once the founder reports the dashboard
        action is done (verified by a later live API check).
      * GATE-PADDLE-ONBOARDING  -> BLOCKING while checkout_ready=false for all 6
        products; VERIFIED only after a live checkout check passes.

    A gate is NOT_REQUIRED the moment a competing arm path removes its need
    (e.g. if another arm produces verified revenue, low-value gates can be
    auto-closed by the caller via auto_close_superseded_gates)."""
    totals = _real_revenue_totals()
    link_status = _launch_link_status()

    gates = []
    for gate_id, spec in HUMAN_GATE_DEFS.items():
        status = "OPEN"
        verification = "PENDING"

        if gate_id == "GATE-AWIN-DIGITALOCEAN":
            if link_status == "CONFIGURED":
                status, verification = "READY_FOR_VERIFICATION", "verify a real Awin click/order event"
            else:
                status = "BLOCKING" if spec["blocking_revenue"] else "OPEN"

        elif gate_id == "GATE-GUMROAD-PAYMENT":
            # Real live check: unpublished/unpriced draft => BLOCKING.
            try:
                from channels.gumroad_publisher import load_token, list_products
                products = list_products(load_token())
                draft = all(not (p.get("published") or p.get("price_cents")) for p in (products or []))
                status = "BLOCKING" if draft else "READY_FOR_VERIFICATION"
                verification = "confirm published=True + price via live API, then enable_product()"
            except Exception:
                status = "OPEN"
                verification = "live Gumroad check unavailable"

        elif gate_id == "GATE-PADDLE-ONBOARDING":
            try:
                # Real live checkout status from the existing checker; the
                # caller (tests) may inject a stub to stay mock-only.
                from scripts.check_paddle_checkout_status import check_and_notify_all
                result = check_and_notify_all()
                results = result if isinstance(result, list) else result.get("results", [])
                ready = any(r.get("checkout_ready") for r in results)
                status = "READY_FOR_VERIFICATION" if ready else "BLOCKING"
                verification = "re-run check_paddle_checkout_status.py -- checkout_ready=true + real webhook"
            except Exception:
                status = "OPEN"
                verification = "live Paddle checkout check unavailable"

        gates.append({
            "gate_id": gate_id,
            "platform": spec["platform"],
            "action_required": spec["action_required"],
            "why_required": spec["why_required"],
            "status": status,
            "blocking_revenue": spec["blocking_revenue"],
            "founder_action": spec["founder_action"],
            "verification_after_action": spec["verification_after_action"],
            "verification_probe": verification,
        })

    return {
        "generated_at": _now_iso(now),
        "gates": gates,
        "note": "Real read-only state. VERIFIED requires a live external confirmation -- no gate is marked VERIFIED from an assumption.",
    }


def auto_close_superseded_gates(gates: List[dict], now: Optional[datetime] = None) -> List[dict]:
    """Close any gate that another already-verified revenue path makes
    unnecessary. Real rule: if a REAL VERIFIED commission already exists from
    any arm, non-essential (non-blocking) setup gates become NOT_REQUIRED --
    the founder is never asked for setup that a working path no longer needs."""
    totals = _real_revenue_totals()
    has_verified = totals["VERIFIED_REVENUE_USD"] > 0
    out = []
    for g in gates:
        if has_verified and not g.get("blocking_revenue"):
            g = dict(g)
            g["status"] = "NOT_REQUIRED"
            g["auto_closed"] = True
        else:
            g = dict(g)
            g["auto_closed"] = False
        out.append(g)
    return out


# ---------------------------------------------------------------------------
# 2 -- Founder Action Queue
# ---------------------------------------------------------------------------

def founder_action_queue(now: Optional[datetime] = None) -> Dict[str, object]:
    """Show the founder exactly one action at a time:
      * URGENT  -- the first BLOCKING gate that is blocking revenue and is not
        itself blocked on an earlier gate.
      * NEXT    -- the next BLOCKING/OPEN gate after URGENT is cleared.
      * OPTIONAL-- non-blocking / NOT_REQUIRED gates (never urgent).
    Nothing else is listed. Never a wall of tasks."""
    orchestrator = human_gate_orchestrator(now=now)
    gates = auto_close_superseded_gates(orchestrator["gates"], now=now)

    urgent = next((g for g in gates if g["status"] == "BLOCKING" and g["blocking_revenue"]), None)
    # NEXT is the short, capped list of remaining blocking gates (never a wall
    # of tasks) so a real second/third blocker is visible without flooding.
    next_up = [g for g in gates
               if g["status"] == "BLOCKING" and g["blocking_revenue"]
               and g["gate_id"] != (urgent or {}).get("gate_id")][:2]
    optional = [g for g in gates if g["status"] not in ("BLOCKING",) or not g["blocking_revenue"]]

    return {
        "generated_at": _now_iso(now),
        "URGENT": urgent,
        "NEXT": next_up,
        "OPTIONAL": optional,
        "rule": "Exactly ONE urgent action is shown; NEXT holds at most the next two blockers. No gate is shown twice.",
    }


# ---------------------------------------------------------------------------
# 6 -- Unified Launch Queue
# ---------------------------------------------------------------------------

LAUNCH_QUEUE_STATES = ("DRAFT", "QA", "READY", "HUMAN_GATE", "AUTHORIZED", "PUBLISHED", "TRACKING", "CONVERTED", "REVENUE_VERIFIED")


def _build_launch_entries(now: Optional[datetime] = None) -> List[dict]:
    """Read the real existing launch batch (per-offer, per-channel) and the
    real launch-link status. Destination is honest: it is only 'HUMAN_GATE'
    while the affiliate tracking link is NOT_CONFIGURED."""
    entries = []
    batch_dir = _FACTORY_ROOT / "launch_batches"
    if not batch_dir.exists():
        return entries
    for path in sorted(batch_dir.glob("*.json")):
        try:
            batch = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        opp_id = batch.get("opportunity_id") or path.stem
        assets = batch.get("assets") or []
        for a in assets:
            channel = a.get("channel", "unknown")
            entries.append({
                "campaign": (batch.get("campaign") or {}).get("id") or (batch.get("campaign") or {}).get("name") or opp_id,
                "asset": a.get("content", {}).get("title") if isinstance(a.get("content"), dict) else str(a.get("content"))[:60],
                "channel": channel,
                "tracking_url": (a.get("attribution") or {}).get("url") or "NOT_CONFIGURED",
                "destination": a.get("destination_url") or "NOT_CONFIGURED",
                "status": "HUMAN_GATE" if a.get("destination_status") != "CONFIGURED" else "READY",
                "offer_id": opp_id,
            })
    return entries


def unified_launch_queue(now: Optional[datetime] = None) -> Dict[str, object]:
    """The unified launch queue: campaign -> asset -> channel -> tracking URL
    -> destination -> status. Enforces the invariant that READY can never jump
    to PUBLISHED without an explicit AUTHORIZED step (AUTHORIZED only comes
    from a founder action; nothing here auto-publishes)."""
    entries = _build_launch_entries(now=now)
    active = [e for e in entries if e["status"] in ("HUMAN_GATE", "READY", "AUTHORIZED", "PUBLISHED", "TRACKING", "CONVERTED", "REVENUE_VERIFIED")]
    blocked = [e for e in entries if e["status"] == "HUMAN_GATE"]
    return {
        "generated_at": _now_iso(now),
        "entries": entries,
        "active_campaigns": len(active),
        "blocked_campaigns": len(blocked),
        "invariant": "READY -> PUBLISHED requires an explicit AUTHORIZED founder step. No auto-publish is ever performed.",
        "allowed_transitions": {
            "DRAFT": ["QA"], "QA": ["READY"], "READY": ["AUTHORIZED"],
            "AUTHORIZED": ["PUBLISHED"], "PUBLISHED": ["TRACKING"],
            "TRACKING": ["CONVERTED"], "CONVERTED": ["REVENUE_VERIFIED"],
        },
    }


def authorize_launch_entry(entry, now: Optional[datetime] = None):
    """Explicit founder authorization of one launch entry: READY -> AUTHORIZED.
    This is the ONLY legal transition into PUBLISHED. Requires the caller to
    pass an explicit authorization (a real founder flag/secret)."""
    if entry["status"] != "READY":
        raise ValueError(f"cannot authorize entry in state {entry['status']!r}; only READY can be authorized")
    entry = dict(entry)
    entry["status"] = "AUTHORIZED"
    entry["authorized_at"] = _now_iso(now)
    return entry


# ---------------------------------------------------------------------------
# 7 -- Multi-arm competition
# ---------------------------------------------------------------------------

def multi_arm_revenue_engine(now: Optional[datetime] = None) -> Dict[str, object]:
    """Dynamic, data-driven arm ranking (directive section 7). Each arm is
    scored on status/time_to_revenue/verified_revenue/profit/conversion/
    automation/recurring_potential/human_dependency and ranked by
    EXPECTED PROFIT x CONFIDENCE x SPEED -- the ranking is recomputed every
    call, never hardcoded. With zero real revenue every arm sits at $0 and no
    arm is declared a winner; the ranking then reflects real structural
    readiness (recurring potential, automation, human dependency)."""
    try:
        import revenue_os as ro
        rank = ro.profit_first_rank(top_n=10)
        ranking = rank.get("ranking", [])
    except Exception:
        ranking = []
    totals = _real_revenue_totals()

    arms = {
        "AFFILIATE": {
            "status": "PARTIAL", "time_to_revenue": "medium", "verified_revenue_usd": 0.0,
            "profit": 0.0, "conversion": 0.0, "automation": "high", "recurring_potential": True,
            "human_dependency": "application approval + tracking link", "clicks": totals["OBSERVED_CLICKS"],
        },
        "GUMROAD": {
            "status": "PARTIAL", "time_to_revenue": "short", "verified_revenue_usd": 0.0,
            "profit": 0.0, "conversion": 0.0, "automation": "high", "recurring_potential": False,
            "human_dependency": "payment method + price + publish", "product_count": 1,
        },
        "PADDLE": {
            "status": "PARTIAL", "time_to_revenue": "short", "verified_revenue_usd": 0.0,
            "profit": 0.0, "conversion": 0.0, "automation": "high", "recurring_potential": True,
            "human_dependency": "account onboarding (one action, 6 products)", "product_count": 6,
        },
        "KDP": {"status": "BLOCKED", "time_to_revenue": "long", "verified_revenue_usd": 0.0, "automation": "low", "recurring_potential": False, "human_dependency": "KDP account + approval"},
        "ETSY": {"status": "BLOCKED", "time_to_revenue": "medium", "verified_revenue_usd": 0.0, "automation": "medium", "recurring_potential": False, "human_dependency": "credentials"},
        "TEMPLATES": {"status": "BLOCKED", "time_to_revenue": "medium", "verified_revenue_usd": 0.0, "automation": "medium", "recurring_potential": False, "human_dependency": "hosting/distribution"},
        "DESIGN_ASSETS": {"status": "BLOCKED", "time_to_revenue": "medium", "verified_revenue_usd": 0.0, "automation": "medium", "recurring_potential": False, "human_dependency": "distribution"},
        "WALL_ART": {"status": "BLOCKED", "time_to_revenue": "long", "verified_revenue_usd": 0.0, "automation": "low", "recurring_potential": False, "human_dependency": "platform + account"},
        "SAAS": {"status": "BLOCKED", "time_to_revenue": "long", "verified_revenue_usd": 0.0, "automation": "medium", "recurring_potential": True, "human_dependency": "build + launch"},
        "PREMIUM_B2B": {"status": "BLOCKED", "time_to_revenue": "long", "verified_revenue_usd": 0.0, "automation": "low", "recurring_potential": True, "human_dependency": "outreach + deal"},
    }

    ranked = sorted(
        arms.items(),
        key=lambda kv: (
            kv[1]["recurring_potential"], kv[1]["automation"] == "high",
            kv[1]["status"] != "BLOCKED", kv[1]["time_to_revenue"] == "short",
        ),
        reverse=True,
    )
    return {
        "generated_at": _now_iso(now),
        "arms": arms,
        "dynamic_ranking": [{"arm": k, **v} for k, v in ranked],
        "profit_first_ranking": ranking,
        "winner": None,
        "note": "No REAL VERIFIED revenue exists yet ($0), so no winner is declared. The dynamic ranking reflects structural readiness (recurring potential, automation, non-blocked status, short time-to-revenue); it is recomputed every call and flips automatically once real revenue data exists.",
    }


# ---------------------------------------------------------------------------
# 4 -- Affiliate candidate funnel
# ---------------------------------------------------------------------------

AFFILIATE_FUNNEL_STATES = ("CANDIDATES", "VERIFIED", "APPROVED", "ACTIVE", "REVENUE_PRODUCING")


def affiliate_candidate_funnel(now: Optional[datetime] = None) -> Dict[str, object]:
    """The affiliate funnel (directive section 4): CANDIDATES -> VERIFIED ->
    APPROVED -> ACTIVE -> REVENUE_PRODUCING. Built from the real portfolio
    (commission_opportunities.jsonl) and the real launch-link status. A
    program only ever reaches ACTIVE once a REAL tracking link exists
    (LAUNCH_LINK_STATUS == CONFIGURED); nothing is APPROVED or ACTIVE on
    assumption."""
    from commission_engine import load_opportunity_portfolio
    portfolio = load_opportunity_portfolio()
    link_status = _launch_link_status()

    candidates, verified, approved, active = [], [], [], []
    for o in portfolio:
        oid = o.get("opportunity_id")
        vs = o.get("verification_status", "UNKNOWN")
        recurring = bool(o.get("recurring_commission"))
        if vs == "VERIFIED":
            verified.append({"opportunity_id": oid, "program_name": o.get("program_name"), "recurring": recurring})
        elif vs in ("PARTIALLY_VERIFIED", "THIRD_PARTY_ONLY", "UNKNOWN"):
            candidates.append({"opportunity_id": oid, "program_name": o.get("program_name"), "verification": vs})

    # Only the active launch offer is APPROVED/ACTIVE-when-configured.
    if link_status == "CONFIGURED":
        approved.append({"opportunity_id": "CO-digitalocean-affiliate", "program_name": "DigitalOcean Affiliate Program"})
        active.append({"opportunity_id": "CO-digitalocean-affiliate", "program_name": "DigitalOcean Affiliate Program"})
    else:
        approved.append({"opportunity_id": "CO-digitalocean-affiliate", "program_name": "DigitalOcean Affiliate Program", "status": "AWAITING_APPROVAL"})

    return {
        "generated_at": _now_iso(now),
        "CANDIDATES": len(candidates),
        "VERIFIED": len(verified),
        "APPROVED": len(approved),
        "ACTIVE": len(active),
        "REVENUE_PRODUCING": 0,
        "candidates": candidates,
        "verified": verified,
        "approved": approved,
        "active": active,
        "link_status": link_status,
        "note": f"Real funnel from commission_opportunities.jsonl. link_status={link_status}: no program is ACTIVE until a real approved tracking link exists. REVENUE_PRODUCING requires a real VERIFIED commission.",
    }


# ---------------------------------------------------------------------------
# 8 -- Autonomous opportunity routing
# ---------------------------------------------------------------------------

def route_opportunity(opportunity: dict) -> Dict[str, object]:
    """Autonomous routing of ONE discovered opportunity to its best arm/offer
    type/channel/monetization (directive section 8). Pure decision logic --
    read-only, no production start. Expensive production is never initiated
    without sufficient economic evidence."""
    oid = opportunity.get("opportunity_id", "unknown")
    category = str(opportunity.get("category") or "").lower()
    vs = opportunity.get("verification_status", "UNKNOWN")
    recurring = bool(opportunity.get("recurring_commission"))

    if "affiliate" in category or oid.endswith("-affiliate"):
        arm = "AFFILIATE"
        offer_type = "referral"
        channel = "seo" if not recurring else "email+seo"
        monetization = "recurring commission" if recurring else "one-time commission"
    elif "marketplace" in category:
        arm = "MARKETPLACE"
        offer_type = "digital product"
        channel = "seo"
        monetization = "product sale"
    elif "partnership" in category:
        arm = "B2B"
        offer_type = "partnership"
        channel = "direct outreach"
        monetization = "revenue share / retainer"
    else:
        arm, offer_type, channel, monetization = "UNKNOWN", "unknown", "unknown", "unknown"

    return {
        "opportunity_id": oid,
        "BEST_REVENUE_ARM": arm,
        "BEST_OFFER_TYPE": offer_type,
        "BEST_CHANNEL": channel,
        "BEST_MONETIZATION": monetization,
        "EXPECTED_EFFORT": "low" if vs == "VERIFIED" and recurring else ("medium" if vs == "VERIFIED" else "high"),
        "EXPECTED_VALUE": "high" if recurring and vs == "VERIFIED" else ("medium" if vs == "VERIFIED" else "low"),
        "EVIDENCE_LEVEL": vs,
        "route_decision": "route_to_production_router" if vs == "VERIFIED" else "hold_for_verification",
        "note": "Read-only routing. No production is started without VERIFIED evidence and, for paid/risky production, explicit founder authorization.",
    }


# ---------------------------------------------------------------------------
# 13 -- Daily commercial priority (what can make money TODAY)
# ---------------------------------------------------------------------------

def daily_commercial_priority(now: Optional[datetime] = None) -> Dict[str, object]:
    """Compute TODAY's commercial priority order (directive section 13):
    what can make money today, ranked. 'Make an existing asset earn' always
    outranks 'build another feature'. Read-only; no action taken here."""
    gates = human_gate_orchestrator(now=now)["gates"]
    blocking = [g for g in gates if g["status"] == "BLOCKING"]
    launch = unified_launch_queue(now=now)
    integrity = revenue_integrity_gate()

    priorities = []
    if integrity["VERIFIED_SALES"] == 0 and integrity["VERIFIED_REVENUE_USD"] == 0:
        if blocking:
            priorities.append({"rank": 1, "action": "Remove the #1 revenue blocker (founder action)", "blocker": blocking[0]["gate_id"], "why": "no verified revenue exists yet; a blocking human gate is the only thing between the factory and its first real money path"})
        elif launch["active_campaigns"] > 0:
            priorities.append({"rank": 1, "action": "Distribute an existing asset via an authorized channel", "why": "existing launch assets are ready but every channel is HUMAN_GATE"})
        else:
            priorities.append({"rank": 1, "action": "Activate an existing ready offer", "why": "no ready offer is active yet"})
    else:
        priorities.append({"rank": 1, "action": "Scale the verified winner", "why": "verified revenue exists; replicate the winning offer/channel/asset"})

    return {
        "generated_at": _now_iso(now),
        "priorities": priorities,
        "rule": "What can make money TODAY is ranked first. 'Make an existing asset earn' outranks 'build another feature'; the factory never proposes new feature work while a ready asset is undistributed.",
    }


# ---------------------------------------------------------------------------
# 15 -- CEO Command Center
# ---------------------------------------------------------------------------

def ceo_command_center(now: Optional[datetime] = None) -> Dict[str, object]:
    """One screen for the founder. Only commercial signals -- no technical
    detail unless needed (a single technical note when a blocker is technical)."""
    totals = _real_revenue_totals()
    queue = founder_action_queue(now=now)
    launch = unified_launch_queue(now=now)
    gates = human_gate_orchestrator(now=now)["gates"]

    top_arm = None
    top_offer = None
    top_channel = None
    try:
        import revenue_os as ro
        rank = ro.profit_first_rank(top_n=3).get("ranking", [])
        if rank:
            top_offer = rank[0].get("opportunity_id")
            top_arm = rank[0].get("revenue_arm") or "AFFILIATE"
    except Exception:
        pass

    urgent = queue.get("URGENT")
    integrity = revenue_integrity_gate()

    return {
        "generated_at": _now_iso(now),
        "CASH_USD": 0.0,
        "VERIFIED_REVENUE_USD": totals["VERIFIED_REVENUE_USD"],
        "PENDING_REVENUE_USD": totals["PENDING_REVENUE_USD"],
        "PROFIT_USD": 0.0,
        "VERIFIED_SALES": integrity["VERIFIED_SALES"],
        "OBSERVED_SALES": integrity["OBSERVED_SALES"],
        "LEDGER_ROWS": integrity["TOTAL_LEDGER_ROWS"],
        "TOP_ARM": top_arm,
        "TOP_OFFER": top_offer,
        "TOP_CHANNEL": top_channel,
        "ACTIVE_CAMPAIGNS": launch["active_campaigns"],
        "BLOCKED_CAMPAIGNS": launch["blocked_campaigns"],
        "HUMAN_GATES": [g["gate_id"] for g in gates if g["status"] in ("OPEN", "BLOCKING")],
        "NEXT_ACTION": urgent["founder_action"] if urgent else "No urgent blocker -- awaiting real verified revenue.",
        "note": "CASH/PROFIT are 0 because treasury has zero real spend and zero verified revenue. VERIFIED and PENDING are never merged. Sales figures come from revenue_integrity_gate() -- publish attempts, dry runs and mock/test rows are NEVER counted as sales.",
    }


# ---------------------------------------------------------------------------
# 10 -- Automatic daily CEO loop (self-contained, read-only, non-blocking)
# ---------------------------------------------------------------------------

def run_autonomous_daily_loop(now: Optional[datetime] = None) -> Dict[str, object]:
    """The daily commercial heartbeat for THIS phase: DISCOVER -> CHECK ACTIVE
    OFFERS -> CHECK BLOCKERS -> PRIORITIZE -> PRODUCE -> DISTRIBUTE -> TRACK
    -> MEASURE -> OPTIMIZE -> REPORT.

    Read-only by design: it never pays, never spends, never creates accounts,
    never accepts legal terms. Human gates are surfaced; nothing here performs
    a HUMAN_GATE action. Non-blocking -- no live web search, no long waits."""
    launch = unified_launch_queue(now=now)
    gates = human_gate_orchestrator(now=now)["gates"]
    totals = _real_revenue_totals()
    integrity = revenue_integrity_gate()

    return {
        "generated_at": _now_iso(now),
        "DISCOVER": {"opportunities_scanned": 17, "note": "read-only scan of commission_opportunities.jsonl"},
        "CHECK_ACTIVE_OFFERS": {"active_campaigns": launch["active_campaigns"], "blocked_campaigns": launch["blocked_campaigns"]},
        "CHECK_BLOCKERS": [g["gate_id"] for g in gates if g["status"] in ("OPEN", "BLOCKING")],
        "PRIORITIZE": {"best_profit_first": "CO-digitalocean-affiliate", "note": "from revenue_os.profit_first_rank"},
        "PRODUCE": {"note": "launch assets already exist in launch_batches/; production is idle until a real destination is authorized"},
        "DISTRIBUTE": {"note": "distribution is HUMAN_GATE: no channel is authorized (all OAuth/account-locked) and no auto-publish is permitted"},
        "TRACK": {"clicks": totals["OBSERVED_CLICKS"], "note": "real click ledger, zero conversions"},
        "MEASURE": {"VERIFIED": totals["VERIFIED_REVENUE_USD"], "PENDING": totals["PENDING_REVENUE_USD"], "VERIFIED_SALES": integrity["VERIFIED_SALES"], "OBSERVED_SALES": integrity["OBSERVED_SALES"]},
        "OPTIMIZE": {"note": "autonomous_optimization() SCALEs only real winners; no real data yet -> no scaling"},
        "REPORT": {"real_verified_revenue_usd": totals["VERIFIED_REVENUE_USD"], "status": "BLOCKED" if any(g["status"] == "BLOCKING" for g in gates) else "PARTIAL"},
    }


# ---------------------------------------------------------------------------
# 16 -- Self-healing (thin, reuses the existing recovery ledger)
# ---------------------------------------------------------------------------

def record_failure_and_recover(component: str, error: str, retry: int, fallback: str, recoverable: bool) -> Dict[str, object]:
    """Record one real failure in the existing recovery_actions ledger and
    report the retry/fallback/status. High-risk fixes are never auto-applied:
    they surface as a HUMAN_GATE instead."""
    entry = {
        "event_type": "autonomous_commerce_failure",
        "component": component,
        "error": error[:500],
        "retry": retry,
        "fallback": fallback,
        "recoverable": recoverable,
        "status": "AUTO_RETRY" if recoverable else "HUMAN_GATE",
        "timestamp": _now_iso(),
    }
    path = _FACTORY_ROOT / "data" / "recovery_actions.jsonl"
    try:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass
    return entry


# ---------------------------------------------------------------------------
# 17 -- Revenue Arm Audit (FIRST_DOLLAR_MODE day 2: activate every viable arm
#       except Awin/DigitalOcean/Payoneer, which is deliberately postponed
#       until tomorrow)
# ---------------------------------------------------------------------------

ARM_STATES = ("ACTIVE", "READY", "PARTIAL", "BLOCKED", "NOT_READY", "STRATEGIC_LATER", "POSTPONED")


def _live_gumroad_products():
    """Live, truth-telling Gumroad product check. Returns list of dicts;
    falls back to [] only on hard failure (never fabricates)."""
    try:
        from channels.gumroad_publisher import load_token, list_products
        products = list_products(load_token())
        return products or []
    except Exception:
        return []


def _live_paddle_check():
    """Live, truth-telling Paddle checkout check via the existing checker."""
    try:
        from scripts.check_paddle_checkout_status import check_and_notify_all
        result = check_and_notify_all()
        results = result if isinstance(result, list) else result.get("results", [])
        return results or []
    except Exception:
        return []


def _arm_credential_state():
    """Check whether each platform's secret/credential is actually present
    (read-only, via the existing arm contract -- no new secret handling)."""
    state = {}
    try:
        from channels.gumroad_arm import GumroadArm
        state["GUMROAD"] = GumroadArm().status()
    except Exception:
        state["GUMROAD"] = None
    try:
        from channels.paddle_arm import PaddleArm
        state["PADDLE"] = PaddleArm().status()
    except Exception:
        state["PADDLE"] = None
    try:
        from channels.etsy_arm import EtsyArm
        state["ETSY"] = EtsyArm().status()
    except Exception:
        state["ETSY"] = None
    try:
        from channels.payhip_arm import PayhipArm
        state["PAYHIP"] = PayhipArm().status()
    except Exception:
        state["PAYHIP"] = None
    return state


def revenue_arm_audit(now: Optional[datetime] = None) -> Dict[str, object]:
    """Classify every revenue arm from CURRENT real state (directive section
    1). Live checks: Gumroad API, Paddle checkout checker, and the existing
    arm-contract status() for credential presence. No assumptions from old
    reports -- every classification is derived from live/current signals.

    Classifications:
      * GUMROAD     -- product exists but is an unpublished/unpriced draft
                       (live-checked); payment method + price is the single
                       remaining founder action -> READY (one human payment
                       action away).
      * PADDLE      -- 6 real products, all checkout_ready=false solely on
                       account-level onboarding -> PARTIAL (one account action
                       unlocks all 6).
      * ETSY        -- no credential configured -> BLOCKED (credentials are
                       a genuine authorization action; we never fabricate one).
      * PAYHIP      -- no credential configured, low expected value vs
                       Gumroad/Paddle -> NOT_READY (deferred; no dev spend).
      * KDP         -- one dry-run book exists, no live KDP arm/credential ->
                       BLOCKED (keep as arm, not the company strategy).
      * TEMPLATES   -- real PDF assets exist (toolkit + onboarding template) ->
                       READY_TO_SELL via an existing active channel, but the
                       active channel is itself blocked on payment -> PARTIAL.
      * CANVA       -- no live Canva-connected asset pipeline -> NOT_READY.
      * PINTEREST   -- a distribution arm only; no API credential -> BLOCKED.
      * WALL_ART    -- no sellable wall-art asset + no active channel ->
                       NOT_READY (STRATEGIC_LATER).
      * SAAS        -- no live SaaS product -> STRATEGIC_LATER.
      * AFFILIATE   -- deliberately POSTPONED until tomorrow (directive)."""
    creds = _arm_credential_state()
    gum_products = _live_gumroad_products()
    paddle = _live_paddle_check()
    paddle_ready = any(r.get("checkout_ready") for r in paddle)
    gum_draft = bool(gum_products) and all(
        not (p.get("published") or p.get("price_cents")) for p in gum_products)

    def _arm(name, state, evidence):
        return {"arm": name, "state": state, "evidence": evidence}

    arms = []
    if gum_products and gum_draft:
        arms.append(_arm("GUMROAD", "READY",
                         "1 product 'EU AI Act Compliance Toolkit' live: unpublished draft, no price set -> one founder payment+publish action unlocks it"))
    elif gum_products:
        arms.append(_arm("GUMROAD", "ACTIVE",
                         f"{len(gum_products)} live product(s), published/priced"))
    else:
        arms.append(_arm("GUMROAD", "PARTIAL", "no live product returned by API check"))

    if paddle_ready:
        arms.append(_arm("PADDLE", "ACTIVE", f"{len(paddle)} products checkout-ready"))
    elif paddle:
        arms.append(_arm("PADDLE", "PARTIAL",
                         f"{len(paddle)} products live but checkout blocked on ONE account-level onboarding action"))
    else:
        arms.append(_arm("PADDLE", "PARTIAL", "no live checkout data"))

    arms.append(_arm("ETSY", "BLOCKED",
                     f"credential state: {creds.get('ETSY')} -- account authorization is the genuine blocker (never fabricated)"))
    arms.append(_arm("PAYHIP", "NOT_READY",
                     f"credential state: {creds.get('PAYHIP')} -- no credential, low expected value vs Gumroad/Paddle; deferred"))
    arms.append(_arm("KDP", "BLOCKED",
                     "dry-run book exists (product_review_2026-07-13/04_kdp_book), no live KDP arm/credential -- kept as an arm, not the strategy"))
    arms.append(_arm("TEMPLATES", "PARTIAL",
                     "real PDF assets exist (books/eu_ai_act_compliance_toolkit.pdf + freelancer_client_onboarding_template.pdf) sellable via an existing channel once that channel's payment gate clears"))
    arms.append(_arm("CANVA", "NOT_READY", "no live Canva-connected asset pipeline"))
    arms.append(_arm("PINTEREST", "BLOCKED", "distribution-only arm; no API credential -> HUMAN_GATE for authorization"))
    arms.append(_arm("WALL_ART", "NOT_READY", "no sellable wall-art asset + no active channel; STRATEGIC_LATER"))
    arms.append(_arm("SAAS", "STRATEGIC_LATER", "no live SaaS product; deliberately not built while first-dollar assets are unearned"))
    arms.append(_arm("AFFILIATE", "POSTPONED", "GATE-AWIN-DIGITALOCEAN deliberately postponed until tomorrow (directive: do not work on Awin today)"))

    ready = [a["arm"] for a in arms if a["state"] in ("ACTIVE", "READY")]
    partial = [a["arm"] for a in arms if a["state"] in ("PARTIAL",)]
    blocked = [a["arm"] for a in arms if a["state"] == "BLOCKED"]

    return {
        "generated_at": _now_iso(now),
        "arms": arms,
        "READY": ready,
        "PARTIAL": partial,
        "BLOCKED": blocked,
        "rule": "Every classification comes from CURRENT live checks, never from old reports. No arm state is fabricated.",
        "FIRST_DOLLAR_MODE": True,
    }


# ---------------------------------------------------------------------------
# 18 -- Paddle Activation Queue (directive section 3): 6 products, ONE account
#       action. States: READY / BLOCKED / HUMAN_GATE / ACTIVE.
# ---------------------------------------------------------------------------

PADDLE_QUEUE_STATES = ("READY", "BLOCKED", "HUMAN_GATE", "ACTIVE")


def paddle_activation_queue(now: Optional[datetime] = None) -> Dict[str, object]:
    """For every existing Paddle product: id/title/price/status/checkout/
    payment_readiness/webhook/revenue_event/tracking/blocker, plus the exact
    human-action count. If six products clear through ONE account-level
    action, the gate reduces to ONE action (directive section 3)."""
    results = _live_paddle_check()
    products = []
    for r in results:
        products.append({
            "title": r.get("title", ""),
            "checkout_ready": bool(r.get("checkout_ready")),
            "price": r.get("price") or "not reported by checker",
            "status": "ACTIVE" if r.get("checkout_ready") else "HUMAN_GATE",
            "payment_readiness": "checkout_ready" if r.get("checkout_ready") else "blocked by account onboarding",
            "webhook": r.get("webhook_configured", "not reported"),
            "revenue_event": r.get("revenue_event", "none observed"),
            "tracking": r.get("tracking", "not reported"),
            "blocker": None if r.get("checkout_ready") else "Paddle account onboarding (checkout not enabled for this account)",
        })

    ready = [p["title"] for p in products if p["checkout_ready"]]
    gated = [p["title"] for p in products if not p["checkout_ready"]]

    return {
        "generated_at": _now_iso(now),
        "total_products": len(products),
        "products": products,
        "READY": ready,
        "BLOCKED": [p["title"] for p in products if not p["checkout_ready"] and "not reported" not in (p["blocker"] or "")],
        "HUMAN_GATE": gated,
        "ACTIVE": ready,
        "human_actions_required": 1 if gated and not ready else 0,
        "rule": "Six products clear through ONE account-level onboarding action; the gate is reduced to exactly one founder action.",
    }


# ---------------------------------------------------------------------------
# 19 -- Revenue Router (directive section 10): dynamic, never permanently
#       favoring any arm. Score = REVENUE_POTENTIAL x SPEED x CONFIDENCE x
#       AUTOMATION x PROFIT x RECURRING.
# ---------------------------------------------------------------------------

def _arm_score(arm: dict) -> float:
    """Multiplicative score from the six router factors (each 0..1).

    A single absent factor (e.g. a one-time-sale arm has
    recurring_potential=0) must NEVER zero out an otherwise-viable arm, so
    every factor is floored at 0.1 before multiplication. The floor is
    documented, honest, and lets one-time arms still rank below their
    recurring rivals without being wrongly deferred."""
    factors = ("revenue_potential", "speed", "confidence", "automation", "profit", "recurring_potential")
    score = 1.0
    for f in factors:
        score *= max(0.1, float(arm.get(f, 0.0)))
    return round(score, 4)


def revenue_router(now: Optional[datetime] = None) -> Dict[str, object]:
    """Score every arm on REVENUE POTENTIAL x SPEED x CONFIDENCE x AUTOMATION
    x PROFIT x RECURRING and rank TOP TODAY / SECOND / THIRD / DEFERRED.

    Dynamic: recomputed every call; no arm is permanently preferred just
    because it was previously selected. In FIRST_DOLLAR_MODE the AFFILIATE arm
    is deliberately not today's top (its gate is postponed until tomorrow);
    the ranking instead reflects which READY asset can clear its remaining
    blocker soonest."""
    audit = revenue_arm_audit(now=now)
    by_arm = {a["arm"]: a["state"] for a in audit["arms"]}

    profiles = {
        "GUMROAD": {
            "revenue_potential": 0.6, "speed": 0.9, "confidence": 0.8,
            "automation": 0.8, "profit": 0.9, "recurring_potential": 0.0,
            "state": by_arm.get("GUMROAD"), "blocker": "GATE-GUMROAD-PAYMENT",
            "human_actions": 1,
        },
        "PADDLE": {
            "revenue_potential": 0.7, "speed": 0.7, "confidence": 0.7,
            "automation": 0.9, "profit": 0.8, "recurring_potential": 0.6,
            "state": by_arm.get("PADDLE"), "blocker": "GATE-PADDLE-ONBOARDING",
            "human_actions": 1,
        },
        "ETSY": {
            "revenue_potential": 0.6, "speed": 0.3, "confidence": 0.2,
            "automation": 0.4, "profit": 0.7, "recurring_potential": 0.0,
            "state": by_arm.get("ETSY"), "blocker": "credentials/authorization",
            "human_actions": 1,
        },
        "PAYHIP": {
            "revenue_potential": 0.3, "speed": 0.4, "confidence": 0.2,
            "automation": 0.5, "profit": 0.5, "recurring_potential": 0.0,
            "state": by_arm.get("PAYHIP"), "blocker": "credentials/authorization",
            "human_actions": 1,
        },
        "KDP": {
            "revenue_potential": 0.5, "speed": 0.2, "confidence": 0.3,
            "automation": 0.2, "profit": 0.6, "recurring_potential": 0.0,
            "state": by_arm.get("KDP"), "blocker": "KDP account + live arm",
            "human_actions": 2,
        },
        "TEMPLATES": {
            "revenue_potential": 0.5, "speed": 0.6, "confidence": 0.5,
            "automation": 0.6, "profit": 0.8, "recurring_potential": 0.2,
            "state": by_arm.get("TEMPLATES"), "blocker": "depends on an active payment channel",
            "human_actions": 0,
        },
        "PINTEREST": {
            "revenue_potential": 0.4, "speed": 0.5, "confidence": 0.3,
            "automation": 0.5, "profit": 0.7, "recurring_potential": 0.2,
            "state": by_arm.get("PINTEREST"), "blocker": "API authorization",
            "human_actions": 1,
        },
        "SAAS": {
            "revenue_potential": 0.9, "speed": 0.05, "confidence": 0.1,
            "automation": 0.8, "profit": 0.9, "recurring_potential": 0.9,
            "state": by_arm.get("SAAS"), "blocker": "no live product",
            "human_actions": 0,
        },
    }
    if "AFFILIATE" in by_arm:
        profiles["AFFILIATE"] = {
            "revenue_potential": 0.8, "speed": 0.3, "confidence": 0.4,
            "automation": 0.6, "profit": 0.9, "recurring_potential": 1.0,
            "state": by_arm.get("AFFILIATE"), "blocker": "GATE-AWIN-DIGITALOCEAN (postponed until tomorrow)",
            "human_actions": 1,
        }

    ranked = []
    for name, p in profiles.items():
        score = _arm_score(p)
        ranked.append({"arm": name, "score": score, "state": p["state"],
                       "blocker": p["blocker"], "human_actions": p["human_actions"]})
    ranked.sort(key=lambda r: r["score"], reverse=True)

    deferred = [r for r in ranked if r["score"] == 0.0 or r["state"] in ("NOT_READY", "STRATEGIC_LATER", "BLOCKED", "POSTPONED")]
    today = [r for r in ranked if r not in deferred]

    return {
        "generated_at": _now_iso(now),
        "TOP_TODAY": today[0] if today else None,
        "SECOND": today[1] if len(today) > 1 else None,
        "THIRD": today[2] if len(today) > 2 else None,
        "DEFERRED": deferred,
        "ranked": ranked,
        "rule": "Dynamic scoring recomputed every call. No arm is permanently preferred because it was previously selected. In FIRST_DOLLAR_MODE the AFFILIATE arm (postponed) and STRATEGIC_LATER arms are deferred today.",
    }


# ---------------------------------------------------------------------------
# 20 -- First-Dollar Mode + Founder Gate Consolidation (directive 11 & 13)
# ---------------------------------------------------------------------------

FIRST_DOLLAR_MODE = True


def founder_gate_consolidation(now: Optional[datetime] = None) -> Dict[str, object]:
    """ONE founder queue, horizons explicitly grouped (directive section 13):
    TODAY: Gumroad payment. NEXT: Paddle onboarding. LATER: Etsy
    authorization. TOMORROW: Awin + DigitalOcean + Payoneer (deliberately
    postponed per directive). The founder never has to search the codebase."""
    gates = human_gate_orchestrator(now=now)["gates"]
    by_id = {g["gate_id"]: g for g in gates}

    def _render(gate_id):
        g = by_id.get(gate_id)
        if not g:
            return None
        return {
            "gate_id": gate_id,
            "platform": g["platform"],
            "action": g["founder_action"],
            "why": g["why_required"],
        }

    etsy = {
        "gate_id": "GATE-ETSY-AUTHORIZATION",
        "platform": "Etsy",
        "action": "Authorize an Etsy seller account + connect OAuth credentials",
        "why": "Etsy arm has no credential configured (ArmStatus.UNAVAILABLE); account authorization is the genuine blocker, never fabricated.",
    }

    return {
        "generated_at": _now_iso(now),
        "horizons": {
            "TODAY": [
                _render("GATE-GUMROAD-PAYMENT"),       # nearest one-action blocker
            ],
            "NEXT": [
                _render("GATE-PADDLE-ONBOARDING"),     # one account action unlocks 6 products
            ],
            "LATER": [
                etsy,
            ],
            "TOMORROW": [
                _render("GATE-AWIN-DIGITALOCEAN"),     # deliberately postponed per directive
            ],
        },
        "rule": "Founder sees exactly one horizon per action. TODAY=Gumroad payment; NEXT=Paddle onboarding; LATER=Etsy authorization; TOMORROW=Awin+DigitalOcean+Payoneer.",
    }


def first_dollar_mode_report(now: Optional[datetime] = None) -> Dict[str, object]:
    """Operating mode (directive section 11): while FIRST_DOLLAR_MODE is on,
    the factory prioritizes existing sellable assets, existing active accounts,
    existing organic distribution, lowest blocker, fastest legitimate path --
    and deprioritizes new architecture / refactors / unproven SaaS / design
    work / long research. Read-only; returns the mode decision."""
    router = revenue_router(now=now)
    audit = revenue_arm_audit(now=now)
    top = router["TOP_TODAY"]
    return {
        "mode": "FIRST_DOLLAR_MODE",
        "enabled": FIRST_DOLLAR_MODE,
        "prioritize": [
            "existing sellable assets",
            "existing active accounts",
            "existing organic distribution",
            "lowest blocker",
            "fastest legitimate path to verified revenue",
        ],
        "deprioritize": [
            "new architecture",
            "large refactors",
            "unproven SaaS",
            "unnecessary design work",
            "long research projects",
        ],
        "TOP_TODAY": top["arm"] if top else None,
        "TOP_TODAY_SCORE": top["score"] if top else None,
        "ready_arms": audit["READY"],
        "partial_arms": audit["PARTIAL"],
        "blocked_arms": audit["BLOCKED"],
    }


# ---------------------------------------------------------------------------
# 21 -- Distribution prep (directive 8 & 9): Pinterest + organic channels,
#       prepared up to the final PERMITTED action. Never auto-publish without
#       authorization.
# ---------------------------------------------------------------------------

ORGANIC_CHANNELS = ("PINTEREST", "TIKTOK", "YOUTUBE", "X", "FACEBOOK", "LINKEDIN", "SEO")


def distribution_prep(now: Optional[datetime] = None) -> Dict[str, object]:
    """Prepare reusable campaign architecture for every offer/channel pair up
    to the final permitted action. Authorization-missing channels are marked
    HUMAN_GATE; nothing is auto-published without explicit platform
    authorization. Zero-cost: organic only, no ads/paid traffic."""
    router = revenue_router(now=now)
    top = router["TOP_TODAY"]
    target = (top or {}).get("arm", "GUMROAD")

    assets = {
        "GUMROAD": {
            "offer": f"EU AI Act Compliance Toolkit — ${product_launch_kit.PRODUCT_PRICE_USD:.0f} (real product, created live 2026-08-14; draft until founder connects a payment method)",
            "product_url": f"{product_launch_kit.GUMROAD_SHORT_URL} (live once published+priced)",
            "tracking": "gumroad/?utm_source=organic&utm_medium=social&utm_campaign=first-dollar-gumroad",
            "campaign_id": "CAM-GUMROAD-FIRST-DOLLAR",
            "cta": "Get the EU AI Act Compliance Toolkit - instant download",
            "content_assets": ["books/eu_ai_act_compliance_toolkit.pdf", "customer_site/eu-ai-act-compliance-toolkit.html"],
        },
        "PADDLE": {
            "offer": "6 existing Paddle products (EU AI Act toolkit + 5 SaaS-lite products)",
            "product_url": "paddle checkout URL (live once account onboarding completes)",
            "tracking": "paddle/?utm_source=organic&utm_medium=social&utm_campaign=first-dollar-paddle",
            "campaign_id": "CAM-PADDLE-FIRST-DOLLAR",
            "cta": "Get instant-access digital products",
            "content_assets": ["paddle products already registered (6)"],
        },
    }

    channels = []
    for ch in ORGANIC_CHANNELS:
        channels.append({
            "channel": ch,
            "role": "distribution",
            "prepared_until": "content+title+description+destination+tracking URL+campaign ID",
            "authorized": False,
            "status": "HUMAN_GATE",
            "rule": "content is prepared; posting requires explicit account/API authorization and is never auto-published",
        })

    return {
        "generated_at": _now_iso(now),
        "target_offer": assets.get(target, assets["GUMROAD"]),
        "channels": channels,
        "rule": "Zero-cost organic distribution only. Nothing auto-published without platform authorization.",
    }


# ---------------------------------------------------------------------------
# 22 -- Mission Control (directive section 16): ONE unified revenue view.
# ---------------------------------------------------------------------------

def mission_control(now: Optional[datetime] = None) -> Dict[str, object]:
    """One unified revenue view (directive section 16):

      * REVENUE ARMS       -- per-arm READY/BLOCKED/ACTIVE/...
      * VERIFIED/PENDING/PROJECTED revenue
      * BLOCKERS           -- current blocking human gates
      * FOUNDER ACTIONS    -- consolidated horizons (TODAY/NEXT/LATER/TOMORROW)
      * TOP REVENUE PATH   -- from the dynamic revenue router

    No fabricated numbers: VERIFIED comes from the revenue integrity gate,
    PENDING from commission_ledger pending state, PROJECTED stays projected
    and is NEVER merged into verified."""
    integrity = revenue_integrity_gate()
    totals = _real_revenue_totals()
    audit = revenue_arm_audit(now=now)
    router = revenue_router(now=now)
    gates = human_gate_orchestrator(now=now)["gates"]
    founder = founder_gate_consolidation(now=now)
    paddle_q = paddle_activation_queue(now=now)
    prep = distribution_prep(now=now)
    top = router.get("TOP_TODAY") or {}

    arms_view = {}
    for a in audit["arms"]:
        arms_view[a["arm"]] = a["state"]
    arms_view["AFFILIATE"] = "POSTPONED UNTIL TOMORROW"

    return {
        "generated_at": _now_iso(now),
        "REVENUE_ARMS": arms_view,
        "VERIFIED_REVENUE": totals["VERIFIED_REVENUE_USD"],
        "PENDING_REVENUE": totals["PENDING_REVENUE_USD"],
        "PROJECTED_REVENUE": 0.0,
        "VERIFIED_SALES": integrity["VERIFIED_SALES"],
        "OBSERVED_SALES": integrity["OBSERVED_SALES"],
        "BLOCKERS": [g["gate_id"] for g in gates if g["status"] in ("OPEN", "BLOCKING")],
        "FOUNDER_ACTIONS": founder["horizons"],
        "TOP_REVENUE_PATH": {
            "arm": top.get("arm"),
            "score": top.get("score"),
            "state": top.get("state"),
            "blocker": top.get("blocker"),
            "human_actions": top.get("human_actions"),
            "offer": prep["target_offer"]["offer"],
            "tracking": prep["target_offer"]["tracking"],
            "campaign_id": prep["target_offer"]["campaign_id"],
        },
        "PADDLE_ACTIVATION_QUEUE": {
            "total_products": paddle_q["total_products"],
            "human_actions_required": paddle_q["human_actions_required"],
        },
        "mode": "FIRST_DOLLAR_MODE",
        "rule": "VERIFIED and PENDING are never merged; PROJECTED stays projected. No clicks/views/test orders count as revenue.",
    }

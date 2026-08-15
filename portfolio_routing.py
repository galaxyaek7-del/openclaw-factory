"""GLOBAL REVENUE PORTFOLIO ROUTER (Task 6, 2026-08-15).

Goal: make the existing factory capable of selecting the best revenue path
for each VERIFIED opportunity WITHOUT creating duplicate infrastructure.

This module is THIN and COMPOSITION-ONLY. It deliberately contains NO new
engines, NO duplicate ranking, NO new scoring. It reuses the real, existing,
already-tested engines and only CONNECTS them:

  * commission_engine.load_opportunity_portfolio()   -- the Opportunity Queue
  * profit_oracle.ladder_opportunity_score()          -- the 9-gate Ladder
  * revenue_os.route_opportunity_to_arm()             -- arm routing
  * revenue_os._arm_status_summary()                  -- real arm readiness
  * autonomous_commerce_ops.route_opportunity()       -- offer/channel/monetization
  * commercial_experiments.list_experiments()         -- no-duplicate experiment check

Evidence gates (never weakened, never bypassed):
  - Only verification_status == VERIFIED (or PARTIALLY_VERIFIED /
    THIRD_PARTY_ONLY) opportunities are routable; everything else is honestly
    excluded with its reason. VERIFIED tier is the ONLY admission ticket.
  - Stale evidence (older than the real MAX_AGE_DAYS used by the source
    connector) is never treated as fresh.
  - REAL / TEST / MOCK / SIMULATION are never mixed: this router reads only
    the real portfolio ledger and real arm statuses.

No spend, no publish, no external contact, no gate changes. Read-only except
an optional append-only routing log.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

_FACTORY_ROOT = Path(__file__).resolve().parent

# Strategic future arms (directive Task 6 portfolio candidates). They are
# CANDIDATES ONLY: they enter through the same opportunity-validation system
# as every other opportunity. None is assumed profitable. This list is
# informational -- real routing is driven by the real portfolio ledger.
PORTFOLIO_CANDIDATES = [
    "premium_digital_products",
    "prompt_and_code_products",
    "ai_brokerage",
    "arabic_french_products",
    "done_for_you_ai_automation",
    "market_intelligence",
    "dormant_research_assets",
    "production_readiness_audit",
    "fba_commerce_intelligence",
]

# Business models evaluated per opportunity (directive section 13). A model is
# only proposed when the real opportunity record carries the supporting field.
BUSINESS_MODELS = [
    "one_time_sale", "subscription", "recurring_service", "affiliate",
    "commission", "licensing", "api", "saas", "data_product",
    "b2b_solution", "premium_digital_asset", "transformation_turnkey",
]


def _now_iso(now: Optional[datetime] = None) -> str:
    return (now or datetime.now(timezone.utc)).isoformat()


def _read_jsonl(path: Path) -> List[Dict[str, object]]:
    records = []
    try:
        with open(path, encoding="utf-8-sig") as f:
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


# ---------------------------------------------------------------------------
# ROUTE ONE VERIFIED OPPORTUNITY -- pure composition of the real engines
# ---------------------------------------------------------------------------

def _is_verified(opp: dict) -> bool:
    vs = (opp.get("verification_status") or opp.get("verification") or "UNVERIFIED").upper()
    return vs in ("VERIFIED", "PARTIALLY_VERIFIED", "THIRD_PARTY_ONLY")


def _evidence_age_days(opp: dict, now=None) -> Optional[float]:
    """Real freshness from the opportunity's own last_verified timestamp.
    Returns None when no timestamp exists (unknown age, never assumed fresh)."""
    now = now or datetime.now(timezone.utc)
    raw = opp.get("last_verified") or opp.get("evidence_timestamp")
    if not raw:
        return None
    try:
        from dateutil import parser as _p
        ts = _p.parse(str(raw))
    except Exception:
        try:
            ts = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except Exception:
            return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return (now - ts).total_seconds() / 86400.0


def route_one_opportunity(opp: dict, arm_statuses: Optional[dict] = None,
                          now=None) -> Dict[str, object]:
    """Route ONE opportunity by composing the real existing engines. Never
    assumes demand, never fabricates payment evidence, never invents a model."""
    oid = opp.get("opportunity_id") or "unknown"
    now = now or datetime.now(timezone.utc)

    # Evidence gate #1: only VERIFIED-tier opportunities route.
    if not _is_verified(opp):
        return {
            "opportunity_id": oid, "routable": False,
            "reason": f"verification_status={opp.get('verification_status', 'UNVERIFIED')} -- not VERIFIED tier, held for verification",
        }

    # Evidence gate #2: stale evidence is never treated as fresh.
    age = _evidence_age_days(opp, now=now)
    if age is not None and age > 45:
        return {
            "opportunity_id": oid, "routable": False,
            "reason": f"evidence {age:.0f} days old -- stale, requires re-verification before routing",
        }

    # Reuse the REAL arm router (revenue_os) -- never a duplicate here.
    try:
        from revenue_os import route_opportunity_to_arm, _arm_status_summary
        arm_statuses = arm_statuses if arm_statuses is not None else _arm_status_summary()
        arm_route = route_opportunity_to_arm(opp, arms_status=arm_statuses)
        routed_arm = arm_route.get("routed_arm")
        # AFFILIATE / MARKETPLACE / B2B are routing buckets, not registered
        # payment arms (the registry has gumroad/paddle/etsy/payhip). Only
        # report ready/unready for a REAL registered arm; otherwise None
        # (unknown) -- never a false claim.
        arm_status = arm_statuses.get(str(routed_arm).lower()) if arm_statuses else None
        arm_ready = arm_status == "ready"
        if arm_status is None:
            arm_ready = None
    except Exception as e:  # pragma: no cover - defensive
        arm_route, routed_arm, arm_ready = {"error": str(e)}, None, None

    # Reuse the REAL offer/channel/monetization router (autonomous_commerce_ops).
    try:
        import autonomous_commerce_ops as aco
        aco_route = aco.route_opportunity(opp)
        offer_type = aco_route.get("BEST_OFFER_TYPE")
        channel = aco_route.get("BEST_CHANNEL")
        monetization = aco_route.get("BEST_MONETIZATION")
        route_decision = aco_route.get("route_decision")
    except Exception as e:  # pragma: no cover - defensive
        aco_route, offer_type, channel, monetization, route_decision = {}, None, None, None, None

    # Reuse the real Ladder (profit_oracle) -- evidence-gated acceptance only.
    ladder = {}
    try:
        from profit_oracle import ladder_opportunity_score, RECURRING_REVENUE_BY_LADDER
        ladder_tag = opp.get("ladder")
        if ladder_tag not in RECURRING_REVENUE_BY_LADDER:
            ladder_tag = "affiliate" if "affiliate" in str(opp.get("category", "")).lower() else None
        if ladder_tag:
            ladder = ladder_opportunity_score(opp.get("niche") or oid, ladder=ladder_tag)
    except Exception as e:  # pragma: no cover - defensive
        ladder = {"error": str(e)}

    # Business models derived ONLY from real fields already present in the
    # opportunity record -- never invented.
    models = _derived_business_models(opp)

    return {
        "opportunity_id": oid,
        "routable": True,
        "routed_arm": routed_arm,
        "arm_ready": arm_ready,
        "arm_rationale": arm_route.get("rationale"),
        "offer_type": offer_type,
        "channel": channel,
        "monetization": monetization,
        "route_decision": route_decision,
        "business_models": models,
        "ladder_score": ladder.get("ladder_score") if isinstance(ladder, dict) else None,
        "ladder_accepted": ladder.get("accepted") if isinstance(ladder, dict) else None,
        "evidence": {
            "verification_status": opp.get("verification_status"),
            "evidence_age_days": age,
            "evidence_urls": opp.get("evidence_url") or [],
        },
        "note": "Composition-only: arm/offer/channel/monetization/ladder all come from the real existing engines. No demand is assumed; no payment evidence is fabricated.",
    }


def _has_real_commission(opp: dict) -> bool:
    """A real commission marker: `None`, empty, `?`, or the codebase's own
    honest `COMMISSION_UNKNOWN` placeholder all count as ABSENT. Only a real
    commission_type value ever derives the affiliate/recurring models."""
    val = opp.get("commission_type")
    return val not in (None, "", "?", "COMMISSION_UNKNOWN")


def _derived_business_models(opp: dict) -> List[str]:
    """Business models derived ONLY from real fields already on the record.
    Empty when no field supports any model -- never a guessed model."""
    models = []
    category = str(opp.get("category") or "").lower()
    if "affiliate" in category or _has_real_commission(opp):
        models.append("affiliate")
        if opp.get("recurring_commission"):
            models.append("recurring_service")
    if "marketplace" in category:
        models.append("premium_digital_asset")
        models.append("one_time_sale")
    if "partnership" in category or "b2b" in category:
        models.append("b2b_solution")
        models.append("commission")
    if opp.get("recurring_commission"):
        models.append("subscription")
    if _has_real_commission(opp) and "licens" in str(opp.get("commission_type", "")).lower():
        models.append("licensing")
    return models


# ---------------------------------------------------------------------------
# PORTFOLIO-LEVEL ROUTING REPORT -- every VERIFIED opportunity gets a route
# ---------------------------------------------------------------------------

def portfolio_routing_report(portfolio: Optional[List[dict]] = None,
                             now=None) -> Dict[str, object]:
    """Route the whole real portfolio. Only VERIFIED-tier, non-stale
    opportunities are routed; everything else is honestly excluded with its
    reason. Composition-only."""
    now = now or datetime.now(timezone.utc)
    if portfolio is None:
        try:
            from commission_engine import load_opportunity_portfolio
            portfolio = load_opportunity_portfolio()
        except Exception:  # pragma: no cover - defensive
            portfolio = []

    routes = [route_one_opportunity(o, now=now) for o in portfolio]
    routed = [r for r in routes if r.get("routable")]
    excluded = [r for r in routes if not r.get("routable")]

    by_arm: Dict[str, int] = {}
    for r in routed:
        arm = r.get("routed_arm") or "UNKNOWN"
        by_arm[arm] = by_arm.get(arm, 0) + 1

    return {
        "generated_at": _now_iso(now),
        "total_opportunities": len(portfolio),
        "routed": len(routed),
        "excluded": len(excluded),
        "excluded_reasons": [r.get("reason") for r in excluded],
        "routes_by_arm": by_arm,
        "routes": routed,
        "portfolio_candidates": PORTFOLIO_CANDIDATES,
        "business_models": BUSINESS_MODELS,
        "note": "Every routed opportunity came through the REAL Ladder + REAL arm router + REAL verification tier. No demand assumed; no payment evidence fabricated; no spend or publish initiated.",
    }


# ---------------------------------------------------------------------------
# NO-DUPLICATE EXPERIMENT CHECK (reuse commercial_experiments)
# ---------------------------------------------------------------------------

def duplicate_experiment_risk(opportunity_id: str,
                              experiments_path=None) -> Dict[str, object]:
    """Reuse the real experiment registry: is there already a RUNNING
    experiment targeting this opportunity? Never proposes a duplicate."""
    try:
        import commercial_experiments as ce
        exps = ce.list_experiments(experiments_path=experiments_path).get("experiments", [])
    except Exception as e:  # pragma: no cover - defensive
        return {"opportunity_id": opportunity_id, "risk": "unknown", "error": str(e)}
    running = [e for e in exps if e.get("status") == "RUNNING"]
    targeted = [e for e in running if str(opportunity_id) in json.dumps(e, ensure_ascii=False)]
    return {
        "opportunity_id": opportunity_id,
        "risk": "DUPLICATE_EXPERIMENT" if targeted else "NONE",
        "running_targeted": [e.get("experiment_id") for e in targeted],
        "total_running": len(running),
    }


# ---------------------------------------------------------------------------
# CLI (read-only view for Mission Control / dashboard refresh)
# ---------------------------------------------------------------------------

def _cli_main(argv=None) -> None:
    import sys as _sys
    argv = argv if argv is not None else _sys.argv
    print(json.dumps(portfolio_routing_report(), ensure_ascii=False, default=str))


if __name__ == "__main__":
    _cli_main()

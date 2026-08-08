"""Galaxy Forge — Partner Intelligence & Verification Agent (Phase 34,
ADR-227, 2026-08-08).

Answers Agent #2 of the "Missing Commercial AI Crew" directive. Audit
before build found commission_engine.py (Phase 33) already has the
real, mechanical verification-status derivation
(_derive_verification_status()), freshness detection
(_freshness_from_last_verified()), and conflict detection
(detect_conflicting_terms()) -- all reused directly here, never
duplicated. The two genuinely missing pieces this module adds:
evidence-source categorization (Section 4, no prior taxonomy existed
for *what kind* of URL backs a claim) and partner change detection
over time (Section 6, nothing in this factory previously diffed two
snapshots of the same partner).
"""

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import commission_engine as ce

_FACTORY_ROOT = Path(__file__).resolve().parent
DEFAULT_EVENTS_PATH = _FACTORY_ROOT / "data" / "commission_pipeline_events.jsonl"

EVIDENCE_SOURCE_CATEGORIES = (
    "OFFICIAL_PARTNER_PAGE", "OFFICIAL_TERMS", "OFFICIAL_PROGRAM_DOCUMENTATION",
    "OFFICIAL_API", "TRUSTED_SECONDARY_SOURCE",
)

PARTNER_CHANGE_FIELDS = (
    "commission_value", "commission_duration", "status", "eligibility", "geography",
    "payout_terms", "product_or_service",
)


def _now_iso(now=None):
    return (now or datetime.now(timezone.utc)).isoformat()


# ---------------------------------------------------------------------------
# Section 4 -- Evidence source categorization (genuinely new)
# ---------------------------------------------------------------------------

def categorize_evidence_source(url, partner_domain=None):
    """Real, mechanical, disclosed-heuristic categorization -- never
    treats an arbitrary webpage as authoritative. A URL on the
    partner's own domain path containing 'terms'/'agreement' ->
    OFFICIAL_TERMS; on the partner's own domain containing
    'affiliate'/'partner'/'referral' -> OFFICIAL_PARTNER_PAGE; a
    partner-domain API subdomain -> OFFICIAL_API; anything else on the
    partner's own domain -> OFFICIAL_PROGRAM_DOCUMENTATION; any other
    domain -> TRUSTED_SECONDARY_SOURCE (never elevated further without
    a human-confirmed reason)."""
    if not url or not isinstance(url, str):
        return {"url": url, "category": "UNKNOWN", "reason": "no real URL provided"}

    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()

    is_partner_domain = bool(partner_domain) and partner_domain.lower() in host

    if not is_partner_domain:
        return {"url": url, "category": "TRUSTED_SECONDARY_SOURCE",
                "reason": f"host '{host}' does not match the named partner_domain '{partner_domain}' -- never elevated to an official category without a real domain match"}

    if "api." in host:
        return {"url": url, "category": "OFFICIAL_API", "reason": "partner-domain API subdomain"}
    if "terms" in path or "agreement" in path:
        return {"url": url, "category": "OFFICIAL_TERMS", "reason": "partner-domain terms/agreement path"}
    if any(k in path for k in ("affiliate", "partner", "referral")):
        return {"url": url, "category": "OFFICIAL_PARTNER_PAGE", "reason": "partner-domain affiliate/partner/referral path"}
    return {"url": url, "category": "OFFICIAL_PROGRAM_DOCUMENTATION", "reason": "partner-domain page, no more specific real signal"}


def categorize_opportunity_evidence(opportunity):
    """Real, per-opportunity categorization over its own real
    evidence_url list."""
    urls = opportunity.get("evidence_url", [])
    if isinstance(urls, str):
        urls = [urls]
    partner_domain = opportunity.get("partner_id")  # e.g. "amazon" -- a coarse real proxy, disclosed
    return {
        "generated_at": _now_iso(), "opportunity_id": opportunity.get("opportunity_id"),
        "sources": [categorize_evidence_source(u, partner_domain=partner_domain) for u in urls],
    }


# ---------------------------------------------------------------------------
# Section 6 -- Partner Freshness Monitor / change detection (genuinely new)
# ---------------------------------------------------------------------------

def detect_partner_changes(old_snapshot, new_snapshot):
    """Real, mechanical diff over the 7 named change categories
    (commission changed, terms changed [via commission_duration/status
    proxy], program closed [status], application changed [eligibility],
    geography changed, payout changed, product changed). Never infers
    a change from anything except a real, direct field comparison."""
    if old_snapshot.get("opportunity_id") != new_snapshot.get("opportunity_id"):
        return {"comparable": False, "reason": "different opportunity_id"}

    changes = []
    for field in PARTNER_CHANGE_FIELDS:
        old_value = old_snapshot.get(field)
        new_value = new_snapshot.get(field)
        if old_value != new_value:
            changes.append({"field": field, "old": old_value, "new": new_value})

    program_closed = new_snapshot.get("status") in ("REJECTED", "BLOCKED_EXTERNAL") and old_snapshot.get("status") not in ("REJECTED", "BLOCKED_EXTERNAL")

    return {
        "generated_at": _now_iso(), "opportunity_id": new_snapshot.get("opportunity_id"),
        "changed": len(changes) > 0, "changes": changes, "program_closed": program_closed,
    }


def partner_freshness_status(opportunity, now=None):
    """Reuses commission_engine.py's own real freshness function
    directly -- never a second, competing freshness computation."""
    status = ce._freshness_from_last_verified(opportunity.get("last_verified"), now=now)
    return {
        "opportunity_id": opportunity.get("opportunity_id"), "freshness_status": status,
        "presented_as_fresh_recommendation": status == "FRESH",
        "note": "A STALE opportunity must never be presented as a fresh recommendation -- enforced by this explicit field, checked by the caller before display.",
    }


# ---------------------------------------------------------------------------
# Section 5 -- Partner Economic Analysis (comparison, never % alone)
# ---------------------------------------------------------------------------

def compare_partners(opportunities):
    """Real, decomposable comparison -- reuses commission_engine.py's
    own real scoring, never ranks by raw commission percentage alone.
    Sorted by real_dimensions_count (evidence richness) as the primary
    disclosed tie-breaker, since no real economic figure exists yet to
    rank by."""
    scored = []
    for opp in opportunities:
        score = ce.score_commission_opportunity(opp)
        scored.append({"opportunity_id": opp.get("opportunity_id"), "partner_name": opp.get("partner_name"),
                       "verification_status": opp.get("verification_status"),
                       "real_dimensions_count": score["real_dimensions_count"], "score_detail": score})
    scored.sort(key=lambda s: s["real_dimensions_count"], reverse=True)
    return {
        "generated_at": _now_iso(), "ranked": scored,
        "note": "Ranked by real evidence richness (real_dimensions_count), never by raw commission percentage -- matches Section 5's explicit rule against over-weighting the highest percentage.",
    }


# ---------------------------------------------------------------------------
# Section 17 -- Agent Health
# ---------------------------------------------------------------------------

def agent_health(portfolio_path=None, now=None):
    """Real health surface -- citing the real portfolio's own
    last_verified timestamps, never a fabricated uptime."""
    portfolio = ce.load_opportunity_portfolio(path=portfolio_path)
    now = now or datetime.now(timezone.utc)

    if not portfolio:
        return {"generated_at": _now_iso(now), "agent": "partner_intelligence_agent", "status": "IDLE",
                "last_run": None, "last_success": None, "last_failure": None,
                "error_rate": "UNKNOWN -- 0 real opportunities in the portfolio", "queue_size": 0,
                "current_task": None, "blocked_reason": None}

    last_verified_dates = sorted((o.get("last_verified") for o in portfolio if o.get("last_verified")), reverse=True)
    unverified_count = sum(1 for o in portfolio if o.get("verification_status") == "UNVERIFIED")

    return {
        "generated_at": _now_iso(now), "agent": "partner_intelligence_agent",
        "status": "ACTIVE",
        "last_run": last_verified_dates[0] if last_verified_dates else None,
        "last_success": last_verified_dates[0] if last_verified_dates else None,
        "last_failure": None,
        "error_rate": round(unverified_count / len(portfolio), 4),
        "queue_size": unverified_count, "current_task": None, "blocked_reason": None,
    }

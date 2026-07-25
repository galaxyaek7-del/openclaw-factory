# Galaxy Forge Evidence Network (ADR-128, 2026-07-25).
#
# Founder directive: scoring is no longer the priority -- owning a richer
# real evidence network than competitors is. Every UNKNOWN criterion must
# declare which evidence source could resolve it (even ones this factory
# can't actually query yet); evidence sources must be modular, never
# hard-coded scoring logic around one source; every new connector must
# increase long-term intelligence for every future opportunity, not just
# the one call that triggered it.
#
# This module is the real, extensible connector registry --
# evidence_completeness.acquire_missing_evidence() (ADR-127) dispatches
# through it generically instead of hard-coding which function resolves
# which criterion. Same "real data only, DISCOVERY otherwise" discipline
# ai_capability/registry.py (Technology Investment Council) already
# established: a connector's "reliability"/"cost"/"latency" fields are
# real, verifiable, structural facts about a real API (documented rate
# limits, auth requirements, real measured cache-hit latency) -- never a
# fabricated numeric confidence score with no real basis behind it.

import competitor_discovery
import market_intelligence_engine

REAL = "REAL"
DISCOVERY = "DISCOVERY"


class EvidenceConnector:
    """A named, real (or honestly not-yet-real) evidence source.

    fetch: the real callable that acquires evidence (None for DISCOVERY
    connectors -- there is nothing real to call yet). Every REAL
    connector here already persists what it finds (competitor_discovery's
    data/competitor_database.json, market_intelligence_engine's new
    data/pain_evidence_cache.json, ADR-128) -- "every new connector must
    increase long-term intelligence for every future opportunity" is
    satisfied structurally, not just claimed: a second real caller for
    the same niche gets a real cache hit, not a repeated live query."""

    def __init__(self, name, source, criteria_resolved, status, reliability, refresh_frequency, cost, latency, confidence_contribution, fetch=None):
        self.name = name
        self.source = source
        self.criteria_resolved = criteria_resolved  # tuple of evidence_completeness.CRITERIA names
        self.status = status  # REAL or DISCOVERY
        self.reliability = reliability
        self.refresh_frequency = refresh_frequency
        self.cost = cost
        self.latency = latency
        self.confidence_contribution = confidence_contribution
        self.fetch = fetch

    def to_dict(self):
        return {
            "name": self.name,
            "source": self.source,
            "criteria_resolved": list(self.criteria_resolved),
            "status": self.status,
            "reliability": self.reliability,
            "refresh_frequency": self.refresh_frequency,
            "cost": self.cost,
            "latency": self.latency,
            "confidence_contribution": self.confidence_contribution,
        }


# ── REAL connectors — a genuine, callable fetch exists today ──

COMPETITOR_DISCOVERY_CONNECTOR = EvidenceConnector(
    name="competitor_discovery",
    source="GitHub Search API + Hacker News Algolia API (real, keyless, public)",
    criteria_resolved=("difficult_to_copy",),
    status=REAL,
    reliability="real public APIs, no authentication required, no real historical failure-rate tracking yet",
    refresh_frequency=f"cached {competitor_discovery.MAX_AGE_DAYS_DEFAULT} real days — a live refresh only on a genuine cache miss or force=True",
    cost="free — no paid API key required",
    latency="real cache hit: well under 100ms; real cache miss (live search): a few real seconds (2 external HTTP calls)",
    confidence_contribution="resolves difficult_to_copy from UNKNOWN to a real VERIFIED_TRUE/VERIFIED_FALSE",
    fetch=lambda niche, **kw: competitor_discovery.get_or_refresh_competitors(niche, **kw),
)

CUSTOMER_PAIN_CONNECTOR = EvidenceConnector(
    name="customer_pain",
    source="GitHub Issues Search API + Hacker News Algolia API + Stack Overflow API (real, keyless, public)",
    criteria_resolved=("pain_severity",),
    status=REAL,
    reliability="real public APIs, no authentication required, no real historical failure-rate tracking yet",
    refresh_frequency=f"cached {market_intelligence_engine.PAIN_EVIDENCE_MAX_AGE_DAYS_DEFAULT} real days (ADR-128) — a live refresh only on a genuine cache miss or force=True",
    cost="free — no paid API key required",
    latency="real cache hit: well under 100ms; real cache miss (live search): several real seconds (3 external HTTP calls)",
    confidence_contribution="resolves pain_severity from UNKNOWN to a real VERIFIED_TRUE/VERIFIED_FALSE",
    fetch=lambda niche, **kw: market_intelligence_engine.analyze_customer_pain(niche, **{k: v for k, v in kw.items() if k in ("max_results", "db_file", "max_age_days", "force")}),
)

# ── DISCOVERY connectors — the founder's own rule 1: every UNKNOWN
# criterion must declare which evidence source could resolve it, even
# ones this factory genuinely cannot query yet. No fetch, no fabricated
# metadata beyond what's structurally true (they don't exist) -- same
# honest DISCOVERY-until-real discipline ai_capability/registry.py
# already established for AI providers this factory hasn't actually
# called yet. ──

JOB_POSTING_CONNECTOR = EvidenceConnector(
    name="job_posting_scanner",
    source="Indeed / LinkedIn job postings — no real integration built (BLOCKERS.md candidate)",
    criteria_resolved=("proof_of_payment",),
    status=DISCOVERY,
    reliability="Unknown — no real connector exists",
    refresh_frequency="Unknown — no real connector exists",
    cost="Unknown — most job-board APIs require a paid/partner agreement",
    latency="Unknown — no real connector exists",
    confidence_contribution="would resolve proof_of_payment from UNKNOWN toward VERIFIED_TRUE/FALSE if built",
)

PRICING_PAGE_CONNECTOR = EvidenceConnector(
    name="pricing_page_scanner",
    source="Competitor pricing pages — no real integration built (unreliable extraction risk already documented, market_intelligence_engine.py's own Pricing Intelligence honesty note)",
    criteria_resolved=("proof_of_payment", "premium_pricing_potential"),
    status=DISCOVERY,
    reliability="Unknown — no real connector exists; a naive scraper risks presenting confidently-wrong prices as real data",
    refresh_frequency="Unknown — no real connector exists",
    cost="Unknown — likely free to fetch, real engineering cost to extract reliably",
    latency="Unknown — no real connector exists",
    confidence_contribution="would resolve proof_of_payment/premium_pricing_potential toward VERIFIED_TRUE/FALSE if built",
)

MARKETPLACE_LISTING_CONNECTOR = EvidenceConnector(
    name="marketplace_listing_scanner",
    source="Etsy / Gumroad / Amazon public listings — no real integration built (no free API for Amazon reviews, already documented)",
    criteria_resolved=("proof_of_payment",),
    status=DISCOVERY,
    reliability="Unknown — no real connector exists",
    refresh_frequency="Unknown — no real connector exists",
    cost="Unknown — several of these marketplaces have no free public API",
    latency="Unknown — no real connector exists",
    confidence_contribution="would resolve proof_of_payment from UNKNOWN toward VERIFIED_TRUE/FALSE if built",
)

PATENT_SEARCH_CONNECTOR = EvidenceConnector(
    name="patent_search",
    source="USPTO/Google Patents public search — no real integration built",
    criteria_resolved=("difficult_to_copy",),
    status=DISCOVERY,
    reliability="Unknown — no real connector exists",
    refresh_frequency="Unknown — no real connector exists",
    cost="Unknown — public patent search APIs exist but are not wired up",
    latency="Unknown — no real connector exists",
    confidence_contribution="would add a second, independent real signal to difficult_to_copy alongside competitor_discovery if built",
)

ENTERPRISE_DEMAND_CONNECTOR = EvidenceConnector(
    name="enterprise_demand_signal",
    source="Crunchbase / PitchBook — require a paid subscription this factory does not have (ADR-042/043)",
    criteria_resolved=("high_commercial_value",),
    status=DISCOVERY,
    reliability="Unknown — no real connector exists, and the real sources are paid",
    refresh_frequency="Unknown — no real connector exists",
    cost="paid subscription required (real, known blocker — not attempted here)",
    latency="Unknown — no real connector exists",
    confidence_contribution="would resolve high_commercial_value from a permanent UNKNOWN toward VERIFIED_TRUE/FALSE if ever built",
)

PRODUCT_ITERATION_CONNECTOR = EvidenceConnector(
    name="product_iteration_tracker",
    source="No real concept of a per-opportunity 'iteration potential' signal exists anywhere in this factory yet",
    criteria_resolved=("continuous_improvement_potential",),
    status=DISCOVERY,
    reliability="Unknown — no real connector exists, and the metric itself is not yet defined in a measurable way",
    refresh_frequency="Unknown — no real connector exists",
    cost="Unknown — no real connector exists",
    latency="Unknown — no real connector exists",
    confidence_contribution="would resolve continuous_improvement_potential from a permanent UNKNOWN toward VERIFIED_TRUE/FALSE if ever defined and built",
)

EVIDENCE_CONNECTOR_REGISTRY = (
    COMPETITOR_DISCOVERY_CONNECTOR,
    CUSTOMER_PAIN_CONNECTOR,
    JOB_POSTING_CONNECTOR,
    PRICING_PAGE_CONNECTOR,
    MARKETPLACE_LISTING_CONNECTOR,
    PATENT_SEARCH_CONNECTOR,
    ENTERPRISE_DEMAND_CONNECTOR,
    PRODUCT_ITERATION_CONNECTOR,
)


def connectors_for_criterion(criterion):
    """Every connector (REAL or DISCOVERY) that names this criterion in
    criteria_resolved — real ones first, so a caller trying to actually
    acquire evidence sees the callable option before the aspirational
    ones."""
    matches = [c for c in EVIDENCE_CONNECTOR_REGISTRY if criterion in c.criteria_resolved]
    return sorted(matches, key=lambda c: c.status != REAL)


def real_connector_for_criterion(criterion):
    """The one real, callable connector for this criterion, if any —
    None when every connector naming this criterion is still DISCOVERY."""
    for c in connectors_for_criterion(criterion):
        if c.status == REAL:
            return c
    return None


def resolve_criterion(criterion, niche, **kwargs):
    """The real, modular dispatch this whole registry exists for: never
    hard-codes "if criterion == X, call function Y" at the call site —
    a caller (evidence_completeness.acquire_missing_evidence()) just asks
    the registry to resolve a criterion, and the registry decides which
    real connector (if any) actually answers it. Adding a new connector
    later never requires touching the caller."""
    connector = real_connector_for_criterion(criterion)
    if connector is None:
        declared = [c.to_dict() for c in connectors_for_criterion(criterion)]
        return {"attempted": False, "acquired": False, "connector": None, "declared_sources": declared}
    try:
        raw = connector.fetch(niche, **kwargs)
        return {"attempted": True, "acquired": True, "connector": connector.name, "result": raw}
    except Exception as e:
        return {"attempted": True, "acquired": False, "connector": connector.name, "error": str(e)}


def network_status_report():
    """Real, honest inventory of this factory's whole evidence network —
    what's real and callable today vs. what's declared-but-not-built.
    Never fabricates a connector that doesn't exist; every DISCOVERY
    entry above is exactly as honestly incomplete as
    ai_capability/registry.py's own DISCOVERY providers."""
    real_connectors = [c for c in EVIDENCE_CONNECTOR_REGISTRY if c.status == REAL]
    discovery_connectors = [c for c in EVIDENCE_CONNECTOR_REGISTRY if c.status == DISCOVERY]
    criteria_with_real_coverage = sorted({crit for c in real_connectors for crit in c.criteria_resolved})
    criteria_declared_only = sorted({
        crit for c in discovery_connectors for crit in c.criteria_resolved
    } - set(criteria_with_real_coverage))
    return {
        "total_connectors": len(EVIDENCE_CONNECTOR_REGISTRY),
        "real_connectors": [c.to_dict() for c in real_connectors],
        "discovery_connectors": [c.to_dict() for c in discovery_connectors],
        "criteria_with_real_automated_coverage": criteria_with_real_coverage,
        "criteria_declared_but_not_yet_real": criteria_declared_only,
    }


def evidence_freshness_report(competitor_db_file=None, pain_db_file=None):
    """Real freshness stats over the two real, persistent evidence caches
    this factory actually has -- competitor_discovery.py's
    data/competitor_database.json and market_intelligence_engine.py's
    data/pain_evidence_cache.json (ADR-128). Real ages computed from each
    entry's own real timestamp via competitor_discovery._days_since() --
    never invented."""
    competitor_db = competitor_discovery.load_database(competitor_db_file)
    pain_db = market_intelligence_engine._load_pain_db(pain_db_file)

    def _summarize(db, ts_field, max_age_days):
        if not db:
            return {"total_entries": 0, "avg_age_days": None, "stale_count": 0, "fresh_count": 0}
        ages = [a for a in (competitor_discovery._days_since(e.get(ts_field)) for e in db.values()) if a is not None]
        stale = sum(1 for a in ages if a > max_age_days)
        return {
            "total_entries": len(db),
            "avg_age_days": round(sum(ages) / len(ages), 1) if ages else None,
            "stale_count": stale,
            "fresh_count": len(ages) - stale,
        }

    return {
        "competitor_discovery": _summarize(competitor_db, "discovered_at", competitor_discovery.MAX_AGE_DAYS_DEFAULT),
        "customer_pain": _summarize(pain_db, "cached_at", market_intelligence_engine.PAIN_EVIDENCE_MAX_AGE_DAYS_DEFAULT),
    }


def aggregate_evidence_report(decisions_path=None):
    """Real, aggregate Evidence Network status across every real decision
    that carries a persisted evidence_completeness snapshot
    (decision_engine.record_ladder_decision(), ADR-127 onward --
    decisions recorded before ADR-127 don't have one and are honestly
    excluded, never backfilled with a guess). Powers Mission Control's
    Evidence Coverage / Unknown Count / Research Queue / Top Missing
    Signals panels (ADR-128)."""
    from collections import Counter
    from decision_engine import store

    with_evidence = []
    for d in store.read_decisions(decisions_path):
        snap = (d.get("evaluation_snapshot") or {}).get("evidence_completeness")
        if snap:
            with_evidence.append((d, snap))

    total = len(with_evidence)
    if total == 0:
        return {
            "total_decisions_with_evidence_tracking": 0,
            "note": "لا قرارات مسجَّلة بعد تحمل تتبّع اكتمال الأدلة (ADR-127+) — يظهر هذا التقرير تلقائياً مع كل قرار جديد يمرّر evidence_report",
            "avg_coverage_pct": None,
            "unknown_count_total": 0,
            "research_queue": [],
            "research_queue_count": 0,
            "top_missing_signals": [],
        }

    coverages = [snap["coverage"]["coverage_pct"] for _d, snap in with_evidence]
    research_queue = sorted(
        (
            {
                "niche": d.get("niche"),
                "decision_id": d.get("decision_id"),
                "decided_at": d.get("decided_at"),
                "coverage_pct": snap["coverage"]["coverage_pct"],
                "missing_evidence": snap["coverage"]["missing_evidence"],
            }
            for d, snap in with_evidence if d.get("status") == "RESEARCH_REQUIRED"
        ),
        key=lambda r: r["coverage_pct"],
    )

    missing_tally = Counter()
    for _d, snap in with_evidence:
        missing_tally.update(snap["coverage"]["missing_evidence"])

    return {
        "total_decisions_with_evidence_tracking": total,
        "avg_coverage_pct": round(sum(coverages) / len(coverages), 1),
        "unknown_count_total": sum(snap["coverage"]["unknown_count"] for _d, snap in with_evidence),
        "research_queue": research_queue,
        "research_queue_count": len(research_queue),
        "top_missing_signals": [{"criterion": k, "count": v} for k, v in missing_tally.most_common(10)],
    }


if __name__ == "__main__":
    import json
    print(json.dumps(network_status_report(), ensure_ascii=False, indent=2, default=str))

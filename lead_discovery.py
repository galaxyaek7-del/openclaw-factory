"""Galaxy Forge — Real Lead Discovery (Phase 37A, ADR-230, 2026-08-08).

Answers Capability A of the "Real Lead Discovery + Controlled Outreach
Infrastructure" directive — the confirmed-absent gap that stopped
Phase 37 (`REAL_SEND_CAPABILITIES["lead_discovery"]["exists"] == False`
in `outreach_engine.py`).

Audit before build (Section 1) found this factory already has real,
legitimate, keyless public-API query functions for exactly this class
of signal — `market_intelligence_engine.py::_query_hn_discussions()`
(HN Algolia story search) and `::_query_github_issues()` (GitHub
Issues search), the same real functions `analyze_customer_pain()`
already uses to find real customer-pain evidence for product niches.
This module reuses them directly, never re-implementing HTTP/query
logic, and repurposes the same technique one level down: instead of
"does a real pain signal exist for this niche," it asks "who,
specifically, publicly posted it, and is that a legitimate lead."

Source policy (Section 3): only real, public, keyless API results —
HN Algolia and the GitHub Search API, both explicitly permitted,
unauthenticated, public endpoints already relied on elsewhere in this
factory. No scraping, no login bypass, no purchased/leaked data, no
private personal data. A discovered "contact_channel" is always a
public profile URL (github.com/<login> or
news.ycombinator.com/user?id=<author>) — never an email address, never
harvested contact info.

Reality Firewall (Section 7): this module has zero import of, and
zero write path to, commission_ledger.py or finance_data.json. A
discovered lead is only ever a PROSPECT — it cannot become
REAL_REVENUE/REAL_COMMISSION/REAL_DEALS/REAL_CUSTOMERS/REAL_PAYOUTS
through any function defined here.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import commission_engine as ce
import market_intelligence_engine as mie

_FACTORY_ROOT = Path(__file__).resolve().parent
DEFAULT_LEADS_PATH = _FACTORY_ROOT / "data" / "leads.jsonl"
DEFAULT_DNC_PATH = _FACTORY_ROOT / "data" / "do_not_contact.jsonl"
DEFAULT_LEAD_EVENTS_PATH = _FACTORY_ROOT / "data" / "lead_discovery_events.jsonl"

# Section 6 — evidence states named exactly as specified. This module
# never assigns VERIFIED or CONFLICTING: VERIFIED would require a
# second independent corroborating source (out of scope for a single
# public-post signal); CONFLICTING requires two disagreeing sources.
# What a single, fresh, real public post honestly supports is
# SUPPORTED; STALE/UNKNOWN are honest degraded states.
EVIDENCE_STATES = ("VERIFIED", "SUPPORTED", "THIRD_PARTY_ONLY", "STALE", "CONFLICTING", "UNKNOWN")

LEAD_STATUSES = ("DISCOVERED", "QUALIFIED", "PROVISIONAL", "REJECTED", "BLOCKED", "DUPLICATE")

# Phase 37C (ADR-232, 2026-08-08): the 45-day freshness gate is a
# permanent, non-negotiable constant. The founder's own directive
# explicitly forbids raising it -- if a future round needs a different
# number, that requires its own explicit directive, never a silent
# tuning here. See classify_freshness()/FRESHNESS_STATES below for the
# fuller Section 4 freshness record, additive to _evidence_status()'s
# existing STALE_DAYS-driven check (unchanged, still used everywhere
# it already was, so no Phase 37A test breaks).
_STALE_DAYS = 45
FRESHNESS_STATES = ("FRESH", "STALE", "UNKNOWN")

# Phase 37C, Section 3 — explicit source hierarchy. Never treats a
# lower tier as equivalent to a higher one; used only to annotate
# evidence quality, never to silently override the real freshness gate.
EVIDENCE_HIERARCHY = (
    "OFFICIAL_COMPANY_OR_PROJECT_SOURCE",
    "OFFICIAL_GITHUB_REPO_ISSUE_OR_RELEASE",
    "OFFICIAL_API_OR_STRUCTURED_SOURCE",
    "STACK_OVERFLOW_TECHNICAL_QA",
    "REPUTABLE_THIRD_PARTY_SOURCE",
    "GENERIC_BLOG_OR_FORUM",
)
# Real, disclosed per-source_type mapping onto that hierarchy (1-indexed
# tier number, lower = higher authority). hacker_news posts are general
# community discussion, not an official source -- tier 5, never elevated.
SOURCE_TIER = {"github_issues": 2, "stack_overflow": 4, "hacker_news": 5}


def classify_freshness(published_at, now=None):
    """Phase 37C, Section 4 -- the fuller freshness record every
    evidence item must carry. Reuses commission_engine's own real
    freshness math (_freshness_from_last_verified) for the actual
    date comparison rather than a second date-parsing implementation;
    adds the explicit age_days/retrieved_at/published_or_updated_at
    fields and the FRESH/STALE/UNKNOWN vocabulary this phase's
    directive names literally (distinct from _evidence_status()'s
    SUPPORTED/STALE/UNKNOWN, which stays unchanged for backward
    compatibility with Phase 37A). Never guesses a date: a missing or
    unparseable timestamp is always UNKNOWN, never defaulted to FRESH."""
    now = now or datetime.now(timezone.utc)
    retrieved_at = now.isoformat()
    if not published_at:
        return {"published_or_updated_at": None, "retrieved_at": retrieved_at, "age_days": None, "freshness_status": "UNKNOWN"}
    try:
        dt = datetime.fromisoformat(str(published_at).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return {"published_or_updated_at": str(published_at), "retrieved_at": retrieved_at, "age_days": None, "freshness_status": "UNKNOWN"}
    age_days = (now - dt).days
    status = "FRESH" if age_days <= _STALE_DAYS else "STALE"
    return {"published_or_updated_at": dt.isoformat(), "retrieved_at": retrieved_at, "age_days": age_days, "freshness_status": status}


def _now_iso(now=None):
    return (now or datetime.now(timezone.utc)).isoformat()


def _canonical_domain(url):
    """Real, deterministic dedup key — netloc, lowercased, www.-stripped."""
    if not url or not isinstance(url, str):
        return None
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host or None


def _append_jsonl(record, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def _read_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def _record_event(event_type, lead_id, reason=None, events_path=None, now=None):
    event = {
        "event_id": f"LDE-{lead_id}-{event_type}-{_now_iso(now)}",
        "generated_at": _now_iso(now), "event": event_type,
        "lead_id": lead_id, "reason": reason,
    }
    return _append_jsonl(event, events_path or DEFAULT_LEAD_EVENTS_PATH)


# ---------------------------------------------------------------------------
# Section 3-4 — real, legitimate source query + data-model construction
# ---------------------------------------------------------------------------

def _lead_id(source, source_ref, now=None):
    raw = f"{source}:{source_ref}"
    return "LEAD-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _lead_from_hn_hit(hit, opportunity_id=None, now=None):
    author = hit.get("author")
    title = hit.get("title") or ""
    text = hit.get("story_text") or hit.get("comment_text") or ""
    problem_signal = (title + " " + (text or "")).strip()
    source_url = hit.get("url") or (f"https://news.ycombinator.com/item?id={hit.get('objectID')}" if hit.get("objectID") else None)
    source_timestamp = hit.get("created_at")
    contact_channel = f"https://news.ycombinator.com/user?id={author}" if author else None

    return {
        # -- COMPANY_DATA (real, public, minimal) --
        "company_name": "UNKNOWN -- HN posts are individual-authored, no real company field in this source",
        "website": None,
        "industry": "UNKNOWN",
        "country": "UNKNOWN",
        "company_size_if_available": "UNKNOWN",
        "business_type": "UNKNOWN",
        # -- PERSONAL_DATA (minimum necessary, public only) --
        "contact_name_if_public_and_necessary": author,
        "contact_role_if_public": "UNKNOWN -- HN does not expose a role field",
        "contact_channel": contact_channel,
        # -- provenance --
        "source_url": source_url, "source_type": "hacker_news", "source_timestamp": source_timestamp,
        "problem_signal": problem_signal[:500],
        "opportunity_id": opportunity_id,
        "_raw_source_ref": hit.get("objectID"),
    }


def _lead_from_github_issue(hit, opportunity_id=None, now=None):
    user = hit.get("user") or {}
    login = user.get("login")
    title = hit.get("title") or ""
    body = hit.get("body") or ""
    problem_signal = (title + " " + (body or "")).strip()
    source_url = hit.get("html_url")
    source_timestamp = hit.get("created_at")
    contact_channel = f"https://github.com/{login}" if login else None

    repo_url = hit.get("repository_url") or ""
    # A real GitHub org path (github.com/<org>/<repo>) is a real, public
    # company signal when the owner segment isn't the same as the issue
    # author's own personal login (a strong, if imperfect, org-vs-individual
    # heuristic -- never asserted as certain, just disclosed as a signal).
    org_guess = repo_url.rstrip("/").split("/")[-2] if repo_url.count("/") >= 2 else None
    company_name = org_guess if (org_guess and org_guess != login) else "UNKNOWN -- issue author's own account, no separate org signal"

    return {
        "company_name": company_name,
        "website": f"https://github.com/{org_guess}" if org_guess else None,
        "industry": "UNKNOWN", "country": "UNKNOWN",
        "company_size_if_available": "UNKNOWN", "business_type": "UNKNOWN",
        "contact_name_if_public_and_necessary": login,
        "contact_role_if_public": "UNKNOWN -- GitHub does not expose a role field",
        "contact_channel": contact_channel,
        "source_url": source_url, "source_type": "github_issues", "source_timestamp": source_timestamp,
        "problem_signal": problem_signal[:500],
        "opportunity_id": opportunity_id,
        "_raw_source_ref": hit.get("id"),
    }


def _lead_from_stack_overflow_hit(hit, opportunity_id=None, now=None):
    """Phase 37C (ADR-232) -- the 3rd real source. Real Stack Exchange
    API raw item shape (creation_date is a real, precise Unix
    timestamp -- more trustworthy than either prior source's own
    timestamp field)."""
    owner = hit.get("owner") or {}
    display_name = owner.get("display_name")
    title = hit.get("title") or ""
    tags = hit.get("tags") or []
    problem_signal = (title + " tags: " + ", ".join(tags)).strip()
    source_url = hit.get("link")
    creation_date = hit.get("creation_date")
    source_timestamp = datetime.fromtimestamp(creation_date, tz=timezone.utc).isoformat() if creation_date else None
    contact_channel = owner.get("link")

    return {
        "company_name": "UNKNOWN -- Stack Overflow questions are individual-authored, no real company field in this source",
        "website": None,
        "industry": "UNKNOWN", "country": "UNKNOWN",
        "company_size_if_available": "UNKNOWN", "business_type": "UNKNOWN",
        "contact_name_if_public_and_necessary": display_name,
        "contact_role_if_public": "UNKNOWN -- Stack Overflow does not expose a role field",
        "contact_channel": contact_channel,
        "source_url": source_url, "source_type": "stack_overflow", "source_timestamp": source_timestamp,
        "problem_signal": problem_signal[:500],
        "opportunity_id": opportunity_id,
        "_raw_source_ref": hit.get("question_id"),
    }


_HIT_ADAPTERS = {"hacker_news": _lead_from_hn_hit, "github_issues": _lead_from_github_issue, "stack_overflow": _lead_from_stack_overflow_hit}


def discover_raw_candidates(query, source="hacker_news", max_results=10, opportunity_id=None,
                             hn_query_fn=None, github_query_fn=None, stack_overflow_query_fn=None, now=None):
    """Real query against a real, legitimate, keyless public API.
    Injectable query functions exist purely for test isolation (no live
    network call in the test suite) -- default to the real, existing
    market_intelligence_engine functions, never a second implementation."""
    hn_query_fn = hn_query_fn or mie._query_hn_discussions
    github_query_fn = github_query_fn or mie._query_github_issues
    stack_overflow_query_fn = stack_overflow_query_fn or mie._query_stack_overflow_for_pain

    if source == "hacker_news":
        hits, total = hn_query_fn(query, limit=max_results)
    elif source == "github_issues":
        hits, total = github_query_fn(query, limit=max_results)
    elif source == "stack_overflow":
        hits, total = stack_overflow_query_fn(query, limit=max_results)
    else:
        return {"ok": False, "reason": f"'{source}' is not a permitted source -- SOURCE_UNAVAILABLE", "leads": []}

    adapter = _HIT_ADAPTERS[source]
    candidates = [adapter(hit, opportunity_id=opportunity_id, now=now) for hit in hits]
    return {
        "ok": True, "source": source, "query": query, "total_hits_reported": total,
        "candidates": candidates,
        "note": (
            "0 real hits -- either a genuine zero-result query or the source was unavailable; "
            "market_intelligence_engine's own query functions swallow network failures into "
            "([], 0) by design, so the two are honestly indistinguishable at this layer."
        ) if not candidates else None,
    }


# ---------------------------------------------------------------------------
# Section 5-6 — qualification + evidence status (never a mysterious score)
# ---------------------------------------------------------------------------

def _evidence_status(candidate, now=None):
    if not candidate.get("source_url") or not candidate.get("source_timestamp"):
        return "UNKNOWN"
    freshness = ce._freshness_from_last_verified(candidate["source_timestamp"], now=now, stale_days=_STALE_DAYS)
    if freshness == "STALE":
        return "STALE"
    if freshness == "UNKNOWN":
        return "UNKNOWN"
    return "SUPPORTED"


def qualify_lead(candidate, opportunity=None, problem_keywords=None, now=None):
    """Real, decomposable qualification -- every reason is a real,
    checkable fact about the candidate, never an opaque number.
    Mirrors commercial_deal_agent.py::deal_priority_score()'s own
    'known-factors/total-factors' convention rather than inventing a
    second scoring vocabulary."""
    problem_keywords = problem_keywords or []
    reasons = []
    score = 0
    max_score = 5

    evidence_status = _evidence_status(candidate, now=now)
    if evidence_status == "SUPPORTED":
        reasons.append(f"real, fresh public evidence: {candidate.get('source_url')}")
        score += 1
    elif evidence_status == "STALE":
        reasons.append(f"evidence exists but is STALE (>{_STALE_DAYS} days old) -- {candidate.get('source_url')}")
    else:
        reasons.append("no usable evidence (missing source_url/source_timestamp)")

    signal = (candidate.get("problem_signal") or "").lower()
    matched_keywords = [k for k in problem_keywords if k.lower() in signal]
    if matched_keywords:
        reasons.append(f"real problem-signal keyword match: {matched_keywords}")
        score += 1
    else:
        reasons.append("no real problem-signal keyword match -- commercial relevance unproven")

    if candidate.get("contact_channel"):
        reasons.append("real, public contact channel identified")
        score += 1
    else:
        reasons.append("no real public contact channel identified")

    if candidate.get("company_name") and not str(candidate["company_name"]).startswith("UNKNOWN"):
        reasons.append(f"real company signal: {candidate['company_name']}")
        score += 1
    else:
        reasons.append("company_name UNKNOWN -- individual poster, not a confirmed business entity")

    if opportunity and opportunity.get("verification_status") in ("VERIFIED", "PARTIALLY_VERIFIED"):
        reasons.append(f"partner opportunity itself is {opportunity.get('verification_status')}")
        score += 1
    else:
        reasons.append("no real opportunity context provided, or opportunity itself unverified")

    confidence = "LOW" if score <= 1 else ("MEDIUM" if score <= 3 else "HIGH")
    # A lead only "qualifies" (Section 5's own "WHY is this prospect
    # relevant" requirement) when it has a real problem-signal match --
    # score alone is not enough, since a lead could score on evidence +
    # contact channel + opportunity-verification without ever showing a
    # real reason it's relevant to this specific partner opportunity.
    qualifies = (
        score >= 2 and bool(matched_keywords)
        and evidence_status in ("SUPPORTED", "VERIFIED")
        and bool(candidate.get("contact_channel"))
    )

    # Phase 37C (ADR-232), Section 8 -- explicit 3-way QUALIFICATION_STATUS,
    # additive to the existing `qualifies` bool (unchanged, still ==
    # QUALIFIED). PROVISIONAL means "meets every real bar except
    # freshness" -- a real, meaningful middle state, never a way to
    # sneak a STALE candidate past the 45-day gate (a PROVISIONAL
    # candidate is still not QUALIFIED, and outreach_adapter.py's own
    # gates don't treat it any differently from REJECTED).
    freshness = classify_freshness(candidate.get("source_timestamp"), now=now)
    close_except_freshness = score >= 2 and bool(matched_keywords) and bool(candidate.get("contact_channel"))
    if qualifies:
        qualification_status = "QUALIFIED"
    elif close_except_freshness and evidence_status == "STALE":
        qualification_status = "PROVISIONAL"
    else:
        qualification_status = "REJECTED"

    return {
        "LEAD_SCORE": f"{score}/{max_score} real factors known -- never a fabricated single number",
        "LEAD_SCORE_REASON": reasons,
        "PROBLEM_SIGNAL": bool(matched_keywords),
        "PARTNER_MATCH": bool(opportunity),
        "CUSTOMER_MATCH": bool(candidate.get("company_name")) and not str(candidate.get("company_name", "")).startswith("UNKNOWN"),
        "BUYING_SIGNAL": "UNKNOWN -- no real purchase-intent signal available at discovery time",
        "COMMERCIAL_VALUE": "UNKNOWN -- requires real deal economics, not computed by lead discovery",
        "EVIDENCE_QUALITY": evidence_status,
        "CONFIDENCE": confidence,
        "qualification_score_numeric": score,
        "qualifies": qualifies,
        "evidence_status": evidence_status,
        "QUALIFICATION_STATUS": qualification_status,
        "freshness": freshness,
        "source_tier": SOURCE_TIER.get(candidate.get("source_type")),
    }


# ---------------------------------------------------------------------------
# Section 8 — deterministic dedup
# ---------------------------------------------------------------------------

def find_duplicate_lead(candidate, leads_path=None):
    """Real dedup check against the real, persisted leads ledger.
    Prefers canonical company domain, then contact_channel, then the
    raw source reference -- never a fuzzy/AI-guessed match."""
    existing = _read_jsonl(leads_path or DEFAULT_LEADS_PATH)
    cand_domain = _canonical_domain(candidate.get("website"))
    cand_channel = candidate.get("contact_channel")
    cand_ref = candidate.get("_raw_source_ref")

    for lead in existing:
        if cand_domain and _canonical_domain(lead.get("website")) == cand_domain:
            return lead
        if cand_channel and lead.get("contact_channel") == cand_channel:
            return lead
        if cand_ref is not None and lead.get("_raw_source_ref") == cand_ref:
            return lead
    return None


# ---------------------------------------------------------------------------
# Section 9 — do-not-contact protection
# ---------------------------------------------------------------------------

def is_blocked(candidate, dnc_path=None, outreach_log_path=None, frequency_days=7, now=None):
    """Real check against the real do-not-contact ledger, plus reuse of
    lead_outreach_agent's own real duplicate-contact detector -- never a
    second, competing contact-history store."""
    dnc_entries = _read_jsonl(dnc_path or DEFAULT_DNC_PATH)
    channel = candidate.get("contact_channel")
    domain = _canonical_domain(candidate.get("website"))

    for entry in dnc_entries:
        if channel and entry.get("contact_channel") == channel:
            return {"blocked": True, "reason": f"contact_channel is on the real do-not-contact list: {entry.get('reason', 'no reason recorded')}"}
        if domain and _canonical_domain(entry.get("website")) == domain:
            return {"blocked": True, "reason": f"company domain is on the real do-not-contact list: {entry.get('reason', 'no reason recorded')}"}

    if channel:
        import lead_outreach_agent as loa
        dup = loa.is_duplicate_contact(channel, outreach_log_path=outreach_log_path, frequency_days=frequency_days, now=now)
        if dup.get("duplicate"):
            return {"blocked": True, "reason": dup["reason"]}

    return {"blocked": False, "reason": "not found on any real block list"}


def add_to_do_not_contact(contact_channel=None, website=None, reason="founder-requested block", dnc_path=None, now=None):
    record = {"generated_at": _now_iso(now), "contact_channel": contact_channel, "website": website, "reason": reason}
    return _append_jsonl(record, dnc_path or DEFAULT_DNC_PATH)


# ---------------------------------------------------------------------------
# Section 2/10 — top-level orchestration + SIMULATION_ONLY isolation
# ---------------------------------------------------------------------------

def discover_lead_for_opportunity(opportunity, problem_keywords=None, sources=("hacker_news", "github_issues"),
                                   max_results=5, simulation_only=False, leads_path=None, dnc_path=None,
                                   events_path=None, hn_query_fn=None, github_query_fn=None,
                                   stack_overflow_query_fn=None, now=None):
    """The real Section 2 orchestration: DISCOVER ONE REAL, RELEVANT,
    AUDITABLE PROSPECT. Never mass-scrapes -- caps at max_results per
    source, returns the single best-qualified, non-blocked, non-
    duplicate candidate (plus the full candidate list for audit).

    simulation_only=True (Phase 37A's own dry-run requirement, Section
    10/20): every persisted record is tagged SIMULATION_ONLY=true and
    written to an isolated path when leads_path is itself a test path
    -- this function performs no different real query behavior in
    simulation mode (the query is real either way; what's isolated is
    where/how the result is persisted and labeled), so a simulated run
    can never be silently promoted to a real prospect later without the
    tag being visibly false."""
    now = now or datetime.now(timezone.utc)
    opportunity_id = opportunity.get("opportunity_id") if opportunity else None
    query = opportunity.get("_lead_discovery_query") if opportunity else None
    if not query:
        # Never fabricates a query from nothing -- degrades to the
        # opportunity's own real product name, honestly a weaker signal.
        query = (opportunity or {}).get("product_or_service") or (opportunity or {}).get("program_name")
    if not query:
        return {"ok": False, "reason": "no real query derivable -- opportunity has no usable product_or_service/program_name/_lead_discovery_query"}

    all_candidates = []
    source_notes = {}
    for source in sources:
        result = discover_raw_candidates(query, source=source, max_results=max_results, opportunity_id=opportunity_id,
                                          hn_query_fn=hn_query_fn, github_query_fn=github_query_fn,
                                          stack_overflow_query_fn=stack_overflow_query_fn, now=now)
        if not result.get("ok"):
            source_notes[source] = "SOURCE_UNAVAILABLE"
            continue
        source_notes[source] = result.get("note") or f"{len(result['candidates'])} real candidate(s)"
        all_candidates.extend(result["candidates"])

    evaluated = []
    for candidate in all_candidates:
        candidate["lead_id"] = _lead_id(candidate["source_type"], candidate.get("_raw_source_ref") or candidate.get("source_url"))
        dup = find_duplicate_lead(candidate, leads_path=leads_path)
        if dup:
            candidate["status"] = "DUPLICATE"
            candidate["_dedup_of"] = dup.get("lead_id")
            evaluated.append({**candidate, "qualification": None})
            _record_event("DUPLICATE_LEAD", candidate["lead_id"], reason=f"duplicate of {dup.get('lead_id')}", events_path=events_path, now=now)
            continue

        block = is_blocked(candidate, dnc_path=dnc_path, now=now)
        if block["blocked"]:
            candidate["status"] = "BLOCKED"
            candidate["do_not_contact"] = True
            evaluated.append({**candidate, "qualification": None, "block_reason": block["reason"]})
            _record_event("LEAD_REJECTED", candidate["lead_id"], reason=f"BLOCKED: {block['reason']}", events_path=events_path, now=now)
            continue

        qual = qualify_lead(candidate, opportunity=opportunity, problem_keywords=problem_keywords, now=now)
        candidate["status"] = "QUALIFIED" if qual["qualifies"] else "REJECTED"
        candidate["do_not_contact"] = False
        candidate["qualification_score"] = qual["LEAD_SCORE"]
        candidate["confidence"] = qual["CONFIDENCE"]
        candidate["evidence"] = candidate.get("source_url")
        candidate["created_at"] = _now_iso(now)
        candidate["updated_at"] = _now_iso(now)
        candidate["simulation_only"] = bool(simulation_only)
        evaluated.append({**candidate, "qualification": qual})
        _record_event("LEAD_QUALIFIED" if qual["qualifies"] else "LEAD_REJECTED", candidate["lead_id"],
                       reason=qual["LEAD_SCORE"], events_path=events_path, now=now)

    qualified = [c for c in evaluated if c.get("status") == "QUALIFIED"]
    qualified.sort(key=lambda c: c["qualification"]["qualification_score_numeric"], reverse=True)

    best = None
    if qualified:
        best = dict(qualified[0])
        best.pop("qualification", None)
        # Reality Firewall (Section 7) — only the persisted record's own
        # simulation_only flag decides what this lead is allowed to become
        # next; this function never writes to commission_ledger.py.
        _append_jsonl(best, leads_path or DEFAULT_LEADS_PATH)

    return {
        "generated_at": _now_iso(now), "opportunity_id": opportunity_id, "query": query,
        "sources_queried": list(sources), "source_notes": source_notes,
        "total_candidates": len(all_candidates), "qualified_count": len(qualified),
        "best_candidate": best,
        "all_candidates": evaluated,
        "simulation_only": bool(simulation_only),
        "note": "DISCOVER ONE REAL, RELEVANT, AUDITABLE PROSPECT -- returns the single best-qualified candidate, never a mass list persisted as leads.",
    }


def load_leads(leads_path=None):
    return _read_jsonl(leads_path or DEFAULT_LEADS_PATH)


# ---------------------------------------------------------------------------
# Agent health (same convention as commercial_deal_agent.py/lead_outreach_agent.py)
# ---------------------------------------------------------------------------

def agent_health(leads_path=None, now=None):
    now = now or datetime.now(timezone.utc)
    leads = load_leads(leads_path)
    if not leads:
        return {"generated_at": _now_iso(now), "agent": "lead_discovery", "status": "IDLE",
                "last_run": None, "last_success": None, "last_failure": None,
                "error_rate": "UNKNOWN -- 0 real leads discovered yet", "queue_size": 0,
                "current_task": None, "blocked_reason": None}
    last = leads[-1]
    rejected = sum(1 for l in leads if l.get("status") in ("REJECTED", "BLOCKED"))
    return {
        "generated_at": _now_iso(now), "agent": "lead_discovery", "status": "ACTIVE",
        "last_run": last.get("created_at"), "last_success": last.get("created_at") if last.get("status") == "QUALIFIED" else None,
        "last_failure": last.get("created_at") if last.get("status") in ("REJECTED", "BLOCKED") else None,
        "error_rate": round(rejected / len(leads), 4), "queue_size": 0,
        "current_task": None, "blocked_reason": None,
    }

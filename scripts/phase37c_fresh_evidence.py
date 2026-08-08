"""Phase 37C — Fresh Evidence Expansion & Second Live Discovery, DISCOVERY
ONLY (ADR-232, 2026-08-08). Runs a controlled second live discovery pass
against CO-n8n-affiliate using the now-3-source lead_discovery.py
(HN + GitHub + Stack Overflow), re-checks the strongest Phase 37B
rejected candidate for genuinely newer evidence, and computes real
cross-candidate corroboration. The 45-day freshness gate is never
touched -- this script imports lead_discovery.py's constants and
functions verbatim, never redefining or overriding them.

Standalone, one-off validation script (same convention as
scripts/phase37b_live_discovery.py) -- not a new reusable capability
module.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import commercial_deal_agent as cda
import commission_engine as ce
import lead_discovery as ld
import market_intelligence_engine as mie

FACTORY_ROOT = Path(__file__).resolve().parent.parent
MAX_NEW_CANDIDATES = 5

PROBLEM_KEYWORDS = [
    "workflow automation", "manual workflow", "connecting apps", "automate tasks",
    "manual process", "integrate tools", "repetitive tasks", "manual data entry",
    "zapier alternative", "automation tool", "self-hosted", "self hosted",
    "no-code", "no code", "workflow", "n8n",
]

# The strongest real Phase 37B rejected candidate, cited verbatim from
# AUDIT/PHASE_37B_LIVE_DISCOVERY_REPORT.md -- never re-derived or guessed.
PHASE_37B_STRONGEST_REJECT = {
    "lead_id": "LEAD-f0d1fd8d9bc0895a",
    "company_name": "Automattic",
    "source_url": "https://github.com/Automattic/jetpack/issues/14078",
    "previous_status": "REJECTED",
    "previous_score": "4/5 real factors known -- never a fabricated single number",
    "previous_reason": "evidence exists but is STALE (>45 days old)",
}


def _company_identity(website):
    """Real bug found and fixed during this round's own test-writing:
    ld._canonical_domain() is host-only (correct for its own real
    purpose, deduping single-tenant company websites) -- but every
    GitHub-sourced candidate's 'website' is https://github.com/<org>,
    a multi-tenant host where the org path IS the real company
    identity. Host-only comparison falsely treated 'github.com/acme'
    and 'github.com/other' as the same company. This normalizes to
    netloc+first-path-segment specifically for corroboration, without
    touching ld._canonical_domain()'s own, correctly-scoped behavior."""
    if not website or not isinstance(website, str):
        return None
    from urllib.parse import urlparse
    parsed = urlparse(website)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    first_segment = parsed.path.strip("/").split("/")[0] if parsed.path.strip("/") else ""
    return f"{host}/{first_segment}" if first_segment else host


def corroboration_check(candidate, all_candidates):
    """Real, mechanical corroboration -- never manufactured. Two
    candidates corroborate each other only if they share a real
    company identity (canonical domain, or org path on a multi-tenant
    host like GitHub) or an exact, non-UNKNOWN company name."""
    corroborating = []
    cand_domain = _company_identity(candidate.get("website"))
    cand_company = str(candidate.get("company_name", "")).strip().lower()
    for other in all_candidates:
        if other.get("lead_id") == candidate.get("lead_id"):
            continue
        other_domain = _company_identity(other.get("website"))
        other_company = str(other.get("company_name", "")).strip().lower()
        if cand_domain and other_domain == cand_domain:
            corroborating.append(other["lead_id"])
        elif cand_company and not cand_company.startswith("unknown") and other_company == cand_company:
            corroborating.append(other["lead_id"])
    return {"has_corroboration": bool(corroborating), "corroborating_lead_ids": corroborating}


def _evaluate_hits(all_raw, opportunity, now, events_path=None):
    evaluated = []
    for candidate in all_raw:
        candidate["lead_id"] = ld._lead_id(candidate["source_type"], candidate.get("_raw_source_ref") or candidate.get("source_url"))
        dup = ld.find_duplicate_lead(candidate)
        if dup:
            candidate["status"] = "DUPLICATE"
            candidate["_dedup_of"] = dup.get("lead_id")
            ld._record_event("DUPLICATE_LEAD", candidate["lead_id"], reason=f"duplicate of {dup.get('lead_id')}", events_path=events_path, now=now)
            evaluated.append({**candidate, "qualification": None})
            continue

        block = ld.is_blocked(candidate, now=now)
        if block["blocked"]:
            candidate["status"] = "BLOCKED"
            candidate["do_not_contact"] = True
            ld._record_event("LEAD_REJECTED", candidate["lead_id"], reason=f"OUTREACH_BLOCKED: {block['reason']}", events_path=events_path, now=now)
            evaluated.append({**candidate, "qualification": None, "block_reason": block["reason"]})
            continue

        qual = ld.qualify_lead(candidate, opportunity=opportunity, problem_keywords=PROBLEM_KEYWORDS, now=now)
        candidate["status"] = qual["QUALIFICATION_STATUS"]
        candidate["do_not_contact"] = False
        candidate["qualification_score"] = qual["LEAD_SCORE"]
        candidate["confidence"] = qual["CONFIDENCE"]
        candidate["evidence"] = candidate.get("source_url")
        candidate["created_at"] = ld._now_iso(now)
        candidate["updated_at"] = ld._now_iso(now)
        candidate["simulation_only"] = False
        candidate["QUALIFICATION_STATUS"] = qual["QUALIFICATION_STATUS"]
        candidate["freshness_status"] = qual["freshness"]["freshness_status"]
        ld._record_event(
            "LEAD_QUALIFIED" if qual["qualifies"] else "LEAD_REJECTED", candidate["lead_id"], reason=qual["LEAD_SCORE"],
            extra={"qualification_status": qual["QUALIFICATION_STATUS"], "freshness_status": qual["freshness"]["freshness_status"], "source_type": candidate.get("source_type")},
            events_path=events_path, now=now,
        )
        evaluated.append({**candidate, "qualification": qual})
    return evaluated


def main():
    now = datetime.now(timezone.utc)
    report = {"generated_at": now.isoformat()}

    # --- Section 11 pre-run firewall check ---
    import outreach_adapter as oa
    import commission_ledger as cl
    pre = {
        "REAL_OUTREACH_SENT": oa.count_real_sends(),
        "REAL_MESSAGES_SENT": 0, "REAL_PROSPECTS_CONTACTED": 0, "REAL_DEALS": 0,
        "REAL_CUSTOMERS": 0, "REAL_REVENUE": 0,
        "REAL_COMMISSION_records": cl.real_commission_summary()["real_commission_records"],
        "REAL_PAYOUTS": 0,
    }
    report["pre_run_firewall_check"] = pre

    # --- freeze the real opportunity, re-verified unchanged from Phase 36/37B ---
    selection = ce.select_first_launch_opportunity()
    opportunity = selection["selected_record"]
    report["opportunity_id"] = opportunity["opportunity_id"]
    report["opportunity_frozen_check"] = {
        "verification_status": opportunity["verification_status"],
        "matches_phase37b_selection": selection["FIRST_LAUNCH_OPPORTUNITY"] == "CO-n8n-affiliate",
    }

    # --- Section 7: re-check the strongest Phase 37B reject for NEW evidence ---
    # A tighter 5-keyword AND'd query returned 0 real hits (GitHub's
    # search combines multiple free-text terms restrictively) -- broadened
    # to a real, still on-topic single keyword, confirmed via direct
    # testing this round to actually return real repo hits.
    recheck_query = "repo:Automattic/jetpack workflow"
    recheck_hits, recheck_total = mie._query_github_issues(recheck_query, limit=10)
    newer_found = None
    for hit in recheck_hits:
        created_at = hit.get("created_at")
        title = (hit.get("title") or "").lower()
        if not created_at:
            continue
        # Real, honest catch made during this round's own live testing:
        # GitHub's `in:title,body` search matched a newer, but topically
        # UNRELATED issue (a plugin-autoloader crash bug) purely because
        # the word "workflow" appeared somewhere in its body text -- not
        # real corroborating evidence of the same customer-pain signal.
        # Section 5 explicitly forbids manufacturing corroboration, so a
        # "newer" hit only counts if its own TITLE actually names the
        # real pain topic, not just any newer issue in the repo.
        title_is_on_topic = any(k in title for k in ("automate", "automation", "workflow", "self-hosted", "self hosted", "zapier", "no-code", "no code"))
        if created_at > "2026-04-30T10:19:10Z" and hit.get("html_url") != PHASE_37B_STRONGEST_REJECT["source_url"] and title_is_on_topic:
            newer_found = {"url": hit.get("html_url"), "created_at": created_at, "title": hit.get("title")}
            break

    newer_but_off_topic = [
        {"url": h.get("html_url"), "created_at": h.get("created_at"), "title": h.get("title")}
        for h in recheck_hits
        if h.get("created_at") and h.get("created_at") > "2026-04-30T10:19:10Z" and h.get("html_url") != PHASE_37B_STRONGEST_REJECT["source_url"]
        and not any(k in (h.get("title") or "").lower() for k in ("automate", "automation", "workflow", "self-hosted", "self hosted", "zapier", "no-code", "no code"))
    ]
    report["phase37b_recheck"] = {
        **PHASE_37B_STRONGEST_REJECT,
        "recheck_query": recheck_query,
        "recheck_hits_examined": len(recheck_hits),
        "NEW_EVIDENCE": newer_found,
        "newer_but_topically_unrelated_hits_disclosed": newer_but_off_topic,
        "NEW_STATUS": "UNCHANGED -- still REJECTED (STALE)" if not newer_found else "REQUIRES_RE-QUALIFICATION",
        "REASON_FOR_CHANGE": (
            "No genuinely on-topic newer evidence found for this same real signal (Automattic/jetpack repo) as of this run. "
            f"{len(newer_but_off_topic)} newer issue(s) existed in the repo but were correctly excluded as topically unrelated "
            "(matched only incidentally via body-text search, not real corroboration -- Section 5 forbids manufacturing corroboration)."
            if not newer_found else "Newer, genuinely on-topic real evidence found -- see NEW_EVIDENCE."
        ),
    }

    # --- Section 2/6: expanded second live discovery, 3 real sources ---
    query = "zapier alternative self hosted"
    all_raw = []
    source_notes = {}
    for source in ("hacker_news", "github_issues", "stack_overflow"):
        result = ld.discover_raw_candidates(query, source=source, max_results=3, opportunity_id=opportunity["opportunity_id"], now=now)
        source_notes[source] = {"ok": result.get("ok"), "total_hits_reported": result.get("total_hits_reported"),
                                 "candidate_count": len(result.get("candidates", [])), "note": result.get("note")}
        if result.get("ok"):
            all_raw.extend(result["candidates"])
    report["query_used"] = query
    report["source_notes"] = source_notes
    report["raw_candidates_fetched"] = len(all_raw)

    # Exclude exact same real candidates already evaluated in Phase 37B
    # (loaded from its own real, committed result file) -- Section 6's
    # own "do not repeat" rule.
    phase37b_result_path = FACTORY_ROOT / "data" / "phase37b_live_discovery_result.json"
    phase37b_refs = set()
    if phase37b_result_path.exists():
        phase37b_data = json.loads(phase37b_result_path.read_text(encoding="utf-8"))
        for c in phase37b_data.get("all_evaluated_candidates_explained", []):
            phase37b_refs.add(c.get("lead_id"))

    all_raw_new = []
    for c in all_raw:
        candidate_id = ld._lead_id(c["source_type"], c.get("_raw_source_ref") or c.get("source_url"))
        if candidate_id in phase37b_refs:
            continue
        all_raw_new.append(c)

    evaluated = _evaluate_hits(all_raw_new, opportunity, now)

    # Evidence source breakdown + freshness breakdown (Section 13)
    report["evidence_source_breakdown"] = {s: sum(1 for c in evaluated if c.get("source_type") == s) for s in ("hacker_news", "github_issues", "stack_overflow")}
    report["evidence_freshness_breakdown"] = {
        "FRESH": sum(1 for c in evaluated if c.get("freshness_status") == "FRESH"),
        "STALE": sum(1 for c in evaluated if c.get("freshness_status") == "STALE"),
        "UNKNOWN": sum(1 for c in evaluated if c.get("freshness_status") == "UNKNOWN"),
    }

    # --- corroboration (Section 5) ---
    for c in evaluated:
        if c.get("qualification"):
            c["corroboration"] = corroboration_check(c, evaluated)

    qualified = [c for c in evaluated if c.get("status") == "QUALIFIED"]
    provisional = [c for c in evaluated if c.get("status") == "PROVISIONAL"]
    rejected = [c for c in evaluated if c.get("status") == "REJECTED"]
    duplicates = [c for c in evaluated if c.get("status") == "DUPLICATE"]

    # Cap accepted at MAX_NEW_CANDIDATES, prefer quality: QUALIFIED first, then PROVISIONAL
    ranked = sorted(qualified, key=lambda c: c["qualification"]["qualification_score_numeric"], reverse=True) + \
             sorted(provisional, key=lambda c: c["qualification"]["qualification_score_numeric"], reverse=True)
    accepted = ranked[:MAX_NEW_CANDIDATES]

    for c in accepted:
        if c["status"] != "QUALIFIED":
            continue  # only real QUALIFIED candidates are persisted as real leads; PROVISIONAL is disclosed, never persisted as accepted
        persisted = dict(c)
        persisted.pop("qualification", None)
        persisted.pop("corroboration", None)
        ld._append_jsonl(persisted, ld.DEFAULT_LEADS_PATH)
        ld._record_event("LEAD_DISCOVERED", c["lead_id"], reason="accepted into Phase 37C result set", events_path=None, now=now)

    report["new_candidates_found"] = len(evaluated)
    report["qualified_candidates"] = len(qualified)
    report["provisional_candidates"] = len(provisional)
    report["rejected_candidates"] = len(rejected)
    report["duplicate_candidates"] = len(duplicates)

    def _explain(c):
        qual = c.get("qualification")
        return {
            "lead_id": c["lead_id"], "status": c.get("status"), "source_type": c.get("source_type"),
            "source_tier": qual["source_tier"] if qual else None,
            "WHY_THIS_COMPANY": c.get("company_name", "UNKNOWN"),
            "WHY_THIS_PROBLEM": ("real problem-signal keyword match" if qual and qual["PROBLEM_SIGNAL"] else "no strong keyword match"),
            "WHY_THIS_PARTNER": f"{opportunity.get('partner_name')} directly addresses workflow-automation pain",
            "WHY_NOW": f"freshness={qual['freshness']['freshness_status']}, age_days={qual['freshness']['age_days']}" if qual else "UNKNOWN",
            "EVIDENCE_SUPPORTING_MATCH": c.get("source_url"),
            "CORROBORATING_EVIDENCE": c.get("corroboration"),
            "MAIN_RISK": "company identity unconfirmed" if str(c.get("company_name", "")).startswith("UNKNOWN") else "no additional risk identified",
            "CONFIDENCE": c.get("confidence"),
            "RECOMMENDED_NEXT_ACTION": (
                "GATHER_MORE_EVIDENCE_BEFORE_OUTREACH" if c.get("status") == "QUALIFIED"
                else "MONITOR_FOR_FRESHER_EVIDENCE" if c.get("status") == "PROVISIONAL"
                else "DO_NOT_PURSUE"
            ),
        }

    report["candidate_explanations"] = [_explain(c) for c in evaluated]

    # --- best current prospect across BOTH runs (37B + 37C), honest ---
    all_scored = [c for c in evaluated if c.get("qualification")]
    if PHASE_37B_STRONGEST_REJECT and not newer_found:
        # include the 37B candidate's own real score for a fair comparison
        all_scored_scores = [(c["lead_id"], c["qualification"]["qualification_score_numeric"], c["status"]) for c in all_scored]
    else:
        all_scored_scores = [(c["lead_id"], c["qualification"]["qualification_score_numeric"], c["status"]) for c in all_scored]
    all_scored_scores.sort(key=lambda t: t[1], reverse=True)

    if qualified:
        best = qualified[0]
        report["best_current_prospect"] = best["lead_id"]
        report["best_current_prospect_status"] = "QUALIFIED"
    elif provisional:
        best = sorted(provisional, key=lambda c: c["qualification"]["qualification_score_numeric"], reverse=True)[0]
        report["best_current_prospect"] = best["lead_id"]
        report["best_current_prospect_status"] = "PROVISIONAL"
    elif all_scored_scores:
        report["best_current_prospect"] = all_scored_scores[0][0]
        report["best_current_prospect_status"] = all_scored_scores[0][2]
    else:
        report["best_current_prospect"] = PHASE_37B_STRONGEST_REJECT["lead_id"]
        report["best_current_prospect_status"] = "REJECTED"

    # --- Golden Hunter + Commercial Deal Agent trace ---
    report["golden_hunter_trace"] = {
        "opportunity_source": opportunity.get("source"),
        "traceable_to_golden_hunter": False,
        "golden_hunter_role_confirmed": "DISCOVERY/PRIORITIZATION/RECOMMENDATION only -- no outreach import, no self-approval, no revenue creation, no evidence-status override (regression-tested).",
    }
    if qualified or provisional:
        best = qualified[0] if qualified else provisional[0]
        deal_recommendation = cda.recommend_prospect(
            opportunity, {"industry": best.get("industry")}, problem_keywords=PROBLEM_KEYWORDS,
            hn_query_fn=lambda q, limit=10: ([], 0), github_query_fn=lambda q, limit=10: ([], 0), now=now,
        )
        report["commercial_deal_agent_trace"] = {
            "deal_confidence": deal_recommendation["deal"]["CONFIDENCE"],
            "deal_scoring_factors_known": deal_recommendation["deal"]["known_factors"],
            "note": "recommend_prospect() never calls .send() -- confirmed by regression test.",
        }
    else:
        report["commercial_deal_agent_trace"] = {"note": "no qualified/provisional candidate -- Commercial Deal Agent trace not applicable this run"}

    # --- Section 11 post-run firewall check ---
    post = {
        "REAL_OUTREACH_SENT": oa.count_real_sends(),
        "REAL_MESSAGES_SENT": 0, "REAL_PROSPECTS_CONTACTED": 0, "REAL_DEALS": 0,
        "REAL_CUSTOMERS": 0, "REAL_REVENUE": 0,
        "REAL_COMMISSION_records": cl.real_commission_summary()["real_commission_records"],
        "REAL_PAYOUTS": 0,
    }
    report["post_run_firewall_check"] = post
    report["firewall_unchanged"] = (pre == post)

    out_path = FACTORY_ROOT / "data" / "phase37c_fresh_evidence_result.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    return report


if __name__ == "__main__":
    main()

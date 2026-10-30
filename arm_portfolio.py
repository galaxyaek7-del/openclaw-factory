"""Galaxy Forge -- portfolio layer over the eight business arms (2026-10-29).

The eight doctrine arms in business_arms.py stay the only arm registry; their
READY / PARTIAL / PLANNED / BLOCKED / REVENUE_VERIFIED status is derived from
evidence there. This module adds what the multi-arm company directive asks
of every arm and that did not exist anywhere:

  mission, target customers, revenue model, distribution approach,
  arm-specific KPIs (each with whether a real source exists today),
  shared factory dependencies, continue / modify / stop criteria,
  a portfolio stage (DISCOVERY .. RETIRE) and the next decision with the
  cheapest credible validation test.

The stage is a declaration, so it is checked against the arm's evidence
status: an arm can never be declared OPERATING without REVENUE_VERIFIED, and
a PLANNED arm cannot claim to be in a commercial test. Pure data and checks:
no network, no writes except through business_arms.write_state().

Directive arms A-J -> doctrine arms (no arm is renumbered or invented):
  A digital products          digital_products
  B productized AI services   productized_ai_services
  C micro-B2B solutions       micro_b2b
  D research-as-a-service     research_data_services
  E AI operations             ai_operations
  F affiliate intelligence    affiliate_intelligence
  G data products             research_data_services (shared arm; doctrine keeps them together)
  H content and distribution  content_distribution
  I children's media          childrens_media_studio
  J new ventures              not an arm: the opportunity engine (trend_to_product/, goos.py,
                              decision_engine/) proposes a new arm only with evidence
"""
from __future__ import annotations

from typing import Any, Dict, List

STAGES = ("DISCOVERY", "VALIDATION", "BUILD", "COMMERCIAL_TEST", "OPERATING", "SCALE_CANDIDATE", "HOLD", "RETIRE")

# Which stages an evidence status permits. A stage beyond these would claim
# more than business_arms can show.
ALLOWED_STAGES = {
    "PLANNED": {"DISCOVERY", "VALIDATION", "HOLD", "RETIRE"},
    "BLOCKED": {"DISCOVERY", "VALIDATION", "BUILD", "HOLD", "RETIRE"},
    "PARTIAL": {"DISCOVERY", "VALIDATION", "BUILD", "COMMERCIAL_TEST", "HOLD", "RETIRE"},
    "READY": {"BUILD", "COMMERCIAL_TEST", "HOLD", "RETIRE"},
    "REVENUE_VERIFIED": {"COMMERCIAL_TEST", "OPERATING", "SCALE_CANDIDATE", "HOLD", "RETIRE"},
}

DIRECTIVE_LETTERS = {
    "digital_products": ["A"], "productized_ai_services": ["B"], "micro_b2b": ["C"],
    "research_data_services": ["D", "G"], "ai_operations": ["E"], "affiliate_intelligence": ["F"],
    "content_distribution": ["H"], "childrens_media_studio": ["I"],
}

# Shared factory capabilities; arms list the ones they depend on.
SHARED_CAPABILITIES = {
    "opportunity_engine": "trend_to_product/, goos.py, decision_engine/ (evidence, scoring, duplication check)",
    "product_engineering_qa": "books/_batch14_src/b14_core.py, lib/xlsx_eval.py, native_workbook_qa.py, file_testing_engine.py",
    "catalog_registry": "product_registry.py -> data/product_registry.json",
    "publication_gate": "channels/publication_authorization.py, channels/write_gate.py, scripts/approve_products.py",
    "distribution_engine": "social_distribution/, scripts/distribution_cycle.py, scripts/pinterest_queue.py",
    "site_and_search": "customer_site/, scripts/tool_pages_daily.py, scripts/indexnow_auto.py",
    "visit_measurement": "NOT CONNECTED: no analytics receiver for the public site (backlog B6)",
    "commercial_measurement": "lib/commercial_funnel.js, commercial_reconciliation.py, channels/ledger.py",
    "experiments": "commercial_experiments.py, data/distribution_metrics.jsonl",
    "customer_intake": "partial: inquiries reach the founder by e-mail (mailto links on the site) and are recorded by hand "
                       "with `python inquiry_intake.py record-email`; the site cannot receive a form POST (GitHub Pages "
                       "answers 405), and contact.html's formsubmit.co relay activation is UNKNOWN",
    "payments": "Gumroad (live); Paddle key refused (403)",
    "incident_memory": "incident_memory.py, docs/factory/SHARED_FILE_EDITING.md",
}

PROFILES: Dict[str, Dict[str, Any]] = {
    "digital_products": {
        "mission": "sell useful, verified digital tools and guides that solve one specific job",
        "target_customers": "small-business owners, freelancers and households with a concrete calculation or tracking job",
        "revenue_model": "one-time digital purchase",
        "distribution": "Gumroad listings + site tool pages + search; social drafts pending approval",
        "stage": "COMMERCIAL_TEST",
        "stage_evidence": "109 listings live and verified; 0 sales (Gumroad, 2026-10-29)",
        "kpis": [
            {"kpi": "live verified listings", "source": "data/product_registry.json", "available": "OBSERVED"},
            {"kpi": "product-page visits", "source": "none (B6)", "available": "UNKNOWN"},
            {"kpi": "orders and gross", "source": "Gumroad /v2/sales via registry", "available": "OBSERVED"},
            {"kpi": "refunds, fees, net", "source": "no refund/fee feed", "available": "UNKNOWN"},
            {"kpi": "listings that deliver what they promise", "source": "reports/GUMROAD_DELIVERY_AUDIT_*.json", "available": "OBSERVED"},
        ],
        "depends_on": ["product_engineering_qa", "catalog_registry", "publication_gate", "site_and_search",
                       "visit_measurement", "payments", "commercial_measurement"],
        "continue_if": "a tracked distribution experiment produces qualified clicks, or the first sale arrives",
        "modify_if": "measured visits exist for 60 days without a sale: change offers, previews or prices, not volume",
        "stop_if": "never as a whole; individual listings that deliver less than promised are repaired or unpublished",
        "next_decision": {"owner": "founder",
                          "decision": "apply the listing repairs; choose a free visit-measurement receiver",
                          "cheapest_test": "EXP-B16-007-LI-01 (two LinkedIn posts, tracked links, 30-click floor per arm)"},
    },
    "micro_b2b": {
        "mission": "solve one narrow, recurring business data problem as a defined service",
        "target_customers": "small teams with messy spreadsheets (CRM exports, inventories, mailing lists)",
        "revenue_model": "fixed-scope service fee ($49 / $79 / $149 hypothesis, unvalidated)",
        "distribution": "service page + interest form; direct outreach not authorized",
        "stage": "BUILD",
        "stage_evidence": "two tested demonstrations on synthetic data: catalogue merge clean-up and a Merchant Center feed preflight (services/feed_preflight, rules cited from Google's spec); no customer engagement",
        "demonstration": "services/spreadsheet_normalization/demo_package/README.md",
        "kpis": [
            {"kpi": "qualified inquiries", "source": "data/customer_interest.jsonl", "available": "OBSERVED"},
            {"kpi": "engagements delivered", "source": "none yet", "available": "UNKNOWN"},
            {"kpi": "delivery hours per engagement", "source": "none yet", "available": "UNKNOWN"},
            {"kpi": "gross margin", "source": "none yet", "available": "UNKNOWN"},
        ],
        "depends_on": ["customer_intake", "site_and_search", "payments", "visit_measurement"],
        "continue_if": "an inquiry describes a real spreadsheet problem within scope",
        "modify_if": "inquiries arrive but are out of scope: narrow or re-target the offer",
        "stop_if": "no in-scope inquiry within 90 days of a live, measured offer page",
        "next_decision": {"owner": "founder",
                          "decision": "publish the service offer page with a working intake that reaches the founder",
                          "cheapest_test": "one sample before/after normalization shown on the page; count in-scope inquiries"},
    },
    "research_data_services": {
        "mission": "turn the factory's own research pipelines into briefs and datasets buyers can use",
        "target_customers": "sellers and small firms needing competitor, pricing or regulatory monitoring (hypothesis)",
        "revenue_model": "paid briefs or dataset access (hypothesis)",
        "distribution": "none yet",
        "stage": "BUILD",
        "stage_evidence": "two validated sample datasets with briefs (USPTO trademark fees; EAA penalty register, 7 countries tied to the statutes, two vendor figures contradicted); not offered",
        "demonstration": "services/research/eaa_penalty_register_brief_2026-10-29.md",
        "kpis": [
            {"kpi": "offers defined", "source": "none", "available": "UNKNOWN"},
            {"kpi": "inquiries", "source": "none", "available": "UNKNOWN"},
            {"kpi": "dataset freshness and rights recorded", "source": "data_products/datacard.py", "available": "OBSERVED"},
        ],
        "depends_on": ["opportunity_engine", "customer_intake"],
        "continue_if": "a buyer segment with a recurring information need is evidenced",
        "modify_if": "evidence points to a one-off report rather than a dataset",
        "stop_if": "no segment with willingness to pay is found after a documented search",
        "next_decision": {"owner": "factory",
                          "decision": "publish the free 7-country sample (page awaits approval); extend to the next EU markets by request count",
                          "cheapest_test": "a free sample brief on the site; count requests for the full register"},
    },
    "affiliate_intelligence": {
        "mission": "earn commissions by recommending tools that genuinely fit a reader's problem",
        "target_customers": "readers of comparison and how-to pages",
        "revenue_model": "affiliate commission (network-confirmed)",
        "distribution": "site comparison pages",
        "stage": "HOLD",
        "stage_evidence": "no approved affiliate account or tag; 0 outside clicks; Algeria payout routes conditional",
        "kpis": [
            {"kpi": "human (non-internal) clicks", "source": "affiliate_commerce click classification", "available": "OBSERVED"},
            {"kpi": "network-confirmed conversions", "source": "no network account", "available": "UNKNOWN"},
            {"kpi": "commissions confirmed or paid", "source": "data/commission_ledger.jsonl", "available": "OBSERVED"},
            {"kpi": "payout received", "source": "none", "available": "UNKNOWN"},
        ],
        "depends_on": ["site_and_search", "visit_measurement", "commercial_measurement"],
        "continue_if": "a program approves the account and confirms a payout route usable from Algeria",
        "modify_if": "approval only for programs with no audience fit",
        "stop_if": "no program with a verified payout route accepts the account",
        "next_decision": {"owner": "founder",
                          "decision": "apply to one program whose payout route is verified for Algeria",
                          "cheapest_test": "account approval plus one tagged link on an existing comparison page"},
    },
    "content_distribution": {
        "mission": "build qualified attention for every arm through channels where its buyers already are",
        "target_customers": "the buyers of the other arms",
        "revenue_model": "none directly; measured by attributable traffic and sales for other arms",
        "distribution": "Telegraph articles (live), Pinterest pins (board missing), LinkedIn/X drafts (founder posting), IndexNow",
        "stage": "VALIDATION",
        "stage_evidence": "8 Telegraph articles with 131 platform-reported views; no attributable click or sale measured",
        "kpis": [
            {"kpi": "platform views per article", "source": "data/distribution_metrics.jsonl (getViews)", "available": "OBSERVED"},
            {"kpi": "outbound clicks per post", "source": "platform analytics (founder) / not imported", "available": "UNKNOWN"},
            {"kpi": "attributable sessions and sales", "source": "UTM links; no site analytics", "available": "UNKNOWN"},
            {"kpi": "drafts prepared vs published", "source": "data/social_campaign_jobs.jsonl", "available": "OBSERVED"},
        ],
        "depends_on": ["distribution_engine", "experiments", "visit_measurement", "site_and_search"],
        "continue_if": "a channel produces measurable clicks toward an offer",
        "modify_if": "views without clicks: change the problem framing, not the volume",
        "stop_if": "a channel shows no measurable response after a fair experiment",
        "next_decision": {"owner": "founder",
                          "decision": "approve EXP-B16-007-LI-01; create the Pinterest board",
                          "cheapest_test": "two LinkedIn posts a week apart, 30 clicks per arm before any verdict"},
    },
    "ai_operations": {
        "mission": "offer the factory's automation patterns (monitoring, QA, reporting) as a service",
        "target_customers": "small operators running fragile automations (n8n, Zapier) (hypothesis)",
        "revenue_model": "setup fee or monthly monitoring (hypothesis)",
        "distribution": "none yet",
        "stage": "BUILD",
        "stage_evidence": "customer-safe n8n automation audit with a tested synthetic demonstration and a written offer; not offered",
        "demonstration": "services/automation_health/README.md",
        "kpis": [
            {"kpi": "offer defined", "source": "none", "available": "UNKNOWN"},
            {"kpi": "internal automations with tests", "source": "tests/ (CI groups)", "available": "OBSERVED"},
        ],
        "depends_on": ["incident_memory", "customer_intake"],
        "continue_if": "a buyer problem is evidenced (e.g. silent automation failures)",
        "modify_if": "demand is for a product (template, guide) rather than a service",
        "stop_if": "no evidence of willingness to pay for monitoring",
        "next_decision": {"owner": "factory",
                          "decision": "approve the audit offer page once a recorded intake exists",
                          "cheapest_test": "one guide page (an existing silent-failures article) with a tracked call to action"},
    },
    "productized_ai_services": {
        "mission": "deliver defined, repeatable AI-assisted services with human review",
        "target_customers": "small online shops and service sites with no accessibility review (hypothesis)",
        "revenue_model": "fixed-scope report fee ($39 for up to 10 pages, unvalidated)",
        "distribution": "none yet; own-site before/after planned as public proof",
        "stage": "BUILD",
        "stage_evidence": "accessibility quick-check implemented and tested (automated rules + human summary, no AI model); synthetic demo and a real run on our own 118 pages (0 errors, 22 warnings); not offered",
        "demonstration": "services/accessibility_check/README.md",
        "kpis": [{"kpi": "offer defined", "source": "services/accessibility_check/README.md", "available": "OBSERVED"},
                 {"kpi": "free checks requested", "source": "data/inquiries.jsonl", "available": "UNKNOWN"}],
        "depends_on": ["opportunity_engine", "customer_intake"],
        "continue_if": "one service can be delivered end to end with tested quality",
        "modify_if": "the service only works with heavy manual effort: price for it or drop it",
        "stop_if": "no tested delivery path exists",
        "next_decision": {"owner": "factory",
                          "decision": "fix our own 22 accessibility warnings and publish the before/after (a site change needs approval)",
                          "cheapest_test": "free 3-page check offered through the inquiry queue; count requests and fixes made"},
    },
    "childrens_media_studio": {
        "mission": "original Arabic-first educational animation for children 4-8",
        "target_customers": "parents and educators of Arabic-speaking young children",
        "revenue_model": "not yet chosen (platform revenue requires eligibility; licensing is an alternative)",
        "distribution": "none wired; publishing/ holds drafts only",
        "stage": "BUILD",
        "stage_evidence": "two verified animatics (ep01, ep02); no narration, scripts DRAFT pending native Arabic review",
        "kpis": [
            {"kpi": "verified episode renders", "source": "kids_studio/renders/*.verify.json", "available": "OBSERVED"},
            {"kpi": "finished episodes (voiced, reviewed)", "source": "kids_studio/production_manifest.json", "available": "OBSERVED"},
            {"kpi": "audience (views, watch time)", "source": "no channel", "available": "UNKNOWN"},
            {"kpi": "rights ledger complete", "source": "kids_studio/rights_ledger.json", "available": "OBSERVED"},
        ],
        "depends_on": ["incident_memory", "publication_gate"],
        "continue_if": "a native Arabic review approves the scripts and a licensed voice route exists",
        "modify_if": "voice route not available: subtitle-first format",
        "stop_if": "child-safety or rights review fails and cannot be fixed",
        "next_decision": {"owner": "founder",
                          "decision": "native Arabic script review and the narration route (founder decision recorded in the studio)",
                          "cheapest_test": "show the ep01 animatic to a few parents privately and record feedback"},
    },
}


# Current experiment per arm (2026-10-29). State is one of PENDING_APPROVAL,
# BLOCKED (with the reason), PREPARED or NONE; nothing here is running unless
# a founder approval is recorded in docs/factory/DISTRIBUTION_EXPERIMENT_2026-11.md.
EXPERIMENTS = {
    "digital_products": {"id": "EXP-B16-007-LI-01", "state": "PENDING_APPROVAL",
                         "what": "two LinkedIn variants for one product, 30 clicks per variant before a verdict"},
    "micro_b2b": {"id": "D2/D5", "state": "BLOCKED: offer page awaits founder approval (e-mail route ready)",
                  "what": "free feed preflight or catalogue clean-up for the first sellers who send a file"},
    "research_data_services": {"id": "D3/D7", "state": "BLOCKED: offer page awaits founder approval (e-mail route ready)",
                               "what": "free EAA register sample (7 countries); count requests for the full register"},
    "affiliate_intelligence": {"id": None, "state": "NONE", "what": "on hold until a payout route is verified"},
    "content_distribution": {"id": None, "state": "BLOCKED: no visit measurement",
                             "what": "Telegraph counters read daily (platform counter, includes bots)"},
    "ai_operations": {"id": "D4", "state": "BLOCKED: offer page awaits founder approval; forum rules unread",
                      "what": "free read-only n8n audit for a few instances in exchange for feedback"},
    "productized_ai_services": {"id": "D6", "state": "PREPARED",
                                "what": "fix our own 22 accessibility warnings and publish the before/after, then a free 3-page check"},
    "childrens_media_studio": {"id": "KF-ep01", "state": "PREPARED",
                               "what": "private parent feedback on the ep01 animatic; protocol and privacy-safe recorder in kids_studio/feedback/ (founder shows it)"},
}


def validate(state: Dict[str, Any], profiles: Dict[str, Dict[str, Any]] = None) -> List[str]:
    """Problems: a missing profile, an unknown stage, or a stage the evidence status does not permit."""
    profiles = PROFILES if profiles is None else profiles
    problems = []
    arms = (state or {}).get("arms") or {}
    for key, arm in arms.items():
        p = profiles.get(key)
        if not p:
            problems.append("%s: no portfolio profile" % key)
            continue
        stage = p.get("stage")
        if stage not in STAGES:
            problems.append("%s: unknown stage %s" % (key, stage))
            continue
        if stage not in ALLOWED_STAGES.get(arm.get("status"), set()):
            problems.append("%s: stage %s not supported by evidence status %s" % (key, stage, arm.get("status")))
        for k in ("mission", "revenue_model", "next_decision", "continue_if", "stop_if"):
            if not p.get(k):
                problems.append("%s: profile lacks %s" % (key, k))
        for dep in p.get("depends_on", []):
            if dep not in SHARED_CAPABILITIES:
                problems.append("%s: unknown shared capability %s" % (key, dep))
    for key in profiles:
        if key not in arms:
            problems.append("%s: profile for an arm business_arms does not define" % key)
    return problems


def summary(state: Dict[str, Any]) -> Dict[str, Any]:
    """Profiles joined with the live evidence status, plus portfolio-level views."""
    arms = (state or {}).get("arms") or {}
    rows = []
    for key, p in PROFILES.items():
        a = arms.get(key, {})
        known = sum(1 for k in p["kpis"] if k["available"] == "OBSERVED")
        rows.append({"arm": key, "name": a.get("name"), "letters": DIRECTIVE_LETTERS.get(key, []),
                     "evidence_status": a.get("status"), "stage": p["stage"], "stage_evidence": p["stage_evidence"],
                     "mission": p["mission"], "target_customers": p["target_customers"],
                     "revenue_model": p["revenue_model"], "distribution": p["distribution"],
                     "kpis": p["kpis"], "kpis_measurable": "%d of %d" % (known, len(p["kpis"])),
                     "depends_on": p["depends_on"], "continue_if": p["continue_if"], "modify_if": p["modify_if"],
                     "stop_if": p["stop_if"], "next_decision": p["next_decision"], "demonstration": p.get("demonstration"),
                     "experiment": EXPERIMENTS.get(key, {"id": None, "state": "NONE", "what": ""})})
    by_stage = {s: [r["arm"] for r in rows if r["stage"] == s] for s in STAGES}
    dependency_load = {}
    for r in rows:
        for d in r["depends_on"]:
            dependency_load.setdefault(d, []).append(r["arm"])
    bottlenecks = sorted(((d, users) for d, users in dependency_load.items()
                          if SHARED_CAPABILITIES[d].startswith("NOT CONNECTED") or "refused" in SHARED_CAPABILITIES[d]
                          or "cannot" in SHARED_CAPABILITIES[d]), key=lambda x: -len(x[1]))
    return {
        "arms": rows,
        "by_stage": {s: v for s, v in by_stage.items() if v},
        "shared_capabilities": SHARED_CAPABILITIES,
        "dependency_load": dependency_load,
        "bottlenecks": [{"capability": d, "state": SHARED_CAPABILITIES[d], "blocks": users} for d, users in bottlenecks],
        "ready_for_controlled_validation": [{"arm": r["arm"], "demonstration": r["demonstration"]}
                                            for r in rows if r.get("demonstration")],
        "founder_decisions": [{"arm": r["arm"], **r["next_decision"]} for r in rows if r["next_decision"]["owner"] == "founder"],
        "factory_decisions": [{"arm": r["arm"], **r["next_decision"]} for r in rows if r["next_decision"]["owner"] == "factory"],
        "unmapped_directive_arms": {"J": "new ventures: proposed by the opportunity engine, not a standing arm"},
        "problems": validate(state),
        "note": "Stage is declared here and checked against the evidence status in business_arms.py; no arm is OPERATING until REVENUE_VERIFIED.",
    }

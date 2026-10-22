#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — The 24 affiliate workstreams (founder mandate, 2026-10-22).

A workstream is a buyer-problem area to evaluate, not a guaranteed niche.
Definitions are static here; candidate programs are referenced by registry
opportunity_id (never copied), and each workstream's state is derived live
from data/commission_opportunities.jsonl plus the eligibility matrix, so
there is no second program registry to drift. Workstreams 22-24 are content
formats that apply to programs from other workstreams.

No historical 24-stage list existed in the repo (searched 2026-10-22), so the
mandate's list is used as the original mapping. Read-only. No network.
"""
from datetime import datetime, timezone

from . import opportunity_rank, registry

_WS = [
    # id, group, name, buyer problem, target buyer, candidate opportunity_ids, content ideas, risk
    ("WS-01", "business_ops", "CRM and sales pipeline tools",
     "Leads and deals get lost in spreadsheets and inboxes", "Small B2B teams, consultants", [],
     ["CRM comparison for 1-5 person teams"], "medium"),
    ("WS-02", "business_ops", "Email marketing and lead management",
     "Needs a list, forms and automated emails without a developer", "Creators, small businesses",
     ["CO-systeme-affiliate", "CO-brevo-affiliate", "CO-aweber-affiliate"],
     ["free-plan email tool comparison", "first automated welcome sequence tutorial"], "low"),
    ("WS-03", "business_ops", "Website builders and ecommerce platforms",
     "Wants a site or store live without hiring", "Solo founders, coaches, sellers",
     ["CO-systeme-affiliate"], ["sales funnel builder comparison"], "low"),
    ("WS-04", "business_ops", "Project management, collaboration, remote work",
     "Remote work loses track of tasks and decisions", "Remote teams, agencies", [],
     ["PM tool picker by team size"], "medium"),
    ("WS-05", "business_ops", "Accounting, invoicing, freelancer business tools",
     "Invoices, expenses and taxes eat billable time", "Freelancers", [],
     ["freelancer invoicing tool guide"], "high"),
    ("WS-06", "business_ops", "Workflow automation and app integration",
     "Repetitive copy-paste work between apps", "Ops-minded small businesses",
     ["CO-n8n-affiliate", "CO-zapier-affiliate"],
     ["n8n vs Zapier for a small business", "self-hosted automation setup guide"], "low"),
    ("WS-07", "ai_productivity", "AI writing, research and knowledge tools",
     "Drafting and research take too long", "Marketers, analysts", [],
     ["AI research tool comparison"], "medium"),
    ("WS-08", "ai_productivity", "AI audio, video and content production",
     "Producing video/audio is slow and costly", "Creators", [],
     ["AI video tool picker"], "medium"),
    ("WS-09", "ai_productivity", "Customer support and conversational automation",
     "Support volume outgrows the team", "SaaS and ecommerce support leads", [],
     ["helpdesk + chatbot comparison"], "medium"),
    ("WS-10", "ai_productivity", "Analytics, reporting and business intelligence",
     "No clear view of revenue and churn", "SaaS founders", [],
     ["subscription analytics tool guide"], "medium"),
    ("WS-11", "ecommerce_ops", "Store management, inventory and merchandising",
     "Running a store across channels is manual", "Online sellers",
     ["CO-etsy-affiliate", "CO-amazon-affiliate"], ["marketplace seller toolkit"], "medium"),
    ("WS-12", "ecommerce_ops", "Email lifecycle automation and cart recovery",
     "Abandoned carts and one-time buyers", "Ecommerce stores",
     ["CO-brevo-affiliate", "CO-systeme-affiliate"], ["cart recovery sequence tutorial"], "low"),
    ("WS-13", "ecommerce_ops", "Product research and competitor intelligence",
     "Picking products without demand data", "New sellers", [],
     ["product research method guide"], "high"),
    ("WS-14", "ecommerce_ops", "Shipping, order operations and support",
     "Order handling breaks as volume grows", "Growing stores", [],
     ["shipping software comparison"], "high"),
    ("WS-15", "content_distribution", "Video editing and production",
     "Editing takes longer than recording", "Creators, marketers",
     ["CO-adobe-affiliate"], ["video editor comparison for beginners"], "medium"),
    ("WS-16", "content_distribution", "Design, creative tools, presentations",
     "Needs professional visuals without a designer", "Small businesses, creators",
     ["CO-canva-affiliate", "CO-adobe-affiliate", "CO-creative_market-affiliate", "CO-envato-affiliate"],
     ["design asset marketplace comparison"], "medium"),
    ("WS-17", "content_distribution", "Content-channel management and analytics",
     "Publishing to many channels is chaotic", "Social media managers", [],
     ["scheduling tool comparison"], "medium"),
    ("WS-18", "content_distribution", "Digital product creation and selling platforms",
     "Wants to sell a course, ebook or template", "Creators, educators",
     ["CO-systeme-affiliate", "CO-gumroad-affiliate"],
     ["where to sell digital products: honest comparison"], "low"),
    ("WS-19", "infrastructure", "Hosting, domains and infrastructure",
     "Needs reliable, affordable hosting", "Site owners, developers",
     ["CO-digitalocean-affiliate", "CO-siteground-affiliate"],
     ["hosting choice for a small business site", "self-hosting n8n on a VPS"], "medium"),
    ("WS-20", "infrastructure", "Security, backup and password management",
     "Weak passwords and no backups", "Small teams", [],
     ["password manager guide for teams"], "medium"),
    ("WS-21", "infrastructure", "Documentation, knowledge management, document search",
     "Knowledge scattered across files and chats", "Teams, consultants",
     ["CO-google-affiliate"], ["team wiki tool comparison"], "medium"),
    ("WS-22", "commercial_content", "Product comparisons and alternatives",
     "Buyer is choosing between named tools", "Buyers late in research", None,
     ["X vs Y", "best alternatives to X"], "medium"),
    ("WS-23", "commercial_content", "Migration guides and tool-switching tutorials",
     "Buyer wants to switch without losing data", "Users of a tool they outgrew", None,
     ["migrate from X to Y step by step"], "low"),
    ("WS-24", "commercial_content", "Profession-specific and industry buying guides",
     "Generic tool lists don't fit their profession", "Specific professions", None,
     ["tool stack for accountants / coaches / agencies"], "medium"),
]

REQUIRED_ASSETS = ["program evaluation", "eligibility and payout check", "one original guide",
                   "disclosure statement", "QA checklist pass"]


def workstream_registry(opportunities=None, evidence=None, now=None):
    opps = opportunities if opportunities is not None else registry.load_opportunities()
    ranked = {r["opportunity_id"]: r for r in opportunity_rank.rank(opps, evidence)}
    known = set(ranked)
    rows = []
    for wid, group, name, problem, buyer, cands, content, risk in _WS:
        cross_cutting = cands is None
        if cross_cutting:
            ids = [oid for oid, r in ranked.items() if r["rankable"]]
        else:
            ids = list(cands)
        present = [i for i in ids if i in known]
        missing = [i for i in ids if i not in known]
        cand = sorted((ranked[i] for i in present), key=lambda r: r["final_score"], reverse=True)
        best = cand[0] if cand else None
        if not present:
            state, task = "NO_CANDIDATE", "discover programs for this buyer problem from official sources"
        elif any(c["components"]["payout_state"] == "PAYOUT_VERIFIED" for c in cand):
            state, task = "READY_FOR_ASSET", "prepare the first original asset"
        elif any(c["components"]["eligibility_state"] == "ELIGIBLE_EVIDENCE_FOUND" for c in cand):
            state, task = "PAYOUT_HOLD", best["next_action"]
        else:
            state, task = "VERIFYING", best["next_action"]
        rows.append({
            "workstream_id": wid, "group": group, "name": name,
            "buyer_problem": problem, "target_buyer": buyer,
            "candidate_programs": [{"opportunity_id": c["opportunity_id"], "final_score": c["final_score"],
                                    "eligibility_state": c["components"]["eligibility_state"],
                                    "payout_state": c["components"]["payout_state"]} for c in cand],
            "missing_from_registry": missing,
            "cross_cutting_format": cross_cutting,
            "content_opportunities": content, "required_assets": REQUIRED_ASSETS,
            "risk": risk, "state": state, "next_task": task,
            "demand_evidence": "UNKNOWN",
            "last_derived": (now or datetime.now(timezone.utc)).isoformat(),
        })
    return rows

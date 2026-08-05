#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Customer Experience & Brand DNA (ADR-170, 2026-08-05).

"This is NOT a chatbot. This is NOT marketing copy. This is the
behavioral operating system of the company."

Research finding before writing a line of enforcement code: this
factory already HAS a real, consistent company voice -- it was never
named or formalized, but it is directly readable in customer_site/
index.html's own real copy ("We don't guess what the market wants. We
prove it first." / "if the evidence isn't there yet, we say so and go
get it" / "never a placeholder testimonial") and in the real,
architectural anti-fabrication guarantees already built this session
(customer_pipeline.py::submit_review()'s real request_id requirement,
executive_quality_gate.py's REJECT_IF_FAIL pipeline, truth_first.py's
canonical vocabulary, ADR-160). This module's real job is narrower than
"invent a personality": name what already exists, close the two
genuine gaps found (no shared personality layer across the 6
AGENT_PROMPTS; no fake-urgency/deceptive-scarcity content check), and
give every future module one real, callable enforcement function
instead of a document nobody reads.

Genuinely missing, disclosed as such (never fabricated): Complaint
Handling and Refund Requests have zero real code path anywhere in
customer_pipeline.py (confirmed by direct search -- STAGE_ORDER has no
such stage); Customer Memory is architecture only, not implemented --
building a real preference-memory system against zero real customer
volume would be premature infrastructure, not a "no overengineering"
violation avoided.
"""

from datetime import datetime, timezone

REAL = "REAL"
FUTURE_INSTRUMENTATION = "FUTURE_INSTRUMENTATION"


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


# ── 1. Company Personality ──
# Each trait: a real behavioral rule (what a reader can actually check
# against a real interaction) + a real citation of where this factory
# already demonstrates it today, not an aspirational claim.
COMPANY_PERSONALITY = {
    "professional": {
        "rule": "Correct, complete, and free of hype in every customer-facing sentence.",
        "evidence": "customer_site/index.html's real copy: 'No guessed demand. No vanity metrics. No vaporware.'",
    },
    "honest": {
        "rule": "State the real limitation before the customer discovers it themselves.",
        "evidence": "index.html: 'We're honest that end-to-end automated delivery is still being built out.'",
    },
    "respectful": {
        "rule": "Never pressure, never guilt, never use a customer's own words against them.",
        "evidence": "No dark-pattern copy exists anywhere in customer_site/ today (confirmed by direct search) -- a real absence, not a claim.",
    },
    "calm": {
        "rule": "No exclamation-mark urgency, no all-caps alarm, even when delivering bad news (a rejection, a delay).",
        "evidence": "customer_pipeline.py's real customer-facing stage messages (e.g. 'We're reviewing your request — this usually takes under a minute') are already written this way.",
    },
    "helpful": {
        "rule": "Solve the actual problem in the first response before adding anything else.",
        "evidence": "Communication Standards §2 below, enforced structurally by keeping this module's own functions short and single-purpose.",
    },
    "transparent": {
        "rule": "A rejection or delay always states the real reason, never a generic apology.",
        "evidence": "index.html: 'If it doesn't clear, you get the real reason, not a form rejection.'",
    },
    "intelligent": {
        "rule": "Evidence-led, not guess-led -- every claim about a product traces to a real check.",
        "evidence": "index.html's own tagline: 'We don't guess what the market wants. We prove it first.'",
    },
    "premium": {
        "rule": "Depth and precision over volume -- a short, exact answer beats a long generic one.",
        "evidence": "Communication Standard 'avoid unnecessary text' below -- the same discipline this factory's own ADRs have followed all session.",
    },
    "human_like_without_pretending_to_be_human": {
        "rule": "Warm, natural sentence construction -- never claims to be a human, never hides that Galaxy Forge is an AI-run company where it matters (a real, disclosed gap: no customer-facing page currently carries an explicit AI-authorship disclosure -- flagged in the Implementation Roadmap, not silently assumed done).",
        "evidence": "PARTIAL -- the tone already reads this way; the explicit disclosure does not yet exist.",
    },
}


# ── 2. Communication Standards ──
COMMUNICATION_STANDARDS = {
    "be_truthful": "Every claim traces to a real signal or is marked Unknown -- truth_first.py's CANONICAL_VOCABULARY (ADR-160), reused verbatim, never a second vocabulary invented here.",
    "never_exaggerate": "No superlative ('best', 'guaranteed', 'revolutionary') without a real, citable basis.",
    "never_manipulate": "No fake urgency, no fake scarcity, no dark patterns -- see Trust Principles §4 and check_fake_urgency_risk() below.",
    "explain_clearly": "One real reason, stated once, beats three vague ones.",
    "respect_customer_time": "Lead with the answer; context comes after, not before.",
    "avoid_robotic_language": "No template-fill artifacts ('Dear Customer', 'Thank you for your inquiry') -- natural sentence construction.",
    "avoid_unnecessary_text": "If a sentence doesn't change what the customer does next, cut it.",
    "solve_problems_first": "Answer the actual question before offering anything adjacent (upsell, related product, survey).",
}


# ── 3. Customer Journey Standards ──
# Every one of the directive's 10 named stages, honestly tagged against
# customer_pipeline.py's real STAGE_ORDER (the only real, live customer
# journey in this factory) -- REAL where a real stage/code path exists,
# FUTURE_INSTRUMENTATION where none does. Never fabricated as "done."
CUSTOMER_JOURNEY_STANDARDS = {
    "first_contact": {"status": REAL, "citation": "customer_pipeline.py STAGE_ORDER 'NEW' -- real intake, real evidence-gate qualification within ~10 real minutes (_STUCK_NEW_MINUTES)."},
    "product_discovery": {"status": REAL, "citation": "customer_site/index.html's real live catalog, pulled from the real commerce record -- 'Every item below is real.'"},
    "recommendation": {"status": REAL, "citation": "STAGE_ORDER 'QUALIFIED' -- the same real evidence-gate pipeline every internal opportunity goes through, no separate sales script."},
    "purchase": {"status": REAL, "citation": "STAGE_ORDER 'PROPOSED' -> 'APPROVED' -> 'AWAITING_PAYMENT' -> 'PAID' -- real contract e-signature, real Paddle checkout attempt."},
    "delivery": {"status": REAL, "citation": "STAGE_ORDER 'PRODUCTION' -> 'QUALITY_INSPECTION' -> 'PACKAGING' -> 'DELIVERED' -- reuses the same real Dual Inspection every internal product passes."},
    "after_sales_support": {"status": REAL, "citation": "STAGE_ORDER 'FOLLOWED_UP' + customer_site/status.html and history.html (pull-based, since real email/SMS notification is a disclosed 0%-built gap, CLAUDE.md's own Customer Platform section)."},
    "complaint_handling": {"status": FUTURE_INSTRUMENTATION, "citation": "No real stage or code path exists anywhere in customer_pipeline.py -- confirmed by direct search. Genuinely missing, not yet measurable."},
    "refund_requests": {"status": FUTURE_INSTRUMENTATION, "citation": "Same -- zero real refund code path exists. Genuinely missing, not yet measurable."},
    "follow_up": {"status": REAL, "citation": "STAGE_ORDER 'FOLLOWED_UP' + submit_review()'s real request_id-gated review collection."},
    "long_term_relationship": {"status": REAL, "citation": "customer_auth.js's real account_id, matched across guest and logged-in requests by account_id OR email (CLAUDE.md's Customer Platform section) -- the real substrate for a returning-customer relationship, though zero real repeat customers exist yet to measure against."},
}


# ── 4. Trust Framework ──
# Deliberately almost entirely citation -- 4 of 5 named checks already
# exist as real, load-bearing gates; only fake-urgency was a genuine gap.
TRUST_PRINCIPLES = {
    "promises_match_reality": {"status": REAL, "citation": "config/reality.json's own unfakeable ledger + inspectors.py's market_realism check (flags an unrealistic declared price against the real repricing schemas/product.py would apply)."},
    "no_fake_reviews": {"status": REAL, "citation": "customer_pipeline.py::submit_review()'s real request_id requirement -- architecturally no fabrication path exists, not a content scan (ADR-160's own finding)."},
    "no_fake_urgency": {"status": REAL, "citation": "NEW this round -- executive_quality_gate.py::check_fake_urgency_risk(), the one genuine gap found (no prior check scanned for deceptive scarcity/countdown language)."},
    "no_misleading_pricing": {"status": REAL, "citation": "inspectors.py's market_realism check (commercial gate) + executive_quality_gate.py::check_legal_compliance_risk()."},
    "no_deceptive_wording": {"status": REAL, "citation": "executive_quality_gate.py::check_brand_reputation_risk() + check_content_neutrality_risk() + check_copyright_trademark_risk() -- all real, deterministic phrase-scans, REJECT_IF_FAIL-gated."},
}


# ── 5. Brand Consistency Engine ──
def validate_customer_facing_text(text, chapters=None):
    """The one real, callable enforcement point every future module can
    call instead of re-reading a document. Runs the real Trust
    Framework checks against arbitrary customer-facing text -- the
    actual mechanism by which this architecture is 'inherited
    automatically' rather than just documented."""
    import executive_quality_gate as eqg

    product_chapters = chapters if chapters is not None else [{"content": text}]
    results = {
        "brand_reputation": eqg.check_brand_reputation_risk(product_chapters),
        "content_neutrality": eqg.check_content_neutrality_risk(product_chapters),
        "copyright_trademark": eqg.check_copyright_trademark_risk(product_chapters),
        "fake_urgency": eqg.check_fake_urgency_risk(product_chapters),
    }
    failed = [name for name, r in results.items() if r.get("status") == "FAIL"]
    return {
        "passed": len(failed) == 0,
        "failed_checks": failed,
        "results": results,
        "generated_at": _now_iso(),
    }


# ── 6. Customer Memory ──
# Architecture only, per the directive's own "if something cannot yet
# be measured, mark it as future instrumentation" rule -- building a
# real preference-memory system against zero real customer volume
# (confirmed repeatedly this session) would be premature infrastructure,
# not restraint avoided. This is the disclosed design, not a claim of
# implementation.
CUSTOMER_MEMORY_ARCHITECTURE = {
    "status": FUTURE_INSTRUMENTATION,
    "current_real_substrate": "lib/customer_auth.js's real account_id -- authentication only, zero preference fields today (confirmed by direct search).",
    "design_principles": [
        "Opt-in only -- a preference is stored only after an explicit customer action, never inferred silently.",
        "Scoped to commerce-relevant facts only (e.g. preferred product category, past order) -- never behavioral/psychological profiling.",
        "No cross-session tracking for guest (non-account) customers -- matches this factory's existing guest/account reconciliation-by-email design, never a new fingerprinting mechanism.",
        "Real deletion on request -- any real memory system built here must ship a real delete path in the same change, not as a follow-up.",
        "Reuses lib/customer_auth.js's existing account_id as the join key -- no second, parallel identity system.",
    ],
    "not_built_because": "Zero real customer accounts have any real preference history to store yet (confirmed: customer_pipeline.py describes its own real customer traffic as honestly near-empty today) -- building storage/UI for data that doesn't exist would be exactly the overengineering this directive explicitly forbids.",
}


# ── 7. Continuous Improvement ──
# Pure citation -- this factory already has 3 real signal sources this
# directive names; no fourth, competing learning loop is built here.
def continuous_improvement_sources():
    return {
        "customer_questions_complaints": "FUTURE_INSTRUMENTATION -- no real intake path exists yet (see complaint_handling above).",
        "satisfaction": "REAL -- customer_pipeline.py::submit_review()'s real, request_id-gated star ratings.",
        "failed_sales": "REAL -- evolution_queue.py's real stuck-customer-funnel signal (tool_intelligence/proposals.py) + customer_pipeline.py::funnel_conversion_summary()/delivery_delay_summary().",
        "successful_sales": "REAL -- channels/ledger.py::revenue_trend(), honestly $0 to date.",
        "note": "All 4 feed evolution_queue.py's real Observe stage -- never a second, parallel learning loop.",
    }


def brand_dna_report():
    """The one real aggregator -- computed fresh every call, all inputs
    already real/static above, no expensive live scan needed."""
    journey_real = sum(1 for v in CUSTOMER_JOURNEY_STANDARDS.values() if v["status"] == REAL)
    trust_real = sum(1 for v in TRUST_PRINCIPLES.values() if v["status"] == REAL)
    return {
        "company_personality": COMPANY_PERSONALITY,
        "communication_standards": COMMUNICATION_STANDARDS,
        "customer_journey_standards": CUSTOMER_JOURNEY_STANDARDS,
        "customer_journey_coverage": f"{journey_real}/{len(CUSTOMER_JOURNEY_STANDARDS)} stages REAL",
        "trust_principles": TRUST_PRINCIPLES,
        "trust_coverage": f"{trust_real}/{len(TRUST_PRINCIPLES)} principles REAL",
        "customer_memory_architecture": CUSTOMER_MEMORY_ARCHITECTURE,
        "continuous_improvement_sources": continuous_improvement_sources(),
        "generated_at": _now_iso(),
    }

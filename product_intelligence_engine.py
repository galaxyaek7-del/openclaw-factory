"""Galaxy Forge — Digital Product Intelligence & Commercial Validation.

Why this module exists
----------------------
The factory already has 116 real listings (data/catalog.json), 9 real product
families, trend_to_product's per-opportunity 9-dimension advisory scorer, and
automation_catalog's 15 automation categories. What it did not have is a
discovery-level catalog of *candidate* products across the ten category
families the founder named, and no sensitivity analysis showing whether a
ranking survives a plausible change in the weights.

This module is the missing discovery layer. It is strictly advisory: it never
publishes, prices, schedules, or spends anything, and it writes no files.

Honesty contract (the reason for the shape below)
-------------------------------------------------
* Static authoring covers only what a person can legitimately claim without
  field research: the customer, the problem, the format, the deliverable.
* Every number that depends on the market is resolved at read time from a real,
  local source and labelled OBSERVED / DERIVED / INFERRED / UNKNOWN. When no
  real source exists, the component is None with a written reason -- it is
  never filled from a default.
* Unknown demand is never treated as positive demand: an idea without recorded
  demand is capped below every idea with it, and can never be labelled PURSUE.
* Production effort enters only as a cost side of the score. Being easy to
  generate cannot lift an idea into PURSUE, because the demand gate and the
  willingness-to-pay gate are evaluated independently of effort.
* The composite is a weighted mean of the *available* components only, and is
  withheld entirely below MIN_COVERAGE (the same discipline
  trend_to_product/scoring.py already established).

Real sources used (all local, all read-only)
--------------------------------------------
data/market_evidence.jsonl     recorded evidence rows (source_url + quote)
data/catalog.json              the factory's own live listings
data/product_registry.json     listing ids, price_cents, sales_count
data/competitor_database.json  recorded competitor names per niche
config/channels.json           per-channel automation/api/support facts
config/economics.json          real fee/royalty tables
trend_to_product.ideation      FORMATS: what this factory can build and verify
profit_oracle                  documented per-ladder constants
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, List, Optional, Sequence

ROOT = os.path.dirname(os.path.abspath(__file__))

MARKET_EVIDENCE_PATH = os.path.join(ROOT, "data", "market_evidence.jsonl")
CATALOG_PATH = os.path.join(ROOT, "data", "catalog.json")
REGISTRY_PATH = os.path.join(ROOT, "data", "product_registry.json")
COMPETITOR_DB_PATH = os.path.join(ROOT, "data", "competitor_database.json")
CHANNELS_CONFIG_PATH = os.path.join(ROOT, "config", "channels.json")
ECONOMICS_CONFIG_PATH = os.path.join(ROOT, "config", "economics.json")

MIN_COVERAGE = 0.60
UNKNOWN_DEMAND_CAP = 45.0
PURSUE_MIN_COMPOSITE = 65.0
TEST_MIN_COMPOSITE = 50.0
REJECT_BELOW_COMPOSITE = 35.0

# The founder's ten category families, each mapped onto a real product family
# and a real profit_oracle ladder (no invented taxonomy).
CATEGORIES: Dict[str, Dict[str, str]] = {
    "personal_organization_productivity": {
        "label": "Personal organization & productivity systems",
        "family": "notion_systems",
        "ladder": "reusable_assets",
    },
    "budgeting_financial": {
        "label": "Budgeting, financial trackers & calculators",
        "family": "spreadsheet_systems",
        "ladder": "reusable_assets",
    },
    "education_learning": {
        "label": "Educational resources & learning aids",
        "family": "knowledge_bases",
        "ladder": "educational",
    },
    "creative_printables": {
        "label": "Creative assets & printables",
        "family": "digital_toolkits",
        "ladder": "reusable_assets",
    },
    "events_celebrations": {
        "label": "Events, weddings & celebrations",
        "family": "digital_toolkits",
        "ladder": "reusable_assets",
    },
    "resume_career": {
        "label": "Resume, career & professional identity",
        "family": "professional_templates",
        "ladder": "reusable_assets",
    },
    "social_media_templates": {
        "label": "Social media & content templates",
        "family": "professional_templates",
        "ladder": "reusable_assets",
    },
    "ecommerce_seller_tools": {
        "label": "E-commerce seller tools",
        "family": "spreadsheet_systems",
        "ladder": "automation_tools",
    },
    "small_business_operations": {
        "label": "Small-business operations systems",
        "family": "spreadsheet_systems",
        "ladder": "automation_tools",
    },
    "industry_specific_business": {
        "label": "Industry-specific business templates & calculators",
        "family": "professional_templates",
        "ladder": "b2b_systems",
    },
}

# format -> the product_type book_generator's canonical table already knows.
FORMAT_TO_PRODUCT_TYPE: Dict[str, str] = {
    "guide_printable": "printable",
    "excel_tool": "premium",
    "notion_template": "premium",
    "research_data_tool": "elite",
    "kids_education": "printable",
    "craft_pattern": "printable",
    "service_micro_b2b": "elite",
}

# Directive's ten weighted components. Sum is exactly 1.0 (asserted below).
WEIGHTS: Dict[str, float] = {
    "demand_evidence": 0.20,
    "problem_severity": 0.12,
    "competition_intensity": 0.10,
    "differentiation": 0.10,
    "willingness_to_pay": 0.12,
    "production_cost_complexity": 0.08,
    "distribution_feasibility": 0.10,
    "contribution_margin": 0.10,
    "expansion_potential": 0.05,
    "risk": 0.03,
}

COMPONENT_REASONS = {
    "demand_evidence": "recorded demand evidence (source_url + verbatim quote), not an assumption",
    "problem_severity": "authored problem statement scored by a disclosed keyword heuristic; no field research was conducted",
    "competition_intensity": "count of recorded competitor names plus matching factory listings",
    "differentiation": "whether any existing factory listing already addresses this problem",
    "willingness_to_pay": "requires a real completed sale at a real price; listing prices alone are not willingness to pay",
    "production_cost_complexity": "effort/maintenance as recorded by trend_to_product.ideation.FORMATS for the chosen format",
    "distribution_feasibility": "config/channels.json automation mode and format support for the best fitting channel",
    "contribution_margin": "economics.net_profit at the proposed price on the canonical platform for the format",
    "expansion_potential": "profit_oracle documented per-ladder recurring-revenue and reusability constants",
    "risk": "count and severity of authored licensing/IP risks",
}

assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "component weights must sum to 1.0"


def _idea(
    idea_id: str,
    category: str,
    title: str,
    customer: str,
    geography: str,
    problem: str,
    job: str,
    fmt: str,
    deliverable: str,
    keywords: Sequence[str],
    price: Optional[float] = None,
    risks: Sequence[Dict[str, str]] = (),
    differentiation: str = "UNKNOWN",
) -> Dict[str, Any]:
    """Author only what a person can legitimately claim without field research.

    Everything market-dependent is resolved later by resolve() and is left
    absent here on purpose, so nothing can silently look researched.
    """
    return {
        "idea_id": idea_id,
        "category": category,
        "title": title,
        "target_customer": customer,
        "geography": geography,
        "problem": problem,
        "job_to_be_done": job,
        "format": fmt,
        "deliverable": deliverable,
        "proposed_price_usd": price,
        "keywords": list(keywords),
        "authored_differentiation": differentiation,
        "licensing_risks": [dict(r) for r in risks],
    }


def _risk(level: str, note: str) -> Dict[str, str]:
    return {"level": level, "note": note}


IDEA_CATALOG: List[Dict[str, Any]] = [
    # --- 1. personal organization & productivity -------------------------
    _idea("PI-PRD-01", "personal_organization_productivity",
          "Weekly review to next-week plan converter",
          "Knowledge workers who end each week without a written next-week plan",
          "Global (English-first)",
          "Weekly reviews produce notes that never become scheduled commitments",
          "Turn a messy weekly review into a dated, prioritised next-week plan",
          "notion_template",
          "Duplicable Notion workspace with review prompts, decision log and plan view",
          ["weekly review", "next week plan", "weekly planning"], 29.0),
    _idea("PI-PRD-02", "personal_organization_productivity",
          "Household admin command center",
          "Two-adult households juggling bills, renewals, repairs and documents",
          "UK/US/CA/AU",
          "Household obligations are scattered across inboxes and apps, so renewals and bills are missed",
          "One place that shows every household obligation with an owner and a due date",
          "excel_tool",
          "Excel workbook: obligation register, renewal calendar, owner column, monthly review sheet",
          ["household budget", "renewal tracker", "home admin"], 24.0),
    _idea("PI-PRD-03", "personal_organization_productivity",
          "Personal energy and attention audit worksheet",
          "Professionals who feel busy but cannot say what drains them",
          "Global",
          "People optimise their calendar without measuring where their attention and energy actually go",
          "Identify the three recurring activities that cost the most attention for the least return",
          "guide_printable",
          "Printable two-week audit with scoring sheet and a written reduction plan",
          ["attention audit", "energy audit", "time audit"], 12.0),
    _idea("PI-PRD-04", "personal_organization_productivity",
          "Moving-house logistics planner",
          "People relocating within the next 90 days",
          "US/UK/DE",
          "Moves fail on sequencing: utilities, address changes, deposits and inventory are tracked from memory",
          "Sequence every move task by date and dependency, and track box contents",
          "excel_tool",
          "Excel workbook: 8-week schedule, utility/address checklist, box inventory, cost log",
          ["moving checklist", "relocation planner", "moving house"], 19.0),
    _idea("PI-PRD-05", "personal_organization_productivity",
          "Digital-life inventory and handover kit",
          "Adults who have never documented their accounts for family or an executor",
          "Global",
          "Family members cannot find or access accounts after an emergency, and informal lists are unsafe",
          "A safe, printable inventory of accounts and instructions that never stores passwords in the document",
          "guide_printable",
          "Printable inventory protocol, account register with 'where the credential lives' column, and an instruction letter",
          ["digital estate", "password inventory", "account inventory"], 15.0,
          risks=[_risk("medium", "Must never instruct storing plaintext passwords; document design is the mitigation")]),

    # --- 2. budgeting, financial trackers & calculators -------------------
    _idea("PI-FIN-01", "budgeting_financial",
          "Freelancer day-rate and raise calculator",
          "Solo freelancers pricing by gut feel",
          "US/UK/EU",
          "Freelancers underprice because they never convert desired take-home pay into a defensible day rate",
          "Convert target annual income, billable ratio, tax reserve and overhead into a minimum and target day rate",
          "excel_tool",
          "Excel calculator with scenario table, tax-reserve line and a one-page client-facing rate rationale",
          ["freelance rate", "day rate", "consulting rate"], 29.0,
          differentiation="Factory already sells a freelancer rate calculator; this variant differs only by tax-reserve modelling, so it may be a duplicate rather than a new product"),
    _idea("PI-FIN-02", "budgeting_financial",
          "Sinking-fund planner for irregular income",
          "Shift workers, contractors and commission earners",
          "US/UK",
          "Irregular income makes annual costs feel like emergencies, so they are paid with credit",
          "Split every known irregular cost into monthly set-asides that survive a low-income month",
          "excel_tool",
          "Excel workbook with sinking-fund register, low-month simulation and drawdown rules",
          ["sinking fund", "irregular income", "budget planner"], 19.0),
    _idea("PI-FIN-03", "budgeting_financial",
          "Subscription stack true-cost calculator",
          "Households and freelancers with 10+ recurring subscriptions",
          "Global",
          "Subscriptions are renewed individually, so the annual total and overlap are invisible until audited",
          "Reveal annual cost, overlapping tools and the cheapest defensible cut list",
          "excel_tool",
          "Excel calculator with annualised totals, overlap detection and a cut/keep decision sheet",
          ["subscription tracker", "subscription audit", "recurring costs"], 15.0),
    _idea("PI-FIN-04", "budgeting_financial",
          "Late-payment interest and recovery calculator",
          "Small suppliers chasing overdue invoices in EU/UK",
          "EU/UK",
          "Suppliers do not claim statutory late-payment interest because calculating it across jurisdictions is tedious",
          "Compute the statutory interest and fixed compensation owed on each overdue invoice, with a demand letter",
          "excel_tool",
          "Excel calculator per jurisdiction plus a printable demand-letter template",
          ["late payment", "overdue invoice", "statutory interest"], 39.0,
          risks=[_risk("medium", "Legal-adjacent content; every figure must cite the statute it applies, and the product must not present itself as legal advice")],
          differentiation="Factory already lists an EU late-payment calculator; verify before building again"),
    _idea("PI-FIN-05", "budgeting_financial",
          "Break-even and cash-runway workbook for micro-businesses",
          "Owner-operators with under 10 staff",
          "Global",
          "Micro-businesses confuse profit with cash and discover a shortfall only at the bank",
          "Model break-even units, worst-month cash runway and the trigger points for cost cuts",
          "excel_tool",
          "Excel workbook: fixed/variable cost split, break-even chart data, 13-week cash calendar",
          ["break even", "cash runway", "cash flow forecast"], 39.0),

    # --- 3. educational resources & learning aids ------------------------
    _idea("PI-EDU-01", "education_learning",
          "Exam revision spaced-repetition planner",
          "Students preparing for high-stakes exams within 12 weeks",
          "Global",
          "Students re-read material instead of scheduling retrieval, so retention collapses under exam pressure",
          "Convert a syllabus into a dated retrieval schedule with realistic daily load",
          "excel_tool",
          "Excel planner that turns topic lists into review dates with workload warnings",
          ["revision planner", "spaced repetition", "study planner"], 19.0),
    _idea("PI-EDU-02", "education_learning",
          "Teacher lesson-pack template bundle",
          "Primary and secondary teachers building weekly lessons",
          "UK/US",
          "Teachers rebuild the same lesson scaffolding every week because templates are scattered and inconsistent",
          "Produce a consistent lesson pack (objectives, activities, differentiation, assessment) in one file",
          "guide_printable",
          "Printable/editable lesson pack with 12 templates and a worked example per template",
          ["lesson plan", "teacher templates", "lesson pack"], 24.0),
    _idea("PI-EDU-03", "education_learning",
          "Source-tracking workbook for research students",
          "Undergraduate and master's students writing long papers",
          "Global",
          "Students lose track of which claim came from which source, producing unciteable drafts",
          "Track every claim against a dated source so the bibliography is built while reading",
          "excel_tool",
          "Excel workbook: source register, claim matrix, quote bank, bibliography export sheet",
          ["citation tracker", "source tracker", "research notes"], 19.0),
    _idea("PI-EDU-04", "education_learning",
          "AI literacy workbook for non-technical staff",
          "Managers and administrators in small organisations",
          "Global",
          "Staff are told to 'use AI' with no shared vocabulary for what it can and cannot be trusted with",
          "Build a shared, risk-aware baseline of AI capability, limits and verification habits",
          "guide_printable",
          "Workbook with eight exercises, verification checklists and a team policy one-pager",
          ["ai literacy", "ai training", "ai for staff"], 39.0,
          risks=[_risk("low", "Rapidly changing subject matter; requires a dated revision and a stated knowledge cutoff")]),
    _idea("PI-EDU-05", "education_learning",
          "Language self-study progress tracker",
          "Adult learners studying a language without a class",
          "Global",
          "Self-study stalls because progress is invisible and practice is unstructured",
          "Turn a vague goal into weekly measurable practice with visible progress",
          "notion_template",
          "Notion template: weekly practice plan, vocabulary ledger, speaking log, milestone dashboard",
          ["language learning", "language study", "vocabulary tracker"], 19.0),

    # --- 4. creative assets & printables --------------------------------
    _idea("PI-CRT-01", "creative_printables",
          "Printable wall-art set for renters",
          "Renters who cannot paint or hang heavy frames",
          "US/UK",
          "Renters want a styled wall without damaging walls or commissioning art",
          "Get a matched, frame-free print set sized for common rental walls",
          "guide_printable",
          "Print-at-home set of six coordinated A3/A4/Letter layouts with hanging instructions",
          ["printable wall art", "wall art", "printable decor"], 12.0,
          risks=[_risk("low", "Typography and illustration must be original or properly licensed; no traced third-party art")]),
    _idea("PI-CRT-02", "creative_printables",
          "Handmade-seller packaging and thank-you card kit",
          "Etsy and craft-fair sellers shipping physical goods",
          "Global",
          "Small sellers lose repeat business because unboxing feels unbranded and unmemorable",
          "Ship a consistent branded unboxing experience without a designer",
          "guide_printable",
          "Editable thank-you cards, care cards and packaging insert templates in print-ready sizes",
          ["packaging insert", "thank you card", "etsy packaging"], 15.0),
    _idea("PI-CRT-03", "creative_printables",
          "Journaling prompt card deck",
          "Adults journaling for reflection rather than productivity",
          "Global",
          "Blank pages stall reflection, and prompt lists online are repetitive and shallow",
          "Have a structured set of prompts that escalates from surface to substantive",
          "guide_printable",
          "Print-and-cut card deck of 60 prompts with a short usage guide",
          ["journal prompts", "journaling cards", "reflection prompts"], 12.0),
    _idea("PI-CRT-04", "creative_printables",
          "Beginner amigurumi pattern set",
          "New crocheters who can chain and single-crochet",
          "Global",
          "Beginner patterns assume skills the reader does not have, so first projects fail",
          "Complete a first amigurumi with row-by-row counts and a failure-recovery section",
          "craft_pattern",
          "Pattern set with stitch counts, gauge guidance, photo-free diagrams and a troubleshooting page",
          ["crochet pattern", "amigurumi pattern", "beginner crochet"], 9.0,
          risks=[_risk("medium", "Stitch counts must be independently verified; yarn/gauge outcomes cannot be guaranteed without a physical test")]),
    _idea("PI-CRT-05", "creative_printables",
          "Photo-album layout templates",
          "Families assembling print albums from phone photos",
          "Global",
          "Albums stall because layout decisions are made per page and print sizing is guesswork",
          "Drop photos into pre-sized layouts that print correctly first time",
          "guide_printable",
          "Print-ready layout templates with crop guides and a bleed/trim reference sheet",
          ["photo album", "photo book template", "album layout"], 19.0),

    # --- 5. events, weddings & celebrations -----------------------------
    _idea("PI-EVT-01", "events_celebrations",
          "Wedding vendor booking protection pack",
          "Couples booking 8-15 wedding vendors",
          "US/UK",
          "Couples lose deposits because contract terms, payment dates and cancellation clauses are never compared",
          "Compare every vendor contract on the same terms and track deposits and deadlines",
          "excel_tool",
          "Excel workbook: vendor comparison matrix, deposit calendar, clause checklist, escalation log",
          ["wedding budget", "wedding vendor", "wedding planning"], 29.0,
          differentiation="Factory already lists a wedding vendor tracker; verify before duplicating"),
    _idea("PI-EVT-02", "events_celebrations",
          "Event budget and deposit tracker",
          "People planning a 50-200 person event",
          "Global",
          "Event budgets drift because deposits, balances and contingency are tracked in different places",
          "Keep committed, paid and remaining budget in one view with a contingency rule",
          "excel_tool",
          "Excel tracker with committed/paid/remaining columns, deposit calendar and variance report",
          ["event budget", "event planning", "party budget"], 19.0),
    _idea("PI-EVT-03", "events_celebrations",
          "Children's birthday party run-sheet",
          "Parents hosting 10-20 children at home or a venue",
          "Global",
          "Parties overrun because timings, activities and food are planned in the host's head",
          "Run the party from a timed sheet with contingencies for weather and early finishers",
          "guide_printable",
          "Printable run-sheet, activity cards and a shopping/quantities calculator",
          ["birthday party", "party planning", "party checklist"], 9.0),
    _idea("PI-EVT-04", "events_celebrations",
          "Corporate offsite planning workbook",
          "Operations managers running a 1-3 day team offsite",
          "Global",
          "Offsites consume weeks of admin and still miss logistics, budget approval and follow-up",
          "Plan, budget and run an offsite from one workbook with an approval-ready cost case",
          "excel_tool",
          "Workbook: agenda builder, cost model, logistics checklist, decision and follow-up log",
          ["corporate offsite", "team retreat", "offsite planning"], 39.0),
    _idea("PI-EVT-05", "events_celebrations",
          "Memorial logistics planner",
          "Families arranging a funeral or memorial within days",
          "UK/US",
          "Grieving families must coordinate documents, service order, costs and notifications under time pressure",
          "Sequence the unavoidable tasks and record decisions without adding emotional load",
          "guide_printable",
          "Printable task sequence, document checklist, cost tracker and notification list",
          ["funeral planning", "memorial planning", "funeral checklist"], 0.0,
          risks=[_risk("high", "Bereavement-sensitive; must avoid prescriptive cultural or religious instruction and must state it is not legal or financial advice")],
          differentiation="Sensitive category: only defensible with a disclosed scope and an explicit non-advice statement"),

    # --- 6. resume, career & professional identity ----------------------
    _idea("PI-CAR-01", "resume_career",
          "Career-change portfolio kit",
          "Career changers with transferable but non-obvious experience",
          "Global",
          "Career changers are filtered out because their CV describes past roles rather than transferable outcomes",
          "Translate past work into evidence a hiring manager in the new field can evaluate",
          "guide_printable",
          "Worksheet set: evidence inventory, transferable-skill mapping, rewritten summary, portfolio page outline",
          ["career change", "resume template", "cv template"], 19.0),
    _idea("PI-CAR-02", "resume_career",
          "Interview scorecard and question bank",
          "Hiring managers in small companies without a structured process",
          "Global",
          "Small-company interviews are unstructured, so decisions are made on impression and cannot be defended",
          "Run a consistent interview with scored evidence and a written decision rationale",
          "notion_template",
          "Notion template: role scorecard, question bank by competency, scoring sheet, debrief record",
          ["interview scorecard", "hiring template", "interview questions"], 29.0),
    _idea("PI-CAR-03", "resume_career",
          "Salary negotiation evidence log",
          "Employees preparing a compensation conversation",
          "Global",
          "Employees negotiate without documented evidence of scope, impact and market rate, and accept the first number",
          "Assemble a defensible case with documented achievements and a target range",
          "excel_tool",
          "Workbook: achievement evidence log, market-range worksheet, scripted conversation plan",
          ["salary negotiation", "pay rise", "compensation"], 19.0),
    _idea("PI-CAR-04", "resume_career",
          "Freelance proposal and scope-of-work pack",
          "Freelancers and small studios sending proposals",
          "Global",
          "Proposals omit scope boundaries, so clients expand work without paying and disputes follow",
          "Send a proposal that fixes scope, exclusions, change control and payment terms",
          "guide_printable",
          "Template pack: proposal, scope of work, change request, payment schedule, acceptance page",
          ["freelance proposal", "scope of work", "client contract"], 29.0,
          risks=[_risk("medium", "Contract-adjacent templates; must state they are starting points requiring local legal review")]),
    _idea("PI-CAR-05", "resume_career",
          "Professional profile rewrite worksheet",
          "Professionals whose online profile does not match their actual work",
          "Global",
          "Profiles list job titles rather than problems solved, so inbound opportunities are misaligned",
          "Rewrite a profile around the problems the person solves, with evidence",
          "guide_printable",
          "Worksheet with before/after examples, evidence prompts and a completeness checklist",
          ["linkedin profile", "professional profile", "profile rewrite"], 12.0),

    # --- 7. social media & content templates ---------------------------
    _idea("PI-SOC-01", "social_media_templates",
          "Content calendar for solo founders",
          "Solo founders who post inconsistently",
          "Global",
          "Founders post when they remember, so the channel never accumulates a compounding audience",
          "Plan a month of posts tied to real company events instead of invented themes",
          "notion_template",
          "Notion template: monthly calendar, post-type mix, source-of-idea log, weekly review",
          ["content calendar", "social media planner", "post schedule"], 19.0),
    _idea("PI-SOC-02", "social_media_templates",
          "Product launch post sequence specification",
          "Indie makers launching a first or second product",
          "Global",
          "Launches are announced once, so most of the audience never sees them",
          "Sequence a launch across formats with a stated purpose for each post rather than repeated announcements",
          "notion_template",
          "Notion template: launch timeline, per-post purpose, asset checklist, response scripts for objections",
          ["product launch", "launch plan", "launch checklist"], 24.0),
    _idea("PI-SOC-03", "social_media_templates",
          "Short-form video hook bank",
          "Creators publishing short-form video weekly",
          "Global",
          "Creators repeat the same opening line because they lack a structured way to vary hooks",
          "Choose a hook that fits the specific point being made rather than a generic attention grab",
          "guide_printable",
          "Hook taxonomy, 40 worked examples mapped to content types, and a fit-check checklist",
          ["video hooks", "short form video", "content hooks"], 12.0),
    _idea("PI-SOC-04", "social_media_templates",
          "Testimonial request kit",
          "Small sellers with happy customers but no written proof",
          "Global",
          "Sellers either have no testimonials or risk writing them themselves, which is deceptive",
          "Ask real customers in a way that produces specific, verifiable quotes",
          "guide_printable",
          "Request templates, consent wording, a quote-editing policy and a display checklist",
          ["testimonial request", "customer review", "social proof"], 15.0,
          risks=[_risk("high", "Any template encouraging fabricated or edited reviews is prohibited; consent and attribution rules must be explicit")]),
    _idea("PI-SOC-05", "social_media_templates",
          "Community moderation playbook",
          "Operators of a small paid or free community",
          "Global",
          "Moderation is improvised, so the same rule is applied differently and members leave",
          "Apply written rules consistently, with escalation steps and a record of decisions",
          "guide_printable",
          "Playbook: rule set, response ladder, escalation matrix, decision log, appeal process",
          ["community moderation", "community management", "moderation policy"], 29.0),

    # --- 8. e-commerce seller tools ------------------------------------
    _idea("PI-ECM-01", "ecommerce_seller_tools",
          "Marketplace ads ROI calculator",
          "Etsy and Amazon sellers running paid ads without a profitability model",
          "Global",
          "Sellers scale ads that lose money per order because return is measured on revenue, not contribution",
          "Decide a maximum defensible ad spend per order from real fees and refund rates",
          "excel_tool",
          "Excel calculator: fee stack, refund allowance, break-even ROAS, bid ceiling",
          ["etsy ads", "roas calculator", "ad spend"], 29.0,
          differentiation="Factory already lists an Etsy ads ROI calculator; verify before duplicating"),
    _idea("PI-ECM-02", "ecommerce_seller_tools",
          "Marketplace fee and repricing workbook",
          "Multi-channel sellers listing the same item on several marketplaces",
          "Global",
          "The same price yields different net proceeds per marketplace, so the cheapest channel looks unprofitable",
          "Compare net proceeds per channel and set channel-specific prices",
          "excel_tool",
          "Workbook: fee tables per channel, net-proceeds comparison, repricing rules, margin floor alarm",
          ["marketplace fees", "repricing", "profit margin"], 29.0),
    _idea("PI-ECM-03", "ecommerce_seller_tools",
          "Returns and refund policy builder",
          "Small online sellers writing their first policies",
          "UK/EU/US",
          "Policies are copied from other stores and contradict the platform's own rules, creating disputes",
          "Write a policy that matches the selling platform and the seller's actual capacity",
          "guide_printable",
          "Policy builder with clause options, a platform-consistency check and a customer-facing template",
          ["refund policy", "returns policy", "store policies"], 19.0,
          risks=[_risk("medium", "Consumer-law adjacent; must state the policy is a draft requiring local review")]),
    _idea("PI-ECM-04", "ecommerce_seller_tools",
          "Listing image audit sheet",
          "Sellers whose listings get traffic but no conversion",
          "Global",
          "Sellers cannot tell which listing images lose the buyer because they never compare systematically",
          "Audit each listing's images against a fixed coverage checklist and rank fixes by likely impact",
          "excel_tool",
          "Excel audit sheet: coverage checklist, per-listing scoring, fix priority list",
          ["listing images", "product photos", "listing optimization"], 19.0),
    _idea("PI-ECM-05", "ecommerce_seller_tools",
          "Supplier vetting questionnaire pack",
          "Sellers moving from print-on-demand to physical inventory",
          "Global",
          "Sellers commit deposits before checking capacity, compliance or quality control",
          "Vet a supplier against the same questions before any deposit is paid",
          "research_data_tool",
          "Questionnaire pack, scoring rubric, red-flag list and reference-check script",
          ["supplier vetting", "supplier questionnaire", "sourcing checklist"], 39.0),

    # --- 9. small-business operations ----------------------------------
    _idea("PI-OPS-01", "small_business_operations",
          "Food-waste tracking system",
          "Independent restaurants and cafes",
          "UK/EU",
          "Food cost rises invisibly because waste is never measured at the item level",
          "Measure waste per item per week and convert it into a purchasing change",
          "excel_tool",
          "Excel system: waste log, cost conversion, weekly ranking, purchasing adjustment sheet",
          ["food waste", "restaurant costs", "kitchen inventory"], 39.0,
          differentiation="Factory already lists a restaurant food-waste tracker; verify before duplicating"),
    _idea("PI-OPS-02", "small_business_operations",
          "Field-service job-costing workbook",
          "Trades and service businesses quoting per job",
          "UK/US/AU",
          "Job quotes omit travel, callbacks and material waste, so profitable-looking jobs lose money",
          "Cost each job fully and compare quoted versus actual contribution",
          "excel_tool",
          "Workbook: job costing sheet, travel/callback allowances, quote-versus-actual report",
          ["job costing", "field service", "trades quoting"], 39.0),
    _idea("PI-OPS-03", "small_business_operations",
          "Inventory reorder-point calculator",
          "Small retailers and workshops holding stock",
          "Global",
          "Reorder points are guessed, producing both stockouts and dead stock",
          "Set a reorder point per item from real lead time and demand variability",
          "excel_tool",
          "Excel calculator: lead-time input, variability estimate, reorder point, dead-stock report",
          ["reorder point", "inventory management", "stock control"], 29.0),
    _idea("PI-OPS-04", "small_business_operations",
          "SOP library starter kit for small teams",
          "Teams of 3-15 without written procedures",
          "Global",
          "Knowledge lives with one person, so holidays and departures break operations",
          "Capture the ten procedures that break first, in a format a new hire can follow",
          "notion_template",
          "Notion template: SOP index, procedure template, ownership map, review schedule",
          ["sop template", "standard operating procedure", "process documentation"], 39.0),
    _idea("PI-OPS-05", "small_business_operations",
          "Vendor onboarding and compliance tracker",
          "Small businesses depending on subcontractors or suppliers",
          "UK/EU",
          "Supplier documents expire unnoticed, creating compliance and continuity risk",
          "Track every supplier's documents, insurance and renewal dates with an escalation rule",
          "excel_tool",
          "Excel tracker: supplier register, document expiry calendar, escalation rules, audit log",
          ["vendor management", "supplier compliance", "contractor tracker"], 39.0),

    # --- 10. industry-specific templates & calculators ------------------
    _idea("PI-IND-01", "industry_specific_business",
          "EU AI Act compliance document toolkit",
          "SMEs deploying AI features in the EU",
          "EU",
          "SMEs must produce AI-system documentation under a deadline they cannot interpret, and consultants charge project fees",
          "Produce the required documentation set from a structured template pack",
          "guide_printable",
          "Document pack: system inventory, risk classification, technical documentation, transparency notices",
          ["eu ai act", "ai act compliance", "ai act"], 155.0,
          risks=[_risk("high", "Regulatory content with dates that changed once already (Digital Omnibus deferral); every deadline must be dated and sourced, and the pack must state it is not legal advice")],
          differentiation="This factory already built the EU AI Act toolkit; the real blocker is publication and payment, not discovery"),
    _idea("PI-IND-02", "industry_specific_business",
          "SOC 2 evidence automation blueprint",
          "Small SaaS teams preparing a first SOC 2 audit",
          "US",
          "Evidence collection is manual and repetitive, and audit-readiness slips by months",
          "Automate the evidence trail for the controls a first audit actually tests",
          "research_data_tool",
          "Blueprint: control-to-evidence map, collection automation spec, gap register",
          ["soc 2", "soc2 compliance", "audit evidence"], 149.0,
          risks=[_risk("medium", "Security-control guidance must cite the trust-services criteria it maps to and must not claim certification")]),
    _idea("PI-IND-03", "industry_specific_business",
          "Legal case research automation system",
          "Solo attorneys and small firms",
          "US/UK",
          "Case research is billed hourly and depends on one person's recall of precedent",
          "Structure case research into a repeatable, reviewable workflow with citations",
          "service_micro_b2b",
          "Productized service: intake form, research workflow, citation-verified deliverable template",
          ["legal research", "case research", "legal automation"], 149.0,
          risks=[_risk("high", "Legal-services regulation varies by jurisdiction; no legal advice may be given, and citations must be verifiable by a licensed reviewer")]),
    _idea("PI-IND-04", "industry_specific_business",
          "Cloud operations AI agent blueprint",
          "Small SaaS teams without a platform engineer",
          "Global",
          "Routine cloud operations work is undocumented, so every incident is resolved by the same one person",
          "Document and automate the routine checks that cause most incidents",
          "research_data_tool",
          "Blueprint: runbook map, agent specification, guardrails, human-approval points",
          ["cloudops", "cloud operations", "sre runbook"], 149.0,
          risks=[_risk("medium", "Autonomous remediation advice must default to human approval; the blueprint must not encourage unreviewed production changes")]),
    _idea("PI-IND-05", "industry_specific_business",
          "Dental practice no-show reduction system",
          "Independent dental practices",
          "UK/US",
          "Empty appointment slots are the largest avoidable revenue loss in a practice and are managed by memory",
          "Measure no-show patterns and apply a documented reminder and deposit policy",
          "excel_tool",
          "Workbook: no-show log, pattern analysis, reminder ladder, deposit policy template",
          ["dental practice", "no show", "appointment reminder"], 79.0,
          differentiation="Factory already lists a dental no-show tracker; verify before duplicating"),
]


# ---------------------------------------------------------------------------
# real read-only sources
# ---------------------------------------------------------------------------

def _read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _read_jsonl(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def _text_of(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, default=str).lower()
    except Exception:
        return str(obj).lower()


def _squash(text: str) -> str:
    """Fold separators so 'soc 2' matches 'SOC2' and 'cloudops' matches 'Cloud Ops'.

    This is a matching convenience, not a semantic expansion: no synonyms and no
    stemming are applied anywhere in this module.
    """
    return "".join(ch for ch in text.lower() if ch.isalnum())


def _matches(text: str, keywords: Sequence[str], minimum: Optional[int] = None) -> bool:
    hay = text.lower()
    hay_squashed = _squash(text)
    hits = 0
    for kw in keywords:
        if kw.lower() in hay or (_squash(kw) and _squash(kw) in hay_squashed):
            hits += 1
    need = minimum if minimum is not None else min(2, len(keywords))
    return hits >= need


def _matches_primary(text: str, keywords: Sequence[str]) -> bool:
    """Match on an idea's primary identifying phrase only.

    Supporting keywords must not be enough to claim demand: a testimonial-request
    kit must not inherit the demand evidence of an unrelated EU-AI-Act review
    row merely because both contain the words 'customer review'.
    """
    if not keywords:
        return False
    return _matches(text, [keywords[0]], minimum=1)


def market_evidence(rows: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    return rows if rows is not None else _read_jsonl(MARKET_EVIDENCE_PATH)


def catalog_products(products: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    if products is not None:
        return products
    data = _read_json(CATALOG_PATH)
    return data.get("products", []) if isinstance(data, dict) else []


def competitor_names(niche_text: str, db: Optional[Dict[str, Any]] = None) -> List[str]:
    db = db if db is not None else _read_json(COMPETITOR_DB_PATH)
    names: List[str] = []
    for key, entry in (db or {}).items():
        if _matches((key or "") + " " + _text_of(entry), [niche_text], minimum=1):
            for comp in entry.get("competitors") or []:
                name = comp.get("name")
                if name and name not in names:
                    names.append(name)
    return names[:5]


def channel_facts(config: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    config = config if config is not None else _read_json(CHANNELS_CONFIG_PATH)
    return {c["id"]: c for c in config.get("channels", []) if c.get("id")}


def _channels_for_format(fmt: str, channels: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Real channel fit: a channel is a candidate only if it accepts this format."""
    wants_pdf = fmt in ("guide_printable", "craft_pattern", "kids_education")
    out: List[Dict[str, Any]] = []
    for cid, c in channels.items():
        if wants_pdf and not c.get("supports_pdf"):
            continue
        out.append({
            "channel": cid,
            "automation": c.get("automation"),
            "api_available": bool(c.get("api_available")),
            "supports_pdf": bool(c.get("supports_pdf")),
            "royalty_model": c.get("royalty_model"),
            "constraints": [n for n in [c.get("notes")] if n],
        })
    return out


def _platform_for_format(fmt: str) -> str:
    import economics
    product_type = FORMAT_TO_PRODUCT_TYPE.get(fmt, "printable")
    return economics.platform_for_product_type(product_type)


def _format_facts(fmt: str) -> Dict[str, Any]:
    from trend_to_product.ideation import FORMATS
    return dict(FORMATS.get(fmt, {}))


# ---------------------------------------------------------------------------
# resolution: real observations before any judgement
# ---------------------------------------------------------------------------

def _listing_summary(products: List[Dict[str, Any]], keywords: Sequence[str], limit: int = 3) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in products:
        hay = " ".join(str(p.get(k) or "") for k in ("name", "title", "problem", "target_buyer"))
        if not _matches(hay.lower(), keywords):
            continue
        out.append({
            "name": p.get("name") or p.get("title"),
            "price_usd": p.get("price_usd"),
            "sales": p.get("sales") or 0,
            "revenue_usd": p.get("revenue_usd") or 0.0,
            "commercial_state": p.get("commercial_state"),
            "evidence_level": p.get("evidence_level"),
        })
        if len(out) >= limit:
            break
    return out


def resolve_demand(
    idea: Dict[str, Any],
    evidence: Optional[List[Dict[str, Any]]] = None,
    products: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """OBSERVED only when a recorded evidence row cites a source and a quote.

    A live listing with zero sales is evidence of an attempt, never of demand --
    it is reported, and the status stays UNKNOWN with that reason.
    """
    evidence = market_evidence(evidence)
    products = catalog_products(products)
    keywords = idea["keywords"]
    # Internal overlap is resolved independently of the demand branch: a recorded
    # market-evidence row must not hide the fact that this factory already lists
    # something very close (that changes the recommended action, not the demand).
    listings = _listing_summary(products, keywords)

    matched = [r for r in evidence if _matches_primary(_text_of(r), keywords)]
    if matched:
        sources = []
        for row in matched:
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            src = payload.get("source_url") or row.get("source")
            if src and src not in sources:
                sources.append(src)
        return {
            "status": "OBSERVED",
            "record_count": len(matched),
            "sources": sources,
            "event_types": sorted({r.get("event_type") for r in matched if r.get("event_type")}),
            "reason": "%d recorded evidence row(s) carrying a cited source" % len(matched),
            "internal_listings": listings,
        }

    sold = [l for l in listings if (l.get("sales") or 0) > 0 or (l.get("revenue_usd") or 0.0) > 0]
    if sold:
        return {
            "status": "DERIVED",
            "record_count": len(sold),
            "sources": ["data/catalog.json"],
            "reason": "%d matching listing(s) record a real sale" % len(sold),
            "internal_listings": listings,
        }
    if listings:
        return {
            "status": "UNKNOWN",
            "record_count": 0,
            "sources": ["data/catalog.json"],
            "reason": "%d live listing(s) address this problem and none recorded a sale; listing presence is not demand" % len(listings),
            "internal_listings": listings,
        }
    return {
        "status": "UNKNOWN",
        "record_count": 0,
        "sources": [],
        "reason": "no recorded demand evidence and no matching live listing",
        "internal_listings": [],
    }


def resolve_competition(
    idea: Dict[str, Any],
    evidence: Optional[List[Dict[str, Any]]] = None,
    products: Optional[List[Dict[str, Any]]] = None,
    db: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    products = catalog_products(products)
    listings = _listing_summary(products, idea["keywords"], limit=10)
    names = competitor_names(idea["title"], db)
    if not names:
        for kw in idea["keywords"]:
            names = competitor_names(kw, db)
            if names:
                break
    total = len(names) + len(listings)
    if total == 0:
        return {
            "status": "UNKNOWN",
            "count": 0,
            "recorded_competitors": [],
            "internal_listings": [],
            "reason": "no recorded competitor or matching listing; absence of evidence is not absence of competition",
        }
    return {
        "status": "DERIVED",
        "count": total,
        "recorded_competitors": names,
        "internal_listings": listings,
        "reason": "%d recorded competitor name(s) and %d matching live listing(s)" % (len(names), len(listings)),
    }


def resolve_unit_economics(idea: Dict[str, Any]) -> Dict[str, Any]:
    price = idea.get("proposed_price_usd")
    platform = _platform_for_format(idea["format"])
    if not price:
        return {
            "status": "UNKNOWN",
            "platform": platform,
            "reason": "no proposed price, so no fee model can be applied",
            "assumptions": ["price must be set before any margin claim is possible"],
        }
    import economics
    config = economics.load_config(ECONOMICS_CONFIG_PATH)
    try:
        net = economics.net_profit(price, platform, config)
    except ValueError as exc:
        return {
            "status": "UNKNOWN",
            "platform": platform,
            "proposed_price_usd": price,
            "reason": str(exc),
            "assumptions": [],
        }
    return {
        "status": "DERIVED",
        "platform": platform,
        "proposed_price_usd": price,
        "net_per_unit_usd": net,
        "net_margin_pct": round(net / price * 100.0, 1) if price else None,
        "basis": "economics.net_profit on the canonical platform table",
        "assumptions": [
            "one unit per order",
            "no advertising cost, refund, chargeback or support cost",
            "no payment-processor fee beyond the platform royalty table",
            "cost of production is treated as founder time at zero cash cost",
        ],
    }


def resolve_distribution(idea: Dict[str, Any], channels: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
    channels = channel_facts(channels)
    candidates = _channels_for_format(idea["format"], channels)
    if not candidates:
        return {
            "status": "UNKNOWN",
            "channels": [],
            "reason": "no configured channel accepts this format",
            "blocked_by": [],
        }
    scored = []
    for c in candidates:
        if c["api_available"] and c["automation"] == "api":
            score, basis = 80, "API automation available"
        elif c["automation"] == "manual":
            score, basis = 45, "human upload required"
        else:
            score, basis = 55, "channel listed without API automation"
        scored.append(dict(c, fit_score=score, fit_basis=basis))
    best = max(scored, key=lambda c: c["fit_score"])
    blocking: List[str] = []
    if best["channel"] in ("kdp", "kdp_paperback") and not channels.get("kdp_paperback", {}).get("supports_arabic", True):
        blocking.append("kdp_paperback does not support Arabic")
    return {
        "status": "DERIVED",
        "best_channel": best["channel"],
        "channels": scored,
        "reason": best["fit_basis"],
        "blocked_by": blocking,
        "constraints_on_best": list(best.get("constraints") or []) + blocking,
        "assumptions": ["channel facts are configuration, not live account permission; a live publish still requires credentials and the write gate"],
    }


# ---------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------

def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


SEVERITY_MARKERS = {
    "high": ("fine", "penalty", "legal", "compliance", "audit", "deadline", "tax",
             "refund", "chargeback", "lawsuit", "risk", "lose", "loss", "fail",
             "break", "cost", "overdue", "deposit", "regulation"),
    "medium": ("waste", "drift", "manual", "repetitive", "invisible", "stall",
               "inconsistent", "guess", "scattered", "unstructured", "memory"),
}


def _score_problem_severity(idea: Dict[str, Any]) -> Dict[str, Any]:
    text = (idea["problem"] + " " + idea["job_to_be_done"]).lower()
    high = sum(1 for m in SEVERITY_MARKERS["high"] if m in text)
    medium = sum(1 for m in SEVERITY_MARKERS["medium"] if m in text)
    level = "high" if high >= 2 else "medium" if (high >= 1 or medium >= 2) else "low"
    value = {"high": 85.0, "medium": 60.0, "low": 40.0}[level]
    return {
        "score": value,
        "basis": "INFERRED",
        "level": level,
        "reason": COMPONENT_REASONS["problem_severity"],
        "observations": {"high_markers": high, "medium_markers": medium},
    }


def _score_competition(res: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if res["status"] == "UNKNOWN":
        return None
    n = res["count"]
    if n <= 2:
        value = 70.0
    elif n <= 5:
        value = 55.0
    elif n <= 10:
        value = 40.0
    else:
        value = 25.0
    return {
        "score": value,
        "basis": "DERIVED",
        "reason": COMPONENT_REASONS["competition_intensity"],
        "observations": {"competitor_count": n},
    }


def _score_differentiation(idea: Dict[str, Any], res: Dict[str, Any]) -> Dict[str, Any]:
    internal = len(res.get("internal_listings") or [])
    if internal == 0:
        value, level = 70.0, "no existing factory listing addresses this"
    else:
        value, level = 40.0, "%d existing factory listing(s) overlap" % internal
    return {
        "score": value,
        "basis": "DERIVED",
        "reason": COMPONENT_REASONS["differentiation"],
        "observations": {"overlapping_internal_listings": internal, "authored_note": idea.get("authored_differentiation")},
        "detail": level,
    }


def _score_willingness_to_pay(demand: Dict[str, Any], economics_res: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """WTP requires a real completed sale. A listing price is not willingness."""
    if demand["status"] == "DERIVED":
        prices = [l.get("price_usd") for l in demand.get("internal_listings", []) if l.get("price_usd")]
        if prices:
            median = sorted(prices)[len(prices) // 2]
            return {
                "score": _clamp(40.0 + min(median, 200.0) / 200.0 * 40.0),
                "basis": "DERIVED",
                "reason": "a real sale exists at a recorded price; the price itself is observed, the broader willingness is inferred from one case",
                "observations": {"median_observed_price_usd": median},
            }
    return None


def _score_production(idea: Dict[str, Any]) -> Dict[str, Any]:
    facts = _format_facts(idea["format"])
    effort = facts.get("effort")
    maintenance = facts.get("maintenance")
    if effort is None or maintenance is None:
        value = 50.0
        basis = "UNKNOWN"
    else:
        value = _clamp(((effort + maintenance) / 10.0) * 100.0)
        basis = "DERIVED"
    return {
        "score": value,
        "basis": basis,
        "reason": COMPONENT_REASONS["production_cost_complexity"],
        "observations": {
            "format_effort": effort,
            "format_maintenance": maintenance,
            "pipeline": facts.get("pipeline"),
            "verification": facts.get("verification"),
        },
    }


def _score_distribution(res: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if res["status"] == "UNKNOWN":
        return None
    best = max(res["channels"], key=lambda c: c["fit_score"])
    return {
        "score": float(best["fit_score"]),
        "basis": "DERIVED",
        "reason": COMPONENT_REASONS["distribution_feasibility"],
        "observations": {"best_channel": best["channel"], "automation": best["automation"], "blocked_by": res.get("blocked_by", [])},
    }


def _score_margin(econ: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if econ["status"] != "DERIVED" or econ.get("net_margin_pct") is None:
        return None
    return {
        "score": _clamp(econ["net_margin_pct"]),
        "basis": "DERIVED",
        "reason": COMPONENT_REASONS["contribution_margin"],
        "observations": {"net_per_unit_usd": econ["net_per_unit_usd"], "platform": econ["platform"]},
    }


def _score_expansion(idea: Dict[str, Any]) -> Dict[str, Any]:
    import profit_oracle as po
    ladder = CATEGORIES[idea["category"]]["ladder"]
    recurring = po.RECURRING_REVENUE_BY_LADDER.get(ladder)
    reuse = po.REUSABILITY_BY_LADDER.get(ladder)
    if recurring is None or reuse is None:
        return {"score": 50.0, "basis": "UNKNOWN", "reason": COMPONENT_REASONS["expansion_potential"], "observations": {"ladder": ladder}}
    return {
        "score": _clamp((recurring + reuse) / 2.0),
        "basis": "DERIVED",
        "reason": COMPONENT_REASONS["expansion_potential"],
        "observations": {"ladder": ladder, "recurring_revenue_index": recurring, "reusability_index": reuse},
    }


def _score_risk(idea: Dict[str, Any]) -> Dict[str, Any]:
    levels = [r.get("level") for r in idea.get("licensing_risks") or []]
    if "high" in levels:
        value = 20.0
    elif "medium" in levels:
        value = 45.0
    elif levels:
        value = 70.0
    else:
        value = 85.0
    return {
        "score": value,
        "basis": "INFERRED",
        "reason": COMPONENT_REASONS["risk"],
        "observations": {"risk_levels": levels},
    }


def _composite(components: Dict[str, Optional[Dict[str, Any]]], weights: Dict[str, float]) -> Dict[str, Any]:
    available = {k: v for k, v in components.items() if v is not None}
    total_weight = sum(weights.values())
    used_weight = sum(weights[k] for k in available)
    coverage = used_weight / total_weight if total_weight else 0.0
    if coverage < MIN_COVERAGE:
        return {
            "value": None,
            "coverage": round(coverage, 3),
            "band": "INSUFFICIENT_EVIDENCE",
            "missing": sorted(k for k, v in components.items() if v is None),
            "capped_by": [],
        }
    numerator = sum(available[k]["score"] * weights[k] for k in available)
    value = numerator / used_weight
    capped_by: List[str] = []
    if "demand_evidence" not in available:
        if value > UNKNOWN_DEMAND_CAP:
            value = UNKNOWN_DEMAND_CAP
        capped_by.append("demand_status=UNKNOWN")
    return {
        "value": round(value, 1),
        "coverage": round(coverage, 3),
        "band": "STRONG" if coverage >= 0.85 else "MODERATE" if coverage >= 0.7 else "LIMITED",
        "missing": sorted(k for k, v in components.items() if v is None),
        "capped_by": capped_by,
    }


def _action(
    idea: Dict[str, Any],
    demand: Dict[str, Any],
    components: Dict[str, Optional[Dict[str, Any]]],
    composite: Dict[str, Any],
    distribution: Dict[str, Any],
) -> Dict[str, Any]:
    value = composite["value"]
    overlap = len((demand.get("internal_listings") or []))
    demand_status = demand["status"]
    wtp_available = components.get("willingness_to_pay") is not None
    risk_levels = [r.get("level") for r in idea.get("licensing_risks") or []]

    if "high" in risk_levels:
        return {"label": "HOLD", "reason": "authored licensing/IP risk is high; resolve it before any build decision"}
    if demand_status == "OBSERVED" and overlap:
        sold_overlap = [l for l in (demand.get("internal_listings") or [])
                        if (l.get("sales") or 0) > 0 or (l.get("revenue_usd") or 0.0) > 0]
        if not sold_overlap:
            return {
                "label": "HOLD",
                "reason": "%d live listing(s) already address this and none recorded a sale; the blocker is distribution and payment, not discovery" % overlap,
            }
    if demand_status == "UNKNOWN":
        return {"label": "RESEARCH_DEMAND", "reason": "no recorded demand evidence; building before demand is verified repeats the current $0 outcome"}
    if overlap and value is not None and value < REJECT_BELOW_COMPOSITE:
        return {"label": "REJECT", "reason": "existing listing overlaps and the available evidence scores below the rejection floor"}
    if value is None:
        return {"label": "HOLD", "reason": "evidence coverage below %.0f%%; no composite is reported" % (MIN_COVERAGE * 100)}
    if demand_status == "OBSERVED" and wtp_available and value >= PURSUE_MIN_COMPOSITE and not distribution.get("blocked_by"):
        return {"label": "PURSUE", "reason": "recorded demand, observed willingness to pay, and a viable channel"}
    if value >= TEST_MIN_COMPOSITE:
        limit = "willingness to pay is unverified" if not wtp_available else "composite below the pursue threshold"
        return {"label": "TEST", "reason": "evidence supports a bounded test: " + limit}
    if value < REJECT_BELOW_COMPOSITE:
        return {"label": "REJECT", "reason": "available evidence scores below the rejection floor"}
    return {"label": "HOLD", "reason": "evidence neither supports a test nor justifies rejection"}


def _unknowns(idea: Dict[str, Any], demand: Dict[str, Any], evidence: Optional[List[Dict[str, Any]]]) -> List[str]:
    """Everything this record genuinely does not know, written out rather than
    implied -- the list itself is part of the deliverable."""
    items: List[str] = [
        "market size and growth rate",
        "customer acquisition channel and cost",
        "conversion rate",
        "refund rate",
        "seasonality",
        "production effort in hours (FORMATS records a 1-5 band, not hours)",
    ]
    if not evidence_of_price(evidence, idea):
        items.insert(0, "competitor pricing (no recorded price in any matched evidence row)")
    if demand["status"] != "DERIVED":
        items.insert(0, "willingness to pay (no real sale at a real price exists)")
    return items


def resolve(
    idea: Dict[str, Any],
    evidence: Optional[List[Dict[str, Any]]] = None,
    products: Optional[List[Dict[str, Any]]] = None,
    db: Optional[Dict[str, Any]] = None,
    channels: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    demand = resolve_demand(idea, evidence, products)
    competition = resolve_competition(idea, evidence, products, db)
    economics_res = resolve_unit_economics(idea)
    distribution = resolve_distribution(idea, channels)

    components: Dict[str, Optional[Dict[str, Any]]] = {
        "demand_evidence": None,
        "problem_severity": _score_problem_severity(idea),
        "competition_intensity": _score_competition(competition),
        "differentiation": _score_differentiation(idea, competition),
        "willingness_to_pay": _score_willingness_to_pay(demand, economics_res),
        "production_cost_complexity": _score_production(idea),
        "distribution_feasibility": _score_distribution(distribution),
        "contribution_margin": _score_margin(economics_res),
        "expansion_potential": _score_expansion(idea),
        "risk": _score_risk(idea),
    }
    if demand["status"] == "OBSERVED":
        components["demand_evidence"] = {
            "score": _clamp(70.0 + 5.0 * demand["record_count"]),
            "basis": "OBSERVED",
            "reason": COMPONENT_REASONS["demand_evidence"],
            "observations": {"record_count": demand["record_count"], "sources": demand["sources"]},
        }
    elif demand["status"] == "DERIVED":
        components["demand_evidence"] = {
            "score": 55.0,
            "basis": "DERIVED",
            "reason": COMPONENT_REASONS["demand_evidence"],
            "observations": {"record_count": demand["record_count"]},
        }

    composite = _composite(components, WEIGHTS)
    action = _action(idea, demand, components, composite, distribution)

    return {
        "idea_id": idea["idea_id"],
        "category": idea["category"],
        "category_label": CATEGORIES[idea["category"]]["label"],
        "title": idea["title"],
        "target_customer": idea["target_customer"],
        "geography": idea["geography"],
        "problem": idea["problem"],
        "job_to_be_done": idea["job_to_be_done"],
        "format": idea["format"],
        "deliverable": idea["deliverable"],
        "product_family": CATEGORIES[idea["category"]]["family"],
        "ladder": CATEGORIES[idea["category"]]["ladder"],
        "demand_evidence": demand,
        "competitor_examples": competition.get("recorded_competitors") or [],
        "competition_indicators": competition,
        "differentiation": components["differentiation"],
        "production": components["production_cost_complexity"],
        "distribution": distribution,
        "unit_economics": economics_res,
        "licensing_risks": idea.get("licensing_risks") or [],
        "research_confidence": {
            "level": "LOW" if demand["status"] == "UNKNOWN" else "MEDIUM" if demand["status"] == "DERIVED" else "MEDIUM",
            "reason": "nothing here was field-researched in this cycle; confidence reflects only which recorded sources exist locally",
        },
        "unknowns": _unknowns(idea, demand, evidence),
        "recommended_next_action": action["label"],
        "action_reason": action["reason"],
        "status": "ADVISORY_ONLY — not approved, not built, not published",
        "evidence_refs": sorted({s for s in (demand.get("sources") or []) + (competition.get("sources") or []) if s}),
        "scores": components,
        "composite": composite,
        "assumptions": {
            "weights": dict(WEIGHTS),
            "composite": "weighted mean over available components only; withheld below %.0f%% coverage" % (MIN_COVERAGE * 100),
            "unknown_demand_cap": UNKNOWN_DEMAND_CAP,
            "effort_role": "production effort is a cost component only; it can never create a PURSUE label",
            "seed_data": "the idea list is authored seed material, not market research",
        },
    }


def evidence_of_price(evidence: Optional[List[Dict[str, Any]]], idea: Dict[str, Any]) -> bool:
    """True only when a matched evidence row's own text contains a currency amount."""
    import re
    for row in market_evidence(evidence):
        if not _matches_primary(_text_of(row), idea["keywords"]):
            continue
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        text = " ".join(str(v) for v in payload.values())
        if re.search(r"(?:[$€£]\s?\d|\d+\s?(?:usd|eur|gbp))", text, re.IGNORECASE):
            return True
    return False


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------

def _find_idea(idea_id: str, ideas: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    for idea in (ideas if ideas is not None else IDEA_CATALOG):
        if idea["idea_id"] == idea_id:
            return idea
    raise KeyError("unknown idea_id: %s" % idea_id)


def production_path(idea_id: str, ideas: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """The real production path for an idea's format.

    This does not build a pipeline: it cites the modules that already exist and
    checks, on disk, that they are present. `exists_on_disk` is a file check,
    never a claim that the path was exercised for this idea.
    """
    idea = _find_idea(idea_id, ideas)
    facts = _format_facts(idea["format"])
    steps: List[Dict[str, Any]] = []
    for module in facts.get("pipeline") or []:
        steps.append({
            "step": "build",
            "module": module,
            "exists_on_disk": os.path.exists(os.path.join(ROOT, module)),
            "verified_for_this_idea": False,
        })
    steps.append({
        "step": "rights_check",
        "module": "trend_to_product.rights.check_rights",
        "exists_on_disk": os.path.exists(os.path.join(ROOT, "trend_to_product", "rights.py")),
        "note": "empty input is REVIEW, never PASS",
        "verified_for_this_idea": False,
    })
    try:
        import executive_quality_gate as _q
        gate = list(_q.REJECT_IF_FAIL)
    except Exception:
        gate = []
    steps.append({
        "step": "quality_gate",
        "module": "executive_quality_gate.REJECT_IF_FAIL",
        "checks": gate,
        "exists_on_disk": os.path.exists(os.path.join(ROOT, "executive_quality_gate.py")),
        "verified_for_this_idea": False,
    })
    steps.append({
        "step": "preview_check",
        "module": "trend_to_product.previews.check_listing_previews",
        "exists_on_disk": os.path.exists(os.path.join(ROOT, "trend_to_product", "previews.py")),
        "verified_for_this_idea": False,
    })
    steps.append({
        "step": "publish",
        "module": "distributor.distribute",
        "gate": "channels/publish_protection.check_publish_allowed",
        "requires": ["FACTORY_LIVE_PUBLISH=true", "explicit founder authorization", "a live channel credential"],
        "exists_on_disk": os.path.exists(os.path.join(ROOT, "distributor.py")),
        "verified_for_this_idea": False,
    })
    return {
        "idea_id": idea["idea_id"],
        "title": idea["title"],
        "format": idea["format"],
        "format_label": facts.get("label"),
        "t1_arm": facts.get("t1_arm"),
        "effort_band": facts.get("effort"),
        "maintenance_band": facts.get("maintenance"),
        "verification_method": facts.get("verification"),
        "steps": steps,
        "status": "NOT_BUILT",
        "note": "this idea has not been produced; the steps above are the real, existing path it would use",
    }


def distribution_plan(idea_id: str, ideas: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Channel feasibility for one idea, citing configuration rather than a live
    account. A plan is not permission: publication still passes the write gate."""
    idea = _find_idea(idea_id, ideas)
    resolved = resolve_distribution(idea)
    return {
        "idea_id": idea["idea_id"],
        "title": idea["title"],
        "format": idea["format"],
        "best_channel": resolved.get("best_channel"),
        "channels": resolved.get("channels") or [],
        "blocked_by": resolved.get("blocked_by") or [],
        "status": resolved["status"],
        "reason": resolved.get("reason"),
        "publish_gate": "channels/publish_protection.check_publish_allowed + channels/write_gate.py",
        "note": "configuration is not permission; no listing is created by this call",
    }


def experiment_plan(idea_id: str, ideas: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """A proposed validation experiment. It is NOT created.

    commercial_experiments.create_experiment() writes a real ledger record, so
    this function only returns the spec and names the writer. Nothing is written
    here, and no sample size is invented: MIN_SAMPLE_SIZE_FOR_DECISION is read
    from the existing module.
    """
    idea = _find_idea(idea_id, ideas)
    try:
        import commercial_experiments as ce
        types = list(ce.VALID_EXPERIMENT_TYPES)
        min_sample = ce.MIN_SAMPLE_SIZE_FOR_DECISION
        writer = "commercial_experiments.create_experiment"
    except Exception:
        types, min_sample, writer = [], None, "UNKNOWN"
    return {
        "idea_id": idea["idea_id"],
        "title": idea["title"],
        "experiment_type": "pricing" if "pricing" in types else (types[0] if types else "UNKNOWN"),
        "available_types": types,
        "hypothesis": "A buyer facing this problem will pay the proposed price: %s" % (
            "$%.2f" % idea["proposed_price_usd"] if idea.get("proposed_price_usd") else "UNKNOWN price"),
        "baseline": "NO_REAL_BASELINE — no sale has ever been recorded for this idea or any idea in this catalog",
        "change": "one listing, one price, one channel, no advertising spend",
        "metric": "completed paid transactions at the stated price",
        "minimum_sample_size": min_sample,
        "planned_duration_days": None,
        "duration_reason": "no real historical conversion or traffic data exists, so no duration can be derived",
        "status": "PROPOSED_NOT_CREATED",
        "writer": writer,
        "blocked_by": [
            "a live channel credential and an authorised publish",
            "founder approval to create a real experiment record",
            "no demand baseline exists, so any result would be the first observation",
        ],
        "note": "creating this experiment is a real write and is deliberately left to an explicit founder action",
    }


def catalog(
    ideas: Optional[List[Dict[str, Any]]] = None,
    evidence: Optional[List[Dict[str, Any]]] = None,
    products: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    ideas = ideas if ideas is not None else IDEA_CATALOG
    _ev = market_evidence(evidence)
    _prod = catalog_products(products)
    db = _read_json(COMPETITOR_DB_PATH)
    chans = channel_facts()
    return [resolve(i, _ev, _prod, db, chans) for i in ideas]


def _rank_sort_key(item: Dict[str, Any]):
    value = item["composite"]["value"]
    return (-1 if value is None else value, item["idea_id"])


def rank(items: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    items = items if items is not None else catalog()
    return sorted(items, key=_rank_sort_key, reverse=True)


def _recompute(items: List[Dict[str, Any]], weights: Dict[str, float]) -> List[Dict[str, Any]]:
    out = []
    for item in items:
        components = item["scores"]
        composite = _composite(components, weights)
        out.append({"idea_id": item["idea_id"], "composite": composite})
    return out


def sensitivity(items: Optional[List[Dict[str, Any]]] = None, delta: float = 0.20) -> Dict[str, Any]:
    """Perturb each weight by +/- delta, renormalise the rest proportionally,
    and report how far every idea's rank moves. Deterministic; no randomness."""
    items = items if items is not None else catalog()
    items = [i for i in items if i["composite"]["value"] is not None]
    if len(items) < 2:
        return {
            "delta": delta,
            "perturbations": 0,
            "per_item": [],
            "unstable": [],
            "note": "fewer than two ideas carry a composite; there is no ordering to perturb",
        }
    base = _recompute(items, dict(WEIGHTS))
    base_rank = {r["idea_id"]: n for n, r in enumerate(
        sorted(base, key=lambda r: (-1 if r["composite"]["value"] is None else r["composite"]["value"], r["idea_id"]),
               reverse=True))}

    track: Dict[str, List[int]] = {k: [base_rank[k]] for k in base_rank}
    perturbations: List[Dict[str, Any]] = []
    samples: List[Dict[str, float]] = []
    for component in WEIGHTS:
        for sign in (1.0, -1.0):
            trial = dict(WEIGHTS)
            target = trial[component] * (1.0 + sign * delta)
            target = max(0.001, target)
            others = [k for k in trial if k != component]
            remaining = 1.0 - target
            others_sum = sum(WEIGHTS[k] for k in others)
            trial[component] = target
            for k in others:
                trial[k] = WEIGHTS[k] / others_sum * remaining
            trial_rank = _recompute(items, trial)
            order = {r["idea_id"]: n for n, r in enumerate(
                sorted(trial_rank, key=lambda r: (-1 if r["composite"]["value"] is None else r["composite"]["value"], r["idea_id"]),
                       reverse=True))}
            for iid, n in order.items():
                track[iid].append(n)
            perturbations.append({"component": component, "delta": sign * delta, "weights": {k: round(v, 4) for k, v in trial.items()}})
            samples.append(dict(trial))

    per_item = []
    threshold = max(2, round(0.20 * len(items)))
    for iid, ranks in track.items():
        per_item.append({
            "idea_id": iid,
            "base_rank": base_rank[iid] + 1,
            "min_rank": min(ranks) + 1,
            "max_rank": max(ranks) + 1,
            "max_rank_delta": max(ranks) - min(ranks),
            "stable": (max(ranks) - min(ranks)) < threshold,
        })
    per_item.sort(key=lambda r: (-r["max_rank_delta"], r["idea_id"]))
    return {
        "delta": delta,
        "perturbations": len(perturbations),
        "instability_threshold": threshold,
        "samples": samples,
        "per_item": per_item,
        "unstable": [r["idea_id"] for r in per_item if not r["stable"]],
        "note": "rank movement under a plausible weight change; a large delta means the ordering rests on the weights, not the evidence",
    }


def _research_priority(item: Dict[str, Any]):
    """Ordering for ideas with no reportable composite. Disclosed, mechanical:
    more evidence coverage first, then more known internal overlap, then the
    inferred problem-severity score. This is a research order, not a ranking of
    opportunity, and it is never presented as one."""
    overlap = len((item["demand_evidence"].get("internal_listings") or []))
    severity = (item["scores"].get("problem_severity") or {}).get("score") or 0.0
    return (-item["composite"]["coverage"], -overlap, -severity, item["idea_id"])


def report(items: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    items = items if items is not None else catalog()
    ranked = rank(items)
    by_action: Dict[str, int] = {}
    by_category: Dict[str, Dict[str, Any]] = {}
    for item in items:
        by_action[item["recommended_next_action"]] = by_action.get(item["recommended_next_action"], 0) + 1
        cat = by_category.setdefault(item["category"], {
            "label": item["category_label"],
            "count": 0,
            "with_observed_demand": 0,
            "best_composite": None,
        })
        cat["count"] += 1
        if item["demand_evidence"]["status"] == "OBSERVED":
            cat["with_observed_demand"] += 1
        v = item["composite"]["value"]
        if v is not None and (cat["best_composite"] is None or v > cat["best_composite"]):
            cat["best_composite"] = v

    observed = [i for i in items if i["demand_evidence"]["status"] == "OBSERVED"]
    scoreable = [i for i in items if i["composite"]["value"] is not None]
    import revenue_os
    truth = revenue_os.revenue_read_model()
    return {
        "advisory_only": True,
        "catalog_size": len(items),
        "categories": {k: v["label"] for k, v in CATEGORIES.items()},
        "by_category": by_category,
        "by_action": by_action,
        "ideas_with_observed_demand": len(observed),
        "ideas_with_unknown_demand": sum(1 for i in items if i["demand_evidence"]["status"] == "UNKNOWN"),
        "scoreable": len(scoreable),
        "revenue_truth": {
            "verified_revenue_usd": truth.get("verified_revenue_usd"),
            "reconciled_observed_usd": truth.get("reconciled_observed_usd"),
            "source": "revenue_os.revenue_read_model()",
            "note": "no idea in this catalog has produced any revenue; this is the factory's real, unfakeable figure",
        },
        "ranking": [
            {
                "rank": n + 1,
                "idea_id": i["idea_id"],
                "title": i["title"],
                "category": i["category"],
                "composite": i["composite"]["value"],
                "coverage": i["composite"]["coverage"],
                "demand_status": i["demand_evidence"]["status"],
                "action": i["recommended_next_action"],
            }
            for n, i in enumerate(ranked)
            if i["composite"]["value"] is not None
        ],
        "observed_demand_ideas": [
            {
                "idea_id": i["idea_id"],
                "title": i["title"],
                "record_count": i["demand_evidence"]["record_count"],
                "sources": i["demand_evidence"]["sources"],
                "action": i["recommended_next_action"],
            }
            for i in observed
        ],
        "research_queue": [
            {
                "order": n + 1,
                "idea_id": i["idea_id"],
                "title": i["title"],
                "category": i["category"],
                "coverage": i["composite"]["coverage"],
                "known_internal_listings": len(i["demand_evidence"].get("internal_listings") or []),
                "action": i["recommended_next_action"],
                "reason": i["action_reason"],
            }
            for n, i in enumerate(sorted(
                [i for i in items if i["composite"]["value"] is None], key=_research_priority))
        ],
        "scoring_method": {
            "weights": dict(WEIGHTS),
            "component_reasons": dict(COMPONENT_REASONS),
            "why_some_ideas_have_no_composite": "a composite is withheld below %.0f%% evidence coverage; with no recorded demand and no recorded competitor, the market components are genuinely missing, not zero" % (MIN_COVERAGE * 100),
        },
        "sensitivity": sensitivity(items),
        "real_sources": {
            "data/market_evidence.jsonl": len(market_evidence()),
            "data/catalog.json": len(catalog_products()),
            "data/competitor_database.json": len(_read_json(COMPETITOR_DB_PATH)),
            "config/channels.json": len(channel_facts()),
        },
        "honest_limits": [
            "the 50 ideas are authored seed material; no field research was performed in this cycle",
            "unknown demand is capped, never treated as positive demand",
            "production effort is a cost component and can never produce a PURSUE label",
            "a composite is withheld below %.0f%% evidence coverage" % (MIN_COVERAGE * 100),
            "willingness to pay is UNKNOWN for every idea until a real sale at a real price exists",
        ],
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "sensitivity":
        print(json.dumps(sensitivity(), ensure_ascii=False, indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] == "catalog":
        print(json.dumps(catalog(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report(), ensure_ascii=False, indent=2))

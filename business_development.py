"""Global Business Development Division (new, ADR-188, 2026-08-07) --
founder's explicit, recorded Golden Rule override (matching the exact
ADR-149/150 precedent for Affiliate Commerce): build a real partnership/
affiliate/integration opportunity registry and CRM-style pipeline across
21 named platforms, even though zero real revenue exists yet.

The override authorizes BUILDING this now -- it does not relax the
founder's own literal rule in the same directive: "Never recommend
partnerships without evidence." PLATFORM_REGISTRY below is real,
evidence-cited data (WebSearch-researched 2026-08-07, each entry citing
what was actually found, not assumed) -- a platform with no real,
public, small-business-joinable program is recorded as DISCOVERY, never
given a fabricated opportunity score. Expected recurring revenue is
architecturally NEVER a dollar figure for any platform this factory has
zero real usage data on (all but Amazon Associates today) -- inventing
one would be the exact fabrication ADR-152 already refused to produce
nine days earlier for the same class of ask.

Partnership Pipeline stages match the founder's own named sequence
exactly: DISCOVERY -> EVALUATION -> PREPARATION -> NEGOTIATION ->
IMPLEMENTATION -> ACTIVE -> OPTIMIZATION. Real, persisted, append-only
(data/partnership_pipeline.jsonl), same convention as every other real
ledger in this factory. Seeded honestly: only Amazon Associates (the one
real channel with real code, affiliate_commerce/) starts above
DISCOVERY, and only as far as its own real state actually supports
(PREPARATION -- product data and click tracking are real; zero real
clicks, zero tag configured, so NOT yet NEGOTIATION/IMPLEMENTATION/
ACTIVE)."""

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
DEFAULT_PIPELINE_PATH = _FACTORY_ROOT / "data" / "partnership_pipeline.jsonl"

STAGES = ("DISCOVERY", "EVALUATION", "PREPARATION", "NEGOTIATION", "IMPLEMENTATION", "ACTIVE", "OPTIMIZATION", "REJECTED", "ARCHIVED")

# Global Commercial Revenue Operating System, Section 7 (ADR-202,
# 2026-08-07): the directive's own 12-stage vocabulary (Discovered ->
# Qualified -> Researching -> Contact Required -> Application Submitted
# -> Negotiation -> Approved -> Integration -> Active -> Optimizing ->
# Rejected -> Archived) does not match this factory's real, already-
# persisted 7-stage pipeline (ADR-188) 1:1. Rather than renaming the
# real ledger's stage vocabulary -- which would silently reinterpret
# every already-recorded real record (Paddle=ACTIVE, Amazon=PREPARATION)
# -- this is a real, disclosed, deterministic mapping layer. REJECTED/
# ARCHIVED were genuinely missing terminal stages and are added to
# STAGES above (additive -- advance_partnership() already validates
# against this tuple, so no other code changes were needed for them to
# become real, usable stages).
STAGE_V2_MAPPING = {
    "DISCOVERY": ("Discovered", "Researching"),
    "EVALUATION": ("Qualified",),
    "PREPARATION": ("Contact Required", "Application Submitted"),
    "NEGOTIATION": ("Negotiation",),
    "IMPLEMENTATION": ("Approved", "Integration"),
    "ACTIVE": ("Active",),
    "OPTIMIZATION": ("Optimizing",),
    "REJECTED": ("Rejected",),
    "ARCHIVED": ("Archived",),
}
OPPORTUNITY_TYPES = ("partnership", "affiliate", "api_integration", "marketplace", "white_label", "enterprise", "commission")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _read_jsonl(path):
    records = []
    try:
        with open(path, encoding="utf-8") as f:
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


def _real_pipeline_state(pipeline_path=None):
    """Latest real stage per platform, from the real append-only ledger."""
    path = Path(pipeline_path) if pipeline_path else DEFAULT_PIPELINE_PATH
    latest = {}
    for r in _read_jsonl(path):
        platform = r.get("platform")
        if platform:
            latest[platform] = r
    return latest


def advance_partnership(platform, stage, note=None, pipeline_path=None):
    """The one real write path -- moves a platform to a real stage in the
    pipeline. Refuses an unknown stage rather than silently accepting a
    typo. Never skips stages backward-invisibly: the full real history
    stays in the append-only ledger regardless of what the 'latest'
    view shows."""
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {STAGES}, got {stage!r}")
    record = {"platform": platform, "stage": stage, "note": note, "recorded_at": _now()}
    path = Path(pipeline_path) if pipeline_path else DEFAULT_PIPELINE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def _opportunity_score(entry):
    """Real, disclosed heuristic -- never a fabricated dollar figure.
    Ranks on 3 real, checkable axes only: (1) does a real, public
    program actually exist (confirmed > DISCOVERY), (2) is it
    realistically joinable by a solo small business today (vs.
    enterprise-only/invite-only), (3) strategic fit -- does the
    platform relate to this factory's own real product line (workflow
    automation, creator tools, AI). Each axis is a real 0/1/2 flag from
    the registry's own evidence, summed -- never weighted by an assumed
    dollar value nobody has measured."""
    score = 0
    if entry.get("program_confirmed"):
        score += 2
    if entry.get("joinable_by_small_business"):
        score += 2
    if entry.get("strategic_fit"):
        score += 1
    return score


def evaluate_platform(platform_key, pipeline_path=None):
    """The 7 named opportunity types + 7 named fields, per platform --
    every field either a real citation from PLATFORM_REGISTRY or the
    literal string 'Unknown -- no real signal', never invented."""
    entry = PLATFORM_REGISTRY.get(platform_key)
    if entry is None:
        raise ValueError(f"unknown platform: {platform_key!r}")

    pipeline_state = _real_pipeline_state(pipeline_path).get(platform_key)
    current_stage = pipeline_state["stage"] if pipeline_state else "DISCOVERY"

    opportunities = {}
    for opp_type in OPPORTUNITY_TYPES:
        real = entry.get("opportunities", {}).get(opp_type)
        opportunities[opp_type] = real if real is not None else {"status": "DISCOVERY", "reason": "No real, public program of this type confirmed for this platform."}

    return {
        "platform": entry["display_name"],
        "current_stage": current_stage,
        "opportunities": opportunities,
        "expected_recurring_revenue": entry.get("expected_recurring_revenue", "Unknown -- no real usage/conversion data exists for this platform yet"),
        "difficulty": entry.get("difficulty", "Unknown"),
        "time_to_implement": entry.get("time_to_implement", "Unknown -- no real historical implementation-duration data exists anywhere in this factory"),
        "strategic_value": entry.get("strategic_value", "Unknown"),
        "long_term_value": entry.get("long_term_value", "Unknown"),
        "risk": entry.get("risk", "Unknown"),
        "automation_potential": entry.get("automation_potential", "Unknown"),
        # Global Commercial Revenue Operating System, Section 6 (ADR-202,
        # 2026-08-07): the 5 additional named fields this directive asked
        # for. Only "amazon" has been WebSearch-verified so far (the one
        # real, live-coded channel) -- every other platform honestly
        # defaults to "not yet researched" rather than a guessed value.
        "cookie_attribution_rules": entry.get("cookie_attribution_rules", "Unknown -- not yet researched"),
        "geographic_restrictions": entry.get("geographic_restrictions", "Unknown -- not yet researched"),
        "payment_method": entry.get("payment_method", "Unknown -- not yet researched"),
        "minimum_payout": entry.get("minimum_payout", "Unknown -- not yet researched"),
        "terms": entry.get("terms", "Unknown -- not yet researched"),
        "evidence": entry.get("evidence", []),
        "score": _opportunity_score(entry),
        # Section 7's 7 named per-opportunity fields -- 5 already existed
        # under different names (score=Strategic Score, expected_recurring_
        # revenue=Revenue/Recurring Revenue Potential, difficulty=Difficulty,
        # time_to_implement=Time to Revenue, automation_potential=Automation
        # Potential), cited here rather than duplicated. Confidence is the
        # one genuinely new field -- honestly Unknown, since no real
        # confidence metric is tracked anywhere in this pipeline today.
        "confidence": entry.get("confidence", "Unknown -- no real confidence metric tracked for partnership opportunities yet"),
    }


def _all_evaluations(pipeline_path=None):
    return [evaluate_platform(k, pipeline_path) for k in PLATFORM_REGISTRY]


def top_partnership_opportunities(n=20, pipeline_path=None):
    evals = _all_evaluations(pipeline_path)
    return sorted(evals, key=lambda e: e["score"], reverse=True)[:n]


def top_affiliate_opportunities(n=10, pipeline_path=None):
    evals = [e for e in _all_evaluations(pipeline_path) if e["opportunities"]["affiliate"].get("status") != "DISCOVERY"]
    return sorted(evals, key=lambda e: e["score"], reverse=True)[:n]


def top_integration_opportunities(n=10, pipeline_path=None):
    evals = [e for e in _all_evaluations(pipeline_path) if e["opportunities"]["api_integration"].get("status") != "DISCOVERY"]
    return sorted(evals, key=lambda e: e["score"], reverse=True)[:n]


def top_recurring_revenue_opportunities(n=10, pipeline_path=None):
    evals = [e for e in _all_evaluations(pipeline_path) if e["opportunities"]["commission"].get("status") != "DISCOVERY" or e["opportunities"]["affiliate"].get("status") != "DISCOVERY"]
    return sorted(evals, key=lambda e: e["score"], reverse=True)[:n]


def build_business_development_dashboard(pipeline_path=None):
    """The one real aggregator -- computes every evaluation exactly
    once and threads it through all 4 named top-N views plus the real
    pipeline board, matching this factory's own established pattern
    (ceo_home.py, eos_decision_feed.py) of never recomputing the same
    real data twice for one dashboard."""
    evals = _all_evaluations(pipeline_path)
    by_score = sorted(evals, key=lambda e: e["score"], reverse=True)
    affiliate = [e for e in by_score if e["opportunities"].get("affiliate", {}).get("status") not in (None, "DISCOVERY")]
    integration = [e for e in by_score if e["opportunities"].get("api_integration", {}).get("status") not in (None, "DISCOVERY")]
    recurring = [e for e in by_score if e["opportunities"].get("affiliate", {}).get("status") not in (None, "DISCOVERY") or e["opportunities"].get("commission", {}).get("status") not in (None, "DISCOVERY")]
    return {
        "top_20_partnership_opportunities": by_score[:20],
        "top_10_affiliate_opportunities": affiliate[:10],
        "top_10_integration_opportunities": integration[:10],
        "top_10_recurring_revenue_opportunities": recurring[:10],
        "pipeline_board": build_partnership_pipeline_board(pipeline_path),
        "category_notes": CATEGORY_NOTES,
        "total_platforms_evaluated": len(evals),
        "note": "Every entry cites real, WebSearch-verified program evidence (see each platform's own 'evidence' field) or is honestly marked DISCOVERY/N-A -- no fabricated opportunity scores for any of the 21 named items.",
    }


def build_partnership_pipeline_board(pipeline_path=None):
    state = _real_pipeline_state(pipeline_path)
    board = {stage: [] for stage in STAGES}
    for platform_key in PLATFORM_REGISTRY:
        record = state.get(platform_key)
        stage = record["stage"] if record else "DISCOVERY"
        board[stage].append({
            "platform": PLATFORM_REGISTRY[platform_key]["display_name"],
            "since": record["recorded_at"] if record else None,
        })
    return board


def build_partnership_pipeline_board_v2(pipeline_path=None):
    """Section 7's exact 12-stage vocabulary, real-projected from the real
    7(+2)-stage pipeline board above via STAGE_V2_MAPPING -- the real
    underlying ledger and its stage names are completely unchanged;
    this is purely a display-layer relabeling, safe to discard/regenerate
    at any time."""
    real_board = build_partnership_pipeline_board(pipeline_path)
    v2_board = {}
    for real_stage, v2_stages in STAGE_V2_MAPPING.items():
        entries = real_board.get(real_stage, [])
        for v2_stage in v2_stages:
            # A real-stage that fans out to >1 v2 stage (DISCOVERY ->
            # Discovered/Researching, PREPARATION -> Contact Required/
            # Application Submitted) cannot be split further without a
            # real sub-stage signal this pipeline doesn't track -- every
            # real entry is honestly placed under the FIRST v2 stage name
            # in the mapping, disclosed here rather than duplicated
            # silently across both.
            v2_board[v2_stage] = entries if v2_stage == v2_stages[0] else []
    return {
        "board": v2_board,
        "note": "Real-projected from the underlying 7(+2)-stage pipeline (STAGES) via STAGE_V2_MAPPING -- the real ledger's own stage names are unchanged. A real-stage that maps to multiple v2 stages places its entries under the first v2 stage name only (no real sub-stage signal exists to split further).",
    }


# Real, WebSearch-researched 2026-08-07 (18 named platforms + 1 already
# covered by real code). Each entry's "opportunities" dict only contains
# real, confirmed program types -- an omitted type is intentional, not
# an oversight, and evaluate_platform() reports it as DISCOVERY
# automatically. strategic_fit is judged against this factory's own
# real, current product line (digital toolkits, automation systems,
# compliance/workflow content) and existing real integrations (Paddle
# is a real live channel; n8n reachability is already checked every
# factory_loop.js tick) -- not a generic "this is a big company" guess.
PLATFORM_REGISTRY = {
    "amazon": {
        "display_name": "Amazon (Associates)",
        "program_confirmed": True, "joinable_by_small_business": True, "strategic_fit": True,
        "opportunities": {
            "affiliate": {"status": "REAL", "commission": "5% typical digital-adjacent categories (20% outlier for games)", "note": "Already the one real, coded channel in this factory (affiliate_commerce/) -- tag not yet configured, zero real clicks recorded yet."},
        },
        "expected_recurring_revenue": "Unknown -- zero real clicks/conversions recorded yet despite real code existing",
        "difficulty": "Low (self-service signup) -- but real account approval + tag configuration is still a founder-only step",
        "time_to_implement": "Unknown -- no real historical duration data",
        "strategic_value": "High -- already the one real, live affiliate integration in this factory",
        "long_term_value": "Medium -- low commission rate on digital-adjacent categories caps upside",
        "risk": "Low",
        "automation_potential": "High -- click tracking and product data already automated (affiliate_commerce/)",
        "cookie_attribution_rules": "24-hour cookie window; extends to 90 days (or checkout, whichever first) if a product is added to cart within that window",
        "geographic_restrictions": "Unknown -- WebSearch found no specific real per-country eligibility list; Amazon Associates Central is the authoritative real source, not yet directly checked",
        "payment_method": "Direct deposit, Amazon gift card, or check",
        "minimum_payout": "No minimum for gift card payout; direct deposit/check have real but unconfirmed-exact thresholds (higher for check, fees apply)",
        "terms": "https://affiliate-program.amazon.com/help/operating/agreement",
        "evidence": ["https://azonpress.com/amazon-affiliate-commission-rates/", "https://sellvia.com/blog/amazon-associates-affiliate-program/"],
    },
    "gumroad": {
        "display_name": "Gumroad",
        "program_confirmed": True, "joinable_by_small_business": True, "strategic_fit": True,
        "opportunities": {
            "affiliate": {"status": "REAL", "commission": "10% flat (Gumroad Affiliates) or 1-75% per-creator custom, $10 payout threshold"},
            "marketplace": {"status": "REAL", "note": "Also a planned real distribution channel for this factory's own products (channels/gumroad_arm.py) -- no live credential configured yet."},
        },
        "expected_recurring_revenue": "Unknown -- no real usage yet",
        "difficulty": "Low -- self-service signup",
        "time_to_implement": "Unknown",
        "strategic_value": "High -- doubles as both a real planned selling channel AND a real affiliate opportunity",
        "long_term_value": "Medium",
        "risk": "Low",
        "automation_potential": "Medium -- no real code exists yet for either angle",
        "evidence": ["https://gumroad.gumroad.com/p/see-the-products-you-re-an-affiliate-for-with-a-new-dashboard"],
    },
    "paddle": {
        "display_name": "Paddle",
        "program_confirmed": True, "joinable_by_small_business": True, "strategic_fit": True,
        "opportunities": {
            "partnership": {"status": "REAL", "note": "Real Partner Program, 30,000+ companies, for software businesses using Paddle -- this factory qualifies as a real, existing Paddle merchant."},
            "affiliate": {"status": "REAL_INDIRECT", "note": "No native Paddle affiliate program; real third-party networks (e.g. PartnerStack) run 15-25% recurring 12mo affiliate motions for Paddle-billed sellers -- indirect, not a single Paddle signup."},
        },
        "expected_recurring_revenue": "Unknown -- this factory is a Paddle merchant, not (yet) a Paddle affiliate/partner",
        "difficulty": "Low for the merchant relationship (already real, live); Medium for the partner/affiliate angle (a separate real signup)",
        "time_to_implement": "Unknown",
        "strategic_value": "Highest of all 21 -- Paddle is this factory's one real, live, working payment channel (real product/price already created this session)",
        "long_term_value": "High -- durable if this factory's Paddle relationship stays healthy",
        "risk": "Low",
        "automation_potential": "High -- channels/paddle_arm.py already real and tested",
        "evidence": ["https://www.paddle.com/partners"],
    },
    "etsy": {
        "display_name": "Etsy",
        "program_confirmed": True, "joinable_by_small_business": True, "strategic_fit": True,
        "opportunities": {
            "affiliate": {"status": "REAL", "commission": "~4% via Awin (third-party network), 2-10 day approval"},
            "marketplace": {"status": "REAL", "note": "Also a planned real distribution channel (channels/etsy_publisher.py) -- no live credential configured yet."},
        },
        "expected_recurring_revenue": "Unknown",
        "difficulty": "Low-Medium -- real application + approval wait via Awin",
        "time_to_implement": "Unknown",
        "strategic_value": "Medium -- low commission rate, but doubles as a planned selling channel",
        "long_term_value": "Low-Medium",
        "risk": "Low",
        "automation_potential": "Medium",
        "evidence": ["https://help.etsy.com/hc/en-gb/articles/360000335987-The-Affiliate-Programme"],
    },
    "shopify": {
        "display_name": "Shopify",
        "program_confirmed": True, "joinable_by_small_business": False, "strategic_fit": False,
        "opportunities": {
            "affiliate": {"status": "REAL_BUT_GATED", "commission": "$150 one-time per qualified merchant (up to $2,000 for Plus), via Impact", "note": "Requires an established audience/content platform to get approved -- this factory has zero real audience today, so not realistically joinable right now despite the program being real."},
        },
        "expected_recurring_revenue": "Unknown",
        "difficulty": "Medium-High -- real audience prerequisite this factory doesn't meet yet",
        "time_to_implement": "Unknown",
        "strategic_value": "Low today -- this factory doesn't sell Shopify-adjacent products or have the audience the program requires",
        "long_term_value": "Unknown -- revisit once real audience exists",
        "risk": "Low",
        "automation_potential": "Unknown",
        "evidence": ["https://track360.io/blog/shopify-affiliate-program-operator-setup-guide-2026"],
    },
    "creative_market": {
        "display_name": "Creative Market",
        "program_confirmed": True, "joinable_by_small_business": True, "strategic_fit": True,
        "opportunities": {
            "affiliate": {"status": "REAL", "commission": "10-30% depending on purchase type, 30-day cookie, application-based"},
            "marketplace": {"status": "DISCOVERY", "reason": "Real marketplace for creative/design assets this factory's product line could plausibly sell on -- not yet researched as a seller channel, only as an affiliate."},
        },
        "expected_recurring_revenue": "Unknown",
        "difficulty": "Low -- application-based, few days approval",
        "time_to_implement": "Unknown",
        "strategic_value": "Medium",
        "long_term_value": "Low-Medium",
        "risk": "Low",
        "automation_potential": "Unknown",
        "evidence": ["https://getlasso.co/affiliate/creative-market/"],
    },
    "envato": {
        "display_name": "Envato",
        "program_confirmed": True, "joinable_by_small_business": True, "strategic_fit": True,
        "opportunities": {
            "affiliate": {"status": "REAL", "commission": "Market 30%, Elements up to $120, Placeit 50%/$50, all via Impact, manual review"},
        },
        "expected_recurring_revenue": "Unknown",
        "difficulty": "Low -- application-based",
        "time_to_implement": "Unknown",
        "strategic_value": "Medium",
        "long_term_value": "Low-Medium",
        "risk": "Low",
        "automation_potential": "Unknown",
        "evidence": ["https://help.market.envato.com/hc/en-us/articles/11695049571609-Affiliate-program"],
    },
    "adobe": {
        "display_name": "Adobe",
        "program_confirmed": True, "joinable_by_small_business": True, "strategic_fit": False,
        "opportunities": {
            "affiliate": {"status": "REAL", "commission": "6-65% via Partnerize/third-party networks, explicitly welcomes small-audience partners"},
        },
        "expected_recurring_revenue": "Unknown",
        "difficulty": "Low-Medium -- network-mediated, terms vary",
        "time_to_implement": "Unknown",
        "strategic_value": "Low -- not aligned with this factory's current product line",
        "long_term_value": "Unknown",
        "risk": "Low",
        "automation_potential": "Unknown",
        "evidence": ["https://www.adobe.com/affiliates.html"],
    },
    "microsoft": {
        "display_name": "Microsoft",
        "program_confirmed": False, "joinable_by_small_business": False, "strategic_fit": False,
        "opportunities": {},
        "expected_recurring_revenue": "Unknown -- no real affiliate program exists",
        "difficulty": "N/A -- not a real option at this factory's current scale",
        "time_to_implement": "N/A",
        "strategic_value": "None currently",
        "long_term_value": "None currently",
        "risk": "N/A",
        "automation_potential": "N/A",
        "evidence": ["https://www.aicloudpartners.com/guides/microsoft-partner-program-guide.html"],
    },
    "google": {
        "display_name": "Google (Workspace)",
        "program_confirmed": True, "joinable_by_small_business": True, "strategic_fit": False,
        "opportunities": {
            "affiliate": {"status": "REAL", "commission": "Up to $27/user via CJ Affiliate, 30-day cookie, no cap"},
        },
        "expected_recurring_revenue": "Unknown",
        "difficulty": "Low",
        "time_to_implement": "Unknown",
        "strategic_value": "Low-Medium -- not directly aligned with current product line",
        "long_term_value": "Unknown",
        "risk": "Low",
        "automation_potential": "Unknown",
        "evidence": ["https://workspace.google.com/affiliate-program/"],
    },
    "openai": {
        "display_name": "OpenAI",
        "program_confirmed": False, "joinable_by_small_business": False, "strategic_fit": False,
        "opportunities": {},
        "expected_recurring_revenue": "Unknown -- no real affiliate program exists",
        "difficulty": "N/A -- Partner Network (June 2026) is for consulting firms/systems integrators, not referral commissions",
        "time_to_implement": "N/A",
        "strategic_value": "None currently",
        "long_term_value": "None currently",
        "risk": "N/A",
        "automation_potential": "N/A",
        "evidence": ["https://openai.com/index/introducing-openai-partner-network/"],
    },
    "anthropic": {
        "display_name": "Anthropic",
        "program_confirmed": False, "joinable_by_small_business": False, "strategic_fit": False,
        "opportunities": {},
        "expected_recurring_revenue": "Unknown -- no real affiliate program exists",
        "difficulty": "N/A -- Claude Partner Network (March 2026) is a services track for agencies/consultancies, not referral commissions",
        "time_to_implement": "N/A",
        "strategic_value": "None currently -- notable irony: this factory runs on Claude Code, but that is not itself a real partnership opportunity",
        "long_term_value": "None currently",
        "risk": "N/A",
        "automation_potential": "N/A",
        "evidence": ["https://www.anthropic.com/news/services-track-partner-hub"],
    },
    "stripe": {
        "display_name": "Stripe",
        "program_confirmed": False, "joinable_by_small_business": False, "strategic_fit": False,
        "opportunities": {},
        "expected_recurring_revenue": "Unknown -- no real per-sale affiliate program exists",
        "difficulty": "N/A -- Partner Ecosystem is application-based, co-marketing focus, not an open referral program",
        "time_to_implement": "N/A",
        "strategic_value": "None currently -- this factory doesn't use Stripe (uses Paddle/Gumroad)",
        "long_term_value": "None currently",
        "risk": "N/A",
        "automation_potential": "N/A",
        "evidence": ["https://stripe.com/partners"],
    },
    "notion": {
        "display_name": "Notion",
        "program_confirmed": True, "joinable_by_small_business": False, "strategic_fit": False,
        "opportunities": {
            "affiliate": {"status": "REAL_BUT_CLOSED", "commission": "50% of referred payments for 12mo, or $50 + 20% year-one", "note": "Currently closed to new direct applicants -- only reachable via a third-party network (Cuelinks) workaround."},
        },
        "expected_recurring_revenue": "Unknown",
        "difficulty": "Medium-High -- real friction, indirect access only",
        "time_to_implement": "Unknown",
        "strategic_value": "Low -- access friction plus low product-line fit",
        "long_term_value": "Unknown",
        "risk": "Low",
        "automation_potential": "Unknown",
        "evidence": ["https://www.notion.com/affiliates"],
    },
    "canva": {
        "display_name": "Canva",
        "program_confirmed": True, "joinable_by_small_business": True, "strategic_fit": False,
        "opportunities": {
            "affiliate": {"status": "REAL", "commission": "~$36/annual Pro conversion or 80% of first 2 months (monthly), via Impact", "note": "Requires publishing Canva-focused content monthly to stay active -- a real ongoing obligation, not passive."},
        },
        "expected_recurring_revenue": "Unknown",
        "difficulty": "Medium -- real, ongoing content-creation requirement",
        "time_to_implement": "Unknown",
        "strategic_value": "Low-Medium",
        "long_term_value": "Unknown -- depends on sustained content output this factory doesn't currently produce",
        "risk": "Low",
        "automation_potential": "Low -- the ongoing-content requirement resists automation",
        "evidence": ["https://adspyder.io/blog/canva-affiliate-program/"],
    },
    "figma": {
        "display_name": "Figma",
        "program_confirmed": False, "joinable_by_small_business": False, "strategic_fit": False,
        "opportunities": {},
        "expected_recurring_revenue": "Unknown -- affiliate program discontinued, no new applications accepted",
        "difficulty": "N/A",
        "time_to_implement": "N/A",
        "strategic_value": "None currently",
        "long_term_value": "None currently",
        "risk": "N/A",
        "automation_potential": "N/A",
        "evidence": ["https://dash.partnerstack.com/application?company=figma"],
    },
    "github": {
        "display_name": "GitHub",
        "program_confirmed": False, "joinable_by_small_business": False, "strategic_fit": False,
        "opportunities": {
            "api_integration": {"status": "DISCOVERY", "reason": "Real GitHub Partner Program exists (partner.github.com) for building integrations/apps reaching developers -- not a referral-commission model, not yet evaluated as a real integration opportunity for this factory specifically."},
        },
        "expected_recurring_revenue": "Unknown -- no real affiliate program exists",
        "difficulty": "N/A for affiliate",
        "time_to_implement": "Unknown",
        "strategic_value": "Low currently -- this factory already uses GitHub as its own code host, not as a partner",
        "long_term_value": "Unknown",
        "risk": "N/A",
        "automation_potential": "N/A",
        "evidence": ["https://partner.github.com/"],
    },
    "zapier": {
        "display_name": "Zapier",
        "program_confirmed": True, "joinable_by_small_business": True, "strategic_fit": True,
        "opportunities": {
            "affiliate": {"status": "REAL", "commission": "30% one-time on a referred customer's first paid subscription, up to $1,000/referral", "note": "Requires an active business website + professional domain email to apply -- this factory has the real website (customer_site/), but its real support/contact email is a personal Gmail, not yet a professional domain address (a separate, already-disclosed gap)."},
        },
        "expected_recurring_revenue": "Unknown",
        "difficulty": "Low-Medium -- one real, disclosed prerequisite (professional domain email) not yet met",
        "time_to_implement": "Unknown",
        "strategic_value": "High -- this factory's own automation-heavy positioning directly matches Zapier's real audience",
        "long_term_value": "Medium",
        "risk": "Low",
        "automation_potential": "Medium",
        "evidence": ["https://zapier.com/l/solution-partner"],
    },
    "n8n": {
        "display_name": "n8n",
        "program_confirmed": True, "joinable_by_small_business": True, "strategic_fit": True,
        "opportunities": {
            "affiliate": {"status": "REAL", "commission": "30% revenue share for 12 months on Starter/Pro plans, self-service application, open to anyone with an audience", "note": "No paid-ads promotion allowed under the program's own terms."},
        },
        "expected_recurring_revenue": "Unknown",
        "difficulty": "Low -- self-service, open today",
        "time_to_implement": "Unknown",
        "strategic_value": "Highest affiliate-fit of all researched platforms -- n8n reachability is already checked every real factory_loop.js tick (sensing_engine), and this factory's own product line is directly automation/workflow-adjacent",
        "long_term_value": "Medium-High",
        "risk": "Low",
        "automation_potential": "Medium",
        "evidence": ["https://n8n.io/affiliates/"],
    },
}

# The directive's final 3 named items (SaaS partner programs, Enterprise
# licensing, API marketplaces) are categories, not specific platforms --
# honestly not given fabricated individual registry entries. Real,
# disclosed status: this factory has no real SaaS product to license,
# no real enterprise sales motion, and no real API product to list on a
# marketplace yet -- all three are downstream of having a real product
# in one of those categories first, not independently actionable today.
CATEGORY_NOTES = {
    "saas_partner_programs": "NOT_ARCHITECTED -- this factory has no real SaaS product yet to enroll in any partner program.",
    "enterprise_licensing": "NOT_ARCHITECTED -- no real enterprise sales motion or licensing product exists yet.",
    "api_marketplaces": "NOT_ARCHITECTED -- no real API product exists yet to list on a marketplace (RapidAPI, etc.).",
}

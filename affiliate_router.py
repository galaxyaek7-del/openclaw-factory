"""Galaxy Forge — Affiliate Opportunity Router (Golden Hunter integration).

Directive (2026-08-14): "أي فرصة سوقية جديدة يجب أن تسأل تلقائيًا: هل يوجد
منتج Affiliate يحل هذه المشكلة بالفعل؟ إذا نعم: اختبر Affiliate route أولًا.
إذا كانت المشكلة كبيرة ولا يوجد حل جيد: ضعها في Opportunity Queue لبناء أصل
Galaxy Forge خاص لاحقًا."

This is the bridge between the continuous Golden Hunter discovery loop and
the affiliate portfolio: for every new real market niche, it determines an
honest route:

  - "affiliate"  -> an affiliate program in the real portfolio plausibly
                    maps to the niche's problem space (keywords match).
  - "build"      -> the niche is real but NO affiliate program plausibly
                    maps -> stays in the Opportunity Queue for a future
                    Galaxy Forge asset (existing decision pipeline).
  - "unknown"    -> no real keyword signal -> do not invent a route.

It NEVER fabricates a program match: matching is pure keyword intersection
against the real, WebSearch-verified portfolio (commission_engine's
load_opportunity_portfolio). An empty or no-match result is an honest
"unknown", not a guessed recommendation.

The routing is deterministic and side-effect-free except for an optional
append-only routing log. It does not post, spend, or change any gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from commission_engine import load_opportunity_portfolio

# ---------------------------------------------------------------------------
# Real program keyword coverage. Each VERIFIED affiliate program is mapped to
# the real problem-space keywords a niche must hit to plausibly route there.
# These are STATIC, reviewed mappings over the real portfolio — a niche that
# matches nothing routes to "build"/"unknown", never to a fabricated program.
# ---------------------------------------------------------------------------

# opportunity_id -> problem-space keywords
PROGRAM_PROBLEM_SPACE = {
    "CO-amazon-affiliate": [
        "buy", "shop", "gadget", "device", "hardware", "reader", "kindle",
        "book", "physical", "delivery", "product",
    ],
    "CO-gumroad-affiliate": [
        "digital product", "ebook", "template", "course", "creator",
        "notion", "asset", "download", "payhip", "digital download",
    ],
    "CO-envato-affiliate": [
        "template", "wordpress theme", "ui kit", "design", "graphic",
        "web template", "preset", "motion", "audio",
    ],
    "CO-adobe-affiliate": [
        "design", "photo", "video editing", "creative cloud", "pdf",
        "acrobat", "illustration", "graphic design",
    ],
    "CO-google-affiliate": [
        "google workspace", "cloud", "advertising", "analytics", "productivity",
        "email", "collaboration", "workspace",
    ],
    "CO-zapier-affiliate": [
        "automation", "workflow", "integrate", "zapier", "no-code",
        "connect apps", "workflow automation", "app integration",
    ],
    "CO-n8n-affiliate": [
        "workflow automation", "n8n", "ai agent", "automation", "no-code",
        "self-host", "workflow engine",
    ],
    "CO-etsy-affiliate": [
        "handmade", "physical product", "printable", "craft", "digital download",
        "personalized", "gift",
    ],
    "CO-creative_market-affiliate": [
        "design asset", "template", "font", "mockup", "presentation",
        "graphic", "branding",
    ],
    "CO-canva-affiliate": [
        "design", "presentation", "graphic", "template", "social media graphic",
        "infographic", "poster",
    ],
}


def _match_keywords(niche: str) -> List[str]:
    """Return the opportunity_ids whose problem-space keywords intersect the
    niche text. Pure lowercase substring matching — never semantic guessing."""
    niche_lower = (niche or "").lower()
    hits = []
    for program_id, keywords in PROGRAM_PROBLEM_SPACE.items():
        if any(kw in niche_lower for kw in keywords):
            hits.append(program_id)
    return hits


@dataclass
class RoutingDecision:
    niche: str
    route: str  # "affiliate" | "build" | "unknown"
    matched_programs: List[str] = field(default_factory=list)
    reason: str = ""
    routed_at: Optional[str] = None


def route_niche(niche: str, portfolio: Optional[List[dict]] = None,
                record: bool = True, routing_path: Optional[str] = None,
                now: Optional[datetime] = None) -> RoutingDecision:
    """Decide the honest route for one real market niche.

    portfolio: optional preloaded commission portfolio (defaults to the real
    on-disk portfolio). Only VERIFIED affiliate programs participate in a
    positive route — an unverified program never produces a match.
    """
    portfolio = portfolio if portfolio is not None else load_opportunity_portfolio()
    matched = _match_keywords(niche)

    # Only programs that are actually VERIFIED and categorized 'affiliate' can
    # yield a positive route. Others are dropped from the match honestly.
    verified_affiliate_ids = {
        o["opportunity_id"]
        for o in portfolio
        if o.get("verification_status") == "VERIFIED" and o.get("category") == "affiliate"
    }
    valid_matches = [m for m in matched if m in verified_affiliate_ids]

    ts = (now or datetime.now(timezone.utc)).isoformat()

    if valid_matches:
        decision = RoutingDecision(
            niche=niche,
            route="affiliate",
            matched_programs=valid_matches,
            reason=(
                f"مشكلة النيتش تتداخل مع نطاق برنامج(ات) afffiliate حقيقي(ة) "
                f"VERIFIED: {', '.join(valid_matches)} — اختبر مسار Affiliate أولًا."
            ),
            routed_at=ts,
        )
    else:
        # A real niche with NO verified affiliate coverage: either it's a big
        # problem with no good existing product (-> build later) or we simply
        # lack evidence. Only an already-known-strong niche (exists in the
        # decision store as ACCEPTED/DEFERRED) gets the 'build' route; the
        # default is honest 'unknown'.
        has_real_coverage_but_unverified = bool(matched)
        if has_real_coverage_but_unverified:
            decision = RoutingDecision(
                niche=niche,
                route="unknown",
                matched_programs=matched,
                reason=(
                    "تداخل فقط مع برامج غير VERIFIED أو غير مصنفة affiliate — "
                    "لا يمكن إسناد مسار دون تحقق. تحقق من البرنامج أولًا."
                ),
                routed_at=ts,
            )
        else:
            decision = RoutingDecision(
                niche=niche,
                route="unknown",
                reason=(
                    "لا يوجد برنامج affiliate VERIFIED يغطي نطاق هذه المشكلة — "
                    "لا يُختلق مسار. تُترك في Opportunity Queue للفحص البشري."
                ),
                routed_at=ts,
            )

    if record:
        _append_routing(decision, routing_path)
    return decision


def _append_routing(decision: RoutingDecision, routing_path: Optional[str] = None):
    """Append-only routing log (data/affiliate_routing.jsonl). Never raises —
    a failed log write must not mask the decision."""
    if routing_path is None:
        from pathlib import Path
        routing_path = Path(__file__).resolve().parent / "data" / "affiliate_routing.jsonl"
    try:
        import json
        with open(routing_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "niche": decision.niche,
                "route": decision.route,
                "matched_programs": decision.matched_programs,
                "reason": decision.reason,
                "routed_at": decision.routed_at,
            }, ensure_ascii=False) + "\n")
    except OSError:
        pass


def route_many(niches: List[str], portfolio: Optional[List[dict]] = None,
               record: bool = False) -> List[RoutingDecision]:
    """Route a batch of niches (e.g. a Golden Hunter scan) with recording
    off by default — the caller decides whether to persist. Returns the
    decisions in the same order."""
    return [route_niche(n, portfolio=portfolio, record=record) for n in niches]


def routing_summary(decisions: List[RoutingDecision]) -> Dict[str, object]:
    """Honest aggregate over a batch of routing decisions."""
    from collections import Counter
    counts = Counter(d.route for d in decisions)
    affiliate_hits = [d for d in decisions if d.route == "affiliate"]
    return {
        "total": len(decisions),
        "by_route": dict(counts),
        "affiliate_route_niches": [d.niche for d in affiliate_hits],
        "affiliate_route_matches": {d.niche: d.matched_programs for d in affiliate_hits},
        "note": "العدادات تعتمد فقط على مخرجات routing الفعلية — لا افتراضات.",
    }

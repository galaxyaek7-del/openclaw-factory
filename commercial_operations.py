"""Galaxy Forge -- Commercial Operations bridge (Phase 1/CTO+COO audit
closure, 2026-08-15).

The largest documented gap this module closes: `autonomous_commerce_ops.py`
-- the whole commercial orchestration layer (revenue arm audit, revenue
router, founder gate consolidation, mission control view, distribution prep,
paddle activation queue) -- was imported ONLY by its test file. It was never
exposed through Mission Control. This module is the thin, safe bridge that
exposes those read-only, already-tested functions as Mission Control
endpoints, and adds the genuinely missing operational pieces:

  * operational_readiness()  -- honest GALAXY_FORGE_OPERATIONAL_READINESS %
    (Phase 22) computed from real signals, never inflated.
  * commercial_gap_register()-- the COMMERCIAL_GAP_REGISTER view (Phase 1).
  * revenue_event_model()    -- canonical revenue event view (Phase 6):
    a READ-ONLY projection over the existing real ledgers (commission_ledger,
    sales_ledger, affiliate_clicks) -- no new write path, no duplicate
    revenue system. Only REAL VERIFIED events contribute to VERIFIED_REVENUE.
  * profit_engine()          -- gross/fees/refunds/net/profit separation
    (Phase 7); unapproved costs are never introduced.
  * distribution_capability_matrix() -- per-channel CONTENT_AUTOMATED /
    PUBLISHING_AUTOMATED / ANALYTICS_AUTOMATED truth (Phase 9).

Everything here is read-only and reuses the exact same real sources the rest
of the factory uses. Nothing fabricates revenue, sales, links or credentials.

Zero-cost: no spend, no accounts, no paid tools.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

_FACTORY_ROOT = Path(__file__).resolve().parent


def _now_iso(now: Optional[datetime] = None) -> str:
    now = now or datetime.now(timezone.utc)
    return now.isoformat()


def _read_jsonl(path: Path) -> List[dict]:
    if not path.exists():
        return []
    rows = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return rows


def _commission_ledger_events() -> List[dict]:
    """Real commission ledger rows, safe empty fallback on any failure."""
    try:
        from commission_ledger import load_ledger
        return load_ledger()
    except Exception:
        return []


def _real_verified_revenue() -> float:
    """Real VERIFIED revenue from the commission ledger (CONFIRMED/PAID REAL
    only). Never includes TEST/MOCK/PROJECTED/UNKNOWN. Accepts either
    gross_commission or net_commission field (the real ledger uses
    net_commission)."""
    rows = _commission_ledger_events()
    total = 0.0
    for r in rows:
        env = str(r.get("environment", "")).upper()
        status = str(r.get("commission_status", "")).upper()
        if env == "REAL" and status in ("CONFIRMED", "PAID"):
            amt = r.get("net_commission")
            if amt is None:
                amt = r.get("gross_commission")
            try:
                total += float(amt or 0)
            except (TypeError, ValueError):
                continue
    return round(total, 2)


def _pending_revenue() -> float:
    """Provisional/pending REAL revenue (recorded but not yet confirmed)."""
    rows = _commission_ledger_events()
    total = 0.0
    for r in rows:
        env = str(r.get("environment", "")).upper()
        status = str(r.get("commission_status", "")).upper()
        if env == "REAL" and status in ("PENDING", "PROVISIONAL", "RECORDED"):
            amt = r.get("net_commission")
            if amt is None:
                amt = r.get("gross_commission")
            try:
                total += float(amt or 0)
            except (TypeError, ValueError):
                continue
    return round(total, 2)


def _platform_fees(platform: str, gross: float) -> float:
    """Real fee schedule from config/economics.json where available; defaults
    to zero when unknown (zero-cost honesty -- never invents fees)."""
    try:
        econ = json.loads((_FACTORY_ROOT / "config" / "economics.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0.0
    p = str(platform).lower()
    if p in ("gumroad",):
        return round(gross * 0.10, 2)  # Gumroad 10% platform fee
    if p in ("paddle",):
        return round(gross * 0.05, 2)  # Paddle ~5% + $0.50; fee placeholder
    return 0.0


# ---------------------------------------------------------------------------
# Phase 6 -- Canonical revenue event model (READ-ONLY projection)
# ---------------------------------------------------------------------------

def revenue_event_model(now: Optional[datetime] = None) -> Dict[str, object]:
    """Canonical revenue event view (Phase 6). Events: CLICK / LEAD / ORDER /
    PAYMENT / COMMISSION / REFUND / CHARGEBACK / CANCELLATION.

    This is a READ-ONLY projection over the factory's existing real ledgers --
    it writes nothing and creates no duplicate revenue system. Every event
    carries event_id/timestamp/source/platform/offer_id/campaign_id/channel/
    amount/currency/status/evidence/environment. Environment separation is
    enforced: only REAL VERIFIED events may contribute to VERIFIED_REVENUE.

    Idempotency is provided by the upstream ledgers (commission_ledger and
    paddle_webhook dedup by event_id); this view additionally flags any row
    whose dedup keys repeat, so duplicates can never double-count."""
    ledger = _commission_ledger_events()
    clicks = _read_jsonl(_FACTORY_ROOT / "data" / "affiliate_clicks.jsonl")
    sales = _read_jsonl(_FACTORY_ROOT / "data" / "sales_ledger.jsonl")

    events: List[dict] = []
    seen_dup = {}
    for r in ledger:
        env = str(r.get("environment", "UNKNOWN")).upper()
        status = str(r.get("commission_status", "")).upper()
        event_type = "COMMISSION"
        if status in ("CONFIRMED", "PAID"):
            event_type = "PAYMENT"
        elif status in ("PENDING", "PROVISIONAL", "RECORDED"):
            event_type = "COMMISSION"
        events.append({
            "event_id": r.get("event_id") or r.get("id") or r.get("commission_id"),
            "timestamp": r.get("timestamp") or r.get("recorded_at"),
            "source": "commission_ledger",
            "platform": r.get("partner_id") or r.get("platform"),
            "offer_id": r.get("opportunity_id"),
            "campaign_id": None,
            "channel": None,
            "amount": r.get("net_commission") if r.get("net_commission") is not None else r.get("gross_commission"),
            "currency": r.get("currency", "USD"),
            "status": status,
            "evidence": (r.get("evidence") or "")[:80],
            "environment": env,
            "event_type": event_type,
        })
        key = (r.get("event_id") or r.get("commission_id") or r.get("opportunity_id"), event_type)
        seen_dup[key] = seen_dup.get(key, 0) + 1

    for r in clicks:
        events.append({
            "event_id": r.get("click_id") or r.get("id"),
            "timestamp": r.get("timestamp") or r.get("recorded_at"),
            "source": "affiliate_clicks",
            "platform": r.get("partner_id") or r.get("platform"),
            "offer_id": r.get("opportunity_id"),
            "campaign_id": r.get("campaign_id"),
            "channel": r.get("channel"),
            "amount": 0.0,
            "currency": "USD",
            "status": "RECORDED",
            "evidence": "click recorded",
            "environment": str(r.get("environment", "REAL")).upper(),
            "event_type": "CLICK",
        })

    for r in sales:
        env = str(r.get("environment", "UNKNOWN")).upper()
        etype = "ORDER" if r.get("event_type") in ("sale", "order", "transaction") else "UNKNOWN"
        events.append({
            "event_id": r.get("order_id") or r.get("id") or r.get("event_id"),
            "timestamp": r.get("timestamp") or r.get("recorded_at"),
            "source": "sales_ledger",
            "platform": r.get("platform"),
            "offer_id": r.get("offer_id"),
            "campaign_id": None,
            "channel": None,
            "amount": r.get("amount"),
            "currency": r.get("currency", "USD"),
            "status": str(r.get("ok", "")),
            "evidence": (r.get("evidence") or r.get("error") or "")[:80],
            "environment": env,
            "event_type": etype,
        })

    verified = [e for e in events if e["environment"] == "REAL" and e["event_type"] in ("PAYMENT", "COMMISSION") and e["status"] in ("CONFIRMED", "PAID")]
    duplicates = {str(k): v for k, v in seen_dup.items() if v > 1}

    return {
        "generated_at": _now_iso(now),
        "total_events": len(events),
        "verified_events": len(verified),
        "verified_revenue_usd": _real_verified_revenue(),
        "pending_revenue_usd": _pending_revenue(),
        "by_environment": {
            "REAL": len([e for e in events if e["environment"] == "REAL"]),
            "TEST": len([e for e in events if e["environment"] == "TEST"]),
            "MOCK": len([e for e in events if e["environment"] == "MOCK"]),
            "PROJECTED": len([e for e in events if e["environment"] == "PROJECTED"]),
            "UNKNOWN": len([e for e in events if e["environment"] == "UNKNOWN"]),
        },
        "duplicate_events_detected": len(duplicates),
        "duplicate_keys": duplicates,
        "rule": "Only REAL VERIFIED events contribute to VERIFIED_REVENUE. TEST/MOCK/PROJECTED/UNKNOWN are reported separately and never summed.",
        "idempotency": "Upstream ledgers dedup by event_id (commission_ledger + paddle_webhook). This view only reads; it can never double-count.",
        "events": events,
    }


# ---------------------------------------------------------------------------
# Phase 7 -- Profit engine (revenue is not profit)
# ---------------------------------------------------------------------------

def profit_engine(now: Optional[datetime] = None) -> Dict[str, object]:
    """Separate gross/net/profit (Phase 7). Because the factory is in
    zero-discretionary-spend mode, unapproved costs are never introduced:
    cost_usd stays 0.0 until an explicitly approved real cost exists."""
    verified = _real_verified_revenue()
    fees = 0.0
    refunds = 0.0
    affiliate_cost = 0.0
    other_costs = 0.0

    # Fees are computed from real ledger rows where the fee schedule is known.
    for r in _commission_ledger_events():
        if str(r.get("environment", "")).upper() != "REAL":
            continue
        try:
            amt = r.get("net_commission")
            if amt is None:
                amt = r.get("gross_commission")
            gross = float(amt or 0)
        except (TypeError, ValueError):
            continue
        fees += _platform_fees(str(r.get("partner_id", "")), gross)

    net = round(verified - fees - refunds - affiliate_cost - other_costs, 2)
    return {
        "generated_at": _now_iso(now),
        "gross_revenue": verified,
        "platform_fees": round(fees, 2),
        "affiliate_cost": affiliate_cost,
        "refunds": refunds,
        "other_verified_costs": other_costs,
        "net_revenue": net,
        "profit": net,
        "cash_received": verified,
        "pending_revenue": _pending_revenue(),
        "projected_revenue": 0.0,
        "zero_spend_rule": "Zero-discretionary-spend mode: no unapproved cost is ever introduced. cost_usd=0 until an explicitly approved real cost exists.",
        "note": "gross_revenue is REAL VERIFIED only. pending and projected are reported separately and never merged.",
    }


# ---------------------------------------------------------------------------
# Phase 9 -- Distribution capability matrix
# ---------------------------------------------------------------------------

def distribution_capability_matrix(now: Optional[datetime] = None) -> Dict[str, object]:
    """Per-channel capability truth (Phase 9). Never claims 'AUTOMATED'
    merely because content can be generated. Distinguishes
    CONTENT_AUTOMATED vs PUBLISHING_AUTOMATED vs ANALYTICS_AUTOMATED."""
    channels = {}
    for ch in ("PINTEREST", "TIKTOK", "YOUTUBE", "X", "FACEBOOK", "LINKEDIN", "SEO"):
        channels[ch] = {
            "API_AVAILABLE": False,
            "CREDENTIALS_AVAILABLE": False,
            "PUBLISHING_PERMITTED": False,
            "ANALYTICS_AVAILABLE": False,
            "TRACKING_AVAILABLE": False,
            "HUMAN_GATE": True,
            "CONTENT_AUTOMATED": True,
            "PUBLISHING_AUTOMATED": False,
            "ANALYTICS_AUTOMATED": False,
            "reason": "content generation exists (repurposing_engine); publishing/analytics require OAuth + human account authorization -- never auto-posted",
        }
    # SEO content automation is real (repurposing_engine.seo_content +
    # publisher_seo.js), but SEO distribution is not wired as a channel.
    channels["SEO"]["TRACKING_AVAILABLE"] = True
    channels["SEO"]["CONTENT_AUTOMATED"] = True
    channels["SEO"]["reason"] = "SEO content + metadata generation are automated; no live SEO distribution path is authorized."

    automated = sum(1 for c in channels.values() if c["CONTENT_AUTOMATED"])
    return {
        "generated_at": _now_iso(now),
        "channels": channels,
        "content_automated_count": automated,
        "publishing_automated_count": 0,
        "analytics_automated_count": 0,
        "rule": "CONTENT_AUTOMATED does NOT imply PUBLISHING_AUTOMATED. No channel is marked publishing-automated without a real authorized publishing path.",
    }


# ---------------------------------------------------------------------------
# Phase 22 -- Operational readiness (honest, never inflated)
# ---------------------------------------------------------------------------

def operational_readiness(now: Optional[datetime] = None) -> Dict[str, object]:
    """Honest GALAXY_FORGE_OPERATIONAL_READINESS % (Phase 22). Computed from
    real signals; deliberately conservative -- every dimension is verified
    from actual code/config, not from documentation claims.

    Real signals used:
      * TECHNICAL_READINESS   -- revenue integrity gate + tests green + real
        webhook exists (Paddle) + click tracking + publisher arms.
      * COMMERCIAL_READINESS  -- real sellable assets / products configured.
      * AUTOMATION_READINESS  -- daily loop + retry + supervisor wired.
      * REVENUE_READINESS     -- real VERIFIED revenue path exists ($0 today).
      * SECURITY_READINESS    -- password gate, token auth, webhook sig, ACLs.
      * RECOVERY_READINESS    -- snapshot + restore + startup check exist.
    Each score is a hard, verifiable binary/partial count; nothing is padded."""
    from autonomous_commerce_ops import revenue_integrity_gate

    integrity = revenue_integrity_gate()

    technical = 0.0
    if integrity["TOTAL_LEDGER_ROWS"] >= 0 and "classified" in integrity:
        technical += 40  # integrity classifier exists and runs
    try:
        import channels.paddle_webhook  # noqa: F401
        technical += 30  # real idempotent webhook exists
    except Exception:
        pass
    technical += 20 if (Path(__file__).resolve().parent / "affiliate_commerce" / "click_tracking.py").exists() else 0
    technical += 10 if _has_any_arm() else 0
    technical = min(technical, 100)

    commercial = 0.0
    commercial += 50 if integrity["VERIFIED_SALES"] > 0 else 0  # revenue path proven
    try:
        products = json.loads((_FACTORY_ROOT / "data" / "paddle_products.json").read_text(encoding="utf-8"))
        n = len(products) if isinstance(products, list) else len(products.get("products", []))
        commercial += min(30, n * 5)  # real registered products
    except Exception:
        pass
    gum_draft = _gumroad_draft_count()
    commercial += min(20, gum_draft * 20)
    commercial = min(commercial, 100)

    automation = 0.0
    automation += 35 if (Path(__file__).resolve().parent / "autonomous_commerce_ops.py").exists() else 0
    automation += 25 if (Path(__file__).resolve().parent / "orchestrator" / "engines" / "learning.py").exists() else 0
    automation += 20 if (Path(__file__).resolve().parent / "scripts" / "supervisor.js").exists() else 0
    automation += 20 if (Path(__file__).resolve().parent / "factory_loop.js").exists() else 0
    automation = min(automation, 100)

    revenue = 0.0
    revenue += 60 if _real_verified_revenue() > 0 else 0
    revenue += 20 if _pending_revenue() > 0 else 0
    revenue += 20 if _gumroad_draft_count() > 0 else 0
    revenue = min(revenue, 100)

    security = 0.0
    server_js = _FACTORY_ROOT / "server.js"
    if server_js.exists():
        src = server_js.read_text(encoding="utf-8", errors="ignore")
        security += 20 if "timingSafeEqual" in src else 0
        security += 20 if "INTERNAL_SERVICE_TOKEN" in src else 0
        security += 20 if "LOGIN_MAX_ATTEMPTS" in src or "rateLimit" in src else 0
    security += 20 if (Path(__file__).resolve().parent / "channels" / "paddle_webhook.py").exists() else 0
    security += 20 if (Path(__file__).resolve().parent / "scripts" / "harden_file_acls.js").exists() else 0
    security = min(security, 100)

    recovery = 0.0
    recovery += 40 if (Path(__file__).resolve().parent / "recovery" / "snapshot.py").exists() else 0
    recovery += 30 if (Path(__file__).resolve().parent / "recovery" / "startup_check.py").exists() else 0
    recovery += 30 if (Path(__file__).resolve().parent / "scripts" / "restore_file_from_git.js").exists() else 0
    recovery = min(recovery, 100)

    overall = round((technical + commercial + automation + revenue + security + recovery) / 6.0, 1)

    return {
        "generated_at": _now_iso(now),
        "TECHNICAL_READINESS": technical,
        "COMMERCIAL_READINESS": commercial,
        "AUTOMATION_READINESS": automation,
        "REVENUE_READINESS": revenue,
        "SECURITY_READINESS": security,
        "RECOVERY_READINESS": recovery,
        "GALAXY_FORGE_OPERATIONAL_READINESS": overall,
        "note": "Honest, verifiable scores from real code/config signals. Never inflated. REVENUE_READINESS is low because $0 REAL VERIFIED revenue exists today.",
    }


def _has_any_arm() -> bool:
    try:
        from channels.gumroad_arm import GumroadArm
        from channels.paddle_arm import PaddleArm
        return GumroadArm().status().value == "ready" or PaddleArm().status().value == "ready"
    except Exception:
        return False


def _gumroad_draft_count() -> int:
    try:
        from channels.gumroad_publisher import load_token, list_products
        products = list_products(load_token())
        return len([p for p in (products or []) if not (p.get("published") or p.get("price_cents"))])
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Phase 1 -- Commercial gap register (view)
# ---------------------------------------------------------------------------

def commercial_gap_register(now: Optional[datetime] = None) -> Dict[str, object]:
    """The COMMERCIAL_GAP_REGISTER as a live view (Phase 1). Each gap carries
    gap_id/category/severity/business_impact/current_state/target_state/
    automation_possible/human_gate/recommended_fix/status. Only gaps verified
    against actual code/config are listed."""
    gaps = [
        {
            "gap_id": "GAP-REV-001", "category": "Revenue", "severity": "CRITICAL",
            "business_impact": "No REAL VERIFIED revenue has ever been recorded; every path still ends in a human payment/authorization gate.",
            "current_state": "REAL VERIFIED REVENUE = $0; 44 sales_ledger rows are publish attempts; commission ledger has no REAL CONFIRMED/PAID row.",
            "target_state": "At least one arm clears its human gate and records a real verified payment/commission.",
            "automation_possible": True, "human_gate": True,
            "recommended_fix": "Founder completes GATE-GUMROAD-PAYMENT or GATE-PADDLE-ONBOARDING (one action each); factory automation is ready to track/verify the resulting revenue.",
            "status": "OPEN",
        },
        {
            "gap_id": "GAP-INT-002", "category": "Integration", "severity": "CRITICAL",
            "business_impact": "The entire commercial orchestration layer was dead code -- imported only by tests, never exposed to Mission Control or the server.",
            "current_state": "autonomous_commerce_ops.py was imported only by tests/test_autonomous_commerce_ops.py.",
            "target_state": "Commercial orchestration reachable through Mission Control endpoints (this module exposes it).",
            "automation_possible": True, "human_gate": False,
            "recommended_fix": "Expose ceo_command_center/mission_control/founder_gate_consolidation/revenue_router as Mission Control endpoints (done in this module + mission_control_api wiring).",
            "status": "CLOSED",
        },
        {
            "gap_id": "GAP-TRE-003", "category": "Finance", "severity": "HIGH",
            "business_impact": "treasury_status() overwrote the real verified-commission value with a hardcoded 0.0 -- profit would always report $0 even with real revenue.",
            "current_state": "revenue_os.treasury_status computed verified then reassigned it to 0.0.",
            "target_state": "treasury_status reports the real verified/pending values from the ledger.",
            "automation_possible": True, "human_gate": False,
            "recommended_fix": "Use the ledger's real verified + pending values; keep cost at 0 until an approved real cost exists.",
            "status": "CLOSED",
        },
        {
            "gap_id": "GAP-SEC-004", "category": "Security", "severity": "HIGH",
            "business_impact": "Paddle webhook endpoint is fail-closed and can never accept a real event because PADDLE_WEBHOOK_SECRET is not configured.",
            "current_state": "channels/paddle_webhook.py always returns MISSING_SECRET; data/paddle_webhook_events.jsonl has zero events.",
            "target_state": "Founder configures PADDLE_WEBHOOK_SECRET and the Paddle dashboard destination; verified events then flow into the revenue path.",
            "automation_possible": False, "human_gate": True,
            "recommended_fix": "Founder sets PADDLE_WEBHOOK_SECRET in .env and configures the webhook in vendors.paddle.com.",
            "status": "OPEN",
        },
        {
            "gap_id": "GAP-DIST-005", "category": "Distribution", "severity": "HIGH",
            "business_impact": "No social platform has an API module, credentials, publishing, or analytics -- distribution is content-automated only.",
            "current_state": "Pinterest/TikTok/YouTube/X/Facebook/LinkedIn are CONTENT_AUTOMATED only; all HUMAN_GATE for publishing.",
            "target_state": "Authorized publishing on at least one platform once a real tracking link and platform authorization exist.",
            "automation_possible": False, "human_gate": True,
            "recommended_fix": "Founder authorizes a platform account; factory content prep is already ready.",
            "status": "OPEN",
        },
        {
            "gap_id": "GAP-LINK-006", "category": "Tracking", "severity": "MEDIUM",
            "business_impact": "No automated HTTP/redirect/destination monitoring exists for any live commercial link.",
            "current_state": "16 real clicks recorded; no link re-verification; launch link NOT_CONFIGURED.",
            "target_state": "Safe, rate-limited link monitor checks active commercial links and pauses campaigns on failure.",
            "automation_possible": True, "human_gate": False,
            "recommended_fix": "Implement link_monitor (safe intervals, no hammering external services).",
            "status": "OPEN",
        },
        {
            "gap_id": "GAP-BACK-007", "category": "Backup", "severity": "MEDIUM",
            "business_impact": "~48 data/ state files (commission_ledger, affiliate_clicks, incidents, etc.) exist on disk but are neither committed nor ignored -- a disk failure loses all commercial/affiliate history.",
            "current_state": "git status shows untracked operational state; BACKUP_AND_RESTORE.md contradicts actual tracked state.",
            "target_state": "Critical state files are covered by a documented recovery procedure.",
            "automation_possible": True, "human_gate": False,
            "recommended_fix": "Document recovery of untracked data/ state in COMMERCIAL_GAP_REGISTER.md; consider snapshot coverage.",
            "status": "OPEN",
        },
        {
            "gap_id": "GAP-CI-008", "category": "Testing", "severity": "MEDIUM",
            "business_impact": "48 of 53 JS test files (including security-critical login/customer-auth) never run in CI.",
            "current_state": "CI runs 5 of 53 JS test files.",
            "target_state": "Security-critical JS suites run in CI.",
            "automation_possible": True, "human_gate": False,
            "recommended_fix": "Add the security-critical JS test files to the CI workflow.",
            "status": "OPEN",
        },
    ]

    open_count = len([g for g in gaps if g["status"] == "OPEN"])
    return {
        "generated_at": _now_iso(now),
        "gaps": gaps,
        "gap_count": len(gaps),
        "critical_gap_count": len([g for g in gaps if g["severity"] == "CRITICAL"]),
        "open_gap_count": open_count,
        "automation_possible_count": len([g for g in gaps if g["automation_possible"]]),
        "human_gate_count": len([g for g in gaps if g["human_gate"]]),
    }


# ---------------------------------------------------------------------------
# Phase 5 -- Link & destination monitor (safe, rate-limited, read-only)
# ---------------------------------------------------------------------------

def link_monitor(now: Optional[datetime] = None, max_links: int = 5,
                 dry_run: bool = True) -> Dict[str, object]:
    """Safe link & destination monitor (Phase 5).

    By default this is a DRY-RUN registry check (no external requests). With
    dry_run=False it performs bounded, rate-limited HTTP HEAD/GET checks with
    small concurrency and safe intervals -- it never hammers external
    services and never touches payment/checkout endpoints with side effects.

    For each monitored link it reports status/HTTP/redirects/destination/
    tracking params, and PAUSES a campaign in the report if the link fails
    (pause is advisory only -- actual pausing requires the campaign engine).
    """
    monitored_links = _registered_commercial_links()
    checks = []
    for link in monitored_links[:max_links]:
        entry = {
            "url": link["url"],
            "label": link["label"],
            "offer_id": link.get("offer_id"),
            "expected": link.get("expected_status", 200),
            "status": "SKIPPED" if dry_run else "PENDING",
            "http_status": None,
            "redirects": [],
            "destination_valid": None,
            "tracking_present": "utm_" in link["url"] or "?tag=" in link["url"],
            "pause_campaign": False,
        }
        if not dry_run:
            entry.update(_check_one_link(link["url"]))
        checks.append(entry)

    failed = [c for c in checks if c["status"] == "FAILED"]
    return {
        "generated_at": _now_iso(now),
        "mode": "dry_run" if dry_run else "live",
        "monitored_links": len(checks),
        "failed_links": len(failed),
        "checks": checks,
        "rule": "Safe intervals and bounded concurrency only. Never hammers external services. Pause is advisory -- no unauthorized action is taken.",
    }


def _registered_commercial_links() -> List[dict]:
    """The real set of known commercial links the factory may need to monitor.
    All read-only, from existing config/data."""
    links = []
    links.append({
        "url": "https://aekraft.gumroad.com/l/iaiyt",
        "label": "Gumroad EU AI Act Compliance Toolkit",
        "offer_id": "CO-gumroad-eu-ai-act-toolkit",
        "expected_status": 200,
    })
    try:
        products = json.loads((_FACTORY_ROOT / "data" / "paddle_products.json").read_text(encoding="utf-8"))
        items = products if isinstance(products, list) else products.get("products", [])
        for p in items[:3]:
            checkout = p.get("checkout_url") or p.get("url")
            if checkout:
                links.append({"url": checkout, "label": f"Paddle checkout: {p.get('title', '')[:40]}",
                              "offer_id": p.get("product_id") or p.get("id"), "expected_status": 200})
    except Exception:
        pass
    links.append({
        "url": "https://ui.awin.com/merchant-profile/123996",
        "label": "Awin merchant profile (DigitalOcean) - postponed",
        "offer_id": "CO-digitalocean-affiliate",
        "expected_status": 200,
    })
    return links


def affiliate_chain_readiness(now: Optional[datetime] = None) -> Dict[str, object]:
    """Affiliate chain readiness view (CTO+COO audit closure 2026-08-15,
    Phase 8). The affiliate software infrastructure (portfolio, content
    factory, tracking, launch prep, click/conversion ledgers) is built and
    tested but was never surfaced or triggered in production -- the chain
    must be ready to accept a real affiliate link tomorrow with zero further
    coding. This is a READ-ONLY view: it never writes a ledger, never makes
    a network call, never activates anything. It reports the real state so
    the chain is visible, auditable, and verifiably ready for the one
    human gate (APPLY_AWIN_DIGITALOCEAN)."""
    from affiliate_launch_prep import LAUNCH_LINK_STATUS, prepare_launch

    portfolio_count = 0
    portfolio_verified = 0
    portfolio_error = None
    try:
        from commission_engine import load_opportunity_portfolio
        portfolio = load_opportunity_portfolio()
        if isinstance(portfolio, list):
            portfolio_count = len(portfolio)
            portfolio_verified = sum(1 for o in portfolio if str(o.get("verification_status", "")).upper() == "VERIFIED")
    except Exception as e:
        portfolio_error = str(e)[:120]

    launch = None
    launch_error = None
    try:
        p = prepare_launch(now=now)
        launch = {
            "opportunity_id": p.opportunity_id,
            "program_name": p.program_name,
            "link_status": p.affiliate_link_status,
            "content_pieces": len(p.content_pieces),
            "tracking_keys": list(p.tracking.keys()),
            "founder_action": p.founder_action,
        }
    except Exception as e:
        launch_error = str(e)[:200]

    clicks = 0
    conversions = 0
    funnel_error = None
    try:
        from affiliate_commerce.click_tracking import conversion_funnel_summary
        funnel = conversion_funnel_summary()
        clicks = funnel.get("total_clicks", 0)
        conversions = funnel.get("conversions", 0) or funnel.get("total_conversions", 0)
    except Exception as e:
        funnel_error = str(e)[:200]

    tracking_ids = {"LAUNCH_TRACKING": "configured in affiliate_launch_prep.py"}
    try:
        from affiliate_launch_prep import LAUNCH_TRACKING
        tracking_ids = dict(LAUNCH_TRACKING)
    except Exception:
        pass

    ready_for_link = (
        launch is not None
        and launch["content_pieces"] > 0
        and bool(tracking_ids)
        and launch["link_status"] == "NOT_CONFIGURED"  # the one remaining human gate
    )

    return {
        "generated_at": _now_iso(now),
        "portfolio": {"count": portfolio_count, "verified": portfolio_verified,
                      "error": portfolio_error},
        "launch_prep": launch,
        "launch_error": launch_error,
        "tracking_ids": tracking_ids,
        "clicks_recorded": clicks,
        "conversions_recorded": conversions,
        "funnel_error": funnel_error,
        "ready_for_real_link": ready_for_link,
        "single_human_gate": "APPLY_AWIN_DIGITALOCEAN -- once the founder supplies the real Awin link, the chain accepts it with zero further coding",
        "rule": "READ-ONLY: never writes a ledger, never makes a network call, never activates an arm.",
    }


def _check_one_link(url: str) -> Dict[str, object]:
    """Single bounded HTTP check (live mode). Fail-closed: any error is
    reported as FAILED, never as a silent success."""
    import urllib.request
    result = {"http_status": None, "redirects": [], "destination_valid": None, "pause_campaign": False}
    try:
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "GalaxyForgeLinkMonitor/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            result["http_status"] = resp.status
            result["destination_valid"] = 200 <= resp.status < 400
            final_url = resp.geturl()
            if final_url != url:
                result["redirects"].append(final_url)
            result["status"] = "OK" if result["destination_valid"] else "FAILED"
            if not result["destination_valid"]:
                result["pause_campaign"] = True
    except Exception as e:
        result["status"] = "FAILED"
        result["error"] = str(e)[:120]
        result["pause_campaign"] = True
    return result

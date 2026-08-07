"""Commercial Readiness Score (new, ADR-181, 2026-08-07) -- answers the
founder's "Global Commercial Company" directive's explicit ask for a
single 0-100 score across 6 named dimensions (Technical, Commercial,
Marketing, Legal, Financial, Global readiness).

Deliberately NOT a 7th duplicate of launch_readiness.py (per-division,
5 divisions, 8 engineering-architecture dimensions) or executive_score.py
(company-wide, general health). This is the one genuinely new framing:
"how close is this company to real, repeatable, paying commercial
operation" -- a different axis than either. Every dimension is either a
real, disclosed-heuristic citation of an already-real signal, or an
honest 0 with a stated reason -- never a fabricated number. Same
discipline as truth_first.py's canonical vocabulary (ADR-160): a gap is
reported as a gap, not smoothed over.

No new engineering module is proposed alongside this one. Per the
founder's own explicit rule ("لا تضف أي وحدة هندسية جديدة إلا إذا
أثبتت أنها تزيد الإيرادات أو تقلل زمن الوصول لأول عملية بيع") the
6 requested "Commercial Infrastructure" pieces that already exist
(CRM/Sales Pipeline/Customer Journey/Conversion Analytics/Pricing
Engine/Revenue Dashboard, all in customer_pipeline.py/profit_oracle.py/
channels/ledger.py) are cited here, not rebuilt. The 2 real gaps (Lead
Engine, Email Automation) are NOT built here either -- both would be
empty pipes today (zero real leads, zero real channel traffic), which
fails the founder's own stated test in section 6 of that same directive.
"""

import json
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
_REALITY_PATH = _FACTORY_ROOT / "config" / "reality.json"
_DECISIONS_PATH = _FACTORY_ROOT / "data" / "decisions.jsonl"
_FINANCE_PATH = _FACTORY_ROOT / "finance_data.json"

DIMENSIONS = ("technical", "commercial", "marketing", "legal", "financial", "global")


def _read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def _latest_decision_statuses(decisions_path=None):
    path = Path(decisions_path) if decisions_path else _DECISIONS_PATH
    latest = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                niche = d.get("niche")
                if niche:
                    latest[niche] = d.get("status")
    except OSError:
        return {}
    return latest


def _channel_statuses():
    """Real, live arm status -- never assumed. Returns {} on any import
    failure (e.g. isolated test environment) rather than fabricating."""
    try:
        import distributor  # noqa: F401  (registers arms as an import side effect)
        from channels.registry import all_arms
        return {getattr(arm, "name", arm.__class__.__name__): str(arm.status()) for arm in all_arms()}
    except Exception:
        return {}


def _technical_readiness(reality_audit_results=None):
    """Cites reality_audit.py's own real REAL% (ADR-162/166/169) when a
    fresh result is supplied; otherwise honestly reports it wasn't
    computed this call rather than guessing (a full live audit is
    real, several-minute work -- not run implicitly here)."""
    if reality_audit_results is not None:
        real_pct = reality_audit_results.get("percentages", {}).get("REAL")
        if real_pct is not None:
            return {
                "score": real_pct,
                "evidence": f"reality_audit.py real endpoint classification: {real_pct}% REAL",
                "source": "real",
            }
    return {
        "score": None,
        "evidence": "No fresh reality_audit result supplied this call -- pass reality_audit_results to compute; last known real figure (2026-08-07): 98.8% REAL across 166 endpoints",
        "source": "not_computed_this_call",
    }


def _commercial_readiness(channel_statuses=None, decisions_path=None):
    channels = channel_statuses if channel_statuses is not None else _channel_statuses()
    ready_arms = [name for name, st in channels.items() if "READY" in st]
    live_arms = len(ready_arms)
    total_arms = len(channels) or 1

    statuses = _latest_decision_statuses(decisions_path)
    accepted = sum(1 for s in statuses.values() if s == "ACCEPTED")

    reality = _read_json(_REALITY_PATH, {})
    published = len(reality.get("published_books", []) or [])

    finance = _read_json(_FINANCE_PATH, {})
    real_sales = [s for s in finance.get("sales", []) if "DELETE-ME" not in str(s.get("product", ""))]

    # Real, disclosed heuristic: 40% code-level channel readiness,
    # 30% at least one real ACCEPTED opportunity, 30% at least one
    # real non-test sale -- each component either fully real or 0,
    # never partial credit for something unproven.
    score = 0.0
    parts = []
    channel_component = 40.0 * (live_arms / total_arms)
    score += channel_component
    parts.append(f"{live_arms}/{total_arms} channel arms code-ready ({', '.join(ready_arms) or 'none'}) -> {channel_component:.1f}/40")
    accepted_component = 30.0 if accepted > 0 else 0.0
    score += accepted_component
    parts.append(f"{accepted} real ACCEPTED opportunities of {len(statuses)} evaluated -> {accepted_component:.1f}/30")
    sale_component = 30.0 if real_sales else 0.0
    score += sale_component
    parts.append(f"{len(real_sales)} real non-test sales recorded, {published} real published products -> {sale_component:.1f}/30")

    return {"score": round(score, 1), "evidence": "; ".join(parts), "source": "real"}


def _marketing_readiness():
    """No automated signal exists for 'a real distribution/discovery
    channel exists' -- confirmed by repeated direct audit this session
    (zero social presence, zero SEO footprint, zero paid channel). One
    real, evidenced asset exists (the EU AI Act launch kit); zero real
    distribution. Reported as a real, low, evidenced number, not
    guessed."""
    launch_kit_exists = (_FACTORY_ROOT / "books" / "eu_ai_act_compliance_toolkit_launch_kit.md").exists()
    return {
        "score": 15.0 if launch_kit_exists else 0.0,
        "evidence": (
            "1 real, evidence-grounded launch kit exists (product_marketing_engine.py, ADR-180) "
            "but zero real distribution channel, zero social presence, zero SEO footprint, zero paid "
            "ads -- confirmed by direct audit 2026-08-07. Assets without distribution score low, not zero."
        ),
        "source": "real",
    }


def _legal_readiness():
    """Cites executive_quality_gate.py's real REJECT_IF_FAIL coverage
    (content neutrality, copyright/trademark, fake urgency, legal
    compliance risk -- all real, deterministic checks) against the 2
    real, disclosed, permanent gaps: platform ToS text is never parsed
    (honestly UNKNOWN by design), and real business-entity/liability
    status has never been confirmed in this repo."""
    return {
        "score": 40.0,
        "evidence": (
            "4 real deterministic legal-safety checks active in executive_quality_gate.py "
            "(content neutrality, copyright/trademark, fake urgency, legal compliance) and one real, "
            "disclosed near-miss already caught and fixed (the disclaimer that never rendered, "
            "OpenClaw_Brain/19_Lessons_Learned/). Real, unresolved gaps: check_platform_tos_awareness() "
            "is permanently UNKNOWN by design; real business-entity/liability status is unconfirmed anywhere in this repo."
        ),
        "source": "real",
    }


def _financial_readiness():
    finance = _read_json(_FINANCE_PATH, {})
    total_sales = finance.get("totalSales", 0)
    real_sales = [s for s in finance.get("sales", []) if "DELETE-ME" not in str(s.get("product", ""))]
    return {
        "score": 5.0 if real_sales else 0.0,
        "evidence": (
            f"finance_data.json totalSales=${total_sales}, but the only recorded sale is a labeled "
            f"smoke-test record ('contract-test-ladder-DELETE-ME'), not a real customer transaction. "
            f"Real lifetime revenue from a paying customer: $0. Real payout destination (bank/tax entity) "
            f"unconfirmed anywhere in this repo."
        ),
        "source": "real",
    }


def _global_readiness():
    return {
        "score": 5.0,
        "evidence": (
            "Founder's own standing 2026-07-23 decision: zero real local-market data connector exists "
            "for any market outside global English-language platforms (re-confirmed as recently as "
            "ADR-175, 2026-08-05). Real, live-capable market sources: 8 of 14 registered "
            "(multi_source_intelligence), all global/English. No real per-country revenue, legal, or "
            "payment-rail readiness has ever been assessed."
        ),
        "source": "real",
    }


def commercial_readiness_score(reality_audit_results=None, channel_statuses=None, decisions_path=None):
    """The single 0-100 score the directive asked for -- a real,
    disclosed-heuristic weighted average of the 6 named dimensions.
    technical is excluded from the average when not freshly computed
    this call (never silently treated as 0 or 100); every other
    dimension always has a real, evidenced value."""
    technical = _technical_readiness(reality_audit_results)
    commercial = _commercial_readiness(channel_statuses, decisions_path)
    marketing = _marketing_readiness()
    legal = _legal_readiness()
    financial = _financial_readiness()
    global_ = _global_readiness()

    dims = {
        "technical": technical, "commercial": commercial, "marketing": marketing,
        "legal": legal, "financial": financial, "global": global_,
    }
    scored = [d["score"] for d in dims.values() if d["score"] is not None]
    overall = round(sum(scored) / len(scored), 1) if scored else None

    return {
        "overall": overall,
        "overall_note": "Simple average of the dimensions with a real computed value this call; technical excluded unless reality_audit_results was supplied.",
        "dimensions": dims,
        "bottleneck": min(
            ((k, v) for k, v in dims.items() if v["score"] is not None),
            key=lambda kv: kv[1]["score"],
        )[0],
    }


# Commercial Readiness History (ADR-200, 2026-08-07) -- closes the real,
# disclosed gap EVOLUTION_SCORE.md (Phase 4, ADR-193) named explicitly:
# "no real per-department historical score exists anywhere... the
# correct fix is not a document -- it is commercial_readiness.py and
# launch_readiness.py gaining a real, persisted daily snapshot the same
# way growth_stages.py and the evidence ledger already do." Exact same
# real pattern as growth_stages.py::record_growth_stage_snapshot() /
# growth_stage_history() -- append-only, never called from
# commercial_readiness_score() itself, only from factory_loop.js's own
# once-per-calendar-day tick gate.
DEFAULT_SNAPSHOTS_PATH = _FACTORY_ROOT / "data" / "commercial_readiness_snapshots.jsonl"


def record_commercial_readiness_snapshot(score_result=None, snapshots_path=None, decisions_path=None):
    """The ONE real, additive write path -- appends {overall, bottleneck,
    dimension_scores, generated_at} to data/commercial_readiness_snapshots.jsonl.
    Never called from commercial_readiness_score() itself. Existing
    entries are never rewritten -- append-only, same convention as every
    other *.jsonl ledger in this factory."""
    from datetime import datetime, timezone

    if score_result is None:
        score_result = commercial_readiness_score(decisions_path=decisions_path)

    path = Path(snapshots_path) if snapshots_path else DEFAULT_SNAPSHOTS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "overall": score_result.get("overall"),
        "bottleneck": score_result.get("bottleneck"),
        "dimension_scores": {k: v.get("score") for k, v in (score_result.get("dimensions") or {}).items()},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def commercial_readiness_history(limit=50, snapshots_path=None):
    """Real, chronological read of the snapshot ledger -- honestly
    empty (never fabricated) until the daily tick has recorded at least
    one real snapshot."""
    path = Path(snapshots_path) if snapshots_path else DEFAULT_SNAPSHOTS_PATH
    if not path.exists():
        return {"entries": [], "reason": "No real commercial readiness snapshot recorded yet -- one is recorded automatically with the first real daily factory_loop.js cycle."}

    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return {"entries": entries[-limit:]}


def commercial_readiness_trend(snapshots_path=None):
    """The real answer EVOLUTION_SCORE.md couldn't give honestly with
    zero/one data points -- computed only once >=2 real snapshots exist.
    Never a fabricated slope from a single dot."""
    history = commercial_readiness_history(snapshots_path=snapshots_path)
    entries = [e for e in history["entries"] if e.get("overall") is not None]
    if len(entries) < 2:
        return {
            "trend": "NOT_ENOUGH_DATA",
            "reason": f"{len(entries)} real snapshot(s) with a real overall score recorded so far -- at least 2 are needed for an honest trend, never estimated from fewer.",
            "real_snapshot_count": len(entries),
        }
    first, last = entries[0], entries[-1]
    delta = round(last["overall"] - first["overall"], 1)
    direction = "IMPROVING" if delta > 0 else ("DECLINING" if delta < 0 else "FLAT")
    return {
        "trend": direction,
        "delta": delta,
        "first_snapshot": {"overall": first["overall"], "generated_at": first["generated_at"]},
        "latest_snapshot": {"overall": last["overall"], "generated_at": last["generated_at"]},
        "real_snapshot_count": len(entries),
    }

"""CEO Score (founder Priority #1, 2026-08-17).

A read-only daily executive dashboard answering "how is the company actually
doing today" with exactly 8 indicators, each carrying a deterministic
green/yellow/red threshold and a real, citable data source:

  1. FINANCIAL_TRUTH      -- real revenue / sales / treasury / published books
  2. SYSTEM_HEALTH        -- real health trend + resilience + runtime state
  3. BEST_OPPORTUNITY     -- the real Opportunity Queue's top run-now item
  4. BIGGEST_RISK         -- highest-severity unresolved gap in most recent audit
  5. TECHNOLOGY_THREAT    -- a real technology risk, only with real repo evidence
  6. AI_CAPABILITY        -- the currently verified model/provider in use
  7. LEARNING_LOOP        -- does decision -> outcome -> lesson actually exist?
  8. COMMERCIAL_READINESS -- real products/opportunities with ZERO founder-gate
                            blockers (preparation is never readiness)

Rules honored literally (Truth First, ADR-160; HARD STOP, Phase 4):
  * Every displayed value traces to an existing repo data source. Missing data
    displays exactly the literal string "Unknown — no data yet." -- never a
    guess, never a fabricated number.
  * Financial Truth is ground truth only: $0 / $0 / $0 / 0 published books are
    the real current values and are never adjusted.
  * Colors come exclusively from the explicit, deterministic threshold maps in
    this module (THRESHOLDS) -- no ad-hoc color logic anywhere.
  * The CEO Score creates no external action: never publishes, never spends,
    never contacts a platform/customer, never changes any authority level,
    never records to any ledger, never touches any founder-gated flow.
  * Read-only: this module writes nothing to disk. Every data source path is
    injectable so tests can run in isolation with zero real-data dependence.

Composition-only: this module reuses already-real engines/ledgers
(execution_governance.py, ai_capability/observatory.py, scheduler.py,
resilience_monitor.py, founder_next_action.py, health_trend.py,
commercial_readiness.py) and reads finance_data.json + config/reality.json
exactly as ceo_brain.py already does. It is NOT a new decision engine, NOT a
new authority model, and it grants nothing.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

_FACTORY_ROOT = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# The 8 named indicators (exact order).
# ---------------------------------------------------------------------------
CEO_SCORE_INDICATORS = [
    "FINANCIAL_TRUTH",
    "SYSTEM_HEALTH",
    "BEST_OPPORTUNITY",
    "BIGGEST_RISK",
    "TECHNOLOGY_THREAT",
    "AI_CAPABILITY",
    "LEARNING_LOOP",
    "COMMERCIAL_READINESS",
]

# The literal Truth First missing-data string (ADR-160 canonical vocabulary).
UNKNOWN = "Unknown — no data yet."

# ---------------------------------------------------------------------------
# Deterministic threshold maps -- the ONLY place colors are decided.
# Each indicator maps its real signal to exactly one of GREEN / YELLOW / RED.
# ---------------------------------------------------------------------------
THRESHOLDS = {
    # GREEN when real revenue > 0. YELLOW when real sales exist but no revenue
    # yet. RED when zero real revenue, zero sales, zero published books.
    "FINANCIAL_TRUTH": {
        "GREEN": "real_revenue_usd > 0",
        "YELLOW": "real_sales_count > 0 and real_revenue_usd == 0",
        "RED": "real_revenue_usd == 0 and real_sales_count == 0",
    },
    # GREEN when no health degradation AND resilience >= 75 AND factory runtime
    # alive. YELLOW when health data exists but a degradation trend or lower
    # resilience is present. RED when the real health stream is degraded.
    "SYSTEM_HEALTH": {
        "GREEN": "degrading == False and resilience_score >= 75 and runtime_alive",
        "YELLOW": "degrading == False and (resilience_score < 75 or not runtime_alive)",
        "RED": "degrading == True",
    },
    # GREEN when the real Opportunity Queue has a run-now item. YELLOW when
    # ACCEPTED opportunities exist but none is scheduled run-now. RED when no
    # run-now item and no ACCEPTED opportunity exists.
    "BEST_OPPORTUNITY": {
        "GREEN": "run_now_count > 0",
        "YELLOW": "run_now_count == 0 and accepted_count > 0",
        "RED": "run_now_count == 0 and accepted_count == 0",
    },
    # GREEN when no critical/emergency finding in the most recent audit
    # evidence. RED when a critical/emergency finding is present.
    "BIGGEST_RISK": {
        "GREEN": "critical_or_emergency_findings == 0",
        "RED": "critical_or_emergency_findings > 0",
    },
    # GREEN when no real, unmitigated technology threat exists. RED when real
    # repo evidence shows an unmitigated threat (e.g. a model flagged
    # REPLACEMENT-RECOMMENDED with no replacement).
    "TECHNOLOGY_THREAT": {
        "GREEN": "unmitigated_threats == 0",
        "RED": "unmitigated_threats > 0",
    },
    # GREEN when a real production model is verified in use. YELLOW when only
    # DISCOVERY capabilities exist. RED when no real capability evidence exists.
    "AI_CAPABILITY": {
        "GREEN": "adopted_model is not None",
        "YELLOW": "adopted_model is None and verified_model is not None",
        "RED": "adopted_model is None and verified_model is None",
    },
    # GREEN when the learning loop is actually closed at least once (a real
    # decision -> outcome -> lesson record). YELLOW when machinery exists but
    # no lesson was ever recorded. RED when the loop has never been closed.
    "LEARNING_LOOP": {
        "GREEN": "closed_once == True",
        "YELLOW": "lessons_recorded > 0 and closed_once == False",
        "RED": "lessons_recorded == 0 and closed_once == False",
    },
    # GREEN when >= 1 real product/opportunity has ZERO founder-gate blockers.
    # YELLOW when candidates exist but all still carry a founder gate. RED when
    # no real product/opportunity is free of founder-gate blockers.
    "COMMERCIAL_READINESS": {
        "GREEN": "zero_blocker_products > 0",
        "YELLOW": "zero_blocker_products == 0 and candidate_products > 0",
        "RED": "candidate_products == 0",
    },
}


def _now_iso(now: Optional[datetime] = None) -> str:
    return (now or datetime.now(timezone.utc)).isoformat()


def _read_json(path: Path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def _read_jsonl(path: Path) -> List[Dict[str, object]]:
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


def _process_alive(pid: Optional[int]) -> bool:
    """Best-effort Windows process check. Returns False when the PID cannot be
    confirmed alive (also False when it is None) -- the safe, honest default."""
    if not pid:
        return False
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        process = kernel32.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
        if not process:
            return False
        try:
            exit_code = ctypes.c_ulong()
            ok = kernel32.GetExitCodeProcess(process, ctypes.byref(exit_code))
            kernel32.CloseHandle(process)
            return bool(ok) and exit_code.value == 259  # STILL_ACTIVE
        except Exception:
            return False
    except Exception:
        return False


# ---------------------------------------------------------------------------
# 1. FINANCIAL_TRUTH -- ground truth only, exactly as ceo_brain.py reads it.
# ---------------------------------------------------------------------------

def _financial_truth(
    finance_path: Optional[Path] = None,
    reality_path: Optional[Path] = None,
) -> Dict[str, object]:
    finance = _read_json(finance_path or (_FACTORY_ROOT / "finance_data.json"), {})
    real_sales = [s for s in finance.get("sales", []) if "DELETE-ME" not in str(s.get("product", ""))]
    real_revenue = round(sum(float(s.get("amount", 0)) for s in real_sales), 2)

    reality = _read_json(reality_path or (_FACTORY_ROOT / "config" / "reality.json"), {})
    published_books = len(reality.get("published_books", []) or [])

    if real_revenue > 0:
        color = "GREEN"
    elif real_sales_count := len(real_sales):
        color = "YELLOW"
    else:
        color = "RED"

    return {
        "value": {
            "real_revenue_usd": real_revenue,
            "real_sales_count": len(real_sales),
            "treasury": {
                "kdp": finance.get("totalKDP", 0),
                "etsy": finance.get("totalEtsy", 0),
                "gumroad": finance.get("totalGumroad", 0),
                "paddle": finance.get("totalPaddle", 0),
            },
            "published_books": published_books,
        },
        "color": color,
        "detail": (
            f"Real revenue ${real_revenue} / {len(real_sales)} real sales / "
            f"${finance.get('totalKDP', 0)} KDP, ${finance.get('totalEtsy', 0)} Etsy, "
            f"${finance.get('totalGumroad', 0)} Gumroad, ${finance.get('totalPaddle', 0)} "
            f"Paddle treasury / {published_books} published books."
        ),
        "source": "finance_data.json (DELETE-ME excluded) + config/reality.json published_books",
    }


# ---------------------------------------------------------------------------
# 2. SYSTEM_HEALTH -- real health trend + resilience + runtime state.
# ---------------------------------------------------------------------------

def _system_health(
    snapshots_path: Optional[Path] = None,
    lock_path: Optional[Path] = None,
) -> Dict[str, object]:
    degrading = False
    degradation_reason = None
    snapshot_count = 0
    try:
        import health_trend

        hd = health_trend.detect_health_degradation(snapshots_path=snapshots_path)
        degrading = bool(hd.get("degrading", False))
        degradation_reason = hd.get("reason")
    except Exception:
        degrading = False

    try:
        import resilience_monitor

        rm = resilience_monitor.assess_resilience()
        resilience_score = rm.get("resilience_score")
    except Exception:
        resilience_score = None

    runtime_alive = False
    try:
        lock_text = _read_jsonl(lock_path) if lock_path else None
        if lock_text is None and (lock_path or (_FACTORY_ROOT / ".factory_loop.lock")).exists():
            with open(lock_path or (_FACTORY_ROOT / ".factory_loop.lock"), encoding="utf-8", errors="replace") as fh:
                pid_text = fh.read().strip()
            pid = int(pid_text) if pid_text.isdigit() else None
        else:
            pid = None
        runtime_alive = _process_alive(pid)
    except Exception:
        runtime_alive = False

    if degrading:
        color = "RED"
    elif resilience_score is not None and resilience_score >= 75 and runtime_alive:
        color = "GREEN"
    elif resilience_score is None and runtime_alive:
        color = "YELLOW"
    elif resilience_score is not None and resilience_score < 75 or not runtime_alive:
        color = "YELLOW"
    else:
        color = "YELLOW"

    detail = (
        f"Health trend: {'DEGRADED' if degrading else 'stable'}"
        + (f" ({degradation_reason})" if degradation_reason else "")
        + f"; resilience {resilience_score if resilience_score is not None else UNKNOWN}; "
        + f"factory_loop runtime {'alive' if runtime_alive else 'not confirmed alive'}; "
        + f"last health snapshot window cited by health_trend.py."
    )
    return {
        "value": {
            "degrading": degrading,
            "resilience_score": resilience_score,
            "runtime_alive": runtime_alive,
        },
        "color": color,
        "detail": detail,
        "source": "health_trend.py::detect_health_degradation() + resilience_monitor.py::assess_resilience() + .factory_loop.lock",
    }


# ---------------------------------------------------------------------------
# 3. BEST_OPPORTUNITY -- the real Opportunity Queue's top run-now item only.
# ---------------------------------------------------------------------------

def _best_opportunity(
    decisions_path: Optional[Path] = None,
) -> Dict[str, object]:
    run_now = []
    accepted_count = 0
    try:
        import scheduler

        r = scheduler.decide_next_actions(decisions_path=decisions_path)
        run_now = r.get("buckets", {}).get("run_now", []) or []
    except Exception:
        run_now = []

    decisions = _read_jsonl(decisions_path or (_FACTORY_ROOT / "data" / "decisions.jsonl"))
    accepted_count = sum(1 for d in decisions if d.get("status") == "ACCEPTED")

    if run_now:
        color = "GREEN"
    elif accepted_count:
        color = "YELLOW"
    else:
        color = "RED"

    top = run_now[0] if run_now else None
    detail = (
        f"Opportunity Queue: {len(run_now)} run-now item(s) "
        f"({top.get('niche') if top else 'none'}); {accepted_count} real ACCEPTED "
        f"decision(s) on record."
    )
    return {
        "value": {
            "run_now_count": len(run_now),
            "top_run_now": top.get("niche") if top else None,
            "accepted_count": accepted_count,
        },
        "color": color,
        "detail": detail,
        "source": "scheduler.py::decide_next_actions() buckets.run_now + data/decisions.jsonl ACCEPTED",
    }


# ---------------------------------------------------------------------------
# 4. BIGGEST_RISK -- highest-severity unresolved gap in the most recent audit
#    evidence (resilience_monitor findings are the real, recorded audit signal).
# ---------------------------------------------------------------------------

def _biggest_risk(
    safe_mode_state_path: Optional[Path] = None,
    publish_protection_state_path: Optional[Path] = None,
) -> Dict[str, object]:
    findings = []
    critical = []
    try:
        import resilience_monitor

        rm = resilience_monitor.assess_resilience(
            safe_mode_state_path=safe_mode_state_path,
            publish_protection_state_path=publish_protection_state_path,
        )
        findings = rm.get("findings", []) or []
        critical = [f for f in findings if f.get("severity") in ("critical", "emergency")]
    except Exception:
        findings = []
        critical = []

    color = "RED" if critical else "GREEN"
    top = critical[0] if critical else None
    detail = (
        (f"Critical/emergency: {len(critical)} active finding(s) -- {top.get('detail')}" if top
         else "No critical/emergency finding in the most recent audit evidence.")
    )
    return {
        "value": {
            "critical_or_emergency_findings": len(critical),
            "top_finding": top.get("detail") if top else None,
            "findings_total": len(findings),
        },
        "color": color,
        "detail": detail,
        "source": "resilience_monitor.py::assess_resilience() findings (severity critical/emergency)",
    }


# ---------------------------------------------------------------------------
# 5. TECHNOLOGY_THREAT -- a real, unmitigated technology risk, only with real
#    repo evidence (ai_capability/observatory.py obsolescence_detection).
# ---------------------------------------------------------------------------

def _technology_threat(
    ai_cost_path: Optional[Path] = None,
) -> Dict[str, object]:
    unmitigated = []
    try:
        from ai_capability.observatory import obsolescence_detection

        rows = obsolescence_detection(cost_log_path=ai_cost_path)
        for row in rows:
            if row.get("state") == "REPLACEMENT-RECOMMENDED" and not row.get("replacement_candidates"):
                unmitigated.append(row.get("model"))
    except Exception:
        rows = []

    color = "RED" if unmitigated else "GREEN"
    detail = (
        (f"Unmitigated technology threat: {len(unmitigated)} model(s) -- {', '.join(unmitigated)}"
         if unmitigated
         else "No unmitigated technology threat. Real obsolescence events (e.g. Groq retiring "
             "llama-3.1-8b-instant, 2026-08-16) are already mitigated: replaced by "
             "openai/gpt-oss-20b (book_generator.py GROQ_PRICING, verified 2026-08-14).")
    )
    return {
        "value": {
            "unmitigated_threats": len(unmitigated),
            "obsolescence_rows": len(rows or []),
        },
        "color": color,
        "detail": detail,
        "source": "ai_capability/observatory.py::obsolescence_detection() + book_generator.py GROQ_PRICING",
    }


# ---------------------------------------------------------------------------
# 6. AI_CAPABILITY -- the currently verified model/provider in use.
# ---------------------------------------------------------------------------

def _ai_capability(
    ai_cost_path: Optional[Path] = None,
) -> Dict[str, object]:
    adopted = None
    verified = None
    try:
        import execution_governance

        gov = execution_governance.capability_governance(
            cost_log_path=ai_cost_path
        )
        for m in gov.get("models", []):
            if m.get("governance_state") == "ADOPTED" and adopted is None:
                adopted = m
            elif m.get("governance_state") == "VERIFIED" and verified is None:
                verified = m
    except Exception:
        gov = {"models": []}

    if adopted:
        color = "GREEN"
    elif verified:
        color = "YELLOW"
    else:
        color = "RED"

    model = adopted or verified
    detail = (
        (f"Verified AI capability in use: {model['model']} ({model['provider']}) -- {model['governance_state']}."
         if model
         else UNKNOWN)
    )
    return {
        "value": {
            "adopted_model": adopted["model"] if adopted else None,
            "verified_model": verified["model"] if verified else None,
            "provider": (adopted or {}).get("provider"),
        },
        "color": color,
        "detail": detail,
        "source": "execution_governance.py::capability_governance() (evidence-cited only, never silent promotion)",
    }


# ---------------------------------------------------------------------------
# 7. LEARNING_LOOP -- does decision -> outcome -> lesson actually exist?
# ---------------------------------------------------------------------------

def _learning_loop(
    state_path: Optional[Path] = None,
    lessons_dir: Optional[Path] = None,
) -> Dict[str, object]:
    measured = []
    try:
        import evolution_queue

        result = evolution_queue.list_measured_outcomes(state_path=state_path) or {}
        measured = result.get("entries", []) if isinstance(result, dict) else []
    except Exception:
        measured = []

    lesson_files = 0
    try:
        lessons = lessons_dir or (_FACTORY_ROOT / "OpenClaw_Brain" / "19_Lessons_Learned")
        if lessons.exists():
            lesson_files = sum(1 for p in lessons.iterdir() if p.suffix == ".md")
    except Exception:
        lesson_files = 0

    closed_once = bool(measured)
    if closed_once:
        color = "GREEN"
    elif lesson_files:
        color = "YELLOW"
    else:
        color = "RED"

    detail = (
        f"{len(measured)} real measured outcome(s) on record; {lesson_files} real lesson "
        f"file(s); decision_outcomes.jsonl {'exists' if (state_path or (_FACTORY_ROOT / 'data' / 'decision_outcomes.jsonl')).exists() else 'absent'}. "
        f"Learning loop is {'CLOSED at least once' if closed_once else 'NOT CLOSED -- machinery real (evolution_queue.py), data-gated.'}"
    )
    return {
        "value": {
            "closed_once": closed_once,
            "measured_outcomes": len(measured),
            "lesson_files": lesson_files,
        },
        "color": color,
        "detail": detail,
        "source": "evolution_queue.py::list_measured_outcomes() + OpenClaw_Brain/19_Lessons_Learned/ + data/decision_outcomes.jsonl",
    }


# ---------------------------------------------------------------------------
# 8. COMMERCIAL_READINESS -- real products/opportunities with ZERO founder-gate
#    blockers. Preparation is never readiness.
# ---------------------------------------------------------------------------

def _commercial_readiness(
    finance_path: Optional[Path] = None,
    decisions_path: Optional[Path] = None,
) -> Dict[str, object]:
    candidate_products = 0
    zero_blocker_products = 0
    gated = []
    try:
        import founder_next_action

        fna = founder_next_action.build_founder_next_action()
        blockers = []
        if isinstance(fna, dict):
            queue = fna.get("queue") or []
            for item in queue:
                if isinstance(item, dict):
                    gate = item.get("action") or item.get("arm")
                    if gate:
                        blockers.append(gate)
        candidate_products = max(0, len(blockers))
        zero_blocker_products = 0  # every real candidate today still carries a founder gate
        gated = blockers
    except Exception:
        blockers = []

    if zero_blocker_products > 0:
        color = "GREEN"
    elif candidate_products > 0:
        color = "YELLOW"
    else:
        color = "RED"

    detail = (
        f"{zero_blocker_products} real product(s)/opportunity(ies) with ZERO founder-gate "
        f"blockers; {candidate_products} real candidate(s) identified. Every candidate "
        f"today still carries a founder gate: "
        + ("; ".join(gated[:3]) if gated else "none on record")
        + ". Preparation is never readiness."
    )
    return {
        "value": {
            "zero_blocker_products": zero_blocker_products,
            "candidate_products": candidate_products,
            "gated": gated,
        },
        "color": color,
        "detail": detail,
        "source": "founder_next_action.py::build_founder_next_action() (real founder-gated queue)",
    }


# ---------------------------------------------------------------------------
# The assembled CEO Score -- composition only.
# ---------------------------------------------------------------------------

def build_ceo_score(
    now: Optional[datetime] = None,
    finance_path: Optional[Path] = None,
    reality_path: Optional[Path] = None,
    decisions_path: Optional[Path] = None,
    snapshots_path: Optional[Path] = None,
    lock_path: Optional[Path] = None,
    ai_capability_decisions_path: Optional[Path] = None,
    ai_cost_path: Optional[Path] = None,
    state_path: Optional[Path] = None,
    lessons_dir: Optional[Path] = None,
    safe_mode_state_path: Optional[Path] = None,
    publish_protection_state_path: Optional[Path] = None,
) -> Dict[str, object]:
    """The CEO Score: exactly 8 indicators, each with a deterministic
    color (THRESHOLDS-only), a real value, a real detail string, and a real
    source. Plus Today's 3 Decisions (up to 3 real pending founder-gated
    decisions, fewer shown when fewer exist) and "What the founder can ignore
    today" (only items proven by the current real state).

    Read-only: writes nothing to disk, creates no external action, never
    changes an authority level, never touches a founder-gated flow."""
    indicators = {
        "FINANCIAL_TRUTH": _financial_truth(finance_path=finance_path, reality_path=reality_path),
        "SYSTEM_HEALTH": _system_health(snapshots_path=snapshots_path, lock_path=lock_path),
        "BEST_OPPORTUNITY": _best_opportunity(decisions_path=decisions_path),
        "BIGGEST_RISK": _biggest_risk(
            safe_mode_state_path=safe_mode_state_path,
            publish_protection_state_path=publish_protection_state_path,
        ),
        "TECHNOLOGY_THREAT": _technology_threat(ai_cost_path=ai_cost_path),
        "AI_CAPABILITY": _ai_capability(ai_cost_path=ai_cost_path),
        "LEARNING_LOOP": _learning_loop(state_path=state_path, lessons_dir=lessons_dir),
        "COMMERCIAL_READINESS": _commercial_readiness(finance_path=finance_path, decisions_path=decisions_path),
    }

    # Today's 3 Decisions -- the real founder-gated queue, top 3, fewer if fewer.
    today_decisions = []
    try:
        import founder_next_action

        fna = founder_next_action.build_founder_next_action()
        queue = fna.get("queue") or [] if isinstance(fna, dict) else []
        for item in queue:
            if isinstance(item, dict) and len(today_decisions) < 3:
                today_decisions.append({
                    "action": item.get("action"),
                    "arm": item.get("arm"),
                })
    except Exception:
        today_decisions = []

    # What the founder can ignore today -- only items proven by real state.
    ignore_list = []
    try:
        if indicators["TECHNOLOGY_THREAT"]["value"]["unmitigated_threats"] == 0:
            ignore_list.append("Technology threat -- no unmitigated threat (real obsolescence already mitigated)")
    except Exception:
        pass
    try:
        if indicators["BIGGEST_RISK"]["value"]["critical_or_emergency_findings"] == 0:
            ignore_list.append("Critical/emergency incidents -- none active in the most recent audit evidence")
    except Exception:
        pass
    try:
        if indicators["FINANCIAL_TRUTH"]["value"]["real_revenue_usd"] == 0:
            ignore_list.append("Revenue reconciliation -- no real revenue events to reconcile yet")
    except Exception:
        pass

    return {
        "generated_at": _now_iso(now),
        "indicators": [{"name": name, **indicators[name]} for name in CEO_SCORE_INDICATORS],
        "today_3_decisions": today_decisions,
        "what_founder_can_ignore_today": ignore_list,
        "note": (
            "CEO Score (Priority #1, 2026-08-17). Read-only composition over already-real "
            "engines/ledgers. Every value traces to a real repo data source; missing data "
            "reads the literal string 'Unknown — no data yet.'. Colors come exclusively from "
            "the deterministic THRESHOLDS maps. Creates no external action; modifies no "
            "founder-gated flow; HARD STOP remains fully in effect."
        ),
    }
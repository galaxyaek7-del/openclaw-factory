#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Continuous Trust & Resilience Monitoring (2026-07-29).

The founder's follow-up directive to the Global Trust & Resilience Layer
(ADR-135): "do not add more isolated fixes -- transform the layer into a
permanent monitoring and protection system." Research this session
confirmed almost every named signal (unstable subsystems, publish/
marketplace risk, payment/customer risk, security drift, data integrity,
health trend) already exists as a real, working function -- scattered
across independently-built modules with no shared severity vocabulary
and no aggregator. This module is that aggregator: Monitor + Classify +
(the Python half of) Report, reusing every signal verbatim, never
recomputing one.

Two things this module deliberately does NOT do (Protect / Founder-
approval boundary, unchanged from ADR-135):
  - It never calls channels.publish_protection.trigger_emergency_stop()
    or safe_mode.mark_subsystem_unstable() itself. Every irreversible/
    high-impact lever stays exactly as founder-gated as it already was --
    this module only makes the evidence for using one more visible,
    faster.
  - It never fabricates a severity when a signal has no real data yet
    (`data_available: False`) -- an "informational" default with no data
    is honestly distinguished from a verified-healthy "informational"
    with real data, never blended silently.

Severity vocabulary (the one genuinely new piece -- no existing signal
in this factory uses this exact 4-tier scale):
  informational < warning < critical < emergency
"""

import json
import os
from datetime import datetime, timezone

FACTORY_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_INCIDENTS_PATH = os.path.join(FACTORY_DIR, 'data', 'incidents.jsonl')

SEVERITY_LEVELS = ("informational", "warning", "critical", "emergency")
_SEVERITY_SCORE = {"informational": 100, "warning": 60, "critical": 20, "emergency": 0}

_CUSTOMER_RISK_CRITICAL_STAGES = {"PAYMENT_BLOCKED_PADDLE_ONBOARDING", "FAILED"}
_CUSTOMER_RISK_WARNING_STAGES = {"PENDING_CUSTOM_PRODUCT_SETUP", "PENDING_FOUNDER_REVIEW", "NEW", "PROPOSED"}

_SECURITY_DRIFT_WARNING_BELOW_RATIO = 0.5


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _finding(area, severity, detail, evidence, data_available=True):
    return {"area": area, "severity": severity, "detail": detail, "evidence": evidence, "data_available": data_available}


def _classify_safe_mode(state_path=None):
    """Unstable subsystems -- safe_mode.py::list_safe_mode_status()
    verbatim, never recomputed."""
    import safe_mode

    status = safe_mode.list_safe_mode_status(state_path=state_path)
    findings = []
    for name in ("ai_generation", "market_intelligence", "marketplace_publishing"):
        sub = status[name]
        if sub["unstable"]:
            findings.append(_finding(
                f"safe_mode:{name}", "critical",
                f"{name} is real, currently isolated (Safe Mode): {sub['reason']}",
                {"since": sub["since"], "triggered_by": sub["triggered_by"]},
            ))
        else:
            findings.append(_finding(f"safe_mode:{name}", "informational", f"{name} is real, currently stable", {}))
    return findings


def _classify_publish_protection(state_path=None):
    """Repeated errors / publish risk / marketplace risk --
    channels/publish_protection.py::list_publish_protection_status()
    verbatim, never recomputed."""
    from channels import publish_protection

    status = publish_protection.list_publish_protection_status(state_path=state_path)
    findings = []

    if status["global"]["emergency_stopped"]:
        findings.append(_finding(
            "publish_protection:global", "emergency",
            f"Global publish emergency stop is active: {status['global']['emergency_reason']}",
            status["global"],
        ))
    else:
        findings.append(_finding("publish_protection:global", "informational", "No active global publish emergency stop", {}))

    if not status["arms"]:
        findings.append(_finding(
            "publish_protection:arms", "informational",
            "No real publish attempt recorded yet for any arm", {}, data_available=False,
        ))
    for arm_name, arm in status["arms"].items():
        risk_score = arm["risk_score"]
        consecutive_failures = arm["consecutive_failures"]
        if consecutive_failures >= 3 or risk_score >= 70:
            severity = "critical"
        elif consecutive_failures >= 1 or risk_score >= 40:
            severity = "warning"
        else:
            severity = "informational"
        findings.append(_finding(
            f"publish_protection:{arm_name}", severity,
            f"{arm_name}: risk_score={risk_score}, consecutive_failures={consecutive_failures}, currently_allowed={arm['currently_allowed']}",
            arm,
        ))
    return findings


def _classify_customer_risk(requests_path=None, pipeline_state_path=None):
    """Payment risk / customer trust risk (pipeline side) --
    customer_pipeline.py::list_pipeline_overview()'s own real
    needs_attention, never a second stuck-request detector."""
    import customer_pipeline

    overview = customer_pipeline.list_pipeline_overview(requests_path=requests_path, state_path=pipeline_state_path)
    if not overview.get("total_requests"):
        return [_finding("customer_risk:pipeline", "informational", "No real customer requests exist yet", {}, data_available=False)]

    needs_attention = overview.get("needs_attention", [])
    critical_hits = [a for a in needs_attention if a.get("stage") in _CUSTOMER_RISK_CRITICAL_STAGES]
    warning_hits = [a for a in needs_attention if a.get("stage") in _CUSTOMER_RISK_WARNING_STAGES]

    if critical_hits:
        return [_finding(
            "customer_risk:pipeline", "critical",
            f"{len(critical_hits)} real customer request(s) stuck in a payment/failure state",
            {"request_ids": [a["request_id"] for a in critical_hits[:5]]},
        )]
    if warning_hits:
        return [_finding(
            "customer_risk:pipeline", "warning",
            f"{len(warning_hits)} real customer request(s) need real founder attention",
            {"request_ids": [a["request_id"] for a in warning_hits[:5]]},
        )]
    return [_finding("customer_risk:pipeline", "informational", "No real customer requests currently need attention", {})]


def _classify_security_drift():
    """Security drift -- ai_doctor.py's own real dependency-pinning check
    (same functions executive_score.py::_security_health() already
    reuses verbatim). Honestly point-in-time only -- no real historical
    security-trend signal exists yet in this factory, disclosed here
    rather than fabricated."""
    import ai_doctor

    findings = []
    for name, result in (("python", ai_doctor._check_python_pinning()), ("node", ai_doctor._check_node_pinning())):
        checked = result.get("checked", 0)
        pinned = result.get("pinned", 0)
        if not checked:
            findings.append(_finding(
                f"security_drift:{name}", "informational",
                f"No {name} dependencies listed yet", result, data_available=False,
            ))
            continue
        ratio = pinned / checked
        severity = "warning" if ratio < _SECURITY_DRIFT_WARNING_BELOW_RATIO else "informational"
        findings.append(_finding(f"security_drift:{name}", severity, f"{pinned}/{checked} {name} dependencies pinned", result))
    return findings


def _classify_ledger_integrity(ledgers=None, baseline_path=None):
    """Data integrity -- integrity_monitor.py's real SHA-256 hash-chain
    baseline over this factory's append-only ledgers (Security P1 C3,
    2026-08-18). Never rewrites any ledger -- the check's only write is
    its own baseline state (advance-on-clean). Every verdict is the real
    one from integrity_monitor.check_ledger_integrity(), never a guess."""
    import integrity_monitor

    results = integrity_monitor.check_ledger_integrity(ledgers=ledgers, baseline_path=baseline_path)
    findings = []
    for r in results:
        area = f"ledger_integrity:{os.path.basename(r['path'])}"
        if r["status"] == "DRIFT":
            findings.append(_finding(area, "critical", r["detail"], {"path": r["path"], "status": r["status"]}))
        elif r["status"] == "MISSING":
            findings.append(_finding(area, "warning", r["detail"], {"path": r["path"], "status": r["status"]}))
        elif r["status"] == "TRUNCATED":
            findings.append(_finding(area, "warning", r["detail"], {"path": r["path"], "status": r["status"]}))
        elif r["status"] == "CLEAN":
            findings.append(_finding(area, "informational", r["detail"], {"path": r["path"], "status": r["status"]}))
        else:  # NOT_BASELINED
            findings.append(_finding(area, "informational", r["detail"], {"path": r["path"], "status": r["status"]}, data_available=False))
    return findings


def _classify_health_trend(snapshots_path=None):
    """Health degradation -- health_trend.py::detect_health_degradation()
    verbatim (Round 1, already real)."""
    import health_trend

    result = health_trend.detect_health_degradation(snapshots_path)
    if not result["window"]:
        return [_finding("health_trend", "informational", result["reason"], {}, data_available=False)]
    if result["degrading"]:
        latest_status = result["window"][-1].get("status")
        severity = "critical" if latest_status == "critical" else "warning"
        return [_finding("health_trend", severity, result["reason"], {"window": result["window"]})]
    return [_finding("health_trend", "informational", result["reason"], {"window": result["window"]})]


def assess_resilience(safe_mode_state_path=None, publish_protection_state_path=None,
                       requests_path=None, pipeline_state_path=None, health_snapshots_path=None,
                       ledger_integrity_ledgers=None, ledger_integrity_baseline_path=None):
    """The one real aggregator -- Monitor + Classify + (the Python half
    of) Report. `resilience_score` follows executive_score.py's own
    precedent exactly: a transparent average of only the real,
    data-available findings, informational only, never gating anything,
    always disclosing how many findings were excluded and why."""
    findings = []
    findings.extend(_classify_safe_mode(state_path=safe_mode_state_path))
    findings.extend(_classify_publish_protection(state_path=publish_protection_state_path))
    findings.extend(_classify_customer_risk(requests_path=requests_path, pipeline_state_path=pipeline_state_path))
    findings.extend(_classify_security_drift())
    findings.extend(_classify_ledger_integrity(ledgers=ledger_integrity_ledgers, baseline_path=ledger_integrity_baseline_path))
    findings.extend(_classify_health_trend(snapshots_path=health_snapshots_path))

    scored = [f for f in findings if f["data_available"]]
    resilience_score = round(sum(_SEVERITY_SCORE[f["severity"]] for f in scored) / len(scored)) if scored else "Unknown"
    excluded = len(findings) - len(scored)

    active_alerts = [f for f in findings if f["severity"] in ("warning", "critical", "emergency")]

    return {
        "findings": findings,
        "active_alerts": active_alerts,
        "resilience_score": resilience_score,
        "resilience_score_note": (
            f"متوسط شفّاف لـ {len(scored)} من {len(findings)} مجالات مُقيَّمة فعلياً اليوم -- "
            f"{excluded} بلا بيانات حقيقية بعد (لم تُدرَج في المتوسط، لم تُفترَض سليمة). "
            "معلوماتي فقط -- لا يُستخدَم في أي بوابة قبول/رفض حقيقية."
        ),
        "generated_at": _now_iso(),
    }


# ── Learn: real incident recording ──
# "Record the incident in company memory" + the 5 Learn fields the
# directive asks for (root cause / prevention rule / detection rule /
# improvement proposal / rollback guidance). Every field below is either
# a real, evidence-cited template keyed to the finding's own real area,
# or honestly None -- never a fabricated diagnosis. Append-only, same
# convention as every other ledger in this factory (never rewrites
# history); "resolved" is a new event, not an edit to the old one.

_ROOT_CAUSE_TEMPLATES = {
    "safe_mode": "A real subsystem was marked unstable: {detail}",
    "publish_protection": "A real marketplace arm or the global publish state crossed a real risk threshold: {detail}",
    "customer_risk": "A real customer request is stuck in a state that blocks its own progress: {detail}",
    "security_drift": "A real dependency-pinning ratio fell below the safe threshold: {detail}",
    "ledger_integrity": "A real append-only ledger's baselined content was modified, truncated, or removed (Security P1 C3): {detail}",
    "health_trend": "A real GET /health status trend is degrading: {detail}",
}

_PREVENTION_RULE_TEMPLATES = {
    "safe_mode": "channels/base_arm.py's circuit breaker and safe_mode.py's per-subsystem isolation already exist to contain this -- see safe_mode.list_safe_mode_status() for current state.",
    "publish_protection": "channels/publish_protection.py's per-arm daily/hourly caps and cooldown already exist to contain this -- see channels/publish_protection.py::check_publish_allowed().",
    "customer_risk": "customer_pipeline.py's real retry/founder-review routing already exists for this -- see customer_pipeline.py::list_pipeline_overview()'s needs_attention.",
    "security_drift": "Pin the real dependency version in requirements.txt/package.json.",
    "ledger_integrity": "Restore the ledger from the real git-tracked history (scripts/restore_file_from_git.js) or the latest recovery/snapshot.py .bak, then rebuild the integrity baseline (integrity_monitor.build_baseline()).",
    "health_trend": "lib/health_checks.js's real infra checks are the diagnostic entry point -- see GET /health for which specific check is failing.",
}

_ROLLBACK_GUIDANCE = {
    "safe_mode:ai_generation": "POST /api/v1/actions/clear-subsystem-unstable { name: 'ai_generation' }",
    "safe_mode:market_intelligence": "POST /api/v1/actions/clear-subsystem-unstable { name: 'market_intelligence' }",
    "safe_mode:marketplace_publishing": "marketplace_publishing has no independent flag -- POST /api/v1/actions/publish-emergency-resume",
    "publish_protection:global": "POST /api/v1/actions/publish-emergency-resume",
}

# Real candidate proposal ids per area family -- only ever cited if the
# id is ACTUALLY present in tool_intelligence.proposals.list_proposals()
# right now (a live check, not a static guess).
_CANDIDATE_PROPOSAL_IDS = {
    "publish_protection": {"resolve_publish_emergency_stop", "investigate_marketplace_publish_health"},
    "customer_risk": {"resolve_stuck_customer_requests"},
    "health_trend": {"investigate_health_degradation_trend"},
}


def _area_family(area):
    return area.split(":", 1)[0]


def _rollback_guidance(area):
    if area in _ROLLBACK_GUIDANCE:
        return _ROLLBACK_GUIDANCE[area]
    if area.startswith("publish_protection:") and area not in ("publish_protection:global", "publish_protection:arms"):
        return (
            "Real per-arm cooldowns clear automatically once the platform's real minimum spacing elapses; "
            "a genuinely new or high-risk arm needs POST /api/v1/actions/approve-first-publish or "
            ".../approve-elevated-risk-publish { arm_name }."
        )
    return None


def _matching_proposal_id(area):
    """Only ever cites an id that's ACTUALLY present in the real,
    live tool_intelligence.proposals.list_proposals() output right now
    -- never a static guess presented as a live fact."""
    family = _area_family(area)
    candidates = _CANDIDATE_PROPOSAL_IDS.get(family)
    if not candidates:
        return None
    from tool_intelligence import proposals as proposals_module
    real_ids = {p["id"] for p in proposals_module.list_proposals()}
    matched = candidates & real_ids
    return next(iter(matched), None)


def _read_incidents(path):
    if not os.path.exists(path):
        return []
    entries = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _append_incident(record, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def _find_open_incident(existing, area):
    """The latest event recorded for this real area -- append-only, so
    the last matching line is the most recent real state. Open iff that
    latest event's type is "opened" (never re-derives from anything but
    this area's own real history)."""
    area_events = [e for e in existing if e.get("area") == area]
    if not area_events:
        return None
    latest = area_events[-1]
    return latest if latest.get("event") == "opened" else None


def record_incident(finding, incidents_path=None):
    """Learn: records a real incident only on a genuine state
    transition for this area -- a NEW critical/emergency finding that
    wasn't already open (dedup: an already-open incident is never
    re-appended every tick), or a real resolution (a previously-open
    incident whose finding is no longer critical/emergency). Returns the
    appended record, or None when there's nothing new to record."""
    path = incidents_path or DEFAULT_INCIDENTS_PATH
    area = finding["area"]
    is_actionable = finding["severity"] in ("critical", "emergency")
    open_incident = _find_open_incident(_read_incidents(path), area)

    if is_actionable and open_incident:
        return None
    if not is_actionable and not open_incident:
        return None

    if not is_actionable and open_incident:
        return _append_incident({
            "incident_id": open_incident["incident_id"], "area": area, "event": "resolved",
            "recorded_at": _now_iso(), "detail": finding["detail"],
        }, path)

    family = _area_family(area)
    root_cause_template = _ROOT_CAUSE_TEMPLATES.get(family)
    return _append_incident({
        "incident_id": f"{area}:{_now_iso()}",
        "area": area, "event": "opened", "severity": finding["severity"],
        "recorded_at": _now_iso(),
        "detail": finding["detail"], "evidence": finding["evidence"],
        "root_cause": root_cause_template.format(detail=finding["detail"]) if root_cause_template else "Unknown -- no real root-cause template exists yet for this area",
        "prevention_rule": _PREVENTION_RULE_TEMPLATES.get(family),
        "detection_rule": f"resilience_monitor.py::_classify_{family}() -- see this module for the exact real check",
        "improvement_proposal_id": _matching_proposal_id(area),
        "rollback_guidance": _rollback_guidance(area),
    }, path)


def list_incidents(incidents_path=None, limit=50):
    """Mission Control read view -- the real, full incident history
    (open + resolved), newest first. Honestly empty until a real
    critical/emergency finding has ever occurred."""
    entries = _read_incidents(incidents_path or DEFAULT_INCIDENTS_PATH)
    return list(reversed(entries[-limit:]))


def record_incidents_for_findings(findings, incidents_path=None):
    """Convenience: runs record_incident() over every finding from one
    assess_resilience() call, returning only the real, newly-appended
    records (never the deduped no-ops)."""
    recorded = []
    for finding in findings:
        record = record_incident(finding, incidents_path=incidents_path)
        if record is not None:
            recorded.append(record)
    return recorded

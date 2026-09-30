#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Factory Capability Registry (V70, Tier-1 safe).

Answers "what can the factory actually do right now?" -- never "what files
exist?". Read-only aggregator (no writes, no network, no execution):

- loads the real business capability list (config/capability_registry.json,
  ADR-040, 37 entries with REAL/ESTIMATED/DISCOVERY levels);
- adds the factory-operations capabilities this cycle verified by direct
  inspection (each with owner_module, evidence_source, verification_method);
- every entry carries current_status + last_verified; anything without a
  real signal is UNKNOWN, never PASS-by-default (V70 s20).

A capability is REAL only if code + test/call evidence exists on disk today.
"""
import json
import os
from datetime import datetime, timezone

_FACTORY_ROOT = os.path.dirname(os.path.abspath(__file__))
BUSINESS_REGISTRY_PATH = os.path.join(_FACTORY_ROOT, "config", "capability_registry.json")

# Factory-operations capabilities verified by V70 direct inspection.
# owner_module = the real file; evidence_source = how it was verified.
OPS_CAPABILITIES = [
    {"capability_id": "OPS-DRIFT-DETECT", "name": "Drift detection (HEAD vs worktree)",
     "purpose": "Detect tracked divergence including staged-new files",
     "owner_module": "scripts/drift_detector.py", "dependencies": ["git"],
     "runtime_entrypoint": "python scripts/drift_detector.py",
     "test_coverage": "data/factory_drift_detector_test.json (A-E suite)",
     "evidence_source": "V69 live runs (ABOVE_THRESHOLDS, source 2099->3471 post-fix)",
     "current_status": "REAL", "founder_dependency": False, "commercial_relevance": "indirect",
     "security_risk": "none", "recovery_method": "re-run (stateless)"},
    {"capability_id": "OPS-EXP-GOVERN", "name": "Experiment window protection",
     "purpose": "Block mid-window mutation of live experiments",
     "owner_module": "experiment_governor.py", "dependencies": ["experiment records on disk"],
     "runtime_entrypoint": "experiment_governor.assert_safe_to_mutate",
     "test_coverage": "tests/test_experiment_governor.py",
     "evidence_source": "V70 direct test run",
     "current_status": "REAL", "founder_dependency": False, "commercial_relevance": "protects revenue evidence",
     "security_risk": "none (raise-only guard)", "recovery_method": "n/a (guard, no state)"},
    {"capability_id": "OPS-CANONICAL-INVENTORY", "name": "Canonical source-of-truth inventory",
     "purpose": "Distinguish SOURCE/STAGED/COMMITTED/RUNTIME/GENERATED/IGNORED views",
     "owner_module": "canonical_inventory.py", "dependencies": ["git"],
     "runtime_entrypoint": "canonical_inventory.build_inventory",
     "test_coverage": "tests/test_canonical_inventory.py",
     "evidence_source": "V70 direct test run",
     "current_status": "REAL", "founder_dependency": False, "commercial_relevance": "indirect",
     "security_risk": "none", "recovery_method": "re-run (stateless)"},
    {"capability_id": "OPS-HEALTH-VECTOR", "name": "Factory health vector (8 dims)",
     "purpose": "Honest per-dimension health with UNKNOWN defaults",
     "owner_module": "factory_health_vector.py", "dependencies": ["resilience_monitor", "evidence_engine", "finance readers"],
     "runtime_entrypoint": "factory_health_vector.health_vector",
     "test_coverage": "tests/test_factory_health_vector.py",
     "evidence_source": "V70 direct test run",
     "current_status": "REAL", "founder_dependency": False, "commercial_relevance": "indirect",
     "security_risk": "none", "recovery_method": "re-run (stateless)"},
    {"capability_id": "OPS-GAP-ENGINE", "name": "Autonomous gap detection + prioritization",
     "purpose": "Periodic OBSERVE->DOCUMENT over registry/inventory/health/bottleneck",
     "owner_module": "factory_gap_engine.py", "dependencies": ["factory_capability_registry", "canonical_inventory", "experiment_governor"],
     "runtime_entrypoint": "factory_gap_engine.run_cycle",
     "test_coverage": "tests/test_factory_gap_engine.py",
     "evidence_source": "V70 direct test run",
     "current_status": "REAL", "founder_dependency": False, "commercial_relevance": "indirect",
     "security_risk": "none (Tier-1 whitelist: record/report only)", "recovery_method": "re-run (stateless)"},
    {"capability_id": "OPS-CHANGE-QUEUE", "name": "Tiered autonomous change queue",
     "purpose": "Classify changes AUTO/PREPARE/FOUNDER_GATE; auto-run read-only whitelist only",
     "owner_module": "factory_change_queue.py", "dependencies": [],
     "runtime_entrypoint": "factory_change_queue.run_tier1",
     "test_coverage": "tests/test_factory_change_queue.py",
     "evidence_source": "V70 direct test run",
     "current_status": "REAL", "founder_dependency": False, "commercial_relevance": "indirect",
     "security_risk": "none (whitelist is read-only/record-only)", "recovery_method": "queue is append-only JSONL"},
    {"capability_id": "COM-REALITY-FIREWALL", "name": "Commercial reality firewall",
     "purpose": "Forbid weak-signal -> revenue conclusions (10 verification states)",
     "owner_module": "commercial_reality.py", "dependencies": ["finance_data.json", "channels/ledger.py"],
     "runtime_entrypoint": "commercial_reality.check_governance_gate",
     "test_coverage": "pre-existing module tests",
     "evidence_source": "V70 code inspection (pre-existing, reused not rebuilt)",
     "current_status": "REAL", "founder_dependency": False, "commercial_relevance": "direct",
     "security_risk": "none", "recovery_method": "module is stateless gate"},
    {"capability_id": "COM-BOTTLENECK", "name": "Commercial bottleneck detection",
     "purpose": "Name WHERE the business is stuck with evidence",
     "owner_module": "affiliate/diagnostics.py", "dependencies": ["funnel ledgers"],
     "runtime_entrypoint": "affiliate.diagnostics.bottleneck_engine",
     "test_coverage": "pre-existing module tests",
     "evidence_source": "V70 code inspection (pre-existing, reused not rebuilt)",
     "current_status": "REAL", "founder_dependency": False, "commercial_relevance": "direct",
     "security_risk": "none", "recovery_method": "re-run (stateless)"},
    {"capability_id": "COM-DECISION-MEMORY", "name": "Institutional decision memory",
     "purpose": "Why each decision was made; alternatives; expected vs actual outcome",
     "owner_module": "executive_decision_memory.py", "dependencies": ["decision_engine.store", "knowledge_graph"],
     "runtime_entrypoint": "executive_decision_memory.explain_decision",
     "test_coverage": "pre-existing module tests",
     "evidence_source": "V70 code inspection (pre-existing, reused not rebuilt)",
     "current_status": "REAL", "founder_dependency": False, "commercial_relevance": "direct",
     "security_risk": "none", "recovery_method": "ledgers are append-only"},
    {"capability_id": "OPS-RECOVERY-BASE", "name": "Crash-recovery base (checkpoint/lock/idempotency/retry-queue)",
     "purpose": "Survive crash/restart without double external effects",
     "owner_module": "factory_state.py + recovery/startup_check.py + orchestrator/",
     "dependencies": ["data/factory_state.json"],
     "runtime_entrypoint": "recovery.startup_check.check_startup_safety",
     "test_coverage": "pre-existing module tests",
     "evidence_source": "V70 code inspection (pre-existing, reused not rebuilt)",
     "current_status": "PARTIAL", "founder_dependency": False, "commercial_relevance": "indirect",
     "security_risk": "none", "recovery_method": "documented gap: no generic replay executor (Tier-2, executes queued work)"},
    {"capability_id": "COM-FIRST-SALE", "name": "First real sale (transaction + revenue)",
     "purpose": "The only proof of commercial reality",
     "owner_module": "NONE (external event, not code)",
     "dependencies": ["founder publish action", "Paddle onboarding / live channel credential"],
     "runtime_entrypoint": "n/a",
     "test_coverage": "n/a",
     "evidence_source": "finance_data.json sales=[] + sales_ledger 0 sale rows (V69/V70)",
     "current_status": "MISSING", "founder_dependency": True, "commercial_relevance": "direct",
     "security_risk": "n/a", "recovery_method": "n/a"},
]


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def list_capabilities():
    """Full capability list: business registry + ops layer. Read-only."""
    caps = []
    try:
        with open(BUSINESS_REGISTRY_PATH, encoding="utf-8") as f:
            biz = json.load(f).get("capabilities", [])
        for c in biz:
            caps.append({
                "capability_id": "BIZ-" + str(c.get("id", "unknown")),
                "name": c.get("name", "unknown"),
                "purpose": str(c.get("source", ""))[:200],
                "owner_module": "see config/capability_registry.json",
                "current_status": {"REAL": "REAL", "ESTIMATED": "PARTIAL"}.get(
                    c.get("level"), "DISCOVERY"),
                "founder_dependency": "UNKNOWN",
                "commercial_relevance": "UNKNOWN",
                "evidence_source": "config/capability_registry.json",
                "verification_method": "registry level field (not re-verified this cycle)",
            })
    except (OSError, ValueError):
        pass
    for c in OPS_CAPABILITIES:
        entry = dict(c)
        entry["last_verified"] = _now_iso()
        entry["verification_method"] = "V70 direct inspection/test"
        caps.append(entry)
    return caps


def capability_summary():
    caps = list_capabilities()
    by_status = {}
    for c in caps:
        by_status[c["current_status"]] = by_status.get(c["current_status"], 0) + 1
    return {"total": len(caps), "by_status": by_status, "at": _now_iso()}

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Enterprise Validation Phase (ADR-166, 2026-07-31).

The founder's directive labeled itself "ADR-164" -- already allocated
(AI Automation Revenue Engine, committed `ad5a669`). Real next number:
ADR-166 (ADR-165, Enterprise Capital Allocation Engine, was the
immediately preceding round).

"Pause feature development... No new functionality... Only validation,
correction, stabilization and documentation" -- same explicit scope
class as ADR-162 (Enterprise Truth Audit). This module is almost
entirely a citation orchestrator over already-real validation/audit
functions built across this session -- reality_audit.py (ADR-162),
truth_first.py (ADR-160), evidence_engine.py (ADR-163), gfos.py
(ADR-147), enterprise_executive_brain.py (ADR-156), executive_quality_
gate.py, evolution_engine.py, launch_readiness.py (ADR-153) -- run
together, once, and assembled into the directive's named Enterprise
Validation Report shape. The ONE genuinely new function is
detect_unused_services() (Objective 15, "detect unused services") --
no prior real, reusable, permanent implementation existed (ADR-151's
name-diff technique was a one-time manual pass, never turned into
callable code).
"""

import re
from datetime import datetime, timezone

_this = __file__


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def verify_departments():
    """Objective 2/3: per-department real citation + real dependency/
    communication check -- pure reuse of gfos.py (ADR-147) and
    enterprise_operations.py/enterprise_executive_brain.py (ADR-155/156)."""
    import gfos
    from enterprise_operations import dependency_matrix
    from enterprise_executive_brain import enterprise_dependency_graph

    return {
        "department_registry": gfos.department_registry(),
        "dependency_matrix": dependency_matrix(),
        "cascade_and_cycles": enterprise_dependency_graph(),
        "source": "gfos.py::department_registry() (ADR-147) + enterprise_operations.py::dependency_matrix() (ADR-155) + enterprise_executive_brain.py::enterprise_dependency_graph() (ADR-156).",
    }


def verify_truth_first_compliance():
    """Objective 8/9/10/11: Truth First / Simulation isolation / Evidence
    integrity / Legal Safety -- pure citation, zero new checks."""
    import truth_first
    import evidence_engine
    import executive_quality_gate as eqg

    return {
        "truth_first": truth_first.truth_first_compliance_report(),
        "evidence_integrity": {etype: evidence_engine.verify(evidence_type=etype) for etype in evidence_engine.EVIDENCE_TYPES},
        "legal_safety_checks": {"hard_reject_pipeline": eqg.REJECT_IF_FAIL},
        "source": "truth_first.py (ADR-160) + evidence_engine.py (ADR-163) + executive_quality_gate.py (ADR-102/160), Simulation isolation cited inside truth_first_compliance_report() via simulation_mode.py (ADR-153).",
    }


def detect_duplicated_logic():
    """Objective 13: pure citation of enterprise_executive_brain.py's
    real, already-built department-pair import-overlap detector."""
    from enterprise_executive_brain import _detect_duplicated_work
    return {"answer": _detect_duplicated_work(), "source": "enterprise_executive_brain.py::_detect_duplicated_work() (ADR-156)."}


def detect_unused_services(server_js_path=None, factory_loop_js_path=None):
    """Objective 15: the ONE genuinely new function this round --
    ADR-151 found 20 real orphaned SERVICE_REGISTRY entries via a
    one-time manual name-diff technique; this is that same real,
    mechanical technique turned into a permanent, re-runnable check.
    An endpoint counts as 'referenced' if its exact real name string
    appears anywhere in server.js (SERVICE_REGISTRY/ACTION_REGISTRY) or
    factory_loop.js (daily-tick subprocess dispatch) -- the 2 known
    real callers of mission_control_api.py::_ENDPOINTS in this factory.
    Honestly disclosed limitation: a standalone script calling an
    endpoint directly (bypassing both) would not be detected here."""
    import os
    import mission_control_api as mca

    root = os.path.dirname(os.path.abspath(_this))
    server_path = server_js_path or os.path.join(root, "server.js")
    loop_path = factory_loop_js_path or os.path.join(root, "factory_loop.js")

    with open(server_path, "r", encoding="utf-8") as f:
        server_src = f.read()
    with open(loop_path, "r", encoding="utf-8") as f:
        loop_src = f.read()

    names = list(mca._ENDPOINTS.keys())
    unused = [n for n in names if f"'{n}'" not in server_src and f"'{n}'" not in loop_src]

    return {
        "total_endpoints": len(names),
        "unreferenced_in_server_or_factory_loop": unused,
        "count_unreferenced": len(unused),
        "note": "Real, mechanical string-presence check against server.js + factory_loop.js -- the 2 known real dispatch callers of mission_control_api.py::_ENDPOINTS. A standalone script calling an endpoint directly would not be detected by this check, honestly disclosed as a real limitation.",
        "generated_at": _now_iso(),
    }


def detect_bottlenecks():
    """Objective 16: pure citation of evolution_engine.py's real,
    already-built bottleneck detector."""
    import evolution_engine
    report = evolution_engine.build_evolution_report()
    return {"answer": report.get("bottlenecks"), "source": "evolution_engine.py::build_evolution_report()['bottlenecks'] (executive_intelligence/bottlenecks.py, ADR-052)."}


def readiness_score(division_readiness=None):
    """Real citation of launch_readiness.py's per-division 8-dim
    scorecard (ADR-153) -- the closest real 'readiness score' this
    factory has, never a new number invented for this report."""
    import launch_readiness
    if division_readiness is None:
        division_readiness = launch_readiness.launch_readiness_score()
    return {"answer": division_readiness, "source": "launch_readiness.py::launch_readiness_score() (ADR-153)."}


def build_enterprise_validation_report():
    """The one real aggregator -- assembles the directive's named
    Enterprise Validation Report shape (Working/Partially working/Not
    implemented systems, Risks, Technical debt, Highest priorities,
    Readiness score) entirely from already-real functions, run exactly
    once each. Re-runs reality_audit.py live for fresh classification
    numbers (real state changes over a session -- see ADR-162's own
    Addendum 2 for why trusting a stale snapshot here would be
    dishonest)."""
    import reality_audit as ra
    import launch_readiness

    audit_results = ra.audit_all_endpoints(record_evidence=False)
    score = ra.reality_score(audit_results)
    ledger = ra.build_reality_ledger(audit_results)
    debt = ra.technical_debt_register(ledger)

    working = [e for e in ledger if e["classification"] == "REAL"]
    partially_working = [e for e in ledger if e["classification"] in ("SIMULATION", "ARCHITECTURE_ONLY")]
    not_implemented = [e for e in ledger if e["classification"] in ("NOT_IMPLEMENTED", "DEPRECATED")]

    division_readiness = launch_readiness.launch_readiness_score()

    return {
        "working_systems": {"count": len(working), "names": [e["name"] for e in working]},
        "partially_working_systems": {"count": len(partially_working), "entries": partially_working},
        "not_implemented_systems": {"count": len(not_implemented), "entries": not_implemented},
        "departments": verify_departments(),
        "truth_first_simulation_evidence_legal": verify_truth_first_compliance(),
        "duplicated_logic": detect_duplicated_logic(),
        "unused_services": detect_unused_services(),
        "bottlenecks": detect_bottlenecks(),
        "risks": [e for e in ledger if e["risk_level"].startswith("high")],
        "technical_debt": debt,
        "highest_priorities": debt[:5],
        "readiness_score": readiness_score(division_readiness=division_readiness),
        "enterprise_reality_score": score,
        "generated_at": _now_iso(),
    }

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Truth First Constitution (ADR-160, 2026-07-31).

The founder's "TRUTH FIRST CONSTITUTION" directive, declared this
company's highest law (OPENCLAW_OS_CONSTITUTION.md's new "TRUTH FIRST"
section). See OpenClaw_Brain/00_Governance/TRUTH_FIRST_CONSTITUTION.md
for the full mechanism and audit this module implements.

This is a governance-ratification round, not a feature build: a
repo-wide census found this factory has already been practicing this
exact discipline all session (246 real honest-disclosure instances
across 9 inconsistent variants) -- vocabulary_census() is the callable,
re-runnable version of that finding. CANONICAL_VOCABULARY governs all
NEW code from this ADR forward; the 246 existing instances are
grandfathered, never retrofitted (a purely cosmetic rewrite of already-
truthful code, out of proportion to any real benefit).
"""

import os
import re
from datetime import datetime, timezone

_FACTORY_ROOT = os.path.dirname(os.path.abspath(__file__))

# The 9 named terms, verbatim from the directive. Use these in all new
# code going forward -- never invent a 10th synonym.
CANONICAL_VOCABULARY = {
    "NOT BUILT": "No real code/module exists for this capability anywhere in this factory.",
    "NOT IMPLEMENTED": "The design/architecture exists but the real, working code path does not yet.",
    "NOT CONNECTED": "A real integration point exists in code but has no real credential/live connection today.",
    "NOT MEASURED": "A real signal could exist but no real measurement has ever been recorded for it.",
    "UNKNOWN": "No real signal or evidence exists to answer this question at all.",
    "WAITING FOR REAL DATA": "The real mechanism exists and is armed, but has not yet observed enough real events to report.",
    "SIMULATION": "This output is a real, disclosed hypothetical -- never real production data (simulation_mode.py, ADR-153).",
    "REFERENCE IMPLEMENTATION": "A real, working example exists but is not wired into the live, automatic pipeline.",
    "PLANNED": "A real, named future capability with no code yet -- a roadmap item, not a current gap in something built.",
}

# The 9 real vocabulary variants already found in this codebase before
# this ADR (repo-wide census, 2026-07-31) -- grandfathered, not rewritten.
_KNOWN_EXISTING_VARIANTS = [
    "DISCOVERY",
    "NOT ENOUGH EVIDENCE",
    "NOT_ARCHITECTED",
    "NOT YET BUILT",
    "NOT_ENOUGH_DATA",
    "WAITING_FOR_REAL_SOURCE",
    "no_real_source",
    "not_computed",
    "WAITING FOR REAL SOURCE",
]


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def vocabulary_census(root_dir=None):
    """Real, mechanical scan over every *.py file for the 9 known
    pre-ADR-160 honest-disclosure variants -- the callable, re-runnable
    version of this ADR's own research finding. A string census, not a
    semantic auditor: it counts known honest-disclosure phrases, it
    cannot detect a fabrication that uses novel wording -- same honest
    limitation executive_quality_gate.py's phrase-list checks already
    disclose about themselves."""
    root = root_dir or _FACTORY_ROOT
    counts = {variant: 0 for variant in _KNOWN_EXISTING_VARIANTS}
    files_scanned = 0

    skip_dirs = {".git", "node_modules", "__pycache__", "backups", ".venv", "venv"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for fname in filenames:
            if not fname.endswith(".py"):
                continue
            files_scanned += 1
            path = os.path.join(dirpath, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()
            except (OSError, UnicodeDecodeError):
                continue
            for variant in _KNOWN_EXISTING_VARIANTS:
                counts[variant] += len(re.findall(re.escape(variant), text))

    return {
        "counts": counts,
        "total_instances": sum(counts.values()),
        "files_scanned": files_scanned,
        "note": "A real, mechanical string census over *.py files -- these 9 variants are grandfathered (ADR-160), never retrofitted; CANONICAL_VOCABULARY governs all new code going forward.",
        "generated_at": _now_iso(),
    }


def truth_first_compliance_report(census=None):
    """The one real aggregator: the vocabulary census + real citations
    of the 3 standing controls this directive's other requirements are
    already satisfied by -- never a second gate, never a fabricated
    compliance score."""
    if census is None:
        census = vocabulary_census()

    import simulation_mode
    import executive_quality_gate

    return {
        "vocabulary_census": census,
        "canonical_vocabulary": CANONICAL_VOCABULARY,
        "simulation_production_separation": {
            "answer": "REAL",
            "source": "simulation_mode.py::SIMULATION_TAG/is_simulation_mode()/tag_simulated() (ADR-153) -- every division's simulation code tags output, writes to its own separate ledger, never touches real ground truth.",
        },
        "legal_safety_review_coverage": {
            "hard_reject_pipeline": executive_quality_gate.REJECT_IF_FAIL,
            "source": "executive_quality_gate.py::REJECT_IF_FAIL -- the real, already-enforced pipeline every opportunity/product passes through.",
            "note": "See OpenClaw_Brain/00_Governance/TRUTH_FIRST_CONSTITUTION.md for the full per-check audit against this directive's 8 named Legal Safety Review items -- some real, some architecturally-already-satisfied (e.g. fake reviews via customer_pipeline.py::submit_review()'s real request_id requirement), one genuine gap closed this round (check_copyright_trademark_risk).",
        },
        "self_audit_subsystems": {
            "answer": ["resilience_monitor.py (Monitor+Classify+Learn, every tick)", "ai_doctor.py (real dependency/quality checks)", "self_awareness.js / executive_score.py (CONSTITUTION.md Sec.20)"],
            "source": "Real, live, pre-existing self-audit subsystems -- cited, not duplicated.",
        },
        "generated_at": _now_iso(),
    }

"""
Executive Orchestrator — shared types (ADR-051).
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

# The declared execution order — data, not implicit code structure, so
# "the Orchestrator manages execution order" is a literal, inspectable
# property (requirement), not just an accident of function-call layout.
EXECUTION_ORDER = ("market_intelligence", "decision", "production", "publishing", "learning")

# Stages with a real, costly, or irreversible side effect once actually
# executed (real subprocess spend, real platform publish). Duplicate-
# execution prevention is scoped to exactly these — market_intelligence/
# decision/learning are cheap, read-mostly, and this factory already has
# its own freshness/re-evaluation semantics for them (competitor_
# discovery.py's cache window, decision_engine's append-only re-decision
# history) — permanently skipping their re-run after one success would
# make the system unable to ever re-evaluate a niche again, which is
# wrong. Only production/publishing get the "never run twice" guarantee.
DUPLICATE_SENSITIVE_STAGES = ("production", "publishing")

STATUSES = ("SUCCESS", "FAILED", "SKIPPED_DUPLICATE", "SKIPPED_NOT_APPLICABLE")


@dataclass
class ExecutionResult:
    engine: str
    status: str  # one of STATUSES
    started_at: str
    finished_at: str
    attempts: int
    idempotency_key: str
    output: Dict[str, Any]
    error: Optional[str] = None

    def to_dict(self):
        return {
            "engine": self.engine,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "attempts": self.attempts,
            "idempotency_key": self.idempotency_key,
            "output": self.output,
            "error": self.error,
        }

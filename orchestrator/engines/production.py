"""
Production engine adapter (ADR-051) — real subprocess integration with
book_generator.py's established stdin-JSON-in / stdout-JSON-out CLI
(the same `--json` contract server.js/factory_loop.js already use,
dispatching on `topic` in the payload -> generate_book()).

Safety: dry_run=True by default, same convention distributor.py already
uses for anything with a real-world cost/side effect. This engine is
only reached at all when the Orchestrator's execute_production gate is
True (see orchestrator.py) AND the decision stage's status was
ACCEPTED — a dry_run=True context reaching here regardless still never
spawns the real subprocess, so misconfiguration can never silently
spend real Groq tokens.
"""

import json
import subprocess
import sys
from pathlib import Path

from orchestrator.registry import register_engine

_FACTORY_ROOT = Path(__file__).resolve().parent.parent.parent
_BOOK_GENERATOR = _FACTORY_ROOT / "book_generator.py"


@register_engine("production")
def run(context):
    if context.get("dry_run", True):
        return {"executed": False, "reason": "dry_run=True — no subprocess spawned, no Groq cost incurred"}

    payload = {"topic": context["niche"], "title": context["niche"], "author": "OpenClaw Factory"}
    proc = subprocess.run(
        [sys.executable, str(_BOOK_GENERATOR), "--json"],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True, text=True, timeout=300, encoding="utf-8",
    )
    try:
        result = json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError):
        return {"executed": True, "success": False, "error": f"invalid JSON from book_generator.py: {proc.stdout[:500]}"}
    return {"executed": True, **result}

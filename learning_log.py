"""Weekly Learning Log (Cycle 82, item 5 -- "the heart of ongoing growth").

A real, append-only, human-triggered record of the weekly loop the directive
asked for: read the real funnel numbers (growth_funnel.py) -> write one
hypothesis -> change exactly one variable (headline/price/post-type) ->
measure the following week -> record here.

No automatic entry is ever created by this module or by any tick -- every
record requires a human (founder or Claude Code, during a real review
session) to have actually looked at real numbers and decided a real change.
Forbidden, honored by construction: this module has no code path that can
beautify a number or substitute a self/test purchase for a sale -- it only
ever stores whatever the caller explicitly passes in as `funnel_snapshot`,
never recomputes or adjusts it.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

_FACTORY_ROOT = Path(__file__).resolve().parent


def _now_iso(now: Optional[datetime] = None) -> str:
    return (now or datetime.now(timezone.utc)).isoformat()


def record_weekly_learning_entry(
    week_label: str,
    hypothesis: str,
    variable_changed: str,
    change_description: str,
    funnel_snapshot: Dict[str, object],
    result: Optional[str] = None,
    log_path: Optional[Path] = None,
    now: Optional[datetime] = None,
) -> Dict[str, object]:
    """Appends one real weekly entry. `variable_changed` must be exactly one
    of the 3 named variables the directive allows ("headline", "price",
    "post_type") -- enforced, not just documented, so a future caller can't
    silently change more than one variable per week and still call it a
    clean experiment."""
    allowed_variables = ("headline", "price", "post_type")
    if variable_changed not in allowed_variables:
        raise ValueError(
            f"variable_changed must be one of {allowed_variables}, got {variable_changed!r}"
        )
    if not hypothesis or not hypothesis.strip():
        raise ValueError("hypothesis must be a real, non-empty statement")

    entry = {
        "week_label": week_label,
        "hypothesis": hypothesis,
        "variable_changed": variable_changed,
        "change_description": change_description,
        "funnel_snapshot": funnel_snapshot,
        "result": result,
        "recorded_at": _now_iso(now),
    }
    path = log_path or (_FACTORY_ROOT / "data" / "learning_log.jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def list_learning_entries(log_path: Optional[Path] = None) -> List[Dict[str, object]]:
    """Real, chronological reader -- returns [] when the log doesn't exist
    yet (never fabricates a first entry)."""
    path = log_path or (_FACTORY_ROOT / "data" / "learning_log.jsonl")
    entries = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return entries

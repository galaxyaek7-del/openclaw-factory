"""
Manual verification ledger (Real Evidence Provider abstraction, ADR-179,
2026-08-06) — the real bridge for the "Web pages" priority tier (10)
and for any other source a human or Claude Code actually tried to
reach live during a session and hit a real, observable outcome
(succeeded, or actively blocked). Same "a human (or Claude Code,
checking a real public page during a session)" discipline
market_evidence.py's own docstring already established for Proof of
Payment evidence — this module is that same discipline generalized to
ANY evidence source's verification status, not only payment evidence.

Never fabricates a live web-fetch capability this factory does not
have: nothing here autonomously fetches a URL. record_verification()
only records what a real session already observed. `web_pages.py`'s
connector reads this ledger back — a real record of a real, honestly
BLOCKED attempt is exactly the kind of evidence the founder's directive
asked to capture rather than silently discard.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LEDGER_PATH = _FACTORY_ROOT / "data" / "verification_attempts.jsonl"

VALID_STATUSES = ("VERIFIED", "BLOCKED")


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def record_verification(niche, source_url, status, reason=None, quote=None, status_code=None, ledger_path=None):
    """Appends one real, observed verification attempt. `status` must be
    a real outcome ("VERIFIED" — the page loaded and the quote below was
    read directly from it; "BLOCKED" — the fetch was actively refused,
    e.g. HTTP 403/429). Never invents a status outside these two; an
    attempt that simply wasn't made yet is never recorded (there is
    nothing real to write)."""
    if status not in VALID_STATUSES:
        raise ValueError(f"status يجب أن يكون أحد {VALID_STATUSES} — لا حالة مُختلَقة: {status!r}")
    if not source_url:
        raise ValueError("record_verification يتطلب source_url حقيقياً — لا تسجيل بلا مصدر قابل للتحقق")

    event = {
        "niche": niche,
        "source": "web_pages",
        "source_url": source_url,
        "status": status,
        "status_code": status_code,
        "reason": reason,
        "quote": quote,
        "recorded_at": _now_iso(),
    }
    path = Path(ledger_path) if ledger_path else Path(DEFAULT_LEDGER_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def get_verification_attempts(niche, ledger_path=None):
    """Every real, previously-recorded attempt for this niche, oldest
    first. Honestly empty when nothing has ever been recorded — never
    inferred from anything else."""
    path = Path(ledger_path) if ledger_path else Path(DEFAULT_LEDGER_PATH)
    if not path.exists():
        return []
    key = (niche or "").strip().lower()
    attempts = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if (event.get("niche") or "").strip().lower() == key:
                attempts.append(event)
    return attempts

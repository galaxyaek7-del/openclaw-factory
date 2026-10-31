#!/usr/bin/env python3
"""Daily distribution-metrics reading for factory_loop.js (2026-10-29).

Once per UTC day, run scripts/poll_distribution_metrics.py (read-only:
Telegraph getViews for the factory's own articles, Gumroad sales, interest
ledger counts), which appends one record to data/distribution_metrics.jsonl.
The ledger's own last timestamp is the daily gate, so no extra state file; a
reading in which no article could be read (network outage) is retried hourly.

Why: eight Telegraph experiments were recorded RUNNING on 2026-10-09 and the
poller was last run that same day; nothing read their exposure for 20 days.

    python scripts/distribution_metrics_daily.py --once
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "data" / "distribution_metrics.jsonl"
POLLER = ROOT / "scripts" / "poll_distribution_metrics.py"


def last_record(ledger=LEDGER):
    try:
        lines = [l for l in Path(ledger).read_text(encoding="utf-8").splitlines() if l.strip()]
        return json.loads(lines[-1]) if lines else None
    except (OSError, ValueError):
        return None


def _poll(timeout_s=240):
    r = subprocess.run([sys.executable, str(POLLER)], cwd=str(ROOT), capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=timeout_s)
    if r.returncode != 0:
        raise RuntimeError(f"poller exited {r.returncode}: {r.stderr.strip()[-200:]}")


RETRY_AFTER_SECONDS = 3600


def _all_unreadable(rec):
    # Every article read failed (e.g. URLError during a network outage): the
    # day has no reading yet. A record with no articles at all is a reading.
    st = rec.get("views_status") or {}
    return bool(st) and not any(v == "ok" for v in st.values())


def run_once(today=None, ledger=LEDGER, poll=None, now=None):
    now = now or datetime.now(timezone.utc)
    today = today or now.date().isoformat()
    last = last_record(ledger)
    if last and str(last.get("timestamp", ""))[:10] == today:
        if not _all_unreadable(last):
            return {"action": "none", "detail": f"distribution metrics already read for {today}"}
        try:
            age = (now - datetime.fromisoformat(last["timestamp"])).total_seconds()
        except (KeyError, ValueError, TypeError):
            age = RETRY_AFTER_SECONDS
        if age < RETRY_AFTER_SECONDS:
            return {"action": "none", "detail": "no article was readable at the last attempt; retrying after an hour"}
    before = (last or {}).get("timestamp")
    try:
        (poll or _poll)()
    except Exception as e:
        return {"action": "failed", "detail": f"{type(e).__name__}: {str(e)[:200]}"}
    rec = last_record(ledger)
    if not rec or rec.get("timestamp") == before:
        return {"action": "failed", "detail": "poller ran but appended no record"}
    views = rec.get("views") or {}
    ok = [k for k, s in (rec.get("views_status") or {}).items() if s == "ok"]
    total = sum(v for v in views.values() if isinstance(v, int))
    return {"action": "recorded",
            "detail": f"{len(ok)}/{len(views)} articles read, {total} platform-reported views (not verified human visits)"}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--once" not in argv:
        print(__doc__)
        return 2
    print(json.dumps(run_once()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

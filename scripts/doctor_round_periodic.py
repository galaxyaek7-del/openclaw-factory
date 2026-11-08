#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Loop step: the factory runs its own doctor round every 6 hours, with nobody in the session (2026-11-08).

    python scripts/doctor_round_periodic.py --once      # prints one JSON line {action, detail}

Founder order 2026-11-08: "have the factory work periodically in your absence". The doctor round used to run only when a session was
open (the connector parts need the session and stay there). Everything that is LOCAL (loop failures, funnel, integrity, subtle audit,
sales path, pin destinations, doctrine gate, constitution wiring, regression gate, approvals) runs here by itself:
  * the full report is saved to data/doctor_round_latest.json (no secrets: the report only holds counts, names and file paths);
  * when the set of agent-owned PROBLEMS changes, the founder gets ONE short Telegram message (the bot already in use), never a repeat of
    the same set, never a message when everything is fine;
  * it changes nothing on any platform and spends nothing.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
STATE = ROOT / "data" / "doctor_periodic_state.json"
LATEST = ROOT / "data" / "doctor_round_latest.json"
MIN_GAP = timedelta(hours=6)


def _read(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _atomic(path, doc):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def problems_hash(problems):
    return hashlib.sha256("\n".join(sorted(problems)).encode("utf-8")).hexdigest()[:16]


def alert_text(problems):
    head = "المصنع (فحص دوري تلقائي): مشاكل على الوكيل تحتاج معالجة" if problems else ""
    return head + "\n" + "\n".join(f"- {p[:200]}" for p in problems[:6]) + (f"\n(+{len(problems) - 6} أخرى)" if len(problems) > 6 else "")


def default_sender(text):
    from channels import telegram_direct
    return telegram_direct.send_telegram_message(text)


def run_once(now=None, state_path=STATE, latest_path=LATEST, runner=None, sender=None):
    now = now or datetime.now(timezone.utc)
    state = _read(state_path)
    try:
        last = datetime.fromisoformat(str(state.get("last_run")).replace("Z", "+00:00"))
        if now - last < MIN_GAP:
            return {"action": "none", "detail": f"periodic doctor round ran {int((now - last).total_seconds() / 3600)} h ago; every 6 h"}
    except ValueError:
        pass
    if runner is None:
        import doctor_round
        runner = doctor_round.run
    rep = runner()
    problems = list(rep.get("agent_problems") or [])
    _atomic(latest_path, {"generated_at": now.isoformat(timespec="seconds"), "problems": problems,
                          "needs_founder": rep.get("needs_founder"), "report": {k: v for k, v in rep.items() if k not in ("agent_problems",)}})
    h = problems_hash(problems)
    sent = ""
    if problems and h != state.get("last_problem_hash"):
        try:
            res = (sender or default_sender)(alert_text(problems))
            sent = "; founder alerted" if (res or {}).get("sent", True) else f"; alert NOT sent ({str((res or {}).get('error'))[:60]})"
        except Exception as e:  # noqa: BLE001 an alert failure must never stop the round
            sent = f"; alert failed ({type(e).__name__})"
    _atomic(state_path, {"last_run": now.isoformat(timespec="seconds"), "last_problem_hash": h if problems else "", "last_problem_count": len(problems)})
    return {"action": "ran", "detail": f"periodic doctor round: {len(problems)} agent problem(s){sent}"}


def main():
    try:
        r = run_once()
    except Exception as e:  # noqa: BLE001
        r = {"action": "failed", "detail": f"{type(e).__name__}: {str(e)[:160]}"}
    sys.stdout.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()

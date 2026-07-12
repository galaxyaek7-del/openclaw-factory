#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenClaw Factory — pending_review/approved/ processor (Human-in-the-Loop
review model, HIGH_VALUE_EXECUTION_PLAN.md).

This is the "المصنع يكمل الفحص المزدوج + التوزيع + السجل بلا تدخل بشري
إضافي" step: everything BEFORE this (drafting via Groq, then human+Claude
review) is manual/periodic; everything from here on is mechanical and
deterministic — no judgment calls, just orchestration of already-existing,
already-tested CLIs (book_generator.py --json, distributor.py --json).

For every *.json file in pending_review/approved/:
  1. Feed it to `book_generator.py --json` (routes to generate_book_from_
     content() because it has a non-empty "chapters" list — ADR-022).
  2. If published, read the resulting books/_generation_log.jsonl record
     and feed it to `distributor.py --json` with dry_run always true
     (never live — going live requires FACTORY_LIVE_PUBLISH set elsewhere,
     completely independent of this script, same as every other
     distribution path in this factory).
  3. Move the source draft to completed/ (published) or rejected/ (Dual
     Inspection failed) with the full result attached for audit — never
     silently deleted either way.

Never live-publishes anything. Never modifies book_generator.py/
distributor.py/inspectors.py — pure orchestration of existing, unchanged
CLIs, same spawn+stdin-JSON/stdout-JSON pattern server.js already uses.

    python scripts/process_approved_drafts.py
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
APPROVED_DIR = _FACTORY_ROOT / "pending_review" / "approved"
COMPLETED_DIR = _FACTORY_ROOT / "pending_review" / "completed"
REJECTED_DIR = _FACTORY_ROOT / "pending_review" / "rejected"
GENERATION_LOG = _FACTORY_ROOT / "books" / "_generation_log.jsonl"


def _run_cli(script_name, payload, timeout=180):
    """Spawns a factory CLI (book_generator.py/distributor.py) exactly the
    way server.js does: write JSON to stdin, parse JSON from stdout."""
    proc = subprocess.run(
        [sys.executable, str(_FACTORY_ROOT / script_name), "--json"],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True, text=True, encoding="utf-8", timeout=timeout,
        cwd=str(_FACTORY_ROOT),
    )
    try:
        return json.loads(proc.stdout.strip())
    except (json.JSONDecodeError, ValueError):
        return {"success": False, "error": f"unparseable output: {proc.stdout!r} stderr={proc.stderr!r}"}


def _read_last_generation_record():
    if not GENERATION_LOG.exists():
        return None
    lines = GENERATION_LOG.read_text(encoding="utf-8").splitlines()
    if not lines:
        return None
    try:
        return json.loads(lines[-1])
    except (json.JSONDecodeError, ValueError):
        return None


def process_one(draft_path: Path) -> dict:
    draft = json.loads(draft_path.read_text(encoding="utf-8"))

    payload = {
        "title": draft.get("title", "Untitled"),
        "subtitle": draft.get("subtitle", ""),
        "chapters": draft.get("chapters", []),
        "price": draft.get("price", 9.99),
        "theme": draft.get("theme", "blue"),
        "author": draft.get("author", ""),
        "product_type": draft.get("product_type", "premium"),
    }
    gen_result = _run_cli("book_generator.py", payload)

    outcome = {
        "draft_file": draft_path.name,
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "generation": gen_result,
        "distribution": None,
    }

    if not gen_result.get("success") or not gen_result.get("published"):
        outcome["moved_to"] = "rejected"
        REJECTED_DIR.mkdir(parents=True, exist_ok=True)
        (REJECTED_DIR / draft_path.name).write_text(json.dumps(outcome, ensure_ascii=False, indent=2), encoding="utf-8")
        draft_path.unlink()
        return outcome

    record = _read_last_generation_record()
    if record and record.get("file") == gen_result.get("file"):
        dist_result = _run_cli("distributor.py", {"record": record, "dry_run": True})
        outcome["distribution"] = dist_result
    else:
        outcome["distribution"] = {"success": False, "error": "could not match the latest books/_generation_log.jsonl record"}

    outcome["moved_to"] = "completed"
    COMPLETED_DIR.mkdir(parents=True, exist_ok=True)
    (COMPLETED_DIR / draft_path.name).write_text(json.dumps(outcome, ensure_ascii=False, indent=2), encoding="utf-8")
    draft_path.unlink()
    return outcome


def main():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    APPROVED_DIR.mkdir(parents=True, exist_ok=True)
    drafts = sorted(APPROVED_DIR.glob("*.json"))
    results = [process_one(p) for p in drafts]
    print(json.dumps({"success": True, "processed": len(results), "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

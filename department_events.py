"""
Department Events (EOS Phase 2, Round 2, 2026-07-19) — the Python-side
twin of lib/department_events.js. Same shared JSONL correlation-index
envelope, same anti-duplication guarantee (emit at the real call site,
never a re-derivation scan), same twelve department slots (Researchers/
Customer Intelligence have no real emitter yet — honest, not fabricated).

No business data is ever duplicated here — only IDs and a one-line
summary; a reader follows ref_id/source_log back to the real record.
"""

import json
import os
import uuid
from datetime import datetime, timezone

FACTORY_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LOG_PATH = os.path.join(FACTORY_DIR, 'data', 'department_events.jsonl')

VALID_DEPARTMENTS = {
    'executive', 'market_intelligence', 'golden_hunter', 'pioneer', 'researchers',
    'production', 'publishing', 'finance', 'customer_intelligence', 'infrastructure',
    'recovery', 'ai_capability_manager',
}


def emit(department, event_type, ref_id=None, source_log=None, summary='', path=None):
    if department not in VALID_DEPARTMENTS:
        raise ValueError(f"department_events.emit: unknown department {department!r}")

    record = {
        "event_id": uuid.uuid4().hex[:16],
        "emitted_at": datetime.now(timezone.utc).isoformat(),
        "department": department,
        "event_type": event_type,
        "ref_id": ref_id,
        "source_log": source_log,
        "summary": summary,
    }
    target_path = path or DEFAULT_LOG_PATH
    try:
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        return {**record, "_log_failed": True, "_error": str(e)}
    return record


def read_events(path=None):
    target_path = path or DEFAULT_LOG_PATH
    if not os.path.exists(target_path):
        return []
    entries = []
    with open(target_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries

"""Daily read-only answer to one question: what stands between now and a sale?

Written for the loop, not for a person. The two operational failures of this
week -- twenty-four pins scheduled in the past, and a Gumroad session eleven
days old that nobody noticed -- were both invisible until someone opened a file
by hand. Neither needs a credential to detect. This script reads local state
only: it never contacts Gumroad, never reads .env, never writes to a listing.

Output is one JSON object (the loop's convention) plus a dated report under
reports/. Every finding names the exact command that clears it, so the only
thing left for a human is the approve/reject decision itself.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
REPORTS = ROOT / "reports"

SESSION_MAX_AGE_SECONDS = 3600


def _load(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def _age_seconds(recorded_at):
    if not recorded_at:
        return None
    try:
        stamp = datetime.fromisoformat(str(recorded_at).replace("Z", "+00:00"))
    except Exception:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return int((datetime.now(timezone.utc) - stamp).total_seconds())


def auth_blocker():
    state = _load(DATA / "gumroad_auth_state.json", {}) or {}
    age = _age_seconds(state.get("recorded_at"))
    stale = age is None or age > SESSION_MAX_AGE_SECONDS
    return {
        "check": "gumroad_session",
        "status": "STALE" if stale else "FRESH",
        "recorded_at": state.get("recorded_at"),
        "age_seconds": age,
        "max_age_seconds": SESSION_MAX_AGE_SECONDS,
        "clears_with": (
            "python -c \"import gumroad_auth_watch as g; print(g.poll()['status'])\""
            if stale else "none"
        ),
    }


def approval_blocker():
    """Latest record per product decides -- approvals are appended, never edited."""
    raw = _load(DATA / "publication_approvals.json", {}) or {}
    records = raw.get("approvals") if isinstance(raw, dict) else raw
    if isinstance(records, dict):
        records = [dict(rec, product_id=rec.get("product_id") or pid)
                   for pid, rec in records.items() if isinstance(rec, dict)]
    now = datetime.now(timezone.utc)
    latest = {}
    for rec in (records or []):
        if not isinstance(rec, dict):
            continue
        pid = rec.get("product_id") or rec.get("id")
        if not pid:
            continue
        try:
            when = datetime.fromisoformat(str(rec.get("approved_at") or "").replace("Z", "+00:00"))
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
        except Exception:
            when = datetime.min.replace(tzinfo=timezone.utc)
        if pid not in latest or when > latest[pid][0]:
            latest[pid] = (when, rec)
    approved, expired, refused = [], [], []
    for pid, (_when, rec) in latest.items():
        status = str(rec.get("status") or "").upper()
        if status and status != "APPROVED":
            refused.append(pid)
            continue
        try:
            exp = datetime.fromisoformat(str(rec.get("expires_at")).replace("Z", "+00:00"))
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
        except Exception:
            exp = None
        (approved if exp is None or exp > now else expired).append(pid)
    return {
        "check": "publication_approvals",
        "status": "OK" if approved else ("EXPIRED" if expired else "NONE"),
        "approved": sorted(approved),
        "expired": sorted(expired),
        "not_approved": sorted(refused),
        "clears_with": (
            "python scripts/approve_products.py --batch <batch> --only <ids> --yes"
            if not approved else "none"
        ),
    }


def registry_blocker():
    reg = _load(DATA / "product_registry.json", {}) or {}
    products = reg.get("products") or []
    states = {}
    for p in products:
        states[(p.get("primary_state") or "UNKNOWN")] = states.get(p.get("primary_state") or "UNKNOWN", 0) + 1
    ready = states.get("READY_FOR_AUTHORIZATION", 0)
    return {
        "check": "product_registry",
        "status": "OK" if ready else "NOTHING_READY",
        "products": len(products),
        "states": states,
        "clears_with": "python product_registry.py --rebuild",
    }


def pinterest_blocker():
    queue = _load(DATA / "pinterest_queue.json", {}) or {}
    items = queue.get("items") or queue.get("queue") or []
    ready = [i for i in items if str(i.get("status") or "").upper() in ("READY", "SCHEDULED")]
    rejected = [i for i in items if str(i.get("status") or "").upper() == "REJECTED"]
    now = datetime.now(timezone.utc)
    past = []
    for i in ready:
        when = i.get("scheduled_at") or i.get("scheduled_for")
        stamp = _age_seconds(when)
        if stamp is not None and stamp > 0:
            past.append(i.get("id") or i.get("pin_id") or when)
    return {
        "check": "pinterest_queue",
        "status": "OK" if ready and not past else ("SCHEDULED_IN_PAST" if past else "EMPTY"),
        "ready": len(ready),
        "rejected": len(rejected),
        "scheduled_in_past": len(past),
        "clears_with": "python scripts/pinterest_queue.py --start <YYYY-MM-DD> --hour 10",
    }


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass

    checks = [auth_blocker(), approval_blocker(), registry_blocker(), pinterest_blocker()]
    blocking = [c for c in checks if c["status"] not in ("OK", "FRESH")]
    verdict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "READ_ONLY",
        "ready_to_publish": not blocking,
        "blocking": [c["check"] for c in blocking],
        "checks": checks,
    }

    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / ("publish_readiness_%s.json" % datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    out.write_text(json.dumps(verdict, indent=1, ensure_ascii=False), encoding="utf-8")

    print(json.dumps({
        "action": "reported",
        "ready_to_publish": verdict["ready_to_publish"],
        "blocking": verdict["blocking"],
        "approved_products": len(checks[1]["approved"]),
        "pinterest_ready": checks[3]["ready"],
        "report": str(out.relative_to(ROOT)).replace("\\", "/") if ROOT in out.parents
        else str(out).replace("\\", "/"),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

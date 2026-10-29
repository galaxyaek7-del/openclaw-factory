"""Customer inquiry intake for every business arm (2026-10-29).

One schema and one review queue for inquiries about any offer, whichever
arm it belongs to. Prepared, not activated: the public site is served by
GitHub Pages, which cannot receive a POST, and the factory's own server is
bound to 127.0.0.1 and is not exposed. Until a receiver is chosen by the
founder, this module is used by the local server and by tests only, and the
dashboard reports intake as NOT CONNECTED.

Data: data/inquiries.jsonl (git-ignored: it holds names and e-mail
addresses). Each line is either an inquiry or a review event for one.
Only what a reply needs is stored: name, e-mail, the message, which offer it
is about, and the page it came from. No IP address, no user agent.
Retention: delete an inquiry 12 months after its last review event.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent
LEDGER = ROOT / "data" / "inquiries.jsonl"

ARMS = ("digital_products", "micro_b2b", "research_data_services", "affiliate_intelligence",
        "content_distribution", "ai_operations", "productized_ai_services", "childrens_media_studio")
LIMITS = {"name": 120, "email": 200, "message": 4000, "offer_id": 80, "source_page": 300, "company": 120}
EMAIL = re.compile(r"^[^\s@<>]+@[^\s@<>]+\.[A-Za-z]{2,}$")
URL = re.compile(r"https?://|www\.", re.I)
MIN_FILL_SECONDS = 3          # a form submitted faster than this was not typed by a person
MAX_LINKS = 2
DUPLICATE_WINDOW = timedelta(hours=24)
OUTCOMES = ("REPLIED", "QUALIFIED", "NOT_A_FIT", "SPAM", "CLOSED")


class InvalidInquiry(ValueError):
    def __init__(self, errors):
        super().__init__("; ".join(errors))
        self.errors = errors


def _now():
    return datetime.now(timezone.utc)


def _clean(v):
    s = str(v or "").replace("\x00", "").strip()
    return re.sub(r"[\r\t]+", " ", s)


def validate(payload: Dict[str, Any], now: Optional[datetime] = None) -> Dict[str, Any]:
    """Normalised inquiry, or InvalidInquiry listing every problem.

    Spam signals do not raise: the record is kept and marked spam, so a false
    positive can still be found in review."""
    now = now or _now()
    errors = []
    if not isinstance(payload, dict):
        raise InvalidInquiry(["payload must be an object"])
    rec = {k: _clean(payload.get(k)) for k in ("name", "email", "message", "arm", "offer_id", "source_page", "company")}
    for k in ("name", "email", "message", "arm"):
        if not rec[k]:
            errors.append("%s is required" % k)
    for k, n in LIMITS.items():
        if len(rec.get(k) or "") > n:
            errors.append("%s exceeds %d characters" % (k, n))
    if rec["email"] and not EMAIL.match(rec["email"]):
        errors.append("email is not a valid address")
    if rec["arm"] and rec["arm"] not in ARMS:
        errors.append("arm is not a known business arm")
    if not payload.get("consent_to_reply"):
        errors.append("consent_to_reply must be true (the address is used only to answer this inquiry)")
    if errors:
        raise InvalidInquiry(errors)
    spam = []
    if _clean(payload.get("website")):           # honeypot field, hidden from people
        spam.append("honeypot filled")
    if len(URL.findall(rec["message"])) > MAX_LINKS:
        spam.append("more than %d links" % MAX_LINKS)
    started = payload.get("form_started_at")
    try:
        if started and (now - datetime.fromisoformat(str(started).replace("Z", "+00:00"))).total_seconds() < MIN_FILL_SECONDS:
            spam.append("submitted in under %d seconds" % MIN_FILL_SECONDS)
    except ValueError:
        pass
    rec["email"] = rec["email"].lower()
    rec["received_at"] = now.isoformat(timespec="seconds")
    rec["inquiry_id"] = "INQ-" + hashlib.sha256(
        (rec["email"] + rec["message"] + rec["received_at"]).encode("utf-8")).hexdigest()[:12]
    rec["spam_signals"] = spam
    rec["status"] = "SPAM_SUSPECTED" if spam else "NEW"
    return rec


def _read(path):
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def _append(path, rec):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def submit(payload: Dict[str, Any], ledger=None, now: Optional[datetime] = None) -> Dict[str, Any]:
    """Validate and store. A repeat of the same message from the same address
    inside 24 hours is not stored again."""
    ledger = ledger or LEDGER
    rec = validate(payload, now)
    t = datetime.fromisoformat(rec["received_at"])
    for old in _read(ledger):
        if old.get("record") != "inquiry" or old.get("email") != rec["email"] or old.get("message") != rec["message"]:
            continue
        if t - datetime.fromisoformat(old["received_at"]) < DUPLICATE_WINDOW:
            return {"stored": False, "duplicate_of": old["inquiry_id"]}
    _append(ledger, {"record": "inquiry", **rec})
    return {"stored": True, "inquiry_id": rec["inquiry_id"], "status": rec["status"]}


def review(inquiry_id: str, outcome: str, note: str = "", ledger=None, now: Optional[datetime] = None) -> Dict[str, Any]:
    ledger = ledger or LEDGER
    if outcome not in OUTCOMES:
        raise ValueError("outcome must be one of %s" % (OUTCOMES,))
    if not any(r.get("record") == "inquiry" and r.get("inquiry_id") == inquiry_id for r in _read(ledger)):
        raise KeyError(inquiry_id)
    ev = {"record": "review", "inquiry_id": inquiry_id, "outcome": outcome, "note": _clean(note)[:500],
          "at": (now or _now()).isoformat(timespec="seconds")}
    _append(ledger, ev)
    return ev


def queue(ledger=None) -> Dict[str, Any]:
    """Inquiries awaiting a person, newest first, with counts per arm. No e-mail
    addresses in the summary (the dashboard shows it)."""
    ledger = ledger or LEDGER
    rows = _read(ledger)
    reviewed = {}
    for r in rows:
        if r.get("record") == "review":
            reviewed[r["inquiry_id"]] = r["outcome"]
    inquiries = [r for r in rows if r.get("record") == "inquiry"]
    pending = [r for r in inquiries if r["inquiry_id"] not in reviewed]
    by_arm = {}
    for r in inquiries:
        by_arm.setdefault(r["arm"], {"total": 0, "pending": 0, "qualified": 0})
        by_arm[r["arm"]]["total"] += 1
        if r["inquiry_id"] not in reviewed:
            by_arm[r["arm"]]["pending"] += 1
        if reviewed.get(r["inquiry_id"]) == "QUALIFIED":
            by_arm[r["arm"]]["qualified"] += 1
    return {"total": len(inquiries), "pending": len(pending),
            "pending_spam_suspected": sum(1 for r in pending if r["status"] == "SPAM_SUSPECTED"),
            "by_arm": by_arm,
            "pending_items": [{"inquiry_id": r["inquiry_id"], "arm": r["arm"], "offer_id": r.get("offer_id"),
                               "received_at": r["received_at"], "status": r["status"]}
                              for r in sorted(pending, key=lambda x: x["received_at"], reverse=True)[:20]]}


def readiness() -> Dict[str, Any]:
    """Whether a public visitor's inquiry can reach this queue today."""
    return {
        "schema_and_queue": "IMPLEMENTED (inquiry_intake.py, tests/test_inquiry_intake.py)",
        "public_receiver": "NOT CONNECTED: GitHub Pages answers 405 to a POST; the factory server listens on 127.0.0.1 only",
        "email_fallback": "contact.html relays to the founder's inbox via formsubmit.co; whether that relay was activated is UNKNOWN; it bypasses this queue",
        "notification": "NOT CONNECTED: Telegram has no chat id; pending inquiries are shown on the dashboard",
        "founder_decision": "choose a receiver: (a) a free form service that forwards to the founder's inbox only, or (b) a free serverless endpoint that writes to this queue; both need an account in the founder's name",
    }

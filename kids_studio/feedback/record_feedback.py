#!/usr/bin/env python3
"""Record one parent's answers about a private animatic viewing (see PROTOCOL.md).

Privacy by construction: no field for a name or contact; free-text answers that
look like an e-mail address or a phone number are refused; nothing about a child
except an age band. The ledger is data/kids_feedback.jsonl (git-ignored).

    python kids_studio/feedback/record_feedback.py --episode ep01 --age-band 4-5 --watched yes \\
        --alone with_me --completion all --language right --next yes \\
        --issues "none" --where "YouTube Kids"
    python kids_studio/feedback/record_feedback.py --summary
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "data" / "kids_feedback.jsonl"

CHOICES = {
    "age_band": ("4-5", "6-8"),
    "watched": ("yes", "no"),
    "alone": ("yes", "with_me", "no"),
    "completion": ("all", "half", "stopped_early", "did_not_watch"),
    "language": ("too_hard", "right", "too_easy"),
    "next": ("yes", "maybe", "no"),
}
CONTACT = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+|(?:\+?\d[\s().-]?){7,}\d")
MAX_TEXT = 500


class Refused(ValueError):
    pass


def make_record(episode, answers, issues="", where="", now=None):
    for k, allowed in CHOICES.items():
        if answers.get(k) not in allowed:
            raise Refused("%s must be one of %s" % (k, ", ".join(allowed)))
    if answers["watched"] == "no" and answers["completion"] != "did_not_watch":
        raise Refused("completion must be did_not_watch when the child did not watch")
    texts = {"issues": (issues or "").strip(), "where": (where or "").strip()}
    for k, v in texts.items():
        if len(v) > MAX_TEXT:
            raise Refused("%s is longer than %d characters" % (k, MAX_TEXT))
        if CONTACT.search(v):
            raise Refused("%s looks like it contains contact details; record the answer without them" % k)
    if not re.fullmatch(r"ep\d{2}", episode or ""):
        raise Refused("episode must look like ep01")
    at = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    rec = {"episode": episode, "recorded_at": at, **{k: answers[k] for k in CHOICES}, **texts}
    rec["feedback_id"] = "KF-" + hashlib.sha256(json.dumps(rec, sort_keys=True).encode()).hexdigest()[:10]
    return rec


def append(rec, ledger=LEDGER):
    ledger = Path(ledger)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def summary(ledger=LEDGER):
    rows = []
    try:
        for line in Path(ledger).read_text(encoding="utf-8").splitlines():
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    except OSError:
        pass
    out = {"responses": len(rows)}
    for k in CHOICES:
        out[k] = {c: sum(1 for r in rows if r.get(k) == c) for c in CHOICES[k]}
    n = len(rows)
    ok = out["alone"]["yes"] + out["alone"]["with_me"]
    out["criteria"] = {
        "continue": n >= 3 and ok * 2 >= n,
        "note": "continue needs >= 3 responses with at least half 'yes' or 'with_me' to question 1 and no "
                "unfixable unsuitable element (read the issues answers yourself)",
    }
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--episode", default="ep01")
    ap.add_argument("--age-band")
    ap.add_argument("--watched")
    ap.add_argument("--alone")
    ap.add_argument("--completion")
    ap.add_argument("--language")
    ap.add_argument("--next")
    ap.add_argument("--issues", default="")
    ap.add_argument("--where", default="")
    ap.add_argument("--ledger", default=str(LEDGER))
    a = ap.parse_args(argv)
    if a.summary:
        print(json.dumps(summary(a.ledger), indent=1))
        return 0
    answers = {"age_band": a.age_band, "watched": a.watched, "alone": a.alone, "completion": a.completion,
               "language": a.language, "next": a.next}
    try:
        rec = make_record(a.episode, answers, a.issues, a.where)
    except Refused as exc:
        print(json.dumps({"refused": str(exc)}))
        return 1
    append(rec, a.ledger)
    print(json.dumps({"recorded": rec["feedback_id"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

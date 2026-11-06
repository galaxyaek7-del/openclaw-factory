#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Offline A/B/C evaluation of the Scout prompt (2026-11-06). Publishes nothing, writes only reports/ and data/scout_eval.json.

    python scripts/scout_eval.py --run            # calls the model (cents), writes data/scout_eval.json + reports/SCOUT_EVAL.md
    python scripts/scout_eval.py --report         # re-renders the report from the saved data (no model calls)

Variants:  A  current prompt (book / KDP, price >= $30) + the raw trend headlines the daily chain feeds it today;
           B  v2 prompt (spreadsheet tools, $9-49, may decline) + the SAME headlines;
           C  v2 prompt + demand-grounded inputs (real buyer questions / market-evidence rows).
Verdict per brief: PASS only if (1) the contract parses, (2) it is a fit for the CURRENT business (price 9-49 and the title
describes a workbook/tool, not a book/journal), and (3) the chain's QA agent says PASS. A v2 decline on a headline with no
money decision behind it is counted separately as DECLINED (a correct refusal, not a pass and not a failure).
The deterministic checks decide; QA is an extra gate, not the judge of record. Nothing here changes the live chain.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
TAG = os.environ.get("SCOUT_EVAL_TAG", "")
DATA_OUT = ROOT / "data" / (f"scout_eval_{TAG}.json" if TAG else "scout_eval.json")
REPORT = ROOT / "reports" / (f"SCOUT_EVAL_{TAG}.md" if TAG else "SCOUT_EVAL.md")

TOOL_WORDS = re.compile(r"\b(workbook|spreadsheet|calculator|tracker|planner|template|model|dashboard|tool|toolkit|budget|estimator|pricing|forecast|worksheet|optimizer|analyzer|estimator|simulator|scorecard|allocator|decision)\b", re.I)
BOOK_WORDS = re.compile(r"\b(journal|diary|coloring|colouring|novel|guide to|ebook|e-book|kdp|cookbook|devotional|affirmations?)\b", re.I)


def read_trends(n_groups=10, per_group=3):
    """Real raw headlines as the daily chain sees them (OPPORTUNITIES.md), distinct, newest first, grouped like a day's slice."""
    txt = (ROOT / "OPPORTUNITIES.md").read_text(encoding="utf-8", errors="ignore")
    seen, items = set(), []
    for m in re.finditer(r"^- \[(\d{4}-\d{2}-\d{2})T[^\]]*\] (.+?) — ", txt, re.M):
        t = m.group(2).strip()
        if t not in seen:
            seen.add(t)
            items.append(t)
    items = items[-(n_groups * per_group):]
    return ["، ".join(items[i * per_group:(i + 1) * per_group]) for i in range(n_groups) if items[i * per_group:(i + 1) * per_group]]


def read_demand_inputs(n=10):
    """Demand-grounded inputs: real rows from data/market_evidence.jsonl, reduced to the buyer problem (no quotes of people)."""
    out, seen = [], set()
    p = ROOT / "data" / "market_evidence.jsonl"
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines() if p.exists() else []:
        try:
            d = json.loads(line)
        except ValueError:
            continue
        niche = str(d.get("niche") or "").strip()
        ev = str(d.get("event_type") or "")
        key = (niche, ev)
        if not niche or key in seen:
            continue
        seen.add(key)
        out.append(f"Market evidence ({ev.replace('_', ' ')}): buyers are searching for and paying for '{niche}'.")
    # Real buyer questions already seen in the factory's own demand files are NOT invented here; when fewer than n exist, we use fewer.
    return out[:n]


def build_inputs():
    rows = []
    for i, t in enumerate(read_trends()):
        rows.append({"id": f"A{i+1}", "variant": "A", "input": t})
        rows.append({"id": f"B{i+1}", "variant": "B", "input": t})
    for i, t in enumerate(read_demand_inputs()):
        rows.append({"id": f"C{i+1}", "variant": "C", "input": t})
    return rows


def node(cmd, payload):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
        path = f.name
    try:
        p = subprocess.run(["node", str(ROOT / "scripts" / "scout_eval_prompts.js"), cmd, path], cwd=str(ROOT), capture_output=True,
                           text=True, encoding="utf-8", timeout=60)
        if p.returncode != 0:
            raise RuntimeError(p.stderr[:300])
        return json.loads(p.stdout)
    finally:
        os.unlink(path)


def fit(brief):
    """Deterministic fit for the CURRENT business: a priced $9-49 tool, not a book."""
    if not brief:
        return False, "no parseable brief"
    price = brief.get("price")
    if not (isinstance(price, (int, float)) and 9 <= price <= 49):
        return False, f"price {price} outside $9-49"
    title = str(brief.get("title") or "")
    if BOOK_WORDS.search(title) and not TOOL_WORDS.search(title):
        return False, "title reads as a book/journal"
    if not TOOL_WORDS.search(title + " " + str(brief.get("topic") or "")):
        return False, "no tool/workbook wording"
    return True, "ok"


def call(system, user, max_tokens=3000, attempts=3):
    """One model call with spaced retries (the host network and the provider both drop requests now and then)."""
    import time
    from ai_capability import orchestrator
    import book_generator
    if os.environ.get("SCOUT_EVAL_MODEL"):
        book_generator.GROQ_MODEL = os.environ["SCOUT_EVAL_MODEL"]  # evaluation only: never changes the live default
    last = None
    for k in range(attempts):
        try:
            out = orchestrator.generate("analysis", system, user, max_tokens=max_tokens, timeout=90, retries=2)["content"]
            if out and out.strip():
                return out
            last = RuntimeError("empty answer")
        except Exception as e:  # noqa: BLE001
            last = e
        time.sleep(4 * (k + 1))
    raise last


def QA_SYS(variant, v1_system):
    """A is judged by the live v1 QA persona; B and C by the reviewer matched to the v2 brief format."""
    if variant == "A":
        return v1_system
    return subprocess.run(["node", "-e", "process.stdout.write(require('./lib/scout_brief_v2').QA_V2_SYSTEM)"], cwd=str(ROOT),
                          capture_output=True, text=True, encoding="utf-8").stdout


def run():
    inputs = build_inputs()
    pr = node("prompts", inputs)
    texts = []
    for r in pr["rows"]:
        try:
            txt, err = call(r["system"], r["user"]), None
        except Exception as e:  # noqa: BLE001 never print the key; message is trimmed
            txt, err = "", type(e).__name__
        texts.append({"id": r["id"], "variant": r["variant"], "text": txt, "error": err})
    parsed = node("parse", texts)
    by_id = {t["id"]: t for t in texts}
    # QA for every parseable brief
    qa_in = []
    for p in parsed:
        if p["qa_user"]:
            try:
                qa_text = call(QA_SYS(by_id[p["id"]]["variant"], pr["qa_system"]), p["qa_user"], max_tokens=1500)
            except Exception as e:  # noqa: BLE001
                qa_text = ""
            qa_in.append({"id": p["id"], "variant": by_id[p["id"]]["variant"], "text": by_id[p["id"]]["text"], "qa_text": qa_text})
    qa_parsed = {q["id"]: q for q in node("parse", [dict(x) for x in qa_in])} if qa_in else {}
    rows = []
    for p in parsed:
        t = by_id[p["id"]]
        ok_fit, why = fit(p["brief"])
        qa = (qa_parsed.get(p["id"]) or {}).get("qa_parse")
        verdict = ("DECLINED" if p["declined"] else
                   "NO_OUTPUT" if t["error"] else
                   "CONTRACT_FAIL" if not p["brief"] else
                   "NOT_FIT" if not ok_fit else
                   "QA_NO_ANSWER" if not qa else
                   "QA_REVISE" if qa.get("qa_verdict") != "PASS" else "PASS")
        rows.append({"id": p["id"], "variant": t["variant"], "input": next(i["input"] for i in inputs if i["id"] == p["id"]),
                     "verdict": verdict, "fit_reason": why, "title": (p["brief"] or {}).get("title"), "price": (p["brief"] or {}).get("price"),
                     "qa": qa, "error": t["error"]})
    doc = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "rows": rows}
    DATA_OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    return doc


def summarize(rows):
    out = {}
    for v in "ABC":
        rs = [r for r in rows if r["variant"] == v]
        n = len(rs)
        c = {k: sum(1 for r in rs if r["verdict"] == k) for k in ("PASS", "DECLINED", "QA_REVISE", "QA_NO_ANSWER", "NOT_FIT", "CONTRACT_FAIL", "NO_OUTPUT")}
        answered = n - c["DECLINED"] - c["NO_OUTPUT"] - c["QA_NO_ANSWER"]
        out[v] = {"n": n, **c, "pass_rate_of_all": round(c["PASS"] / n, 2) if n else None,
                  "pass_rate_of_answered": round(c["PASS"] / answered, 2) if answered else None}
    return out


def render(doc):
    s = summarize(doc["rows"])
    L = [f"# Scout prompt evaluation ({doc['at']})", "",
         "Offline, nothing published. A = current prompt on raw headlines; B = v2 prompt on the same headlines; C = v2 prompt on demand-grounded inputs.",
         "PASS = parses + fits the $9-49 tool business + the chain's QA agent says PASS.", "",
         "| Variant | n | PASS | DECLINED | QA_REVISE | QA_NO_ANSWER | NOT_FIT | CONTRACT_FAIL | NO_OUTPUT | pass of all | pass of answered |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for v, x in s.items():
        L.append(f"| {v} | {x['n']} | {x['PASS']} | {x['DECLINED']} | {x['QA_REVISE']} | {x['QA_NO_ANSWER']} | {x['NOT_FIT']} | {x['CONTRACT_FAIL']} | {x['NO_OUTPUT']} | {x['pass_rate_of_all']} | {x['pass_rate_of_answered']} |")
    L += ["", "## Rows", ""]
    for r in doc["rows"]:
        L.append(f"- {r['id']} {r['verdict']}: {str(r['input'])[:90]} -> {r['title']} (${r['price']}) {('| ' + r['fit_reason']) if r['verdict'] == 'NOT_FIT' else ''}")
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    return s


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--run" in argv:
        doc = run()
    elif "--report" in argv:
        doc = json.loads(DATA_OUT.read_text(encoding="utf-8"))
    else:
        sys.stdout.write(__doc__)
        return 0
    s = render(doc)
    sys.stdout.buffer.write((json.dumps(s, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

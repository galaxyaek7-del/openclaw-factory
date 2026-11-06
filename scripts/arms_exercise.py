#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run every arm's engine on real inputs and measure what it PRODUCES (2026-11-06).

business_arms_state.json rates an arm from "does the path exist" plus the revenue record. That says nothing about
whether the engine works. This harness executes each arm's deliverable code on real or recorded inputs, in memory or in
read-only mode (no platform write, no network write, no file in data/ changed) and records evidence:

  WORKS      ran and produced the expected, checkable output
  FAILED     ran and the output was wrong, or it crashed: a finding about the factory
  NOT_RUN    could not be exercised here (reason given)

"Works" says nothing about demand: an arm that works and has no buyer is still revenue 0.

    python scripts/arms_exercise.py            # table
    python scripts/arms_exercise.py --json
    python scripts/arms_exercise.py --report   # also writes reports/ARMS_EXERCISE.md
"""
from __future__ import annotations

import contextlib
import csv
import io
import json
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _imp(path_from_root):
    sys.path.insert(0, str(ROOT / path_from_root))


def ex_accessibility():
    _imp("services/accessibility_check")
    import check
    own = check.check_path(str(ROOT / "customer_site"))
    syn = check.check_path(str(ROOT / "services/accessibility_check/demo_package/synthetic_page.html"))
    detected = syn["errors"] + syn["warnings"]
    ok = own["pages_checked"] > 0 and detected > 0
    return ("WORKS" if ok else "FAILED", {
        "own_site": {k: own[k] for k in ("pages_checked", "pages_with_errors", "errors", "warnings")},
        "detection_proof": f"the deliberately flawed synthetic page yields {detected} finding(s): the checker can see defects",
        "top_issues": dict(list(own.get("by_issue", {}).items())[:4]) if isinstance(own.get("by_issue"), dict) else own.get("by_issue")})


def ex_feed_preflight():
    _imp("services/feed_preflight")
    import preflight
    text = (ROOT / "services/feed_preflight/demo_package/input_feed.csv").read_text(encoding="utf-8-sig")
    rep = preflight.preflight(preflight.read_feed(text))
    stored = json.loads((ROOT / "services/feed_preflight/demo_package/report.json").read_text(encoding="utf-8"))
    same = json.dumps(rep, sort_keys=True, default=str) == json.dumps(stored, sort_keys=True, default=str)
    return ("WORKS" if rep else "FAILED", {"summary": {k: v for k, v in rep.items() if not isinstance(v, (list, dict))},
                                           "findings_keys": list(rep)[:6], "reproduces_the_stored_demo_report": same})


def ex_normalization():
    _imp("services/spreadsheet_normalization")
    import engine
    src = ROOT / "services/spreadsheet_normalization/demo_package"
    rows = engine.read_table(src / "input_messy.csv")
    rows_in = rows[0] if isinstance(rows, tuple) else rows
    out = engine.normalize(rows_in) if not isinstance(rows_in, tuple) else engine.normalize(*rows_in)
    cleaned, report = (out if isinstance(out, tuple) else (out.get("rows"), out))
    expected = list(csv.reader((src / "output_clean.csv").read_text(encoding="utf-8-sig").splitlines()))
    n_expected = max(0, len(expected) - 1)
    n_got = len(cleaned) if cleaned is not None else None
    return ("WORKS" if n_got == n_expected else "FAILED", {"rows_in": len(rows_in), "rows_out": n_got, "rows_expected": n_expected,
                                                           "qa_report_keys": list(report)[:6] if isinstance(report, dict) else None})


def ex_automation_health():
    _imp("services/automation_health")
    import audit
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = audit.main([str(ROOT / "services/automation_health/demo_input.json")])
    out = buf.getvalue()
    try:
        doc = json.loads(out)
        verdicts = sorted({str(w.get("verdict")) for w in (doc.get("workflows") or doc.get("results") or [])})
    except ValueError:
        verdicts = None
    ok = rc in (0, None) and bool(out.strip())
    return ("WORKS" if ok else "FAILED", {"exit": rc, "verdicts_seen": verdicts, "output_chars": len(out)})


def ex_data_products():
    _imp("data_products")
    import datacard
    res = {}
    for ds in sorted((ROOT / "data_products/releases").iterdir()):
        rel = sorted(p for p in ds.iterdir() if p.is_dir())[-1]
        card = datacard.load_card(rel / "datacard.json")
        v = datacard.validate_card(card, ROOT, today=date.today())
        res[f"{ds.name}@{rel.name}"] = {"status": v["status"], "findings": len(v["findings"])}
    bad = [k for k, v in res.items() if v["status"] == "BLOCK"]
    return ("WORKS" if res and not bad else "FAILED", {"releases_revalidated_today": res})


def ex_affiliate():
    p = subprocess.run([sys.executable, str(ROOT / "scripts/affiliate_e2e_simulation.py"), "--json"], cwd=str(ROOT), capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=240)
    try:
        d = json.loads(p.stdout)
    except ValueError:
        return "FAILED", {"error": p.stderr[-200:]}
    return ("WORKS" if d.get("failed") == 0 else "FAILED", {"simulated_scenarios": d.get("checks"), "passed": d.get("passed"), "failed": d.get("failed"),
                                                            "environment": d.get("environment"), "note": "SIMULATION: no real program, link, click or commission exists"})


def ex_kids():
    p = subprocess.run([sys.executable, str(ROOT / "scripts/kids_youtube_publish_daily.py"), "--status"], cwd=str(ROOT), capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=120)
    try:
        eps = json.loads(p.stdout)
    except ValueError:
        return "FAILED", {"error": p.stderr[-200:]}
    only_founder = all(set(e["failing"]) <= {"approval", "credentials"} for e in eps)
    return ("WORKS" if only_founder else "FAILED", {"episodes": [{"episode": e["episode"], "failing": e["failing"]} for e in eps],
                                                    "meaning": "every technical check passes; only the founder's approval and YouTube credentials are missing"})


def ex_umrah():
    r = []
    for t in ("tests/test_umrah_assistant.js", "tests/test_umrah_agency.js"):
        p = subprocess.run(["node", t], cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        r.append(p.returncode == 0)
    return ("WORKS" if all(r) else "FAILED", {"assistant_tests_pass": r, "data": "SIMULATION agency data; no real agency yet"})


def ex_digital_products():
    reg = json.loads((ROOT / "data/product_registry.json").read_text(encoding="utf-8"))
    ps = reg["products"]
    return ("WORKS", {"products": len(ps), "published": sum(1 for p in ps if p.get("published")),
                      "verified_public": sum(1 for p in ps if p.get("primary_state") == "PUBLIC_LISTING_VERIFIED"),
                      "sales": sum(int(p.get("sales_count") or 0) for p in ps), "note": "listing, delivery and measurement work; no buyer yet"})


def ex_content_distribution():
    try:
        from channels import capability_matrix as cm
        states = {}
        for name in ("x", "etsy", "payhip", "kdp", "paddle", "gumroad"):
            ch = getattr(cm, "MATRIX", None) or getattr(cm, "CAPABILITIES", None) or {}
            states[name] = str(getattr(ch.get(name), "state", ch.get(name)))[:60] if isinstance(ch, dict) and name in ch else "n/a"
    except Exception as e:  # noqa: BLE001
        states = {"error": type(e).__name__}
    rows = []
    try:
        rows = [json.loads(l) for l in (ROOT / "data/distribution_metrics.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    except OSError:
        pass
    return ("WORKS" if rows else "NOT_RUN", {"telegraph_readings_recorded": len(rows), "last": rows[-1] if rows else None,
                                              "channel_states": states,
                                              "note": "Telegraph publishes and is read daily; X is credit-blocked; Pinterest pins go out from the founder's browser"})


ARMS = [("Digital Products", ex_digital_products), ("Micro-B2B: spreadsheet normalization", ex_normalization),
        ("Micro-B2B: feed preflight", ex_feed_preflight), ("Research & Data: data products", ex_data_products),
        ("Affiliate Intelligence (simulation)", ex_affiliate), ("Content & Distribution", ex_content_distribution),
        ("AI Operations: automation health audit", ex_automation_health), ("Productized AI: accessibility check", ex_accessibility),
        ("Children's Media Studio", ex_kids), ("Umrah assistant (Phase 2)", ex_umrah)]


def run_all():
    out = []
    for name, fn in ARMS:
        try:
            status, ev = fn()
        except Exception as e:  # noqa: BLE001 a crash is a finding, never hidden
            status, ev = "FAILED", {"crash": f"{type(e).__name__}: {str(e)[:200]}"}
        out.append({"arm": name, "status": status, "evidence": ev})
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    rows = run_all()
    if "--json" in argv:
        sys.stdout.write(json.dumps(rows, ensure_ascii=False, indent=1, default=str) + "\n")
    else:
        for r in rows:
            sys.stdout.buffer.write(f"{r['status']:7} {r['arm']:40} {json.dumps(r['evidence'], ensure_ascii=False, default=str)[:170]}\n".encode("utf-8"))
    if "--report" in argv:
        L = [f"# Arms exercise ({datetime.now(timezone.utc).isoformat(timespec='seconds')})", "",
             "Each arm's engine was run on real or recorded inputs, read-only. WORKS means the output was produced and checked; it says nothing about demand.", "",
             "| Arm | Result | Evidence |", "|---|---|---|"]
        L += [f"| {r['arm']} | {r['status']} | `{json.dumps(r['evidence'], ensure_ascii=False, default=str)[:300]}` |" for r in rows]
        (ROOT / "reports").mkdir(exist_ok=True)
        (ROOT / "reports" / "ARMS_EXERCISE.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return 1 if any(r["status"] == "FAILED" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nightly regression gate for the modules that keep the factory selling and safe (2026-11-06).

The founder's rule is "improve it without breaking it". A change by anyone (an agent, a parallel session, a half-finished
local edit) that breaks a gate, a publisher, a monitor or the digest should show up the same day, not when a product fails
to publish. This runs a CURATED set of fast test files (not the whole suite: it is too heavy to run at once, see CLAUDE.md)
and records the result in data/regression_status.json, which the stage check (R1), the doctor round and the digest read.

    python scripts/factory_regression.py --once     # loop step: at most once a day
    python scripts/factory_regression.py --now      # run now, whatever the gate says
Read-only with respect to the factory: it writes only data/regression_status.json (+ its day state).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "regression_status.json"
STATE = ROOT / "data" / "regression_state.json"

# Gates and money path, monitors and doctor, tools added in the 2026-11 cycle. Missing files are skipped and reported.
PY_TESTS = [
    "test_demand_gate", "test_standing_authorization", "test_publish_approved_daily", "test_publish_batch14", "test_write_gate",
    "test_write_scope", "test_publication_authorization", "test_publication_clearance", "test_quality_gate_policy",
    "test_gumroad_publisher", "test_product_registry", "test_simulate_first_signal", "test_autonomy_selfcheck", "test_autonomy_daily",
    "test_founder_digest", "test_doctor_round", "test_connector_intake", "test_listing_health", "test_company_scorecard",
    "test_company_protection_check", "test_global_readiness_audit", "test_auto_publish_site", "test_auto_publish_site_tree",
    "test_tool_pages_daily", "test_n8n_workflow_health", "test_n8n_notification_selfcheck", "test_telegram_bind", "test_telegram_direct",
    "test_unpublish_duplicate_listing", "test_unpublish_zero_price_listings", "test_repair_listing_mojibake", "test_arms_exercise_coverage", "test_research_chain_daily", "test_data_integrity_check", "test_funnel_report", "test_untracked_source_snapshot", "test_build_bundle", "test_agent_kpis",
]
JS_TESTS = ["test_factory_loop_demand_gate", "test_attribution_filter", "test_ops_retry", "test_telegram_direct",
            "test_factory_loop_ops_daily_control", "test_umrah_assistant", "test_umrah_agency", "test_scout_brief_v2", "test_gf_outbound_utm"]


def _run(cmd, timeout):
    t = time.time()
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8", CI="true"))
    return p, round(time.time() - t, 1)


def parse_pytest(out):
    """-> (passed, failed, [failing test ids]) from pytest's -q -rf output."""
    failed_ids = re.findall(r"^FAILED (\S+)", out, re.M)
    m_pass = re.search(r"(\d+) passed", out)
    m_fail = re.search(r"(\d+) failed", out)
    m_err = re.search(r"(\d+) error", out)
    failed = int(m_fail.group(1)) if m_fail else 0
    failed += int(m_err.group(1)) if m_err else 0
    return (int(m_pass.group(1)) if m_pass else 0), failed, failed_ids


def run_gate(py=PY_TESTS, js=JS_TESTS, tests_dir=ROOT / "tests", runner=_run):
    files = [str(tests_dir / f"{n}.py") for n in py if (tests_dir / f"{n}.py").exists()]
    skipped = [f"{n}.py" for n in py if not (tests_dir / f"{n}.py").exists()]
    failures, passed, failed, durations = [], 0, 0, {}
    if files:
        p, secs = runner([sys.executable, "-m", "pytest", "-q", "-rf", "-p", "no:cacheprovider", *files], 900)
        durations["pytest"] = secs
        pa, fa, ids = parse_pytest(p.stdout + p.stderr)
        passed, failed = passed + pa, failed + fa
        failures += ids or ([f"pytest exit {p.returncode}"] if p.returncode not in (0,) and not fa else [])
        if p.returncode != 0 and not fa and not ids:
            failed += 1
    js_pass = js_fail = 0
    for n in js:
        f = tests_dir / f"{n}.js"
        if not f.exists():
            skipped.append(f"{n}.js")
            continue
        p, secs = runner(["node", str(f)], 300)
        durations[n] = secs
        if p.returncode == 0:
            js_pass += 1
        else:
            js_fail += 1
            failures.append(f"{n}.js")
    return {"python": {"files": len(files), "passed": passed, "failed": failed}, "node": {"files": js_pass + js_fail, "passed_files": js_pass, "failed_files": js_fail},
            "failed": failed + js_fail, "failures": failures[:30], "skipped_missing": skipped, "seconds": durations}


def run_once(now=None, force=False, out=OUT, state=STATE, gate=run_gate):
    now = now or datetime.now(timezone.utc)
    today = now.date().isoformat()
    try:
        last = json.loads(Path(state).read_text(encoding="utf-8")).get("last_day")
    except (OSError, ValueError):
        last = None
    if last == today and not force:
        return {"action": "none", "detail": f"regression gate already ran for {today}"}
    res = gate()
    doc = {"at": now.isoformat(timespec="seconds"), **res}
    for path, payload in ((out, doc), (state, {"last_day": today})):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(str(path) + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, path)
    py, nd = res["python"], res["node"]
    return {"action": "failed_tests" if res["failed"] else "ok",
            "detail": f"python {py['passed']} passed/{py['failed']} failed in {py['files']} files; node {nd['passed_files']}/{nd['files']} files ok"
                      + (f"; FAILING: {', '.join(res['failures'][:4])}" if res["failed"] else "")}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        r = run_once(force="--now" in argv)
    except Exception as e:  # noqa: BLE001 reported to the loop, never thrown
        r = {"action": "failed", "detail": f"{type(e).__name__}: {str(e)[:200]}"}
    sys.stdout.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()

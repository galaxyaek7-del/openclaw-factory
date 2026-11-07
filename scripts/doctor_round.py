#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Factory doctor round: one read-only command that lists everything needing attention (2026-11-06).

    python scripts/doctor_round.py            # human report
    python scripts/doctor_round.py --json

Sections: (1) stage check: BLOCKED/WAITING with owner; (2) loop steps that FAILED in the last 24 h, by step;
(3) connector intake freshness (a Claude session must refresh it: the loop cannot call connectors);
(4) approvals that expire within 36 h; (5) unpublished local commits and site difference.
Exit code 1 when an agent-owned problem exists (failed steps, stale intake, expiring approval), 0 otherwise.
Everything is read from live files; nothing is written, sent or changed.
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))


def failed_steps(log_path, now, hours=24):
    """Per step with failures in the window: how many, the last detail, and whether it is failing NOW (its most recent
    action is a failure). A step that failed and then ran fine is recovered: listed, not raised as a problem."""
    since = (now - timedelta(hours=hours)).isoformat()
    c, last, latest = Counter(), {}, {}
    try:
        for line in Path(log_path).read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if str(d.get("timestamp", "")) < since:
                continue
            # `diagnose` writes an action only when it fails or acts; a healthy tick carries its result in `diagnosis` instead.
            # A later tick with diagnosis checks therefore means the step ran fine (the doctor flagged a 19:28 health timeout as "failing
            # now" two hours after it had recovered).
            if (d.get("diagnosis") or {}).get("checks") and "diagnose" in latest and latest["diagnose"] == "failed":
                latest["diagnose"] = "recovered"
            for a in d.get("actions", []) or []:
                st = a.get("step")
                latest[st] = a.get("action")
                if a.get("action") == "failed":
                    c[st] += 1
                    last[st] = str(a.get("detail"))[:110].replace("\n", " ")
    except OSError:
        pass
    return [{"step": s, "failures": n, "last": last[s], "failing_now": latest.get(s) == "failed"} for s, n in c.most_common()]


def published_product_ids(root=None):
    """Product ids with a LIVE publish result that created the listing (a product_id): their approval is spent, its expiry is not a problem."""
    import glob
    out = set()
    for f in glob.glob(str((root or ROOT) / "data" / "batch*_publish_results.json")):
        try:
            runs = json.loads(Path(f).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for run in runs if isinstance(runs, list) else []:
            if str(run.get("mode", "")).upper() != "LIVE":
                continue
            for r in run.get("results", []):
                if isinstance(r, dict) and r.get("product_id") and r.get("status") in ("PASS", "BLOCKED"):
                    out.add(r.get("id"))
    return out


def expiring_approvals(path, now, hours=36, spent=frozenset()):
    out = []
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return out
    items = d.get("approvals", d) if isinstance(d, dict) else d
    rows = items.items() if isinstance(items, dict) else enumerate(items or [])
    for k, v in rows:
        if not isinstance(v, dict):
            continue
        exp = v.get("expires_at") or v.get("expires") or v.get("valid_until")
        try:
            t = datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
        except ValueError:
            continue
        left = (t - now).total_seconds() / 3600
        pid = v.get("product_id") or v.get("id") or str(k)
        if 0 < left <= hours and pid not in spent:
            out.append({"product": pid, "hours_left": round(left, 1)})
    return out


def git_counts():
    def g(*a):
        return subprocess.run(["git", *a], cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    try:
        ahead = len(g("rev-list", "origin/main..main").split())
        site = len([l for l in g("diff", "--name-status", "--no-renames", "origin/main", "HEAD", "--", "customer_site", "sitemap.xml").splitlines() if l.strip()])
    except Exception:  # noqa: BLE001
        return {"unpublished_commits": None, "site_files_differ": None}
    return {"unpublished_commits": ahead, "site_files_differ": site}


def run(now=None):
    now = now or datetime.now(timezone.utc)
    import autonomy_selfcheck
    import connector_intake
    stages = autonomy_selfcheck.collect()
    ci = connector_intake.summary(ROOT / "data" / "connector_intake.jsonl", now)
    ages = [r["age_hours"] for r in ci["last_intake"]]
    rep = {
        "at": now.isoformat(timespec="seconds"),
        "needs_founder": [{"stage": s["name"], "need": s["owner"]} for s in stages if s["status"] == "BLOCKED"],
        "waiting_on_reality": [s["name"] for s in stages if s["status"] == "WAITING"],
        "failed_steps_24h": failed_steps(ROOT / "factory_loop.log", now),
        "connector_intake": {"newest_age_hours": min(ages) if ages else None, "pin_outbound_clicks": ci["pin_outbound_clicks"]},
        "approvals_expiring": expiring_approvals(ROOT / "data" / "publication_approvals.json", now, spent=published_product_ids()),
        "git": git_counts(),
    }
    try:
        import agent_kpis
        ak = agent_kpis.gather(now)
        rep["agents"] = {"cost_usd": ak["total_cost_usd"], "llm_calls": ak["llm_calls"],
                         "flagged": {r["agent"]: r["flags"] for r in ak["agents"] if r["flags"]}}
    except Exception as e:  # noqa: BLE001
        rep["agents"] = {"error": type(e).__name__}
    try:
        import company_scorecard
        sc = company_scorecard.score(company_scorecard.evaluate(*company_scorecard.gather(now)))
        rep["company_automation"] = {"percent": sc["percent"], "automatic_or_gated": sc["automatic_or_gated"], "of": sc["capabilities"]}
    except Exception as e:  # noqa: BLE001  the scorecard must never stop the round
        rep["company_automation"] = {"error": type(e).__name__}
    problems = []
    for f in rep["failed_steps_24h"]:
        if f["failing_now"]:
            problems.append(f"step {f['step']} is failing now ({f['failures']}x in 24h; last: {f['last']})")
    if rep["connector_intake"]["newest_age_hours"] is None or rep["connector_intake"]["newest_age_hours"] > 48:
        problems.append("connector intake older than 48 h: run the connector part of the doctor round")
    for a in rep["approvals_expiring"]:
        if a["hours_left"] <= 12:  # an approval that outlives the next publishing window is not yet a problem
            problems.append(f"approval for {a['product']} expires in {a['hours_left']} h")
    try:
        rg = json.loads((ROOT / "data" / "regression_status.json").read_text(encoding="utf-8"))
        if rg.get("failed"):
            problems.append(f"regression gate: {rg['failed']} failing ({', '.join(rg.get('failures', [])[:4])})")
    except (OSError, ValueError):
        pass
    try:
        lh = json.loads((ROOT / "data" / "listing_health.json").read_text(encoding="utf-8"))
        for f in lh.get("findings", []):
            if f.get("severity") in ("CRITICAL", "HIGH"):
                problems.append(f"listing {f['slug']}: {f['kind']} ({f['detail']})")
    except (OSError, ValueError):
        pass
    try:
        import data_integrity_check as dic
        bj, bl = dic.scan()
        try:
            known = json.loads(dic.KNOWN.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            known = {"json": [], "jsonl": {}}
        nj, nl_ = dic.compare(bj, bl, known)
        for f in nj:
            problems.append(f"data integrity: {f} no longer parses (new corruption)")
        for f, n in nl_.items():
            problems.append(f"data integrity: {f} has {n} bad line(s) (new or grown)")
    except Exception:  # noqa: BLE001  the integrity scan must never stop the round
        pass
    try:
        import funnel_report
        fr = funnel_report.report(now.date())
        rep["funnel"] = {"pins_due": fr["pins_due_by_today"], "pin_clicks": fr["pin_outbound_clicks"], "clicks_measured": fr["pin_clicks_measured"], "sales": fr["sales"],
                         "checkpoints": {c["id"]: c["verdict"] for c in fr["checkpoints"]}}
        for c in fr["checkpoints"]:
            if c["verdict"] == "TRIGGERED":
                rep["needs_founder"].append({"stage": "kill criterion " + c["id"], "need": "founder decision: " + c["if_missed"]})
            elif c["verdict"] == "UNKNOWN":
                problems.append("kill criterion " + c["id"] + " cannot be judged: pin clicks are not measured (fix the Metricool/connector measurement)")
    except Exception:  # noqa: BLE001  the funnel must never stop the round
        pass
    try:  # subtle cross-source contradictions (scripts/subtle_audit.py); HIGH findings are agent problems
        import subtle_audit
        found = subtle_audit.run_all()
        rep["subtle_audit"] = {"high": sum(f["severity"] == "HIGH" for f in found), "medium": sum(f["severity"] == "MEDIUM" for f in found)}
        for f in found:
            if f["severity"] == "HIGH":
                problems.append(f"subtle audit [{f['area']}]: {f['what']} -> {f['next']}")
        reg = subtle_audit.jf(subtle_audit.ROOT / "data" / "product_registry.json", {}) or {}
        if (reg.get("drift") or {}).get("live_missing_from_catalog"):
            problems.append("live products missing from data/catalog.json: run scripts/catalog_sync.py --write, then product_registry.run()")
    except Exception:  # noqa: BLE001  the audit must never stop the round
        pass
    try:  # can a visitor reach a purchase? (scripts/sales_path_audit.py, local); HIGH = a broken path
        import sales_path_audit
        sp = sales_path_audit.audit()
        rep["sales_path"] = {"high": sum(f["severity"] == "HIGH" for f in sp), "medium": sum(f["severity"] == "MEDIUM" for f in sp)}
        for f in sp:
            if f["severity"] == "HIGH":
                problems.append(f"sales path: {f['what']} -> {f['next']}")
    except Exception:  # noqa: BLE001  the audit must never stop the round
        pass
    rep["agent_problems"] = problems
    return rep


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    rep = run()
    if "--json" in argv:
        sys.stdout.write(json.dumps(rep, ensure_ascii=False, indent=1) + "\n")
    else:
        L = [f"DOCTOR ROUND {rep['at']}", "", f"Needs the founder ({len(rep['needs_founder'])}):"]
        L += [f"  - {x['stage']}: {x['need']}" for x in rep["needs_founder"]]
        L += ["", "Waiting for real data: " + ", ".join(rep["waiting_on_reality"]), "", "Agent problems:"]
        L += [f"  ! {p}" for p in rep["agent_problems"]] or ["  none"]
        rec = [f for f in rep["failed_steps_24h"] if not f["failing_now"]]
        if rec:
            L += ["", "Recovered in the last 24 h (failed, then ran fine): " + ", ".join(f"{f['step']} x{f['failures']}" for f in rec)]
        L += ["", f"Connector intake: newest {rep['connector_intake']['newest_age_hours']} h, pin outbound clicks {rep['connector_intake']['pin_outbound_clicks']}",
              f"Git: {rep['git']}", f"Company automation: {rep.get('company_automation')}", f"Agents: {rep.get('agents')}"]
        sys.stdout.buffer.write(("\n".join(L) + "\n").encode("utf-8"))
    return 1 if rep["agent_problems"] else 0


if __name__ == "__main__":
    sys.exit(main())

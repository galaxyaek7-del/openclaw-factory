#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Subtle-error audit: contradictions between the factory's own sources of truth (2026-11-07). Read-only.

    python scripts/subtle_audit.py            # human report, exit 1 when a HIGH finding exists
    python scripts/subtle_audit.py --json

Nothing here crashes when it is wrong; each check looks for a place where two records that should agree do not, or where a step
reports success while doing nothing. Severity: HIGH (a decision or customer-facing page is wrong now), MEDIUM (wrong or stale, no
immediate harm), INFO (worth knowing). Every finding names the two things that disagree and a concrete next step.
Checks: catalog vs live products vs site pages vs covers; registry drift; Pinterest ledger vs due dates; loop steps that never do
anything; stale state files; flag combinations that contradict each other; approvals for products already live.
"""
from __future__ import annotations

import glob
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def jl(path):
    out = []
    try:
        for line in Path(path).read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("{"):
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
    except OSError:
        pass
    return out


def jf(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return default


def F(sev, area, what, fix):
    return {"severity": sev, "area": area, "what": what, "next": fix}


def check_catalog_vs_pages(root=ROOT):
    out = []
    cat = (jf(root / "customer_site" / "catalog.json", {}) or {}).get("data", {}).get("products", [])
    ids = {p["id"] for p in cat}
    urls = {p.get("url") for p in cat}
    pages = glob.glob(str(root / "customer_site" / "tool-*.html"))
    page_urls = {}
    for f in pages:
        t = Path(f).read_text(encoding="utf-8", errors="ignore")
        m = re.search(r'"url":\s*"(https://[^"]*gumroad\.com/l/[^"?]+)', t)
        if m:
            page_urls[Path(f).name] = m.group(1)
    for name, u in page_urls.items():
        if u not in urls:
            out.append(F("HIGH", "site", f"{name} points at a Gumroad product that is not in customer_site/catalog.json", "rebuild registry + catalog, or retire the page"))
    for p in cat:
        cover = root / "customer_site" / (p.get("cover_url") or "")
        if p.get("cover_url") and not cover.exists():
            out.append(F("HIGH", "site", f"catalog cover for {p['id']} is missing on disk ({p['cover_url']})", "export_public_catalog.js copies it; commit the file"))
    tool_ids = set()
    for f in pages:
        t = Path(f).read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"covers/([A-Z0-9-]+)\.png", t)
        if m:
            tool_ids.add(m.group(1))
    missing_page = sorted(i for i in ids if i.startswith(("B14", "B15", "B16", "B17", "B18")) and i not in tool_ids)
    if missing_page:
        out.append(F("MEDIUM", "site", f"live catalog products without a tool page: {', '.join(missing_page[:6])}", "check the page generator module list"))
    titles = Counter(p["title"] for p in cat)
    dup = [t for t, n in titles.items() if n > 1]
    if dup:
        out.append(F("MEDIUM", "catalog", f"duplicate titles in the public catalog: {dup[:2]}", "unpublish or retitle one"))
    return out


def check_registry(root=ROOT):
    out = []
    reg = jf(root / "data" / "product_registry.json", {}) or {}
    drift = reg.get("drift") or reg.get("drifts") or []
    if isinstance(drift, dict):
        drift = [{"kind": k, "detail": v} for k, v in drift.items()]
    for d in drift[:8]:
        if isinstance(d, dict) and not d.get("detail"):
            continue  # an empty drift list is agreement, not a finding
        kind = d.get("kind") if isinstance(d, dict) else str(d)
        out.append(F("MEDIUM", "registry", f"registry drift: {kind}: {str(d.get('detail') if isinstance(d, dict) else '')[:140]}", "see product_registry.run(); fix the source, not the registry"))
    states = Counter(p.get("primary_state") for p in reg.get("products", []))
    if states.get("UPLOAD_COMPLETED", 0) > 0:
        out.append(F("INFO", "registry", f"{states['UPLOAD_COMPLETED']} products are UPLOAD_COMPLETED (uploaded, never verified public): old test/held listings", "decide per product: verify, unpublish or leave"))
    return out


def check_pinterest(root=ROOT, today=None):
    out = []
    today = today or datetime.now(timezone.utc).date()
    rows = jl(root / "data" / "pinterest_manual_posts.jsonl")
    seen, bad_dates = Counter(), []
    for r in rows:
        seen[(r.get("offer_id"), str(r.get("scheduled_for", ""))[:10])] += 1
        try:
            date.fromisoformat(str(r.get("scheduled_for", ""))[:10])
        except ValueError:
            bad_dates.append(r.get("offer_id"))
    dups = [k for k, n in seen.items() if n > 1]
    if dups:
        out.append(F("HIGH", "pinterest", f"the same pin is logged twice: {dups[:3]}", "one of the rows is a double scheduling; check the profile"))
    if bad_dates:
        out.append(F("MEDIUM", "pinterest", f"ledger rows with an unreadable date: {bad_dates[:3]}", "fix the row"))
    by_day = Counter(str(r.get("scheduled_for", ""))[:10] for r in rows)
    over = [d for d, n in by_day.items() if n > 5]
    if over:
        out.append(F("HIGH", "pinterest", f"more than 5 pins scheduled on {over[:3]} (the standing approval allows 5 a day)", "reschedule"))
    ids = [r.get("offer_id") for r in rows]
    again = [k for k, n in Counter(ids).items() if n > 1]
    if again:
        out.append(F("MEDIUM", "pinterest", f"products pinned more than once: {again[:4]}", "intended repeats only"))
    last = max((str(r.get("scheduled_for", ""))[:10] for r in rows), default="")
    if last:
        try:
            left = (date.fromisoformat(last) - today).days
            if left <= 3:
                out.append(F("MEDIUM", "pinterest", f"the pin schedule runs out in {left} day(s) (last: {last})", "schedule the next batch (standing approval)"))
        except ValueError:
            pass
    return out


def check_loop_steps(root=ROOT, hours=48):
    """Steps that run every tick but never do anything, and steps that only ever fail."""
    out = []
    rows = jl(root / "factory_loop.log")
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    acts = defaultdict(Counter)
    for r in rows:
        if str(r.get("timestamp", "")) < since:
            continue
        for a in r.get("actions", []) or []:
            acts[a.get("step")][a.get("action") or a.get("event") or "?"] += 1
    ticks = sum(1 for r in rows if str(r.get("timestamp", "")) >= since and r.get("actions"))
    idle = []
    for step, c in sorted(acts.items()):
        total = sum(c.values())
        if total >= 20 and set(c) <= {"none", "skipped", "?"}:
            idle.append(step)
        if total >= 5 and c.get("failed", 0) == total:
            out.append(F("HIGH", "loop", f"step {step} failed on every one of its {total} runs in {hours} h", "fix or disable"))
    if idle:
        out.append(F("INFO", "loop", f"{len(idle)} steps ran 20+ times in {hours} h and never acted: {', '.join(idle[:14])}", "fine when gated or waiting for a date; dead weight otherwise"))
    return out


STATE_FILES = {  # file -> max age in hours before it is suspicious
    "data/regression_status.json": 40, "data/listing_health.json": 40, "data/product_registry.json": 40,
    "data/tool_pages_daily_state.json": 50, "data/connector_intake.jsonl": 72, "data/digital_discovery_run.json": 30,
}


def check_stale_state(root=ROOT, now=None):
    out = []
    now = now or datetime.now(timezone.utc).timestamp()
    for rel, hrs in STATE_FILES.items():
        p = root / rel
        if not p.exists():
            out.append(F("MEDIUM", "state", f"{rel} does not exist", "the step that writes it never ran"))
            continue
        age = (now - p.stat().st_mtime) / 3600
        if age > hrs:
            out.append(F("MEDIUM", "state", f"{rel} was last written {age:.0f} h ago (expected within {hrs} h)", "check the loop step that writes it"))
    return out


def env_flags(root=ROOT):
    d = {}
    try:
        for line in (root / ".env").read_text(encoding="utf-8", errors="ignore").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                d[k.strip()] = v.strip()
    except OSError:
        pass
    return d


def check_flags(root=ROOT):
    out = []
    e = env_flags(root)
    t = lambda k: str(e.get(k, "")).lower() == "true"
    if t("GF_DEMAND_GATED") and not t("GF_FREEZE_NEW_PRODUCTS"):
        out.append(F("INFO", "flags", "GF_DEMAND_GATED=true has no effect while GF_FREEZE_NEW_PRODUCTS=false (the gate only works with the freeze)", "remove the dead flag or restore the freeze; the doc line in CLAUDE.md still describes the gated freeze"))
    if t("FACTORY_AUTO_PRODUCE") and not t("GF_FREEZE_NEW_PRODUCTS") and e.get("GF_GOLDEN_SCORE_FLOOR"):
        out.append(F("INFO", "flags", f"auto production is ON and the hunter floor is lowered to {e.get('GF_GOLDEN_SCORE_FLOOR')}: capped at GF_GOLDEN_DAILY_CAP={e.get('GF_GOLDEN_DAILY_CAP', '3 (default)')}", "intended since 2026-11-06; keep the cap"))
    if t("FACTORY_LIVE_PUBLISH") and not t("GF_AUTO_PUBLISH_APPROVED"):
        out.append(F("INFO", "flags", "FACTORY_LIVE_PUBLISH=true but GF_AUTO_PUBLISH_APPROVED is not: live writes are possible, the daily publisher will not run", "fine if publishing is manual"))
    return out


def check_approvals(root=ROOT, now=None):
    out = []
    now = now or datetime.now(timezone.utc)
    ap = jf(root / "data" / "publication_approvals.json", []) or []
    ap = ap.get("approvals", ap) if isinstance(ap, dict) else ap
    live = set()
    for f in glob.glob(str(root / "data" / "batch*_publish_results.json")):
        for run in jf(f, []) or []:
            for r in run.get("results", []) if isinstance(run, dict) and str(run.get("mode", "")).upper() == "LIVE" else []:
                if r.get("product_id"):
                    live.add(r.get("id"))
    valid_unused = []
    for v in ap if isinstance(ap, list) else []:
        try:
            exp = datetime.fromisoformat(str(v.get("expires_at")).replace("Z", "+00:00"))
        except ValueError:
            continue
        if exp > now and v.get("status") == "APPROVED" and v.get("product_id") not in live:
            valid_unused.append(v.get("product_id"))
    if valid_unused:
        out.append(F("INFO", "approvals", f"valid approvals not yet used: {valid_unused[:5]}", "the publisher uses them when Gumroad's window has room"))
    return out


def run_all(root=ROOT):
    findings = []
    for fn in (check_catalog_vs_pages, check_registry, check_pinterest, check_loop_steps, check_stale_state, check_flags, check_approvals):
        try:
            findings += fn(root)
        except Exception as e:  # noqa: BLE001 an audit must never crash
            findings.append(F("MEDIUM", "audit", f"{fn.__name__} could not run: {type(e).__name__}: {str(e)[:80]}", "fix the audit"))
    order = {"HIGH": 0, "MEDIUM": 1, "INFO": 2}
    return sorted(findings, key=lambda f: order[f["severity"]])


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    f = run_all()
    if "--json" in argv:
        sys.stdout.write(json.dumps(f, ensure_ascii=False, indent=1) + "\n")
    else:
        c = Counter(x["severity"] for x in f)
        L = [f"SUBTLE AUDIT: {c.get('HIGH', 0)} high, {c.get('MEDIUM', 0)} medium, {c.get('INFO', 0)} info", ""]
        for x in f:
            L.append(f"[{x['severity']}] {x['area']}: {x['what']}")
            L.append(f"        -> {x['next']}")
        sys.stdout.buffer.write(("\n".join(L) + "\n").encode("utf-8"))
    return 1 if any(x["severity"] == "HIGH" for x in f) else 0


if __name__ == "__main__":
    sys.exit(main())

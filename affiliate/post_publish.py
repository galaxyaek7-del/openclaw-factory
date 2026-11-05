#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Post-publication verification + measurement machine (awaits URL).

Fires only on a founder-supplied Medium URL. Read-only verification
(12 checks), measurement activation, evidence-ledger appends. Never
modifies the article, never manufactures events, never writes revenue.
NOT_VERIFIED or material mismatch -> HOLD + exact report, full stop."""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
PUB_PATH = _FACTORY_ROOT / "data" / "medium_publication.json"
EVIDENCE_PATH = _FACTORY_ROOT / "data" / "post_publish_evidence.jsonl"

MARKERS = ["listing editor", "trader status", "responsible person",
           "does not itself make you compliant", "aekraft.gumroad.com/l/fetmu"]


def intake_url(url: str) -> dict:
    """Validate shape only. Malformed -> NOT_VERIFIED, no further action."""
    u = (url or "").strip()
    if not (u.startswith("https://") and "medium.com" in u):
        return {"accepted": False, "STATUS": "NOT_VERIFIED",
                "reason": "not a well-formed medium.com https URL"}
    rec = {"MEDIUM_PUBLIC_URL": u, "received_at": datetime.now(timezone.utc).isoformat(),
           "status": "PENDING_VERIFICATION"}
    PUB_PATH.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"accepted": True, "STATUS": "PENDING_VERIFICATION"}


def verify_article(url: str, timeout: int = 30) -> dict:
    """12 read-only checks. Material mismatch -> HOLD (never silent repair)."""
    checks, fails = {}, []

    def check(name, ok, evidence, level="OBSERVED"):
        checks[name] = {"pass": bool(ok), "evidence": evidence, "level": level}
        if not ok:
            fails.append(name)

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GalaxyForge-verify/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            html, final, status = (r.read().decode("utf-8", "replace"),
                                   r.geturl(), r.status)
    except Exception as e:
        return {"STATUS": "NOT_VERIFIED", "checks": {},
                "reason": "%s: %s" % (type(e).__name__, str(e)[:120])}
    low = html.lower()
    check("http_accessible", status == 200, "HTTP %d" % status)
    check("https", final.startswith("https://"), final[:80])
    check("no_unexpected_redirect", "medium.com" in final, final[:120])
    title_ok = "gpsr" in low and "etsy" in low
    check("title", title_ok, "title carries GPSR+Etsy" if title_ok else "title mismatch")
    found = [m for m in MARKERS if m in low]
    check("content_identity", len(found) >= 4, "%d/5 draft markers present" % len(found))
    check("gpsr_content", "responsible person" in low and "technical file" in low,
          "core sections present")
    check("destination_link", "aekraft.gumroad.com/l/fetmu" in html,
          "fetmu URL present in raw HTML")
    check("utm_intact", "utm_source=medium" in html and "utm_campaign=gpsr-etsy-guide" in html,
          "UTM params present in raw HTML")
    check("no_corruption", len(html) > 5000, "%d chars fetched" % len(html))
    check("no_platform_flag", not any(k in low for k in
                                      ("this post is under review", "suspended", "removed")),
          "no restriction markers")
    check("matches_approved", len(found) == 5 and title_ok, "full marker set + title",
          level="DERIVED")
    # affiliate scope: must NOT contain systeme link (separate evidence path)
    check("no_affiliate_injection", "systeme.io" not in low,
          "article untouched by affiliate path")
    if fails:
        material = [f for f in fails if f in ("content_identity", "matches_approved",
                                              "destination_link", "title")]
        return {"STATUS": "HOLD" if material else "NOT_VERIFIED",
                "checks": checks, "failed": fails,
                "reason": "material mismatch, no silent repair" if material else "checks failed"}
    return {"STATUS": "VERIFIED", "checks": checks, "failed": [],
            "url": final, "checked_at": datetime.now(timezone.utc).isoformat()}


def log_evidence(event: dict) -> dict:
    row = {"at": datetime.now(timezone.utc).isoformat(), **event}
    with open(EVIDENCE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"logged": True}


def activate_measurement() -> dict:
    """Open GPSR measurement: state flag on the test record (sales polling
    already covers purchases; exposure stays UNKNOWN until evidenced)."""
    from prospecting import market_test as mt
    d = _FACTORY_ROOT / "data" / "market_test_gpsr_path_b_v1"
    rec = json.loads((d / "test_record.json").read_text(encoding="utf-8"))
    rec["MEASUREMENT"] = {"opened_at": datetime.now(timezone.utc).isoformat(),
                          "channels": ["medium_article (pending URL verification)",
                                       "gumroad_sales_poll"],
                          "exposure": "UNKNOWN until first evidence"}
    (d / "test_record.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
    return {"measurement": "OPEN", "note": "no traffic invented at open"}


def first_cycle(url: str) -> dict:
    """Full first run on a supplied URL: intake -> verify -> branch."""
    from affiliate import gates as gt
    inc = intake_url(url)
    log_evidence({"experiment": "GPSR_PATH_B_V1", "event": "URL_INTAKE", **inc})
    if not inc["accepted"]:
        return {"outcome": "NOT_VERIFIED", **inc}
    ver = verify_article(url)
    log_evidence({"experiment": "GPSR_PATH_B_V1", "event": "ARTICLE_VERIFY",
                  "STATUS": ver["STATUS"], "failed": ver.get("failed", [])})
    if ver["STATUS"] != "VERIFIED":
        return {"outcome": ver["STATUS"], "verification": ver,
                "action": "HOLD — exact failure reported, external execution stopped"}
    meas = activate_measurement()
    gt.acknowledge_gate("f386228d0bf5")
    with open(gt.GATES_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps({"GATE_ID": "f386228d0bf5", "status": "EXECUTED_VERIFIED",
                            "flow_state": "AUTOMATION_RELEASED",
                            "evidence": "article VERIFIED (%s)" % ver["url"]},
                           ensure_ascii=False) + "\n")
    log_evidence({"experiment": "GPSR_PATH_B_V1", "event": "MEASUREMENT_OPEN",
                  **meas})
    return {"outcome": "MEASURING", "verification": ver, "measurement": meas,
            "next": "heartbeat resumes; diagnosis on real evidence only"}

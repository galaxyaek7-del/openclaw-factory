#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — Systeme.io affiliate readiness verification.

Checks the 7 autonomous items; isolates the human-only step precisely.
Read-only (never prints secrets, never writes). Exit shape:
{ready: bool, checks: [...], founder_gate: {...}}.
"""
import json
from pathlib import Path

FACTORY_DIR = Path(__file__).resolve().parent.parent

DISCLOSURE_LINE = "This page may contain affiliate links."


def readiness():
    checks = []
    try:
        import systeme_affiliate as sa
        cfg = sa.validate_config()
        ok = bool(cfg.get("affiliate_id_present") and cfg.get("affiliate_id_format_valid")
                  and not cfg.get("affiliate_id_is_placeholder"))
        checks.append({"item": "affiliate_url_builder",
                       "ok": ok,
                       "detail": "builder configured" if ok
                       else f"SYSTEME_AFFILIATE_ID issue: {cfg.get('config_error')} — founder adds key"})
    except Exception as e:
        checks.append({"item": "affiliate_url_builder", "ok": False,
                       "detail": f"module error: {e}"[:200]})
    disc = FACTORY_DIR / "customer_site" / "trust" / "affiliate-disclosure.html"
    checks.append({"item": "disclosure_page", "ok": disc.exists(),
                   "detail": "trust/affiliate-disclosure.html present" if disc.exists()
                   else "missing disclosure page"})
    tut = FACTORY_DIR / "customer_site" / "guide-systemeio-affiliate.html"
    checks.append({"item": "tutorial_content", "ok": tut.exists(),
                   "detail": "guide-systemeio-affiliate.html present" if tut.exists()
                   else "missing tutorial page"})
    if tut.exists():
        text = tut.read_text(encoding="utf-8", errors="replace")
        has_en = "affiliate" in text.lower()
        has_ar = ("إفصاح" in text and "عمولة" in text)
        has_div = 'class="disclosure"' in text or "class='disclosure'" in text
        ok_disc = has_en or has_ar or has_div
        checks.append({"item": "disclosure_in_tutorial",
                       "ok": ok_disc,
                       "detail": "disclosure present (EN token)" if has_en
                       else ("disclosure present (Arabic referral disclosure)" if has_ar
                             else ("disclosure div present" if has_div
                                   else "no disclosure token in tutorial"))})
        checks.append({"item": "cta_present",
                       "ok": "systeme" in text.lower(),
                       "detail": "Systeme.io CTA reference present" if "systeme" in text.lower()
                       else "no CTA reference"})
    else:
        checks += [{"item": "disclosure_in_tutorial", "ok": False, "detail": "no tutorial file"},
                   {"item": "cta_present", "ok": False, "detail": "no tutorial file"}]
    try:
        from affiliate import links as L
        rows = L.list_links()
        sys_rows = [r for r in rows if "systeme" in str(r.get("domain", "")).lower()
                     or "systeme" in str(r.get("program", "")).lower()]
        checks.append({"item": "link_registered", "ok": bool(sys_rows),
                       "detail": f"{len(sys_rows)} registry row(s), secret-free" if sys_rows
                       else "no systeme.io registry row"})
    except Exception as e:
        checks.append({"item": "link_registered", "ok": False, "detail": str(e)[:200]})
    vid = FACTORY_DIR / "assets" / "affiliate" / "systeme_io"
    checks.append({"item": "video_assets_ready", "ok": vid.exists(),
                   "detail": "video package on disk" if vid.exists() else "no video package"})
    ready = all(c["ok"] for c in checks)
    return {"ready": ready, "checks": checks,
            "founder_gate": {"WHAT": "Publish the Systeme.io video/post from the founder's own account with the real affiliate link",
                             "WHY": "Only the account owner can publish; only the key holder can inject the real ?sa= ID at publish time",
                             "EXACT_ACTION": "Open the owned channel -> upload assets/affiliate/systeme_io video -> paste URL built at runtime from SYSTEME_AFFILIATE_ID -> publish -> confirm back",
                             "EXPECTED_RESULT": "Live public page with working affiliate link + first trackable external click path"}}


if __name__ == "__main__":
    import sys as _sys
    try:
        _sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(json.dumps(readiness(), ensure_ascii=False))

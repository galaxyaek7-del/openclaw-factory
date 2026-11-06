#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Repair mojibake in live Gumroad descriptions (2026-11-06).

Found by a read-only scan of all listings: 9 live descriptions show "â€”" instead of an em dash, "â€“" for an en dash
and "Â£" for a pound sign: UTF-8 text that was decoded as cp1252 and saved again. The buyer sees the corruption on the
public page. The repair is deterministic: only a corrupted sequence that decodes back to exactly ONE character is
replaced; every other character is left untouched, and a second run changes nothing.

Safety: description only (the sanctioned scoped writer refuses any other field); one single-use write scope per product,
bound to the exact new text; the writer reads the listing back and the run stops reporting FAILED on any mismatch;
price, title, files and publication state are never sent.

    python scripts/repair_listing_mojibake.py            # dry run: shows every replacement
    python scripts/repair_listing_mojibake.py --live
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
REPORT = ROOT / "data" / "listing_mojibake_repair_20261106.json"
NOTE = "2026-11-06 mojibake repair (founder: fix every gap, chat order)"

# lead character of a cp1252-decoded UTF-8 sequence (U+00C2/C3/E2/F0) followed by 1-3 characters cp1252 can produce
_TAIL = "\u0080-ÿŒœŠšŸŽžƒˆ˜–-›€™"
MOJIBAKE = re.compile("[ÂÃâð][" + _TAIL + "]{1,3}")


def fix_text(text):
    """-> (fixed_text, [(bad, good), ...]). A sequence is replaced only if it decodes to exactly one character."""
    changes = []

    def repl(m):
        bad = m.group()
        for n in (3, 2, 1):  # longest valid prefix: a corrupted char may be followed by ordinary text
            piece = bad[:n + 1]
            try:
                good = piece.encode("cp1252").decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
            if len(good) == 1 and good != piece:
                changes.append((piece, good))
                return good + bad[n + 1:]
        return bad

    return MOJIBAKE.sub(repl, text or ""), changes


def plan(token, gp, only=None):
    actions = []
    for p in gp.list_products(token):
        slug = (p.get("short_url") or "").rstrip("/").rsplit("/", 1)[-1]
        if only and slug not in only:
            continue
        f = gp.get_product(token, p["id"])
        new, changes = fix_text(f.get("description") or "")
        name_new, name_changes = fix_text(f.get("name") or "")
        if not changes and not name_changes:
            continue
        a = {"slug": slug, "product_id": p["id"], "name": (f.get("name") or "")[:70], "published": f.get("published"),
             "replacements": sorted({(b, g) for b, g in changes}), "count": len(changes)}
        if name_changes:  # the scoped writer cannot change a title: reported, not touched
            a["title_needs_manual_fix"] = name_new
        if changes:
            a["new_description"] = new
            a["result"] = "PLANNED"
        else:
            a["result"] = "SKIPPED"
        actions.append(a)
    return actions


def apply(token, gp, ws, actions):
    done = []
    for a in actions:
        if a["result"] != "PLANNED":
            done.append(a)
            continue
        try:
            scope = ws.issue_scope(product_id=a["product_id"], slug=a["slug"], payload={"description": a["new_description"]},
                                   operation="update_description", note=NOTE)
            gp.update_product_description_scoped(token, a["product_id"], a["new_description"], scope_id=scope.scope_id)
            after = gp.get_product(token, a["product_id"])
            again, left = fix_text(after.get("description") or "")
            ok = not left and after.get("published") == a["published"]
            done.append({**{k: v for k, v in a.items() if k != "new_description"}, "result": "PASS" if ok else "FAILED",
                         **({} if ok else {"reason": f"still {len(left)} corrupted sequence(s) or publication state changed"})})
            if not ok:
                break  # stop at the first doubt
        except Exception as e:  # noqa: BLE001
            done.append({**{k: v for k, v in a.items() if k != "new_description"}, "result": "FAILED",
                         "reason": f"{type(e).__name__}: {str(e)[:300]}"})
            break
    return done


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args(argv)
    from channels import gumroad_publisher as gp
    token = gp.load_token()
    actions = plan(token, gp, set(args.only) if args.only else None)
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "mode": "LIVE" if args.live else "DRY_RUN"}
    if args.live:
        import gumroad_auth_watch as auth
        from channels import publication_authorization as pa
        from channels import write_scope as ws
        pa.assert_session_fresh(auth.poll(), max_age_seconds=3600)
        os.environ["FACTORY_LIVE_PUBLISH"] = "true"
        try:
            report["actions"] = apply(token, gp, ws, actions)
        finally:
            os.environ["FACTORY_LIVE_PUBLISH"] = "false"
    else:
        report["actions"] = [{k: v for k, v in a.items() if k != "new_description"} for a in actions]
    REPORT.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=list), encoding="utf-8")
    summary = {}
    for a in report["actions"]:
        summary[a["result"]] = summary.get(a["result"], 0) + 1
    print(json.dumps({"mode": report["mode"], "summary": summary, "listings": len(actions)}))
    return 0 if all(a["result"] in ("PASS", "PLANNED", "SKIPPED") for a in report["actions"]) else 1


if __name__ == "__main__":
    sys.exit(main())

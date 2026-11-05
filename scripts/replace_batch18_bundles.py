#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Replace the attached bundle on the ten live batch-18 listings with the rebuilt, longer-guide bundles (2026-11-05).

Why: after publication the guides were extended (where each input comes from, sanity checks), so the delivered
file is better than the one first uploaded. No listing has sold, so replacing the file changes nothing for a buyer.

Safety:
  * the local bundle must exist and match the sha256 in its manifest (the bytes QA tested);
  * a listing whose attached file already has the local bundle's exact size is skipped (idempotent);
  * each upload goes through the write gate and one write scope bound to that product and that file;
  * after the upload the listing is read back: exactly ONE file must be attached and its size must match,
    otherwise the result is FAILED and nothing else is touched;
  * price, title, tags, cover and publication state are never sent.

    python scripts/replace_batch18_bundles.py                        # dry run
    python scripts/replace_batch18_bundles.py --live --only B18-001  # one product first
    python scripts/replace_batch18_bundles.py --live
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
REPORT = ROOT / "data" / "batch18_bundle_replacement.json"
NOTE = ("Founder in-session 2026-11-05, verbatim: 'واصل المهام المتبقية للمصنع و المنتجات العشر الاخيرة و ماينقصها اكمله بصفة جيدة دون نقصان'. "
        "Replaces the delivered bundle with the rebuilt longer-guide bundle; no sales yet.")


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def plan(token, gp, only=None):
    results = json.loads((ROOT / "data" / "batch18_publish_results.json").read_text(encoding="utf-8"))
    urls = {}
    for run in results:
        for r in run.get("results", []):
            if r.get("url") and r.get("steps", {}).get("published"):
                urls[r["id"]] = r["url"].rstrip("/").rsplit("/", 1)[-1]
    by_slug = {(p.get("short_url") or "").rstrip("/").rsplit("/", 1)[-1]: p for p in gp.list_products(token)}
    actions = []
    for pid in sorted(urls):
        if only and pid not in only:
            continue
        man = json.loads((ROOT / "books" / "batch18" / pid / "manifest.json").read_text(encoding="utf-8"))
        bundle = ROOT / man["files"]["bundle"]["path"]
        base = {"id": pid, "slug": urls[pid], "bundle": str(bundle.relative_to(ROOT))}
        if not bundle.exists() or sha256(bundle) != man["files"]["bundle"]["sha256"]:
            actions.append({**base, "error": "local bundle missing or does not match its manifest sha256"})
            continue
        p = by_slug.get(urls[pid])
        if not p:
            actions.append({**base, "error": "listing not found"})
            continue
        full = gp.get_product(token, p["id"])
        files = full.get("files") or []
        size = bundle.stat().st_size
        base.update({"product_id": p["id"], "local_size": size, "attached_sizes": [f.get("size") for f in files]})
        if len(files) == 1 and files[0].get("size") == size:
            actions.append({**base, "already_applied": True})
        else:
            actions.append(base)
    return actions


def apply(token, gp, ws, actions):
    done = []
    for a in actions:
        if a.get("error") or a.get("already_applied"):
            done.append({**a, "result": "SKIPPED" if a.get("error") else "ALREADY_APPLIED"})
            continue
        try:
            path = ROOT / a["bundle"]
            scope = ws.issue_scope(product_id=a["product_id"], slug=a["slug"], payload={"file_path": str(path)},
                                   operation="upload_file", note=NOTE)
            full = gp.update_product_file(token, a["product_id"], path, upload_scope_id=scope.scope_id)
            sizes = [f.get("size") for f in (full.get("files") or [])]
            ok = len(sizes) == 1 and sizes[0] == a["local_size"]
            done.append({**a, "result": "PASS" if ok else "FAILED", "attached_after": sizes,
                         **({} if ok else {"reason": f"expected exactly one file of {a['local_size']} bytes, found {sizes}"})})
            if not ok:
                break  # stop at the first doubt: do not touch the other nine
        except Exception as e:  # each listing stands alone, but a failure stops the run
            done.append({**a, "result": "FAILED", "reason": f"{type(e).__name__}: {str(e)[:300]}"})
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
        report["actions"] = [{**a, "result": "SKIPPED" if a.get("error") else
                              ("ALREADY_APPLIED" if a.get("already_applied") else "PLANNED")} for a in actions]
    REPORT.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    summary = {}
    for a in report["actions"]:
        summary[a["result"]] = summary.get(a["result"], 0) + 1
    print(json.dumps({"mode": report["mode"], "summary": summary, "report": str(REPORT.relative_to(ROOT))}))
    return 0 if all(a["result"] in ("PASS", "PLANNED", "ALREADY_APPLIED") for a in report["actions"]) else 1


if __name__ == "__main__":
    sys.exit(main())

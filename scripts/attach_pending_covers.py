#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Attach covers to live Gumroad listings whose cover step failed at publish time (2026-11-06). Loop step, idempotent.

    python scripts/attach_pending_covers.py      # prints one JSON line {action, detail}

Why: Gumroad FETCHES a cover from a public URL on our site (customer_site/assets/covers/<id>.png). B17-002 was created live, its
cover step failed because that file was not on the public site yet, and the listing stayed without a cover until repaired by hand.
Now, for every LIVE publish result whose steps.cover starts with FAILED:
  1. make sure the cover file is in customer_site/assets/covers (copied from books/covers) and committed on its own, so the
     normal site publisher pushes it;
  2. wait until its public URL answers 200 with an image;
  3. attach it with the standard safeguards (Gumroad auth VERIFIED, a fresh read shows the product published with ZERO covers,
     a re-read proves the cover is there). Cover only: no price, file, name or publication change.
It never creates a listing and never touches a product that already has a cover.
"""
from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "channels"))
PUBLIC = "https://galaxyaek7-del.github.io/openclaw-factory/customer_site/assets/covers/{id}.png"
RESULTS = ROOT / "data" / "gumroad_cover_results.json"
AUTHORIZATION = "cover repair for a listing created under a named founder approval; cover only, no price/file/name/publication change"


def pending(results_glob=None, root=ROOT):
    """[(id, product_id)] from LIVE results whose cover step FAILED, minus ids already recorded as ATTACHED."""
    done = set()
    rf = RESULTS if Path(root) == ROOT else Path(root) / "data" / "gumroad_cover_results.json"
    try:
        for run in json.loads(Path(rf).read_text(encoding="utf-8")):
            for r in run.get("results", []):
                if str(r.get("result", "")).startswith("ATTACHED"):
                    done.add(r.get("name") or r.get("id"))
    except (OSError, ValueError):
        pass
    out = {}
    for f in sorted(glob.glob(results_glob or str(Path(root) / "data" / "batch*_publish_results.json"))):
        try:
            runs = json.loads(Path(f).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for run in runs if isinstance(runs, list) else []:
            if str(run.get("mode", "")).upper() != "LIVE":
                continue
            for r in run.get("results", []):
                cov = str((r.get("steps") or {}).get("cover", ""))
                if r.get("product_id") and cov.startswith("FAILED") and r.get("id") not in done:
                    out[r["id"]] = r["product_id"]
    return sorted(out.items())


def image_ok(url, opener=urllib.request.urlopen):
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
        with opener(req, timeout=30) as r:
            return r.status == 200 and str(r.headers.get("Content-Type", "")).startswith("image/")
    except Exception:  # noqa: BLE001
        return False


def stage_cover(pid_id, root=ROOT):
    """Copy the cover into the site folder and commit just that file. -> 'ready' | 'committed' | 'missing'."""
    site = Path(root) / "customer_site" / "assets" / "covers" / f"{pid_id}.png"
    src = Path(root) / "books" / "covers" / f"{pid_id}.png"
    if not site.exists():
        if not src.exists():
            return "missing"
        site.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, site)
    rel = site.relative_to(root).as_posix()
    st = subprocess.run(["git", "status", "--porcelain", "--", rel], cwd=str(root), capture_output=True, text=True).stdout.strip()
    if not st:
        return "ready"
    subprocess.run(["git", "add", "--", rel], cwd=str(root), check=True)
    c = subprocess.run(["git", "commit", "-q", "-m", f"Site: cover image for {pid_id} (Gumroad fetches it from this public URL)", "--", rel],
                       cwd=str(root), capture_output=True, text=True)
    return "committed" if c.returncode == 0 else "missing"


def run_once(pending_fn=pending, stage_fn=stage_cover, ok_fn=image_ok, gp=None, auth=None, record=True):
    todo = pending_fn()
    if not todo:
        return {"action": "none", "detail": "no live listing with a failed cover step"}
    notes, attach = [], []
    for pid_id, product_id in todo:
        s = stage_fn(pid_id)
        if s == "missing":
            notes.append(f"{pid_id}: no cover file on disk")
        elif not ok_fn(PUBLIC.format(id=pid_id)):
            notes.append(f"{pid_id}: cover {s}, waiting for the site publish (URL not live yet)")
        else:
            attach.append((pid_id, product_id))
    if not attach:
        return {"action": "waiting", "detail": "; ".join(notes)}
    if gp is None:
        import gumroad_publisher as gp
    if auth is None:
        import gumroad_auth_watch as auth
    token = gp.load_token()
    st = auth.poll()
    if st.get("status") != "VERIFIED":
        return {"action": "blocked", "detail": f"Gumroad auth state is {st.get('status')}, not VERIFIED"}
    results = []
    prev = os.environ.get("FACTORY_LIVE_PUBLISH")
    os.environ["FACTORY_LIVE_PUBLISH"] = "true"  # this process only
    try:
        for pid_id, product_id in attach:
            rec = {"id": product_id, "name": pid_id, "cover": PUBLIC.format(id=pid_id)}
            try:
                fresh = gp.get_product(token, product_id)
                if not fresh.get("published") or len(fresh.get("covers") or []) != 0:
                    rec["result"] = "SKIPPED: unpublished or already has a cover"
                else:
                    got = gp.add_product_cover(token, product_id, rec["cover"], expected_cover_count=0)
                    rec["result"] = "ATTACHED" if len(got.get("covers") or []) > 0 else "FAILED: re-read shows no cover"
            except Exception as e:  # noqa: BLE001
                rec["result"] = f"FAILED: {type(e).__name__}: {str(e)[:160]}"
            results.append(rec)
            if rec["result"].startswith("FAILED"):
                break
    finally:
        if prev is None:
            os.environ.pop("FACTORY_LIVE_PUBLISH", None)
        else:
            os.environ["FACTORY_LIVE_PUBLISH"] = prev
        if record and results:
            old = json.loads(RESULTS.read_text(encoding="utf-8")) if RESULTS.exists() else []
            RESULTS.write_text(json.dumps(old + [{"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "authorization": AUTHORIZATION,
                                                  "results": results}], indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    ok = [r for r in results if r["result"] == "ATTACHED"]
    tail = ("; " + "; ".join(notes)) if notes else ""
    return {"action": "attached" if ok else "failed", "detail": "; ".join(f"{r['name']}: {r['result']}" for r in results) + tail}


def main():
    try:
        r = run_once()
    except Exception as e:  # noqa: BLE001
        r = {"action": "failed", "detail": f"{type(e).__name__}: {str(e)[:160]}"}
    sys.stdout.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()

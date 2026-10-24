#!/usr/bin/env python3
"""Publish the batch-14 products to Gumroad (founder authorization 2026-10-23).

Founder, 2026-10-23: "produce ten high-value digital products, with review,
inspection and testing, and upload and publish them on Gumroad, a full cycle,
with realistic prices". This script is the publication step for exactly the
products whose QA manifest under books/batch14/<id>/manifest.json is ok.

Live writes are refused unless --live is given; the live-publish flag is set
only inside this process (never in .env) and only after the Gumroad auth
state has been re-verified. Per product, failing closed and stopping the run
at the first failure:

  1. manifest qa.ok must be true and the bundle's SHA-256 must equal the one
     recorded at QA time (nothing changed since review);
  2. a single-use upload scope bound to the exact bundle path is minted;
  3. create_product() (its own duplicate-title refusal applies);
  4. read back: name, price and published must match; enable if unpublished;
  5. cover attached from its public URL and verified by re-read;
  6. the public listing URL must answer 200 and contain the title;
  7. one publish_attempt event per product in the ledger, and a results file.

  python scripts/publish_batch14.py            # dry run: checks only
  python scripts/publish_batch14.py --live     # publish
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
BATCH = ROOT / "books" / "batch14"
RESULTS = ROOT / "data" / "batch14_publish_results.json"
# 2026-10-24: the same publication path for later batches (--batch). Each has
# its own folder, results file and the founder authorization it ran under.
BATCHES = {
    "batch14": (BATCH, RESULTS, "founder 2026-10-23: publish ten batch-14 products on Gumroad at realistic prices"),
    "batch15": (ROOT / "books" / "batch15", ROOT / "data" / "batch15_publish_results.json",
                "founder 2026-10-24: produce ten new real-pain digital products with review and testing, and publish them on Gumroad"),
}
COVER_URL = "https://raw.githubusercontent.com/galaxyaek7-del/openclaw-factory/main/books/covers/{id}.png"
AUTHORIZATION = "founder 2026-10-23: publish ten batch-14 products on Gumroad at realistic prices"


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load_manifests(batch=BATCH):
    out = []
    prefix = "B" + Path(batch).name.replace("batch", "")          # batch14 -> B14, batch15 -> B15
    for m in sorted(Path(batch).glob(f"{prefix}-*/manifest.json")):
        out.append(json.loads(m.read_text(encoding="utf-8")))
    return out


def preflight(man, root=ROOT):
    """-> (ok, reason, bundle_path). Pure apart from reading the bundle."""
    if not (man.get("qa") or {}).get("ok"):
        return False, "QA manifest is not ok", None
    b = man["files"]["bundle"]
    path = root / b["path"]
    if not path.is_file():
        return False, f"bundle missing: {b['path']}", None
    if sha256(path) != b["sha256"]:
        return False, "bundle changed since QA (sha256 mismatch)", None
    if not ((man.get("qa") or {}).get("listing") or {}).get("description_html"):
        return False, "no listing description", None
    if not (100 <= int(man["price_cents"]) <= 10000):
        return False, f"price {man['price_cents']} cents outside the 1-100 range", None
    return True, "ok", path


def url_ok(url, must_contain, timeout=30, opener=urllib.request.urlopen):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 GalaxyForge-verify"})
        r = opener(req, timeout=timeout)
        from html import unescape
        body = unescape(r.read().decode("utf-8", "replace"))
        return r.status == 200 and must_contain.lower() in body.lower()
    except Exception:
        return False


def publish_one(man, token, *, gp, write_scope, ledger, cover_url_fn, opener=urllib.request.urlopen):
    ok, why, bundle = preflight(man)
    rec = {"id": man["id"], "title": man["title"], "price_cents": man["price_cents"], "steps": {}}
    if not ok:
        rec["error"] = f"preflight: {why}"
        return rec
    scope = write_scope.issue_scope(product_id=gp.NEW_PRODUCT, slug=man["slug"], payload={"file_path": str(bundle)},
                                    operation="upload_file", note=AUTHORIZATION)
    spec = {"title": man["title"], "price_cents": int(man["price_cents"]), "file_path": str(bundle),
            "description": man["qa"]["listing"]["description_html"], "expected_sha256": man["files"]["bundle"]["sha256"]}
    product = gp.create_product(token, spec, upload_scope_id=scope.scope_id)
    pid = product.get("id")
    rec.update(product_id=pid, steps={"create": "ok"})
    time.sleep(2)
    got = gp.get_product(token, pid)
    if got.get("name") != man["title"] or int(got.get("price", -1)) != int(man["price_cents"]):
        rec["error"] = f"read-back mismatch: name={got.get('name')!r} price={got.get('price')}"
        return rec
    if not got.get("published"):
        gp.enable_product(token, pid)
        got = gp.get_product(token, pid)
    rec["steps"]["published"] = bool(got.get("published"))
    if not got.get("published"):
        rec["error"] = "product did not become published"
        return rec
    rec["url"] = got.get("short_url")
    try:
        # expected_cover_count is the count BEFORE the attach: the re-read must grow past it
        gp.add_product_cover(token, pid, cover_url_fn(man["id"]), expected_cover_count=len(got.get("covers") or []))
        rec["steps"]["cover"] = "ok"
    except Exception as e:  # the listing is live; a missing cover is reported, not hidden
        rec["steps"]["cover"] = f"FAILED: {str(e)[:160]}"
    rec["steps"]["public_page"] = url_ok(rec["url"], man["title"].split(" (")[0], opener=opener) if rec.get("url") else False
    result = SimpleNamespace(ok=rec["steps"]["published"] and rec["steps"]["public_page"], platform="gumroad", product_id=pid,
                             url=rec.get("url"), error=None if rec["steps"]["public_page"] else "public page not verified", dry_run=False)
    ledger.record_publish_attempt(SimpleNamespace(title=man["title"], source_id=man["id"], product_type="xlsx_tool_bundle"), result)
    rec["ok"] = result.ok and rec["steps"]["cover"] == "ok"
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--only", nargs="*", help="publish only these ids, e.g. B14-001")
    ap.add_argument("--batch", choices=sorted(BATCHES), default="batch14")
    a = ap.parse_args()
    global BATCH, RESULTS, AUTHORIZATION
    BATCH, RESULTS, AUTHORIZATION = BATCHES[a.batch]
    mans = [m for m in load_manifests(BATCH) if not a.only or m["id"] in a.only]
    checks = [(m["id"], *preflight(m)[:2]) for m in mans]
    print(json.dumps({"products": len(mans), "preflight": checks}, indent=1))
    if not a.live or not all(c[1] for c in checks):
        print("dry run only" if not a.live else "preflight failed: nothing published")
        return 0 if not a.live else 1
    import gumroad_auth_watch as auth
    state = auth.poll()
    if state.get("status") != "VERIFIED":
        print(json.dumps({"error": f"Gumroad auth state is {state.get('status')}, not VERIFIED"}))
        return 1
    os.environ["FACTORY_LIVE_PUBLISH"] = "true"  # this process only
    from channels import gumroad_publisher as gp, ledger, write_scope
    token = gp.load_token()
    results = []
    try:
        for m in mans:
            try:
                rec = publish_one(m, token, gp=gp, write_scope=write_scope, ledger=ledger, cover_url_fn=lambda i: COVER_URL.format(id=i))
            except Exception as e:
                rec = {"id": m["id"], "title": m["title"], "error": f"{type(e).__name__}: {str(e)[:200]}"}
            results.append(rec)
            print(json.dumps(rec, ensure_ascii=False))
            if rec.get("error"):
                break
    finally:
        os.environ["FACTORY_LIVE_PUBLISH"] = "false"
        prev = json.loads(RESULTS.read_text(encoding="utf-8")) if RESULTS.exists() else []
        RESULTS.write_text(json.dumps(prev + [{"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "authorization": AUTHORIZATION,
                                               "results": results}], indent=1), encoding="utf-8")
    return 0 if results and all(r.get("ok") for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Publish founder-approved products when Gumroad's window allows (2026-10-29).

For factory_loop.js. Every tick:
  1. find registry products in READY_FOR_AUTHORIZATION that belong to a batch
     the publisher knows (scripts/publish_batch14.BATCHES);
  2. run the publisher's own dry-run audit for them; only products whose every
     check passes -- including a VALID per-product approval bound to the exact
     revision, price and currency -- are eligible;
  3. if GF_AUTO_PUBLISH_APPROVED=true, publish as many as Gumroad's rolling
     24-hour creation limit allows, by running the publisher with --live.

No gate is changed: the approval, revision, price, auth-freshness and window
checks are the publisher's own and run again inside the live run. With the
switch off (the default) this only reports what is approved and waiting.

    python scripts/publish_approved_daily.py --once
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
SWITCH = "GF_AUTO_PUBLISH_APPROVED"
APPROVALS = ROOT / "data" / "publication_approvals.json"


def _batch_of(manifest, batches):
    for name, (folder, _results) in batches.items():
        try:
            if (ROOT / manifest).resolve().is_relative_to(Path(folder).resolve()):
                return name
        except (OSError, ValueError):
            continue
    return None


def candidates(registry, batches):
    out = {}
    for p in (registry or {}).get("products", []):
        if p.get("primary_state") != "READY_FOR_AUTHORIZATION" or not p.get("manifest"):
            continue
        b = _batch_of(p["manifest"], batches)
        if b:
            out.setdefault(b, []).append(p["internal_id"])
    return out


def _publisher(args, timeout_s):
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "publish_batch14.py"), *args], cwd=str(ROOT),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout_s)
    try:
        return json.loads(r.stdout)
    except ValueError:
        raise RuntimeError(f"publisher output not JSON (exit {r.returncode}): {r.stderr.strip()[-200:]}")


def eligible(batch, ids, run=_publisher):
    doc = run(["--batch", batch, "--approvals", str(APPROVALS), "--only", *ids], 600)
    return [p.get("id") or p.get("product_id") for p in doc.get("products", []) if p.get("status") == "PASS"]


def run_once(env=os.environ, registry=None, batches=None, window_used=None, run=_publisher, limit=None):
    import publish_batch14 as pb
    batches = batches if batches is not None else pb.BATCHES
    limit = pb.GUMROAD_DAILY_CREATION_LIMIT if limit is None else limit
    if registry is None:
        registry = json.loads((ROOT / "data" / "product_registry.json").read_text(encoding="utf-8"))
    groups = candidates(registry, batches)
    if not groups:
        return {"action": "none", "detail": "no product waiting for publication"}
    ready = {b: eligible(b, ids, run) for b, ids in groups.items()}
    ready = {b: ids for b, ids in ready.items() if ids}
    waiting = sum(len(v) for v in groups.values())
    n_ready = sum(len(v) for v in ready.values())
    if not n_ready:
        return {"action": "none", "detail": f"{waiting} built product(s) waiting; none has a valid approval"}
    if str(env.get(SWITCH, "")).lower() != "true":
        return {"action": "none", "detail": f"{n_ready} approved product(s) ready; auto-publish is off ({SWITCH})"}
    used = pb.creations_in_window(now_ts=time.time()) if window_used is None else window_used
    room = max(0, limit - used)
    if not room:
        return {"action": "none", "detail": f"{n_ready} approved product(s) ready; Gumroad window full ({used}/{limit})"}
    published, failed = [], []
    for batch, ids in ready.items():
        take = ids[:room]
        if not take:
            break
        doc = run(["--batch", batch, "--live", "--approvals", str(APPROVALS), "--only", *take], 1800)
        for r in doc.get("results") or doc.get("products") or []:
            (published if r.get("status") == "PASS" else failed).append(r.get("id"))
        room -= len(take)
    action = "published" if published else "failed"
    return {"action": action, "detail": f"published {len(published)} {published}; not passed {len(failed)} {failed}"}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--once" not in argv:
        print(__doc__)
        return 2
    try:
        out = run_once()
    except Exception as e:  # reported to the loop, never raised into the tick
        out = {"action": "failed", "detail": f"{type(e).__name__}: {str(e)[:200]}"}
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())

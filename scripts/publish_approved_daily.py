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
FREEZE = "GF_FREEZE_NEW_PRODUCTS"  # founder freeze 2026-11-05: wins over SWITCH, deletes nothing
FOUNDER_APPROVED = "GF_PUBLISH_FOUNDER_APPROVED_WHEN_FROZEN"  # opt-in: freeze does not block products carrying a valid founder approval
GATED = "GF_DEMAND_GATED"  # founder 2026-11-05 (second order): the freeze lifts only while demand_gate.py is open
APPROVALS = ROOT / "data" / "publication_approvals.json"


def _demand_gate(env):
    """demand_gate.evaluate() or None when it cannot run: the caller treats None as closed (fail-closed)."""
    try:
        sys.path.insert(0, str(ROOT))
        import demand_gate
        return demand_gate.evaluate(environ=env)
    except Exception:
        return None


def _batch_of(manifest, batches):
    for name, (folder, _results) in batches.items():
        try:
            if (ROOT / manifest).resolve().is_relative_to(Path(folder).resolve()):
                return name
        except (OSError, ValueError):
            continue
    return None


def _live_published_ids(results_path):
    """Ids the batch results file already records as a LIVE PASS. The product registry is rebuilt once a day, so a product published
    mid-day stays READY_FOR_AUTHORIZATION there; without this every loop tick tried to publish it again (blocked by the duplicate
    guard, but noisy and one guard away from a duplicate listing; seen 2026-11-06 with B17-001 at 17:36 and 17:38)."""
    ids = set()
    try:
        doc = json.loads(Path(results_path).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return ids
    for run in doc if isinstance(doc, list) else []:
        if not isinstance(run, dict) or str(run.get("mode", "")).upper() != "LIVE":
            continue
        for r in run.get("results") or []:
            if isinstance(r, dict) and r.get("status") == "PASS" and r.get("product_id"):
                ids.add(r.get("id"))
    return ids


def candidates(registry, batches):
    out = {}
    done = {name: _live_published_ids(res) for name, (_folder, res) in batches.items()}
    for p in (registry or {}).get("products", []):
        if p.get("primary_state") != "READY_FOR_AUTHORIZATION" or not p.get("manifest"):
            continue
        b = _batch_of(p["manifest"], batches)
        if b and p["internal_id"] not in done.get(b, set()):
            out.setdefault(b, []).append(p["internal_id"])
    return out


def _publisher(args, timeout_s):
    # The publisher prints JSON containing non-ASCII text; without this a console-less Windows run encodes it as
    # cp1252 and dies with UnicodeEncodeError (seen 2026-11-06 on a manual run), so the child is told to use UTF-8.
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "publish_batch14.py"), *args], cwd=str(ROOT),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout_s,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    try:
        return json.loads(r.stdout)
    except ValueError:
        raise RuntimeError(f"publisher output not JSON (exit {r.returncode}): {r.stderr.strip()[-200:]}")


def eligible(batch, ids, run=_publisher):
    doc = run(["--batch", batch, "--approvals", str(APPROVALS), "--only", *ids], 600)
    return [p.get("id") or p.get("product_id") for p in doc.get("products", []) if p.get("status") == "PASS"]


FOLLOWUP_STATES = ("tool_pages_daily_state.json", "indexnow_auto.json", "listing_health_state.json")


def reopen_daily_followups(data_dir=None):
    """A product published mid-day must not wait until tomorrow for its tool page, IndexNow ping and listing check: those steps are
    gated once per UTC day and had already run. Clear their own day marker so the next loop tick runs them again (2026-11-06)."""
    d = Path(data_dir) if data_dir else ROOT / "data"
    cleared = []
    for name in FOLLOWUP_STATES:
        f = d / name
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(doc, dict) and doc.get("last_day"):
                doc["last_day"] = None
                tmp = Path(str(f) + ".tmp")
                tmp.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
                tmp.replace(f)
                cleared.append(name)
        except (OSError, ValueError):
            continue
    return cleared


def run_once(env=os.environ, registry=None, batches=None, window_used=None, run=_publisher, limit=None):
    gate_cap = None
    if str(env.get(FREEZE, "")).lower() == "true":
        gate = _demand_gate(env) if str(env.get(GATED, "")).lower() == "true" else None
        if gate and gate.get("open"):
            gate_cap = int(gate.get("daily_cap") or 0)
        elif str(env.get(FOUNDER_APPROVED, "")).lower() != "true":
            why = (gate or {}).get("why") or "demand gate not enabled"
            return {"action": "none", "detail": f"new products frozen ({FREEZE}=true), {why}: nothing is published"}
        # else: GF_PUBLISH_FOUNDER_APPROVED_WHEN_FROZEN=true. The freeze stops AUTOMATIC additions; a product with a valid
        # per-product founder approval is the founder's own act, so it may still go out. eligible() below only passes
        # products whose approval validates (id, price, currency, actions, expiry, revision), nothing else is published.
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
    if gate_cap is not None:
        room = min(room, gate_cap)
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
    if published:
        reopen_daily_followups()
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

"""Backlog B27 (2026-10-29): move test-fixture rows out of live ledgers.

A full pytest run on 2026-10-29 (00:16-00:46Z) wrote fixture rows into live
ledgers because several tests use default paths (backlog B5). The founder granted
execution authority for this on 2026-10-29. Nothing is deleted:

  data/quarantine/B27_20261029/backup/<file>      full copy of each file before the change
  data/quarantine/B27_20261029/<file>.rows.jsonl  each moved row with its line number and reason
  data/quarantine/B27_20261029/manifest.json      rules, counts, sha256 before/after

Only rows matching BOTH the run's time window AND a fixture signature traced to a
named test are moved. Rows from the same window that could be real (factory loop
output, the reality_audit evidence records, an unexplained page view) stay.

Run with --apply to change files; without it, it reports what it would move.
The rewrite re-reads each file immediately before replacing it and aborts that
file if it changed (the factory loop appends to some ledgers).
"""
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QDIR = os.path.join(ROOT, "data", "quarantine", "B27_20261029")


def _ts(r):
    for k in ("timestamp", "created_at", "at", "generated_at"):
        v = r.get(k)
        if isinstance(v, str):
            return v
    return ""


def in_window(r, start, end):
    return start <= _ts(r) < end


DESIGN_BURST = ("2026-10-29T00:16:56", "2026-10-29T00:16:58")
RUN_WINDOW = ("2026-10-29T00:16", "2026-10-29T00:47")

RULES = {
    "design_audit.jsonl": (lambda r: in_window(r, *DESIGN_BURST),
                           "1-second burst from tests/test_canva_e2e.py / test_canva_failures.py "
                           "(DesignPipeline has no non-test caller)"),
    "design_candidates.jsonl": (lambda r: in_window(r, *DESIGN_BURST), "same burst"),
    "design_approvals.jsonl": (lambda r: in_window(r, *DESIGN_BURST), "same burst"),
    "distribution_events.jsonl": (
        lambda r: in_window(r, *RUN_WINDOW) and (
            (r.get("record") or {}).get("product_id") == "PRD-001" or "asset1.pdf" in json.dumps(r)
            or r.get("distribution_id") == "DIST-e88c273b"),
        "tests/test_distribution_engine.py fixture (PRD-001, asset1.pdf)"),
    "recovery_actions.jsonl": (
        lambda r: in_window(r, *RUN_WINDOW) and r.get("error") == "e" and r.get("component") == "webhook",
        "tests/test_autonomous_commerce_ops.py fixture (error 'e')"),
    "arm5_attribution.jsonl": (
        lambda r: in_window(r, *RUN_WINDOW) and r.get("source") == "src" and r.get("evidence") == "h",
        "tests/test_attribution_engine.py fixture (source 'src', evidence 'h')"),
}


# Pass 2 (same day): the same fixture signatures across all dates. Each one is
# an exact value set written by a named test, never by production code.
HQDIR = os.path.join(ROOT, "data", "quarantine", "B27_historical_20261029")


def _fixture_distribution_ids(path):
    ids = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            rec = r.get("record") if isinstance(r, dict) else None
            if isinstance(rec, dict) and rec.get("product_id") == "PRD-001" and rec.get("distribution_id"):
                ids.add(rec["distribution_id"])
    return ids


def historical_rules(root=ROOT):
    dist_ids = _fixture_distribution_ids(os.path.join(root, "data", "distribution_events.jsonl"))         if os.path.exists(os.path.join(root, "data", "distribution_events.jsonl")) else set()
    return {
        "recovery_actions.jsonl": (
            lambda r: r.get("error") == "e" and r.get("component") == "webhook",
            "tests/test_autonomous_commerce_ops.py fixture (component webhook, error 'e')"),
        "arm5_attribution.jsonl": (
            lambda r: r.get("source") == "src" and r.get("evidence") == "h",
            "tests/test_attribution_engine.py fixture (source 'src', evidence 'h')"),
        "distribution_events.jsonl": (
            lambda r: (r.get("distribution_id") in dist_ids)
            or ((r.get("record") or {}).get("distribution_id") in dist_ids),
            "tests/test_distribution_engine.py fixture (distributions created for product PRD-001)"),
    }


RESTORE_TEST_QDIR = os.path.join(ROOT, "data", "quarantine", "B36_restore_test_20261029")


def restore_test_rules():
    """Pass 3: rows tests/test_restore_file_from_git.js appended before it was
    moved to a temporary repository (exact reasons and targets from that test)."""
    reasons = {"regression test (no-op restore to HEAD)": ["CLAUDE.md"],
               "regression test (no prior local file)": ["requirements.txt"]}
    return {"recovery_actions.jsonl": (
        lambda r: r.get("reason") in reasons and r.get("affected_systems") == reasons[r.get("reason")],
        "tests/test_restore_file_from_git.js (before 2026-10-29 it wrote to the live ledger)")}


DESIGN_QDIR = os.path.join(ROOT, "data", "quarantine", "B36_design_ledgers_20261029")
DESIGN_FIXTURE_PRODUCTS = {"EU AI Act Compliance Toolkit", "Failure Test Product", "Test Product", "Test", "T"}


def design_ledger_rules():
    """Pass 4 (B36): the three design ledgers hold only test output. Verified
    2026-10-29: canva_autodesign/DesignPipeline has no non-test caller; every
    SPEC_STRUCTURED row names one of the fixture products defined in
    tests/test_canva_e2e.py / tests/test_canva_failures.py; 90 of 92 write-minutes
    are bursts of 10+ rows; no site page, product or script references
    data/design_output. Every row of the three files is moved."""
    why = ("test output of tests/test_canva_e2e.py and tests/test_canva_failures.py "
           "(DesignPipeline has no non-test caller; only fixture products appear)")
    return {name: (lambda r: True, why)
            for name in ("design_audit.jsonl", "design_candidates.jsonl", "design_approvals.jsonl")}


def design_fixture_check(root=ROOT):
    """Refuse the pass if any row names a product that is not a test fixture."""
    path = os.path.join(root, "data", "design_audit.jsonl")
    if not os.path.exists(path):
        return []
    foreign = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            p = (r.get("details") or {}).get("product")
            if p and p not in DESIGN_FIXTURE_PRODUCTS:
                foreign.add(p)
    return sorted(foreign)


def all_design_images(root=ROOT):
    d = os.path.join(root, "data", "design_output")
    return sorted(os.path.join(d, n) for n in os.listdir(d)) if os.path.isdir(d) else []


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def plan(root=ROOT, rules=None):
    out = {}
    for name, (match, why) in (rules or RULES).items():
        path = os.path.join(root, "data", name)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8", newline="") as f:
            lines = f.readlines()
        moved = []
        for i, line in enumerate(lines):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if isinstance(r, dict) and match(r):
                moved.append(i)
        out[name] = {"path": path, "lines": lines, "moved": moved, "why": why}
    return out


def design_images(root=ROOT):
    d = os.path.join(root, "data", "design_output")
    if not os.path.isdir(d):
        return []
    lo = datetime.fromisoformat(DESIGN_BURST[0] + "+00:00").timestamp()
    hi = datetime.fromisoformat(DESIGN_BURST[1] + "+00:00").timestamp()
    return sorted(os.path.join(d, n) for n in os.listdir(d) if lo <= os.path.getmtime(os.path.join(d, n)) < hi)


def apply(root=ROOT, qdir=QDIR, rules=None, images=True):
    p = plan(root, rules)
    os.makedirs(os.path.join(qdir, "backup"), exist_ok=True)
    manifest = {"created_at": datetime.now(timezone.utc).isoformat(), "authority": "founder, 2026-10-29",
                "rules": {k: v[1] for k, v in (rules or RULES).items()}, "files": {}, "images": []}
    for name, info in p.items():
        if not info["moved"]:
            continue
        path, lines = info["path"], info["lines"]
        before = sha(path)
        shutil.copy2(path, os.path.join(qdir, "backup", name))
        with open(os.path.join(qdir, name + ".rows.jsonl"), "w", encoding="utf-8") as f:
            for i in info["moved"]:
                f.write(json.dumps({"line": i + 1, "reason": info["why"], "row": json.loads(lines[i])},
                                   ensure_ascii=False) + "\n")
        keep = [l for i, l in enumerate(lines) if i not in set(info["moved"])]
        if sha(path) != before:  # appended to while we worked: leave it alone
            manifest["files"][name] = {"status": "SKIPPED_CHANGED_DURING_RUN"}
            continue
        tmp = path + ".b27tmp"
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            f.writelines(keep)
        os.replace(tmp, path)
        manifest["files"][name] = {"status": "MOVED", "rows_before": len(lines), "rows_moved": len(info["moved"]),
                                   "rows_after": len(keep), "sha256_before": before, "sha256_after": sha(path)}
    imgdir = os.path.join(qdir, "design_output")
    image_list = (all_design_images(root) if images == "all" else design_images(root)) if images else []
    for img in image_list:
        os.makedirs(imgdir, exist_ok=True)
        dst = os.path.join(imgdir, os.path.basename(img))
        shutil.move(img, dst)
        manifest["images"].append({"from": os.path.relpath(img, root).replace(os.sep, "/"),
                                   "to": os.path.relpath(dst, root).replace(os.sep, "/")})
    with open(os.path.join(qdir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    return manifest


if __name__ == "__main__":
    if "--design-ledgers" in sys.argv:
        foreign = design_fixture_check()
        if foreign:
            print(json.dumps({"refused": "non-fixture products present", "products": foreign}, indent=1))
            sys.exit(1)
        rules = design_ledger_rules()
        if "--apply" in sys.argv:
            m = apply(qdir=DESIGN_QDIR, rules=rules, images="all")
            print(json.dumps({k: v.get("rows_moved", v.get("status")) for k, v in m["files"].items()}
                             | {"images_moved": len(m["images"])}, indent=1))
        else:
            print(json.dumps({k: len(v["moved"]) for k, v in plan(rules=rules).items()}
                             | {"images": len(all_design_images())}, indent=1))
        sys.exit(0)
    if "--restore-test" in sys.argv:
        rules = restore_test_rules()
        if "--apply" in sys.argv:
            m = apply(qdir=RESTORE_TEST_QDIR, rules=rules, images=False)
            print(json.dumps({k: v.get("rows_moved", v.get("status")) for k, v in m["files"].items()}, indent=1))
        else:
            print(json.dumps({k: len(v["moved"]) for k, v in plan(rules=rules).items()}, indent=1))
        sys.exit(0)
    if "--historical" in sys.argv:
        rules = historical_rules()
        if "--apply" in sys.argv:
            m = apply(qdir=HQDIR, rules=rules, images=False)
            print(json.dumps({k: v.get("rows_moved", v.get("status")) for k, v in m["files"].items()}, indent=1))
        else:
            print(json.dumps({k: len(v["moved"]) for k, v in plan(rules=rules).items()}, indent=1))
        sys.exit(0)
    if "--apply" in sys.argv:
        m = apply()
        print(json.dumps({k: v.get("rows_moved", v.get("status")) for k, v in m["files"].items()}
                         | {"images_moved": len(m["images"])}, indent=1))
    else:
        p = plan()
        print(json.dumps({k: len(v["moved"]) for k, v in p.items()} | {"images": len(design_images())}, indent=1))

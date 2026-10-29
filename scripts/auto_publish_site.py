#!/usr/bin/env python3
"""Push site-page-only commits to origin/main automatically (2026-10-23).

Founder authorization (2026-10-23): "the loop pushes site-page updates
automatically once they pass the tests". Scope is exactly that:

  - every commit in origin/main..main may touch only SITE_PATHS (customer_site/,
    sitemap.xml, robots.txt, the IndexNow key file). A range containing any
    other file is NOT pushed: code changes still need a reviewed manual push;
  - no commit may add a product-like binary (.pdf .xlsx .docx .zip .epub .pptx)
    or a path the current .gitignore excludes -- the repository is public;
  - origin/main must be an ancestor of main (fast-forward only, never --force);
  - the site test files and the secret scan must pass on the committed tree;
  - if the last push made by this script failed CI, nothing is pushed again
    until origin/main moves (someone fixed it by hand).

  python scripts/auto_publish_site.py --once      # check, test, push
  python scripts/auto_publish_site.py --dry-run   # report only
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "data" / "auto_publish_site.json"
SITE_PATHS = re.compile(r"^(customer_site/|sitemap\.xml$|robots\.txt$|c8742f1da91ebe577587681839ae0004\.txt$)")
PRODUCT_LIKE = re.compile(r"\.(pdf|xlsx|xlsm|docx|zip|epub|pptx)$", re.I)
SITE_TESTS_PY = ["tests/test_affiliate_disclosure_placement.py", "tests/test_affiliate_static.py",
                 "tests/test_content_qa_terms_and_tokens.py", "tests/test_cycle82.py",
                 "tests/test_exp_c81_utm_regression.py", "tests/test_hold_promotion.py",
                 "tests/test_no_committed_affiliate_links.py", "tests/test_seo_distribution.py"]
SITE_TESTS_JS = ["tests/test_customer_front_door.js", "tests/test_gf_pageview.js"]
REPO = "galaxyaek7-del/openclaw-factory"


def git(*args, check=True):
    p = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:2])} failed: {p.stderr.strip()[:200]}")
    return p.stdout


def changed_paths(commit):
    """(status, path) pairs a commit adds/modifies/deletes relative to its first parent."""
    out = git("diff-tree", "--no-commit-id", "-r", "--name-status", "-m", "--first-parent", commit)
    return [tuple(l.split("\t", 1)) for l in out.splitlines() if "\t" in l]


def review_range(commits, is_ignored):
    """-> (ok, reason). Pure: callers pass the commits and an ignore checker."""
    for c, paths in commits:
        for status, path in paths:
            path = path.split("\t")[-1]
            if status[0] in "AMR" and PRODUCT_LIKE.search(path):
                return False, f"{c[:7]} adds a product-like file {path}"
            if status[0] in "AMR" and is_ignored(path):
                return False, f"{c[:7]} adds {path}, which .gitignore excludes"
            if not SITE_PATHS.match(path):
                return False, f"{c[:7]} touches {path}: not a site page, needs a reviewed manual push"
    return True, "site pages only"


def is_ignored(path):
    return subprocess.run(["git", "check-ignore", "-q", "--no-index", path], cwd=ROOT).returncode == 0


def run_gate(tree_dir):
    env = dict(os.environ, CI="true", PYTHONIOENCODING="utf-8")
    steps = [[sys.executable, "scripts/scan_for_secrets.py"],
             [sys.executable, "-m", "pytest", "-q", *SITE_TESTS_PY],
             ["node", "--test", *SITE_TESTS_JS]]
    for cmd in steps:
        p = subprocess.run(cmd, cwd=tree_dir, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=900)
        if p.returncode != 0:
            return False, f"{' '.join(cmd[1:3])} failed: {(p.stdout + p.stderr).strip().splitlines()[-1:]}"
    return True, "secret scan and site tests passed"


def ci_conclusion(sha):
    """'success' | 'failure' | 'pending' | None (unknown), from the public Actions API."""
    try:
        req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/actions/runs?head_sha={sha}&per_page=20",
                                     headers={"User-Agent": "GalaxyForge-auto-publish", "Accept": "application/vnd.github+json"})
        runs = [r for r in json.load(urllib.request.urlopen(req, timeout=20)).get("workflow_runs", []) if r.get("name") == "CI"]
    except Exception:
        return None
    if not runs:
        return None
    r = runs[0]
    if r.get("status") != "completed":
        return "pending"
    return "success" if r.get("conclusion") == "success" else "failure"


def read_state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def write_state(s):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, indent=1), encoding="utf-8")
    os.replace(tmp, STATE)


def run(dry_run=False):
    git("fetch", "-q", "origin", "main")
    origin, head = git("rev-parse", "origin/main").strip(), git("rev-parse", "main").strip()
    if origin == head:
        return {"action": "none", "detail": "nothing to publish (main == origin/main)"}
    if subprocess.run(["git", "merge-base", "--is-ancestor", origin, head], cwd=ROOT).returncode != 0:
        return {"action": "blocked", "detail": "main and origin/main have diverged; not a fast-forward, never forced"}
    state = read_state()
    last = state.get("last_push")
    if last and last.get("origin_before") is not None and origin == last.get("sha"):
        if ci_conclusion(last["sha"]) == "failure":
            return {"action": "blocked", "detail": f"CI failed for the last automatic push {last['sha'][:7]}; waiting for a manual fix"}
    commits = [(c, changed_paths(c)) for c in git("rev-list", "--reverse", f"{origin}..{head}").split()]
    ok, why = review_range(commits, is_ignored)
    if not ok:
        return {"action": "none", "detail": f"{len(commits)} unpublished commits; {why}"}
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(f'git archive {head} | tar -x -C "{d}"', cwd=ROOT, shell=True, check=True)
        nm = ROOT / "node_modules"
        if nm.exists():
            os.symlink(nm, Path(d) / "node_modules", target_is_directory=True) if os.name != "nt" else \
                subprocess.run(["cmd", "/c", "mklink", "/J", str(Path(d) / "node_modules"), str(nm)], capture_output=True)
        ok, why = run_gate(d)
    if not ok:
        return {"action": "blocked", "detail": f"gate failed, not pushed: {why}"}
    if dry_run:
        return {"action": "dry_run", "detail": f"would push {len(commits)} site-only commits ({why})"}
    git("push", "origin", f"{head}:refs/heads/main")
    # Merge, not replace: keeps outage_open_since so the outage can be closed after this run.
    write_state({**read_state(), "last_push": {"sha": head, "origin_before": origin, "commits": len(commits)}})
    return {"action": "pushed", "detail": f"{len(commits)} site-only commits pushed ({head[:7]}); {why}"}


# 2026-10-29: 23 of 109 runs in a day were reported "failed" only because github.com
# could not be reached (the host loses its network most mornings). They are now
# "deferred" with reason "network", and each outage is recorded once as a window
# (start, end, minutes) so real publishing failures are not buried in outage noise
# and the outage pattern is measurable. Nothing about what may be pushed changes.
OUTAGES = ROOT / "data" / "network_outages.jsonl"
NETWORK_ERRORS = ("could not resolve host", "failed to connect", "connection timed out",
                  "operation timed out", "connection reset", "network is unreachable",
                  "could not connect to server", "timed out after")


def is_network_error(text):
    t = (text or "").lower()
    return any(p in t for p in NETWORK_ERRORS)


def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def record_outage(reachable, detail="", now=None, outages=None, state=None):
    """Open an outage record on the first unreachable run, close it on the first
    reachable one. Returns (event written or None, updated state)."""
    outages = outages or OUTAGES
    state = dict(state if state is not None else read_state())
    now = now or _now()
    open_since = state.get("outage_open_since")
    event = None
    if not reachable and not open_since:
        state["outage_open_since"] = now
        event = {"event": "github_unreachable", "start": now, "detail": detail[:200]}
    elif reachable and open_since:
        from datetime import datetime
        minutes = round((datetime.fromisoformat(now) - datetime.fromisoformat(open_since)).total_seconds() / 60, 1)
        state.pop("outage_open_since", None)
        event = {"event": "github_reachable_again", "start": open_since, "end": now, "minutes": minutes}
    if event:
        outages.parent.mkdir(parents=True, exist_ok=True)
        with open(outages, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event, state


def classify_and_record(run_fn, dry_run=False, outages=None, state_reader=None, state_writer=None,
                        now=None):
    state_reader = state_reader or read_state
    state_writer = state_writer or write_state
    try:
        r = run_fn(dry_run=dry_run)
        reachable = True
    except Exception as e:
        detail = f"{type(e).__name__}: {str(e)[:200]}"
        if not is_network_error(str(e)):
            return {"action": "failed", "detail": detail}
        r = {"action": "deferred", "reason": "network", "detail": detail}
        reachable = False
    event, state = record_outage(reachable, r.get("detail", ""), now=now, outages=outages, state=state_reader())
    if event:
        state_writer(state)
        if reachable:
            r["outage_closed_minutes"] = event["minutes"]
        else:
            r["outage"] = "opened"
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    r = classify_and_record(run, dry_run=a.dry_run)
    sys.stdout.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()

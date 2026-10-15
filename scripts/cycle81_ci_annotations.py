"""Cycle 81 Phase 2: get the failing test via the Checks API annotations.

scripts/run_python_group.py exists precisely because the logs API is not
readable unauthenticated: it emits ::error:: lines so the failing test shows up
in check annotations. So the failing test name is reachable without auth --
through a different endpoint than the one that returned 403.
"""
import json
import subprocess
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

remote = subprocess.run(["git", "remote", "get-url", "origin"],
                        capture_output=True, text=True).stdout.strip()
repo = remote.split("github.com/")[1].replace(".git", "")
hdr = {"User-Agent": "cycle81", "Accept": "application/vnd.github+json"}


def api(path):
    return json.load(urllib.request.urlopen(
        urllib.request.Request(f"https://api.github.com/repos/{repo}{path}",
                               headers=hdr), timeout=45))


sha = subprocess.run(["git", "rev-parse", "HEAD"],
                     capture_output=True, text=True).stdout.strip()
print(f"repo: {repo}\nHEAD: {sha[:12]}\n")

# The latest CI run for main
runs = api("/actions/runs?branch=main&per_page=10")["workflow_runs"]
ci = next((r for r in runs if r["name"] == "CI"), None)
if not ci:
    print("no CI run found")
    sys.exit(0)
print(f"CI run {ci['id']} sha={ci['head_sha'][:7]} -> {ci['conclusion']}")
print(f"  {ci['html_url']}\n")

out = {"probe": "cycle81_ci_annotations", "run_id": ci["id"],
       "run_url": ci["html_url"], "sha": ci["head_sha"],
       "conclusion": ci["conclusion"], "annotations": []}

# Check runs for this commit
checks = api(f"/commits/{ci['head_sha']}/check-runs?per_page=50")
print(f"check runs: {checks['total_count']}")
for cr in checks.get("check_runs", []):
    if cr["name"] not in ("test", "CI"):
        continue
    print(f"\n  check run: {cr['name']} -> {cr['conclusion']}")
    raw = api(f"/check-runs/{cr['id']}/annotations?per_page=100")
    # This endpoint returns a bare list, not a {total_count, ...} envelope.
    anns = raw if isinstance(raw, list) else raw.get("check_run_annotations", [])
    print(f"  annotations: {len(anns)}")
    for a in anns:
        rec = {"path": a.get("path"), "start_line": a.get("start_line"),
               "title": a.get("title"), "message": a.get("message"),
               "annotation_level": a.get("annotation_level")}
        out["annotations"].append(rec)
        print(f"\n  --- {a.get('annotation_level')}: {a.get('title')}")
        print(f"      path: {a.get('path')}:{a.get('start_line')}")
        print(f"      {a.get('message')[:1200]}")

if not out["annotations"]:
    print("\nno annotations returned")

json.dump(out, open("data/cycle81_ci_annotations.json", "w", encoding="utf-8"),
          indent=2, ensure_ascii=False)
print("\nwrote data/cycle81_ci_annotations.json")
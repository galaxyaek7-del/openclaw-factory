"""Cycle 85: report the actual CI result for the commits pushed this cycle."""
import json
import subprocess
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

remote = subprocess.run(["git", "remote", "get-url", "origin"],
                        capture_output=True, text=True).stdout.strip()
repo = remote.split("github.com/")[1].replace(".git", "")
print("repo:", repo)

url = f"https://api.github.com/repos/{repo}/actions/runs?branch=main&per_page=4"
try:
    req = urllib.request.Request(
        url, headers={"User-Agent": "cycle85", "Accept": "application/vnd.github+json"})
    d = json.load(urllib.request.urlopen(req, timeout=25))
    runs = d.get("workflow_runs", [])
    if not runs:
        print("no workflow runs returned")
    for r in runs:
        print(f"  {r['head_sha'][:7]}  {r['status']:11s} {str(r['conclusion']):9s} "
              f"{r['name']:6s} {r['created_at']}")
except Exception as e:
    # Unauthenticated API is rate-limited; say so rather than imply CI passed.
    print(f"CI STATUS UNKNOWN -- could not query the Actions API unauthenticated: "
          f"{type(e).__name__}")
    print("This is reported as UNKNOWN, not as a pass.")
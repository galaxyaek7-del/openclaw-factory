"""Cycle 81 Phase 2: CI forensics for main.

gh is not installed and no GITHUB_TOKEN is present, so this uses the public
Actions API. Logs are fetched where access permits; where it does not, the
result is reported as BLOCKED rather than as a pass.
"""
import io
import json
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

remote = subprocess.run(["git", "remote", "get-url", "origin"],
                        capture_output=True, text=True).stdout.strip()
repo = remote.split("github.com/")[1].replace(".git", "")
hdr = {"User-Agent": "cycle81", "Accept": "application/vnd.github+json"}


def get(url, raw=False):
    r = urllib.request.urlopen(urllib.request.Request(url, headers=hdr),
                               timeout=45)
    return r.read() if raw else json.load(r)


def api(path):
    return get(f"https://api.github.com/repos/{repo}{path}")


runs = api("/actions/runs?branch=main&per_page=10")["workflow_runs"]
print(f"repo: {repo}\n")

out = {"probe": "cycle81_ci_forensics", "repo": repo, "runs": []}

for r in runs[:6]:
    rec = {"run_id": r["id"], "sha": r["head_sha"][:12], "name": r["name"],
           "status": r["status"], "conclusion": r["conclusion"],
           "url": r["html_url"], "created": r["created_at"], "jobs": []}
    jobs = api(f"/actions/runs/{r['id']}/jobs?per_page=50")["jobs"]
    for j in jobs:
        failed_steps = [s["name"] for s in j.get("steps", [])
                        if s.get("conclusion") == "failure"]
        rec["jobs"].append({
            "job": j["name"], "conclusion": j["conclusion"],
            "failed_steps": failed_steps,
            "started": j.get("started_at"), "completed": j.get("completed_at"),
        })
    ok = sum(1 for j in rec["jobs"] if j["conclusion"] == "success")
    rec["jobs_ok"] = ok
    rec["jobs_total"] = len(rec["jobs"])
    out["runs"].append(rec)

    if r["name"] != "CI":
        continue
    print(f"CI run {r['id']}  sha={r['head_sha'][:7]}  -> {r['conclusion'].upper()}")
    print(f"   url: {r['html_url']}")
    print(f"   jobs: {ok}/{len(jobs)} succeeded")
    for j in jobs:
        if j["conclusion"] != "success":
            print(f"   FAILED JOB: {j['name']}")
            for s in j.get("steps", []):
                mark = "x" if s.get("conclusion") == "failure" else " "
                print(f"     [{mark}] {s['name']}")
    print()

# Log availability
latest_ci = next((r for r in runs if r["name"] == "CI"), None)
if latest_ci:
    try:
        blob = get(f"/repos/{repo}/actions/runs/{latest_ci['id']}/logs", raw=True)
        out["logs_available"] = True
        zf = zipfile.ZipFile(io.BytesIO(blob))
        names = zf.namelist()
        print(f"logs: AVAILABLE ({len(names)} entries)")
        out["log_entries"] = len(names)
        # find the failing test job log
        for n in names:
            if "test" in n.lower() and n.endswith(".txt"):
                txt = zf.read(n).decode("utf-8", "replace")
                if "FAILED" in txt or "AssertionError" in txt or "Error" in txt:
                    out["failing_log_entry"] = n
                    idx = txt.find("::error::")
                    out["first_error"] = txt[idx:idx + 1200] if idx != -1 else None
                    break
    except urllib.error.HTTPError as e:
        out["logs_available"] = False
        out["logs_error"] = f"HTTP {e.code}"
        print(f"logs: BLOCKED - HTTP {e.code} (unauthenticated API cannot fetch)")
    except Exception as e:
        out["logs_available"] = False
        out["logs_error"] = type(e).__name__
        print(f"logs: BLOCKED - {type(e).__name__}")

json.dump(out, open("data/cycle81_ci_forensics.json", "w", encoding="utf-8"),
          indent=2, ensure_ascii=False)
print("\nwrote data/cycle81_ci_forensics.json")
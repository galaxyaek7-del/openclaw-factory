import json, urllib.request, ssl, os, datetime
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
out = {"at": now, "internal": {}, "external": {}, "inbound": {}}

# INTERNAL: processes
try:
    import subprocess
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
        "Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" | Select-Object ProcessId,CreationDate,CommandLine | ConvertTo-Json"],
        capture_output=True, text=True, timeout=20)
    out["internal"]["node_processes"] = r.stdout[:800]
except Exception as e:
    out["internal"]["node_processes"] = ("ERR " + str(e))[:100]

# INTERNAL: health + metrics endpoints (local server)
def get(path, timeout=12):
    try:
        req = urllib.request.Request("http://localhost:3000" + path, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=timeout)
        return {"status": resp.status, "body_len": len(resp.read())}
    except Exception as e:
        return {"error": str(e)[:120]}
out["internal"]["health"] = get("/api/v1/health")
out["internal"]["metrics"] = get("/api/v1/metrics.json")
out["internal"]["site_root"] = get("/site/")

# INTERNAL: factory_loop marker files (daily ticks alive?)
import glob
markers = {}
for f in sorted(glob.glob("data/.*marker*")) + sorted(glob.glob("data/*marker*")):
    try:
        markers[os.path.basename(f)] = open(f, encoding="utf-8", errors="replace").read().strip()[:40]
    except Exception:
        pass
out["internal"]["tick_markers"] = markers

# EXTERNAL: key surfaces
ctx = ssl.create_default_context()
def head(url, timeout=12):
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        return {"status": resp.status}
    except Exception as e:
        return {"error": str(e)[:100]}
targets = {
    "gumroad_product": "https://aekraft.gumroad.com/l/fetmu",
    "telegraph_gpsr": "https://telegra.ph/GPSR-EU-Seller-Action-Kit-Non-EU-Seller-Compliance-Guide-2026-10-02",
    "telegraph_ftc": "https://telegra.ph/FTC-Consumer-Review-Rule-Compliance-Guide-for-Small-Businesses-2026-10-02",
    "systeme": "https://systeme.io",
    "github_repo": "https://api.github.com/repos/openclaw/openclaw-dashboard",
}
for k, u in targets.items():
    out["external"][k] = head(u)

# INBOUND: local endpoints (no writes except interest reject-path which writes nothing)
def post(path, payload, timeout=25):
    try:
        d = json.dumps(payload).encode()
        req = urllib.request.Request("http://localhost:3000" + path, data=d, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=timeout)
        return {"status": resp.status, "body": resp.read()[:120].decode("utf-8", "replace")}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "body": e.read()[:120].decode("utf-8", "replace")}
    except Exception as e:
        return {"error": str(e)[:120]}
import urllib.error
out["inbound"]["page_view"] = post("/api/page-view", {"page_id": "arm-audit-probe"})
out["inbound"]["interest_reject"] = post("/api/customer/interest", {"email": "probe@example.com", "message": "TEST_EVENT arm audit probe"})
out["inbound"]["support_validation"] = post("/api/customer/support-ticket", {"name": "", "email": "x", "message": ""})

with open("data/arm_audit_full.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
print(json.dumps(out, indent=1)[:3000])

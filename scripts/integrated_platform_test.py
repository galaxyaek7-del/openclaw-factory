"""Integrated platform test — ALL arms, reads only. No writes, no spend."""
import json, urllib.request, ssl, os, datetime, sys
sys.path.insert(0, '.')
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
ctx = ssl.create_default_context()
R = {"at": now, "results": {}}

def head(name, url, timeout=12):
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
        s = urllib.request.urlopen(req, timeout=timeout, context=ctx).status
        R["results"][name] = {"transport": "HEAD", "status": s, "verdict": "PASS" if s == 200 else "FAIL"}
    except Exception as e:
        R["results"][name] = {"transport": "HEAD", "error": str(e)[:100], "verdict": "FAIL"}

def local_post(name, path, payload, expect, timeout=30):
    try:
        d = json.dumps(payload).encode()
        req = urllib.request.Request("http://localhost:3000" + path, data=d, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=timeout)
        ok = resp.status == expect
        R["results"][name] = {"transport": "POST", "status": resp.status, "verdict": "PASS" if ok else "FAIL"}
    except urllib.error.HTTPError as e:
        R["results"][name] = {"transport": "POST", "status": e.code, "verdict": "PASS" if e.code == expect else "FAIL"}
    except Exception as e:
        R["results"][name] = {"transport": "POST", "error": str(e)[:100], "verdict": "FAIL"}
import urllib.error

# External surfaces
head("gumroad_product", "https://aekraft.gumroad.com/l/fetmu")
head("gumroad_leadlists", "https://aekraft.gumroad.com/l/drtaj")
head("telegraph_gpsr", "https://telegra.ph/GPSR-EU-Seller-Action-Kit-Non-EU-Seller-Compliance-Guide-2026-10-02")
head("telegraph_ftc", "https://telegra.ph/FTC-Consumer-Review-Rule-Compliance-Guide-for-Small-Businesses-2026-10-02")
head("systeme", "https://systeme.io")
head("site_local", "http://localhost:3000/site/")

# Platform APIs (public, no auth)
try:
    req = urllib.request.Request("https://www.freelancer.com/api/projects/0.1/projects/active/?compact=true&limit=1", headers={"User-Agent": "Mozilla/5.0"})
    d = json.loads(urllib.request.urlopen(req, timeout=15, context=ctx).read())
    n = len(d.get("result", {}).get("projects", []))
    R["results"]["freelancer_api"] = {"status": 200, "projects": n, "verdict": "PASS"}
except Exception as e:
    R["results"]["freelancer_api"] = {"error": str(e)[:100], "verdict": "FAIL"}

# Arm statuses (in-process, reads only)
try:
    import channels.gumroad_arm, channels.paddle_arm, channels.etsy_arm, channels.payhip_arm, channels.kdp_arm, channels.x_arm
    from channels.registry import get
    for name in ["gumroad", "paddle", "etsy", "payhip", "kdp", "x"]:
        try:
            st = str(get(name).status())
            R["results"][f"arm_{name}"] = {"status": st, "verdict": "PASS"}
        except Exception as e:
            R["results"][f"arm_{name}"] = {"error": str(e)[:80], "verdict": "FAIL"}
    # Live reads where available
    try:
        r = get("gumroad").list_products()
        R["results"]["gumroad_list"] = {"count": len(r.get("products", [])), "verdict": "PASS" if r.get("status") == "OK" else "FAIL"}
    except Exception as e:
        R["results"]["gumroad_list"] = {"error": str(e)[:80], "verdict": "FAIL"}
    try:
        r = get("paddle").list_products()
        R["results"]["paddle_list"] = {"status": r.get("status"), "verdict": "PASS" if r.get("status") == "OK" else "FAIL"}
    except Exception as e:
        R["results"]["paddle_list"] = {"error": str(e)[:80], "verdict": "FAIL"}
except Exception as e:
    R["results"]["arms"] = {"error": str(e)[:100], "verdict": "FAIL"}

# Inbound loops (validation paths only — write nothing)
local_post("inbound_pageview", "/api/page-view", {"page_id": 12345}, 400)
local_post("inbound_interest_reject", "/api/customer/interest", {"email": "probe@example.com", "message": "TEST_EVENT integrated test"}, 400)
local_post("inbound_support_validate", "/api/customer/support-ticket", {"name": "", "email": "x", "message": ""}, 400)

# Sales truth
R["results"]["sales_poll"] = {"verdict": "PENDING", "note": "run via poll_sales.py separately"}

# Summary
vals = [v.get("verdict") for v in R["results"].values()]
R["summary"] = {"total": len(vals), "pass": sum(1 for v in vals if v == "PASS"), "fail": sum(1 for v in vals if v == "FAIL"), "pending": sum(1 for v in vals if v == "PENDING")}
with open("data/integrated_platform_test.json", "w", encoding="utf-8") as f:
    json.dump(R, f, indent=1)
print(json.dumps(R["summary"], indent=1))
for k, v in R["results"].items():
    print(f"  {k}: {v.get('verdict')} {v.get('status', v.get('error', ''))}")

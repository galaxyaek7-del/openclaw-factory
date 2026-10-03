import json, urllib.request, ssl, os, datetime
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
out = {"at": now}
ctx = ssl.create_default_context()

# Freelancer public API (no auth needed for public search)
try:
    req = urllib.request.Request(
        "https://www.freelancer.com/api/projects/0.1/projects/active/?compact=true&limit=3",
        headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=15, context=ctx)
    d = json.loads(resp.read())
    out["freelancer_public"] = {"status": resp.status, "projects_returned": len(d.get("result", {}).get("projects", []))}
except Exception as e:
    out["freelancer_public"] = {"error": str(e)[:120]}

# Telegram credential presence only (never send test)
tg = ""
for src in [".env"]:
    try:
        for line in open(src, encoding="utf-8", errors="replace"):
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                tg = line.strip().split("=", 1)[1]
    except FileNotFoundError:
        pass
if not tg:
    tg = os.environ.get("TELEGRAM_BOT_TOKEN", "")
out["telegram"] = {"credential_present": bool(tg), "send_test": "avoided_by_policy"}

# X API status from existing queue state
try:
    xq = json.load(open("data/x_queue.json", encoding="utf-8")) if os.path.exists("data/x_queue.json") else {}
    out["x_api"] = {"last_known": "402 credits depleted", "queue_file": bool(xq)}
except Exception as e:
    out["x_api"] = {"last_known": "402 credits depleted"}

# Amazon tag
tag = os.environ.get("AMAZON_ASSOCIATE_TAG", "")
if not tag:
    try:
        for line in open(".env", encoding="utf-8", errors="replace"):
            if line.startswith("AMAZON_ASSOCIATE_TAG="):
                tag = line.strip().split("=", 1)[1]
    except FileNotFoundError:
        pass
out["amazon"] = {"tag_present": bool(tag)}

# Record
with open("data/arm_blocked_recheck.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
print(json.dumps(out, indent=1))

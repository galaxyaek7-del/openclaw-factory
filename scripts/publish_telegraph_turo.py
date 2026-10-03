"""Publish Turo dispute guide to Telegraph (one attempt)."""
import json, urllib.request, urllib.parse, ssl, time, datetime
ctx = ssl.create_default_context()
title = "Turo Damage Claims: How Guests Should Respond in 48 Hours"
try:
    data = urllib.parse.urlencode({"short_name": "GalaxyForge", "author_name": "Galaxy Forge"}).encode()
    req = urllib.request.Request("https://api.telegra.ph/createAccount", data=data)
    token = json.loads(urllib.request.urlopen(req, timeout=15, context=ctx).read())["result"]["access_token"]
except Exception as e:
    print("ACCOUNT_FAIL:" + str(e)[:100])
    raise SystemExit
time.sleep(1)
content = [
    {"tag": "p", "children": ["Got a damage claim after your Turo trip? You have 48 hours to respond before Turo auto-charges you. Here's exactly what to do."]},
    {"tag": "h2", "children": ["1. Document everything immediately"]},
    {"tag": "p", "children": ["Your pickup and return photos with timestamps are your best defense. No photos = weak position. Compare the host's claim photos against yours side by side."]},
    {"tag": "h2", "children": ["2. Respond in writing, stay factual"]},
    {"tag": "p", "children": ["Answer each claimed damage point-by-point: pre-existing, normal wear, or disputed with evidence. Never admit fault in writing before reviewing."]},
    {"tag": "h2", "children": ["3. Know the escalation path"]},
    {"tag": "p", "children": ["Guest support -> supervisor review -> collections dispute. Each level needs the same evidence pack, so build it once, reuse it."]},
    {"tag": "h2", "children": ["Full toolkit"]},
    {"tag": "p", "children": ["The Turo Guest Dispute Toolkit ($29) with response templates and checklists: "]},
    {"tag": "p", "children": [{"tag": "a", "attrs": {"href": "https://aekraft.gumroad.com/l/adyvd?utm_source=telegraph&utm_medium=article&utm_campaign=s3_exec_05&utm_content=turo_guide"}, "children": ["https://aekraft.gumroad.com/l/adyvd"]}]},
    {"tag": "p", "children": [{"tag": "em", "children": ["Disclosure: commercial link, digital product, instant delivery."]}]},
]
page_data = urllib.parse.urlencode({"title": title, "author_name": "Galaxy Forge", "content": json.dumps(content), "access_token": token, "return_content": "false"}).encode()
req = urllib.request.Request("https://api.telegra.ph/createPage", data=page_data)
page = json.loads(urllib.request.urlopen(req, timeout=20, context=ctx).read())
url = page.get("result", {}).get("url", "N/A")
print("PAGE:" + url)
rec = {"url": url, "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(), "title": title, "campaign": "s3_exec_05", "product": "Turo Toolkit", "utm_source": "telegraph"}
open("data/telegraph_turo_guide.json", "w").write(json.dumps(rec, indent=1))
print("saved")

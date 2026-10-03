"""Publish EPR/PPWR guide to Telegraph (one attempt)."""
import json, urllib.request, urllib.parse, ssl, time, datetime
ctx = ssl.create_default_context()
title = "EU Packaging EPR + PPWR: What Non-EU Sellers Must Do in 2026"
try:
    data = urllib.parse.urlencode({"short_name": "GalaxyForge", "author_name": "Galaxy Forge"}).encode()
    req = urllib.request.Request("https://api.telegra.ph/createAccount", data=data)
    token = json.loads(urllib.request.urlopen(req, timeout=15, context=ctx).read())["result"]["access_token"]
except Exception as e:
    print("ACCOUNT_FAIL:" + str(e)[:100])
    raise SystemExit
time.sleep(1)
content = [
    {"tag": "p", "children": ["GPSR isn't the only EU wall. Packaging EPR + the new PPWR can block your listings and fine you up to EUR 200,000. Here's what non-EU sellers must do."]},
    {"tag": "h2", "children": ["1. Register for EPR in every member state you sell to"]},
    {"tag": "p", "children": ["Unlike GPSR's single Responsible Person, packaging EPR is per-country: Germany (LUCID), France (Citeo), Spain, Italy each need registration plus a local authorized representative."]},
    {"tag": "h2", "children": ["2. PPWR 2026 changes the math"]},
    {"tag": "p", "children": ["The Packaging and Packaging Waste Regulation adds recyclability grades, deposit-return schemes, and extended producer fees scaled by packaging weight and material."]},
    {"tag": "h2", "children": ["3. Label + declare correctly"]},
    {"tag": "p", "children": ["Sorting instructions (Triman/Green Dot), registration numbers on invoices, and annual volume declarations — miss one and marketplaces delist first, authorities fine second."]},
    {"tag": "h2", "children": ["Full kit"]},
    {"tag": "p", "children": ["The EU Packaging EPR Action Kit ($69) with per-country registration walkthroughs and declaration templates: "]},
    {"tag": "p", "children": [{"tag": "a", "attrs": {"href": "https://aekraft.gumroad.com/l/gfsvu?utm_source=telegraph&utm_medium=article&utm_campaign=s3_exec_05&utm_content=epr_guide"}, "children": ["https://aekraft.gumroad.com/l/gfsvu"]}]},
    {"tag": "p", "children": [{"tag": "em", "children": ["Disclosure: commercial link, digital product, instant delivery."]}]},
]
page_data = urllib.parse.urlencode({"title": title, "author_name": "Galaxy Forge", "content": json.dumps(content), "access_token": token, "return_content": "false"}).encode()
req = urllib.request.Request("https://api.telegra.ph/createPage", data=page_data)
page = json.loads(urllib.request.urlopen(req, timeout=20, context=ctx).read())
url = page.get("result", {}).get("url", "N/A")
print("PAGE:" + url)
rec = {"url": url, "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(), "title": title, "campaign": "s3_exec_05", "product": "EPR Kit", "utm_source": "telegraph"}
open("data/telegraph_epr_guide.json", "w").write(json.dumps(rec, indent=1))
print("saved")

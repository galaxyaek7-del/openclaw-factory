"""Publish ADA demand-letter guide to Telegraph (one attempt)."""
import json, urllib.request, urllib.parse, ssl, time, datetime
ctx = ssl.create_default_context()
title = "ADA Demand Letters: How US Small Businesses Should Respond in 24 Hours"
try:
    data = urllib.parse.urlencode({"short_name": "GalaxyForge", "author_name": "Galaxy Forge"}).encode()
    req = urllib.request.Request("https://api.telegra.ph/createAccount", data=data)
    token = json.loads(urllib.request.urlopen(req, timeout=15, context=ctx).read())["result"]["access_token"]
except Exception as e:
    print("ACCOUNT_FAIL:" + str(e)[:100])
    raise SystemExit
time.sleep(1)
content = [
    {"tag": "p", "children": ["An ADA demand letter just arrived. Settlements run $5,000-$20,000, and California's Unruh Act lets penalties stack per violation. Here's how to triage in 24 hours."]},
    {"tag": "h2", "children": ["1. Don't ignore it, don't panic"]},
    {"tag": "p", "children": ["Ignoring the letter converts a negotiable claim into a lawsuit. But most letters — especially serial-filer templates — settle for far less than demanded when answered fast and correctly."]},
    {"tag": "h2", "children": ["2. Triage: physical barrier vs website vs policy"]},
    {"tag": "p", "children": ["Identify which category the claim falls in. Quick physical fixes (signage, parking striping) cost hundreds and remove leverage. Website claims need an accessibility audit trail."]},
    {"tag": "h2", "children": ["3. Respond with a plan, not just a check"]},
    {"tag": "p", "children": ["A response showing a remediation timeline plus a reasonable offer settles most cases. Know when the exposure justifies hiring counsel (multiple locations, Unruh stacking, prior suits)."]},
    {"tag": "h2", "children": ["Full kit"]},
    {"tag": "p", "children": ["The ADA Demand-Letter Response & Triage Kit ($69) with triage checklist, response templates, and exposure calculator: "]},
    {"tag": "p", "children": [{"tag": "a", "attrs": {"href": "https://aekraft.gumroad.com/l/palmdr?utm_source=telegraph&utm_medium=article&utm_campaign=s3_exec_05&utm_content=ada_guide"}, "children": ["https://aekraft.gumroad.com/l/palmdr"]}]},
    {"tag": "p", "children": [{"tag": "em", "children": ["Disclosure: commercial link, digital product, instant delivery. Not legal advice."]}]},
]
page_data = urllib.parse.urlencode({"title": title, "author_name": "Galaxy Forge", "content": json.dumps(content), "access_token": token, "return_content": "false"}).encode()
req = urllib.request.Request("https://api.telegra.ph/createPage", data=page_data)
page = json.loads(urllib.request.urlopen(req, timeout=20, context=ctx).read())
url = page.get("result", {}).get("url", "N/A")
print("PAGE:" + url)
rec = {"url": url, "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(), "title": title, "campaign": "s3_exec_05", "product": "ADA Kit", "utm_source": "telegraph"}
open("data/telegraph_ada_guide.json", "w").write(json.dumps(rec, indent=1))
print("saved")

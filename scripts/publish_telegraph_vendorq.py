"""Publish VendorQ B2B guide to Telegraph (one attempt)."""
import json, urllib.request, urllib.parse, ssl, time, datetime
ctx = ssl.create_default_context()
title = "Vendor Questionnaires: How SMBs Answer Enterprise Security Reviews in 48 Hours"
try:
    data = urllib.parse.urlencode({"short_name": "GalaxyForge", "author_name": "Galaxy Forge"}).encode()
    req = urllib.request.Request("https://api.telegra.ph/createAccount", data=data)
    token = json.loads(urllib.request.urlopen(req, timeout=15, context=ctx).read())["result"]["access_token"]
except Exception as e:
    print("ACCOUNT_FAIL:" + str(e)[:100])
    raise SystemExit
time.sleep(1)
content = [
    {"tag": "p", "children": ["Enterprise deals stall when the vendor questionnaire arrives: 200 questions on security, compliance, and data handling. Most SMBs take weeks. Here's how to answer in 48 hours."]},
    {"tag": "h2", "children": ["1. Build a reusable answer library"]},
    {"tag": "p", "children": ["80% of questionnaires ask the same 40 questions (data encryption, access controls, incident response, subprocessors). Answer once, reuse forever."]},
    {"tag": "h2", "children": ["2. Know the frameworks"]},
    {"tag": "p", "children": ["Map your answers to SOC 2, ISO 27001, and GDPR language buyers expect — even if you're not certified, show aligned practices."]},
    {"tag": "h2", "children": ["3. Turnaround process"]},
    {"tag": "p", "children": ["Triage on receipt, assign owners per section, review once, return with a cover summary. 48 hours is achievable with a library in place."]},
    {"tag": "h2", "children": ["Full kit"]},
    {"tag": "p", "children": ["The Vendor Questionnaire Response Kit ($89) with pre-written answers and templates: "]},
    {"tag": "p", "children": [{"tag": "a", "attrs": {"href": "https://aekraft.gumroad.com/l/pyzqa?utm_source=telegraph&utm_medium=article&utm_campaign=s3_exec_05&utm_content=vendorq_guide"}, "children": ["https://aekraft.gumroad.com/l/pyzqa"]}]},
    {"tag": "p", "children": [{"tag": "em", "children": ["Disclosure: commercial link, digital product, instant delivery."]}]},
]
page_data = urllib.parse.urlencode({"title": title, "author_name": "Galaxy Forge", "content": json.dumps(content), "access_token": token, "return_content": "false"}).encode()
req = urllib.request.Request("https://api.telegra.ph/createPage", data=page_data)
page = json.loads(urllib.request.urlopen(req, timeout=20, context=ctx).read())
url = page.get("result", {}).get("url", "N/A")
print("PAGE:" + url)
rec = {"url": url, "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(), "title": title, "campaign": "s3_exec_05", "product": "VendorQ Kit", "utm_source": "telegraph"}
open("data/telegraph_vendorq_article.json", "w").write(json.dumps(rec, indent=1))
print("saved")

"""Publish Trademark DIY guide to Telegraph (one attempt)."""
import json, urllib.request, urllib.parse, ssl, time, datetime
ctx = ssl.create_default_context()
title = "First US Trademark Filing: A Founder's DIY Walkthrough for 2026"
try:
    data = urllib.parse.urlencode({"short_name": "GalaxyForge", "author_name": "Galaxy Forge"}).encode()
    req = urllib.request.Request("https://api.telegra.ph/createAccount", data=data)
    token = json.loads(urllib.request.urlopen(req, timeout=15, context=ctx).read())["result"]["access_token"]
except Exception as e:
    print("ACCOUNT_FAIL:" + str(e)[:100])
    raise SystemExit
time.sleep(1)
content = [
    {"tag": "p", "children": ["Filing your first US trademark? Counsel quotes $1,000-$5,000, but a straightforward word mark is genuinely DIY-able. Here's the walkthrough."]},
    {"tag": "h2", "children": ["1. Search first (TESS)"]},
    {"tag": "p", "children": ["Run a USPTO TESS knockout search for identical marks in your class plus obvious phonetic equivalents. Most DIY failures start here — filing on a taken mark wastes the $250-$350 fee."]},
    {"tag": "h2", "children": ["2. Pick use-in-commerce vs intent-to-use"]},
    {"tag": "p", "children": ["Already selling under the mark? File use-based with a specimen. Not yet? Intent-to-use costs an extra $100 per class later at the statement-of-use stage."]},
    {"tag": "h2", "children": ["3. Describe goods/services precisely"]},
    {"tag": "p", "children": ["Use the ID Manual's pre-approved descriptions to avoid Office Actions. Custom wording triggers review delays in most cases."]},
    {"tag": "h2", "children": ["Full kit"]},
    {"tag": "p", "children": ["The Trademark DIY Filing Action Kit ($69) with TEAS walkthrough, description templates, specimen guide, and Office Action responses: "]},
    {"tag": "p", "children": [{"tag": "a", "attrs": {"href": "https://aekraft.gumroad.com/l/vkqogv?utm_source=telegraph&utm_medium=article&utm_campaign=s3_exec_05&utm_content=trademark_guide"}, "children": ["https://aekraft.gumroad.com/l/vkqogv"]}]},
    {"tag": "p", "children": [{"tag": "em", "children": ["Disclosure: commercial link, digital product. Not legal advice; complex cases need counsel."]}]},
]
page_data = urllib.parse.urlencode({"title": title, "author_name": "Galaxy Forge", "content": json.dumps(content), "access_token": token, "return_content": "false"}).encode()
req = urllib.request.Request("https://api.telegra.ph/createPage", data=page_data)
page = json.loads(urllib.request.urlopen(req, timeout=20, context=ctx).read())
url = page.get("result", {}).get("url", "N/A")
print("PAGE:" + url)
rec = {"url": url, "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(), "title": title, "campaign": "s3_exec_05", "product": "Trademark Kit", "utm_source": "telegraph"}
open("data/telegraph_trademark_guide.json", "w").write(json.dumps(rec, indent=1))
print("saved")

"""Publish STR direct-booking guide to Telegraph (one attempt)."""
import json, urllib.request, urllib.parse, ssl, time, datetime
ctx = ssl.create_default_context()
title = "OTA Fees Eat 15 Percent: A Direct-Booking Playbook for STR Hosts"
try:
    data = urllib.parse.urlencode({"short_name": "GalaxyForge", "author_name": "Galaxy Forge"}).encode()
    req = urllib.request.Request("https://api.telegra.ph/createAccount", data=data)
    token = json.loads(urllib.request.urlopen(req, timeout=15, context=ctx).read())["result"]["access_token"]
except Exception as e:
    print("ACCOUNT_FAIL:" + str(e)[:100])
    raise SystemExit
time.sleep(1)
content = [
    {"tag": "p", "children": ["Airbnb and Vrbo take ~15.5% of every booking. On $80k gross, that's $12,400 a year gone. Here's how hosts take bookings direct."]},
    {"tag": "h2", "children": ["1. A one-page booking site that converts"]},
    {"tag": "p", "children": ["Photos, calendar, price, one button. Most hosts overbuild; conversion comes from availability clarity and reviews, not design awards."]},
    {"tag": "h2", "children": ["2. Capture every guest's email"]},
    {"tag": "p", "children": ["OTA guests are rented, not owned. A checkout message offering 10% off direct rebooking converts 15-25% into repeat direct guests."]},
    {"tag": "h2", "children": ["3. Reviews that travel"]},
    {"tag": "p", "children": ["Funnel Google reviews alongside Airbnb stars. Direct bookers check Google first; ten real reviews beat a pretty site."]},
    {"tag": "h2", "children": ["Full kit"]},
    {"tag": "p", "children": ["The STR Direct Booking Revenue Kit ($59) with site template, email scripts, and pricing strategy: "]},
    {"tag": "p", "children": [{"tag": "a", "attrs": {"href": "https://aekraft.gumroad.com/l/ppsluq?utm_source=telegraph&utm_medium=article&utm_campaign=s3_exec_05&utm_content=str_guide"}, "children": ["https://aekraft.gumroad.com/l/ppsluq"]}]},
    {"tag": "p", "children": [{"tag": "em", "children": ["Disclosure: commercial link, digital product, instant delivery."]}]},
]
page_data = urllib.parse.urlencode({"title": title, "author_name": "Galaxy Forge", "content": json.dumps(content), "access_token": token, "return_content": "false"}).encode()
req = urllib.request.Request("https://api.telegra.ph/createPage", data=page_data)
page = json.loads(urllib.request.urlopen(req, timeout=20, context=ctx).read())
url = page.get("result", {}).get("url", "N/A")
print("PAGE:" + url)
rec = {"url": url, "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(), "title": title, "campaign": "s3_exec_05", "product": "STR Kit", "utm_source": "telegraph"}
open("data/telegraph_str_guide.json", "w").write(json.dumps(rec, indent=1))
print("saved")

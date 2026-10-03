import urllib.request, json, datetime
KEY = "c8742f1da91ebe577587681839ae0004"
HOST = "galaxyaek7-del.github.io"
BASE = "https://galaxyaek7-del.github.io/openclaw-factory/customer_site/"
URLS = [
    BASE + "gpsr-landing.html",
    BASE + "offer-eu-ai-act-toolkit.html",
    BASE + "eu-ai-act-compliance-toolkit.html",
    BASE + "blog-eu-ai-act-compliance-sme-guide.html",
    BASE + "service-verified-lead-lists.html",
    BASE + "service-kdp-typesetting.html",
    BASE + "service-eu-deadline-briefing.html",
    BASE + "turo-guest-dispute-toolkit.html",
    BASE + "index.html",
]
payload = json.dumps({"host": HOST, "key": KEY, "urlList": URLS}).encode()
out = {"at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "urls": URLS, "receipts": {}}
for endpoint in ["https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"]:
    req = urllib.request.Request(endpoint, data=payload, headers={"Content-Type": "application/json", "User-Agent": "GalaxyForge-indexnow/1.0"})
    try:
        r = urllib.request.urlopen(req, timeout=30)
        out["receipts"][endpoint] = r.status
        print(endpoint, "->", r.status)
    except Exception as e:
        out["receipts"][endpoint] = "FAIL:" + str(e)[:100]
        print(endpoint, "-> FAIL:", str(e)[:100])
json.dump(out, open("data/indexnow_submit_20261003.json", "w"), indent=1)
print("submitted", len(URLS), "urls")

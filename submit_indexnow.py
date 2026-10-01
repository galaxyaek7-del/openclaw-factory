import urllib.request, json

KEY = "c8742f1da91ebe577587681839ae0004"
HOST = "galaxyaek7-del.github.io"
BASE = "https://galaxyaek7-del.github.io/openclaw-factory/customer_site/"

# 1. key file must already be live at repo root (committed+pushed before this runs)
key_url = "https://galaxyaek7-del.github.io/openclaw-factory/%s.txt" % KEY
try:
    r = urllib.request.urlopen(
        urllib.request.Request(key_url, headers={"User-Agent": "GalaxyForge-indexnow/1.0"}),
        timeout=25,
    )
    print("key file:", r.status)
except Exception as e:
    print("key file NOT LIVE:", str(e)[:100])
    raise SystemExit("push the key file first, then submit")

URLS = [
    BASE + "service-verified-lead-lists.html",
    BASE + "service-kdp-typesetting.html",
    BASE + "affiliate-standing-desks.html",
]
payload = json.dumps({"host": HOST, "key": KEY, "urlList": URLS}).encode()
for endpoint in ["https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"]:
    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "GalaxyForge-indexnow/1.0"},
    )
    try:
        r = urllib.request.urlopen(req, timeout=30)
        print(endpoint, "->", r.status)
    except Exception as e:
        print(endpoint, "-> FAIL:", str(e)[:120])

json.dump(
    {"at": "2026-10-01T20:30:00+00:00", "key": KEY, "urls": URLS,
     "note": "submission receipts above; indexing itself is search-engine-side (UNKNOWN until observable)"},
    open("data/indexnow_submit.json", "w"),
    indent=1,
)

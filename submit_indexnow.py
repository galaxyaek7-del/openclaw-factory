#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Submit the live sitemap to IndexNow.

C101 fixed the real defect here. This script previously sent
{"host", "key", "urlList"} with NO keyLocation. IndexNow verifies ownership by
fetching the key file from the HOST ROOT (https://<host>/<key>.txt). This site
is a GitHub Pages PROJECT page, so the host root is the github.io user page,
which returns 404 for the key file and cannot be controlled from this
repository. The engine therefore concluded the key was invalid and answered
403 UserForbiddedToAccessSite - the documented "key not found" case.

The key file lives one directory down at
https://galaxyaek7-del.github.io/openclaw-factory/<key>.txt. The protocol
supports that via the keyLocation field (Option 2), which also scopes which
URLs the key may cover: a key at /openclaw-factory/ covers URLs starting with
https://galaxyaek7-del.github.io/openclaw-factory/, which is every URL we
submit. With keyLocation added, both endpoints answer HTTP 200.

URLs are read from the live sitemap rather than hardcoded, so the submission
can never drift from what is actually published.

A 200/202 response means the URLs were RECEIVED as changed. It is a crawl
request. It is NOT evidence of crawling, indexing, ranking, impressions, or any
visit. Google does not participate in IndexNow at all; only Search Console can
submit to Google.
"""

import datetime
import json
import re
import urllib.error
import urllib.request

KEY = "c8742f1da91ebe577587681839ae0004"
HOST = "galaxyaek7-del.github.io"
SITE = "https://galaxyaek7-del.github.io/openclaw-factory/"
KEY_LOCATION = f"{SITE}{KEY}.txt"
SITEMAP = f"{SITE}sitemap.xml"
UA = {"User-Agent": "GalaxyForge-IndexNow/1.0"}


def _get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30)


def _post(endpoint, payload):
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8", **UA},
    )
    try:
        r = urllib.request.urlopen(req, timeout=45)
        return r.status, r.read().decode("utf-8", "replace")[:300]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:300]


def main():
    # 1. the key file must be publicly readable before submitting
    try:
        r = _get(KEY_LOCATION)
        print("key file (keyLocation):", r.status)
        if r.status != 200:
            raise SystemExit("key file is not publicly readable; push it first")
    except SystemExit:
        raise
    except Exception as e:
        raise SystemExit(f"key file NOT reachable at {KEY_LOCATION}: {str(e)[:120]}")

    # 2. read the real published URL list
    sm = _get(SITEMAP).read().decode("utf-8")
    urls = re.findall(r"<loc>(.*?)</loc>", sm)
    print("urls from live sitemap:", len(urls))
    if not urls:
        raise SystemExit("sitemap contained no URLs; refusing to submit")
    off_host = [u for u in urls if not u.startswith("https://" + HOST)]
    if off_host:
        raise SystemExit(f"refusing to submit {len(off_host)} URLs outside {HOST}")

    # 3. submit WITH keyLocation - this is the fix
    payload = {"host": HOST, "key": KEY, "keyLocation": KEY_LOCATION, "urlList": urls}
    receipts = []
    for endpoint in ["https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"]:
        status, body = _post(endpoint, payload)
        receipts.append({"endpoint": endpoint, "http_status": status, "response": body})
        print(endpoint, "->", status, body[:100])

    ok = all(x["http_status"] in (200, 202) for x in receipts)
    record = {
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "host": HOST,
        "key_file_url": KEY_LOCATION,
        "url_count": len(urls),
        "urls": urls,
        "receipts": receipts,
        "accepted": ok,
        "interpretation": (
            "HTTP 200 = submitted successfully; HTTP 202 = received, key validation pending. "
            "Both are a CRAWL REQUEST only. NOT crawl, NOT index, NOT impressions, NOT visits. "
            "Google does not participate in IndexNow."
        ),
    }
    with open("data/indexnow_submit.json", "w", encoding="utf-8") as f:
        json.dump(record, f, indent=1)
    print("\nreceipt -> data/indexnow_submit.json | accepted:", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
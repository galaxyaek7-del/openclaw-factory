"""Galaxy Forge — lightweight HTTP validation (P8).

conditional_get(): sends If-None-Match / If-Modified-Since from memory,
returns (changed: bool, status, body_or_None). 304 -> no download.
Respects a caller-supplied minimum interval per URL (politeness default
60s; never below 10s). No auth/rate-limit bypass, ever.
"""
import time
import urllib.request

_MEM = {}
MIN_INTERVAL = 60.0


def conditional_get(url, headers=None, min_interval=MIN_INTERVAL, timeout=30):
    """Return dict(status, changed, bytes|None, note). Never raises."""
    now = time.time()
    mem = _MEM.get(url, {})
    if now - mem.get("at", 0) < max(10.0, min_interval):
        return {"status": "CACHED_INTERVAL", "changed": False, "bytes": None,
                "note": "politeness interval, not re-fetched"}
    hdrs = dict(headers or {})
    if mem.get("etag"):
        hdrs["If-None-Match"] = mem["etag"]
    if mem.get("lastmod"):
        hdrs["If-Modified-Since"] = mem["lastmod"]
    try:
        req = urllib.request.Request(url, headers=hdrs)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            _MEM[url] = {"at": now, "etag": r.headers.get("ETag"),
                         "lastmod": r.headers.get("Last-Modified")}
            return {"status": r.status, "changed": True, "bytes": len(body),
                    "note": "fetched"}
    except Exception as e:
        code = getattr(getattr(e, "hdrs", None), "status", None)
        text = str(e)
        if "304" in text or "Not Modified" in text:
            _MEM[url] = dict(mem, at=now)
            return {"status": 304, "changed": False, "bytes": None,
                    "note": "not modified, no download"}
        return {"status": "ERROR", "changed": False, "bytes": None,
                "note": text[:120]}

"""Galaxy Forge — shared JSON HTTP client (S3-TOOLS).

get_json(): requests-based GET returning parsed JSON, with tenacity-bounded
retries (3 attempts, exponential backoff) and Retry-After respect on
429/503 (capped, never hangs). Complements lib/httpcheck.py (conditional
page fetches) — this one is for JSON APIs. Never raises raw transport
details beyond a short summary; never logs bodies.
"""
from __future__ import annotations

import time

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

USER_AGENT = "GalaxyForge-http/1.0"
TIMEOUT = 30
MAX_RETRIES = 3


class HttpError(RuntimeError):
    def __init__(self, url, code, body=""):
        super().__init__("GET %s -> HTTP %s: %s" % (url, code, body[:200]))
        self.url = url
        self.code = code


def _retry_after_seconds(resp):
    try:
        return min(30.0, max(0.0, float(resp.headers.get("Retry-After", "0"))))
    except (TypeError, ValueError):
        return 0.0


def _should_retry(exc):
    if isinstance(exc, HttpError):
        return exc.code in (429, 503) or exc.code >= 500
    return isinstance(exc, (requests.ConnectionError, requests.Timeout))


@retry(stop=stop_after_attempt(MAX_RETRIES),
       wait=wait_exponential(multiplier=1, min=1, max=8),
       retry=retry_if_exception(_should_retry),
       reraise=True)
def _fetch(url, headers, timeout):
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
    except requests.RequestException as e:
        raise requests.ConnectionError(str(e)[:150])
    if r.status_code == 429 or r.status_code == 503:
        wait = _retry_after_seconds(r)
        if wait:
            time.sleep(wait)
    if r.status_code != 200:
        raise HttpError(url, r.status_code, r.text)
    try:
        return r.json()
    except ValueError:
        raise HttpError(url, r.status_code, "non-JSON body")


def get_json(url, headers=None, timeout=TIMEOUT):
    """GET JSON with bounded retries. Raises HttpError on final failure."""
    hdrs = {"User-Agent": USER_AGENT}
    hdrs.update(headers or {})
    return _fetch(url, hdrs, timeout)

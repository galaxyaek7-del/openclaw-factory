#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""X credential read-only verification (OAuth1 GET users/me, stdlib only).
Proves credential validity WITHOUT posting. No tweet is created, no write
occurs, secrets never leave memory or enter logs/reports. OAuth1 signing
implemented with stdlib hmac (no new dependency) because oauthlib is absent."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import urllib.parse
import urllib.request
import uuid


def _load(name, env_path=".env"):
    import os
    v = os.environ.get(name, "").strip()
    if v:
        return v
    try:
        with open(env_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line.startswith(name + "="):
                    return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""


def verify_credentials(timeout=20) -> dict:
    ck, cs = _load("X_API_KEY"), _load("X_API_SECRET")
    at, ats = _load("X_ACCESS_TOKEN"), _load("X_ACCESS_TOKEN_SECRET")
    if not all((ck, cs, at, ats)):
        return {"valid": False, "reason": "credentials incomplete"}
    url = "https://api.x.com/2/users/me"
    nonce, ts = uuid.uuid4().hex, str(int(time.time()))
    params = {"oauth_consumer_key": ck, "oauth_nonce": nonce,
              "oauth_signature_method": "HMAC-SHA1", "oauth_timestamp": ts,
              "oauth_token": at, "oauth_version": "1.0"}
    base = "&".join([
        "GET", urllib.parse.quote(url, safe=""),
        urllib.parse.quote("&".join("%s=%s" % (k, urllib.parse.quote(str(v), safe=""))
                                    for k, v in sorted(params.items())), safe="")])
    key = (urllib.parse.quote(cs, safe="") + "&" + urllib.parse.quote(ats, safe="")).encode()
    sig = base64.b64encode(hmac.new(key, base.encode(), hashlib.sha1).digest()).decode()
    auth = ("OAuth " + ", ".join('%s="%s"' % (k, urllib.parse.quote(str(v), safe=""))
                                 for k, v in sorted(params.items()))
            + ', oauth_signature="%s"' % urllib.parse.quote(sig, safe=""))
    try:
        req = urllib.request.Request(url, headers={"Authorization": auth})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            u = (json.loads(r.read().decode()).get("data") or {})
            return {"valid": True, "username": u.get("username"),
                    "user_id": u.get("id"), "method": "GET users/me (read-only)"}
    except Exception as e:
        return {"valid": False, "reason": "%s" % type(e).__name__,
                "detail": str(e)[:150]}

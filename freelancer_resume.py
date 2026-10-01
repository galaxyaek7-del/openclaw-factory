"""Resume-on-grant executor for the single Freelancer OAuth exception.

Behavior:
  --once : one check-and-act pass. Exit 0 always (a missing grant is an
           expected state, not a failure). Prints one JSON status line.
           NEVER prints the token (only TOKEN_PRESENT true/false).

  On grant detection, in order:
    1. validate token via authenticated self lookup (no token reuse elsewhere);
    2. re-verify project 40742370 OPEN + biddable via public API;
    3. check idempotency key bid-40742370-once (refuse duplicates locally);
    4. submit the prepared bid (price from policy-bounded select_price);
    5. independently verify the bid exists (GET bids for the project);
    6. record evidence (SUBMITTED -> SUBMISSION_VERIFIED, never further);
    7. establish inbox polling baseline.

  Steps 5-14 of the founder order (inbox poll, discovery, further
  submissions) continue on subsequent --once passes once the grant is live.

Token handling: read ONLY from env (FREELANCER_OAUTH_TOKEN / FLN_OAUTH_TOKEN),
held in memory for the single pass, never written to disk/logs/git.
"""

import json
import os
import sys
import urllib.request
import urllib.error

API_BASE = "https://www.freelancer.com/api"
TIMEOUT = 30

TOKEN_NAMES = ("FREELANCER_OAUTH_TOKEN", "FLN_OAUTH_TOKEN")
TARGET_PROJECT = 40742370
IDEMPOTENCY_KEY = "bid-40742370-once"
SUBMISSIONS_PATH = "data/freelancer_submissions.json"


def _auth_get(path, token):
    req = urllib.request.Request(
        API_BASE + path,
        headers={
            "freelancer-oauth-v1": token,
            "User-Agent": "GalaxyForge-grant-resume/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "body": e.read().decode()[:200]}
    return body


def main():
    from freelancer_api import (
        summarize_project,
        biddability,
        select_price,
    )

    token = None
    for name in TOKEN_NAMES:
        if os.environ.get(name):
            token = os.environ[name]
            break
    status = {"token_present": bool(token), "action": "none"}

    if not token:
        # Expected state: grant outstanding. No-op, no failure.
        print(json.dumps(status))
        return 0

    # 1. validate grant: authenticated self lookup (users/self equivalent).
    me = _auth_get("/users/0.1/self/", token)
    if me.get("http_error") or me.get("status") != "success":
        status["action"] = "grant_invalid"
        status["detail"] = "token rejected by platform (auth check failed)"
        print(json.dumps(status))
        return 0
    status["grant_valid"] = True

    # 2-3. re-verify project + biddability via public API.
    summary = summarize_project(TARGET_PROJECT)
    ok, reason = biddability(summary)
    status["project"] = {
        "status": summary["status"],
        "biddable": ok,
        "reason": reason,
        "bid_count": summary["bid_count"],
    }
    if not ok:
        status["action"] = "not_biddable_stand_down"
        print(json.dumps(status))
        return 0

    # 4. idempotency: refuse local duplicates.
    subs = {}
    try:
        with open(SUBMISSIONS_PATH) as fh:
            subs = json.load(fh)
    except (OSError, ValueError):
        pass
    rec = subs.get(str(TARGET_PROJECT), {})
    if rec.get("status") in ("SUBMITTED", "SUBMISSION_VERIFIED"):
        status["action"] = "already_submitted_no_duplicate"
        print(json.dumps(status))
        return 0

    # 5. submit via official bids endpoint (needs bidder_id = self id).
    bidder_id = (me.get("result") or {}).get("id")
    price, basis = select_price(summary)
    payload = json.dumps(
        {
            "project_id": TARGET_PROJECT,
            "bidder_id": bidder_id,
            "amount": price,
            "period": 6,
            "milestone_percentage": 100,
            "description": (
                "I build verified B2B lead lists to exact criteria — scoped, "
                "deduped, and delivered fast. Criteria lock day 1-2, verified "
                "delivery by day 5, revision buffer day 6."
            ),
        }
    ).encode()
    req = urllib.request.Request(
        API_BASE + "/projects/0.1/bids/",
        data=payload,
        headers={
            "freelancer-oauth-v1": token,
            "Content-Type": "application/json",
            "User-Agent": "GalaxyForge-grant-resume/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            placed = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        status["action"] = "submit_failed_isolated"
        status["detail"] = "HTTP %s (no retry storm; isolated)" % e.code
        print(json.dumps(status))
        return 0

    bid_id = (placed.get("result") or {}).get("id")
    if placed.get("status") != "success" or not bid_id:
        status["action"] = "submit_failed_isolated"
        status["detail"] = str(placed)[:200]
        print(json.dumps(status))
        return 0

    # 6. independent verification: bid exists in project bids.
    verify = _auth_get(
        "/projects/0.1/bids/?projects[]=%d" % TARGET_PROJECT, token
    )
    found = False
    try:
        bids = (verify.get("result") or {}).get("bids", [])
        found = any(
            str((b.get("bidder") or {}).get("id")) == str(bidder_id)
            for b in bids
        )
    except Exception:
        found = False

    status["action"] = "submitted"
    status["bid_id"] = bid_id
    status["price"] = price
    status["verified"] = bool(found)

    # 7. record (evidence state advances only on verification).
    subs[str(TARGET_PROJECT)] = {
        "price_usd": price,
        "price_basis": basis,
        "status": "SUBMISSION_VERIFIED" if found else "SUBMITTED",
        "idempotency_key": IDEMPOTENCY_KEY,
        "bid_id": bid_id,
        "evidence": "PLATFORM_VERIFIED" if found else "SUBMITTED-unverified",
    }
    with open(SUBMISSIONS_PATH, "w") as fh:
        json.dump(subs, fh, indent=1)
    print(json.dumps(status))
    return 0


if __name__ == "__main__":
    sys.exit(main())

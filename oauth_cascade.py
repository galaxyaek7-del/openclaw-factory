"""OAuth cascade executor: validate grant, submit 4 guarded proposals, verify.
Token in memory only. Output contains booleans and IDs only — never the token.
"""
import json
import os
import sys
import urllib.request
import urllib.error

API = "https://www.freelancer.com/api"
UA = {"User-Agent": "GalaxyForge-cascade/1.0"}


def load_token():
    for n in ("FREELANCER_OAUTH_TOKEN", "FLN_OAUTH_TOKEN"):
        if os.environ.get(n):
            return os.environ[n]
    try:
        with open(".env", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                s = line.strip()
                if s.startswith("FREELANCER_OAUTH_TOKEN=") or s.startswith("FLN_OAUTH_TOKEN="):
                    v = s.split("=", 1)[1].strip()
                    if v:
                        return v
    except OSError:
        pass
    return None


def authed(path, token, data=None):
    headers = {"freelancer-oauth-v1": token}
    headers.update(UA)
    body = json.dumps(data).encode() if data is not None else None
    hdrs = dict(headers)
    if data is not None:
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(API + path, data=body, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode()[:150]}


def main():
    token = load_token()
    print(json.dumps({"detected": bool(token)}))
    if not token:
        return 1
    code, me = authed("/users/0.1/self/", token)
    ok = code == 200 and me.get("status") == "success"
    print(json.dumps({"usable": ok, "http": code if not ok else 200}))
    if not ok:
        return 2
    bidder = (me.get("result") or {}).get("id")
    subs = json.load(open("data/freelancer_submissions.json", encoding="utf-8"))
    import freelancer_api as F

    for pid in ["40744952", "40745859", "40741347", "40746029"]:
        rec = subs.get(pid, {})
        if rec.get("status") in ("SUBMITTED", "SUBMISSION_VERIFIED"):
            print(json.dumps({"project": pid, "action": "already-submitted-no-duplicate"}))
            continue
        try:
            s = F.summarize_project(pid)
        except Exception:
            print(json.dumps({"project": pid, "action": "unreadable-skip"}))
            continue
        okb, reason = F.biddability(s)
        if not okb:
            rec["status"] = "CLOSED_UNSUBMITTED"
            rec["evidence"] = reason
            subs[pid] = rec
            print(json.dumps({"project": pid, "action": "not-biddable", "reason": reason}))
            continue
        prop = rec.get("proposal_personalized", "")
        if isinstance(prop, dict):
            desc = "%s. Deliverables: %s. Timeline: %s. Price border: within your stated range." % (
                prop.get("solution", prop.get("problem", "")),
                prop.get("deliverables", ""), prop.get("timeline", ""))
        else:
            desc = str(prop)[:1500] or "Fixed-scope delivery per agreed criteria."
        code, placed = authed("/projects/0.1/bids/", token, {
            "project_id": int(pid), "bidder_id": bidder,
            "amount": float(rec.get("price_usd", 100)),
            "period": 6, "milestone_percentage": 100, "description": desc})
        bid = (placed.get("result") or {}).get("id") if isinstance(placed, dict) else None
        if code in (200, 201) and bid:
            rec["status"] = "SUBMITTED"
            rec["bid_id"] = bid
            rec["evidence"] = "PLATFORM response ok"
            print(json.dumps({"project": pid, "action": "submitted", "bid_id": bid}))
        else:
            rec["status"] = "SUBMIT_FAILED"
            rec["evidence"] = "HTTP %s" % code
            print(json.dumps({"project": pid, "action": "submit-failed", "http": code}))
        subs[pid] = rec
        json.dump(subs, open("data/freelancer_submissions.json", "w", encoding="utf-8"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())

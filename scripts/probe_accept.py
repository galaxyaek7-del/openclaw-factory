"""GF-16 repair: accept-cycle proof WITHOUT touching production ledgers.

The old version POSTed a valid payload to the LIVE endpoint, writing a real
row to customer_interest.jsonl on every run ("will be removed" cleanup is not
a control). This version runs the full record path against isolated temp
ledgers and refuses live testing unless GF_LIVE_PROBE=1 is set explicitly by
a human who accepts the ledger write.
"""
import json, os, sys, tempfile
sys.path.insert(0, ".")
from lib.customer_evidence import record_interest_signal
payload = {"email": "verify-loop@t.com", "message": "TEST_EVENT full accept-cycle proof (INTERNAL, excluded from metrics)", "source": "loop-proof", "campaign": "s3_exec_05"}
if os.environ.get("GF_LIVE_PROBE") == "1":
    import urllib.request, urllib.error
    d = json.dumps(payload).encode()
    r = urllib.request.Request("http://localhost:3000/api/customer/interest", data=d, headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(r, timeout=60)
        print("LIVE HTTP", resp.status, resp.read()[:200])
    except urllib.error.HTTPError as e:
        print("LIVE HTTP", e.code, e.read()[:200])
else:
    tmp = tempfile.mkdtemp(prefix="gf_int_")
    res = record_interest_signal(payload, ledger_path=f"{tmp}/interest.jsonl", rejected_ledger_path=f"{tmp}/rejected.jsonl")
    print("ISOLATED", json.dumps(res)[:200], "(production ledgers untouched)")

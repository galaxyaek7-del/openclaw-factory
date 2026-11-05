"""GF-16 repair: timing probe WITHOUT polluting buyer-interest ledgers.

Every POST to /api/customer/interest persists a row (accepted or rejected),
so this probe never POSTs there. It times (a) transport via GET (no write
path on GET) and (b) validation logic via the pure function (zero writes).
"""
import sys, time, urllib.request, urllib.error
sys.path.insert(0, ".")
from lib.customer_evidence import validate_and_classify
t0 = time.time()
try:
    req = urllib.request.Request("http://localhost:3000/api/customer/interest",
                                 headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=60)
    print(f"TRANSPORT-GET HTTP {resp.status} in {time.time()-t0:.1f}s (no write path on GET)")
except urllib.error.HTTPError as e:
    print(f"TRANSPORT-GET HTTP {e.code} in {time.time()-t0:.1f}s (no write path on GET)")
except Exception as e:
    print(f"TRANSPORT-GET FAIL after {time.time()-t0:.1f}s:", str(e)[:150])
t1 = time.time()
ok, cls, reason, enr = validate_and_classify({"email": "probe@example.com", "message": "TEST_EVENT timing probe"})
print(f"VALIDATE local in {time.time()-t1:.1f}s: ok={ok} reason={reason} (zero writes)")

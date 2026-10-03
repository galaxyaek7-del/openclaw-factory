import json, urllib.request, urllib.error, time
d = json.dumps({"email": "probe@example.com", "message": "TEST_EVENT timing probe"}).encode()
r = urllib.request.Request("http://localhost:3000/api/customer/interest", data=d, headers={"Content-Type": "application/json"})
t0 = time.time()
try:
    resp = urllib.request.urlopen(r, timeout=60)
    print(f"HTTP {resp.status} in {time.time()-t0:.1f}s:", resp.read()[:150])
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code} in {time.time()-t0:.1f}s:", e.read()[:150])
except Exception as e:
    print(f"FAIL after {time.time()-t0:.1f}s:", str(e)[:150])

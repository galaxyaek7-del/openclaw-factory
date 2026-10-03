import json, urllib.request, urllib.error
d = json.dumps({"email": "verify-loop@t.com", "message": "TEST_EVENT full accept-cycle proof, will be removed", "source": "loop-proof", "campaign": "s3_exec_05"}).encode()
r = urllib.request.Request("http://localhost:3000/api/customer/interest", data=d, headers={"Content-Type": "application/json"})
try:
    resp = urllib.request.urlopen(r, timeout=60)
    print("HTTP", resp.status, resp.read()[:200])
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read()[:200])

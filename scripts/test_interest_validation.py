import json, urllib.request
# Missing message -> expect 400 from validation (proves route+module chain, writes nothing)
d = json.dumps({"email": "test-event@example.com"}).encode()
r = urllib.request.Request("http://localhost:3000/api/customer/interest", data=d, headers={"Content-Type": "application/json"})
try:
    resp = urllib.request.urlopen(r, timeout=60)
    print("UNEXPECTED 200:", resp.read()[:150])
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read()[:150])

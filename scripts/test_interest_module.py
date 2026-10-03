import json, subprocess
payload = {"email": "test-event@example.com", "message": "TEST_EVENT direct module check"}
p = subprocess.run(["python3", "lib/customer_evidence.py", "record"],
                   input=json.dumps(payload), capture_output=True, text=True, timeout=25)
print("stdout:", p.stdout[:300])
print("stderr:", p.stderr[:300])
print("rc:", p.returncode)

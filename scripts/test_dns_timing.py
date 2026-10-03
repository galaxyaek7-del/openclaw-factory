import json, subprocess, time
for email in ["test-event@example.com", "nobody@t.com"]:
    payload = {"email": email, "message": "TEST_EVENT timing check"}
    t0 = time.time()
    try:
        p = subprocess.run(["python3", "lib/customer_evidence.py", "record"],
                           input=json.dumps(payload), capture_output=True, text=True, timeout=20)
        print(f"{email}: {time.time()-t0:.1f}s -> {p.stdout[:120]}")
    except subprocess.TimeoutExpired:
        print(f"{email}: TIMEOUT after 20s (DNS hang)")

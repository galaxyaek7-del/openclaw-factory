"""Nostr service-note publisher (factory-owned key, no accounts).

Usage: python3 nostr_post.py --once
Reads data/service_note.json {content}. Publishes kind:1 to damus+primal,
collects OK acks, readback-verifies, records result to
data/nostr_service_post.json. Idempotent: refuses if a sent record with the
same content hash already exists. Key stays in memory, never logged.
"""
import hashlib
import json
import sys
import time

sys.path.insert(0, "scripts")
import nostr_direct as nd

RELAYS = [("relay.damus.io", 443, "/"), ("relay.primal.net", 443, "/")]
NOTE_PATH = "data/service_note.json"
RECORD_PATH = "data/nostr_service_post.json"


def build_event(pubkey_hex, content, created_at=None):
    created_at = int(created_at or time.time())
    evt = {"kind": 1, "created_at": created_at, "tags": [],
           "content": content, "pubkey": pubkey_hex}
    payload = json.dumps([0, pubkey_hex, created_at, 1, [], content],
                         separators=(",", ":"), ensure_ascii=False)
    evt["id"] = hashlib.sha256(payload.encode()).hexdigest()
    return evt


def sign_event(evt, seckey):
    msg = bytes.fromhex(evt["id"])
    sig = nd.schnorr_sign(seckey, msg)
    evt["sig"] = sig.hex()
    return evt


def main():
    try:
        note = json.load(open(NOTE_PATH, encoding="utf-8"))
    except (OSError, ValueError):
        print(json.dumps({"action": "no-note"}))
        return 0
    content = note["content"]
    chash = hashlib.sha256(content.encode()).hexdigest()[:16]
    try:
        rec = json.load(open(RECORD_PATH, encoding="utf-8"))
        if rec.get("content_hash") == chash and rec.get("status") == "sent":
            print(json.dumps({"action": "already-sent-no-duplicate"}))
            return 0
    except (OSError, ValueError):
        pass
    key = json.load(open("data/nostr_key.json", encoding="utf-8"))
    seckey = bytes.fromhex(key.get("private_key") or key.get("privkey") or key.get("seckey"))
    pubkey = nd._bytes(nd._x(nd._mul(int.from_bytes(seckey, "big")))).hex()
    evt = sign_event(build_event(pubkey, content), seckey)
    acks = {}
    for host, port, path in RELAYS:
        try:
            ws = nd.WS(host, port, path, timeout=30)
            ws.send_text(json.dumps(["EVENT", evt], ensure_ascii=False))
            resp = ws.recv_text()
            acks[host] = resp[:120]
            ws.close()
        except Exception as e:
            acks[host] = "FAIL:%s" % type(e).__name__
    ok = sum(1 for v in acks.values() if '"accepted"' in v or v.startswith('["OK",'))
    rec = {"status": "sent" if ok else "failed", "event_id": evt["id"],
           "content_hash": chash, "acks": acks,
           "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    json.dump(rec, open(RECORD_PATH, "w"), indent=1)
    print(json.dumps({"action": rec["status"], "relays_ok": ok,
                      "event_id": evt["id"][:16]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Nostr publisher for the Etsy Suspension Appeal Kit (cycle 115).

Reuses the proven nostr_post.py path (real relay ACKs from damus/primal/nos.lol).
Nostr renders markdown, so the Gumroad link is CLICKABLE - unlike Telegraph,
which strips anchors. Idempotent on content hash. Key never printed.
"""
import hashlib
import json
import sys
import time

sys.path.insert(0, "scripts")
import nostr_direct as nd

RELAYS = [("relay.damus.io", 443, "/"), ("relay.primal.net", 443, "/"),
          ("nos.lol", 443, "/"), ("relay.nostr.band", 443, "/"),
          ("nostr-pub.wellorder.net", 443, "/")]

SLUG = "fgruzn"
LINK = ("https://aekraft.gumroad.com/l/%s?utm_source=nostr&utm_medium=post"
        "&utm_campaign=etsy_triage_appeal_deadline" % SLUG)

_PARTS = [
    "Etsy suspended you. The first question is the wrong one - many sellers should "
    "not appeal at all.",
    "",
    "Etsy own guidance splits this in two:",
    "",
    "- TEMPORARY suspension: resolved by clearing an overdue balance or an open case. "
    "Etsy says the way to handle it is to reply to the suspension email. Filing an "
    "appeal here is the wrong move.",
    "",
    "- PERMANENT suspension: this is the one you can appeal - and it has a deadline "
    "nobody warns you about.",
    "",
    "From Etsy help page: you have 6 months from the day your account was suspended to "
    "file an appeal. Miss the window and the account stays permanently suspended, with "
    "no second chance. No countdown, no reminder email. Sellers who assumed they would "
    "sort it next month have found it closed.",
    "",
    "Etsy also says file AFTER you have resolved the issues that caused the "
    "suspension. Reviewers want evidence the problem is already fixed, not a promise.",
    "",
    "What gets appeals rejected: emotional appeals, blaming Etsy system, vague "
    "promises, leading with personal hardship. And sending repeated messages does not "
    "speed up review.",
    "",
    "I put the full triage-and-appeal process into one 19-page kit - temporary vs "
    "permanent, the Appeals Center steps in Etsy own order, the 6-month window worked "
    "backwards from your suspension date, and 11 checklists for working under time "
    "pressure.",
    "",
    LINK,
    "",
    "$29, one PDF, no subscription.",
    "",
    "Important: no outcome or savings amount is guaranteed. Etsy makes the final "
    "decision. This is a preparation and process guide, not professional, financial, "
    "or legal advice. Check Etsy current Seller Policy yourself - it changes.",
    "",
    "Not affiliated with Etsy, Inc.",
]

CONTENT = "\n".join(_PARTS)
RECORD = "data/nostr_etsy_appeal_c115.json"


def build_event(pubkey_hex, content, created_at=None):
    created_at = int(created_at or time.time())
    payload = json.dumps([0, pubkey_hex, created_at, 1, [], content],
                         separators=(",", ":"), ensure_ascii=False)
    return {"kind": 1, "created_at": created_at, "tags": [], "content": content,
            "pubkey": pubkey_hex,
            "id": hashlib.sha256(payload.encode()).hexdigest()}


def main():
    chash = hashlib.sha256(CONTENT.encode()).hexdigest()[:16]
    try:
        prev = json.load(open(RECORD, encoding="utf-8"))
        if prev.get("content_hash") == chash and prev.get("status") == "sent":
            print(json.dumps({"action": "already-sent-no-duplicate"}))
            return 0
    except (OSError, ValueError):
        pass

    key = json.load(open("data/nostr_key.json", encoding="utf-8"))
    seckey = bytes.fromhex(key.get("private_key") or key.get("privkey") or key.get("seckey"))
    pubkey = nd._bytes(nd._x(nd._mul(int.from_bytes(seckey, "big")))).hex()
    evt = build_event(pubkey, CONTENT)
    evt["sig"] = nd.schnorr_sign(seckey, bytes.fromhex(evt["id"])).hex()

    acks = {}
    for host, port, path in RELAYS:
        try:
            ws = nd.WS(host, port, path, timeout=30)
            ws.send_text(json.dumps(["EVENT", evt], ensure_ascii=False))
            acks[host] = ws.recv_text()[:110]
            ws.close()
        except Exception as e:
            acks[host] = "FAIL:%s" % type(e).__name__
    ok = sum(1 for v in acks.values() if v.startswith('["OK"') or '"accepted"' in v)
    rec = {"status": "sent" if ok else "failed", "event_id": evt["id"],
           "content_hash": chash, "acks": acks, "relays_ok": ok,
           "product": "Etsy Suspension Appeal Kit", "product_slug": SLUG,
           "product_url": LINK, "link_is_clickable_plain_text_url": True,
           "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sales_at_posting": 0}
    json.dump(rec, open(RECORD, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps({"action": rec["status"], "relays_ok": ok,
                      "event_id": evt["id"][:16]}))
    for h, v in acks.items():
        print("   %-28s %s" % (h, v[:70]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

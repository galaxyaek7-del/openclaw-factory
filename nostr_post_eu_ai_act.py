"""Nostr publisher for the EU AI Act Compliance Toolkit (Cycle 99 follow-on).

Reuses the proven nostr_post_etsy_appeal.py / nostr_post.py path (real relay
ACKs from damus/primal/nos.lol etc). Nostr renders markdown, so the Gumroad
link is CLICKABLE -- unlike Telegraph, which strips anchors (ADR/Cycle 115
finding). Idempotent on content hash. Key never printed.

This is the 2nd of 3 "Start Here" flagship products (customer_site/
products.html) to get a Nostr post -- Etsy Suspension Appeal Kit already has
one (data/nostr_etsy_appeal_c115.json); EU AI Act and Legal Research did not,
confirmed by grep across every data/nostr_post_*.json file before writing
this script.

Every pricing figure below is copied verbatim from a real, already-recorded
citation in data/market_evidence.jsonl -- never invented for this post.
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

SLUG = "iaiyt"
LINK = ("https://aekraft.gumroad.com/l/%s?utm_source=nostr&utm_medium=post"
        "&utm_campaign=eu_ai_act_toolkit" % SLUG)

_PARTS = [
    "EU AI Act compliance templates range from $99 to $5,000/year depending "
    "who you ask.",
    "",
    "A few real, currently-listed prices in this exact space:",
    "",
    "- A template-only product sells at $99 with real customer reviews "
    "(governancedocs.com).",
    "- An 80+ template document kit (68 forms, 68 procedures, 20 registers) "
    "lists at $699 (riskprofs.com).",
    "- A full governance/compliance platform starts at $5,000/year "
    "(governmy.ai) -- enterprise tooling, not a one-time document kit.",
    "",
    "Also worth knowing if you have not checked recently: the standalone "
    "high-risk-system deadline moved from August 2026 to 2 December 2027 "
    "under the Digital Omnibus. The Article 50 transparency rules "
    "(chatbot/deepfake disclosure) are already in force -- that part is not "
    "deferred.",
    "",
    "I put a 31-page implementation guide together at a one-time $155: risk-"
    "classification decision tree, Annex IV technical-documentation "
    "requirements, conformity-assessment steps, human-oversight design, "
    "post-market monitoring, and a 90-day roadmap built to the corrected "
    "timeline above.",
    "",
    LINK,
    "",
    "$155, one PDF, no subscription. Practical implementation guide, not "
    "legal advice -- verify anything specific to your business with counsel.",
    "",
    "Not affiliated with any EU institution or the products named above.",
]

CONTENT = "\n".join(_PARTS)
RECORD = "data/nostr_eu_ai_act_c99.json"


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
           "product": "EU AI Act Compliance Toolkit", "product_slug": SLUG,
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

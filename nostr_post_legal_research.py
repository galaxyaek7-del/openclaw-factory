"""Nostr publisher for the Legal Case Research Automation Kit (Cycle 99
follow-on). Reuses the proven nostr_post_etsy_appeal.py path -- real relay
ACKs, markdown-rendered clickable link, idempotent on content hash, key
never printed.

3rd of 3 "Start Here" flagship products (customer_site/products.html) to
get a Nostr post -- Etsy and EU AI Act already have one.

Every pricing figure is copied verbatim from a real, already-recorded
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

SLUG = "uldlwa"
LINK = ("https://aekraft.gumroad.com/l/%s?utm_source=nostr&utm_medium=post"
        "&utm_campaign=legal_research_automation" % SLUG)

_PARTS = [
    "AI legal research tools for solo attorneys run $104 to $639 per user, "
    "per month.",
    "",
    "Real, currently-listed pricing in this space:",
    "",
    "- CoCounsel by Thomson Reuters: $104-$639/user/month as of August 2026. "
    "Westlaw Advantage + CoCounsel Essentials for a solo attorney, All "
    "States & Federal: $639.20/user/mo on a 1-year term, or $519.35/user/mo "
    "on 3 years (Thomson Reuters' own public configurator).",
    "- Lexis+ AI: $128/$314/$494/month tiers, $171/user/month base.",
    "- Harvey: a 20-seat minimum, commonly quoted around $288,000/year -- "
    "built for firms, not solo practice.",
    "",
    "A real comment from a solo dev bootstrapping, on the cost of legal "
    "help generally: \"those overhead costs are just too much when talking "
    "to an IP attorney can go for $200+ an hour.\" The same math applies to "
    "research tooling priced for firms, not solos.",
    "",
    "I put together a one-time-purchase research workflow instead: query "
    "structuring, source triage, hallucination-verification discipline to "
    "run before relying on any AI output in a matter, citation checking, "
    "and matter-ready memo templates. 16 pages, no invented authorities -- "
    "every case or statute you rely on is one you verify yourself.",
    "",
    LINK,
    "",
    "$29, one PDF, no subscription. A workflow guide, not legal advice and "
    "not a citation library.",
    "",
    "Not affiliated with Thomson Reuters, LexisNexis, or Harvey.",
]

CONTENT = "\n".join(_PARTS)
RECORD = "data/nostr_legal_research_c99.json"


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
           "product": "Legal Case Research Automation Kit", "product_slug": SLUG,
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

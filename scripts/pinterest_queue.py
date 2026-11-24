"""Prepare the Pinterest queue: one validated Metricool review post per product.

    python scripts/pinterest_queue.py [--start 2026-10-27] [--hour 10] [--no-fetch]

Steps: find the target board on the linked Pinterest account (read-only, by
its own public data), check each pin image is publicly reachable, build each
post through social_distribution.metricool (which refuses anything incomplete),
give each product its own day at --hour Europe/Paris, and skip anything already
created. Writes data/pinterest_queue.json. It never calls Metricool: the agent
submits READY items one at a time through the review flow (ask rule), then
records the read-back with metricool.record_attempt().
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from social_distribution import metricool, pinterest_boards  # noqa: E402

QUEUE = ROOT / "data" / "pinterest_queue.json"
PINS = ROOT / "data" / "pinterest_pins.json"
OFFERS = ROOT / "data" / "distribution_offers.json"
TZ = "Europe/Paris"
REVIEWER = "aekgalaxy47@gmail.com"  # the founder's own Metricool login (brand owner)


def _mentions_other_amount(sentence: str, price_cents) -> bool:
    """True if the sentence carries a dollar amount that is not this product's price.

    metricool.build_pinterest_review_post rejects any pin text containing a $amount
    that does not equal the offer price, so a sentence quoting a third party's cost
    ("$350 base per class", "settlements $5K-20K") would make the whole pin
    unpublishable. Such a sentence is dropped rather than weakening that guard: a
    number that is not the price is also the kind of claim the offer's own
    prohibited_claims exclude.
    """
    for amount in re.findall(r"\$\s?(\d[\d,]*(?:\.\d{2})?)", sentence):
        if price_cents is None or abs(float(amount.replace(",", "")) * 100 - price_cents) > 0.5:
            return True
    return False


def pin_text(offer: dict) -> str:
    """The listing's own opening sentences plus its price, within Pinterest's 500."""
    price = f"${offer['price_cents'] / 100:.2f}".replace(".00", "")
    tail = f" {price}, one-time purchase."
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", (offer.get("description") or "").split("\n")[0]) if s.strip()]
    out = ""
    for s in sents:
        if _mentions_other_amount(s, offer.get("price_cents")):
            continue
        if len(out) + len(s) + 1 + len(tail) > 450:
            break
        out = (out + " " + s).strip()
    return (out or offer["title"]) + tail


def fetch_profile(username: str, attempts=4, timeout=40, opener=None) -> str:
    """GET the public profile page (read-only); this host's connection to
    Pinterest is intermittent, so a few spaced attempts, then ConnectionError."""
    import time
    opener = opener or urllib.request.urlopen
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(f"https://www.pinterest.com/{username}/", headers={"User-Agent": "Mozilla/5.0"})
            with opener(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001 -- retried, then reported as UNKNOWN, never as "no board"
            last = e
            time.sleep(min(20, 5 * (i + 1)))
    raise ConnectionError(f"Pinterest profile unreachable after {attempts} attempts: {last}")


def image_status(url, opener=None) -> str:
    """PUBLIC / NOT_PUBLIC / UNKNOWN for one pin image URL.

    A network failure is UNKNOWN, never NOT_PUBLIC. Before 2026-11-24 any
    exception (DNS, timeout, TLS) was folded into "not reachable", so one
    offline tick rewrote a live 105-pin READY queue as all-blocked and the
    queue stayed wrong until someone looked by hand. Only the server actually
    answering 404/410 proves a file is missing.
    """
    opener = opener or urllib.request.urlopen
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
        with opener(req, timeout=30) as r:
            return "PUBLIC" if r.status == 200 else "NOT_PUBLIC"
    except urllib.error.HTTPError as e:
        return "NOT_PUBLIC" if e.code in (404, 410) else "UNKNOWN"
    except Exception:  # noqa: BLE001 -- DNS/timeout/TLS: cannot tell, so do not guess
        return "UNKNOWN"


def url_ok(url, opener=None) -> bool:
    return image_status(url, opener=opener) == "PUBLIC"


def run(*, start: date, hour=10, fetch=True, board=None, offers_doc=None, pins_doc=None, brand_record=None,
        attempts_path=metricool.ATTEMPTS, now=None, image_check=None, image_ok=None, html=None):
    if image_check is None:
        image_check = (lambda u: "PUBLIC" if image_ok(u) else "NOT_PUBLIC") if image_ok else image_status
    offers_doc = offers_doc or json.loads(OFFERS.read_text(encoding="utf-8"))
    pins_doc = pins_doc or json.loads(PINS.read_text(encoding="utf-8"))
    brand_record = brand_record or metricool.brand()
    board_note = "not looked up"
    board_unknown = False
    if board is None and fetch:
        try:
            user = brand_record["connected_networks"]["pinterest"]
            boards = pinterest_boards.parse_boards(html or fetch_profile(user), user)
            board = pinterest_boards.find_board(boards)
            board_note = (f"found '{board['name']}' ({board['id']})" if board else
                          f"no public board named '{pinterest_boards.TARGET_BOARD_NAME}'; boards: {sorted(boards)}")
        except ConnectionError as e:
            board_note = f"UNKNOWN: {e}"
            board_unknown = True
    attempts = metricool.read_attempts(attempts_path)
    created = {a["fingerprint"] for a in attempts if a.get("created")}
    # The fingerprint includes the scheduled time, so a re-plan that moves a pin
    # changes its fingerprint and a submitted pin would look new -- the exact way
    # an automated re-plan posts the same pin twice. Offer id is the stable key.
    created_offers = {a.get("offer_id") for a in attempts if a.get("created")}
    items = []
    day = start
    by_id = {o["offer_id"]: o for o in offers_doc["offers"]}
    order = ["B14-001"] + sorted(k for k in pins_doc["pins"] if k != "B14-001")  # the founder's planned first post
    candidates = []
    for oid in order:
        if oid not in pins_doc["pins"] or oid not in by_id:
            continue
        pin, offer = pins_doc["pins"][oid], dict(by_id[oid])
        offer.update(cover_url=pin["public_url"], pin_text=pin_text(offer), title=offer["title"][:100])
        candidates.append((oid, pin, offer, f"{day}T{hour:02d}:00:00"))
        day += timedelta(days=1)

    # Read-only HEAD checks run concurrently. Sequentially they blew the loop's
    # 8-minute step budget: this host's route to GitHub Pages answered some
    # single pins in 21/42/84 s, so 131 in a row could never finish in time.
    image_states = {}
    if candidates:
        from concurrent.futures import ThreadPoolExecutor
        urls = list({c[1]["public_url"] for c in candidates})
        with ThreadPoolExecutor(max_workers=min(12, len(urls))) as pool:
            image_states = dict(zip(urls, pool.map(image_check, urls)))

    for oid, pin, offer, when_local in candidates:
        item = {"offer_id": oid, "title": offer["title"], "image": pin["public_url"], "when_local": when_local}
        image_state = image_states.get(pin["public_url"], "UNKNOWN")
        if image_state == "UNKNOWN":
            item.update(status="UNKNOWN_IMAGE_UNREACHABLE",
                        reason="could not verify the pin image URL (network); not treated as missing")
        elif image_state != "PUBLIC":
            item.update(status="BLOCKED_IMAGE_NOT_PUBLIC", reason="pin image is not reachable at its public URL yet")
        elif board_unknown:
            item.update(status="UNKNOWN_BOARD_UNREACHABLE", reason=board_note)
        elif not board:
            item.update(status="BLOCKED_NO_BOARD", reason=board_note)
        else:
            try:
                call = metricool.build_pinterest_review_post(
                    offer=offer, board_id=board["id"], when_local=item["when_local"], tz=TZ, reviewers=REVIEWER,
                    approval_system="any", brand_record=brand_record, now=now,
                    expected_brand_id=brand_record.get("brand_id"))
                fp = metricool.fingerprint(call)
                item.update(status="ALREADY_CREATED" if (fp in created or oid in created_offers) else "READY",
                            call=call, fingerprint=fp)
            except metricool.PostRejected as e:
                item.update(status="REJECTED", reason=str(e))
        items.append(item)
        day += timedelta(days=1)
    from collections import Counter
    image_definitive = any(image_states.get(c[1]["public_url"], "UNKNOWN") != "UNKNOWN" for c in candidates)
    if board_unknown:
        # The board lookup failed for network reasons: nothing here is proof
        # that the board or the images are wrong, so the caller must not
        # overwrite a good queue with this run.
        checks_complete = False
    elif board is None:
        # A successful lookup that genuinely found no target board is real.
        checks_complete = True
    else:
        # Board resolved: write the honest per-item states unless every single
        # image check also failed, which would replace a good queue with noise.
        checks_complete = (not candidates) or image_definitive
    return {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "board": board, "board_lookup": board_note,
            "timezone": TZ, "checks_complete": checks_complete, "items": items,
            "summary": dict(Counter(i["status"] for i in items))}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    # Was default="2026-10-27", a fixed date. Every run after that date rebuilt the
    # schedule in the past, and Metricool rejected 24 pins with "the publication
    # time is not in the future". A default that rots is not a default; today is.
    ap.add_argument("--start", default=None)
    ap.add_argument("--hour", type=int, default=10)
    ap.add_argument("--no-fetch", action="store_true")
    # factory_loop.runOnceScript appends --once to every step; this script is a
    # single pass by design, so the flag is accepted and ignored rather than
    # refusing to run from the loop.
    ap.add_argument("--once", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args()
    start = date.fromisoformat(a.start) if a.start else datetime.now(timezone.utc).date()
    q = run(start=start, hour=a.hour, fetch=not a.no_fetch)
    s = q["summary"]
    if not q.get("checks_complete", True) and QUEUE.exists():
        # A network blip must not clobber a good queue. Before this guard one
        # offline tick rewrote every pin as BLOCKED_IMAGE_NOT_PUBLIC /
        # BLOCKED_NO_BOARD and the real READY plan was lost.
        print(json.dumps({"action": "blocked",
                          "detail": f"network checks incomplete; kept previous queue. board={q['board_lookup']} summary={s}",
                          "board_lookup": q["board_lookup"], "summary": s, "kept_previous": True}, ensure_ascii=False))
        sys.exit(0)
    QUEUE.write_text(json.dumps(q, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    # Single line: factory_loop.runOnceScript parses the last stdout line as JSON,
    # so an indented dump made every tick report "could not parse ... '}'".
    # `action`/`detail` are the fields the loop logs; without them the step shows
    # as a silent "none" and the queue state is invisible in the tick report.
    s = q["summary"]
    print(json.dumps({"action": "reported",
                      "detail": f"board={q['board_lookup']} ready={s.get('READY', 0)} rejected={s.get('REJECTED', 0)}",
                      "board_lookup": q["board_lookup"], "summary": s}, ensure_ascii=False))

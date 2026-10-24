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


def pin_text(offer: dict) -> str:
    """The listing's own opening sentences plus its price, within Pinterest's 500."""
    price = f"${offer['price_cents'] / 100:.2f}".replace(".00", "")
    tail = f" {price}, one-time purchase."
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", (offer.get("description") or "").split("\n")[0]) if s.strip()]
    out = ""
    for s in sents:
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


def url_ok(url, opener=None) -> bool:
    opener = opener or urllib.request.urlopen
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
        with opener(req, timeout=30) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def run(*, start: date, hour=10, fetch=True, board=None, offers_doc=None, pins_doc=None, brand_record=None,
        attempts_path=metricool.ATTEMPTS, now=None, image_ok=url_ok, html=None):
    offers_doc = offers_doc or json.loads(OFFERS.read_text(encoding="utf-8"))
    pins_doc = pins_doc or json.loads(PINS.read_text(encoding="utf-8"))
    brand_record = brand_record or metricool.brand()
    board_note = "not looked up"
    if board is None and fetch:
        try:
            user = brand_record["connected_networks"]["pinterest"]
            boards = pinterest_boards.parse_boards(html or fetch_profile(user), user)
            board = pinterest_boards.find_board(boards)
            board_note = (f"found '{board['name']}' ({board['id']})" if board else
                          f"no public board named '{pinterest_boards.TARGET_BOARD_NAME}'; boards: {sorted(boards)}")
        except ConnectionError as e:
            board_note = f"UNKNOWN: {e}"
    created = {a["fingerprint"] for a in metricool.read_attempts(attempts_path) if a.get("created")}
    items, day = [], start
    by_id = {o["offer_id"]: o for o in offers_doc["offers"]}
    order = ["B14-001"] + sorted(k for k in pins_doc["pins"] if k != "B14-001")  # the founder's planned first post
    for oid in order:
        if oid not in pins_doc["pins"] or oid not in by_id:
            continue
        pin, offer = pins_doc["pins"][oid], dict(by_id[oid])
        offer.update(cover_url=pin["public_url"], pin_text=pin_text(offer), title=offer["title"][:100])
        item = {"offer_id": oid, "title": offer["title"], "image": pin["public_url"], "when_local": f"{day}T{hour:02d}:00:00"}
        if not image_ok(pin["public_url"]):
            item.update(status="BLOCKED_IMAGE_NOT_PUBLIC", reason="pin image is not reachable at its public URL yet")
        elif not board:
            item.update(status="BLOCKED_NO_BOARD", reason=board_note)
        else:
            try:
                call = metricool.build_pinterest_review_post(
                    offer=offer, board_id=board["id"], when_local=item["when_local"], tz=TZ, reviewers=REVIEWER,
                    approval_system="any", brand_record=brand_record, now=now,
                    expected_brand_id=brand_record.get("brand_id"))
                fp = metricool.fingerprint(call)
                item.update(status="ALREADY_CREATED" if fp in created else "READY", call=call, fingerprint=fp)
            except metricool.PostRejected as e:
                item.update(status="REJECTED", reason=str(e))
        items.append(item)
        day += timedelta(days=1)
    from collections import Counter
    return {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "board": board, "board_lookup": board_note,
            "timezone": TZ, "items": items, "summary": dict(Counter(i["status"] for i in items))}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2026-10-27")
    ap.add_argument("--hour", type=int, default=10)
    ap.add_argument("--no-fetch", action="store_true")
    a = ap.parse_args()
    q = run(start=date.fromisoformat(a.start), hour=a.hour, fetch=not a.no_fetch)
    QUEUE.write_text(json.dumps(q, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"board_lookup": q["board_lookup"], "summary": q["summary"]}, indent=1, ensure_ascii=False))

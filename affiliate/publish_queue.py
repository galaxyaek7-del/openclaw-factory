#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Publish queue: cap-aware retry scheduler for pending Gumroad products.
Detects cap reset (probe create is NOT used — a failed create is free but
noisy; instead the queue retries on heartbeat cadence and stops at the
first cap signal). Verifies HTTP + existence + price + URL per publish."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
QUEUE_PATH = _FACTORY_ROOT / "data" / "publish_queue.json"


def load_queue() -> list:
    if QUEUE_PATH.exists():
        try:
            return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
        except ValueError:
            pass
    return [
        {"slug": "ppwr_seller_update_pack", "file": "factory_workspace/sprint14/ppwr_seller_update_pack.pdf",
         "price": 39, "title": "PPWR Seller Update Pack (August 2026 Rules Now Applying)",
         "description": "Packaging & Packaging Waste Regulation now applying. Orientation, not legal advice.",
         "tags": ["ppwr", "packaging", "eu compliance", "epr"], "status": "PENDING_CAP"},
        {"slug": "marketplace_fee_escape_pack", "file": "factory_workspace/sprint14/marketplace_fee_escape_pack.pdf",
         "price": 39, "title": "Marketplace Fee Escape Pack (Etsy & Amazon 2026)",
         "description": "Stay/diversify/leave math for fee-squeezed sellers. Verify current fees.",
         "tags": ["etsy", "amazon", "fees", "ecommerce"], "status": "PENDING_CAP"},
        {"slug": "eudr_due_diligence_starter", "file": "factory_workspace/sprint14/eudr_due_diligence_starter.pdf",
         "price": 39, "title": "EUDR Due Diligence Starter (Dec 2026 Deadline)",
         "description": "Deforestation-free proof for commodity importers. Orientation, not legal advice.",
         "tags": ["eudr", "deforestation", "eu compliance", "import"], "status": "PENDING_CAP"},
    ]


def save_queue(items: list) -> None:
    QUEUE_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")


def retry_queue() -> dict:
    """Attempt each PENDING_CAP item once; stop at first cap signal."""
    from channels import gumroad_publisher as gp
    items = load_queue()
    if not QUEUE_PATH.exists():
        save_queue(items)
    done, blocked, errors = [], False, []
    token = gp.load_token()
    for it in items:
        if it.get("status") != "PENDING_CAP":
            continue
        try:
            prod = gp.create_product(token, {"file_path": it["file"],
                                             "price_cents": int(it["price"] * 100),
                                             "title": it["title"],
                                             "description": it["description"]})
            pid = prod.get("id")
            gp.enable_product(token, pid)
            try:
                gp.update_product(token, pid, {"tags": it.get("tags", ["toolkit"])})
            except Exception:
                pass
            check = gp.get_product(token, pid)
            assert check.get("price") == int(it["price"] * 100), "price mismatch"
            assert (check.get("short_url") or check.get("url")), "no URL"
            it.update({"status": "LIVE", "product_id": pid,
                       "url": check.get("short_url") or check.get("url"),
                       "published_at": datetime.now(timezone.utc).isoformat()})
            done.append(it["slug"])
        except Exception as e:
            msg = str(e)[:160]
            errors.append((it["slug"], msg))
            if "10 products per day" in msg or "429" in msg or "rate" in msg.lower():
                blocked = True
                break
    save_queue(items)
    return {"published": done, "cap_blocked": blocked, "errors": errors,
            "pending": sum(1 for i in items if i.get("status") == "PENDING_CAP")}

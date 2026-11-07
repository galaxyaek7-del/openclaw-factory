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
    """Report the pending items. It does NOT publish (changed 2026-11-07).

    This module used to create AND enable Gumroad products directly (create_product + enable_product), an auto-publish path that
    sat outside the per-product approval flow; nothing in the factory called it, and the repository invariant
    (tests/test_final_rehearsal.py::test_no_autopublish_path) forbids it in affiliate/. Live publication now goes only through
    scripts/publish_batch14.py / scripts/publish_approved_daily.py, which need the founder's approval naming the product, the
    Quality Gate and channels/write_gate.py. Live publish from this queue: NOT IMPLEMENTED on purpose.
    """
    items = load_queue()
    pending = [i for i in items if i.get("status") == "PENDING_CAP"]
    return {"published": [], "cap_blocked": False, "errors": [], "pending": len(pending),
            "note": "report only: publication needs a founder approval naming the product (scripts/publish_batch14.py)"}

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge Invoice Generator (Customer Platform Round 3, 2026-07-29).

Deterministic invoice built entirely from real, already-recorded pipeline
state -- the locked contract price and the real Paddle transaction id --
never a second, independently-computed price. Only ever called once a real
Paddle transaction has actually been confirmed paid (customer_pipeline.py's
check_payment_status()); this module has no opinion on payment status
itself.
"""

from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc).isoformat()


def generate_invoice(record, transaction):
    """record: the pipeline record (must have "proposal" and "contract").
    transaction: the real Paddle transaction dict that was confirmed paid.
    """
    proposal = record.get("proposal") or {}
    contract = record.get("contract") or {}
    parties = contract.get("parties") or {}
    price = proposal.get("price")
    currency = proposal.get("currency", "USD")

    return {
        "invoice_number": f"INV-{record['request_id'][-10:].upper()}",
        "issued_at": _now(),
        "provider": "Galaxy Forge",
        "bill_to": parties.get("customer"),
        "line_items": [{
            "description": contract.get("scope") or "Galaxy Forge product/service",
            "amount": price,
            "currency": currency,
        }],
        "total": price,
        "currency": currency,
        "payment_reference": transaction.get("id"),
        "status": "PAID",
    }

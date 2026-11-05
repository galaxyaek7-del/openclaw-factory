#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Founder tool: log ONE real affiliate commission you saw in a partner dashboard.

Why it exists: the commission ledger has no automatic feed (no webhook from systeme.io), so
without a human entry it can never move. This is a thin wrapper over
commission_ledger.record_commission(); all anti-fabrication rules stay there.

Dry run by default (prints what would be written). Nothing is written without --apply.

    python scripts/record_real_commission.py --amount 29.50 --status PENDING \
        --evidence "systeme.io dashboard 2026-11-20, referral #123" --apply
    python scripts/record_real_commission.py --amount 29.50 --status PAID \
        --evidence "payout email 2026-12-01" --txid SYS-PAYOUT-0001 --apply

A PAID or CONFIRMED record needs --txid (the partner's own transaction id). A repeat of the
same txid is refused (no double counting). Use --environment TEST to rehearse.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import commission_ledger as cl  # noqa: E402

DEFAULT_PARTNER = "systeme.io"
DEFAULT_OPPORTUNITY = "CO-systeme-affiliate"


def build_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--amount", type=float, required=True, help="gross commission in the stated currency")
    p.add_argument("--status", required=True, choices=cl.COMMISSION_STATUSES)
    p.add_argument("--evidence", required=True, help="what you saw and where (dashboard, email, date)")
    p.add_argument("--txid", default=None, help="partner transaction id (required for CONFIRMED/PAID)")
    p.add_argument("--environment", default="REAL", choices=cl.LEDGER_ENVIRONMENTS)
    p.add_argument("--currency", default="USD")
    p.add_argument("--fees", type=float, default=0.0)
    p.add_argument("--partner", default=DEFAULT_PARTNER)
    p.add_argument("--opportunity", default=DEFAULT_OPPORTUNITY)
    p.add_argument("--ledger", default=None, help="ledger path (tests); default data/commission_ledger.jsonl")
    p.add_argument("--apply", action="store_true", help="actually write (default: dry run)")
    return p.parse_args(argv)


def run(args) -> int:
    plan = {"partner": args.partner, "opportunity": args.opportunity, "status": args.status,
            "environment": args.environment, "amount": args.amount, "currency": args.currency,
            "txid": args.txid, "evidence": args.evidence}
    if not args.apply:
        print(json.dumps({"dry_run": True, "would_write": plan}, ensure_ascii=False, indent=1))
        print("Nothing written. Add --apply to record it.")
        return 0
    try:
        rec = cl.record_commission(
            args.partner, args.opportunity, args.status, args.amount, args.environment,
            external_transaction_id=args.txid, fees=args.fees, currency=args.currency,
            evidence=args.evidence, source="founder_manual_entry", ledger_path=args.ledger)
    except (cl.AntiFabricationError, cl.DuplicateCommissionError, ValueError) as e:
        print("REFUSED: %s" % e)
        return 2
    print("RECORDED:", json.dumps({k: rec.get(k) for k in
                                   ("environment", "commission_status", "gross_commission", "external_transaction_id")},
                                  ensure_ascii=False))
    s = cl.real_commission_summary(args.ledger)
    print("REAL records: %s, paid USD: %s" % (s["real_commission_records"], s["real_paid_commission_usd"]))
    return 0


if __name__ == "__main__":
    sys.exit(run(build_args()))

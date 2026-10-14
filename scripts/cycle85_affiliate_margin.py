"""Cycle 85 -- real margin per sale, so an affiliate rate can be chosen on
evidence instead of on the local economics config, which is wrong.

THE CONFIG IS WRONG
-------------------
config/economics.json records Gumroad as royalty_rate 0.9 with
flat_fee_usd 0.0, self-described as "Simplified". Gumroad's own help article
66 (https://gumroad.com/help/article/66-gumroads-fees) states:

    "For sales made on Gumroad's website, we charge a 10% + $0.50 fee per
     transaction. This does not include: Credit card processing (2.9% + $0.30)"

So the real per-sale cost is roughly 12.9% + $0.80, not 10% + $0. That
$0.80 is not a rounding detail: it is 3.3% of a $24 product and 0.5% of a
$155 one, and it is exactly why cheap products cannot carry an affiliate
commission.

DISCOVER IS A SEPARATE, WORSE PATH
----------------------------------
    "Sales made through Gumroad's marketplace (discovery sales via
     Gumroad.com) are subject to a flat 30% fee."

An affiliate is a DIRECT sale, so the 10% + $0.50 path applies, and the
affiliate commission is the seller's own money on top of Gumroad's.

WHAT THIS MODULE DOES
---------------------
Computes, per candidate price, what is actually left after Gumroad and card
processing, and then what remains under several candidate affiliate rates --
so the rate can be chosen against a floor rather than guessed.

Every rate below is quoted from Gumroad's own published fee page, not
estimated. Read-only, offline, $0. Nothing here performs a purchase.

Run:  python scripts/cycle85_affiliate_margin.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent

# Quoted from https://gumroad.com/help/article/66-gumroads-fees
GUMROAD_PCT = 0.10
GUMROAD_FLAT = 0.50
CARD_PCT = 0.029
CARD_FLAT = 0.30
DISCOVER_PCT = 0.30  # not applicable to affiliate/direct sales


def net_to_seller(price: float) -> float:
    """What the seller actually receives on a direct card sale."""
    fees = (price * GUMROAD_PCT + GUMROAD_FLAT
            + price * CARD_PCT + CARD_FLAT)
    return round(price - fees, 2)


def with_affiliate(price: float, pct: float) -> dict:
    base = net_to_seller(price)
    commission = round(price * pct, 2)
    return {
        "price": price,
        "gumroad_plus_card_fees": round(price - base, 2),
        "seller_net_before_affiliate": base,
        "effective_fee_pct": round((price - base) / price * 100, 2),
        f"affiliate_{int(pct * 100)}pct_commission": commission,
        f"seller_net_after_affiliate_{int(pct * 100)}pct": round(base - commission, 2),
    }


CANDIDATES = [
    ("EU AI Act Transparency & AI Literacy Quickstart", 9.0, None),
    ("EU AI Act Compliance Quickstart Checklist", 19.0, None),
    ("Turo Guest Dispute Toolkit", 29.0, "adyvd"),
    ("EU AI Act Audit Logging Kit", 29.0, None),
    ("Clinic No-Show Reduction Kit", 59.0, "eiztlg"),
    ("EU AI Act Compliance Toolkit (TARGET)", 155.0, "iaiyt"),
]

RATES = (0.20, 0.25, 0.30)


def main() -> int:
    out = {
        "probe": "cycle85_affiliate_margin",
        "cost_usd": 0,
        "fee_source": "https://gumroad.com/help/article/66-gumroads-fees",
        "quoted_fees": {
            "gumroad_direct_pct": GUMROAD_PCT,
            "gumroad_direct_flat_usd": GUMROAD_FLAT,
            "card_processing_pct": CARD_PCT,
            "card_processing_flat_usd": CARD_FLAT,
            "discover_marketplace_pct": DISCOVER_PCT,
            "discover_note": ("applies to Gumroad-sourced discovery sales, NOT "
                              "to affiliate or direct-link sales"),
        },
        "config_discrepancy": {
            "file": "config/economics.json",
            "says": "royalty_rate 0.9, flat_fee_usd 0.0 ('Simplified')",
            "reality": "12.9% + $0.80 per direct card sale",
            "consequence": ("every margin computed from that config is "
                            "overstated, and the error grows as price falls"),
        },
        "candidates": [],
    }

    print("=" * 74)
    print("REAL MARGIN PER DIRECT SALE  (Gumroad 10%+$0.50 + card 2.9%+$0.30)")
    print("=" * 74)
    for name, price, sid in CANDIDATES:
        row = {"name": name, "short_id": sid}
        for r in RATES:
            row.update(with_affiliate(price, r))
        out["candidates"].append(row)
        tag = f"  /l/{sid}" if sid else ""
        print(f"\n{name}{tag}  ${price:.0f}")
        print(f"  seller net before affiliate : ${row['seller_net_before_affiliate']:>7.2f}"
              f"   (effective fee {row['effective_fee_pct']}%)")
        for r in RATES:
            k = int(r * 100)
            print(f"  affiliate {k:>2}%  -> commission ${row[f'affiliate_{k}pct_commission']:>6.2f}"
                  f"   seller keeps ${row[f'seller_net_after_affiliate_{k}pct']:>7.2f}")

    print()
    print("=" * 74)
    print("CORRECTION TO THE CYCLE 85 REPORT")
    print("=" * 74)
    print("An earlier draft of the report claimed a 30% commission \"exceeds the")
    print("price\" on the $9 Transparency Checklist. That was wrong. 30% of $9 is")
    print("$2.70, and the seller still keeps a positive amount.")
    print()
    print("The accurate reason not to attach commission to the three cheap EU AI")
    print("Act listings is not that it is impossible -- it is that the affiliate")
    print("earns $2.70 on a $9 sale and $5.70 on a $19 sale. That is not worth an")
    print("hour of anyone's promotion, so those listings would earn no volume")
    print("while still exposing the margin to a sale that costs more to support")
    print("than it returns. The $155 listing is the only one where the commission")
    print("is large enough to motivate real promotion AND the seller still clears")
    print("the factory's $70 elite floor ($87.70).")

    print()
    print("=" * 74)
    print("READING")
    print("=" * 74)
    print("The fixed $0.80 is why price decides. At $29 it eats 2.8% of the")
    print("sale before an affiliate earns a cent; at $155 it eats 0.5%.")
    print("An affiliate rate that is safe on a $155 product is not the same")
    print("rate that is safe on a $29 one.")
    print()
    print("Also worth stating plainly: a Discover/marketplace sale costs 30%")
    print("flat, nearly double a direct sale. Driving an affiliate to send")
    print("buyers to Gumroad Discover would be the expensive path. Direct")
    print("product links are the cheap one.")

    (ROOT / "data" / "cycle85_affiliate_margin.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
# Galaxy Forge — First Deal Commercial Economics

**Date:** 2026-08-08 | ADR-229, Phase 36, Section 7. `commission_engine.commission_economics()` applied to `CO-n8n-affiliate`.

---

## Separation of terms (never confused)

| Term | Value | Basis |
|---|---|---|
| **COMMISSION_RATE** | 30% | OBSERVED (n8n's own real, live-fetched page, corroborated by independent WebSearch) |
| **COMMISSION_PER_SALE** | 30% × 12 months of a referred subscription | OBSERVED (real, disclosed program mechanic) |
| **RECURRING_COMMISSION** | Yes, for 12 months per referral | OBSERVED |
| **EXPECTED_COMMISSION** (per one hypothetical Pro-tier referral) | $3.60 (30% × $600 assumed 12-month Pro-tier value × 2% assumed conversion) | **ESTIMATED** — the $50/month Pro price is a real, publicly known figure not independently re-verified via a live pricing-page fetch this round; the 2% conversion rate is a disclosed industry-baseline assumption, not an observed rate (this factory has 0 real conversions of any kind) |
| **REAL_COMMISSION** | $0 | REAL — no external transaction has occurred |
| **PAYOUT** | $0 | REAL — no payout has ever occurred; PayPal, €100 minimum, monthly (real, disclosed mechanic, unexercised) |

## The calculation, shown in full

```
EXPECTED_GROSS_COMMISSION = expected_deal_value × commission_rate × expected_conversion_rate
                          = $600 × 0.30 × 0.02
                          = $3.60

EXPECTED_ACQUISITION_COST = ai_cost + outreach_cost = $0.01 + $0 = $0.01

EXPECTED_NET_CONTRIBUTION = $3.60 − $0.01 − $0 (platform_cost) = $3.59
```

**EXPECTED_PAYBACK:** `UNKNOWN` — no real historical time-to-payout data exists anywhere in this factory (a standing, disclosed gap since Phase 31).

## What this number is not

This $3.60/$3.59 figure is a **single hypothetical referral's** expected value under a **disclosed, ESTIMATED** conversion assumption — it is not a forecast of aggregate revenue, not a claim about how many referrals will occur, and it never enters `REAL_REVENUE`/`REAL_COMMISSION_REVENUE`, both of which remain **$0** per `commission_ledger.py`'s own hard anti-fabrication guard until a real, externally-verified transaction occurs.

---

*See also: `LAUNCH/FIRST_DEAL_OPPORTUNITY_DOSSIER.md`, `COMMERCIAL/COMMISSION_ECONOMICS.md`.*

# Affiliate subsystem: current state (2026-10-23)

Evidence classes: OBSERVED, DERIVED, INFERRED, UNKNOWN. Index of all affiliate documents: [README.md](README.md).

## Code that exists

| Area | Modules | Class |
|---|---|---|
| Program registry (read model) | `affiliate/registry.py` (authoritative source `data/commission_opportunities.jsonl`) | OBSERVED |
| Eligibility and payout (Algeria) | `affiliate/eligibility_matrix.py` (`data/affiliate_algeria_evidence.json`) | OBSERVED |
| Link registry | `affiliate/links.py` (`data/affiliate_links.jsonl`) | OBSERVED |
| Amazon product links + redirect | `affiliate_commerce/networks.py`, `products.py`, `/api/affiliate/click/:id` in `server.js` | OBSERVED |
| Click tracking | `affiliate_commerce/click_tracking.py` (`data/affiliate_clicks.jsonl`) | OBSERVED |
| Content QA | `affiliate/content_qa.py` (disclosure, dated claims, banned phrases) | OBSERVED |
| Commission ledger | `commission_ledger.py` (REAL/TEST/SIMULATION/PROVISIONAL, anti-fabrication) | OBSERVED |
| Commerce engine | `commission_engine.py` (2,611 lines; has uncommitted edits from a parallel session) | OBSERVED |
| Revenue firewall | `affiliate/ledger_firewall.py` | OBSERVED |
| Publication gate | `channels/write_gate.py` (messages need `GF_ALLOW_OUTBOUND_MESSAGES`) | OBSERVED |

Sprawl: about 65 affiliate modules; 20 untracked (parallel session work in progress, e.g. `affiliate/portfolio.py`, 1,558 lines). Overlapping roles: two firewalls (`firewall.py`, `ledger_firewall.py`), two control panels, three loops, two ledgers (`aff_ledger.py`, `commission_ledger.py`), three registries (`registry.py`, `eligibility_matrix.py`, untracked `portfolio.py`).

## Real program portfolio (tracked registry)

- 17 records for 15 partners; 3 of the records are sales channels, not affiliate programs (Gumroad marketplace, Etsy marketplace, Paddle partnership).
- Registry status: QUALIFIED 15, HOLD 1, RESEARCHING 1. Approvals recorded: 0.
- Eligibility evidence found: 4 (n8n, Brevo, AWeber, SiteGround); unknown: 13.
- Payout: conditional 6, unverified 11, verified 0.
- The "32 records / 10 CONDITIONAL / 19 UNKNOWN" figures come from the untracked `affiliate/portfolio.py`; the tracked registry and that file disagree (two sources of truth).

## Real financial state

| Measure | Value | Class |
|---|---|---|
| REAL commission records | 0 (the ledger holds 1 TEST record) | OBSERVED |
| Confirmed or paid commission | 0 USD | OBSERVED |
| FIRST_REAL_DOLLAR | False | OBSERVED |
| Recorded clicks | 30 (27 without a source, 3 "direct"); local server only | OBSERVED |
| Real public click traffic | UNKNOWN (no receiver on GitHub Pages) | OBSERVED |
| Amazon Associates tag | not configured: every Amazon click earns 0 | OBSERVED |

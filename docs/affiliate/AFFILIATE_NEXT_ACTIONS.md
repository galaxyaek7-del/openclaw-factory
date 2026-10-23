# Affiliate next actions

## Founder (external authority required)

1. Apply to one program with evidence of eligibility (n8n, Brevo, AWeber or SiteGround); record the outcome with `affiliate.registry.record_approval(...)` and the approval email reference.
2. Confirm the payout account (the conditional rail) can receive a transfer.
3. If Amazon is wanted: create the Associates account and set `AMAZON_ASSOCIATE_TAG`.
4. Choose a free analytics service for the static site (or a host for `/api/page-view` and `/api/affiliate/click`), so public visits and clicks can be measured at all.

## Engineering (safe, next)

1. A7: separate sales channels from affiliate programs in the registry.
2. A9: make `commission_engine` reuse `real_commission_summary()` once the parallel session's edits land.
3. A8: settle one portfolio source (tracked registry vs untracked `affiliate/portfolio.py`) with the parallel session.
4. A10: encode and validate the Amazon tag in `networks.build_amazon_url`.
5. A manual import helper for network statements (CSV) that writes REAL records with evidence and transaction ids, refusing duplicates.

## Revenue truth

Clicks: UNKNOWN (public), 30 local rows. Conversions: ZERO VERIFIED. Commissions: ZERO VERIFIED. Payouts: ZERO VERIFIED.

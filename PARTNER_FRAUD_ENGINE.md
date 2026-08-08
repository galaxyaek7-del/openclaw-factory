# Galaxy Forge — Partner Fraud Engine

**Date:** 2026-08-08 | ADR-215, Phase 25, Section 27. `global_partnership_network.partner_fraud_status()` — genuinely new this round.

---

## The real state machine

`SUSPICION → INVESTIGATION → EVIDENCE → DECISION` (`FRAUD_STATES`, 5 named states including `NONE`). **Never auto-accuses a partner** — verified by a dedicated regression test confirming `current_state` stays `NONE` and `open_investigations` stays empty absent real evidence.

## The 10 named fraud categories monitored

Fake Leads, Duplicate Leads, Artificial Traffic, Self-Referral, Suspicious Conversion Patterns, Refund Abuse, Attribution Manipulation, Commission Abuse, Unusual Customer Patterns, Automated Fraud.

## Real, honest state

**0 real conversions/leads/commissions exist anywhere in this factory's partner network** — fraud detection has nothing real to monitor yet. This is the correct, honest state, not a missing capability: the state machine is real and ready to escalate the moment a real suspicious pattern appears.

---

*See also: `PARTNER_DUE_DILIGENCE.md`, `PARTNER_TERMINATION.md`.*

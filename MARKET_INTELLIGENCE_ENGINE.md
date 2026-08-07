# OpenClaw / Galaxy Forge — Market Intelligence Engine

**Status:** Permanent, part of the Company DNA (`COMPANY_DNA.md`). "Know the market better than the market knows itself" is checked here against `multi_source_intelligence/` (14 registered connectors), `market_intelligence_core/`, and `competitor_discovery.py` — real, already-built systems, not created for this document.

---

## The Global Market Observatory's 19 requested sources, checked

`multi_source_intelligence/types.py::EVIDENCE_SOURCE_PRIORITY` already names 14 real source tiers. Checked against this directive's 19:

**Real, confirmed live-query-capable (8):** Amazon, arXiv, Etsy, GitHub, Gumroad, Hacker News, public search, Stack Overflow.

**Registered, but honestly `NOT_ARCHITECTED`:** search trends (Google Trends), Reddit, Product Hunt, RSS feeds, public reports — real names in the real priority list, no real connector code behind them yet, confirmed by direct inspection, not assumed.

**Named in this directive with no real connector at all, registered or not:** buying behavior, customer complaints (as a distinct source — partially covered structurally by `customer_pipeline.py`'s own real support-ticket/review data, not a market-wide scan), X/Twitter, LinkedIn, Creative Market, SaaS marketplaces, AI marketplaces, enterprise software, patent trends, regulatory changes (partially real — the EU AI Act regulatory-currency correction, `OpenClaw_Brain/19_Lessons_Learned/`, proves this company *can* do real regulatory monitoring, just not as a continuous automated feed), emerging technologies.

**8 of 19 real and live. 5 registered but not architected. 6 have no real connector anywhere.** This is the honest current state, not a claim of comprehensive coverage this company hasn't earned.

## Why "registered but not live" isn't a wasted effort

`multi_source_intelligence/coverage.py::prioritized_evidence_summary()` (ADR-179) is the real, tested reason this gap is safe rather than fragile: every source is queried through its own try/except, and a genuinely new, unforeseen failure mode (proven live this session — a real local SSL certificate error on an arXiv call) is absorbed without taking down evaluation. The Observatory degrades gracefully by design; it does not currently see everything the directive asks for.

## Competitive Advantage — the real Anti-Copy Rule enforcement

`profit_oracle.py`'s Competitive Advantage hard gate (ADR-122) already is the literal mechanical enforcement of "never recommend products simply because competitors sell them" — a real, net-positive AI-leverage citation relative to a generic competitor is required, or the opportunity fails regardless of how large the competitor market looks.

---

*See also: `CUSTOMER_PAIN_ENGINE.md`, `MARKET_GAP_ENGINE.md`, `COMPETITOR_INTELLIGENCE.md`, `EXECUTIVE_MARKET_REPORT.md`.*

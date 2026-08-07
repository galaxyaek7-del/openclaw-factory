# OpenClaw / Galaxy Forge — Competitor Intelligence

**Status:** Permanent, part of the Company DNA (`COMPANY_DNA.md`). "Maintain live intelligence for every major competitor" checked against `competitor_discovery.py` and the real `data/competitor_database.json` (57 real tracked niches as of this writing) — field by field, honestly, not overstated.

---

## The 7 requested tracking fields, checked against a real database entry

A real, current entry (`data/competitor_database.json`) was read directly while writing this document, not assumed:

| Requested field | Real coverage |
|---|---|
| Products | **Partial** — real competitor names/URLs discovered via Hacker News/GitHub mentions, classified by category |
| Pricing | **Honestly not real** — the database's own real per-competitor `metrics.pricing_model` field literally states: "not confidently inferable from HN/GitHub data alone" |
| Features | **Not tracked** — no real field exists |
| Weaknesses | **Partial** — `category_reason` sometimes carries a real, disclosed confidence note (e.g., "very weak signal, 3 points, 1 comment — not enough confidence to classify") |
| Reviews | **Not real** — no live review-aggregation source is connected |
| Customer complaints | **Not real** — same gap |
| Positioning | **Partial** — the real `category` classification (Emerging Startup / Unclassified / etc.) |

**2 of 7 fields have real, if partial, coverage. 5 are honestly not real today** — and the database's own real per-entry data says so explicitly, for every single competitor, not just disclosed once in this document. Sample real, verbatim disclosures already in the live database: "no free visit-tracking tool connected (SimilarWeb/Ahrefs need a paid subscription)"; "Reddit API needs credentials not available this session"; "no live Trends connection (n8n Sensing Engine built, not activated)"; "needs prior official contact with Product Hunt before commercial use."

## "Update continuously" — the real, honest cadence

`competitor_discovery.py`'s real per-niche scan is genuinely re-runnable, but it is **on-demand, per-niche**, not a standing, continuous, all-competitors-at-once feed. `data/competitor_history.jsonl` (real, append-only) is where real snapshot deltas would accumulate if the same niche were re-scanned over time — this exists as a mechanism, not yet as a rich real history, since most niches have been scanned once.

## Why this gap is disclosed rather than glossed over

Every one of the 5 real gaps above requires either a paid tool (SimilarWeb, Ahrefs) or real platform credentials (Reddit API, a prior Product Hunt relationship) this company does not have yet. Pretending this data exists — even approximately — would be a direct, textbook violation of `COMPANY_DNA.md`'s "evidence over assumptions" principle, applied to the exact class of claim (a competitor's real pricing or real weaknesses) a customer or investor would most quickly catch as fabricated if it were wrong.

---

## Phase 17 update (2026-08-08, ADR-207) — Competitor Change Detection

The founder's "Global Intelligence & Competitive Moat Engine" directive (Section 5) asked for detection of 12 named competitor change types (new product, price change, new subscription, new market, new partnership, new feature, new platform, complaint patterns, technology change, business model change, shutdown, acquisition/expansion). Checked against this document's own real, disclosed gaps above before building anything: `competitor_discovery.py::diff_competitor_snapshots()` (cited above, "Update continuously") already real-detects exactly 1 of these 12 — real `github_stars`/`hacker_news_points` growth, a genuine but narrow proxy for "new feature"/"expansion" activity. **The other 11 named change types have no real data source anywhere in this factory** — each would require either a paid tool (price-tracking, SimilarWeb) or a real, credentialed platform API this company does not have, the exact same 5 gaps this document already disclosed in 2026-07-29 and re-confirmed unchanged this round. No new detection code was built to paper over this — the honest state is 1/12, not fabricated coverage of the rest.

Also re-verified this round: the 2 real named competitors for the EU AI Act Compliance Toolkit (governancedocs.com, riskprofs.com) remain this factory's only instance of genuinely current, human-verified competitor intelligence — see `competitive_moat_engine.py` (new, ADR-207) for how that evidence now feeds a real, product-level moat assessment.

---

*See also: `MARKET_INTELLIGENCE_ENGINE.md`, `MARKET_GAP_ENGINE.md`, `EXECUTIVE_MARKET_REPORT.md`, `COMPETITIVE_MOAT_ENGINE.md` (Phase 17).*

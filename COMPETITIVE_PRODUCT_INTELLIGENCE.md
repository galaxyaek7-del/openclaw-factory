# Galaxy Forge — Competitive Product Intelligence

**Date:** 2026-08-08 | ADR-213, Phase 23, Section 7. Citation over `competitor_discovery.py` (real, already-built) — not rebuilt.

---

## The 13 named fields, checked

| Field | Real coverage |
|---|---|
| Competitors, Products | `competitor_discovery.py::get_or_refresh_competitors()` — real, cached, sourced from HN/GitHub |
| Pricing | Real where a competitor's pricing was directly researched (e.g. `governancedocs.com`/`riskprofs.com` for the EU AI Act Toolkit); `UNKNOWN` otherwise — never fabricated |
| Features | Not systematically extracted — real gap |
| Distribution | Not tracked |
| Reviews, Customer Complaints | Not tracked — no real review-scraping infrastructure exists |
| Strengths, Weaknesses | Real where directly researched (e.g. the EU AI Act Toolkit's real regulatory-timeline moat vs. competitors' vague/stale language) |
| Market Position | `competitor_discovery.py::compute_threat_assessment()` — real |
| Switching Difficulty | Real via `competitive_moat_engine.py`'s 12 named mechanisms (Phase 17) |
| Potential Moat | See `PRODUCT_MOAT_ENGINE.md` |

## Never fabricates competitor information

Confirmed by direct inspection of `competitor_discovery.py`: every entry cites a real source URL/name from a real HN/GitHub query — no invented competitor has ever been recorded. Unknown fields stay `UNKNOWN`.

---

*See also: `PRODUCT_MOAT_ENGINE.md`, `COMPETITOR_INTELLIGENCE.md`.*

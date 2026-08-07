# OpenClaw / Galaxy Forge — Galaxy Forge × Golden Hunter

**Status:** Permanent, part of the Company DNA (`COMPANY_DNA.md`). "Galaxy Forge becomes the visual brain of Golden Hunter" is a real, buildable ask — unlike Phases 1 and 2, this document describes something genuinely new: `golden_hunter_room.py` (ADR-192), a real panel now live in Mission Control.

---

## What's real, right now

`golden_hunter_room.py::ceo_view()` answers the directive's 4 named CEO View questions directly, computed once from `goos.py::rank_build_candidates()` (ADR-178) — never a new scoring engine, never a second ranking pass:

- **Best opportunity today** — the top-ranked real candidate not marked for rejection.
- **Second best opportunity** — the next one.
- **Which opportunity could become a million-dollar asset** — the real, disclosed heuristic: highest real ROI proxy score among viable candidates. Explicitly, honestly **never a literal dollar projection** — no real pre-acceptance revenue data exists anywhere in this factory to produce one without fabricating it.
- **Which opportunity should be ignored** — every candidate `goos.py` itself already recommends rejecting.

Mission Control: `golden-hunter-room` (`SERVICE_REGISTRY` + a real panel, placed in the Opportunity group), live-verified against the running server.

## The room's 11 named fields, per opportunity

Opportunity / Opportunity Score / Expected Revenue / Market Size / Competition / Difficulty / ROI / Confidence / Priority / Reason / Recommended Next Action — every field either cites a real value from `rank_build_candidates()`'s own output, or is honestly `NOT_MEASURABLE`/`Unknown` (Expected Revenue and Market Size specifically, since no real pre-acceptance dollar or TAM/SAM/SOM data exists — `OPPORTUNITY_SCORING.md`). **Priority** and **Recommended Next Action** are the two genuinely new, mechanical derivations this module adds: Priority from rank position and `reject_recommended`; Next Action from the real `prior_status` (ACCEPTED → proceed to production; DEFERRED → gather new evidence; REJECTED → don't re-litigate without new evidence; flagged for rejection → don't pursue, regardless of status).

## What this round's investigation found, and fixed the honest way

Building this panel required first checking whether the underlying data was current. It wasn't — `golden_opportunities.json` (the older `market_hunter.py`/`profit_oracle.py` pathway) was 16 days stale. Rather than silently building a panel on top of stale data, or worse, quietly "refreshing" the timestamp without new evidence, a real, live hunt cycle was run as part of this work: 13 real candidates scanned, 0 new golden opportunities found — an honest, correct result given an exhausted static seed list, not a bug. `GOLDEN_HUNTER_ENGINE.md` documents this fully; `golden_hunter_room.py` deliberately reads from `goos.py::rank_build_candidates()` instead, which sources from `data/decisions.jsonl` directly (including the real, currently-active daily `ladder_fast_gate` discovery pathway) rather than the stale file.

## What was deliberately not built

- **A visual world map, network graph, or Bloomberg-terminal-style live feed of the hunt itself** — real UI investment beyond a data panel, not attempted this round given the same commercial-priority discipline this whole directive series has applied throughout (`INTEGRITY_RULES.md`).
- **New discovery connectors** (Google Trends, Reddit, Product Hunt) — named as a real, disclosed gap in `GOLDEN_HUNTER_ENGINE.md`, not silently built as a side effect of a panel.
- **A refreshed seed candidate list** — the real, root fix for Golden Hunter's actual current constraint (`GOLDEN_HUNTER_ENGINE.md`'s own finding). Real, valuable, and explicitly out of scope for a "make the CEO view work" round — flagged as the next real candidate for founder attention, not quietly done in passing.

---

*See also: `GOLDEN_HUNTER_ENGINE.md`, `OPPORTUNITY_PIPELINE.md`, `OPPORTUNITY_SCORING.md`, `EXECUTIVE_OPPORTUNITY_BRIEF.md`.*

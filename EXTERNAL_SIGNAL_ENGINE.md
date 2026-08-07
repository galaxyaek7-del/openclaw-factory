# Galaxy Forge — External Signal Engine

**Date:** 2026-08-08 | Phase 17, Sections 2-3. Real citation over `multi_source_intelligence/types.py::ConnectorResult` — not rebuilt.

---

## The 13 named signal fields, mapped

| Requested field | Real equivalent |
|---|---|
| Signal ID | Not a distinct field on `ConnectorResult` — each real signal is identified by `(source, timestamp)`, sufficient for this factory's real query volume; a dedicated UUID field was not added, per "do not add intelligence for the sake of having more intelligence" |
| Source | `ConnectorResult.source` — real |
| Timestamp | `ConnectorResult.timestamp` — real |
| Category | Implicit in which connector produced it (e.g. `hacker_news`, `arxiv`) — no separate taxonomy field |
| Market/Entity | Carried in `raw_data`/`parsed_data`, not a normalized top-level field |
| Observation | `parsed_data` |
| Evidence | `raw_data` (verbatim, never reshaped) |
| Source URL | Present in `raw_data` where the connector's own API returns one |
| Confidence | `ConnectorResult.confidence` — real (0/low/medium/high scale) |
| Importance / Potential Impact | Not computed at the connector level — this is `goos.py`/`capital_allocation_engine.py`'s job once a signal is used in a real evaluation, deliberately not duplicated here |
| Status | `ConnectorResult.verification_status` — real (`VERIFIED`/`UNKNOWN`/`BLOCKED`/`NOT_ARCHITECTED`) |

## Section 3 — Source quality classification

`multi_source_intelligence/types.py::EVIDENCE_SOURCE_PRIORITY` already real-ranks 10 named source tiers (ADR-179's "Real Evidence Provider" work) — a genuine, if differently-labeled, match for the directive's PRIMARY/OFFICIAL/HIGH QUALITY SECONDARY/COMMUNITY/SOCIAL/UNVERIFIED taxonomy. No second, competing taxonomy was built. **Real, disclosed rule already enforced**: `prioritized_evidence_summary()`'s own `confidence` computation averages only `VERIFIED` sources — a `BLOCKED`/`NOT_ARCHITECTED` source can only ever fail to raise confidence, never lower it below what real verified evidence already earned. Social/community signals never automatically become business facts — this is the same discipline `profit_oracle.py`'s Proof of Payment gate already enforces at the point of use.

## Never treating an unverified signal as fact

Confirmed, company-wide, via `truth_first.py`'s canonical vocabulary and re-verified this round via `anti_bias_check.py` (Phase 16) — any recommendation built from thin/unverified evidence is now mechanically flagged, not just a documentation promise.

---

*See also: `AI_CAPABILITY_OBSERVATORY.md`, `INTELLIGENCE_KNOWLEDGE_GRAPH.md`.*

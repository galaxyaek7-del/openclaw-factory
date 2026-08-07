# Galaxy Forge — Knowledge Lifecycle

**Date:** 2026-08-08 | Phase 18, Sections 13-14, 17. The 7 named lifecycle states and the "have we seen this before?" reuse questions.

---

## Section 17 — The 7 named states, mapped

| Requested | Real equivalent | Evidence |
|---|---|---|
| DISCOVERED | `multi_source_intelligence`'s raw connector output | Real |
| UNVERIFIED | `truth_first.py`'s `UNKNOWN`/`NOT_ARCHITECTED` | Real |
| SUPPORTED | `Decision` records with 2+ real agreeing signals | Real |
| VERIFIED | `multi_source_intelligence`'s `VERIFIED` | Real |
| OUTDATED | **New this round** — `knowledge_decay.py::check_staleness()` | Real |
| CONTRADICTED | **New this round** — `contradiction_engine.py` | Real |
| ARCHIVED | `data/decisions.jsonl`'s own append-only history — a real, superseded record is never deleted, only followed by a newer real record | Real |

**"Never delete important historical knowledge merely because it became outdated"**: already this factory's strongest architectural guarantee — every real ledger (`decisions.jsonl`, `sales_ledger.jsonl`, `evidence_ledger.jsonl`) is append-only by construction; no code path in this factory deletes a historical record (confirmed by direct search across every `channels/ledger.py`-pattern module this session built).

## Sections 13-14 — Golden Hunter Memory / Knowledge reuse

`goos.py::_duplicates_existing_family()` already implements exactly Section 13's ask for one specific case (does a candidate niche duplicate an already-ACCEPTED product family) — real, cited, not duplicated. The broader ask ("check whether we've researched this market/competitor/platform/technology before, across all 7 named categories, before ranking a new opportunity") is **honestly partial**: real historical data exists for markets (`data/decisions.jsonl`, 91 real evaluated niches) and competitors (`data/competitor_database.json`, 57 real niches) — a candidate opportunity evaluation does NOT currently cross-check either before scoring, a real, disclosed gap.

**The 7 named reuse questions, real answers**:
- "Have we seen this before?" — `data/decisions.jsonl` (real, queryable, 2,056 records)
- "What happened last time?" — `decision_engine/feedback.py::sync_outcomes()` (real, never yet exercised)
- "What did we learn?" — `OpenClaw_Brain/19_Lessons_Learned/` (7 real files)
- "Which assumptions were wrong?" — `contradiction_engine.py` (new this round, 19 real findings)
- "Which products solved similar problems?" — `product_master_catalog.py` + `Niche` graph traversal
- "Which markets failed?" — `data/decisions.jsonl`'s real REJECTED records (94 of 2,056)
- "Which platforms performed well?" — `PLATFORM_INTELLIGENCE.md` (Phase 16) — honestly, none has real revenue data yet

---

*See also: `KNOWLEDGE_GRAPH_ARCHITECTURE.md`, `GOLDEN_HUNTER_LEARNING_LOOP.md` (Phase 17).*

# OpenClaw / Galaxy Forge — Executive Memory

**Status:** Permanent, part of the Company DNA (`COMPANY_DNA.md`). "Never forget why decisions were made" is checked here against 5 real, already-existing, permanent record systems — not a new memory store, which would fragment the real memory this company already has rather than protect it.

---

## The 5 requested memory types, mapped to real ledgers

| Requested | Real, permanent record |
|---|---|
| Major decisions | `data/decisions.jsonl` (every real opportunity evaluation, `decision_engine/`) + `data/executive_directives.jsonl` (every real Executive Brain arbitration) |
| Rejected decisions | `data/decisions.jsonl`'s real REJECTED/DEFERRED entries + `QUARANTINE.md`'s 3,300+ real product rejections, each with its real reason attached |
| Lessons learned | `OpenClaw_Brain/19_Lessons_Learned/` — real incident write-ups (mistake → consequence → how it was found → fix → generalizable lesson), picked up automatically by the Knowledge Graph, no code changes needed per lesson |
| Strategic pivots | `data/executive_directives.jsonl` + the ADR log itself (`OpenClaw_Brain/00_Governance/`) — every real strategic redirection in this company's history is a numbered, dated, permanent record |
| Commercial outcomes | `data/decision_outcomes.jsonl` (`decision_engine/feedback.py::sync_outcomes()`) — real sales matched back to the decisions that predicted them |

## The real join: from decision to outcome to lesson

Memory that only records decisions, never what happened after, is not real memory. `knowledge_graph/build.py` adds a real `Outcome` node with a `resulted_in` edge back to its `Decision` node, mechanically joined by `decision_id` — only for a real matched outcome, never backfilled or guessed. This is the literal mechanism by which "the Executive Brain must never forget why decisions were made" is enforced: the *why* (`reasoning`, `evaluation_snapshot`), the *what happened* (`Outcome`), and the *what it taught* (`Lesson`, when one was written) are three real, linked nodes in one graph — 4,308 real nodes and 4,116 real edges as of the most recent snapshot, queryable directly (`global_search.py`, ADR-185).

## Real duplicate-prevention

`executive_brain.py::_detect_repeat()` (ADR-145) tags an identical recommendation, recommended again, as `is_repeat_of` the prior `decision_id` — still recorded, since the underlying alert may genuinely still be active, but never silently treated as new. This is memory actively preventing this company from re-deciding the same thing twice without noticing.

## Real conflict detection

`executive_decision_memory.py::detect_niche_conflict()` / `detect_ledger_conflicts()` (ADR-145) are real, mechanical, keyword-based checks — the same discipline `evolution_queue.py`'s `SENSITIVE_AREA_KEYWORDS` already established — never semantic/AI judgment pretending to be more certain than a keyword match actually is.

## What this document does not do

It does not create a second decision ledger, a second outcome tracker, or a second lessons-learned folder. Every real record cited above already existed before this document was written; this document's only job is naming them as the answer to "Executive Memory" so the next person (or the next AI session) doesn't wonder whether a 6th system needs to be built to satisfy this directive.

---

*See also: `EXECUTIVE_BRAIN.md`, `DECISION_PROTOCOL.md`, `SELF_REVIEW_PROTOCOL.md`.*

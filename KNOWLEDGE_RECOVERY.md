# Galaxy Forge — Knowledge Recovery

**Date:** 2026-08-08 | Phase 18, Section 26. Real citation over `BACKUP_AND_RESTORE.md` (Phase 14) — the Knowledge Graph's real source files (`data/decisions.jsonl`, `data/market_evidence.jsonl`) are already part of that real, tested backup system.

---

## Real, tested backup coverage

`recovery/snapshot.py::DEFAULT_SNAPSHOT_TARGETS` already includes `data/decisions.jsonl` and `data/market_evidence.jsonl` — 2 of the Knowledge Graph's primary real source files. `BACKUP_AND_RESTORE.md` (Phase 14) already proved this round's real restore test: a real `.bak` snapshot of `decisions.jsonl` was restored to an isolated path and validated — **2,030 real lines, 0 malformed.**

## What is NOT separately backed up

`data/competitor_database.json` (this round's new Competitor node source) and `data/knowledge_graph_snapshot.json` (the derived, disposable graph cache itself) are **not** in `DEFAULT_SNAPSHOT_TARGETS`. The graph snapshot is explicitly disposable by design (`knowledge_graph/build.py`'s own docstring: "DERIVED, DISPOSABLE snapshot... rebuild any time") — losing it costs nothing beyond a real rebuild (`build_graph()`, a fast, deterministic function over the real source files). `competitor_database.json` is a real, disclosed gap — not yet in the snapshot list, a small, safe follow-up.

## Per the directive's own rule: "knowledge loss must be treated as an enterprise incident"

**Recommendation, not built this round**: add `data/competitor_database.json` to `DEFAULT_SNAPSHOT_TARGETS`. A one-line, safe, additive change — deliberately deferred to keep this round's real, riskier work (the Knowledge Graph extension, Contradiction Engine, Knowledge Decay) as the focus, rather than touching `recovery/snapshot.py`'s own tested, real, already-in-production list inside an already-large round.

---

*See also: `BACKUP_AND_RESTORE.md` (Phase 14), `KNOWLEDGE_GRAPH_ARCHITECTURE.md`.*

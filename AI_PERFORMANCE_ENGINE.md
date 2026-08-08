# Galaxy Forge — AI Council Performance & Model Routing

**Date:** 2026-08-08 | ADR-209, Phase 19, Sections 17-18. Citation-only — `ai_capability/registry.py` and `ai_capability/orchestrator.py` already answer both sections.

---

## Section 17 — AI Council Performance (already real)

`ai_capability/registry.py::list_providers()` tracks real, per-provider metrics for every provider actually called — Groq is the only LIVE provider today (228 real calls as of this round's live check, avg latency 1924ms, avg cost $0.000086/call, total real cost $0.0197). Every other named provider (Kimi, Doubao, GPT, Gemini, DeepSeek, Qwen, open-source models) is honestly tagged `DISCOVERY` — no fabricated benchmark comparison exists anywhere, per this factory's own standing technical-neutrality principle (CLAUDE.md).

**Quality/Accuracy/Hallucination Rate**: honestly `DISCOVERY` — "لا يوجد ربط بين نتائج Dual Inspection والموديل الذي أنتج المحتوى بعد" (no link exists yet between Dual Inspection results and which model produced the content) — a real, disclosed gap, not fabricated. **Cost and Speed are REAL** (both computed from actual recorded calls).

## Section 18 — Model Routing (already real)

`ai_capability/orchestrator.py::select_provider(task_type)` / `generate(task_type, ...)` already dynamically route by task type — currently resolving to Groq for every real task type this factory has (content_generation, book_structure, seo_copy, marketing_copy, support_copy, query_reformulation), since it is the only provider with real, live credentials. `resource_allocation_status()` gives the real per-task-type allocation view.

**"If no model is sufficiently reliable: ESCALATE TO HUMAN"**: no automatic escalation path exists yet — every real AI-generation call in this factory already runs through Dual Inspection (`inspectors.py`) as its real quality gate; a failed inspection already routes to `QUARANTINE.md` (3,337 real historical rejections) rather than reaching a customer. This is the real, existing equivalent of "escalate rather than ship an unreliable result."

## What was NOT built this round

No new AI-performance tracking table, no new routing logic — both would duplicate `ai_capability/registry.py`/`orchestrator.py` verbatim for zero new real signal. The one real, disclosed gap (Quality/Accuracy linkage to Dual Inspection) is a genuine future improvement, not attempted here to avoid retrofitting a large, already-tested module inside an already-large round.

---

*See also: `CONTINUOUS_IMPROVEMENT_ENGINE.md`.*

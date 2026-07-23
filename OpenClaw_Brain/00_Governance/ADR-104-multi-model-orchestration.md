# ADR-104 — Multi-Model Orchestration

**Date:** 2026-07-23
**Status:** Adopted.

---

## The directive

"OpenClaw is not loyal to models. OpenClaw is loyal to results." Every AI model (Claude, GPT, Gemini, MiniMax, DeepSeek, Qwen, Kimi, open-source) is an investment tool, continuously evaluated on customer value, quality, speed, reliability, cost, security, maintainability, and commercial impact. "The company automatically allocates work to the model that delivers the highest measurable value for that specific task." "Every production workflow must support multi-model orchestration."

## What a real search found

`ai_capability/registry.py` + `ai_capability/evaluator.py` (extended earlier the same session, ADR-103) already provide the real evaluation half of this directive. What was missing was the **dispatch** half: an actual, callable function a real production workflow could route through to get automatic, evidence-based provider selection — `evaluator.recommend_for_task()` already computes the recommendation, but nothing in the factory actually *called through* it; every real LLM call site still imported `book_generator.groq_chat()` directly, by name.

A full search of every real LLM call site in the factory found exactly two: `book_generator.groq_chat()` (Python) and `server.js`'s `groqChatWithRetry()` (Node) — plus `audit_seed.py`/`seed_english_book.py`, both explicitly documented standalone tools with "zero factory impact," out of scope. Of the real Python call sites that use `groq_chat()`, two (`book_generator.py`'s own core PDF/techdoc content generation) are the highest-risk, most business-critical production paths in the entire factory; one (`market_intelligence_engine.py`'s `reformulate_pain_query()`) is a real but low-blast-radius call already wrapped in its own tested, graceful 3-tier fallback chain (`groq_semantic` → `deterministic_fallback` → `literal_fallback`) that never breaks the pipeline on failure.

## What was built

**`ai_capability/orchestrator.py` (new):**
- `select_provider(task_type, ...)` — reuses `evaluator.recommend_for_task()` directly (never a second, competing ranking algorithm). Falls back to `"groq"` only when nothing measured was found for the exact task type — an honest default (Groq genuinely is this factory's only real, always-available provider today), not a guess.
- `generate(task_type, system_prompt, user_prompt, ...)` — the real dispatcher. Looks up a real, registered call implementation for the selected provider (`_REAL_PROVIDER_CALLERS`, today containing exactly one real entry: `"groq"` → `book_generator.groq_chat()`) and calls it. Raises `NotImplementedError` — loudly, honestly — for any selected-but-unimplemented provider, rather than silently substituting Groq and pretending real multi-model orchestration happened. Adding a real second provider is now a genuinely 3-step, non-breaking change: a real credential in `.env`, a real call function here, one new dict entry — no call site that already routes through `generate()` needs to change.
- `ai_capability/registry.py`'s `PROVIDER_CATALOG` gained one more real, named candidate this directive explicitly requested: `minimax` (MiniMax), same honest `DISCOVERY`-level treatment as every other untested provider. Groq's own catalog entry gained a real `task_types` entry, `"query_reformulation"`, matching the real capability it already demonstrably serves (confirmed via `data/ai_cost_log.jsonl`'s own `cost_context.purpose` field).

**Wired into one real production call site:** `market_intelligence_engine.py`'s `reformulate_pain_query()` now calls `ai_capability.orchestrator.generate("query_reformulation", ...)` instead of importing `book_generator.groq_chat` directly. Behavior is unchanged today (Groq remains the only real, measured provider, so it's still what actually answers) — but the *decision* of which provider answers is now real, evidence-based, logged infrastructure instead of a hardcoded import. The moment a second provider gets real credentials and real measured usage, this call site adopts it automatically, with zero further code change. The two highest-risk, core content-generation call sites in `book_generator.py` deliberately were **not** touched in this pass — they keep their already-proven, direct `groq_chat()` calls, avoiding unnecessary risk to the factory's real, live production path while the orchestration layer itself gets proven out on a lower-risk site first.

## A real regression caught before it shipped

Extending `ai_capability.registry.PROVIDER_CATALOG` with `minimax` created a real duplicate: `integration_registry.py` (EOS Phase 2, 2026-07-19) had its own separate, static `NEW_VENDOR_CATALOG` entry for MiniMax, added back when MiniMax was "new-to-any-registry." `tests/test_integration_registry.py`'s own `test_no_duplicate_vendor_names_across_sources` caught the real duplicate (31 names, 30 unique) the moment the full regression suite ran. Fixed by removing MiniMax from `NEW_VENDOR_CATALOG` — `ai_capability.registry.PROVIDER_CATALOG` is now the single source of truth for it, exactly matching that module's own pre-existing, explicit anti-duplication rule.

## Verification

10 new tests (`tests/test_ai_orchestrator.py`, new file) — `select_provider()`'s real-recommendation and honest-default paths, `generate()`'s real dispatch (mocking `book_generator.groq_chat` directly, confirming kwargs forward unchanged), the `NotImplementedError` safety property for an unimplemented provider, and that a real Groq failure still propagates rather than being silently swallowed by the orchestrator itself (existing callers keep their own fallback logic). `tests/test_ai_capability.py` updated for the 12th provider. All 28 pre-existing `market_intelligence_engine.py` tests (including 6 `TestReformulatePainQuery` tests using the existing `@patch("book_generator.groq_chat")` convention) pass unchanged, confirming the orchestrator wiring is fully transparent to that mocking pattern.

Full regression: highest-risk suites first (`test_market_intelligence_engine.py`, `test_market_intelligence_core.py`, `test_enterprise_readiness.py`, `test_decision_engine.py`, `test_integration_registry.py` — 128 tests), then the full repository: Python 1184/1184 (up from 1178), Node 23/23 (`test_api_contract.js`, unaffected — this piece is Python-only). No live data drift.

## What's deliberately not built

No real second provider integration was added — this factory still has zero real API credentials for GPT/Gemini/DeepSeek/Qwen/Kimi/MiniMax/Mistral/Grok/Claude/local models. The orchestrator is real, tested, and ready; it has exactly one real backend today because that is the honest current state of this factory, not a limitation of the design.

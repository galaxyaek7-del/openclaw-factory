# MASTER_CHARTER.md — OpenClaw Factory

**Date:** 2026-07-17
**Status:** Adopted (`ADR-065`).
**Supersedes, for prioritization purposes only:** `CLAUDE.md`'s six-track table and `PRODUCT_VISION.md`'s implicit "books first" ordering. Does not replace either document — both remain the source of truth for architecture and product vision; this charter only reorders *what gets built next*.

---

## 1. Why this exists now

On 2026-07-17 the founder directed a full strategic pivot away from "books are the active track, everything else waits for the first book dollar" toward a new priority ladder (§2). This is the same class of decision as `ADR-034`'s trigger-gated freeze on institutional ceremony — and it is being handled the same way that decision itself documents: not silent compliance, not refusal. The conflict was raised once, plainly (freeze not yet objectively triggered; KDP marked "active now" in `CLAUDE.md`), the founder confirmed explicitly he was firing the trigger himself, and `ADR-065` records that as the trigger event. See `ADR-065` for the full record of that exchange.

**What did not change:** the three-layer architecture (Core/Engines/Channels, `OCTOPUS_ARCHITECTURE.md`), the six governing principles (`PRINCIPAL_ARCHITECT_CHARTER.md` §2 — wrap don't rewrite, contract before implementation, open/closed, fail-safe on missing secrets, `dry_run` always-on by default, full memory), the Protected Right to Object, the single-Google-account identity constraint (`IDENTITY_ARCHITECTURE.md`), and the "no scheduler" design. This charter is a reprioritization of product lines, not an architecture rewrite.

## 2. Strategic Production Priority Ladder

Ranked by what gets engineering attention and what a new opportunity is scored against first:

| Rank | Track | Why it outranks what's below it |
|---|---|---|
| 1 | **AI SaaS** | Recurring revenue, near-zero marginal cost per additional customer, fully reusable across niches once built |
| 2 | **B2B Systems** | Recurring or high-ticket, reusable core with per-client configuration, professional buyers with real budgets |
| 3 | **Automation Tools** | One-time or subscription tooling, high reusability, sellable to both consumers and businesses |
| 4 | **Reusable Assets** | Build-once-sell-many (templates, packaged systems), no recurring revenue but strong reusability |
| 5 | **Educational** | Real value, but lower reusability per unit of effort than 1–4 (courses/guides are closer to one-off content) |
| 6 | **KDP Books** | Last, supporting only — kept running because it is the only track with proven live infrastructure (`book_generator.py`, KDP channel) and non-zero real production evidence (4 products passed Dual Inspection, `books/`), but no longer the track new engineering effort defaults to |

**Scoring consequence:** `profit_oracle.py`'s opportunity gate (`ADR-026`, extended by `ADR-065`/Step 2 of this mission) now weights recurring revenue and reusability as the two highest-weighted factors, and rejects any opportunity below a **$97 profit floor** regardless of tier. See `ADR-065` §3 for the exact formula change.

## 3. What this ladder does *not* mean

- It does not mean KDP book production stops. `book_generator.py`, the KDP channel, and the 4 already-QA'd products remain live and supported — "last/supporting" is a priority-of-new-effort ranking, not a shutdown order.
- It does not mean `gumroad_arm.py` is deleted. It is archived (moved, not removed — see Step 4 record) because Gumroad was never activated live (`GUMROAD_ACCESS_TOKEN` was always the missing piece per `CLOSING_NOTE.md`), and Paddle better fits tracks 1–3 (subscriptions, license keys, B2B invoicing) than a one-time-download marketplace does.
- It does not reopen the rest of `ADR-034`'s freeze. Named departments, KPI agents, a 9-gate review process, and a 15-domain "executive" dashboard are still gated behind their own triggers (first sale / live API key / real Tier-1 candidate) — this charter fires the freeze *only* for the specific ceremony it names (a charter, a blueprint, a re-ranked ladder, one ADR), not for the rest of `PHASE_4_EXECUTIVE_STRUCTURE.md`.

## 4. Standing principles (unchanged, restated for this charter's scope)

1. **Wrap, don't rewrite.** New tracks (SaaS, B2B, automation) get new engines beside `book_engine`, not a rewrite of it.
2. **Contract before implementation.** Any new engine follows `book_engine`'s existing interface shape before its first line of product-specific code, per `CLAUDE.md`'s "كل محرك جديد يجب أن يتبع نفس واجهة `book_engine` الموجود". As of 2026-07-19, the Universal Production Engine's Product Definition Registry (`UNIVERSAL_PRODUCTION_ENGINE.md`) is the concrete mechanism for this principle: a new track that reuses existing generators needs one `ProductManifest` (configuration), not a new engine — and the same "don't expand before proving the current pattern insufficient" discipline this charter's §1 already established was applied when scoping that registry itself (a lighter, Python-object manifest was built instead of a full file-based loader/DI framework, since only one family existed to prove the need for either). The same day, the Commercial Execution Layer (`COMMERCIAL_EXECUTION.md`) applied the identical discipline to publishing: `channels/registry.py`, `distributor.py`, and `channels/ledger.py` were already the real Marketplace Registry/fan-out/audit-ledger — Step 4 unified and manifest-integrated them rather than building a second, parallel publishing system.
3. **No product line launches ahead of the ladder's own discipline:** no new track gets a dedicated engine built out fully before the ladder's own opportunity gate (§2) has actually accepted a real candidate for it. Building `paddle_arm.py`'s skeleton now is preparation, not a claim that a Paddle-sold product exists yet.
4. **Full memory.** Every opportunity, decision, and rejection stays logged (`data/decisions.jsonl`, `data/golden_hunter_events.jsonl`) — the ladder changes what wins, not whether losses are recorded honestly.
5. **Protected Right to Object stays in force**, including against this charter itself, if a future session finds the ladder producing bad outcomes.
6. **One real decision per opportunity, never re-derived.** As of the Strategic Phase (2026-07-19, `COMPANY_INTEGRATION_MAP.md`), the modern pipeline (`orchestrator.run_cycle()`) can be triggered automatically from `factory_loop.js`'s existing tick — but only by *reusing* a decision Golden Hunter already recorded (`existing_decision=`), never by re-evaluating the same niche a second time. This is what makes automatic triggering safe: a second independent decision for the same real opportunity would mean a second `production_id` and real duplicate-publishing risk. Still gated by the same `FACTORY_AUTO_PRODUCE` review process `AUTO_PRODUCE_ACTIVATION_CHECKLIST.md` already documents — no new switch, no new review process.

## 5. Ownership

Same as `PRINCIPAL_ARCHITECT_CHARTER.md` §6 — founder holds final decision authority; this charter is an operating agreement, not a self-executing policy engine.

## 6. Autonomous Digital Company v1 note (2026-07-19)

Does not change the ladder (§2) or fire any new trigger — this milestone (`COMPANY_INTEGRATION_MAP.md`'s own dedicated section) is internal tooling: real executive/infrastructure/AI-capability/tool-integration intelligence surfaced in Mission Control. Worth recording here because it extends this charter's "never fabricate" discipline (already governing §2's opportunity gate) into a new domain: `ai_capability/`'s provider registry compares AI systems on real, measured metrics only — Groq is the one provider with real usage data; every other named provider (Claude, GPT, Gemini, Grok, DeepSeek, Qwen, Mistral, local models) stays honestly unmeasured until a real credential exists and is actually called. Same standard as this charter's own §2 scoring — no invented number substitutes for missing real evidence.

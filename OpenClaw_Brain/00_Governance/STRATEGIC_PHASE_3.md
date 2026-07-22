# STRATEGIC_PHASE_3.md — OpenClaw Factory

**Date:** 2026-07-22
**Status:** Adopted.
**Supersedes, for prioritization purposes only:** nothing — this sharpens `MASTER_CHARTER.md`'s existing ladder and `ELITE_ASSET_DOCTRINE.md`'s existing central doctrine, it does not replace either.

---

## 1. Why this exists

The founder declared the company has entered a new phase: infrastructure-building is over ("the infrastructure now exists"); the primary mission from here is discovering/creating rare, high-value, hard-to-copy digital businesses, not producing volume. Five named priorities, in order: **Opportunity Intelligence Engine, Golden Hunter Evolution, Product Laboratory, Market Validation, Continuous Evolution.** Standing filter for every future module: *"Will this increase the probability of discovering or creating a high-value business?"*

**An honest note worth recording plainly, not silently:** this philosophy is not new to this factory. `ELITE_ASSET_DOCTRINE.md` (2026-07-13) already declared, verbatim, the identical central doctrine — *"Revenue ÷ Time, not Products ÷ Time... fewer assets, better, higher value... never optimize for quantity"* — enforced numerically since that date via `profit_oracle.py`'s `MIN_OPPORTUNITY_SCORE=65` gate. `MASTER_CHARTER.md`/`ADR-065` (2026-07-17) already ranks AI SaaS > B2B Systems > Automation Tools > Reusable Assets > Educational > KDP Books with a $97 profit floor. Strategic Phase 3 doesn't introduce this — it sharpens the priority ordering into 5 concrete, actionable engineering areas and gives them a durable, one-question test. Books/KDP are further and explicitly demoted here to "supporting business units only," the clearest statement yet of what `MASTER_CHARTER.md`'s ladder already implied.

## 2. The 5 named priorities

1. **Opportunity Intelligence Engine** — continuous global market search: industries, companies, startups, Reddit, GitHub, Product Hunt, research papers, developer communities, enterprise requests, emerging technologies.
2. **Golden Hunter Evolution** — score opportunities on urgency, competition, pricing power, willingness to pay, scalability, technical feasibility, recurring revenue potential, defensibility, long-term strategic value.
3. **Product Laboratory** — auto-generate product concepts, compare alternatives, estimate ROI/dev cost, prioritize only exceptional opportunities.
4. **Market Validation** — never trust assumptions; require multiple independent evidence signals before production.
5. **Continuous Evolution** — every successful product becomes a living asset that improves permanently via customer feedback, AI analysis, and commercial performance.

**Product types are not limited to digital downloads** (2026-07-22 addendum): AI platforms, SaaS, enterprise tools, professional automation, commercial datasets, research intelligence, decision systems, knowledge systems, industry operating systems, APIs, digital assets, subscription businesses are all in scope whenever a real opportunity calls for one — the ladder's `ai_saas`/`b2b_systems`/`automation_tools` ranks already anticipate this, though no real adapter exists yet for anything beyond a PDF/document artifact (`ADR-083`'s Track C, unchanged).

## 3. What already existed before this phase (don't rebuild)

Real, code-level research (three parallel passes, 2026-07-22) found much of priority #1 already substantially built: `multi_source_intelligence/` (`ADR-059`, 2026-07-16) is a 10-connector package (now 11 with `arxiv`, this round) covering almost the exact named source list — real for Hacker News/GitHub/Stack Overflow/arXiv, honestly blocked for Reddit ($12,000/mo commercial API — a hard financial wall), Product Hunt (ToS requires prior business contact), Google Trends (needs n8n activation). `competitor_discovery.py` (`ADR-042`) already does real HN+GitHub competitor discovery with 5-category classification and a 7-day cache. `profit_oracle.py`'s scoring already carries real fields for 3 of Golden Hunter Evolution's 9 named dimensions (competition, recurring revenue potential, long-term strategic value) and partial proxies for 3 more (pricing power, scalability, technical feasibility) — see `ADR-083` for the full per-dimension map. None of this was rebuilt this round.

## 4. Standing principles (unchanged, restated for this phase's scope)

1. **Fewer, better, higher-value products** — `ELITE_ASSET_DOCTRINE.md`'s Revenue÷Time equation, unchanged, still the load-bearing filter behind `MIN_OPPORTUNITY_SCORE=65` and the $97 ladder floor.
2. **Never fabricate a signal.** `ADR-039`'s hard-won discipline (founder's own words: *"never create fake metrics"*) governs every new Golden Hunter Evolution dimension: real data or honestly `Unknown`, never a plausible-looking invented number.
3. **Live-network cost stays out of the automatic hot path.** Every existing research module that touches a real external API (`competitor_discovery.py`, `multi_source_intelligence/`) was deliberately kept independent of `profit_oracle.py`'s synchronous scoring and the automatic daily tick, to avoid unbounded live-network latency/cost on autopilot. New Opportunity Intelligence/Market Validation work extends this as founder-triggered, on-demand tooling rather than crossing that boundary.
4. **Informational until proven, never gating.** New ROI/concept-comparison/evidence-gathering tools stay advisory — same discipline `revenue_pipeline/plan.py::estimate_pre_acceptance_roi()` already established — until enough real evidence (first real sales, first real product built) exists to responsibly gate a decision on them.
5. **No infrastructure expansion unless absolutely necessary** (2026-07-22 addendum). The primary objective this phase is maximizing the factory's commercial intelligence, not growing the codebase. If a capability already exists, improve/wire it rather than rebuild it — the same Track A/B/C discipline every round this year already applies, now stated as an explicit standing rule rather than an implicit habit. `ADR-083`'s Round 1 items were each checked against this after the fact: the one genuinely new file (`arxiv.py`) is a single small connector following an established contract, not new infrastructure; everything else was composition over already-real modules.
6. **Optimize for high customer value, high willingness to pay, low competition, recurring revenue, long-term defensibility** (2026-07-22 addendum) — the explicit scoring lens for every opportunity going forward, restating and sharpening `ELITE_ASSET_DOCTRINE.md`'s Revenue÷Time equation and Golden Hunter Evolution's 9 named dimensions (§2 above) into one memorable checklist. **The objective is not to produce more — the objective is to own valuable markets.**
7. **Protected Right to Object stays in force**, including against this document itself, if a future session finds this phase's priorities producing bad outcomes.

## 5. Ownership

Same as `PRINCIPAL_ARCHITECT_CHARTER.md` §6 — founder holds final decision authority; this document is an operating agreement, not a self-executing policy engine.

## 6. Round 1 (2026-07-22)

Full build record in `ADR-083-strategic-phase-3-round-1.md`. Shipped: a real `defensibility` scoring signal (Golden Hunter Evolution), `decision_path` transparency in Mission Control (Market Validation), a real `arxiv` connector (Opportunity Intelligence Engine), a founder-triggered "Go Deep" evidence action (Market Validation), and a real per-ladder product-concept comparison tool (Product Laboratory). Rounds 2/3 (deeper Opportunity Intelligence wiring, real AI SaaS/B2B software adapters, Continuous Evolution's feedback loop) remain a documented, deliberately deferred roadmap — see `ADR-083`'s Track C for exact unblock conditions.

# Company Integration Audit — 2026-07-18

**Phase:** Planning. **No features implemented in this pass** — every claim below is verified against real code/config, not assumed carried over from prior reports (`ENGINEERING_ASSESSMENT_20260718.md`, `ADR-076`).

---

## The 13-stage pipeline, verified stage by stage

| # | Stage | Connected? | Production-ready or prototype? | Automatic or manual? | Blocking issues | Required integrations | Effort |
|---|---|---|---|---|---|---|---|
| 1 | **Market Intelligence** | Yes — feeds Golden Hunter | Mixed. Sensing Engine (n8n → `/api/trends`) is real, proven live once. `multi_source_intelligence/`'s 9 real connectors (Amazon/Etsy/GitHub/Reddit) are real, tested, **zero live caller** (`ENGINEERING_ASSESSMENT_20260718.md` C5). Real signal for the new B2B/SaaS ladder categories is still keyword-heuristic-dominated. | Automatic (Sensing Engine on n8n's own schedule once activated; `market_hunter.py` daily via `factory_loop.js`) | 2 Sensing-Engine n8n workflows (`Openclaw_Sensing_Engine`, `02_Sales_Poll`) still need the founder's one-time UI activation click (`BLOCKERS.md` #1 — separate from the Telegram workflow already activated) | Activate the 2 workflows; wire `multi_source_intelligence` into `market_hunter`'s real-signal path | Small (n8n click) + Medium (wiring) |
| 2 | **Golden Hunter** | Yes → Decision Engine (`ADR-076`) | **Production-ready.** Real, tested, verified live: 5 real ACCEPTED opportunities recorded. | Automatic (daily, `factory_loop.js`) | None critical | None | Done |
| 3 | **Decision Engine** | Yes — single source of truth (`ADR-076`) | **Production-ready.** | Fast path automatic; rich AI-CEO evaluation manual by design (live network calls, deliberately not run on every tick) | None | None | Done |
| 4 | **Mission Control** | Yes — reads the unified store directly, zero code changes needed after `ADR-076` | **Production-ready** for observability | Read side automatic/live; state-changing actions (triggering a full evaluation, starting the production pipeline) are manual by design (human-in-the-loop) | None critical; internal-route auth remains a known, loopback-mitigated gap | None required | Done |
| 5 | **Product Generator** | Yes, wired (`factory_loop.js` → `/generate-book` → `book_generator.py`) | Code is real and tested. **But the automatic trigger has never fired for real** — `FACTORY_AUTO_PRODUCE` is unset in `.env` today (confirmed). Every real product generated so far (this session included) was via direct/manual invocation, never the live autonomous tick. | Automatic *in code*; **effectively off** at the master switch | (a) `FACTORY_AUTO_PRODUCE` unset — real Groq-spend implication, a founder decision, not an engineering gap. (b) **`generate_product_package()`'s default section content is placeholder text**, not real generated content (`ADR-068`'s own honesty note) — turning on automation today would autonomously mass-produce placeholder-content packages | (a) Founder flips the switch. (b) Build real content generation for techdoc sections (no AI content engine exists for this path — `generate_book()`'s Groq engine only serves the old book/journal path) | (a) None (config only) (b) **Medium-Large** — new work, not a flip |
| 6 | **Quality Assurance** | Yes, unconditional (`inspectors.py`) | **Production-ready.** | Automatic | None blocking; zero *direct* unit tests on `inspectors.py` itself (medium risk, not a blocker — flagged in the prior review) | None required to unblock | Done (test coverage is a separate, non-blocking improvement) |
| 7 | **Packaging** | Yes (`generate_product_package()` + `schemas/product.py`) | Real for PDF assembly/Dual-Inspection routing. **Same placeholder-content gap as Stage 5** — same root cause, not a separate problem | Automatic mechanically; ships placeholder content when it fires | Same as Stage 5(b) | Same fix as Stage 5(b) | Shared with Stage 5 |
| 8 | **Paddle** | Yes for product/price creation (`ADR-074`); checkout blocked | Product/price creation real and tested. Checkout/transaction creation blocked by **Paddle's own account-onboarding gate**, confirmed via Paddle's real API error, not a code defect | `distributor.py` would trigger this automatically once QA passes **and** `FACTORY_LIVE_PUBLISH=true` — also unset in `.env` today | (a) Paddle account onboarding incomplete (founder-only, `vendors.paddle.com`). (b) `FACTORY_LIVE_PUBLISH` unset (founder decision) | Founder resolves both | **None** — zero engineering, two founder actions |
| 9 | **Email** | **No.** Confirmed via direct search: zero references to Gmail/SMTP/nodemailer/any mail provider anywhere in this codebase | **Does not exist.** Not a prototype — nothing has been built (`BLOCKERS.md` #1b, unchanged since 2026-07-15) | N/A | Gmail OAuth consent or app-password (founder-only, external credential); no existing n8n email node in this instance to use as a real schema reference | Get the founder's Gmail credential; build a real send-email node (n8n or direct) once it exists — deliberately not hand-built blind before then | Medium (once credential exists) — genuinely 0% started today |
| 10 | **Telegram** | Yes, live, verified twice with real message delivery (`ADR-072`/`073`) | **Production-ready** for the "opportunity accepted" event only. "Product ready" / "sale made" / "errors" are **not wired to Telegram at all** — disclosed gap, `ADR-073` | Automatic | None for what exists | Extend to the other 3 event types if wanted | Small-Medium per additional type (same established pattern) |
| 11 | **Analytics** | Yes (Mission Control dashboard, `lib/metrics.js`, `self_awareness.js`, `reality.py`) | **Production-ready.** | Automatic, real-time, cached | None critical | None | Done |
| 12 | **Finance** | **Partial — a real, live risk.** Sales ARE recorded to `data/sales_ledger.jsonl` (real, tested, `channels/ledger.py`). **Confirmed via direct code inspection: `scripts/poll_sales.py` never touches `finance_data.json`** — the file the founder's actual "total revenue" figure reads from | Ledger side real/tested. Reconciliation into the founder-facing total is **missing entirely** | Ledger writes are automatic every tick; the founder-facing total is not — would silently stay $0 after a real sale until manually reconciled | **The company's first real dollar could land and be invisible in Mission Control** the moment Paddle's checkout unblocks | Build one reconciliation step: ledger entries → `finance_data.json` totals, reusing `channels/ledger.py`'s existing dedup key | **Small** (already flagged Small/High-value by the prior 2026-07-17 audit cycle, still unfixed) |
| 13 | **Knowledge Base** | Yes (`OpenClaw_Brain/`, 76 ADRs, `GROWTH_LOG.md`, unified `decisions.jsonl`) | **Production-ready.** | `self_awareness.js`'s daily assessment is automatic; ADR-writing/architecture documentation is a deliberate human(+AI) process, not self-generating | None critical (`FACTORY_STATUS.md` stale, no ADR index — both known, low priority) | None required | Done |

---

## Dependency Graph — shortest path to full autonomy

```
                     ┌─────────────────────────────────────────────┐
                     │  FOUNDER-ONLY, ZERO ENGINEERING (parallel)   │
                     │  1. Flip FACTORY_AUTO_PRODUCE=true            │
                     │  2. Flip FACTORY_LIVE_PUBLISH=true            │
                     │  3. Complete Paddle account onboarding        │
                     │  4. Activate 2 remaining n8n workflows        │
                     └───────────────────┬───────────────────────────┘
                                         │
                                         ▼
  Market Intelligence → Golden Hunter → Decision Engine → Mission Control
  (all real, tested, automatic once the founder-only items above are done)
                                         │
                                         ▼
                          ┌─────────────────────────────┐
                          │  ENGINEERING GATE (blocking) │
                          │  Real content generation for  │
                          │  Packaging/Product Generator  │
                          │  (placeholder text today)     │
                          └──────────────┬────────────────┘
                                         │
                                         ▼
                    Quality Assurance → Packaging → Paddle
                    (all real; Paddle checkout works once onboarding clears)
                                         │
                                         ▼
                          ┌─────────────────────────────┐
                          │  ENGINEERING GATE (small)     │
                          │  Finance reconciliation:       │
                          │  ledger → finance_data.json     │
                          │  (real sale would else be        │
                          │  invisible to the founder)        │
                          └──────────────┬────────────────┘
                                         │
                                         ▼
                    Analytics → Finance → Knowledge Base
                    (all real, automatic, reporting complete)

  Telegram: already fully live for "opportunity accepted" — parallel, not
  on the critical path.
  Email: 0% built — parallel, not on the critical path to a first sale;
  only matters for a specific notification channel the founder hasn't
  asked to prioritize yet.
```

**The shortest real path to "discovering, building, selling, and reporting with minimal founder intervention" has exactly two engineering gates left** (both named above) plus four founder-only, zero-engineering actions that can happen in parallel with nothing blocking them.

---

## Next highest-impact integration

**Build real content generation for `generate_product_package()`'s technical-docs sections (Stages 5/7).**

Not "flip the two switches" — those cost nothing and the founder can do them any time, in parallel, without waiting on engineering. The one gap that **actively works against** the goal if left alone is this one: turning on `FACTORY_AUTO_PRODUCE` today, as-is, would make the company autonomously mass-produce real PDFs whose content is a placeholder string ("`[Placeholder — {section} content for '{topic}' not yet written...]`") for every ladder-tagged AI SaaS/B2B opportunity it accepts. That is worse than staying dormant — it would consume real Groq/compute cycles and real QA-gate cycles to produce something unsellable, right at the one stage this session's entire ladder pivot was built to finally get right.

Closing this gate is what turns "the pipeline is wired end-to-end" (true today, verified in `ADR-076`) into "the pipeline can be turned on and trusted" (not true yet) — the actual, single highest-leverage next step toward autonomous production.

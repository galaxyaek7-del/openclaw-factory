# PROJECT.md — OpenClaw Factory, Current State

**Last updated:** 2026-07-18. **This is a pointer document, not a duplicate** — it orients a new reader to where the real, living state actually lives, and states the current one-paragraph truth. Don't hand-maintain the details here; update the documents it points to instead.

## What this is

OpenClaw Factory is an AI-first digital-product company: a real, automated pipeline (opportunity discovery → decision → product generation → QA → distribution → revenue tracking → notification) with a human founder overseeing it, not running it by hand. See `CLAUDE.md` for the technical stack and `OpenClaw_Brain/00_Governance/PRINCIPAL_ARCHITECT_CHARTER.md` for how engineering decisions get made here.

## Current priorities (governing document)

`OpenClaw_Brain/00_Governance/MASTER_CHARTER.md` — the Strategic Production Priority Ladder: **AI SaaS > B2B Systems > Automation Tools > Reusable Assets > Educational > KDP Books (last, supporting only)**. Adopted 2026-07-17 (`ADR-065`), a deliberate reversal of the earlier "books first" era — see that ADR for why, and `MASTER_BLUEPRINT.md` for how the ladder maps onto real code.

## The one-paragraph current truth

The automated pipeline fired end-to-end for the first time in this company's history on 2026-07-17/18: a real opportunity was discovered, scored, accepted, produced as a real technical-docs product, quality-checked, and reached a real distribution attempt — with zero manual intervention beyond starting the process. Telegram notifications are live (in Arabic, per the founder's own instruction). A real, approved Paddle account can create real products and prices; the last mile (a working checkout link) is blocked by Paddle's own account-onboarding step, not by this codebase. No real dollar has been earned yet. See `OpenClaw_Brain/00_Governance/ENGINEERING_ASSESSMENT_20260718.md` for the full, current, evidence-based picture — architecture, strengths, and prioritized gaps — and `COMPANY_OPERATING_MODEL.md` / `CAPABILITY_MAP.md` for the mechanics (both carry 2026-07-18 update notes reconciling them with the ladder pivot).

## Where to look for what

| Question | Document |
|---|---|
| What are we prioritizing and why? | `OpenClaw_Brain/00_Governance/MASTER_CHARTER.md` |
| How does the pipeline actually work, file by file? | `OpenClaw_Brain/00_Governance/MASTER_BLUEPRINT.md` |
| What's the current architecture, what's strong, what's broken, in priority order? | `OpenClaw_Brain/00_Governance/ENGINEERING_ASSESSMENT_20260718.md` (this review) |
| How does the company mechanically operate, stage by stage? | `COMPANY_OPERATING_MODEL.md` (+ 2026-07-18 update note) |
| What capabilities exist, what's missing, what's the dependency graph? | `CAPABILITY_MAP.md` (+ 2026-07-18 update note) |
| What's blocked on the founder specifically, right now? | `BLOCKERS.md` |
| Why was a specific technical decision made? | `OpenClaw_Brain/00_Governance/ADR-*.md` (74+ and counting — no index yet, a known small gap) |
| What can I do without asking first? | `OpenClaw_Brain/00_Governance/PRINCIPAL_ARCHITECT_CHARTER.md` §1, §5 (Protected Right to Object) |

## Rule for future sessions maintaining this file

Don't restate detail that already lives in one of the documents above — if you're tempted to write more than a sentence about something, that sentence belongs in the specific document, with a pointer added here if the pointer table above doesn't already cover it. This file's only job is: orient a reader in under two minutes, then send them to the real source.

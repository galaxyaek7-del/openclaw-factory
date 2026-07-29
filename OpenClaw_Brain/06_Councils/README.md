# 06 — Councils

OPENCLAW_OS_CONSTITUTION.md names 12 Councils but doesn't say which code implements which — this file is that mapping, kept honest about what's real vs. aspirational.

| Council | What's actually built | Status |
|---|---|---|
| **Quality** | `inspectors.py` — Technical Inspector + Commercial Auditor (CONSTITUTION.md §17) | ✅ Built |
| **Golden Hunter** | `market_hunter.py` (candidate discovery, Brain-aware) + `profit_oracle.py` (scoring) + Scout's niche-picking in `server.js` | ✅ Built |
| **Engineering** | `server.js`, `book_generator.py`, `factory_loop.js` — the core pipeline | ✅ Built |
| **Knowledge** | This Brain (`OpenClaw_Brain/`) + `knowledge_brain.js` | ✅ Built (today) |
| **Security** | `.env` secrets, guarded imports everywhere, the token-handling protocol (see [11_Security](../11_Security/)) | ✅ Practiced, not a named module |
| **Digital Sanitation** | The circuit breaker's cooldown logic; manual test-artifact cleanup discipline this session | ⚠️ Practiced ad hoc, no dedicated automation |
| **Executive** | The Chairman (Galaxy) directly, via conversation-driven tasks; `self_awareness.js` (Day 08) now gives Galaxy an honest daily verdict to decide from, via `GET /awareness` and `GET /good-morning` | ✅ Human-led, now with a real self-report to read first |
| **Innovation** | No dedicated component | ❌ Not built |
| **Publishing** | `channels/base_arm.py` + `channels/gumroad_arm.py` + `distributor.py`, wired end to end: `factory_loop.js` calls `POST /api/distribute` automatically the moment a book clears Dual Inspection (§17), no human step in the normal path. Every attempt (dry-run or live) is recorded to `data/sales_ledger.jsonl`. Real live pushes still require `GUMROAD_ACCESS_TOKEN` (not present in `.env` yet) + an explicit `FACTORY_LIVE_PUBLISH=true` — dry_run is the default, no exceptions. Only Gumroad is wired; Payhip/Etsy/Redbubble are deliberately not (OCTOPUS_ARCHITECTURE.md ADR-8: prove one arm sells before copying the pattern). | ✅ Built (2026-07-11) |
| **Marketing** | `AGENT_PROMPTS.publisher` generates SEO copy on request, but nothing posts anywhere automatically | ⚠️ Partial (content generation only) |
| **Investment** | No dedicated component | ❌ Not built |
| **Product Lifecycle** | No dedicated component — no book has ever been formally "retired" or archived | ❌ Not built |

## Reading this table

Five Councils (Quality, Golden Hunter, Knowledge, Publishing, and Engineering as the substrate all of them run on) have real, working code. Security and Digital Sanitation are *practiced* — real habits enforced in every task this session — but have no single file to point to. The rest are named in the supreme law but have nothing built for them yet, which is expected: [01_Vision](../01_Vision/)'s Golden Rule says don't build ahead of proven need.

## Not the same as two other rosters (2026-07-29)

This table's 12 Constitution-named Councils are a **third, distinct roster** from two later, code-real bodies — don't confuse them:

- **Executive Board** (`executive_board.py`, Executive Directive, 2026-07-22) — 10 C-suite roles (CEO/CTO/CFO/COO/CPO/Chief Market Intelligence/Chief Risk/Chief Revenue/Chief Customer/Chief Innovation Officer) that vote APPROVE/REJECT/DEFER on one already-evaluated decision.
- **Galaxy Council** (`galaxy_council.py`, ADR-138, 2026-07-29) — 10 named members (Strategic/Market/Production/Customer/Financial/Security/Resilience/Innovation Intelligence, Executive Memory, Mission Control) that each state what they currently believe about a niche, side by side, honest disagreement never hidden.

None of the three rosters share membership. This is deliberate, not an oversight — see ADR-138 for the reasoning.

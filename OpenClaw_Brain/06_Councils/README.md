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
| **Executive** | The Chairman (Galaxy) directly, via conversation-driven tasks | ✅ De facto — no software component, doesn't need one |
| **Innovation** | No dedicated component | ❌ Not built |
| **Publishing** | No automated KDP/Etsy upload — see [13_Publishing](../13_Publishing/) | ❌ Not built |
| **Marketing** | `AGENT_PROMPTS.publisher` generates SEO copy on request, but nothing posts anywhere automatically | ⚠️ Partial (content generation only) |
| **Investment** | No dedicated component | ❌ Not built |
| **Product Lifecycle** | No dedicated component — no book has ever been formally "retired" or archived | ❌ Not built |

## Reading this table

Four Councils (Quality, Golden Hunter, Knowledge, and Engineering as the substrate all of them run on) have real, working code. Security and Digital Sanitation are *practiced* — real habits enforced in every task this session — but have no single file to point to. The rest are named in the supreme law but have nothing built for them yet, which is expected: [01_Vision](../01_Vision/)'s Golden Rule says don't build ahead of proven need.

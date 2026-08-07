# Galaxy Forge — AI Capability Observatory

**Date:** 2026-08-08 | Phase 17, Sections 10-12. `ai_capability/registry.py` already IS this observatory (named almost identically) — live-verified this round, not rebuilt.

---

## Real, live registry state (captured this round)

**12 real providers registered.** 1 has real, measured usage:

| Provider | Configured | Real calls | Avg latency | Avg cost/call | Quality | Availability |
|---|---|---|---|---|---|---|
| Groq (Llama 3.1 8B Instant) | Yes (real key) | **228 real calls** | **1,924ms** (real, measured) | **$0.000086** (real, measured) | `DISCOVERY` — no real link between Dual Inspection results and the generating model exists yet | `DISCOVERY` — only successful calls are logged, no real failure-rate tracking |
| 11 other providers | No | 0 | — | — | `DISCOVERY` | `DISCOVERY` |

**Real, disclosed limitation, unchanged since this registry was built**: every non-Groq provider stays `DISCOVERY` until a real credential and a real call exist — never a fabricated comparison. Section 11's own rule ("never assume a model capability without testing") is already this registry's founding discipline (ADR-040).

## Section 12 — AI Council Optimization

**Currently trivial, honestly**: with only 1 of 12 providers real-callable, "selecting the best available model for each task" has exactly one real candidate today. The real selection logic exists (`ai_capability/orchestrator.py::generate()`, task-type routing) and is technology-neutral by design (`CLAUDE.md`'s own stated principle: "no loyalty to any AI model or company") — it is simply unexercised across providers because only one is real. Never selects a model merely because it's newest; selects because it's the only real, evidenced option.

---

*See also: `EXTERNAL_SIGNAL_ENGINE.md`, `GLOBAL_INTELLIGENCE_ENGINE.md`.*

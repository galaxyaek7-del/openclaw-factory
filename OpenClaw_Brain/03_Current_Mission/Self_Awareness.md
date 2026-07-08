# Self-Awareness Engine (Day 08)

Per CONSTITUTION.md §20 and OPENCLAW_OS_CONSTITUTION.md's North Star ("the factory must become smarter every single day. Know more than yesterday.") — the factory had cells (Scout, `profit_oracle`, `market_hunter`, `inspectors`, the circuit breaker, the Knowledge Brain) but nothing that looked at all of them together and said, honestly, how the whole was doing. `self_awareness.js` is that engine.

## The one question it answers

*"How am I doing, truthfully?"* — not "how am I doing" alone. Every function in `self_awareness.js` was built to be able to report bad news; there is no code path that forces a positive verdict. This was verified directly, not assumed: see Testing below — the very first real run (baseline, healthy dashboard, no simulated failures at all) already produced *"أضعف خلية: Butter Compliance (15%)"* as part of its honest output, because that was the true state of recent inspection data at the time.

## The five parts

1. **Vital signs** — real-time checks, not assumptions: dashboard `/health`, whether the golden pipeline (`market_hunter` → `profit_oracle` → `inspectors`) has had activity within the last 48 hours (not just "does the file exist"), the Knowledge Brain's real file count (via `knowledge_brain.js`), real lesson count (`OpenClaw_Brain/19_Lessons_Learned/`, excluding its own README), real rejection counts (`REJECTED_NICHES.md` + `QUARANTINE.md`), and butter-price compliance computed from `inspections.log`'s actual recent `butter_price` check results — not a guess.
2. **Growth tracking** — `GROWTH_LOG.md` (repo root), one Markdown table row per calendar day. Each run reads back *yesterday's own row* and compares today's freshly computed numbers against it — never against a fixed target. First run has no row to compare against and honestly reports `direction: "baseline"`, not a fabricated trend.
3. **Self-diagnosis** — every vital sign that's failing or stalled becomes a named weakness (`{cell, issue}`); the first one is the officially "weakest cell." A dedicated Constitution-compliance check also surfaces `market_hunter.py`'s own already-documented, still-open gap (the circuit breaker not covering `/api/scout/run` — see [19_Lessons_Learned/The_Circuit_Breaker_Discovery.md](../19_Lessons_Learned/The_Circuit_Breaker_Discovery.md)) on *every single run*, so it can never be silently forgotten.
4. **The daily verdict** — one paragraph, built entirely from the three parts above: health word, growth word + real reason, strongest/weakest cell by score, biggest opportunity (from `golden_opportunities.json`'s real count), and next recommended focus (the weakest cell's actual issue, verbatim).
5. **Integration** — `GET /awareness` (fresh assessment every call, never writes `GROWTH_LOG.md` itself); `factory_loop.js` runs the write-once-daily version (`maybeRunSelfAwareness`, gated the same way `market_hunter`'s daily run is — by checking the log's own last date, not a separate marker file); `GET /good-morning` now includes a `self_awareness` section so Galaxy sees the truth every morning without a separate request.

## Why growth is measured against yesterday, not a fixed target

A fixed target ("knowledge entries should be ≥ 30") would need to be re-chosen constantly and would eventually just get raised whenever the factory happened to exceed it — turning the metric into self-congratulation. Comparing only against yesterday's own recorded state means the question is always the same, honest one: *did today's real work move any real number, in either direction* — and a `"weaker"` verdict is exactly as easy for the code to produce as a `"smarter"` one, because the comparison logic (`compareGrowth()`) is symmetric across both directions and the "same" case.

## Testing (all four required scenarios, verified for real — not asserted)

| # | Scenario | How it was actually tested | Result |
|---|---|---|---|
| 1 | First run creates baseline | `GROWTH_LOG.md` confirmed absent, ran `assessSelfAwareness()` | `growth.has_baseline: false`, `direction: "baseline"` — correct |
| 2 | Second-day growth comparison | Unit-tested `compareGrowth()` directly with hand-crafted improved/declined/unchanged inputs (all three verified independently); then integration-tested by calling `assessSelfAwareness(futureDate)` and confirming it correctly read back the real row just written for "today" | All three directions (`smarter`/`weaker`/`same`) produced correctly, with a real named reason each time |
| 3 | Weak cell → honest diagnosis | Temporarily renamed `market_hunter_runs.log` (simulating the cell having gone stale), ran the assessment, restored the file immediately after | `weakest_cell: "market_hunter"`, correctly first in the weaknesses list, verdict's "next recommended focus" pointed at it |
| 4 | Verdict is honestly not always positive | Demonstrated twice: (a) the very first real baseline run already flagged Butter Compliance at 15% despite an otherwise healthy dashboard; (b) pointed `DASHBOARD_URL` at an unreachable port and confirmed the verdict opened with *"اليوم المصنع غير متاح تماماً"* (today the factory is completely unavailable) rather than silently defaulting to a positive tone | Both confirmed — the verdict genuinely reflects bad news when there is bad news to reflect |

## Related

- [19_Lessons_Learned](../19_Lessons_Learned/) — the circuit-breaker gap this engine surfaces on every run
- [05_Living_Cells](../05_Living_Cells/) — the honest per-cell scoring this engine's own vital signs are modeled after
- [08_Market_Intelligence](../08_Market_Intelligence/) — `golden_opportunities.json`, the source of the verdict's "biggest opportunity" line

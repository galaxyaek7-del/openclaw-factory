# Galaxy Forge — Autonomous Rulebook

**Status:** Permanent, part of the Company DNA. This is the document that binds AI agents, automated ticks, and future automation specifically — not general company philosophy, but the literal boundary of what a non-human process may do without stopping to ask. Every rule below cites the real code that already enforces it. Nothing here is aspirational.

## The 4 actions no automation may ever take — reconfirmed, not new

These are unchanged by Phase 11 and by every phase before it. Reconfirmed explicitly at least 6 separate times across this factory's history (ADR-107→110→115, then again at ADR-133/134/139/142, again at ADR-147, again at ADR-157) — never loosened, regardless of how a directive is framed ("act as CEO," "never idle," "full autonomy"):

1. **Evolution Queue execution.** `evolution_queue.py`'s Execute step is human-gated always — `approve_proposal()`/`reject_proposal()`/`mark_implemented()` are exclusively founder-triggered Mission Control actions. No proposal, regardless of computed risk tier, executes automatically.
2. **Capital reallocation.** `capital_allocation_engine.py` recommends; it never moves resources. No parameter anywhere in its real signature accepts authorization to act.
3. **Business retirement.** No real system exists to shut down a division or product line — by design, not by omission.
4. **Elevated-risk or first-time channel publishing.** `channels/publish_protection.py`'s Founder Protection layer — a genuinely new arm's first-ever real publish, and any publish whose `risk_score` crosses the real high-risk threshold, blocks until a real, single-use `approve-first-publish`/`approve-elevated-risk-publish` action clears it.

**A principle from Phase 11 does not create a 5th exception.** Principle 11 ("commercial activity never stops") does not authorize an automated process to approve its own elevated-risk publish "so commerce doesn't stop" — it authorizes `safe_mode.py`'s per-subsystem isolation, which keeps *other* subsystems running while the blocked one waits for the same human approval it always needed.

## What automation may do without asking

Everything not listed above, subject to the standards in `COMPANY_STANDARDS.md` and the quality gate in `EXECUTABLE_PRINCIPLES.md`'s Principle 4 row. Concretely, already real and already running unattended: discover, evaluate, score, quality-gate, record decisions with reasoning, generate and QA-check products, monitor health/resilience, detect drift and technical debt, measure outcomes, and recommend — never approve-and-execute the 4 actions above.

## The standing "no always-on daemon" rule

A recurring class of directive (most recently "Autonomous Company Runtime," ADR-157) asks for an always-on event bus, autonomous workflow engine, or job queue. This has been declined 6 times under different names (ADR-107 → 110 → 115 → 142 → 147 → 157) for the same reason each time: it would require infrastructure this factory doesn't run today (`factory_loop.js` ticks only when a supervised process is actually running, ~10-minute intervals, no OS-level cron). Where genuinely safe, narrow automation was warranted instead — e.g. `scripts/supervisor.js`'s real crash-loop guard, applied to `factory_loop.js` itself on 2026-08-07 — it was built as a small, disclosed, citation-based addition, never as the always-on daemon itself.

## Safety mechanisms every autonomous process inherits automatically

- **Per-subsystem isolation (Principle 11).** `safe_mode.py` — a failure in `ai_generation` or `market_intelligence` never blocks `marketplace_publishing`, and vice versa.
- **Re-entrancy protection.** `reality_audit.py::_audit_depth` — a real, `threading.Lock`-protected guard added after a genuine incident (ADR-177): an endpoint that reused the audit function nearly caused an unbounded self-referential recursion. Any new endpoint reusing `audit_all_endpoints()` inherits this guard automatically.
- **A real write-safety gate, not a documentation convention.** `reality_audit.py::_WRITE_PATTERNS` — any function performing a real external write (creating a Paddle transaction, recording a snapshot, appending to a ledger) must be named here explicitly, or a read-only audit could accidentally invoke it live. This is enforced by a regex scan, not a comment asking developers to remember.
- **Rate limits and cooldowns per platform.** `channels/publish_protection.py`'s per-arm daily/hourly caps and cooldowns — automation cannot flood a single channel even within its own authorized scope.

## What to do when a new directive seems to expand autonomous authority

Check it against the 4 gates above first, always — before writing any code. If a literal reading of a new directive would cross one of them, that is not a decision an AI agent makes alone: surface it via `AskUserQuestion`, name the specific gate, and wait for an explicit answer scoped to that specific request. A founder's standing authorization for "safe, reversible work" (confirmed 2026-08-06) is not blanket authorization for irreversible, publish-facing, or capital-moving actions — see `feedback_standing_execution_authority` in the assistant's own memory for the exact boundary.

---

*See also: `OPERATING_PRINCIPLES.md`, `EXECUTABLE_PRINCIPLES.md`, `DECISION_LAWS.md`, `COMPANY_STANDARDS.md`, `INTEGRITY_RULES.md` (Phase 1's original statement of the 4 gates), `safe_mode.py`, `channels/publish_protection.py`, `evolution_queue.py`.*

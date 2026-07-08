# 16 — Laboratory

## The principle (OPENCLAW_OS_CONSTITUTION.md — Future Evolution)

> Continuously research: AI, applications, frameworks, libraries, servers, APIs, automation tools, business opportunities. Every candidate enters the Laboratory before production.

## Honest current state: no formal Laboratory process exists

There is no staging environment, feature-flag system, or "candidate" review step separate from production in this repository. In practice, every new capability this project has built (`profit_oracle.py`, `inspectors.py`, the circuit breaker, `cover_designer_v2.py`) was built, tested live against the running dashboard, and merged directly — there was never a separate "lab" phase.

## What has functioned *like* a lab, informally

- New Python modules are almost always tested standalone first (`python module.py` demo mode, or direct `python -c "..."` calls) before being wired into `book_generator.py`/`server.js` — this is the closest existing analog to "enter the lab before production."
- `niche_reports/` exists as a place for saved, manual niche research (via `niche_validator_v2.py`) that then feeds real data into `profit_oracle`'s scoring — a small, real example of research artifacts becoming production inputs.

## Gap worth naming

If OpenClaw ever adopts a new AI provider, framework, or automation tool at meaningful scale, there is currently no defined process (a directory convention, a checklist, a review gate) for that to go through before it reaches `book_generator.py` or `server.js` directly. Worth building deliberately rather than continuing informally, once the cost of an informal mistake becomes higher than it is today.

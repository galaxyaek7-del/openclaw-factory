# OpenClaw / Galaxy Forge — Executive Council

**Status:** Permanent, part of the Company DNA (`COMPANY_DNA.md`). This directive's 10 named roles match `executive_board.py`'s real `EXECUTIVE_ROLES` (2026-07-22) almost exactly. No 4th parallel council roster is created here — this document names the real one and discloses the 2 real differences honestly rather than silently rebuilding it under a new name, which this company's own history has already learned the cost of once (`CLAUDE.md`'s own note: "Three distinct rosters now exist... deliberately not merged" — a 4th would make that worse, not better).

---

## The real roster

`executive_board.py::EXECUTIVE_ROLES` = **CEO, CTO, CFO, COO, CPO, Chief Market Intelligence Officer, Chief Risk Officer, Chief Revenue Officer, Chief Customer Officer, Chief Innovation Officer.**

8 of this directive's 10 named roles match exactly or by direct real-world equivalence (CEO, COO, CTO, CFO≈Chief Financial Officer, CPO≈Chief Product Officer, Chief Innovation Officer, Chief Risk Officer, Chief Customer Officer). Two genuinely differ:

- **Chief Commercial Officer** (requested) vs. **Chief Revenue Officer + Chief Market Intelligence Officer** (real) — the real roster splits commercial territory into revenue-execution and market-intelligence lenses rather than one combined CCO seat. Functionally overlapping, not identical.
- **Chief Security Officer** (requested) — a genuine, real gap. No named executive role in `executive_board.py` owns security specifically; real security concerns are instead covered structurally by `resilience_monitor.py`, `safe_mode.py`, and the real security-audit work already done this session (Mission Control auth, `INTERNAL_SERVICE_TOKEN`), just not voiced through a named council seat.

## How each member actually works

Each real role in `executive_board.py` is a function producing `{opinion, confidence, evidence, risk, recommendation, founder_approval_required}` from a real, cited source — never a fabricated independent judgment. The CEO seat, for example, synthesizes the other 9; the CFO seat cites real financial signals; the Chief Risk Officer cites the real 8-item risk registry. Disagreement between members is never blended into a fake consensus — a real board vote (`data/board_meetings.jsonl`) records genuine splits as splits.

**A second, real, deliberately distinct council also exists:** `galaxy_council.py` (ADR-138) — 9 members, a different, company-wide-scoped roster (Strategic/Market/Production/Customer/Financial/Security/Resilience/Innovation/Executive-Memory), used for per-niche convening rather than board-level irreversible-decision votes. `galaxy_council.py`'s Security member is the closest real analog to the requested Chief Security Officer seat — cited here, not duplicated.

## Review requirement

**Every irreversible or high-stakes decision already requires real board review** — `executive_board.py`'s own rule: irreversible decisions require unanimous approval, production decisions require a real majority, matching this company's standing "5 things need explicit approval" taxonomy (`COMPANY_DNA.md`, `INTEGRITY_RULES.md`). This is not a new requirement introduced by this document — it is the real, existing rule, named here for visibility.

---

*See also: `EXECUTIVE_BRAIN.md` (which synthesizes across the Council's real inputs), `DECISION_PROTOCOL.md` (the format every reviewed decision follows).*

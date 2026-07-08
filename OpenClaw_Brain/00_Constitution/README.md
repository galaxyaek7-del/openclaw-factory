# 00 — Constitution

The two governing documents of OpenClaw, in authority order:

1. **[OPENCLAW_OS_CONSTITUTION.md](../../OPENCLAW_OS_CONSTITUTION.md)** — supreme law. Mission, DNA, Living Cell Architecture, the Councils, Golden Hunter, Quality, Smart Publishing, Intelligent Marketing, Digital Sanitation, Knowledge, Security, Neutrality, Anti-Fragility. Installed 2026-07-08.
2. **[CONSTITUTION.md](../../CONSTITUTION.md)** — engineering-specific implementation standard. 18 numbered principles (as of this Brain's creation) translating the supreme law into concrete code-level rules for this repository. Never contradicts document 1; where they'd conflict, document 1 wins.

## Why two documents, not one

`OPENCLAW_OS_CONSTITUTION.md` describes what kind of company OpenClaw is and why (mission, culture, councils) — it doesn't mention a single file, function, or endpoint by name. `CONSTITUTION.md` is the opposite: every principle names the actual file that implements it (`inspectors.py`, `profit_oracle.py`, `factory_loop.js`...). Keeping them separate means the supreme law never needs to change just because the codebase does.

## Amendment discipline (a real, recurring pattern worth knowing)

Several tasks this project has referenced a `CONSTITUTION.md` principle as if it already existed — it didn't. Every time, the fix was the same: verify with `grep` first, then add the missing principle at its true next number (never skip numbers to match a task's guessed number), and record *why* in `CONSTITUTION.md`'s own Amendment History table. This has happened for: the 70/20/10 cover rule, the Butter Principle (§16), Dual Inspection (§17), and (most likely) this Brain's own Principle 24 request. See [19_Lessons_Learned](../19_Lessons_Learned/) for the general pattern this reveals about how tasks get specified.

# 🧠 OpenClaw Brain — Master Index

> "Knowledge evolves the factory. Without permanent knowledge, there is no self-evolution." — OPENCLAW_OS_CONSTITUTION.md, Knowledge

This is the home page of OpenClaw's permanent, organizational memory. Written in plain Markdown — works with or without the Obsidian app (open this folder as an Obsidian vault for backlinks/graph view, or just read it as files). Nothing here is fabricated: where real information didn't exist for a section, that gap is stated explicitly rather than invented. Search this Brain before building — see [knowledge_brain.js](../knowledge_brain.js).

## The traceability chain

This is the intended reading order — each link is a real, load-bearing relationship, not just a folder list:

```
01_Vision            → why OpenClaw exists, the six tracks, the Golden Rule
   ↓
00_Constitution      → the two governing documents that encode that vision into law
   ↓
04_Architecture       → how the law is implemented as running systems (3 layers, Living Cells)
   ↓
05_Living_Cells      → each real component, scored honestly against the Living Cell checklist
   ↓
06_Councils          → which Cell answers to which Council mandate
   ↓
03_Current_Mission   → what's actually being worked on right now (Day 07)
   ↓
18_Daily_Logs        → the day-by-day history that produced today's state
   ↓
19_Lessons_Learned   → what broke, why, and the fix — read before repeating a mistake
```

## Full folder map

| # | Folder | What's there |
|---|---|---|
| 00 | [Constitution](./00_Constitution/) | The supreme law + engineering constitution, and how they relate |
| 01 | [Vision](./01_Vision/) | Mission, the six product tracks, the Golden Rule |
| 02 | [Roadmap](./02_Roadmap/) | Real near-term milestones (⚠️ no "20-day plan"/"octopus vision" doc exists yet) |
| 03 | [Current_Mission](./03_Current_Mission/) | Day 07 status — kept in sync with `FACTORY_STATUS.md` |
| 04 | [Architecture](./04_Architecture/) | The 3 real layers (⚠️ not 6) + today's actual running system diagram |
| 05 | [Living_Cells](./05_Living_Cells/) | Scout, profit_oracle, inspectors, circuit breaker — honestly scored |
| 06 | [Councils](./06_Councils/) | Which component implements which of the 12 named Councils |
| 07 | [Knowledge_Base](./07_Knowledge_Base/) | Index into the more specific knowledge domains below |
| 08 | [Market_Intelligence](./08_Market_Intelligence/) | `GOLDEN_OPPORTUNITIES.md` explained — what's real data vs. estimate |
| 09 | [Prompt_Library](./09_Prompt_Library/) | The 6 agent prompts + Scout's brief prompt + the pricing-example lesson |
| 10 | [Automation](./10_Automation/) | The n8n contract, both integration paths, the manual step still pending |
| 11 | [Security](./11_Security/) | Guarded imports, the token-handling protocol, fail-closed design |
| 12 | [Production](./12_Production/) | `book_generator.py` pipeline, `cover_designer_v2.py`, the publish-gate distinction |
| 13 | [Publishing](./13_Publishing/) | Honest state: no automated upload exists anywhere yet |
| 14 | [Marketing](./14_Marketing/) | Honest state: content generation only, no distribution |
| 15 | [Finance](./15_Finance/) | `finance_data.json`, self-healing, and the real number: $0 revenue to date |
| 16 | [Laboratory](./16_Laboratory/) | The supreme law's "test before production" principle vs. today's informal practice |
| 17 | [Research](./17_Research/) | Open notebook for research that doesn't fit elsewhere yet |
| 18 | [Daily_Logs](./18_Daily_Logs/) | Day 05–07 narrative (⚠️ Days 01–04 not documented anywhere found) |
| 19 | [Lessons_Learned](./19_Lessons_Learned/) | **Read first.** The success:true bug, the $12.99 pricing trap, the circuit-breaker discovery |
| 99 | [Archive](./99_Archive/) | Where superseded knowledge goes to stay findable |

## The standing rule

CONSTITUTION.md §18 (Knowledge Brain): *nothing valuable stays only in conversations.* Every real lesson, decision, or discovery from a task gets written here — in the specific folder it belongs to, linked from here — before the task is considered finished.

## Tools

- `knowledge_brain.js` (repo root) — searches this whole tree by keyword from the command line or from `server.js`
- `GET /brain` (dashboard endpoint) — returns this folder structure + a live count of entries per section, so the knowledge map is checkable without opening every file

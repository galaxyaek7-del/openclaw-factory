# 07 — Knowledge Base

This folder is the index for the Brain's more specific knowledge domains. It doesn't duplicate their content — it points to it, so there's exactly one place each fact lives.

| Domain | Where it actually lives |
|---|---|
| Market intelligence (scored niches, GOLDEN opportunities) | [08_Market_Intelligence](../08_Market_Intelligence/) |
| Prompts that work (and why) | [09_Prompt_Library](../09_Prompt_Library/) |
| n8n / automation contracts | [10_Automation](../10_Automation/) |
| Security practices | [11_Security](../11_Security/) |
| Production pipeline internals | [12_Production](../12_Production/) |
| Daily operational history | [18_Daily_Logs](../18_Daily_Logs/) |
| Hard-won lessons (read these first) | [19_Lessons_Learned](../19_Lessons_Learned/) |

## The standing rule (CONSTITUTION.md §18, Knowledge Brain)

> Nothing valuable stays only in conversations. Every lesson becomes permanent, linked knowledge. Search the Brain before building.

In practice: before starting a non-trivial task, check [19_Lessons_Learned](../19_Lessons_Learned/) and [05_Living_Cells](../05_Living_Cells/) for whether this exact problem (or a component it depends on) has already been solved, has a known gap, or has already failed once for a documented reason. `knowledge_brain.js` (see repo root) is a small helper that searches this whole folder tree by keyword, so that check doesn't require manually opening 20 folders.

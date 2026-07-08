# 04 — Architecture

## ⚠️ Honesty note on "6-layer"

This task asked for a "6-layer + living cells map." **The real, documented architecture in [CLAUDE.md](../../CLAUDE.md) is 3 layers, not 6** — verified by reading the file directly. Reporting it as 3 here rather than stretching it to 6. If "6-layer" refers to something else (perhaps the six product *tracks* in [01_Vision](../01_Vision/), which are a separate concept from the layers), that distinction is worth clarifying with Galaxy rather than guessed at.

## The 3 real layers (CLAUDE.md)

```
Layer 1 — Shared Brain (Core)
  The six agents + Groq + shared tools. Never changes.

Layer 2 — Product Engines
  book_engine   template_engine   art_engine
  app_engine    service_engine    trade_engine
  Independent — addable/removable. Only book_engine exists today.

Layer 3 — Publishing Channels
  kdp_channel   etsy_channel   gumroad_channel
  shopify_channel   direct_channel
  If a platform shuts down, only its channel stops — nothing else does.
```

## Today's actual running architecture (as opposed to the aspirational 3-layer plan)

```
server.js (Express, port 3000)          — the Brain (Constitution: "Sensing ↔ Brain")
  ├─ /api/scout/run    → Groq brief → book_generator.py
  ├─ /generate-book    → book_generator.py directly
  ├─ /api/trends       → n8n → OPPORTUNITIES.md (Quality Gate filtered)
  ├─ /oracle, /inspections, /good-morning, /health, /finance, /brain (new)
  └─ 6 agent endpoints (/api/agent/:name) — live Groq calls

book_generator.py (Python)              — Production
  ├─ ai_generate_book_content()  — Groq
  ├─ cover_designer_v2.generate_cover()  — Pillow, 70/20/10
  ├─ _resolve_price()  — Smart Publishing repricing
  └─ inspectors.final_inspection()  — the master publish gate

factory_loop.js (separate process)      — Self-Healing / Anti-Fragility
  ├─ HEAL: finance corruption, empty books/, n8n unreachable
  ├─ HUNT: retry the most recent Quality-Gate-passed niche
  ├─ circuit breaker: REJECTED_NICHES.md, 7-day cooldown
  └─ weekly report generation (Sundays)

n8n (separate process, localhost:5678)  — Sensing layer only
  knows nothing about book generation, quality gates, or pricing
```

## Living Cell Architecture (OPENCLAW_OS_CONSTITUTION.md)

Every component above is meant to satisfy this checklist. See [05_Living_Cells](../05_Living_Cells/) for the honest per-component scoring — not every cell satisfies every property yet.

| Property | Meaning |
|---|---|
| Independent | Can run/fail without taking down the rest |
| Reusable | Not hardcoded to one specific use |
| Scalable | Can handle more load without a rewrite |
| Secure | Guarded inputs, no leaked secrets |
| Observable | Logs its own behavior somewhere real |
| Documented | A human (or this Brain) can understand it without reading all the code |
| Recoverable | Failure has a defined, safe fallback — never a silent crash |

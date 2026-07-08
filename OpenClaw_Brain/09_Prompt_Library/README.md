# 09 — Prompt Library

Real prompts, quoted from `server.js`, not paraphrased. Each entry notes what actually works and why, or what changed and what broke before the fix.

## The 6 Agent System Prompts (`AGENT_PROMPTS` in `server.js`)

All six follow the same shape: role definition → numbered output requirements → language/format instruction. This consistency is deliberate (Constitution §2, modular architecture) — a 7th agent should follow the same shape.

| Agent | Trigger (what fires by default with no user message) |
|---|---|
| `scout` | "حلّل السوق الآن وأعطني أفضل 5 أفكار كتب رابحة لهذا الشهر على Amazon KDP وEtsy" |
| `builder` | "اقترح كتاباً رقمياً جديداً مع هيكله الكامل ومثال على محتواه" |
| `design` | "اقترح تصميماً احترافياً كاملاً لغلاف وصفحات داخلية لكتاب journal أو planner" |
| `qa` | "افحص معايير الجودة وأعطني checklist كاملة لضمان قبول منتجنا الرقمي" |
| `publisher` | "حضّر بيانات نشر كاملة ومحسّنة لـ SEO لكتاب daily journal على Amazon KDP" |
| `finance` | "حلّل الربحية وأعطني استراتيجية تسعير كاملة لكتبنا الرقمية على KDP وEtsy وGumroad" |

Full system prompt text: `server.js` lines ~250–311 (`AGENT_PROMPTS`) — not duplicated here to avoid drift; read the source.

## Scout's Niche/Brief Prompt (`scoutBriefPrompt()`, `server.js`)

This is the prompt that actually picks what book gets built next. It uses a **few-shot example** — Groq imitates the example's format *and*, it turns out, its numbers. This was a real, discovered bug:

> The example originally showed `##PRICE## 9.99`. Groq consistently suggested prices in the $9.99–$14.99 range — not because the niche was weak, but because that's what the example taught it "normal" looked like. See [19_Lessons_Learned/The_1299_Pricing_Trap.md](../19_Lessons_Learned/The_1299_Pricing_Trap.md).

**Fixed (Day 06–07):** the prompt now explicitly instructs value-based premium pricing (depth, professional audience, market comparables, $30 minimum, justify by value) *and* the few-shot example's price was changed to `$39`. A live test after the fix: Groq suggested $49 on its own, unprompted by a specific number. The lesson generalizes — **a few-shot example is a stronger behavioral signal than an instruction sentence.** If a prompt's few-shot example and its stated rule ever disagree, expect the model to follow the example.

## QA/Placeholder-Detection Prompts (not LLM prompts — pattern to reuse)

Not a Groq prompt, but a related "prompt-adjacent" lesson: `book_generator.py`'s content parser expects the AI to echo literal section tags (`##SUBTITLE##`, `##TITLE##`). When the model does exactly that (as instructed), naive parsing can mistake the *tag name itself* for content. See [19_Lessons_Learned](../19_Lessons_Learned/) — any future prompt using tag-based section markers should validate parsed output isn't the tag name itself before trusting it.

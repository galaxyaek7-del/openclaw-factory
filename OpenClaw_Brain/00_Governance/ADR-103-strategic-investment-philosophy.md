# ADR-103 — Strategic Investment Philosophy: Digital Investment Company, Technology-Agnostic Principle, Deferred Global Expansion

**Date:** 2026-07-23
**Status:** Adopted (philosophy + Technology Investment Council extension). Global Market Expansion / China Strategic Program explicitly **deferred**, not built, per founder confirmation.

---

## The directive

"OpenClaw is not a software company. It is a Digital Investment Company." Software/AI/automation/templates/books/courses are investment vehicles, not the mission itself. Adopt a technology-agnostic principle (no loyalty to any AI model/company/platform — Claude, GPT, Gemini, DeepSeek, Qwen, Kimi, Doubao, open-source are all production tools, selected only on results/quality/speed/reliability/economics/customer outcomes). Create a permanent Technology Investment Council continuously evaluating the AI stack. Treat every country as an independent investment opportunity (9 named priority markets); create a permanent China Intelligence Division. "Value before products" — never ask "what can we build," always ask "what is worth investing in."

## What this is, structurally

Most of this directive is a **doctrine/philosophy statement**, not a set of features to build — it belongs in governance documentation (this ADR + `CLAUDE.md`), not in new code. Three concrete build requests were embedded in it: a Technology Investment Council, a China Intelligence Division, and per-country market intelligence for 9 named markets. Each was evaluated against what's real in this factory before any code was written, per this whole engagement's standing discipline.

## "Value before products" — already substantially built

`value_engine.py` (ADR-102, same session) already **is** the real, working answer to "does this increase long-term company value" — 17 dimensions, a real Priority Score, a real Recommendation, per real ACCEPTED opportunity. No new module was needed here; this directive's "Value Before Products" section is fully satisfied by already-shipped work, cross-referenced rather than duplicated.

## Technology Investment Council — a real search found it 90% already built

`ai_capability/registry.py` (ADR from Autonomous Digital Company v1, Track B2, 2026-07-19) is, in substance, already the Technology Investment Council this directive asks for: a real `PROVIDER_CATALOG` naming every candidate provider, real computed metrics for Groq (the only provider this factory has ever actually called — cost, latency, from `data/ai_cost_log.jsonl`), and an honest `DISCOVERY`-level status (never a fabricated benchmark) for every other named provider until a real credential exists and is actually called. `ai_capability/evaluator.py`'s `recommend_for_task()` already implements "continuously evaluated, adopted when measurably better" — conservatively, since real comparative data exists for exactly one provider today.

**What was extended, not rebuilt:**
- `PROVIDER_CATALOG` gained 2 real, named candidates this directive explicitly asked for that weren't tracked yet: `moonshot_kimi` (Kimi) and `bytedance_doubao` (Doubao) — same honest `DISCOVERY`-level entry as every other untested provider.
- `METRIC_NAMES` gained the 4 named criteria from this directive not already covered: `security`, `maintainability`, `customer_value`, `business_impact` (`quality`/`cost` already existed; `speed`≈latency and `availability`≈stability already existed under different names). Every existing and new metric for every non-Groq provider stays honest `DISCOVERY` — this directive did not, and could not honestly, change that; this factory still has zero real API access to GPT/Gemini/DeepSeek/Qwen/Kimi/Doubao/Mistral/Grok/local models.

No new module, no new Mission Control action needed — `mission_control_api.py`'s existing `ai_capability`/`ai_capability_request` actions are already passthrough over `registry.list_providers()` and picked up both extensions automatically; only their docstring was updated for accuracy.

## Global Market Expansion / China Intelligence Division — deferred, documented, not built

A real search found:
- This factory's only two real external data sources are Hacker News and GitHub Search — both English-language, globally-mixed, not meaningfully segmented by country. Zero real connectors exist to any China-specific platform (Baidu, WeChat, Xiaohongshu, Douyin, Zhihu, JD, Alibaba) or to any real localized data source for the other 8 named markets (Japan, South Korea, Germany, UK, India, Southeast Asia, Middle East) beyond the same generic global English-language signal already used for every niche regardless of geography.
- Building "independent intelligence" per named market with these inputs would mean either (a) fabricating country-specific signal that doesn't actually exist, or (b) silently relabeling the same generic HN/GitHub search as "China intelligence" — both are exactly the failure mode this whole engagement has refused, repeatedly, all session (the Global Opportunity Intelligence mission and the Live Competitive Intelligence mission both hit and disclosed the identical class of gap).
- This also runs directly against `CLAUDE.md`'s own pre-existing, standing golden rule: **"لا توسع بمنتج جديد قبل أول دولار من المنتج الحالي"** (no expansion to a new product/market before the first real dollar from the current one) — and zero real completed sales exist on any channel today, confirmed repeatedly across this session's own audits (`ENTERPRISE_UPGRADE_ROADMAP.md` finding 5.1).

**Founder-confirmed decision:** document the philosophy now (this ADR + the new `CLAUDE.md` section); build no country-specific intelligence module yet. Revisit when either (a) a real first dollar lands on any channel, or (b) a real localized data connector for at least one named market becomes genuinely available — whichever comes first. This is a deliberate, disclosed deferral, not a silently dropped request.

## Verification

`ai_capability/registry.py`'s extension: `tests/test_ai_capability.py` updated (`test_all_nine_providers_present` → `test_all_eleven_providers_present`, reflecting the 2 new real candidates) plus 1 new test confirming all 8 named Technology Investment Council criteria exist in `METRIC_NAMES`. Full `tests/test_ai_capability.py` suite green (18/18).

## What's next

No further pieces are queued for this directive's build scope. The deferred Global Market Expansion / China Intelligence Division piece has explicit, real revisit triggers documented above rather than an open-ended "someday."

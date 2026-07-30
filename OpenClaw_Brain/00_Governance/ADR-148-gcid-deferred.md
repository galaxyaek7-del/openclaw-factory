# ADR-148 — Global Commerce Intelligence Division (GCID): Deferred

**Date:** 2026-07-30
**Status:** Deferred (documented, not built — by explicit founder decision).

---

## The directive

"EXECUTIVE DIRECTIVE — GLOBAL COMMERCE INTELLIGENCE DIVISION (GCID)." A permanent new business division and revenue engine: continuous discovery of affiliate programs, marketplace partnerships, and 9 other named commerce categories; continuous evaluation across commission rate/conversion rate/market demand/competition/customer value/refund risk/partner reputation/recurring revenue/long-term sustainability; automatic discovery, ranking, comparison-page and landing-page generation, offer recommendation, conversion/commission monitoring, campaign retirement/scaling; a Mission Control view (Affiliate Revenue, Top Partners, Top Products, Conversion Rate, Commission Forecast, Partner Health, Growth Opportunities); resource allocation from the Executive Brain by expected ROI.

## The real conflict, verified before any code was written

`CLAUDE.md`'s own "القواعد الذهبية" (Golden Rules) — the single most foundational, repeated principle in this factory's entire governing document — states: **"لا توسع بمنتج جديد قبل أول دولار من المنتج الحالي"** ("No expansion with a new product before the first real dollar from the current product"). This rule has been personally invoked by the founder, and applied, multiple times before today to defer other expansions under materially identical circumstances: the six-track product vision (`CLAUDE.md`'s own architecture section) has kept Tracks 2–6 (templates, digital art, apps/tools, VIP services, international trade) undocumented-as-built specifically pending this condition; the country-level/China market expansion was explicitly deferred on 2026-07-23, with `CLAUDE.md` itself citing this exact rule as the reason ("هذا يتعارض أيضاً مباشرة مع القاعدة الذهبية أعلاه").

**Verified directly before any code was written, not assumed**: this factory has zero real revenue today. `finance_data.json`'s one recorded "sale" is a literal smoke-test record — its product field reads `"contract-test-ladder-DELETE-ME"`. The factory's own stricter, founder-designed ground-truth ledger (`config/reality.json`, whose own header states "the factory cannot fake these numbers" — a human must manually add a real Amazon ASIN after a real KDP publish before an entry exists here) shows `published_books: []` — zero real products published on any channel, confirmed live this same session via the Company Health panel's own real verdict: `"CRITICAL... Zero products published on any channel (KDP or otherwise). The factory produces inventory nobody can buy."`

GCID would launch an entirely new, genuinely unbuilt revenue-generating business division — confirmed by a direct repo-wide search finding zero existing affiliate/commission/partner infrastructure anywhere in this codebase — under exactly the condition (zero real dollars from the current product) the Golden Rule exists to prevent expansion under.

**Surfaced via `AskUserQuestion` before writing any code. The founder's answer: defer entirely, document only** — the same resolution this factory has already applied to every other pre-first-dollar expansion request.

## What was built

Nothing. This ADR itself is the complete deliverable for this directive, by explicit founder decision.

## The real trigger to revisit

Per the same standing pattern the country-expansion deferral already established (`CLAUDE.md`): re-examine when either (a) the first real dollar is earned from the current product (a real completed sale on any live channel, verifiable against `config/reality.json`'s own real ground-truth ledger — not `finance_data.json`'s raw, unvetted totals, which the test-record incident above shows can carry non-real entries), or (b) the founder explicitly overrides the Golden Rule for this specific initiative, in a session that begins from that explicit instruction rather than rediscovering the conflict fresh.

## Note on `finance_data.json`'s test record

Not fixed here (out of scope for a documentation-only ADR, and not requested) — flagged for whoever next touches finance data: a real smoke-test sale (`"contract-test-ladder-DELETE-ME"`, `id: 1784854757424`, dated 2026-07-24) remains live in `finance_data.json`'s real totals (`totalSales: 150`), which is why this ADR verified the real ground truth via `config/reality.json` instead of trusting `finance_data.json` at face value. A future session should decide whether to remove it (its own product name asks to be deleted) or leave it as a known, disclosed test artifact.

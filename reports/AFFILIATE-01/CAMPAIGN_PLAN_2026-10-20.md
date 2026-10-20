# GF-AFFILIATE-01 — Campaign plan (first zero-spend attempt)

Recorded 2026-10-20. Budget: `TOTAL_NEW_SPEND = $0`. Accounts created: 0. Applications submitted: 0.
Publication: **NOT AUTHORIZED** — nothing here has been posted anywhere.

---

## 1. What the research actually changed

The mission asked me to treat Digistore24, PartnerStack and impact.com as the first three to investigate, then to select the first offer on evidence.

Result of that investigation (`NETWORK_VERIFICATION_2026-10-20.json`):

| Network | Signup cost | Reaches an Algerian bank? | Verdict |
|---|---|---|---|
| impact.com | $0 | Bank transfer, Algeria selectable as bank country | `USABLE_FREE_PENDING_AUTHORIZATION` |
| Digistore24 | $0 | Only international wire, €250 minimum, 10% held 60 days | `HOLD` |
| PartnerStack | $0 | No published rail (Airwallex excludes Algeria) | `HOLD` |
| Awin | $1 refundable deposit | International wire likely | `BLOCKED_BY_ZERO_SPEND` |
| systeme.io direct | $0 | Wire or PayPal; already enrolled | `USABLE_NOW` |

**The finding that matters:** the first campaign does not need a new network at all. `systeme.io`'s direct program is free, requires no approval, pays 60% recurring for the life of the subscription, has a $30 minimum, and this factory **already holds a verified active tracked link** for it (`SYSTEME_DIRECT`, registered 2026-09-21, attribution confirmed 2026-10-01).

Starting with a network I would have to be approved by introduces an unverifiable delay for zero added value. The rational first attempt is the offer where the link already works and the buyer can evaluate the product for free.

impact.com remains the correct **second** network: it is the only new one that is free *and* plausibly payable to Algeria. It is prepared for the founder to submit, not submitted by me — registration accepts a binding agreement.

---

## 2. Offer selection

**Selected: systeme.io (direct).**

Criteria applied, in the order the mission gave them:

| Criterion | Assessment |
|---|---|
| Real buyer demand | Small business owners and course creators searching for an all-in-one funnel + email tool. Genuine, long-standing, high-volume search category. |
| Honest product | The free plan is genuinely usable and does not expire. Verified on systeme.io's own pricing page: 2,000 contacts, 3 funnels, 1 course, unlimited emails, no credit card. |
| Commission | 60% of every payment, lifetime recurring. $30 minimum. Monthly payout on the 10th. |
| Can I describe it truthfully without exaggeration? | Yes — the honest angle exists and is more persuasive than hype: *the free plan is enough for most people below 2,000 contacts; you only need to pay when you hit a named ceiling.* |
| Zero spend to test | Yes — link already active, publication is the only remaining cost. |
| Attribution verifiable | Yes — tracked link on file; clicks land in `data/affiliate_clicks.jsonl`. |

**Honest disadvantage that must appear in the content:** the free plan's ceiling is real (2,000 contacts, 3 funnels, 1 automation rule, 1 email campaign, 500 students). A reader who needs any of those today should not be nudged to upgrade blindly — they should be told the ceiling exists.

**Not selected, and why:**
- impact.com — no specific brand hand-picked yet; the marketplace cannot be browsed before approval. Preparing a generic "apply now" campaign would be guesswork.
- Digistore24 / PartnerStack — `HOLD` for payout reasons above, not for quality.
- Awin — deposit is spend.
- Amazon Associates — existing factory program but the tag is unset, so links cannot earn. Founder-only fix.
- The two offers already in `data/partnership_pipeline.jsonl` (hostaway 20%×12mo, lemsub 25% recurring) — real but only `DISCOVERY`; no tracked link exists, and neither is reachable without a PartnerStack payout path. They stay in the pipeline as second-wave candidates.

---

## 3. Content themes (chosen for search intent, not for virality)

Three themes, in order of expected qualified traffic per unit of effort:

1. **"What the free plan actually gives you, and what it stops giving you."**
   Buyers search this before upgrading. The answer is useful whether or not they buy, which is why it earns trust and clicks. → drafted: `drafts/affiliate/systeme_free_plan_ceiling_2026-10-20.md`.

2. **"Free plan vs $17 plan: the three limits that decide it."**
   Decision-stage comparison, built only from systeme.io's own published limits. No competitor bashing, no invented benchmarks. → outlined below, drafted after theme 1 is reviewed.

3. **"Migration reality check"** — deliberately *deferred*. systeme.io advertises free migration; describing a migration honestly requires hands-on experience this factory does not have. Writing it now would be second-hand marketing. Skipped rather than faked.

Explicitly rejected themes: "make $X/month with systeme.io", "top 10 tools 2026" listicles (unverifiable comparisons), anything using fake scarcity or a countdown.

---

## 4. Promotion plan — what is allowed without authorization

The mission forbids external publishing without authorization. So the plan separates preparation from action:

**Prepared now (no external effect):**
- One complete article draft, publication-ready, with the affiliate disclosure and a tracked-link placeholder.
- A value-first community answer template, for Q&A threads where the question is literally about funnel-tool limits.

**Requires founder authorization (not done):**
- Publishing the article anywhere: a factory-owned page, a blog, LinkedIn article, Medium, Reddit, Quora, or a directory.
- Sending anything outbound: email, DM, cold outreach.
- Paid traffic: permanently out of scope under `TOTAL_NEW_SPEND = $0`.

**Channel ranking, if authorized:**
1. A page on infrastructure the factory already controls — no new account, no new spend, disclosure in place.
2. A single substantive answer in one relevant Q&A thread where the question matches the article's exact subject. One answer, disclosure included, no link-dropping in unrelated threads.
3. LinkedIn post summarising the decision rule, link in the first comment.

Explicitly not planned: mass posting, comment spam, fake accounts, incentivised reviews, automated DMs.

---

## 5. Tracking and evidence

**No new tracking system was built, because one already exists and duplicating it would be worse than reusing it.**

| Stage | Where it is recorded | Current truth |
|---|---|---|
| Offer / network | `data/affiliate_activation_pack.json`, `data/affiliate_links.jsonl` | 1 real tracked link (`SYSTEME_DIRECT`) |
| Content asset | `drafts/affiliate/` + this plan | 1 draft, `NOT_PUBLISHED` |
| Publication status | article front-matter `publication_status` | `NOT_PUBLISHED` |
| Clicks | `data/affiliate_clicks.jsonl` (append-only, UTM fields) | 29 rows, **all `referrer: null`** → zero qualified clicks ever |
| Page views | `data/affiliate_page_views.jsonl` | no real traffic |
| Attributed / approved / payable / received | `commission_ledger.py` — statuses `EXPECTED, PENDING, CONFIRMED, PAID, REVERSED, REFUNDED, DISPUTED, UNKNOWN`, environments `REAL, TEST, SIMULATION, PROVISIONAL` | **0 real commission records, $0** |

The ladder the mission asked for maps onto this as: click = click ledger; attributed = `EXPECTED`; approved = `CONFIRMED`; payable = `CONFIRMED` and past threshold; received = `PAID`. `REVERSED`/`REFUNDED` cover reversals. **Revenue is counted only at `PAID`** — `real_commission_summary()` already enforces that and reports 0 today.

Gap that remains, stated plainly: the click ledger records clicks only and never conversions (by design, its own docstring says so). A conversion has to be entered from the network's dashboard via `commission_ledger.record_commission()` with `environment="REAL"`, which requires evidence. Until a real conversion happens, that path is untested against reality — not broken, just unexercised.

---

## 6. Execution order

1. Founder reviews the draft and the network record. *(you are here)*
2. Founder decides whether to authorize publication of theme 1. If yes, publish in one channel only.
3. Founder decides on impact.com registration — it is free, but it is a binding agreement and therefore not mine to accept.
4. After 30 days with the link live: read the click ledger. If zero qualified clicks, the problem is distribution, not the offer — fix distribution before writing asset two.

---

## 7. Acceptance criteria, reported separately as required

| Criterion | State |
|---|---|
| Networks researched | 4 primary + 2 existing programs, each with evidence URL and date |
| Networks verified usable for an Algerian seller at zero cost | 1 clean (`impact.com`, pending approval), 1 already active (`systeme.io`), 2 `HOLD`, 1 `BLOCKED_BY_ZERO_SPEND` |
| Applications prepared | 0 submitted. Preparation notes exist for impact.com; submission is founder-only |
| Offers validated | 1 (`systeme.io`) with live pricing and program terms cited; 2 pipeline candidates deferred |
| Content assets published | **0.** 1 draft at `NOT_PUBLISHED` |
| Traffic | **0 qualified clicks.** 29 historical click rows, all null referrer |
| Commissions | **0.** No real commission record exists |
| Payouts received | **$0** |
| Founder-only actions identified | impact.com registration; Amazon Associates tag; any publication; any outbound message |

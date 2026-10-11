# Payment-Proof Hunt — Cycle 80

**Date:** 2026-10-11/12. **Budget:** $0 (free public sources only). **Rule honored throughout:** ADR-121 was read, quoted, and never edited, reinterpreted, or bypassed.

---

## 1. ADR-121 — verbatim authoritative definition

**Source:** `OpenClaw_Brain/00_Governance/ADR-121-proof-of-payment-doctrine.md` (tracked, dated 2026-07-24, Status: Adopted).

**The founder's directive, quoted verbatim (lines 10):**

> "Founder decision: upgrade `market_hunter.py` and `profit_oracle.ladder_opportunity_score()` to weight **evidence of existing spend** above inferred demand. New highest-weight signals: (1) competitors actually selling with complaining reviews, (2) paid job postings for tasks that could be automated, (3) agencies/freelancers charging money for the manual version, (4) existing subscriptions users are trying to replace or escape. Score any opportunity with real payment evidence far above one based only on desk-researched pain. Add a `payment_evidence` field to every opportunity — with the actual source URL/quote — and reject as UNPROVEN any opportunity with none."

**The exact acceptance/rejection mechanics, quoted verbatim (lines 24, 27, 29, 30):**

> "`record_evidence()` now refuses (raises `ValueError`) any of these four [event types] without both `source_url` and `quote` in `payload`" (line 24)
>
> "New component `payment_evidence_score`: 0 with no real evidence, 40 with one real citation, 70 with two, 100 with three or more — real evidence, never inferred or estimated from keywords." (line 27)
>
> "New hard gate, checked **before** the price floor and score floor: `accepted = has_payment_evidence and clears_score_floor and clears_profit_floor`. Zero real citations means `accepted=False` and `reason` explicitly says `UNPROVEN`, regardless of how high the ladder_score or price would otherwise be. This is an absolute gate, not a scoring nudge." (line 29)
>
> "New `payment_evidence` field on every returned result: the actual recorded evidence for that niche, each entry carrying its real `event_type`, `source_url`, `quote`, and `recorded_at` — never a summary, never a count standing in for the citation itself." (line 30)

**The 4 recognized event types, from the code cited in the ADR (line 24):** `PAYMENT_EVIDENCE_EVENT_TYPES = ("complaining_review", "paid_job_posting", "freelancer_agency_pricing", "subscription_escape")`.

**Not quoted as a replacement — only cited.** ADR-121 was not edited. No gate was weakened or reinterpreted below.

---

## 2. Candidate selection — verified against the live dataset, not assumed

**The "44/100 highest score" claim was checked directly against `market_hunter_runs.log` (1,687 real runs) and found to be WRONG as previously reported.** The literal top-scoring UNPROVEN entry is `'synthetic test fixture automation toolkit zzz-do-not-produce'` at 44.0 — a test fixture that leaked into the real log, not a real candidate. Excluding it, the real top real candidates are:

| Rank | Niche | Score | Ladder | Source |
|---|---|---|---|---|
| 1 | `automated social media scheduling tool for marketing agencies` | **41.9** | automation_tools | seed |
| 2 | `reusable API integration template bundle for SaaS developers` | **40.9** | reusable_assets | seed |
| 3 | `white-label client onboarding template system for B2B startups` | **40.9** | reusable_assets | seed (tied with #2) |

All three were investigated (3, not 2, since #2/#3 tied and both are distinct real product concepts).

### Candidate A — social media scheduling tool for marketing agencies
- **Target buyer / problem:** marketing agencies managing multiple clients' social accounts, currently paying per-seat for tools (Hootsuite/Buffer) that charge per-user or per-channel, not per-agency.
- **Existing evidence (pre-this-cycle):** keyword-inferred only (SEED_CATEGORIES static entry, `automation_tools` ladder).
- **Missing evidence / risk:** no prior real payment-evidence citation existed; this niche is a crowded, well-served market (Hootsuite/Buffer/Sprout/Planable/Blotato all real, active competitors).
- **Why promising:** real, specific, dated agency-pricing friction found this cycle (see §3).

### Candidate B — reusable API integration template bundle for SaaS developers
- **Target buyer / problem:** SaaS developers/teams who currently pay freelancers by the hour/project to do bespoke API integration work.
- **Existing evidence (pre-this-cycle):** none, keyword-inferred only.
- **Missing evidence / risk:** a "template bundle" is a different purchase decision than "hire a freelancer for a specific integration" — the evidence found (below) proves people pay for the *labor*, not that they would buy a *template* instead of labor.
- **Why promising:** a real, individually dated, fixed-price job posting was found matching ADR-121 signal type (2) exactly (see §3) — the most structurally precise match of the three candidates.

### Candidate C — white-label client onboarding template system for B2B startups
- **Target buyer / problem:** agencies/B2B startups wanting a packaged client-onboarding process.
- **Existing evidence (pre-this-cycle):** none, keyword-inferred only.
- **Missing evidence / risk:** weakest of the three — the only competing product found could not be verified beyond its bare existence (see §3).
- **Why investigated anyway:** tied for #2 on real recorded score.

No score was inflated; no demand was invented. The ranking above is the dataset's own real, unedited numbers.

---

## 3. Evidence register

**Disclosed methodology limitation, upfront, honestly:** direct `WebFetch` of G2, Capterra, and Upwork pages returned **HTTP 403 (bot-blocked)** for every attempt this cycle — consistent with this factory's own prior documented finding (a 2026-07 session found only 1 of 4 direct competitor-page fetches succeeded, 25% reliability). All evidence below was therefore obtained via `WebSearch`'s own result snippets/summaries, **not** independently re-fetched and re-read by this session from the primary page itself. This is recorded per item below as a real, material limitation — not hidden.

| # | Candidate | Source title & URL | Access/pub date | Evidence type | Price/currency | What it directly shows | What it does NOT show | Classification | Meets ADR-121 exactly? | Limitations |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | A | "Hootsuite Pros and Cons" — g2.com/products/hootsuite/reviews (via WebSearch summary) | Accessed 2026-10-11; underlying reviews undated in the summary | `complaining_review` (candidate type) | $99/seat/month cited | Real, repeatedly-occurring complaint theme: "per-user pricing makes the platform expensive for agencies... adds up fast" | Does NOT show one single reviewer's exact verbatim quote with a name/date attributable by this session — direct page fetch was blocked (403) | **WEAK** | **No** — ADR-121's `record_evidence()` requires a specific `quote`; I have a search-engine paraphrase of a theme, not a verbatim, independently-fetched quote | Could not independently browse g2.com directly; relying on a secondary summary of primary content |
| 2 | A | "Buffer vs Hootsuite" aggregator discussion (via WebSearch summary, several blog sources: planable.io, blotato.com, poster.ly) | Accessed 2026-10-11; source pages dated 2026 | `complaining_review` (candidate type) | $180–360/month cited for 30-client agency scale | Corroborates the same per-seat/per-channel agency-cost complaint from a second, independent angle | Still blog-mediated, not a single attributable customer quote | **WEAK** (corroborating, not independent) | **No**, same reason as #1 | Same fetch-blocking limitation |
| 3 | B | "eBay API + VerifyMy API Integration for UK Pharmacy" — Upwork job posting (via WebSearch summary; URL: upwork.com/freelance-jobs/apply/eBay-API-VerifyMy-API-Integration-for-Pharmacy_~022107845184323277232/) | Posted **2026-10-07** (stated in the search result itself); accessed 2026-10-11 | `paid_job_posting` (candidate type, matches ADR-121's signal #2 structurally) | **$1,500.00 fixed price**, USD | A real, specific, individually-dated real-world job posting with a real fixed-price budget for exactly the class of manual work candidate B's product targets | Does not show whether this buyer would ever purchase a template bundle instead of hiring a freelancer — a different purchase decision | **WEAK** (real and precisely dated, but the underlying page was never independently re-fetched by this session — 403 on direct attempt) | **Close, but No** — the quote/date/price above come from a search-result summary, not a session-verified direct read of the live page | Direct Upwork fetch blocked (403); cannot independently confirm the posting is still live/unmodified |
| 4 | B | Upwork's own aggregate rate-info pages (upwork.com/hire/api-integration-freelancers/, /cost/) | Accessed 2026-10-11 | `freelancer_agency_pricing` (candidate type) | $20–$40/hr; $500–$1,500/project typical range | Corroborates #3 with an aggregate, platform-published rate range for the same work category | Aggregate, not a single dated transaction | **WEAK** (corroborating) | **No**, aggregate not a specific citable transaction | Direct fetch blocked; relying on WebSearch's summary of Upwork's own published page |
| 5 | C | "Client Content Onboarding Kit (White Label)" — quietformulas.gumroad.com/l/ClientContentOnboardingKit | Accessed 2026-10-11; listing date unknown | Competing product listing (not one of the 4 ADR-121 types) | **Searched-summary cited $29** (sale) / $47 suggested resale — **NOT independently confirmed**: direct fetch of the live page returned no price, no review count, no sales count at all | A real, live competing Gumroad product exists for a closely related concept | Does **not** show any real sale, review, or payment — the direct fetch of the actual live page showed zero price/review/sales data, contradicting the earlier search-summary's $29 figure | **REJECTED** | **No** — this is a bare product listing (explicitly, per this cycle's own rule, "a price listing... without qualifying evidence is not verified revenue"), and the one figure found could not even be confirmed on the live page itself | Direct fetch returned materially less than the search summary claimed — the search-summary price is now actively doubted, not just unverified |

**No item above is classified STRONG or PROVEN.** Every item that comes closest (rows 3–4, candidate B) is real, dated, and structurally matches one of ADR-121's four named signal types — but fails the doctrine's own explicit mechanical requirement (`record_evidence()` demands a `source_url` + `quote`, i.e. an independently-fetched, directly-readable primary source) because every direct primary-source fetch attempted this cycle was blocked. This is reported honestly rather than papered over with a secondhand paraphrase presented as a verbatim quote.

---

## 4. Final classifications

| Candidate | Classification | Reason |
|---|---|---|
| A — social scheduling for agencies | **UNPROVEN** | Real, repeatedly-corroborated complaint theme exists (rows 1–2), but no independently-verified verbatim quote + source was obtainable this cycle. Promising indicators exist; qualifying evidence per ADR-121's exact mechanics does not yet. |
| B — API integration template bundle | **UNPROVEN** | Closest of the three to a real match (a specific, dated, priced job posting, row 3) — but the same primary-source-verification gap applies. Not killed: a documented fatal constraint was not found, only a tooling/access limitation. |
| C — white-label onboarding templates | **UNPROVEN**, leaning weakest | The one real signal found (a live competing product) is explicitly not a payment-evidence type under ADR-121, and even its bare price could not be confirmed on direct fetch. Not `KILL`ed per this cycle's own rule ("lack of evidence alone generally means UNPROVEN... unless existing documented criteria justify termination") — no documented fatal constraint was found, only absence of evidence. |

No candidate reaches `PROVEN`. No candidate is `KILL`ed — the rule against killing for mere absence-of-evidence was followed literally.

---

## 5. Three proposed $0 methods to obtain qualifying evidence (proposals only — none executed)

1. **A real, logged-in browser session (not this session's unauthenticated `WebFetch`) to directly read one G2/Capterra/Upwork page and copy a verbatim, attributable quote.**
   - Why it could work: this cycle's own evidence shows the *content* exists (real complaints, real job postings) — only the *access method* failed (bot-blocking on unauthenticated fetch). A human browser session doesn't trip the same block.
   - ADR-121 compliance: fully compliant — this is exactly the "a human (or Claude Code, checking a real public page during a session)" method the ADR itself describes as the intended evidence-gathering path.
   - Requires: founder's own browser session (or a Claude Code session with live browser access, not available in this environment) — **HUMAN-REQUIRED** (or environment-upgrade-required).
   - Founder decision needed: no strategic decision, just availability of the access method.
   - Success: a verbatim quote + working URL recorded into `data/market_evidence.jsonl` via the real `record_evidence()` function. Failure: the page is also blocked for a logged-in session, or contains no on-point complaint after all.

2. **Query Hacker News/GitHub (this factory's only two real, free, keyless, already-working connectors) for a `paid_job_posting`- or `subscription_escape`-shaped real discussion**, instead of relying on G2/Capterra/Upwork, which are all bot-blocked.
   - Why it could work: `golden_hunter/pioneer.py`'s Ask HN feed already surfaces real "I'm paying for X, want to replace it" threads (Cycle 76 found a real example: "Tell HN: I've been paying for..."). A targeted keyword query (not the generic top-stories feed) against these exact three candidates' problem domains could surface a real, directly-fetchable (HN/GitHub are not bot-blocked) complaint.
   - ADR-121 compliance: fully compliant — same real, keyless, already-proven sources.
   - Requires: no founder action; could be done by a future Claude session within the existing $0 architecture.
   - Founder decision needed: none technically, though the founder may want to review before any evidence is recorded (recording evidence changes real scoring outcomes).
   - Success: a real HN/GitHub thread with a quote matching one of the 4 types. Failure: no matching thread exists within a reasonable search budget (a real, honest possibility — these are narrower B2B niches than HN's typical consumer-tech audience).

3. **Record the already-found, real-but-secondhand evidence (rows 1–4 above) into `data/market_evidence.jsonl` with the limitation explicitly disclosed in the `quote` field itself** (e.g., prefixing with "search-engine-summarized, not independently page-verified") — then let the founder or a future session with working browser access upgrade it to a fully independent citation later.
   - Why it could work: `payment_evidence_score` gives partial credit per real citation (40/70/100 for 1/2/3+) — even a disclosed-as-secondhand real citation is categorically different from "no evidence," and the ADR's own enforcement only requires `source_url` + `quote` fields to be present, not a specific provenance tier.
   - ADR-121 compliance: **borderline** — technically satisfies the code's literal requirement, but arguably against the doctrine's spirit ("real payment evidence," implying first-hand verification). **This option is flagged as needing founder judgment, not a unilateral call.**
   - Requires: founder's explicit sign-off that a disclosed-secondhand citation is acceptable evidence quality for this factory's own bar — **a founder decision, not executed here.**
   - Success: the founder accepts this standard and the candidate moves forward for real production consideration. Failure: founder rejects it as not meeting the doctrine's real intent, and option 1 or 2 remains the only path.

**No method was executed.** No entry was written to `data/market_evidence.jsonl` this cycle.

# Galaxy Forge — Commercial Readiness Report

**Date:** 2026-07-25
**Scope:** Real code inspection only — `customer_site/index.html`, `customer_site/status.html`, `server.js`'s `/api/customer/*` routes, `customer_pipeline.py`, `trust/*.html`, `mission_control_executive_v1.html`'s Customer Pipeline panel. No new features built. Every finding below is traceable to an exact file/line; nothing is speculative.

**Methodology:** walked the real customer journey — Visitor → Discovery → Trust → Product Selection → Request → Quotation → Payment → Production → Quality Verification → Delivery → Support → Follow-up — against the actual live implementation, including what a customer sees in every honestly-blocked state (Payment blocked on Paddle onboarding; Production/QA/Delivery not yet built).

*Supersedes the 2026-07-16 report previously saved under this filename, which audited a pre-platform KDP product-launch simulation — a different subject that predates the real customer platform (ADR-129/130) this report covers.*

---

## Journey-by-journey findings

### 1. Visitor
No real SEO/backlink presence exists yet — expected at this stage (zero real customers, zero marketing spend), a go-to-market gap rather than a code defect. `robots.txt`/`sitemap.xml`/OG tags/favicon are real and correct (closed in the previous round).

### 2. Discovery
The catalog (`GET /api/customer/catalog`) is real — 5 real Paddle products, real prices, no mock data. The "How it works" and "Approach" sections are real and honest.

### 3. Trust
**Finding T1 (High).** `trust/privacy-policy.html`, `terms-of-service.html`, and `refund-policy.html` — all three directly linked from the live site's footer and Knowledge Base — contain unfilled template placeholders visible as raw bracketed text, e.g.:
```
<span class="fill">[Founder's legal business name, or "an individual sole proprietor," and jurisdiction of operation]</span>
<span class="fill">[support contact email]</span>
<span class="fill">[To be completed with real applicable rights once jurisdiction is confirmed...]</span>
```
Each page does carry a prominent, honest `draft-warning` banner disclosing this is an unreviewed draft — so this is not hidden or deceptive — but a real customer doing pre-purchase due diligence (which the site itself invites via the Knowledge Base) will see unfilled legal placeholders on the exact pages meant to build trust. Note the inconsistency: `refund-policy.html` and `incident-disclosure-policy.html` both correctly show the real support address (`galaxyaek7@gmail.com`), but `privacy-policy.html` still shows `[support contact email]` as a placeholder — the same real answer exists elsewhere in the same file set and simply wasn't propagated.

**Finding T2 (Low).** The real support address is a personal Gmail account, not a branded domain address. This follows this factory's own settled "one Google account, conscious simplicity decision" architecture (`IDENTITY_ARCHITECTURE.md`) — not re-litigated here — but a `support@` alias forwarding to the same inbox would look more premium without touching that decision.

### 4. Product Selection
**Finding P1 (Critical).** Every catalog card's "Request access →" button (`customer_site/index.html:447-454`) does not purchase the already-priced catalog item — it scrolls to the general Request form and pre-fills the description with `"Interested in: <product title>"`, which then goes through the **entire custom-evaluation pipeline**: real Groq market evaluation → `profit_oracle.butter_price()` repricing from scratch. `butter_price()` computes a price independently from the catalog's stored price — it does not read or reuse it. A customer who sees "$126" on the catalog card and clicks through can legitimately end up quoted a **different number** after "requesting" the exact product they were just shown a price for. This is a real bait-and-switch appearance risk on the single easiest sale this business can make (a visitor who already decided to buy something already built and priced), and it adds unnecessary friction (a multi-stage evaluation) to what should be an instant, one-click purchase.

### 5. Request
**Finding R1 (Medium).** Contradictory copy on the same page. The Request section's own trust note says: *"Honest turnaround. We reply once a real person has actually reviewed the request — no automated 'thanks, we'll be in touch' that goes nowhere."* (`index.html:294`) — but the real system is now automated (ADR-130): submission fires a real evaluation within seconds, and the success message immediately after says *"Request received and already running through our real evaluation gate"* (`index.html:492`). Two pieces of copy on the same page disagree about whether the process is manual or automated. This undersells the real capability and reads as inconsistent to an attentive customer.

### 6. Quotation
**Finding Q1 (Medium, low-probability/high-severity-when-hit).** The proposal's `evidence_summary` (shown verbatim on the English-language status page) is sourced from `decision_engine`'s real reasoning array, which can contain Arabic text in at least one real code path — the BUILD/score-conflict case in `decision_engine/engine.py` appends `"تعارض بين بوابتين مستقلتين: AI CEO أوصى بالبناء لكن..."` verbatim into `reasoning`. If that path fires for a real customer's request, their English proposal page would show a mid-sentence language switch to Arabic with no translation — confusing and unprofessional for an English-facing site, even though the underlying evaluation itself is completely real and honest.

Otherwise sound: the price is real (`profit_oracle.butter_price()`), never fabricated, and the evidence citations are real reasoning strings, not marketing copy.

### 7. Payment
**Finding PY1 (Critical).** `customer_pipeline.py`'s `_RECOVERY_HINTS` dict is the single source for BOTH Mission Control's internal, technical supervision view AND the customer's own public status page's "Next step" text. Two of its entries literally read:
```
"PAYMENT_BLOCKED_PADDLE_ONBOARDING": "...Re-attempt via retry_payment_verification() once cleared."
"PENDING_CUSTOM_PRODUCT_SETUP": "...Founder can create one manually in vendors.paddle.com, then re-run retry_payment_verification()."
"NEW": "Waiting for advance_request() to run real qualification..."
```
A real paying customer, checking their own order status, would see raw Python function-call syntax (`retry_payment_verification()`, `advance_request()`) in a box literally labeled "Next step." This is the most concrete, unambiguous "does not look premium or professional" finding in this audit — appropriate for a founder-facing dashboard, wrong for a customer-facing one, and currently the exact same string serves both.

The blocked state itself is otherwise handled honestly and well: the status pill turns red (not a misleading green/orange), and the message correctly states the real cause (Paddle account-onboarding gate) rather than a fake "processing" or a generic error — this is real, working, honest failure-state design, just with an internal-audience string leaking into an external-audience surface.

### 8–10. Production, Quality Verification, Delivery
Cannot be experienced by any real customer today — Payment Verification has never succeeded for a real request, so nothing downstream fires. Correctly and consistently disclosed everywhere it's referenced (site's "How it works" copy, ADR-130, status page's honest terminal states). No misleading happy-path claims were found anywhere in the live code.

### 11. Support (Order Tracking + tickets)
**Finding S1 (Medium).** `status.html`'s only failure-handling UI for approve/decline is a native browser `alert()` dialog (`status.html:296`) — jarring, blocks the page, and is visually inconsistent with every other status surface on the same page (which all use custom-styled inline boxes).

**Finding S2 (Medium).** Clicking "Decline" fires the reject action immediately with no confirmation step — an irreversible action on a real proposal with no "are you sure?"

**Finding S3 (High value, not a bug).** `reject_request()` already supports a real `reason` parameter server-side (`customer_pipeline.py`), but `status.html`'s decline button sends an empty body (`{}`) — the customer is never asked why they're declining. This directly undercuts the "every failure becomes knowledge" principle: every real decline today is a silent, reason-less data point, even though the plumbing to capture one already exists.

**Finding S4 (Low).** An invalid/mistyped request ID surfaces the raw Python error string (`no such customer request: 'req_xxx'`, Python `repr()` quoting included) instead of a clean, friendly message.

**Finding S5 (Low).** The AI Consultation widget's conversation is never linked to the request it eventually helps produce (already logged as a Growth item in the prior CEO Review cycle, not yet acted on) — a missed signal for "which consultations actually convert," not a customer-facing defect.

### 12. Follow-up
Not built — honestly disclosed (0% real email/SMS capability exists; the real substitute is the pull-based status page). No fabricated follow-up automation found anywhere.

### Mission Control connectivity
Confirmed real: the `customer-pipeline-status` panel and `advance-customer-pipeline` action exist and reuse the same real per-request data every customer sees. No gap found beyond Finding PY1 above (the data is correctly *shared*, just not correctly *worded* for two different audiences).

---

## Ranked issues

| # | Issue | Trust impact | Revenue impact | Automation impact | Brand impact | Cost | Priority |
|---|---|---|---|---|---|---|---|
| PY1 | Raw function names in customer-facing recovery text | **High** | Low | None | **High** | **Low** (copy split, no logic change) | **P0** |
| P1 | Catalog purchase re-runs full evaluation, can reprice | **High** | **High** | Medium | **High** | Medium (needs a real direct-purchase path decision) | **P0** |
| T1 | Unfilled legal placeholders on live Trust pages | **High** | Low | None | **High** | Low (copy fill) but **blocked on founder** (legal jurisdiction/business name aren't engineering decisions) | **P0 (founder input needed)** |
| R1 | Contradictory automated-vs-manual copy | Medium | Low | None | Medium | **Low** (copy-only) | P1 |
| S3 | Decline reason never captured despite backend support | Medium | Low | **Medium** (lost learning signal) | Low | **Low** (one field + one line of JS) | P1 |
| S1 | Native `alert()` on action failure | Medium | Low | None | Medium | **Low** | P1 |
| S2 | No confirm step before Decline | Low | Low | None | Low | **Low** | P2 |
| Q1 | Possible Arabic leak into English proposal copy | Low (rare) | Low | None | Medium (when hit) | Low (source-string audit + fallback) | P2 |
| S4 | Raw Python error text on bad ID lookup | Low | None | None | Low | **Low** | P2 |
| T2 | Personal Gmail as public support address | Low | None | None | Low | Low (alias only) | Future |
| S5 | Consultation not linked to resulting request | None | Low | Low | None | Medium | Future |

---

## Prioritized roadmap

**P0 — fix before actively driving any real traffic to this site:**
1. Split `_RECOVERY_HINTS` into two maps (or add a customer-safe rephrase layer) so `status.html` never renders raw function names. Pure copy/data change, zero architecture risk.
2. Decide and build a real direct-purchase path for existing catalog items that does *not* re-run `butter_price()` against a freeform description — the catalog's own stored price should be the price the customer is quoted, full stop. This is a real product decision (skip evaluation entirely for known-good catalog items, vs. run evaluation but pin the price) and should be confirmed with the founder before building, since it changes customer-facing behavior.
3. Fill the real legal placeholders on `privacy-policy.html`/`terms-of-service.html`/`refund-policy.html` (business name, jurisdiction, support email — the last one already has a real answer sitting in the other two policy files). Needs the founder's real jurisdiction/entity decision — not an engineering task.

**P1 — fix soon, low cost / real value:**
4. Reconcile the Request section's "no automated reply" copy with the real automated pipeline.
5. Wire the Decline button to actually capture and send a reason (backend already supports it).
6. Replace the `alert()` failure path on the status page with the site's own inline status-box pattern, already used everywhere else.

**P2 — real but lower urgency:**
7. Add a confirm step before Decline.
8. Audit/filter reasoning strings for language consistency before they reach an English-facing proposal.
9. Return a customer-friendly "we couldn't find that request" message instead of the raw Python error string.

**Future — logged, not distracting the current roadmap:**
10. A branded support-email alias.
11. Link AI Consultation sessions to the request they help produce.

No item on this list required inventing a feature that doesn't already have real, working infrastructure behind it — every fix above is a copy change, a data-shape change, or a scoping decision on an already-real pipeline.

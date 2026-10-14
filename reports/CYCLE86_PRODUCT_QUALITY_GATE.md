# CYCLE 86 — PRODUCT QUALITY GATE · EU AI ACT COMPLIANCE TOOLKIT

**Date:** 2026-10-14 · **Spend:** $0 · **Verdict:** 🔴 **HOLD — DO NOT MARKET**

---

## 1. TOOLS THAT ALREADY EXISTED (reused, not replaced)

The factory already had a large quality toolchain. None of it was rebuilt.

| Tool | What it does | Reused how |
|---|---|---|
| `product_claim_integrity.py` (Cycle 81) | Does the delivered payload match the marketing claim? | **Ran first.** Confirmed both PDFs real. Its limit is the finding below. |
| `inspectors.py` | Dual-inspection QA gate | Reused as-is |
| `executive_quality_gate.py` | 23 rejection checks incl. legal-safety, copyright, brand | Reused as-is |
| `scripts/verify_delivery_integrity.py` | Byte/SHA-256 fetch-verify across the catalog | Source of the file-completeness score |
| `truth_first.py`, `brand_dna.py` | Canonical vocabulary, brand enforcement | Referenced for scoring language |

**The gap that justified exactly one new tool** is stated in §3.

---

## 2. THE DEFECT — found by actually reading the shipped bytes

I extracted and read all 31 pages of the PDF that buyers actually receive
(`books/eu_ai_act_compliance_toolkit_v2.pdf`, sha256 `18c41583…`, the file
whose length and hash match the verified attachment in `data/delivery_integrity.json`).

### 2.1 CRITICAL — fabricated Annex III categories, presented as literal citations

The shipped document states, on page 18:

> "Annex III, Part A, category 1: Autonomy"
> "Annex III, Part A, category 2: Creativity and adaptability"
> "Annex III, Part A, category 3: Real-time data and physical interaction"
> "Annex III, Part A, category 4: Significant adverse impact"

**None of these are Annex III categories.** The European Commission's own AI
Act Service Desk lists exactly eight, and "autonomy" is not among them:

1. Biometrics
2. Critical infrastructure
3. Education and vocational training
4. Employment, workers' management and access to self-employment
5. Access to and enjoyment of essential private services and essential public services and benefits
6. Law enforcement
7. Migration, asylum and border control management
8. Administration of justice and democratic processes

Sources: `ai-act-service-desk.ec.europa.eu/en/ai-act/annex-3` and
`…/high-risk-ai-listed-use-cases`.

This is not a style error. It is fabricated text wearing the citation of the
European Union's primary legislation, in a product sold **specifically** on
regulatory accuracy, to **customers whose entire reason to buy is regulatory
accuracy**.

### 2.2 CRITICAL — Annex III has no "Part A" / "Part B"

Asserted 7 times (pages 13 and 19). Page 26 compounds it: *"Limited-risk AI
systems in Annex III, Part B are subject to lower penalties."* That division
does not exist.

### 2.3 CRITICAL — a prohibition the Act does not contain

Page 17, Chapter 8: *"Prohibit the use of high-risk general-purpose AI
models."* The AI Act contains no such prohibition. GPAI models carry Chapter V
obligations.

### 2.4 MAJOR — the substantive chapters are padding

The nineteen content chapters run **47–115 words each, median 72**. Each is a
five-bullet list of the shape *"Establish clear X. Develop Y. Implement Z.
Regularly review W. Maintain records."* For a $155 product this is the exact
pattern the standard forbids: *"do not produce large bundles of generic content
just to increase size."*

### 2.5 MAJOR — verification stamp is 68 days stale

*"verified 2026-08-06"* against today 2026-10-14, in a fast-moving regulatory area.

### 2.6 MINOR — presentation defects visible to buyers

12 literal `**bold**` markdown markers survived into the rendered PDF (glossary and FAQ). TOC entries truncated mid-word: "A Decision-Tree Chec…", "…for Limited-Ri…".

### 2.7 What is *not* wrong

- Page 1 is an image cover (1600×2560), not a blank page — verified.
- The corrected deadline is **right** and independently corroborated by three unrelated sources (§4).
- The "Not Legal Advice" disclaimer is present, first, and clearly worded.
- Files are real, byte-verified, unencrypted, openable.

---

## 3. WHY NO EXISTING TOOL CAUGHT THIS

`product_claim_integrity.py` answers **"does the payload match the promise?"**
It is genuinely load-bearing. It cannot answer **"is the content itself true?"**

Nothing in the factory had a mechanical check for a *fabricated legal citation*
in a shipped file. That is a real, proven gap — one new tool, not a suite.

**New tool:** `product_content_integrity.py` (cost: $0, pure offline, no network, no new dependency).

Nine rules, each evidence-returning: `FABRICATED_CITATION`, `INVENTED_STRUCTURE`, `FALSE_PROHIBITION`, `AI_ARTIFACT`, `UNSUPPORTED_PROMISE`, `MARKDOWN_LEAKAGE`, `TRUNCATED_HEADING`, `CONTENT_PADDING`, `STALE_VERIFICATION`. It checks citations against a reference table transcribed from the EC source — not against a keyword vibe.

It also exports `legal_review_required()`, which is always `True` for regulatory products, so no caller can present a mechanical pass as clearance.

### Two bugs I found in my own new tool, and fixed

1. **`CONTENT_PADDING` silently never fired.** It used the *mean*; four long reference chapters inflated it to 112 words on a document whose real median is 72, so it reported nothing. A rule that cannot fire looks identical to a working one. Now uses the **median**; floor raised to 150.
2. **`UNSUPPORTED_PROMISE` false-positived on the product's own disclaimer** — "does *not* guarantee compliance" matched. Now excludes negated forms. A gate that cries wolf on a disclaimer protects nothing.

Both were caught by `tests/test_product_content_integrity.py`, which asserts each rule **fires** on a known-bad sample rather than merely returning a verdict.

---

## 4. SCORECARD (100 pts)

| Dimension | Score | Evidence |
|---|---:|---|
| Content correctness & sources | **2 / 25** | Fabricated Annex III categories cited as regulation text (2.1–2.3) |
| File completeness & usability | **25 / 25** | Both PDFs fetched, hashed, parsed, size-matched |
| Practical value & customer fit | **7 / 20** | Median 72 words/chapter; five-bullet padding (2.4) |
| Independent verification & tests | **5 / 15** | Automated gate now exists; **no qualified human legal review has ever occurred** |
| Commercial presentation & accuracy | **12 / 15** | Literal `**markdown**`, truncated TOC |
| **TOTAL** | **51 / 100** | |

### DECISION: **HOLD**

Threshold is 90. Score is 51. But the decisive rule is not arithmetic: **any critical failure means HOLD regardless of total.** Eleven critical defects are open. A 95 would not rescue fabricated citations.

---

## 5. WHAT PASSED AND WHAT DID NOT

**PASSED (1 of 1 priority products):** none passed. The single product Phase 5 required inspection failed.

**Correctly still-standing:** file integrity (25/25), the disclaimer, and the corrected deadline — which is now corroborated by three independent sources:

- `euai-act.com` — "Regulation (EU) 2026/1744 … defers … high-risk regime: **2 December 2027** … Annex III (previously 2 August 2026)"
- `aicomplyapp.eu` — "Annex III start on **December 2, 2027** — Regulation (EU) 2026/1744 moved them."
- `regulation-ai.eu` — confirms Art. 50 transparency live from 2 Aug 2026 while high-risk is deferred.

The deadline correction this factory made **before selling anything** was right. The risk classification content around it is fabricated.

**Untested:** the other 78 products were not inspected. Three more EU AI Act listings carry the same name and were produced by the same pipeline — they are the highest-risk next target.

---

## 6. IMMEDIATE ACTIONS TAKEN

1. **Built** `product_content_integrity.py` + **29 tests** (13 subtests) — all pass.
2. **Placed the product on HOLD**, recorded in `data/cycle86_content_gate.json`.
3. **Quarantined `customer_site/affiliate-program.html`** — the recruitment page built last cycle now carries a red DO-NOT-PUBLISH banner naming the defect. It is retained as a record, not deleted.
4. **Left prices, product listings, payouts and Gumroad state untouched.** Unpublishing the listing is a founder decision (see §8).

---

## 7. TOOLING PROPOSED

| Tool | Gap it fills | New cost |
|---|---|---|
| `product_content_integrity.py` | Fabricated/invented legal citations in shipped files | **$0** |
| `scripts/cycle86_content_gate.py` | Runs the gate + emits the scorecard | **$0** |

Nothing else proposed. No purchase, no subscription, no new API, no new dependency.

**Automatable now:** citation checking, padding detection, markdown leakage, stale-stamp detection, guarantee language.
**Founder-only:** human legal review, any unpublish/reprice decision.

---

## 8. BLOCKERS REQUIRING THE FOUNDER

1. **The content must be rewritten**, not patched. The Annex III classification material has to be replaced with the eight real categories, sourced and cited. The GPAI chapter and the "Part A/B" claims need correction.
2. **Qualified human legal review** before this product is ever marketed. The standard says automated evaluation does not replace specialist human review where risk demands it — this is the clearest possible case.
3. **Decide whether to unpublish the Gumroad listing** now. It is live and purchasable at $155 with 0 sales, so no buyer has been harmed yet — which is exactly the cheap moment to act.
4. **Check the three sibling EU AI Act listings** ($29 / $19 / $9) for the same fabricated categories.

I did not unpublish, reprice, or alter the listing. Those are your calls, not mine.

---

## 9. NEXT MOST-USEFUL COMMERCIAL STEP

**Not more marketing. It is impossible to market this honestly today.**

The ordered next moves:

1. **Rewrite the classification content from the primary source** (EC AI Act Service Desk / EUR-Lex), with real citations. I can do this; it needs no spend and no permission beyond doing it.
2. **Run the new gate across the other three EU AI Act listings** before assuming they are fine — same pipeline, likely same defect.
3. **Sweep the catalog** for other regulatory products (CCPA, GDPR, SOC 2, FTC, GPSR) — they were generated by the same process and carry the same risk of invented legal citations.
4. **Only then** revisit the affiliate programme. Recruiting marketers to a document that misstates EU law is the failure mode this whole standard exists to prevent.

---

## PROOF RULES

- Every finding above quotes text extracted from the shipped file, with page numbers.
- The Annex III correction is sourced to the European Commission's own service desk, not to a competitor blog.
- No sale, revenue, review or demand is claimed. `VERIFIED_REVENUE` remains `$0.00`.
- Spend this cycle: **$0**.
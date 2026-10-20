# Cycle 107 — Regulatory Opportunity Discovery

**Date:** 2026-10-20 · **Spend:** $0.00 · **Publication:** not attempted, `FACTORY_LIVE_PUBLISH=false` unchanged
**Starting state:** `0cab561`, clean for this cycle, doctrine 9/9 ok, 53 doctrine tests passing
**Verdict: NO QUALIFIED CANDIDATE**

Three regulatory opportunities were examined against authoritative sources and live competitor artefacts. None
passed the hard gates. EUDR — the strongest — was rejected this cycle rather than deferred, because the gate
that now applies is stricter than the one used in Cycle 106.

---

## 1. What Cycle 106's evidence actually proved

Every URL from the two Cycle 106 discovery records was re-fetched (`EVIDENCE_VERIFICATION_2026-10-20.json`,
29 unique URLs, full status table). The rejections survive, but on narrower evidence than claimed:

| Defect | Detail | Effect |
|---|---|---|
| V1 dead URL | `depositbackr.com/tools/...` → **404** | One of two free-substitute citations is gone; Quire Paper ($12, live) still decides it |
| V2 DNS failure | `capveri.com`, `lextract.io` do not resolve | Two CAM competitors now **UNVERIFIED**; Sheet Chief and leaseabstracts.com still decide it |
| V3 blocked source | Four Reddit threads return **403** to a plain client and serve a block page | The "OBSERVED customer complaint" label was wrong. They are **UNVERIFIED** |

Three evidence classes were conflated in Cycle 106 and are separated here:

- **Verified purchases:** none exist. Zero sales anywhere in this factory.
- **Verified competitor artefacts:** real, and the strongest evidence available. Quire Paper, Sheet Chief,
  leaseabstracts, six COI templates, SawmillSmart and polygon-one all returned 200 with substantive content.
- **Customer complaints:** not verified. No fetched copy of a Reddit thread was retained.

The correct conclusion from Cycle 106 is narrower than "customers complain and will pay." It is: **free and
cheap competitors demonstrably exist and are current**, which is sufficient to reject a me-too product without
any demand inference at all.

---

## 2. Candidates examined this cycle

### CANDIDATE 1 — EUDR operator/downstream register (re-examination of the deferred probe)

**Jurisdiction / buyer:** EU importers and traders of in-scope commodities (coffee, cocoa, palm, rubber, soy,
cattle, wood).
**Instrument:** Regulation (EU) 2023/1115 as amended by (EU) 2025/2650.
**Dates, verified live this cycle:** large and medium operators **30 December 2026**; micro and small
**30 June 2027**; micro/small already under the EUTR **30 December 2026**. Due diligence now sits with the
first operator placing on the market; downstream operators and traders no longer submit their own statement.
Source: `https://environment.ec.europa.eu/topics/forests/deforestation/regulation-deforestation-free-products_en` (200).

**Operational task:** collect supplier declarations and plot geolocation, keep five-year records, decide
whether you are the first placer (statement required) or downstream (no statement, records only).

**Free substitutes, verified live:** SawmillSmart publishes a free six-sheet workbook (statement worksheet,
Article 9 checklist, plot geolocation, inbound register, outbound register, supplier form) explicitly updated
for the 2025/2650 amendment — 200. polygon-one publishes a free preparation sheet **plus a free worked coffee
import example** — 200.

**Score: 19/25** (demand 4, WTP 4, differentiation vs market 2, vs catalogue 3, buildability 3, risk 1,
traceability 2).

**Verdict: REJECTED.** It clears the numeric threshold but fails a hard gate this cycle states explicitly:
*"Reject any candidate that is materially duplicated by an adequate free alternative."* For coffee — the
commodity where a non-wood wedge was most plausible — polygon-one already gives away the worked example and the
preparation sheet. The remaining differentiation is commodity-specific phrasing, which is not a product.

Cycle 106 recorded this as DEFERRED for capacity reasons. That label was too generous: the evidence was already
sufficient to reject, and capacity was a second, independent reason. Corrected here.

---

### CANDIDATE 2 — CBAM definitive regime, small importer data collection

**Jurisdiction / buyer:** EU importers of cement, iron/steel, aluminium, fertilisers, hydrogen, electricity.
**Instrument:** Regulation (EU) 2023/956 as simplified by (EU) 2025/2083.
**Dates, verified live:** definitive regime from **1 January 2026**; first annual declaration and certificate
surrender by **30 September 2027** for the 2026 import year; quarterly certificate purchases from 2027;
50-tonne mass threshold; hydrogen and electricity always authorised.

**Operational task:** obtain embedded-emissions data from third-country producers, file an annual declaration,
surrender certificates.

**Free substitutes, verified live from the Commission:** the official quarterly report structure (XLSX), the
corrected default values (XLSX), and the operator communication template with the `Summary_Communication`
worksheet are all published and free. The Commission's own Q&A states the Excel template "is not compulsory but
recommended" and that it takes all source streams, precursors and electricity into account.

**Score: 15/25** (demand 4, WTP 3, vs market 1, vs catalogue 3, buildability 1, risk 1, traceability 2).

**Verdict: REJECTED.** The Commission already supplies the calculation tool, and reproducing embedded-emissions
methodology under Implementing Regulation (EU) 2025/2547 without a verifier's competence would be the exact
"pretending to replace qualified advice" failure this cycle forbids.

---

### CANDIDATE 3 — EU EmpCo green-claims audit (Directive (EU) 2024/825)

**Jurisdiction / buyer:** any EU trader making voluntary environmental claims to consumers, including digital
sellers and marketplaces.
**Instrument:** Directive (EU) 2024/825 amending 2005/29/EC and 2011/83/EU.
**Dates, verified on EUR-Lex:** in force 26 March 2024; transposition due **27 March 2026**; **applies from
27 September 2026**. Generic environmental claims without recognised excellent performance become blacklisted
(Annex I point 4a); uncertified sustainability labels banned; carbon-neutral-by-offsetting claims banned.

**Operational task:** inventory every live claim across site, listings, packaging and social; sort each into
keep / specify / retire; hold evidence for each kept claim.

**Competitors, verified live:** Kilde sells an "EU Green Claims Compliance Kit" — twelve banned points verbatim,
thirteen rewrite patterns, a claim register CSV, substantiation memos, current to 21 August 2026. Conphora runs
it as a platform workflow. EcoClaim offers a **free** scanner against 82 banned terms. greenwashing-checker
publishes a free eight-step SME checklist that already covers the inventory fields. Mallbutiken sells a 33-file
package for 79 SEK, legally reviewed 6 October 2026.

**Score: 16/25** (demand 4, WTP 3, vs market 0, vs catalogue 2, buildability 3, risk 2, traceability 2).

**Verdict: REJECTED.** This is the most crowded of the three. A free scanner and a free checklist cover the
inventory step; a mature paid kit covers the register and rewrite library. Differentiation would be zero.

---

## 3. Hard-gate summary

| Gate | EUDR | CBAM | EmpCo |
|---|---|---|---|
| Authoritative evidence for the obligation | PASS | PASS | PASS |
| Credible buyer problem | PASS | PASS | PASS |
| Not materially duplicated by an adequate free alternative | **FAIL** | **FAIL** | **FAIL** |
| Reliable without paid data | PASS | PASS | PASS |
| No unsupported legal interpretation | **RISK** | **FAIL** | RISK |
| Maintainable at zero spend | PASS | RISK | PASS |
| Differentiated from the catalogue | PASS | PASS | PASS |
| **Result** | **REJECTED** | **REJECTED** | **REJECTED** |

**NO QUALIFIED CANDIDATE.**

The pattern is consistent with the Cycle 106 structural finding and sharpens it: regulators and vendors
themselves now publish the artefact. The European Commission ships the CBAM workbook; a competitor ships a free
EUDR worked example; a vendor ships a free green-claims scanner. In a market where the primary artefact is free
and official, a paid spreadsheet has to sell something other than the artefact — and none of these three has an
identified "something" that the free alternatives leave open.

---

## 4. Why no product was built

The instruction was to build only when evidence passes the gates, and not to manufacture a winner. All three
candidates fail the same hard gate. Building one anyway would require asserting a differentiation the research
does not support — precisely the fabrication this cycle forbids.

Nothing was published, repriced or spent. The B13-001 listing assets from Cycle 106 remain local and
unpublished, awaiting the founder's price and publication decisions.

---

## 5. What would change the answer

A candidate becomes viable when it has at least one of these, verified rather than assumed:

1. **A regulator publishes the obligation but not the artefact** — the operational task exists in guidance
   prose with no official workbook, no free vendor template, and no scanner.
2. **A verified purchase signal** — a real paid transaction for a comparable product, not a marketing page.
3. **A decision the buyer cannot make alone** — a genuine branching determination (which regime applies, which
   role you occupy) that the free artefacts deliberately leave to counsel.

For EUDR specifically, the re-trigger is a commodity where the free worked example does not exist and where the
first-placer/downstream determination is genuinely ambiguous for the buyer. That would need to be verified, not
assumed.

---

## 6. Recommended next task

Do not open a fourth regulatory probe in the same shape. Three in a row failed on the same gate, which is
evidence about the search method, not bad luck: searching for obligations with public artefacts reliably finds
free artefacts.

The recommended next task is the one Cycle 106 left executable and which requires no new research: **resolve
B13-001's price and publication**, which are founder decisions with numbers already attached ($15 clears both
checks at the current 15 pages; $19 needs 30 pages; $27.99 works on premium). That is the shortest path to a
verified external transaction, and a verified transaction is the only evidence class that would strengthen the
next discovery cycle.

If a fourth probe is preferred, it should target a category where the *regulator* has not published a workbook:
sector-specific recordkeeping duties enforced by inspection rather than by filing.

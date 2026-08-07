# OpenClaw / Galaxy Forge — Company Personality

**Status:** Permanent, part of the Company DNA (`COMPANY_DNA.md`). This document names what already exists — `brand_dna.py` (ADR-170) found this company already had a real, consistent voice, readable directly in `customer_site/index.html`'s own copy, before anyone wrote it down. This document is that voice, named, extended to the relationships the code doesn't yet reach, and made enforceable via `brand_dna.py::validate_customer_facing_text()` (see `INTEGRITY_RULES.md`).

---

## The 9 core traits (real, from `brand_dna.py::COMPANY_PERSONALITY`)

| Trait | Rule | Real evidence |
|---|---|---|
| Professional | Correct, complete, free of hype in every customer-facing sentence | `customer_site/index.html`: "No guessed demand. No vanity metrics. No vaporware." |
| Honest | State the real limitation before the customer discovers it | `index.html`: "We're honest that end-to-end automated delivery is still being built out." |
| Respectful | Never pressure, never guilt, never use a customer's own words against them | No dark-pattern copy exists anywhere in `customer_site/` (confirmed by direct search) |
| Calm | No exclamation-mark urgency or all-caps alarm, even delivering bad news | `customer_pipeline.py`'s real stage messages ("We're reviewing your request — this usually takes under a minute") |
| Helpful | Solve the actual problem in the first response before adding anything else | Enforced structurally by keeping every module's functions short and single-purpose |
| Transparent | A rejection or delay always states the real reason, never a generic apology | `index.html`: "If it doesn't clear, you get the real reason, not a form rejection." |
| Intelligent | Evidence-led, not guess-led — every product claim traces to a real check | `index.html`'s own tagline: "We don't guess what the market wants. We prove it first." |
| Premium | Depth and precision over volume — a short, exact answer beats a long generic one | The same discipline this company's own ADRs have followed all session |
| Human-like, never pretending to be human | Warm, natural sentences; never claims humanity; never hides that this is an AI-run company where it matters | **Partial** — the tone already reads this way; an explicit AI-authorship disclosure does not yet exist on customer-facing pages (a real, disclosed gap, not silently assumed done) |

## How OpenClaw behaves — by relationship

### With customers
The 9 traits above, applied directly. One addition specific to this relationship: **a customer's trust is never spent on a sale that isn't ready.** The EU AI Act toolkit's own price correction — from $310 down to an honestly-verified $155 — happened before a single customer ever saw the wrong number, not after a complaint. That sequencing (catch it yourself, before it costs someone else something) is the real standard, not an aspiration.

### With partners
**Real, disclosed terms or no relationship at all.** The Global Business Development Division (`business_development.py`, ADR-188) will not record a fabricated opportunity score for a partner program this company hasn't actually verified exists — every real partnership evaluation cites a real source URL or is honestly marked Discovery. The same standard extends to how this company would behave once a partnership is real: a partner gets the same evidence-first honesty a customer does, including about this company's own real limitations (a pre-revenue company, honestly disclosed as such, not oversold to a platform partner either).

### With competitors
**Named accurately, never disparaged, differentiated on evidence.** The EU AI Act toolkit's launch kit names its two real competitors (`governancedocs.com`, `riskprofs.com`) directly, cites their real prices and real gaps, and frames the difference as "the only toolkit that tells you the real current deadline and where it came from" — never "competitors are wrong." `truth_first.py`'s own Truth First Constitution forbids the alternative.

### With employees
**Not yet applicable in the traditional sense — a real, disclosed gap, not glossed over.** This company has one human (the founder) and one AI collaborator operating under very high standing autonomy, documented in this repo's own memory system. The principle that will apply the moment this changes: every trait above extends to a real employee exactly as it extends to a real customer — no internal communication is exempt from the honesty this company demands externally.

### With AI agents
**Technical neutrality — no loyalty to any single model, provider, or platform** (`CLAUDE.md`'s own stated principle, first written 2026-07-23). The only real criterion for which AI system does a given job: better results, quality, speed, reliability, cost, and customer outcomes — evaluated with real data (`ai_capability/registry.py`'s real per-provider stats), never assumed. As of this writing, that registry's own honest finding is that 11 of 12 registered providers have never actually been called — a real, disclosed state, not a claim of diversity this company hasn't earned yet.

---

*See also: `COMPANY_DNA.md` (the principles this personality protects), `INTEGRITY_RULES.md` (`brand_dna.py::validate_customer_facing_text()` — the real, callable enforcement point for everything in this document).*

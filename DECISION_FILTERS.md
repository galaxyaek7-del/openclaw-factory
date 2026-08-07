# OpenClaw / Galaxy Forge — Decision Filters

**Status:** Permanent, part of the Company DNA (`COMPANY_DNA.md`). Every product, feature, or partnership proposal is run through these six filters before approval. A "no" on any filter is a real rejection, not a note for later — the same discipline `profit_oracle.py`'s hard gates already apply mechanically to every real opportunity this company has ever evaluated.

This is not a new evaluation engine. It is the founder's six named questions, mapped explicitly onto the real, already-built systems that already answer them — so "decision filter" means something checkable, not a slogan.

---

## 1. Does it solve a real problem?

**Real mechanism:** `goos.py::evaluate_dimensions()`'s `real_customer_pain` dimension, backed by `executive_quality_gate.py::check_customer_pain_evidence()` and the Proof of Payment doctrine (`profit_oracle.py`, ADR-121) — real, human-cited evidence that someone is already paying money to solve this exact problem today (a competitor's paid review, a real paid job posting, a real freelancer charging for the manual version, a real subscription someone is trying to escape).

**The bar:** Not "this sounds useful." Real, dated, sourced evidence — a `source_url` and a verbatim `quote`, or the answer is no. This is the single filter this company has failed most often (0 of 87 real evaluated niches have ever cleared it and everything else) — and the one it has never relaxed to get a faster yes.

## 2. Is the market large enough?

**Real mechanism:** `goos.py`'s `market_size_tam_sam_som` dimension — honestly `NOT_MEASURABLE` today, disclosed as a real, standing gap (`profit_oracle.py` has no real TAM/SAM/SOM data source anywhere in this factory). `willingness_to_pay` (via `executive_quality_gate.check_willingness_to_pay()`) and `competition_level` (via real competitor-saturation scoring) are the real, currently-available proxies.

**The bar:** Until a real market-sizing capability exists, this filter is answered honestly as "insufficient evidence" rather than a fabricated number — and an opportunity that only clears on willingness-to-pay and competition signals, without a real size estimate, is treated as more speculative, not automatically approved.

## 3. Is it difficult to copy?

**Real mechanism:** `goos.py`'s `difficulty_of_copying` dimension, backed by `value_engine.py`'s real `defensibility` scoring and `profit_oracle.py`'s Competitive Advantage hard gate (ADR-122) — net-positive real AI-leverage relative to a generic competitor, not a vague "we're better" claim.

**The bar:** A product that is trivially reproducible by anyone with the same AI tools this company uses does not clear this filter on effort or polish alone — it needs a real, cited reason a copier would struggle (proprietary evidence, a real workflow advantage, a real regulatory-currency edge like the EU AI Act toolkit's own verified December-2027 correction that two named live competitors still don't have).

## 4. Can it become a long-term asset?

**Real mechanism:** `profit_oracle.py`'s Long-Term Strategic Asset hard gate (ADR-122/126) and `goos.py`'s `scalability` / `recurring_revenue_potential` dimensions.

**The bar:** A one-time sale that cannot plausibly become a recurring line, a reusable asset, or a durable product family scores lower than one that can — this is the real, mechanical reason this company's own stated preference for recurring revenue (the regulatory-update-subscription model, the affiliate/commission lines) exists as a standing evaluation criterion, not just a founder preference stated once.

## 5. Does it strengthen the company?

**Real mechanism:** `capital_allocation_engine.py`'s Investment Score (14 dimensions, ADR-139) and `enterprise_capital_allocation.py`'s resource-allocation map — does this opportunity compete for the same scarce real resources (founder attention, AI compute, publishing capacity, cash) as something already ranked higher, and does it strengthen the whole portfolio or just itself.

**The bar:** `capital_allocation_engine.py::opportunity_cost()` names, explicitly, what a "yes" here would take resources away from — a proposal is never approved in isolation from what it displaces.

## 6. Does it align with the mission?

**Real mechanism:** Direct citation of `COMPANY_DNA.md` §1 (proving evidence before building, refusing to let internal sophistication substitute for a real customer) and the Golden Rule (`CLAUDE.md`: no new product before the first real dollar from the current one).

**The bar:** This is the filter that has, in this company's own real history, rejected proposals that passed every other filter — the Global Commerce Intelligence Division (ADR-148) and the Global Affiliate Commerce Engine's original 20-network scope (ADR-152) were both real, well-evidenced ideas that failed this filter specifically, because building them before the first real dollar existed would have repeated the exact mistake this company's own mission was defined to prevent.

---

## If the answer to any filter is NO

**Reject it — document why, keep the evidence.** Every real rejection is recorded (`QUARANTINE.md` for products, `data/decisions.jsonl` for opportunities, `data/executive_directives.jsonl` for executive-level calls) with its real reason attached, never silently dropped. A "no" today is not permanent: `data/decisions.jsonl`'s own real re-evaluation history shows niches moving between DEFERRED and RECONSIDERED as real evidence changes — but the burden is always on new evidence arriving, never on relaxing the filter.

---

*See also: `COMPANY_DNA.md` (the principles these filters exist to protect), `INTEGRITY_RULES.md` (how these filters are actually enforced against every AI recommendation before execution).*

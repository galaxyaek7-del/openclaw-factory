# ADR-247 — Single Audience, Single Product Line: Arabic HVAC/Refrigeration Technicians

**Date:** 2026-10-12
**Status:** Adopted (Cycle 82, "From Builder to Seller").

---

## The directive

Founder decision: stop building broadly and converge on exactly one audience and one product line until the first 10 real, verified sales exist. **Freeze on new arms, new infrastructure, or new product categories until that threshold is reached** — every unit of work this cycle and after serves selling the existing focus, not expanding scope.

- **Audience:** Arabic-speaking refrigeration/air-conditioning (HVAC-R) technicians — primarily Algeria, the broader Maghreb, and the Gulf.
- **Product line:** Arabic-language digital technical reference guides for this exact trade — refrigerant pressure-temperature (P-T) charts for common refrigerants, fault-diagnosis guides, AC wiring/electrical diagrams, maintenance checklists.

## Why this audience, why this product line (the real diagnosis this ADR responds to)

The standing, repeatedly-reconfirmed real finding across Cycles 77–82: 500 real candidate niches discovered, $0 verified revenue, Gumroad's own live `/v2/sales` API confirming 0 orders, PayPal showing 0 transactions in 31 days. The factory has a real, working production pipeline and no real customer acquisition motion pointed at any one audience long enough to learn from it. This ADR is a scope-narrowing decision, not a new capability — it does not add a product family, a platform, or a code path that didn't already exist (`book_generator.py`, `product_families/families/professional_templates.py` / `digital_toolkits.py`, Gumroad distribution are all already real and already proven on other content).

**Why this specific audience/product pair, not another:** chosen directly by the founder for this cycle (not derived from the existing 500-candidate dataset, which has never independently surfaced this niche — see ADR-121 evidence-hunt findings in `docs/CYCLE_82_FINAL_REPORT.md` for why). A real evidence check against existing competing products (any language, any platform) was run before building anything — see that same report's §2 for the specific products found and the top-3 ranking.

## What this ADR does NOT do

- Does **not** relax ADR-121's Proof-of-Payment doctrine, Gate-2, or `profit_oracle.py`'s score/profit floors. The one product built under this focus must still clear the real, unchanged gates before any real production/sale decision.
- Does **not** add a new business arm, a new platform integration, or new infrastructure. Distribution uses the already-real Gumroad channel; content uses the already-real `book_generator.py`/manifest-driven product-family pipeline.
- Does **not** authorize publishing, outreach, or any external communication — those remain founder-gated per every standing rule this factory has reconfirmed for months.

## Scope and exit condition

This focus holds until **10 real, independently verified sales** exist (verified the same way this factory verifies everything else: a real transaction record, not a page view, click, or self-purchase). At that point the founder decides whether to keep narrowing, broaden the product line within the same audience, or expand audience — not decided in advance here.

## Cross-reference

`docs/PRODUCT_CLASSES.md` — this audience/product pair is recorded there as a named, evidence-tracked class (see that file's update in this same cycle) rather than a parallel, undocumented decision.

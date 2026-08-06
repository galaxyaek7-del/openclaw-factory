# The Nested Evidence Shape Bug

## The mistake

`profit_oracle.py::_score_urgency()` reads real customer-pain evidence a caller passes in via `external_signal["customer_pain"]`, and computes a real urgency score from two fields: `willingness_to_pay_hits` and `pain_language_hits`. The function read them from the top level of that dict:

```python
pain = (external_signal or {}).get("customer_pain") or {}
wtp_hits = pain.get("willingness_to_pay_hits")
pain_hits = pain.get("pain_language_hits")
```

But `market_intelligence_engine.py::analyze_customer_pain()` — the one real function in this factory that actually produces this data — always nests both fields one level deeper, under a `real_evidence` key:

```python
{"pain_score": 8, "real_evidence": {"willingness_to_pay_hits": 0, "pain_language_hits": 0, ...}}
```

`pain.get("willingness_to_pay_hits")` on the real shape always returned `None`. `_score_urgency()` treated `None` as "no evidence was ever passed in at all" and honestly reported `"Unknown"` — even when `analyze_customer_pain()` had, in fact, run a real query and found real (if weak) evidence.

## The consequence

`ladder_opportunity_score()`'s Pain Severity hard gate (Strategic Doctrine v2, ADR-122) requires `urgency_score >= 25` to pass. Since the real score was silently always `None`, this gate could never be satisfied by any real caller — not because the underlying evidence was always weak, but because the two functions disagreed about where the numbers lived. This one shape mismatch was a real, structural contributor to why this factory has had 0 real ACCEPTED opportunities across every evaluation it has ever run.

## How it was found

Not by code review of `profit_oracle.py` in isolation — by trying to actually wire real evidence through the full pipeline for a real candidate product (2026-08-06, "EXECUTION MODE"), watching the real rejection reason change from "no evidence passed" to a *plausible-looking but still-zero* urgency score, and tracing that number back through both functions' real return shapes side by side.

## The fix

`_score_urgency()` now checks `real_evidence` first, falling back to the flat top-level shape only if that's absent — compatible with both the real, correct shape and this file's own pre-existing test fixture's flatter one, so no existing caller broke.

## The generalizable lesson

**Two independently-well-tested functions can each be internally correct and still be wrong together**, when one produces a shape the other was never actually exercised against with real data. `_score_urgency()`'s own test fixture (`_pain_evidence_signal()`) had, itself, been quietly encoding the wrong shape all along — every unit test passed, because the test and the code agreed with each other, not because either agreed with the one real function that actually produces this data in production. **A contract between two functions is only real once it's been exercised with a genuinely real payload from the actual producer, not a hand-constructed test fixture that might silently encode the same wrong assumption as the consumer.**

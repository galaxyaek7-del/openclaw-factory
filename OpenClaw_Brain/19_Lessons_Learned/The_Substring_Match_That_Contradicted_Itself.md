# The Substring Match That Contradicted Itself

**Found:** 2026-08-08, Phase 34 (ADR-227), building `lead_outreach_agent.py::explain_customer_match()`.

## The mistake

The first version of `WHY_THIS_CUSTOMER` checked `if any("real" in r.lower() for r in base_match["reason"])` to decide whether to report "Real signals present" vs. "No real customer signal available." But `commission_engine.py::match_customer_to_opportunity()`'s own real reason strings for an *unknown* field read `"industry UNKNOWN -- no real signal to match against"` — which contains the literal substring `"real"` inside the phrase `"no real signal"`. The check matched it, and the function printed a self-contradicting message: *"Real signals present: industry UNKNOWN -- no real signal to match against."*

## How it was found

Live-testing the function against the real, existing `UNKNOWN` customer-profile case (the honest default this factory has for every real customer today, since 0 real customer records exist) rather than only testing the positive case.

## The fix

Checked for the real function's actual positive-signal prefix convention (`"real industry provided: ..."`, `"real budget signal: ..."` — both literally start with `"real "`) instead of a bare substring match anywhere in the sentence.

## The generalizable lesson

A disclosed-honesty codebase's own negative/gap-disclosure sentences (`"no real X"`, `"UNKNOWN"`, `"NOT_AVAILABLE"`) are adversarial inputs to any later substring check for the word "real" — the same word that marks a *positive* real signal elsewhere in this factory's vocabulary also appears inside every *negative* disclosure sentence. Any future "does this text indicate a real signal" check must match a real, positive prefix/pattern, never a bare keyword search — the exact same class of risk `truth_first.py`'s own vocabulary discipline exists to prevent at the schema level, now confirmed at the string-matching level too.

---

*See also: `OpenClaw_Brain/19_Lessons_Learned/The_Nested_Evidence_Shape_Bug.md` (a related "misread the real shape of another module's output" class of bug).*

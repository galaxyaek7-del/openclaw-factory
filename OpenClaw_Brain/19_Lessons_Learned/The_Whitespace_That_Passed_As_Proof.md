# The Whitespace That Passed As Proof

## The mistake

`commission_ledger.py::record_commission()` guards real (`environment="REAL"`) commission records against fabrication: a `CONFIRMED`/`PAID` status requires real `evidence` and a real `external_transaction_id`, enforced by raising `AntiFabricationError` when either is missing. The check was a bare Python truthiness test:

```python
if not evidence:
    raise AntiFabricationError(...)
```

## The consequence

`not value` treats any non-empty string as truthy — including `"   "` (three spaces) or `"x"`. The firewall that was supposed to require *real* proof could be satisfied by a string that carried no actual information at all. A caller — human error, a bad template default, or a genuinely adversarial input — could record a `REAL`/`PAID` commission with a whitespace `evidence` field and a two-character `external_transaction_id`, and the guard would let it through clean.

Three of the module's own pre-existing tests had, unnoticed, been relying on exactly this looseness — using fixture values like `"t1"`/`"e1"`/`"e2"` that only ever passed *because* the check was too lenient, not because they represented anything a real evidence trail would look like.

## How it was found

A dedicated Phase 35 adversarial pass specifically asked "what is the minimum input that still satisfies this guard" rather than testing only the missing-field case the guard was originally written to catch.

## The fix

`_is_meaningful(value)` — requires a stripped string of at least 4 characters — replaces the bare truthiness check for both `evidence` and `external_transaction_id`. The three pre-existing tests that had been quietly exploiting the old looseness were updated to realistic-length fixture values, and 3 new regression tests assert the whitespace/trivially-short paths are now correctly rejected.

## The generalizable lesson

**A "not empty" check is not the same guarantee as "not fake."** Any anti-fabrication guard whose bar is merely "the field is non-empty" is only ever as strong as its weakest satisfying input — and that input is worth testing explicitly, not assumed away. The fact that this factory's own test suite had silently normalized around the weak version of the check (rather than the intended one) is itself the pattern to watch for: a guard's own tests can encode the same blind spot as the guard.

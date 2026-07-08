# The Self-Awareness Blind Spot (and Its Own Fix)

## What happened

`self_awareness.js` (Day 08) was built to honestly report the factory's weaknesses — and its own Constitution-compliance check (§19, Golden Hunter) surfaced a real, already-documented gap: `REJECTED_NICHES.md`, the circuit breaker's memory, was only ever written by `factory_loop.js`'s own `hunt()` function. The Scout button (`/api/scout/run`) and a direct `/generate-book` call both went through `book_generator.py`'s `generate_book()` — the exact same underlying function — but neither path ever recorded a rejection anywhere Node could see. A niche rejected via Scout could be retried endlessly through that path, with no memory of the previous failure.

This is the same root shape as [The_Circuit_Breaker_Discovery.md](./The_Circuit_Breaker_Discovery.md)'s original finding, but that fix only ever closed the gap for `factory_loop.js`'s own autonomous loop — it never actually reached the Scout path, and (worse) `self_awareness.js`'s own compliance check for this exact issue was a **hardcoded, unconditional warning string** — it would have kept saying "this gap is still open" forever, even after the gap was closed, because nothing in it actually re-checked reality.

## The fix

Moved the recording itself into `book_generator.py`'s `generate_book()` — the one function every caller (Scout, `hunt()`, a direct `/generate-book` call) already goes through. `_record_rejected_niche()` writes to `REJECTED_NICHES.md` in the *exact* same format `factory_loop.js`'s own `recordRejectedNiche()` always used — verified directly: `Date.parse()` on the Node side correctly parses Python's `datetime.now().isoformat()` timestamps (no `Z` suffix; naive local time, same convention `inspectors.py`'s `QUARANTINE.md` already used), so either side can read what the other wrote without any format negotiation. `factory_loop.js`'s own write call was removed from `triggerGenerateBook()` (it would now double-record the same event every time `hunt()` calls `/generate-book`) — but the *read*-side check (`isNicheRejected()`) stayed exactly as it was, since Python writing to the same file is functionally invisible to it.

`self_awareness.js`'s compliance check for this gap was also rewritten from a hardcoded string into `checkScoutCircuitBreakerCoverage()` — a real check of whether `book_generator.py`'s own source contains `_record_rejected_niche`. Not a live functional test, but a genuine, verifiable signal instead of an assumption baked into the file forever.

## How it was verified (not just asserted)

1. Rejected a niche ("منتج", a genuinely SKIP-tier score) directly through `book_generator.py.generate_book()` — the same function Scout calls — and confirmed the rejection landed in `REJECTED_NICHES.md`, in clean, correctly-encoded Arabic (an earlier attempt via `curl` from the Bash tool corrupted the Arabic text into `????` — a known, previously-documented shell-encoding artifact, not a real bug; redone via a direct Python call instead).
2. Crafted a `scout_runs.log` entry pointing at that same niche and ran `factory_loop.js`'s real `hunt()` — it correctly read the Python-written rejection and returned `action: "skipped"`, without ever calling `/generate-book` again.
3. Ran `self_awareness.js`'s real assessment afterward — its own §19 compliance note changed from *"فجوة معروفة ومستمرة"* (known, ongoing gap) to *"مُغلَقة"* (closed), driven by the actual source-code check, not a stale string.

## The generalizable lesson

**A self-awareness system's own diagnostic checks are code too, and can go stale exactly like anything else they're meant to monitor.** A hardcoded "this is broken" note is honest on the day it's written and a lie on every day after the underlying thing gets fixed — the fix isn't complete until the *detector* is updated to actually re-check, not just the thing it was detecting. This is also, quietly, proof that [CONSTITUTION.md §20](../../CONSTITUTION.md) is working as designed: the factory found this gap by being asked to look at itself honestly, not because a human happened to notice it.

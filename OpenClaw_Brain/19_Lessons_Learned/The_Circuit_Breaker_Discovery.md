# The Circuit Breaker Discovery

## What was found

While building `inspectors.py` (Dual Inspection), a routine check of `QUARANTINE.md` for leftover test data revealed something that wasn't test data at all: real, autonomous rejection entries for the same niche, timestamped roughly 10 minutes apart, spanning **over 5 continuous hours** (2026-07-06, 11:32 → 16:55). `factory_loop.js`'s HUNT logic had been retrying a niche that could never pass — burning a real Groq API call every single time — with no memory that it had already tried and failed.

## The root cause (see [The_Success_True_Bug.md](./The_Success_True_Bug.md))

`server.js`'s `/generate-book` handler was silently dropping the `published`/`inspection` fields from its response, so `factory_loop.js` had no way to distinguish a quarantined book from a real success. That had to be fixed first — a circuit breaker checking a field that never arrives is not a circuit breaker.

## The fix

`REJECTED_NICHES.md` — a durable, append-only memory (Anti-Fragility: "every failure becomes knowledge," not a discarded error). `triggerGenerateBook()` records a rejection whenever `published === false` comes back; `hunt()` checks `isNicheRejected()` **before** attempting generation, and skips with a 7-day cooldown if the same niche was rejected recently. Verified with a genuine closed-loop test: a brand-new niche → `hunt()` actually calls `/generate-book`, gets rejected, records it → a second `hunt()` call on the same niche skips instantly, no network call made.

## The second discovery — while trying to *demonstrate* the first fix

Running a real, live end-to-end test (`/api/scout/run`, not a synthetic scenario) to show the whole pipeline working surfaced a **second, still-open gap**: `REJECTED_NICHES.md` is only written to by `factory_loop.js`'s own `hunt()` → `triggerGenerateBook()` path. `/api/scout/run` — the actual button a human or n8n triggers — calls `book_generator.py` through server.js's separate `runBookGenerator()` function and never touches `REJECTED_NICHES.md` at all. The circuit breaker protects the *autonomous* loop only; a human (or n8n) repeatedly clicking Scout on a similarly-priced niche is not yet protected.

**This gap is not fixed as of this writing.** Candidate fix: move the rejection-recording logic to a shared point both callers go through — `book_generator.py` itself, or `/generate-book`'s response handling — so every caller shares one memory instead of `factory_loop.js` keeping its own.

## The generalizable lesson

**A fix demonstrated only in isolation can hide a scope gap that only shows up when tested through the real, full path a user would actually take.** The circuit breaker's unit tests all passed cleanly — the gap only became visible when proving the fix by running the actual Scout button end-to-end, the same discipline named in [19_Lessons_Learned/README.md](./README.md)'s general pattern. Always test a fix through the path that will actually exercise it in production, not just the path that was easiest to script.

# The `success:true` Bug

## The mistake

`book_generator.py`'s `generate_book()` can return `success: true` (the PDF genuinely was written to disk) while also setting `published: false` (CONSTITUTION.md §17, Dual Inspection, blocked it — e.g. on price or a technical failure). These are two different, independent facts: *"did generation complete"* and *"is this cleared to publish."*

`server.js`'s `/generate-book` route handler, however, only ever forwarded this to callers:

```js
res.json({ success: true, filename: result.file || filename, pages: result.pages });
```

`published` and `inspection` were silently dropped. Any caller — `factory_loop.js` included — saw `success: true` and had **no way to know** the book had actually been quarantined.

## The consequence

`factory_loop.js`'s HUNT logic used `data.success` as its only signal of whether a niche needs retrying. Since a quarantined book still reports `success: true`, HUNT treated a rejected niche as a completed success and, on finding no matching usable output on a later check, retried it. The result: the same rejected niche was retried **every ~10 minutes for over 5 hours** (2026-07-06, 11:32→16:55), each attempt burning a real Groq call for a niche that could never pass the same price check twice.

## How it was found

Not by code review — by noticing `QUARANTINE.md` had far more entries than expected, all for the same niche, spaced almost exactly 10 minutes apart. That spacing matched `factory_loop.js`'s own tick interval exactly, which pointed straight at the autonomous loop as the source before a single line of `server.js` was even opened.

## The fix

```js
res.json({
  success: true,
  filename: result.file || filename,
  pages: result.pages,
  published: result.published,
  inspection: result.inspection,
});
```

This was a **prerequisite**, not an optional improvement — the circuit breaker (see [The_Circuit_Breaker_Discovery.md](./The_Circuit_Breaker_Discovery.md)) could not have worked at all without this fix landing first, since it depends entirely on `published` actually reaching the caller.

## The generalizable lesson

**A response object silently dropping a field is invisible from either side of the boundary alone.** The Python side was correct. The Node side's handler was "correct" by its own old contract (nobody had asked it to forward those fields — they didn't exist when it was written). The bug only existed *between* the two files, in a place no single-file review would catch. When a new field is added to a lower-level function's return value that changes what "success" means, **every caller across every process boundary must be checked**, not just the function itself.

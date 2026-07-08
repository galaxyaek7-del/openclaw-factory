# 19 — Lessons Learned

**Read this folder before building anything non-trivial.** Per CONSTITUTION.md §18 (Knowledge Brain): "search the Brain before building" — these are the lessons most likely to repeat a real, already-paid-for mistake if skipped.

## The critical lessons

1. [The_Success_True_Bug.md](./The_Success_True_Bug.md) — a field silently dropped between two processes caused a 5-hour retry storm
2. [The_1299_Pricing_Trap.md](./The_1299_Pricing_Trap.md) — a few-shot example taught bad pricing more strongly than an instruction sentence could fix it
3. [The_Circuit_Breaker_Discovery.md](./The_Circuit_Breaker_Discovery.md) — the fix for #1 turned out to have its own scope gap
4. [The_Self_Awareness_Blind_Spot.md](./The_Self_Awareness_Blind_Spot.md) — the factory's own self-awareness engine found (and helped fix) #3's remaining gap, and its own diagnostic check was a stale hardcoded string until it, too, was fixed to actually re-check reality

## The general pattern underneath all four

Every one of these was found by **actually running the real pipeline and reading real output** — not by reviewing code in the abstract. The `success:true` bug was invisible in any single file's code; it only showed up by tracing a value across a process boundary. The pricing trap only became obvious after several live Groq calls all landed suspiciously close to the few-shot example's number. The circuit-breaker gap was found while trying to *demonstrate* the fix working, not while writing it. The self-awareness blind spot was found by the factory being asked to honestly evaluate itself, and its fix required noticing that a *diagnostic* can go stale exactly like the thing it diagnoses. **Testing a fix by running the exact end-to-end path it's meant to protect — not just the unit under change — is what surfaced every one of these.**

## Other real lessons from this project (bonus, not part of the "critical three")

- **A few-shot example is a stronger behavioral signal than a stated rule** (see lesson #2) — generalizes beyond pricing to any prompt with an example.
- **Tag-based AI output parsing must reject the tag name itself as a false-positive value** — the SUBTITLE bug: when Groq correctly echoed a literal `##SUBTITLE##` tag as instructed, naive parsing mistook the tag name for the actual subtitle content.
- **Pillow does not shape Arabic text** — `arabic_reshaper` + `python-bidi` are required for any RTL rendering; this was missed in an early cover-generation pass because all prior testing had used English sample titles only.
- **A library that opens a file successfully doesn't guarantee every read pattern against it is reliable** — `pypdf`'s `reader.pages[i].get_contents().get_data()` returned inconsistent results against this factory's reportlab-generated PDFs (a known reportlab xref quirk) depending on subtle call-context differences; the fix was to use a coarser but reliable proxy (file-size-per-page) rather than keep a flaky check.

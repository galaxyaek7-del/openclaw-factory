# The Disclaimer That Never Rendered

## The mistake

Generating `books/eu_ai_act_compliance_toolkit.pdf`, the founder's real "not legal advice" requirement was written into the `topic` field passed to `book_generator.py::ai_generate_book_content()` — text meant as *context* for what the AI should write about, not an instruction guaranteed to appear as its own visible section:

```python
topic = "... Not a substitute for legal advice -- a practical starting toolkit."
```

The real, live Groq generation used this as background framing and never actually wrote a standalone disclaimer into any chapter. The assumption — "if I tell the model the disclaimer matters, it will include it" — was never verified against the actual rendered output.

## The consequence

A real, technically-valid, commercially-validated 46-page compliance product shipped with genuine legal-liability exposure: directive "SMEs must:" language throughout, and zero occurrences of "legal advice," "disclaimer," or "attorney" anywhere in the real extracted text (confirmed only by direct `pypdf` text extraction, not by re-reading the prompt). A second, compounding issue rode along undetected the same way: the $349 launch price was never actually checked against real content depth, and the factory's own existing `market_realism` safety check would have silently repriced it to $250 — below the founder's explicit $300+ requirement — invisibly, at real distribution time, had this not been caught first.

## How it was found

Not by re-reading the generation prompt — by treating "did the disclaimer actually render" as a claim requiring its own real verification, extracting the real PDF text with `pypdf`, and grepping it directly. The prompt said the disclaimer mattered; only reading the actual shipped artifact proved whether it was there.

## The fix

`book_generator.py::generate_book_from_content()` — the existing "human/Claude-authored, real pipeline unchanged" path (ADR-022) — was used to insert a real, deterministic disclaimer chapter that is always present regardless of what any future LLM call does or doesn't decide to include. Real, substantive reference content (a deadlines timeline, a glossary, an FAQ) was added the same way — written directly rather than re-rolling the dice on a second live generation call, restoring genuine content depth so the $300+ price the founder required was verified as real, not assumed.

## The generalizable lesson

**A requirement mentioned in a generation prompt is a hope, not a guarantee — the only real proof a critical requirement was met is inspecting the actual output artifact directly, not re-reading the instructions that were supposed to produce it.** For any requirement where the cost of it silently not showing up is real (legal exposure, a broken price floor, a missing safety disclosure), verify by reading the shipped thing itself, and if reliability matters, make the requirement structurally guaranteed (deterministic code) rather than probabilistically requested (a prompt instruction to a model that can't be checked for compliance without checking the output).

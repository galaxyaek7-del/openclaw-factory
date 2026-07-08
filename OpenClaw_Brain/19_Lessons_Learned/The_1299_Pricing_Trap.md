# The $12.99 Pricing Trap

## The mistake

`scoutBriefPrompt()` in `server.js` asks Groq to suggest a book's price via a few-shot example, showing the model the exact output format to imitate:

```
##PRICE##
9.99
```

Groq consistently suggested prices clustered at $9.99–$14.99 across many real runs. Once `inspectors.py`'s Commercial Auditor enforced the Butter Principle's $30 floor (CONSTITUTION.md §16), **every single Scout-generated book failed Dual Inspection on price alone** — even niches that scored GOOD or GOLDEN on `profit_oracle`'s own demand/competition/execution signals. A structurally sound gate (the $30 floor is correct and shouldn't be lowered) was rejecting good work because of an upstream habit, not because the niches were actually weak.

## Why simply "asking nicely" wasn't enough

The first fix attempt was to add an instruction sentence asking for value-based pricing. This helps, but a **few-shot example is a stronger behavioral signal than an instruction sentence** — the model imitates the shape and scale of the example even when the surrounding text says something different. The real fix required changing *both*: the instruction (explicit value-based reasoning: depth, target audience, market comparables, $30 minimum, justify by value) **and** the example's own number (9.99 → 39).

## The two-layer fix that actually worked

1. **Root cause (the prompt):** rewrote the instruction to require premium, value-justified pricing, and changed the few-shot example's price to `$39`. Verified live: a real `/api/scout/run` call after this change had Groq suggest **$49** on its own — no repricing needed.
2. **Safety net (never trust a single fix to hold forever):** `profit_oracle.butter_price(niche)` — given a niche, computes a defensible $30–$100 price from real signals already used elsewhere (keyword tier, recurring-revenue signal, this niche's own `profit_score`). `book_generator.py`'s `_resolve_price()` calls this automatically whenever a price under $30 arrives, **but only if the niche's own `profit_score` verdict isn't `SKIP`** — a genuinely weak niche is left to fail honestly; repricing rescues correctable pricing mistakes, not bad niches.

## The generalizable lesson

**Raise the value, don't lower the floor.** When a correct quality gate starts rejecting most of what reaches it, the fix is almost never to weaken the gate — it's to find and fix whatever upstream habit is producing sub-standard input in the first place. And when that upstream habit lives inside a prompt: check the few-shot example's own numbers as carefully as the instruction text, because the model may be learning more from the example than from the sentence telling it what to do.

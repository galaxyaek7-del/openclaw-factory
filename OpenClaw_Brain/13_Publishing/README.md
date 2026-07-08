# 13 — Publishing

## Honest current state: not automated

`inspection.published == true` means a book is *cleared* to publish — it does not mean anything has actually been uploaded anywhere. No KDP, Etsy, or Gumroad API integration exists in this repository. "Publishing" today is entirely manual: a human takes an approved PDF from `books/` and uploads it themselves.

## What Smart Publishing (OPENCLAW_OS_CONSTITUTION.md) asks for, not yet built

> Select: best platform, language, keywords, title, description, pricing, schedule, distribution strategy.

`profit_oracle.py`'s `recommended_platform` field is the one piece of this that exists today (e.g. "KDP + Etsy + Gumroad" for template-like niches vs. plain "KDP" for a standard book) — a recommendation only, not an actual multi-platform publish action.

## What the `publisher` agent does today

`AGENT_PROMPTS.publisher` (see [09_Prompt_Library](../09_Prompt_Library/)) generates SEO-optimized titles, descriptions, and KDP backend keywords on request — real, useful content generation, but a human still copies it into Amazon's dashboard by hand.

## Where this fits the roadmap

Building real publishing automation before `book_engine` has proven a single dollar (see [01_Vision](../01_Vision/)'s Golden Rule) would be scope creep ahead of need. This folder exists so that when it *is* time to build it, the requirements (Smart Publishing's own checklist above) are already collected in one place.

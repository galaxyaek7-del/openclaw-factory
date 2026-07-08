# 12 — Production

## `book_generator.py` — the core pipeline

```
generate_book(title, topic, chapters, audience, price, theme, author)
  → _resolve_price(topic, price)         Smart Publishing repricing
  → quality_gate(topic, theme)            niche/competition/cover-theme check — blocks BEFORE any AI call
  → ai_generate_book_content()            Groq, real content
  → _resolve_subtitle()                   rejects placeholder echoes (e.g. "SUBTITLE")
  → create_ai_book() → draw_cover_v2()     cover_designer_v2, 70/20/10, falls back to vector cover
  → inspectors.final_inspection()          the master publish gate — result includes `published`
```

Every stage degrades rather than crashes: AI failure → `_fallback_book_content()`; cover_v2 failure → `safe_cover()`; inspectors.py absent → fails closed (never silently approved).

## `cover_designer_v2.py` — standalone, Pillow-only

Deliberately does **not** import `book_generator.py` — avoids pulling in the whole `reportlab`/`niche_validator_v2` dependency chain for a lightweight image tool. Duplicates the 8 theme colors instead of sharing them; a real, accepted tradeoff (Constitution §2 modular architecture vs. DRY) — documented in the file's own comments.

Real bug fixed here: Arabic text rendered via raw `PIL.ImageDraw.text()` produces disconnected, unshaped, wrong-direction letters — Pillow does not do Arabic contextual shaping or bidi reordering on its own. Fixed via `arabic_reshaper` + `python-bidi`'s `get_display()`, applied at every draw call, always *after* word-wrapping (shaping before wrapping breaks line-width math).

## The "publish" gate, concretely

A book existing in `books/` (`success: true`) is **not** the same as it being cleared to sell (`published: true`). See [19_Lessons_Learned/The_Success_True_Bug.md](../19_Lessons_Learned/The_Success_True_Bug.md) for the real incident where this distinction was silently lost between two processes.

## Related

- [09_Prompt_Library](../09_Prompt_Library/) — the content-generation prompts
- [05_Living_Cells](../05_Living_Cells/) — honest capability scoring of this pipeline's components

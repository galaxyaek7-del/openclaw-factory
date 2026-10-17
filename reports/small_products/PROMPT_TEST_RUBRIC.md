# Prompt-pack test rubric (Cycle 88, 2026-10-17)

- **Applies to:** `books/arabic_teacher_prompts/README.md` (20 prompts).
- **Script:** `scripts/prompt_pack_tests.py`, which is reproducible. Run `python scripts/prompt_pack_tests.py`; it exits 1 on any FAIL.
- **Tests of the script:** `tests/test_prompt_pack_tests.py`.

## Criteria (a prompt PASSes only if all seven pass)

| Criterion | How it is checked | Type |
|---|---|---|
| Clarity | No unclear phrasing. Each finding names the exact phrase and clears only when that phrase is gone. | Model review (Claude), recorded in the script's `REVIEW` |
| Usefulness | Produces a classroom-ready artefact. | Model review |
| Specificity | Asks for a count, a duration or an explicit structure (table, list, half page, steps). | Automatic |
| Ambiguity | Brackets balance and there is at least one placeholder. No bare `[الاسم]`: unclear whose name it is, and it invites a real student name. | Automatic |
| Factual reliability | A prompt that rewrites the user's text must forbid adding facts. | Automatic |
| Duplicate content | No other prompt in the pack is ≥ 0.55 similar (difflib ratio). | Automatic |
| Intended-user fit | A class-content prompt carries `[الصف]` (grade). A student-specific prompt asks for a pseudonym, as the README privacy note already requires. | Automatic |

## Results
- **Before repair:** 7/20 PASS (`PROMPT_TEST_RESULTS_before.json`).
- **After repair:** 20/20 PASS (`PROMPT_TEST_RESULTS_after.json`).

## Limits
- **No live run:** no prompt was run in ChatGPT. No local model was available, and none was downloaded.
- **Not a teacher's review:** the clarity and usefulness reviews are a model reading of the text.
- **Before selling:** the founder's live test (`TEST_CHECKLIST.md`, 18/20 GOOD or better) is still required. The small-product gate stays FIX_REQUIRED until those ratings are recorded.

## E-commerce pack (`--profile ecommerce`, 25 prompts)

Same seven criteria, with marketing-specific rules. Run `python scripts/prompt_pack_tests.py --profile ecommerce`.

**Factual reliability** fails if any of these holds:
- **Persuasive copy without an honesty guard:** an ad, description, landing page, posts, script, bullets, bundles, keywords or FAQ with no instruction against invented claims or numbers.
- **Ungrounded store policy:** a store-policy FAQ that isn't given the real store facts.
- **Unguarded rewrite:** a rewrite of the user's text that doesn't forbid new claims.

**Ambiguity** also fails when a bracket holds an instruction rather than a value, e.g. `[جدول]` ("in a table").

**Intended-user fit:** the prompt names the product, audience, store or topic.

**Results:**
- **Before repair:** 7/25 PASS (`PROMPT_TEST_RESULTS_ecommerce_before.json`).
- **After repair:** 25/25 PASS (`PROMPT_TEST_RESULTS_ecommerce_after.json`).
- **The repairs that matter most for honesty:**
  - #9, #15 and #23 now ask for the real price, discount, duration, bonus and alternative instead of letting the model invent them;
  - #12 and #13 answer delivery, refund and support questions only from the store facts the user supplies.

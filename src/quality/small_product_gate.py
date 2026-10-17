"""Quality gate for small products (prompt packs, templates, checklists).

Implements the rules from the "Quality Gate for Small Products" mission.
Small products carry different quality rules than long-form books: a prompt
pack is judged by item count and how many were actually tested, a template by
whether it is usable and filled, a checklist by whether it is specific.

Scope note (honest): this module implements the prompt_pack branch as
specified. ``template`` and ``checklist`` rule dicts are declared for future
use; the current ``gate_small_product`` returns a neutral PASS for them
(score 100) rather than scoring them, because their checks were not part of
the specified logic. Do not read a PASS for those types as evidence they were
inspected.
"""

from __future__ import annotations

SMALL_PRODUCT_RULES = {
    "prompt_pack": {
        "min_items": 15,
        "test_rate": 0.90,
        "must_have_examples": True,
        "no_placeholders": True,
        "language_match": True,
    },
    "template": {
        "must_be_usable": True,
        "instructions_included": True,
        "no_placeholders": True,
        "sample_filled": True,
    },
    "checklist": {
        "min_items": 10,
        "actionable": True,
        "specific_not_generic": True,
    },
}

PLACEHOLDERS = ["[TODO]", "[ADD]", "[FILL]", "[INSERT]", "[TBD]", "..."]


def gate_small_product(
    product_type: str,
    items: list,
    tested_items: list,
) -> dict:
    rules = SMALL_PRODUCT_RULES.get(product_type, {})
    issues = []
    blocking = []
    score = 100
    # Items must be the real prompt texts (strings), and tested_items only the
    # ones a person actually ran; dummy values would make the checks meaningless.
    if any(not isinstance(i, str) or not i.strip() for i in items):
        issues.append("items must be the real prompt texts (non-empty strings)")
        blocking.append("items_not_text")

    if product_type == "prompt_pack":
        if len(items) < rules["min_items"]:
            issues.append(
                f"Only {len(items)} prompts — need {rules['min_items']}+"
            )
            score -= 30

        if items:
            test_rate = len(tested_items) / len(items)
            if test_rate < rules["test_rate"]:
                issues.append(
                    f"Only {test_rate*100:.0f}% tested — need "
                    f"{rules['test_rate']*100:.0f}%+"
                )
                score -= 25
                # Blocking, not just a deduction: 100 - 25 = 75 used to pass,
                # so an untested pack was APPROVED (found 2026-10-17).
                blocking.append("test_rate")

        all_text = " ".join(str(i) for i in items)
        found = [p for p in PLACEHOLDERS if p in all_text]
        if found:
            issues.append(f"Placeholders found: {found}")
            score -= 40

    passed = score >= 75 and not blocking
    return {
        "product_type": product_type,
        "score": max(0, score),
        "passed": passed,
        "issues": issues,
        "blocking": blocking,
        "verdict": "APPROVED" if passed else "FIX_REQUIRED",
        "items_count": len(items),
        "tested_count": len(tested_items),
    }


if __name__ == "__main__":  # pragma: no cover - manual demo
    import json

    print(json.dumps(gate_small_product("prompt_pack", ["a prompt"] * 20, ["a prompt"] * 20), indent=2))

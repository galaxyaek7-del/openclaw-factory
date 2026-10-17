"""Reproducible quality tests for the Arabic teacher prompt pack (Cycle 88).

Source of truth: the prompts as shipped, i.e. the ``` blocks in
books/arabic_teacher_prompts/README.md (numbered "### N) title").

Rubric (reports/small_products/PROMPT_TEST_RUBRIC.md), per prompt:
  clarity          no unclear phrasing (reviewer judgement, recorded in REVIEW)
  usefulness       produces a classroom-ready artefact (reviewer judgement)
  specificity      asks for a count, a duration or an explicit structure (automatic)
  ambiguity        placeholders are unambiguous: no bare [الاسم] reused for
                   different things, brackets balanced (automatic)
  factual          prompts that rewrite user text forbid adding facts (automatic)
  duplicate        no other prompt in the pack is >= 0.55 similar (automatic)
  user_fit         class-content prompts carry the grade [الصف] or a level;
                   student-specific prompts use a pseudonym, matching the
                   README privacy note (automatic)

What this does NOT do: run the prompts in ChatGPT. A PASS here means the
prompt text is well-formed and fit for purpose on reading; the founder's
live test (reports/small_products/TEST_CHECKLIST.md) is still required
before the pack can be sold.

    python scripts/prompt_pack_tests.py            # prints results, exit 1 on any FAIL
    python scripts/prompt_pack_tests.py --out reports/small_products/PROMPT_TEST_RESULTS.json
"""
import argparse
import difflib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "books" / "arabic_teacher_prompts" / "README.md"
ECOM_README = ROOT / "books" / "ecommerce_arabic_prompts" / "README.md"

PLACEHOLDER = re.compile(r"\[([^\[\]]+)\]")
NUMBERISH = re.compile(r"[0-9٠-٩]|جدول|قائمة|نصف صفحة|أسبوعان|خطوات")
GRADE = re.compile(r"\[الصف\]|صف \[|لمستوى")
PSEUDONYM_OK = re.compile(r"اسم مستعار|الطالب أ")
REWRITE = re.compile(r"أعد كتابة|بسّط|تبسيط")
NO_ADD = re.compile(r"لا تُضف|لا تضف")
DUP_LIMIT = 0.55

# Reviewer judgements (Claude model review of the prompt TEXT, 2026-10-17;
# not a teacher's review and not a live run). Only failures are listed; any
# prompt not listed passed clarity and usefulness on reading.
# Each finding names the exact phrase it objects to, so it clears only when
# that phrase is actually gone from the prompt text.
REVIEW = {
    "clarity": {
        15: ("تحمل الشخصيات والمغزى الواحد",
             "unclear: what the story 'carries' is not said (characters? a moral?)"),
    },
    "usefulness": {},
}


# E-commerce pack (Cycle 88 follow-up): same rubric, marketing-specific rules.
REVIEW_ECOM = {
    "clarity": {
        24: ("كبيرة الأحرف",
             "cannot be followed: Arabic has no capital letters"),
    },
    "usefulness": {},
}
# Persuasive copy must carry an explicit no-fabrication instruction.
PERSUASIVE = re.compile(r"إعلان|وصف|صفحة هبوط|تغريد|سكريبت|نقاط بيع|عناوين|باقات|كلمات مفتاحية|أسئلة شائعة")
HONESTY_GUARD = re.compile(r"مبالغة|ادعاءات|تضليل|صادق|حقيقي|وهمي|مثبت|استخدم فقط|لا تملك مصدراً")
# Prompts that state store policy (delivery, refunds, support) must be fed the real facts.
POLICY = re.compile(r"أسئلة شائعة|الاسترجاع|التسليم|الدعم")
GROUNDED = re.compile(r"استخدم فقط|\[معلومات|\[سياسة")
ECOM_REWRITE = re.compile(r"حسّن (وصف|النص)|أعد كتابة")
# "Placeholders" that are really instructions, not values for the user to fill.
NOT_A_VALUE = {"جدول"}
ECOM_SUBJECT = re.compile(r"\[(اسم المنتج|المنتج|المنتج أ|الجمهور|المتجر|النوع|القائمة|الموضوع|المشكلة|الكلمة|الصق)")


def _review(kind, p, review=None):
    review = review or REVIEW
    found = review[kind].get(p["n"])
    if found and found[0] in p["text"]:
        return False, f"«{found[0]}» {found[1]}"
    return True, None
# Prompts about one named student (pseudonym required, grade not required).
STUDENT_SPECIFIC_TITLES = ("رسالة لأولياء الأمور", "تقرير تقدّم فردي")


def parse(readme=README):
    text = Path(readme).read_text(encoding="utf-8")
    prompts = []
    for m in re.finditer(r"^### (\d+)\) (.+?)\n```\n(.*?)\n```", text, re.S | re.M):
        prompts.append({"n": int(m.group(1)), "title": m.group(2).strip(), "text": m.group(3).strip()})
    return prompts


def check(p, others, profile="teacher"):
    t, title = p["text"], p["title"]
    phs = PLACEHOLDER.findall(t)
    student = title.startswith(STUDENT_SPECIFIC_TITLES)
    checks = {}
    checks["clarity"] = _review("clarity", p)
    checks["usefulness"] = _review("usefulness", p)
    checks["specificity"] = (bool(NUMBERISH.search(t)), None if NUMBERISH.search(t) else "no count, duration or structure requested")
    amb = []
    if t.count("[") != t.count("]"):
        amb.append("unbalanced brackets")
    if not phs:
        amb.append("no placeholder to customise")
    if "[الاسم]" in t:
        amb.append("bare [الاسم]: unclear whose name, and invites a real student name")
    checks["ambiguity"] = (not amb, "; ".join(amb) or None)
    fact_ok = not REWRITE.search(t) or bool(NO_ADD.search(t))
    checks["factual"] = (fact_ok, None if fact_ok else "rewrites user text without forbidding added facts")
    sims = [(o["n"], round(difflib.SequenceMatcher(None, t, o["text"]).ratio(), 2)) for o in others if o["n"] != p["n"]]
    top = max(sims, key=lambda x: x[1]) if sims else (None, 0)
    checks["duplicate"] = (top[1] < DUP_LIMIT, None if top[1] < DUP_LIMIT else f"{top[1]} similar to prompt {top[0]}")
    if profile == "ecommerce":
        checks["clarity"] = _review("clarity", p, REVIEW_ECOM)
        checks["usefulness"] = _review("usefulness", p, REVIEW_ECOM)
        bad_ph = [x for x in phs if x.strip() in NOT_A_VALUE]
        if bad_ph:
            amb = ([checks["ambiguity"][1]] if checks["ambiguity"][1] else []) +                   [f"[{bad_ph[0]}] is an instruction, not a value to fill"]
            checks["ambiguity"] = (False, "; ".join(amb))
        problems = []
        if ECOM_REWRITE.search(t) and not NO_ADD.search(t):
            problems.append("rewrites the user's text without forbidding new claims")
        if PERSUASIVE.search(title + " " + t) and not HONESTY_GUARD.search(t):
            problems.append("persuasive copy without a no-fabrication instruction")
        if POLICY.search(t) and "أسئلة شائعة" in t and not GROUNDED.search(t):
            problems.append("asks for store-policy answers without supplying the real store facts")
        checks["factual"] = (not problems, "; ".join(problems) or None)
        fit_ok = bool(ECOM_SUBJECT.search(t))
        checks["user_fit"] = (fit_ok, None if fit_ok else "no product/audience/store placeholder: output cannot be fitted")
    elif student:
        fit_ok = bool(PSEUDONYM_OK.search(t))
        checks["user_fit"] = (fit_ok, None if fit_ok else "student-specific prompt should ask for a pseudonym (README privacy note)")
    else:
        fit_ok = bool(GRADE.search(t))
        checks["user_fit"] = (fit_ok, None if fit_ok else "no grade/level placeholder: output cannot be fitted to the class")
    failed = [k for k, (ok, _) in checks.items() if not ok]
    return {"n": p["n"], "title": title, "words": len(t.split()), "placeholders": phs,
            "max_similarity": top[1], "result": "PASS" if not failed else "FAIL",
            "failed": failed, "reasons": {k: why for k, (ok, why) in checks.items() if not ok}}


PROFILES = {"teacher": {"readme": README, "count": 20}, "ecommerce": {"readme": ECOM_README, "count": 25}}


def run(readme=None, profile="teacher"):
    readme = readme or PROFILES[profile]["readme"]
    prompts = parse(readme)
    rows = [check(p, prompts, profile) for p in prompts]
    return {"source": str(Path(readme).relative_to(ROOT)).replace("\\", "/") if Path(readme).is_relative_to(ROOT) else str(readme),
            "profile": profile,
            "prompt_count": len(prompts), "count_ok": len(prompts) == PROFILES[profile]["count"],
            "passed": sum(r["result"] == "PASS" for r in rows),
            "failed": [r["n"] for r in rows if r["result"] == "FAIL"],
            "live_chatgpt_test": "NOT DONE (founder action: reports/small_products/TEST_CHECKLIST.md)",
            "reviewer_note": "clarity/usefulness are a model review of the text, not a teacher's review",
            "rows": rows}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=sorted(PROFILES), default="teacher")
    ap.add_argument("--readme", help="defaults to the profile's pack README")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    rep = run(a.readme, a.profile)
    if a.out:
        Path(a.out).write_text(json.dumps(rep, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in rep.items() if k != "rows"}, indent=2, ensure_ascii=False))
    for r in rep["rows"]:
        if r["result"] == "FAIL":
            print(f"FAIL {r['n']:>2} {r['title']}: {r['reasons']}")
    return 0 if rep["count_ok"] and not rep["failed"] else 1


if __name__ == "__main__":
    sys.exit(main())

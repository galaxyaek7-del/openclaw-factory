"""scripts/prompt_pack_tests.py: the rubric catches each defect class, and the
shipped Arabic teacher pack passes it. Temp files only; no network."""
import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("prompt_pack_tests", ROOT / "scripts" / "prompt_pack_tests.py")
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)


def _pack(prompts):
    body = "\n\n".join(f"### {n}) {title}\n```\n{text}\n```" for n, title, text in prompts)
    return "# pack\n\n" + body + "\n"


class TestPromptPackRubric(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _run(self, prompts):
        f = self.tmp / "README.md"
        f.write_text(_pack(prompts), encoding="utf-8")
        return {r["n"]: r for r in T.run(f)["rows"]}

    def test_shipped_teacher_pack_passes_all_20(self):
        rep = T.run()
        self.assertEqual((rep["prompt_count"], rep["passed"], rep["failed"]), (20, 20, []))

    def test_each_defect_class_is_caught(self):
        rows = self._run([
            (1, "درس", "اقترح نشاطاً حول [الموضوع] بلا عدد ولا بنية"),            # no grade, no structure
            (2, "رسالة لأولياء الأمور", "اكتب رسالة في [٥] أسطر لولي أمر [الاسم]"),  # bare [الاسم]
            (3, "تبسيط", "أعد كتابة النص لصف [الصف] بجمل من [١٠] كلمات: [النص]"),   # may add facts
            (15, "قصة", "حوّل درس [الموضوع] لصف [الصف] إلى قصة تحمل الشخصيات والمغزى الواحد في [٣] فقرات"),
        ])
        self.assertIn("user_fit", rows[1]["failed"])
        self.assertIn("specificity", rows[1]["failed"])
        self.assertIn("ambiguity", rows[2]["failed"])
        self.assertIn("user_fit", rows[2]["failed"])
        self.assertIn("factual", rows[3]["failed"])
        self.assertIn("clarity", rows[15]["failed"])

    def test_near_duplicates_are_caught(self):
        text = "أنشئ [١٠] أسئلة اختيار من متعدد حول [الموضوع] لصف [الصف] مع مفتاح الإجابة."
        rows = self._run([(1, "أ", text), (2, "ب", text.replace("[١٠]", "[١٢]"))])
        self.assertIn("duplicate", rows[1]["failed"])


class TestEcommerceProfile(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _run(self, prompts):
        f = self.tmp / "README.md"
        f.write_text(_pack(prompts), encoding="utf-8")
        return {r["n"]: r for r in T.run(f, "ecommerce")["rows"]}

    def test_shipped_ecommerce_pack_passes_all_25(self):
        rep = T.run(profile="ecommerce")
        self.assertEqual((rep["prompt_count"], rep["passed"], rep["failed"]), (25, 25, []))

    def test_marketing_specific_defects_are_caught(self):
        rows = self._run([
            (1, "نص إعلان", "اكتب [٣] إعلانات عن [المنتج] في [٤٠] كلمة"),                         # no honesty guard
            (2, "أسئلة شائعة", "اكتب [٦] أسئلة شائعة عن [المنتج]: التسليم والاسترجاع. بلا مبالغة"),  # policies not grounded
            (3, "مقارنة", "قارن [المنتج أ] و[المنتج ب] ضمن [جدول] بلا مبالغة"),                    # fake placeholder
            (4, "رد", "اكتب رداً في [٨٠] كلمة على عميل غاضب"),                                     # no product
            (5, "تحسين", "حسّن وصف المنتج في [١٢٠] كلمة بلا مبالغة: [الصق الوصف هنا]"),             # may add claims
        ])
        self.assertIn("factual", rows[1]["failed"])
        self.assertIn("factual", rows[2]["failed"])
        self.assertIn("ambiguity", rows[3]["failed"])
        self.assertIn("user_fit", rows[4]["failed"])
        self.assertIn("factual", rows[5]["failed"])


if __name__ == "__main__":
    unittest.main()

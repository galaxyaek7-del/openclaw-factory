"""src/quality/small_product_gate.py: an untested or dummy pack never passes."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.quality.small_product_gate import gate_small_product  # noqa: E402

PROMPTS = [f"اكتب خطة درس رقم {i} لصف [الصف] حول [الموضوع]." for i in range(20)]


class TestSmallProductGate(unittest.TestCase):
    def test_untested_pack_is_not_approved(self):
        r = gate_small_product("prompt_pack", PROMPTS, [])
        self.assertEqual((r["score"], r["verdict"], r["passed"]), (75, "FIX_REQUIRED", False))
        self.assertIn("test_rate", r["blocking"])

    def test_tested_pack_with_real_text_is_approved(self):
        r = gate_small_product("prompt_pack", PROMPTS, PROMPTS[:18])          # 90%
        self.assertEqual((r["verdict"], r["blocking"]), ("APPROVED", []))

    def test_dummy_items_cannot_pass(self):
        r = gate_small_product("prompt_pack", list(range(20)), list(range(20)))
        self.assertEqual(r["verdict"], "FIX_REQUIRED")
        self.assertIn("items_not_text", r["blocking"])


if __name__ == "__main__":
    unittest.main()

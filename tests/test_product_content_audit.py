"""scripts/product_content_audit.py: verdict logic on synthetic content. No network."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("product_content_audit", ROOT / "scripts" / "product_content_audit.py")
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)

BODY = ("Freelancer rate calculator: compute your minimum hourly rate from take-home pay, tax buffer, "
        "expenses, billable weeks and hours, then add a safety margin for scope creep and late payers. ") * 6


def units(*texts):
    return [(f"p{i + 1}", t) for i, t in enumerate(texts)]


class TestVerdicts(unittest.TestCase):
    def test_nothing_delivered_is_empty(self):
        self.assertEqual(A.verdict(None, has_delivery=False)[0], "EMPTY")

    def test_near_identical_pages_are_filler(self):
        tracker = "HABIT TRACKER Month: ____ " + " ".join(str(d) for d in range(1, 32)) + " Wake up early Exercise Read Drink water Meditate"
        pages = ["Freelancer Rate Calculator cover"] + [tracker + (" x" if i % 2 else "") for i in range(8)]
        m = A.measure("Freelancer Rate Calculator", units(*pages), {})
        self.assertEqual(A.verdict(m, True)[0], "FILLER")

    def test_short_single_page_is_thin(self):
        m = A.measure("Freelancer Rate Calculator", units(BODY[:600]), {})
        self.assertEqual(A.verdict(m, True)[0], "THIN")

    def test_substantial_on_topic_content_is_ok(self):
        pages = [BODY * 2, "Client ranking and raise planning. " * 40 + BODY, "Worked example and README steps. " * 40 + BODY]
        m = A.measure("Freelancer Rate Calculator", units(*pages), {})
        self.assertEqual(A.verdict(m, True)[0], "OK", A.verdict(m, True)[1])

    def test_content_about_something_else_is_off_topic(self):
        pages = [("Sourdough baking schedule: feed the starter and autolyse the flour. " * 30),
                 ("Fold the dough every thirty minutes, then shape a tight boule. " * 30),
                 ("Proof overnight in the fridge and bake in a dutch oven at high heat. " * 30)]
        m = A.measure("Freelancer Rate Calculator Workbook", units(*pages), {})
        self.assertEqual(A.verdict(m, True)[0], "OFF_TOPIC")


if __name__ == "__main__":
    unittest.main()

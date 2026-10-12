"""Tests for Cycle 82 ("From Builder to Seller") items 3 and 4's two hard
rules: (1) every technical number in the product review file must carry a
disclosed source, (2) every content-queue post must carry a distinct,
trackable link.

These are mechanical presence/shape checks over the real, committed files
this cycle produced -- not a semantic correctness check of the HVAC content
itself (that review is explicitly the founder's own job, per the directive).

    python -m unittest tests.test_cycle82_sourcing_and_tracking -v
"""

import csv
import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

_REVIEW_FILE = _FACTORY_ROOT / "docs" / "PRODUCT_REVIEW_HVAC_PT_CHART_AR.md"
_QUEUE_CSV = _FACTORY_ROOT / "data" / "content_queue_cycle82.csv"
_QUEUE_MD = _FACTORY_ROOT / "docs" / "CONTENT_QUEUE_CYCLE82.md"


class TestProductReviewFileSourcing(unittest.TestCase):
    """Item 3: "no technical number without a source is permitted, ever."""

    def setUp(self):
        if not _REVIEW_FILE.exists():
            self.skipTest(f"{_REVIEW_FILE} not present in this checkout")
        self.text = _REVIEW_FILE.read_text(encoding="utf-8")

    def test_the_real_source_publisher_and_url_are_cited(self):
        self.assertIn("ADVANTAGE Engineering", self.text)
        self.assertIn("advantageengineering.com", self.text)

    def test_the_real_publication_and_update_dates_are_cited(self):
        self.assertIn("9/17/2009", self.text)
        self.assertIn("10/10/2012", self.text)

    def test_the_source_own_disclaimer_is_carried_verbatim(self):
        self.assertIn("Advantage assumes no responsibility", self.text)

    def test_the_safety_classification_source_is_cited(self):
        self.assertIn("ASHRAE", self.text)

    def test_the_file_is_explicitly_marked_not_published(self):
        self.assertIn("لم يُنشر", self.text)

    def test_the_pressure_table_has_real_numeric_rows_not_just_headers(self):
        # A loose structural check: the markdown table must contain a
        # meaningful number of real data rows (one per table), not just a
        # header -- confirms the table wasn't left as a stub.
        pipe_rows = [
            line for line in self.text.splitlines()
            if line.strip().startswith("|") and "°F" not in line and "---" not in line
        ]
        self.assertGreater(len(pipe_rows), 50)


class TestContentQueueTracking(unittest.TestCase):
    """Item 4: every post must carry a link with a distinct, trackable
    source identifier, and Gumroad's real `?referrer=` mechanism must be
    the one used (not an invented parameter name)."""

    def setUp(self):
        if not _QUEUE_CSV.exists():
            self.skipTest(f"{_QUEUE_CSV} not present in this checkout")
        with open(_QUEUE_CSV, encoding="utf-8", newline="") as f:
            self.rows = list(csv.DictReader(f))

    def test_fourteen_posts_exist(self):
        self.assertEqual(len(self.rows), 14)

    def test_every_post_has_a_non_empty_referrer_id(self):
        for row in self.rows:
            self.assertTrue(row.get("referrer_id", "").strip(), msg=row)

    def test_every_referrer_id_is_unique(self):
        ids = [row["referrer_id"] for row in self.rows]
        self.assertEqual(len(ids), len(set(ids)), "duplicate referrer_id found")

    def test_every_link_template_uses_the_real_gumroad_referrer_parameter(self):
        for row in self.rows:
            self.assertIn("?referrer=", row.get("link_template", ""), msg=row)

    def test_every_row_referrer_id_matches_its_own_link_template(self):
        for row in self.rows:
            self.assertIn(row["referrer_id"], row["link_template"], msg=row)

    def test_post_types_are_only_value_or_cta(self):
        for row in self.rows:
            self.assertIn(row.get("type"), ("value", "cta"), msg=row)

    def test_roughly_80_percent_of_posts_are_value_not_cta(self):
        value_count = sum(1 for row in self.rows if row.get("type") == "value")
        self.assertGreaterEqual(value_count / len(self.rows), 0.7)


class TestContentQueueMarkdownNeverPublished(unittest.TestCase):
    def setUp(self):
        if not _QUEUE_MD.exists():
            self.skipTest(f"{_QUEUE_MD} not present in this checkout")
        self.text = _QUEUE_MD.read_text(encoding="utf-8")

    def test_the_file_discloses_nothing_was_sent_or_published(self):
        self.assertIn("لم يُنشر", self.text)


if __name__ == "__main__":
    unittest.main()

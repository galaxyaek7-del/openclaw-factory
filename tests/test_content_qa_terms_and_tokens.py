"""content_qa checks added 2026-10-22.

- forbidden_terms: the systeme.io affiliate agreement bans competitor
  trademarks in promotion of systeme.io, so a guide naming them must HOLD.
- fused/template tokens: the live systeme.io guide shipped
  "APPLICATIONImplementation" inside its disclosure.

    python -m pytest tests/test_content_qa_terms_and_tokens.py -q
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from affiliate.content_qa import qa_content  # noqa: E402

BASE = {"title": "Guide", "body": "Build an opt-in page.", "disclosure": True, "cta_present": True}


class TestForbiddenTerms(unittest.TestCase):
    def test_banned_competitor_name_holds(self):
        r = qa_content(dict(BASE, body="Cheaper than Kajabi.", forbidden_terms=["kajabi"]))
        self.assertEqual(r["status"], "HOLD")
        self.assertIn("forbidden term by program terms: 'kajabi'", r["failures"])

    def test_whole_word_only(self):
        r = qa_content(dict(BASE, body="Use the wixard tool.", forbidden_terms=["wix"]))
        self.assertEqual(r["status"], "PASS", r["failures"])

    def test_absent_list_changes_nothing(self):
        self.assertEqual(qa_content(BASE)["status"], "PASS")


class TestFusedTokens(unittest.TestCase):
    def test_the_real_live_defect_is_caught(self):
        r = qa_content(dict(BASE, body="النتائج تعتمد على جهدك و APPLICATIONImplementation الخاص بك."))
        self.assertIn("fused/template token: 'APPLICATIONImplementation'", r["failures"])

    def test_normal_acronyms_and_brands_pass(self):
        r = qa_content(dict(BASE, body="NASA, HTML and Systeme.io work with SaaS and the FTC."))
        self.assertEqual(r["status"], "PASS", r["failures"])

    def test_live_guide_now_passes(self):
        import html
        import re
        s = (ROOT / "customer_site" / "guide-systemeio-affiliate.html").read_text(encoding="utf-8")
        body = re.sub(r"<script.*?</script>", "", s[s.find("<body"):], flags=re.S)
        text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", body)))
        r = qa_content({"title": "systeme guide", "body": text, "disclosure": "إفصاح" in text,
                        "cta_present": 'class="cta-button"' in s,
                        "forbidden_terms": ["kajabi", "clickfunnels", "mailchimp", "wix", "shopify"]})
        self.assertEqual(r["status"], "PASS", r["failures"])
        self.assertLess(s.find('class="disclosure"'), s.find('class="cta-button" target'),
                        "disclosure must come before the affiliate link")


if __name__ == "__main__":
    unittest.main()

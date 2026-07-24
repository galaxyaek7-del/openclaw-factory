"""Tests for build_in_public.py (Build in Public / Marketing Arm,
2026-07-24): real weekly progress reports, ADR-to-post drafting (mocked
-- never a real Groq call in tests), and the Telegram approval queue
(mocked -- never a real send in tests).

Runs with stdlib unittest. Every function reads only from temp-file-
isolated fixtures -- never the real data/*.jsonl files.

    python -m unittest tests.test_build_in_public -v
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import build_in_public as bip
from decision_engine import engine


def _temp_path():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(path)
    return path


class TestBuildWeeklyProgressReport(unittest.TestCase):
    def setUp(self):
        self.decisions_path = _temp_path()
        self.ledger_path = _temp_path()

    def tearDown(self):
        for p in (self.decisions_path, self.ledger_path):
            if os.path.exists(p):
                os.remove(p)

    def _record(self, niche, status="ACCEPTED", days_ago=1):
        from datetime import datetime, timedelta, timezone
        decided_at = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
        ladder_result = {
            "accepted": status == "ACCEPTED", "ladder_score": 85.0, "price": 200, "reason": "test",
            "components": {
                "market_demand": 60, "competition_favorability": 70, "profit_potential": 50,
                "recurring_revenue_potential": 90, "reusability": 85, "automation_potential": 40,
            },
            "risk": {"score": 90, "level": "low", "notes": []},
            "confidence": {"score": 55, "level": "متوسطة", "note": "test"},
        }
        # record_ladder_decision always stamps "now" -- patch datetime.now via decided_at override not
        # supported directly, so we post-process the written record's decided_at for real window testing.
        engine.record_ladder_decision(niche, "ai_saas", ladder_result, decisions_path=self.decisions_path)
        self._rewrite_last_decided_at(decided_at)

    def _rewrite_last_decided_at(self, decided_at):
        with open(self.decisions_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        record = json.loads(lines[-1])
        record["decided_at"] = decided_at
        lines[-1] = json.dumps(record) + "\n"
        with open(self.decisions_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

    def test_zero_activity_is_honestly_reported(self):
        report = bip.build_weekly_progress_report(decisions_path=self.decisions_path, ledger_path=self.ledger_path)
        self.assertEqual(report["scored"], 0)
        self.assertEqual(report["real_revenue_this_week"], 0.0)
        self.assertIn("No new opportunities", report["report_markdown"])

    def test_real_recent_decisions_are_counted(self):
        self._record("a recent niche", status="ACCEPTED", days_ago=1)
        self._record("a rejected niche", status="REJECTED", days_ago=2)
        report = bip.build_weekly_progress_report(decisions_path=self.decisions_path, ledger_path=self.ledger_path)
        self.assertEqual(report["scored"], 2)
        self.assertEqual(report["accepted"], 1)
        self.assertEqual(report["rejected"], 1)

    def test_old_decisions_outside_window_are_excluded(self):
        self._record("an old niche", status="ACCEPTED", days_ago=30)
        report = bip.build_weekly_progress_report(decisions_path=self.decisions_path, ledger_path=self.ledger_path)
        self.assertEqual(report["scored"], 0)

    def test_report_never_uses_hype_language(self):
        self._record("a niche", status="ACCEPTED", days_ago=1)
        report = bip.build_weekly_progress_report(decisions_path=self.decisions_path, ledger_path=self.ledger_path)
        for hype_word in ("amazing", "revolutionary", "game-changing", "incredible"):
            self.assertNotIn(hype_word, report["report_markdown"].lower())


class TestDraftAdrPost(unittest.TestCase):
    def test_reuses_the_real_orchestrator_never_a_second_path(self):
        fd, adr_path = tempfile.mkstemp(suffix=".md")
        os.close(fd)
        try:
            with open(adr_path, "w", encoding="utf-8") as f:
                f.write("# ADR-999 Test\nSome real decision content.")
            with patch("ai_capability.orchestrator.generate", return_value={"content": "draft text", "provider": "groq", "selection": {}}) as mock_gen:
                result = bip.draft_adr_post(adr_path)
            mock_gen.assert_called_once()
            self.assertEqual(mock_gen.call_args[0][0], "marketing_copy")
            self.assertEqual(result["draft_text"], "draft text")
            self.assertEqual(result["provider"], "groq")
        finally:
            os.remove(adr_path)


class TestQueueDraftForApproval(unittest.TestCase):
    def test_writes_a_real_file_and_sends_telegram(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("channels.telegram_direct.send_telegram_message", return_value={"sent": True, "message_id": 1, "error": None}) as mock_send:
                result = bip.queue_draft_for_approval(
                    "weekly_report", "Test Draft", "# Real content", "ملخص عربي حقيقي", drafts_dir=tmpdir,
                )
            mock_send.assert_called_once()
            self.assertTrue(os.path.exists(result["draft_path"]))
            with open(result["draft_path"], "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "# Real content")
            self.assertTrue(result["telegram"]["sent"])

    def test_never_auto_publishes_only_writes_a_pending_review_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("channels.telegram_direct.send_telegram_message", return_value={"sent": False, "message_id": None, "error": "not configured"}):
                result = bip.queue_draft_for_approval(
                    "adr_post", "Another Draft", "content", "ملخص", drafts_dir=tmpdir,
                )
            # Telegram failure must never block the real file being written --
            # same fail-safe discipline as every other real notification path.
            self.assertTrue(os.path.exists(result["draft_path"]))
            self.assertFalse(result["telegram"]["sent"])


class TestApproveDraft(unittest.TestCase):
    def test_moves_a_real_draft_from_pending_to_approved(self):
        with tempfile.TemporaryDirectory() as pending, tempfile.TemporaryDirectory() as approved:
            src = os.path.join(pending, "2026-07-24_weekly_report_test.md")
            with open(src, "w", encoding="utf-8") as f:
                f.write("# Final real content")

            result = bip.approve_draft(
                "2026-07-24_weekly_report_test.md", drafts_dir=pending, approved_dir=approved,
            )

            self.assertTrue(result["approved"])
            self.assertFalse(os.path.exists(src))
            dest = os.path.join(approved, "2026-07-24_weekly_report_test.md")
            self.assertTrue(os.path.exists(dest))
            with open(dest, "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "# Final real content")

    def test_missing_draft_reports_honestly_not_fabricated_success(self):
        with tempfile.TemporaryDirectory() as pending, tempfile.TemporaryDirectory() as approved:
            result = bip.approve_draft("does-not-exist.md", drafts_dir=pending, approved_dir=approved)
            self.assertFalse(result["approved"])
            self.assertIn("not found", result["error"])


class TestBuildPublicSiteStructure(unittest.TestCase):
    def test_real_product_catalog_is_reused_verbatim(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = bip.build_public_site_structure(output_dir=tmpdir)
            self.assertEqual(result["real_product_count"], 5)
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "index.html")))
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "README.md")))
            with open(os.path.join(tmpdir, "products.json"), "r", encoding="utf-8") as f:
                products = json.load(f)
            self.assertEqual(len(products), 5)
            self.assertIn("AI-Powered Compliance Automation System for Accounting Firms", [p["title"] for p in products])

    def test_never_creates_or_pushes_a_real_github_repo(self):
        """This function must only ever write real local files -- never
        shell out to git/gh or make any network call."""
        import inspect
        source = inspect.getsource(bip.build_public_site_structure)
        for forbidden in ("subprocess", "git push", "gh repo", "requests."):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()

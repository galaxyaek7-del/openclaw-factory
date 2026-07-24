"""Tests for scripts/weekly_public_report.py (Build in Public, 2026-07-24):
the real cron entrypoint invoked by the durable Windows Scheduled Task
(ADR-119) every Friday. Mocks build_in_public.py entirely -- never a
real Telegram send or real Groq call in tests.

    python -m unittest tests.test_weekly_public_report_script -v
"""

import importlib.util
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

_SCRIPT_PATH = _FACTORY_ROOT / "scripts" / "weekly_public_report.py"
_spec = importlib.util.spec_from_file_location("weekly_public_report", _SCRIPT_PATH)
weekly_public_report = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(weekly_public_report)


class TestWeeklyPublicReportScript(unittest.TestCase):
    def test_calls_the_real_report_and_queue_functions_reuses_only(self):
        fake_report = {"report_markdown": "# report", "scored": 5, "accepted": 2, "rejected": 1, "real_revenue_this_week": 0.0}
        fake_queue_result = {"draft_path": "p", "filename": "f", "telegram": {"sent": True, "error": None}}
        with patch("build_in_public.build_weekly_progress_report", return_value=fake_report) as mock_report, \
             patch("build_in_public.queue_draft_for_approval", return_value=fake_queue_result) as mock_queue, \
             patch("sys.exit") as mock_exit:
            weekly_public_report.main()

        mock_report.assert_called_once_with()
        mock_queue.assert_called_once()
        self.assertEqual(mock_queue.call_args[0][0], "weekly_report")
        mock_exit.assert_not_called()

    def test_exits_nonzero_when_telegram_send_fails(self):
        fake_report = {"report_markdown": "# report", "scored": 0, "accepted": 0, "rejected": 0, "real_revenue_this_week": 0.0}
        fake_queue_result = {"draft_path": "p", "filename": "f", "telegram": {"sent": False, "error": "not configured"}}
        with patch("build_in_public.build_weekly_progress_report", return_value=fake_report), \
             patch("build_in_public.queue_draft_for_approval", return_value=fake_queue_result), \
             patch("sys.exit") as mock_exit:
            weekly_public_report.main()
        mock_exit.assert_called_once_with(1)


if __name__ == "__main__":
    unittest.main()

"""Tests for affiliate_discovery.py — real program discovery + portfolio merge.

    python -m unittest tests.test_affiliate_discovery -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from affiliate_discovery import (
    NEWLY_VERIFIED_PROGRAMS,
    merge_newly_verified_programs,
    discovery_status,
    verify_program_from_official_source,
)
from commission_engine import load_opportunity_portfolio


def _temp_portfolio_path():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(path)
    return path


class TestVerifiedProgramsData(unittest.TestCase):
    def test_all_new_programs_are_verified_with_official_urls(self):
        for p in NEWLY_VERIFIED_PROGRAMS:
            self.assertEqual(p["verification_status"], "VERIFIED", p["opportunity_id"])
            self.assertTrue(p["evidence_url"], f"{p['opportunity_id']} lacks evidence_url")
            for u in p["evidence_url"]:
                self.assertTrue(u.startswith("https://"), f"{p['opportunity_id']} evidence not https")
            self.assertEqual(p["last_verified"], "2026-08-14")

    def test_recurring_programs_correctly_marked(self):
        recurring = {p["opportunity_id"] for p in NEWLY_VERIFIED_PROGRAMS if p["recurring_commission"]}
        self.assertIn("CO-aweber-affiliate", recurring)
        self.assertIn("CO-digitalocean-affiliate", recurring)
        # SiteGround is one-time per sale, Brevo is CPA flat
        self.assertNotIn("CO-siteground-affiliate", recurring)
        self.assertNotIn("CO-brevo-affiliate", recurring)


class TestMerge(unittest.TestCase):
    def test_merge_adds_new_and_is_idempotent(self):
        path = _temp_portfolio_path()
        try:
            # Seed the temp file with the real portfolio snapshot MINUS the
            # 4 new programs (so the merge has something real to add).
            real = load_opportunity_portfolio()
            new_ids = {p["opportunity_id"] for p in NEWLY_VERIFIED_PROGRAMS}
            seed = [o for o in real if o.get("opportunity_id") not in new_ids]
            from commission_engine import save_opportunity_portfolio
            save_opportunity_portfolio(seed, path)
            r1 = merge_newly_verified_programs(path, record_merge=False)
            self.assertEqual(len(r1["added"]), 4)
            self.assertEqual(r1["total_portfolio_size"], len(seed) + 4)
            # 2nd run: nothing added, everything already present.
            r2 = merge_newly_verified_programs(path, record_merge=False)
            self.assertEqual(r2["added"], [])
            self.assertEqual(len(r2["already_present"]), 4)
            # File has exactly seed+4 lines.
            lines = [l for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
            self.assertEqual(len(lines), len(seed) + 4)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_merge_on_real_portfolio_is_honest_about_existing(self):
        # Running against the real portfolio must report 4 added exactly once.
        r = merge_newly_verified_programs(record_merge=False)
        self.assertEqual(r["added"], [])
        self.assertEqual(len(r["already_present"]), 4)
        # And never reduce the real portfolio.
        self.assertGreaterEqual(r["total_portfolio_size"], 17)


class TestVerifyFunction(unittest.TestCase):
    def test_refuses_to_verify_without_official_url(self):
        path = _temp_portfolio_path()
        try:
            res = verify_program_from_official_source("CO-x-affiliate", "", "", path)
            self.assertEqual(res["verification_status"], "UNVERIFIED")
        finally:
            if os.path.exists(path):
                os.remove(path)


if __name__ == "__main__":
    unittest.main()
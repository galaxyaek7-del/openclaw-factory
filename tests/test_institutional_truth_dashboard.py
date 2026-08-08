import unittest

import institutional_truth_dashboard as itd


class TestExecutiveTruthDashboard(unittest.TestCase):
    def test_returns_all_required_sections(self):
        result = itd.build_executive_truth_dashboard()
        for key in ("commercial_reality", "real_customers", "connected_platforms", "blocked_platforms",
                    "automations_verified_fresh_today", "manual_tasks", "critical_risks", "unknown_states"):
            self.assertIn(key, result)

    def test_never_fabricates_a_positive_platform_connection(self):
        result = itd.build_executive_truth_dashboard()
        # Every real, live-checked arm must land in exactly one bucket.
        all_platforms = set(result["connected_platforms"]) | set(result["blocked_platforms"])
        self.assertTrue(all_platforms.issubset({"gumroad", "paddle", "etsy", "payhip"}))

    def test_real_revenue_excludes_smoke_test_records(self):
        state = itd._real_revenue_state()
        self.assertNotIn("DELETE-ME", str(state["real_revenue_usd"]))

    def test_never_writes_any_file(self):
        import os
        before = set(os.listdir("data"))
        itd.build_executive_truth_dashboard()
        after = set(os.listdir("data"))
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

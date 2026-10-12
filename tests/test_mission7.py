#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mission 7 tests (offline; live X verification ran separately, read-only)."""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))


class TestMission7(unittest.TestCase):
    def test_oauth_signer_shape(self):
        from channels import x_verify as xv
        with patch("urllib.request.urlopen") as uo:
            class R:
                def read(self):
                    return json.dumps({"data": {"username": "u", "id": "1"}}).encode()

                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    return False
            uo.return_value = R()
            with patch.dict("os.environ", {"X_API_KEY": "k", "X_API_SECRET": "s",
                                           "X_ACCESS_TOKEN": "t", "X_ACCESS_TOKEN_SECRET": "ts"}):
                r = xv.verify_credentials()
        self.assertTrue(r["valid"])
        # Authorization header used, no POST anywhere
        sent_req = uo.call_args[0][0]
        self.assertIn("OAuth", sent_req.headers.get("Authorization", ""))
        self.assertNotIn("POST", str(sent_req.get_method()))

    def test_mission7_record(self):
        rec = json.loads((_FACTORY_ROOT / "data" / "mission7.json").read_text(encoding="utf-8"))
        self.assertEqual(rec["spend"], 0)
        self.assertIn("x_draft_status", rec)
        self.assertTrue(rec["x_draft_status"].startswith("UNPUBLISHED"))

    def test_draft_honest(self):
        rec = json.loads((_FACTORY_ROOT / "data" / "mission7.json").read_text(encoding="utf-8"))
        d = rec["x_draft"].lower()
        self.assertLessEqual(len(rec["x_draft"]), 280)
        for claim in ("guaranteed", "testimonial", "passive income", "risk-free"):
            self.assertNotIn(claim, d)


if __name__ == "__main__":
    unittest.main(verbosity=2)

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import standing_authorization as sa  # noqa: E402
import quality_gate_policy as qgp  # noqa: E402

NOW = datetime(2026, 11, 20, tzinfo=timezone.utc)
ON = {sa.ENV_SWITCH: "true"}
OPEN = lambda: {"open": True, "why": "real demand recorded: SALE"}  # noqa: E731
CLOSED = lambda: {"open": False, "why": "WAITING FOR REAL DATA"}  # noqa: E731


def auth(**over):
    a = {"authorization_id": "SA-T1", "status": "ACTIVE", "granted_by": "founder",
         "valid_from": "2026-11-05T00:00:00Z", "expires_at": "2027-02-03T00:00:00Z",
         "reference": "Founder in-session order 2026-11-05, a verbatim quote of at least twenty chars",
         "scope": {"platforms": ["gumroad"], "product_types": ["printable"], "max_price_usd": 29}}
    a.update(over)
    return a


class StandingAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "sa.json")

    def write(self, *auths):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"authorizations": list(auths)}, f)

    def cov(self, price=15, ptype="printable", platform="gumroad", demand=OPEN, env=ON, now=NOW):
        return sa.covers(product=SimpleNamespace(price_usd=price), product_type=ptype, platform=platform,
                         path=self.path, now=now, demand_fn=demand, environ=env)

    def test_switch_off_or_no_file_covers_nothing(self):
        self.write(auth())
        self.assertFalse(self.cov(env={})["covered"])
        os.remove(self.path)
        self.assertFalse(self.cov()["covered"])

    def test_a_product_inside_scope_with_demand_is_covered(self):
        self.write(auth())
        r = self.cov()
        self.assertTrue(r["covered"])
        self.assertEqual("SA-T1", r["authorization_id"])

    def test_no_demand_means_no_cover(self):
        self.write(auth())
        r = self.cov(demand=CLOSED)
        self.assertFalse(r["covered"])
        self.assertIn("demand gate closed", r["reason"])

    def test_a_broken_demand_gate_fails_closed(self):
        self.write(auth())

        def boom():
            raise RuntimeError("x")
        self.assertFalse(self.cov(demand=boom)["covered"])

    def test_scope_limits_price_type_and_platform(self):
        self.write(auth())
        self.assertFalse(self.cov(price=30)["covered"])
        self.assertFalse(self.cov(price=0)["covered"])
        self.assertFalse(self.cov(price=None)["covered"])
        self.assertFalse(self.cov(ptype="premium")["covered"])
        self.assertFalse(self.cov(platform="etsy")["covered"])

    def test_revoked_expired_forged_or_unquoted_authorizations_do_not_count(self):
        for bad in (auth(status="REVOKED"), auth(granted_by="agent"), auth(reference="short"),
                    auth(expires_at="2026-11-10T00:00:00Z"), auth(valid_from="2027-01-01T00:00:00Z"),
                    auth(expires_at="not a date")):
            self.write(bad)
            self.assertFalse(self.cov()["covered"], bad)


class GateHookTests(unittest.TestCase):
    """quality_gate_policy._apply_standing_authorization: only a MISSING Gate 2 can be satisfied."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "sa.json")
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"authorizations": [auth()]}, f)
        self.product = SimpleNamespace(price_usd=12, product_type="printable")
        self._orig = sa.DEFAULT_PATH
        sa.DEFAULT_PATH = type(self._orig)(self.path)
        self.addCleanup(lambda: setattr(sa, "DEFAULT_PATH", self._orig))
        os.environ[sa.ENV_SWITCH] = "true"
        self.addCleanup(lambda: os.environ.pop(sa.ENV_SWITCH, None))
        import demand_gate
        self._dg = demand_gate.evaluate
        demand_gate.evaluate = lambda *a, **k: {"open": True, "why": "test"}
        self.addCleanup(lambda: setattr(demand_gate, "evaluate", self._dg))

    def hook(self, g2):
        return qgp._apply_standing_authorization(g2, self.product, None, "gumroad")

    def test_missing_becomes_a_clearly_marked_standing_pass(self):
        out = self.hook({"passed": False, "status": "MISSING", "decision": None})
        self.assertTrue(out["passed"])
        self.assertEqual("APPROVED_STANDING", out["decision"])
        self.assertEqual("standing:SA-T1", out["reviewer"])
        self.assertIn("not a per-product sign-off", out["notes"])

    def test_a_recorded_founder_decision_is_never_overridden(self):
        for status in ("BLOCK", "STALE", "MISMATCH"):
            g2 = {"passed": False, "status": status, "decision": "REJECTED"}
            self.assertEqual(g2, self.hook(g2), status)
        ok = {"passed": True, "status": "ok", "decision": "APPROVED"}
        self.assertEqual(ok, self.hook(ok))

    def test_with_the_switch_off_the_gate_stays_missing(self):
        os.environ.pop(sa.ENV_SWITCH, None)
        out = self.hook({"passed": False, "status": "MISSING", "decision": None})
        self.assertFalse(out["passed"])
        self.assertFalse(out["standing_authorization"]["covered"])

    def test_out_of_scope_product_stays_missing(self):
        self.product = SimpleNamespace(price_usd=99, product_type="printable")
        self.assertFalse(self.hook({"passed": False, "status": "MISSING", "decision": None})["passed"])


if __name__ == "__main__":
    unittest.main()

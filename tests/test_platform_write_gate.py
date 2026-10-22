"""Cross-platform live-write gate (2026-10-22).

FACTORY_LIVE_PUBLISH used to protect only channels/gumroad_publisher.py.
These tests prove the default is refusal everywhere else, directly and via
the arms, with every network call mocked to fail the test if reached.

    python -m pytest tests/test_platform_write_gate.py -q
"""
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from channels import write_gate as wg  # noqa: E402
from channels import paddle_publisher as pp  # noqa: E402
from channels import etsy_publisher as ep  # noqa: E402

CLEAN_ENV = {"FACTORY_LIVE_PUBLISH": "", wg.CHECKOUT_ENV: "", wg.MESSAGE_ENV: ""}
NO_NET = AssertionError("network must not be reached")


def no_network():
    return patch.multiple("requests", post=lambda *a, **k: (_ for _ in ()).throw(NO_NET),
                          put=lambda *a, **k: (_ for _ in ()).throw(NO_NET),
                          patch=lambda *a, **k: (_ for _ in ()).throw(NO_NET))


@patch.dict(os.environ, CLEAN_ENV)
class TestDefaultRefusal(unittest.TestCase):
    def test_paddle_catalog_mutations_refuse_before_any_request(self):
        with no_network():
            for call in (lambda: pp.create_product("k", {"title": "T"}),
                         lambda: pp.update_product("k", "pro_1", {"name": "x"}),
                         lambda: pp.create_price("k", "pro_1", {"unit_price": 100}),
                         lambda: pp.create_checkout_transaction("k", "pri_1")):
                with self.assertRaises(wg.WriteNotAuthorized):
                    call()

    def test_etsy_create_refuses(self):
        with no_network(), self.assertRaises(wg.WriteNotAuthorized):
            ep.create_product("k", "t", "shop", {"title": "T"})

    def test_x_arm_live_publish_returns_blocked_without_network(self):
        from channels.x_arm import XArm
        from channels.base_arm import ArmStatus
        arm = XArm()
        with patch.object(XArm, "status", return_value=ArmStatus.READY), \
             patch.object(XArm, "_supports", return_value=True, create=True), no_network():
            r = arm.publish({"title": "T", "description": "d", "url": "https://x", "price_usd": 10.0},
                            dry_run=False)
        self.assertFalse(r.ok)
        self.assertIn("write gate", r.error or "")

    def test_indirect_path_paddle_arm_live_publish_is_refused(self):
        from channels.paddle_arm import PaddleArm
        from schemas.product import Product
        product = Product.from_jsonl_record({"title": "T", "topic": "d", "price": 10.0, "path": __file__})
        from channels.base_arm import ArmStatus
        with patch.object(pp, "load_api_key", return_value="k"),              patch.object(PaddleArm, "status", return_value=ArmStatus.READY),              patch.object(PaddleArm, "supports", return_value=True), no_network():
            r = PaddleArm().publish(product, dry_run=False)
        self.assertFalse(r.ok)
        self.assertIn("live mutation disabled", r.error or "")


class TestFlagSemantics(unittest.TestCase):
    def test_checkout_has_its_own_switch(self):
        with patch.dict(os.environ, dict(CLEAN_ENV, **{wg.CHECKOUT_ENV: "true"})):
            self.assertTrue(wg.check_platform_write("paddle", "tx", checkout=True).allowed)
            self.assertFalse(wg.check_platform_write("paddle", "create_product").allowed)

    def test_live_publish_does_not_authorize_messages(self):
        with patch.dict(os.environ, dict(CLEAN_ENV, FACTORY_LIVE_PUBLISH="true")):
            self.assertTrue(wg.check_platform_write("paddle", "create_product").allowed)
            self.assertFalse(wg.check_platform_write("outreach", "contact_form", message=True).allowed)
        with patch.dict(os.environ, dict(CLEAN_ENV, **{wg.MESSAGE_ENV: "true"})):
            self.assertTrue(wg.check_platform_write("outreach", "contact_form", message=True).allowed)

    def test_contradictory_or_junk_values_deny(self):
        for v in ("", "0", "false", "no", "maybe", "TRUE-ish"):
            with patch.dict(os.environ, dict(CLEAN_ENV, FACTORY_LIVE_PUBLISH=v)):
                self.assertFalse(wg.check_platform_write("etsy", "create_product").allowed, v)


@patch.dict(os.environ, CLEAN_ENV)
class TestScriptsRefuse(unittest.TestCase):
    def test_outreach_contact_forms_are_blocked(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import direct_customer_outreach as dco
        with patch.object(dco.urllib.request, "urlopen", side_effect=NO_NET):
            self.assertEqual(dco.reach_out_to_easecert()["status"], "blocked")
            self.assertEqual(dco.reach_out_to_euverify()["status"], "blocked")

    def test_direct_gumroad_put_script_is_gated(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        src = (ROOT / "scripts" / "upgrade_thin_descriptions.py").read_text(encoding="utf-8")
        body = src[src.index("def put_description"):]
        self.assertLess(body.index("check_write_authorization"), body.index("requests.put"))

    def test_module_level_publishers_exit_before_network(self):
        env = {k: v for k, v in os.environ.items() if k not in CLEAN_ENV}
        env["PYTHONIOENCODING"] = "utf-8"
        for script in ("scripts/publish_telegraph_ftc.py", "scripts/submit_indexnow_round2.py"):
            r = subprocess.run([sys.executable, script], cwd=ROOT, env=env, capture_output=True,
                               text=True, timeout=60)
            self.assertNotEqual(r.returncode, 0, script)
            self.assertIn("WriteNotAuthorized", r.stderr, script)


class TestCoverageInventory(unittest.TestCase):
    """Every tracked file that sends a write to a known external platform host
    must reference the write gate, or be listed here with the reason it is
    exempt. A new unguarded write path fails this test."""

    HOSTS = re.compile(r"api\.gumroad\.com|api\.paddle\.com|sandbox-api\.paddle|openapi\.etsy\.com|api\.x\.com|"
                       r"api\.twitter\.com|api\.telegra\.ph|indexnow|freelancer\.com/api|api\.linkedin\.com|"
                       r"easecert\.com|euverify")
    WRITE = re.compile(r"requests\.(post|put|patch|delete)\(|_requests\.post\(|method=['\"](POST|PUT|PATCH|DELETE)|"
                       r"Request\([^)]*data=|urlopen\([^)]*data=|_api_post\(|authed\(")
    EXEMPT = {
        "scripts/run_campaign_review.py": "Telegraph getPage/getViews only (POST is the API's read transport)",
        "channels/gumroad_publisher.py": "gated by write_gate.check_write_authorization (stronger Gumroad check)",
        "scripts/integrated_platform_test.py": "writes only to localhost:3000; external calls are GET reads",
        "freelancer_resume.py": "explicit founder order 2026-10-01: one scoped bid on project 40742370 once the "
                                "OAuth grant exists, idempotency key bid-40742370-once; preserved, not overridden",
    }

    def test_every_external_write_file_is_gated_or_explained(self):
        files = subprocess.run(["git", "ls-files", "*.py"], cwd=ROOT, capture_output=True, text=True).stdout.split()
        unguarded = []
        for rel in files:
            if rel.startswith(("tests/", "backups/")):
                continue
            src = (ROOT / rel).read_text(encoding="utf-8", errors="replace")
            if self.HOSTS.search(src) and self.WRITE.search(src) and "write_gate" not in src and rel not in self.EXEMPT:
                unguarded.append(rel)
        self.assertEqual(unguarded, [])


if __name__ == "__main__":
    unittest.main()

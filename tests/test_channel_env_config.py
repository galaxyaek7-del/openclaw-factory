"""Regression tests for channels/env_config.py -- the shared credential
reader every non-Gumroad arm now uses -- and for the X/KDP `.env`
fallback it added. Pure local file I/O; no network, no real `.env`.

    python -m unittest tests.test_channel_env_config -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from channels import env_config, etsy_publisher, paddle_publisher, payhip_publisher
from channels.env_config import read_env_value

_KEYS = ("GF_TEST_KEY", "PADDLE_API_KEY", "PAYHIP_API_KEY", "ETSY_API_KEY",
         "ETSY_ACCESS_TOKEN", "ETSY_SHOP_ID", "X_API_KEY", "X_API_SECRET",
         "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET", "KDP_USERNAME",
         "KDP_SESSION_COOKIE")


class _EnvFileCase(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.env_path = Path(self._dir.name) / ".env"
        p = patch.dict(os.environ, {k: "" for k in _KEYS})
        p.start()
        self.addCleanup(p.stop)

    def write(self, text):
        self.env_path.write_text(text, encoding="utf-8")


class TestReadEnvValue(_EnvFileCase):
    def test_process_env_wins(self):
        self.write("GF_TEST_KEY=from_file\n")
        os.environ["GF_TEST_KEY"] = "from_env"
        self.assertEqual(read_env_value("GF_TEST_KEY", self.env_path), "from_env")

    def test_empty_process_env_falls_back_to_file(self):
        self.write("GF_TEST_KEY=from_file\n")
        self.assertEqual(read_env_value("GF_TEST_KEY", self.env_path), "from_file")

    def test_longer_key_sharing_prefix_is_not_matched(self):
        # The old payhip/paddle/etsy readers matched by bare prefix and
        # would have returned "sandbox" here.
        self.write("GF_TEST_KEY_SANDBOX=sandbox\nGF_TEST_KEY=live\n")
        self.assertEqual(read_env_value("GF_TEST_KEY", self.env_path), "live")
        self.write("GF_TEST_KEY_SANDBOX=sandbox\n")
        self.assertEqual(read_env_value("GF_TEST_KEY", self.env_path), "")

    def test_quotes_export_and_inline_comment_are_stripped(self):
        self.write('export GF_TEST_KEY="abc123"  # rotated monthly\n')
        self.assertEqual(read_env_value("GF_TEST_KEY", self.env_path), "abc123")
        self.write("GF_TEST_KEY='xyz'\n")
        self.assertEqual(read_env_value("GF_TEST_KEY", self.env_path), "xyz")

    def test_key_line_without_equals_does_not_raise(self):
        # The old readers raised IndexError on this line.
        self.write("GF_TEST_KEY\n# GF_TEST_KEY=commented\n")
        self.assertEqual(read_env_value("GF_TEST_KEY", self.env_path), "")

    def test_missing_file_returns_empty(self):
        self.assertEqual(read_env_value("GF_TEST_KEY", self.env_path / "nope"), "")


class TestPublishersUseSharedReader(_EnvFileCase):
    def test_paddle_quoted_key_is_unquoted(self):
        self.write('PADDLE_API_KEY_SANDBOX=wrong\nPADDLE_API_KEY="pdl_live_x"\n')
        self.assertEqual(paddle_publisher.load_api_key(self.env_path), "pdl_live_x")

    def test_paddle_missing_still_raises_config_error(self):
        self.write("PADDLE_API_KEY_SANDBOX=wrong\n")
        with self.assertRaises(paddle_publisher.ConfigError):
            paddle_publisher.load_api_key(self.env_path)

    def test_payhip_prefix_collision_and_missing(self):
        self.write("PAYHIP_API_KEY_OLD=old\n")
        with self.assertRaises(payhip_publisher.ConfigError):
            payhip_publisher.load_token(self.env_path)
        self.write("PAYHIP_API_KEY=ph_live\n")
        self.assertEqual(payhip_publisher.load_token(self.env_path), "ph_live")

    def test_etsy_requires_all_three(self):
        self.write("ETSY_API_KEY=k\nETSY_ACCESS_TOKEN_EXPIRES=123\nETSY_SHOP_ID=9\n")
        with self.assertRaises(etsy_publisher.ConfigError):
            etsy_publisher.load_credentials(self.env_path)
        self.write("ETSY_API_KEY=k\nETSY_ACCESS_TOKEN=t\nETSY_SHOP_ID=9\n")
        self.assertEqual(etsy_publisher.load_credentials(self.env_path), ("k", "t", "9"))


class TestArmEnvFileFallback(_EnvFileCase):
    def test_x_arm_reads_credentials_from_env_file(self):
        from channels import x_arm
        self.write("X_API_KEY=a\nX_API_SECRET=b\nX_ACCESS_TOKEN=c\nX_ACCESS_TOKEN_SECRET=d\n")
        with patch.object(x_arm, "DEFAULT_ENV_PATH", self.env_path):
            self.assertEqual(x_arm._load_credentials(), ("a", "b", "c", "d"))

    def test_x_arm_partial_file_is_still_missing(self):
        from channels import x_arm
        self.write("X_API_KEY=a\nX_API_SECRET=b\n")
        with patch.object(x_arm, "DEFAULT_ENV_PATH", self.env_path):
            with self.assertRaises(x_arm._ConfigError):
                x_arm._load_credentials()

    def test_kdp_arm_reads_credentials_from_env_file(self):
        from channels import kdp_arm
        self.write("KDP_USERNAME=u\nKDP_SESSION_COOKIE=c\n")
        with patch.object(env_config, "DEFAULT_ENV_PATH", self.env_path):
            self.assertEqual(kdp_arm.KdpArm._load_credentials(), ("u", "c"))
        with patch.object(env_config, "DEFAULT_ENV_PATH", self.env_path / "nope"):
            with self.assertRaises(kdp_arm.ConfigError):
                kdp_arm.KdpArm._load_credentials()


if __name__ == "__main__":
    unittest.main()

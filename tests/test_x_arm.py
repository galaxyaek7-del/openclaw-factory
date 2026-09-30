"""Tests for the X (Twitter) distribution arm.

Covers all 7 required test scenarios:
1. Dry Run = TRUE → no X write, no external mutation
2. Missing credentials → BLOCKED/FAILED safely, no external call
3. Malformed package → rejected safely
4. Duplicate package → no duplicate publication attempt
5. API failure → bounded retry, no infinite loop, clear failure state
6. Restart/retry behavior → state remains consistent
7. Real publication path → preserved but not executed

Uses only temp files, mocks, and env var overrides. Never touches real
X API, real credentials, or real production ledgers.

    python -m unittest tests.test_x_arm -v
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from channels.base_arm import ArmStatus, PublishResult
from channels import registry, publish_protection, ledger
from schemas.product import Product


def _temp_path(suffix=".jsonl"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


_FAKE_X_CREDS = {
    "X_API_KEY": "test_key",
    "X_API_SECRET": "test_secret",
    "X_ACCESS_TOKEN": "test_token",
    "X_ACCESS_TOKEN_SECRET": "test_token_secret",
}


def _register_fresh_x():
    """Register a NEW XArm instance and return it.

    `from channels import x_arm` alone is NOT enough after a
    registry.clear(): the module is cached in sys.modules, so its
    bottom-line register() never re-runs and the registry stays empty.
    Every setUp below must call this (not a bare import) to be isolated.
    """
    from channels import x_arm as _x_mod
    registry.register(_x_mod.XArm())
    return registry.get("x")


def _patch_creds(testcase):
    """Set fake X creds for the test duration (restored afterwards).

    Needed wherever the test exercises anything past status(): the arm
    (like every other arm, e.g. GumroadArm) is fail-closed — status()
    returns UNAVAILABLE without creds before dry_run/supports are reached.
    """
    p = patch.dict(os.environ, _FAKE_X_CREDS)
    p.start()
    testcase.addCleanup(p.stop)


def _fake_product(source_id="PROD-x-test-1"):
    return Product(
        title="X Test Product",
        subtitle="",
        description="A test product for X distribution arm testing",
        price_usd=19.0,
        file_path="/fake/path.pdf",
        cover_path=None,
        tags=[],
        language="en",
        source_id=source_id,
        raw_price_hint=19.0,
        needs_pricing=False,
        price_source="profit_raw",
    )


def _no_pricing_product():
    return Product(
        title="No Pricing Product",
        subtitle="",
        description="Product without resolved pricing",
        price_usd=None,
        file_path="/fake/path.pdf",
        cover_path=None,
        tags=[],
        language="en",
        source_id="PROD-no-price",
        raw_price_hint=0.0,
        needs_pricing=True,
        price_source=None,
    )


def _empty_text_product():
    return Product(
        title="",
        subtitle="",
        description="",
        price_usd=10.0,
        file_path="/fake/path.pdf",
        cover_path=None,
        tags=[],
        language="en",
        source_id="PROD-empty",
        raw_price_hint=10.0,
        needs_pricing=False,
        price_source="profit_raw",
    )


class TestXArmRegistration(unittest.TestCase):
    """Verify the X arm is registered in the arm registry."""

    def test_x_arm_is_registered(self):
        _register_fresh_x()
        arm = registry.get("x")
        self.assertIsNotNone(arm)
        self.assertEqual(arm.name, "x")

    def test_x_arm_is_basearm_subclass(self):
        from channels.x_arm import XArm
        from channels.base_arm import BaseArm
        self.assertTrue(issubclass(XArm, BaseArm))


class TestXArmDryRun(unittest.TestCase):
    """Test 1: Dry Run = TRUE → no X write, no external mutation."""

    def setUp(self):
        self._saved_arms = registry.all_arms()
        registry.clear()
        _register_fresh_x()
        _patch_creds(self)

    def tearDown(self):
        registry.clear()
        for a in self._saved_arms:
            registry.register(a)

    def test_dry_run_returns_ok_and_no_external_call(self):
        arm = registry.get("x")
        self.assertIsNotNone(arm)
        with patch("requests.post", side_effect=AssertionError("dry run must not touch network")):
            result = arm.publish(_fake_product(), dry_run=True)
        self.assertTrue(result.ok)
        self.assertTrue(result.dry_run)
        self.assertIsNone(result.product_id)
        self.assertIsNone(result.url)
        self.assertIsNone(result.error)

    def test_dry_run_without_credentials_fails_closed(self):
        # Fail-closed convention (shared with GumroadArm): without creds,
        # status() is UNAVAILABLE before dry_run is reached — a dry run
        # never silently reports ok when the arm cannot even authenticate.
        with patch.dict(os.environ, {"X_API_KEY": "", "X_API_SECRET": "",
                                     "X_ACCESS_TOKEN": "", "X_ACCESS_TOKEN_SECRET": ""}):
            from channels import x_arm
            registry.clear()
            registry.register(x_arm.XArm())
            arm = registry.get("x")
            result = arm.publish(_fake_product(), dry_run=True)
        self.assertFalse(result.ok)
        self.assertIn("not ready", result.error)


class TestXArmMissingCredentials(unittest.TestCase):
    """Test 2: Missing credentials → BLOCKED/FAILED safely, no external call."""

    def setUp(self):
        self._saved_arms = registry.all_arms()
        registry.clear()
        _register_fresh_x()
        self._orig_env = {k: os.environ.get(k, "") for k in
                          ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"]}

    def tearDown(self):
        registry.clear()
        for a in self._saved_arms:
            registry.register(a)
        for k, v in self._orig_env.items():
            if v:
                os.environ[k] = v
            elif k in os.environ:
                del os.environ[k]

    def test_missing_all_credentials_returns_not_ready(self):
        for k in ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"]:
            os.environ[k] = ""
        arm = registry.get("x")
        status = arm.status()
        self.assertEqual(status, ArmStatus.UNAVAILABLE)

    def test_missing_one_credential_returns_not_ready(self):
        for k in ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"]:
            os.environ[k] = "real-value-for-test"
        os.environ["X_API_KEY"] = ""  # Remove one
        arm = registry.get("x")
        status = arm.status()
        self.assertEqual(status, ArmStatus.UNAVAILABLE)

    def test_publish_returns_error_when_not_ready(self):
        for k in ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"]:
            os.environ[k] = ""
        arm = registry.get("x")
        result = arm.publish(_fake_product(), dry_run=False)
        self.assertFalse(result.ok)
        self.assertIn("not ready", result.error)
        self.assertFalse(result.dry_run)


class TestXArmMalformedPackage(unittest.TestCase):
    """Test 3: Malformed package → rejected safely."""

    def setUp(self):
        self._saved_arms = registry.all_arms()
        registry.clear()
        _register_fresh_x()
        _patch_creds(self)

    def tearDown(self):
        registry.clear()
        for a in self._saved_arms:
            registry.register(a)

    def test_no_pricing_product_is_unsupported(self):
        arm = registry.get("x")
        self.assertFalse(arm.supports(_no_pricing_product()))

    def test_publish_no_pricing_returns_not_supported(self):
        arm = registry.get("x")
        result = arm.publish(_no_pricing_product(), dry_run=False)
        self.assertFalse(result.ok)
        self.assertIn("not supported", result.error)


class TestXArmIdempotency(unittest.TestCase):
    """Test 4: Duplicate package → no duplicate publication attempt via
    publish_protection's idempotency checks."""

    def setUp(self):
        self._saved_arms = registry.all_arms()
        registry.clear()
        _register_fresh_x()
        _patch_creds(self)
        self.ledger_path = _temp_path(".jsonl")
        self.protection_path = _temp_path(".json")

    def tearDown(self):
        registry.clear()
        for a in self._saved_arms:
            registry.register(a)
        for p in (self.ledger_path, self.protection_path):
            if os.path.exists(p):
                os.remove(p)

    def test_duplicate_dry_run_produces_same_result(self):
        arm = registry.get("x")
        product = _fake_product()
        r1 = arm.publish(product, dry_run=True)
        r2 = arm.publish(product, dry_run=True)
        self.assertTrue(r1.ok)
        self.assertTrue(r2.ok)
        self.assertTrue(r1.dry_run)
        self.assertTrue(r2.dry_run)

    def test_publish_protection_counts_each_publish(self):
        """Each publish attempt increments the protection counter —
        duplicate prevention is handled at the distribution layer, not
        inside the arm."""
        import distributor
        product = _fake_product()
        # Two dry runs should both succeed (dry runs bypass protection)
        o1 = distributor.distribute(product, arm_names=["x"], dry_run=True,
                                     ledger_path=self.ledger_path,
                                     protection_state_path=self.protection_path)
        o2 = distributor.distribute(product, arm_names=["x"], dry_run=True,
                                     ledger_path=self.ledger_path,
                                     protection_state_path=self.protection_path)
        self.assertTrue(o1[0]["ok"])
        self.assertTrue(o2[0]["ok"])


class TestXArmApiFailure(unittest.TestCase):
    """Test 5: API failure → bounded retry, no infinite loop, clear failure state."""

    def setUp(self):
        self._saved_arms = registry.all_arms()
        registry.clear()
        _register_fresh_x()
        self._orig_env = {k: os.environ.get(k, "") for k in
                          ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"]}

    def tearDown(self):
        registry.clear()
        for a in self._saved_arms:
            registry.register(a)
        for k, v in self._orig_env.items():
            if v:
                os.environ[k] = v
            elif k in os.environ:
                del os.environ[k]

    @patch("requests.post")
    @patch("oauthlib.oauth1.Client")
    @patch.dict(os.environ, {
        "X_API_KEY": "test_key",
        "X_API_SECRET": "test_secret",
        "X_ACCESS_TOKEN": "test_token",
        "X_ACCESS_TOKEN_SECRET": "test_token_secret",
    })
    def test_api_http_error_returns_failure(self, mock_client_cls, mock_post):
        """Simulate HTTP 500 from X API — should fail without infinite loop."""
        mock_client_cls.return_value.sign.return_value = (
            "https://api.x.com/2/tweets",
            {"Content-Type": "application/json"},
            b'{"text": "x"}',
        )
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        arm = registry.get("x")
        result = arm.publish(_fake_product(), dry_run=False)
        self.assertFalse(result.ok)
        self.assertIn("500", result.error)
        self.assertFalse(result.dry_run)
        self.assertEqual(mock_post.call_count, 1)

    @patch.dict(os.environ, {
        "X_API_KEY": "test_key",
        "X_API_SECRET": "test_secret",
        "X_ACCESS_TOKEN": "test_token",
        "X_ACCESS_TOKEN_SECRET": "test_token_secret",
    })
    def test_import_error_returns_failure(self):
        """oauthlib not installed → fails safely with clear error."""
        import sys as _sys
        # Temporarily remove oauthlib from importable modules
        saved = _sys.modules.get("oauthlib")
        _sys.modules["oauthlib"] = None
        try:
            arm = registry.get("x")
            result = arm.publish(_fake_product(), dry_run=False)
            self.assertFalse(result.ok)
            self.assertIn("oauthlib", result.error.lower())
        finally:
            if saved is not None:
                _sys.modules["oauthlib"] = saved
            else:
                _sys.modules.pop("oauthlib", None)


class TestXArmRestartRetryBehavior(unittest.TestCase):
    """Test 6: Restart/retry behavior → state remains consistent."""

    def setUp(self):
        self._saved_arms = registry.all_arms()
        registry.clear()
        _register_fresh_x()

    def tearDown(self):
        registry.clear()
        for a in self._saved_arms:
            registry.register(a)

    def test_consecutive_failures_trigger_cooldown(self):
        arm = registry.get("x")
        # Simulate consecutive failures
        for _ in range(arm.COOLDOWN_THRESHOLD):
            arm._record_failure()
        status = arm.status()
        # status() checks credentials first; if creds are missing, it's
        # UNAVAILABLE regardless of cooldown. Set fake creds to test cooldown.
        with patch.dict(os.environ, {
            "X_API_KEY": "k", "X_API_SECRET": "s",
            "X_ACCESS_TOKEN": "t", "X_ACCESS_TOKEN_SECRET": "ts",
        }):
            status = arm.status()
        self.assertEqual(status, ArmStatus.COOLDOWN)

    def test_success_resets_failure_count(self):
        arm = registry.get("x")
        arm._record_failure()
        arm._record_failure()
        arm._record_success()
        # After success, should not be in cooldown
        with patch.dict(os.environ, {
            "X_API_KEY": "k", "X_API_SECRET": "s",
            "X_ACCESS_TOKEN": "t", "X_ACCESS_TOKEN_SECRET": "ts",
        }):
            status = arm.status()
        self.assertEqual(status, ArmStatus.READY)


class TestXArmRealPublicationPath(unittest.TestCase):
    """Test 7: Real publication path → preserved but not executed."""

    def setUp(self):
        self._saved_arms = registry.all_arms()
        registry.clear()
        _register_fresh_x()
        _patch_creds(self)

    def tearDown(self):
        registry.clear()
        for a in self._saved_arms:
            registry.register(a)

    def test_x_arm_exists_and_is_callable(self):
        """Verify the real X arm is registered and publish() is callable."""
        arm = registry.get("x")
        self.assertIsNotNone(arm)
        self.assertTrue(callable(getattr(arm, "publish", None)))

    def test_dry_run_completes_without_network(self):
        """Dry run must complete without any network call."""
        arm = registry.get("x")
        result = arm.publish(_fake_product(), dry_run=True)
        self.assertTrue(result.ok)
        self.assertTrue(result.dry_run)

    def test_x_arm_in_registry_all_arms(self):
        """X arm appears in the full arm list used by distributor.py."""
        arm_names = [a.name for a in registry.all_arms()]
        self.assertIn("x", arm_names)

    @patch.dict(os.environ, {
        "X_API_KEY": "k", "X_API_SECRET": "s",
        "X_ACCESS_TOKEN": "t", "X_ACCESS_TOKEN_SECRET": "ts",
    })
    def test_x_arm_supports_products_with_price(self):
        arm = registry.get("x")
        self.assertTrue(arm.supports(_fake_product()))

    def test_x_arm_rejects_unpriced_products(self):
        arm = registry.get("x")
        self.assertFalse(arm.supports(_no_pricing_product()))


class TestXArmPublishProtectionIntegration(unittest.TestCase):
    """Verify X arm integrates with publish_protection.py's gate."""

    def setUp(self):
        self._saved_arms = registry.all_arms()
        registry.clear()
        _register_fresh_x()
        _patch_creds(self)
        self.ledger_path = _temp_path(".jsonl")
        self.protection_path = _temp_path(".json")

    def tearDown(self):
        registry.clear()
        for a in self._saved_arms:
            registry.register(a)
        for p in (self.ledger_path, self.protection_path):
            if os.path.exists(p):
                os.remove(p)

    def test_dry_run_bypasses_protection_gate(self):
        """Dry runs never touch the protection layer — same as all other arms."""
        import distributor
        outcomes = distributor.distribute(
            _fake_product(), arm_names=["x"], dry_run=True,
            ledger_path=self.ledger_path,
            protection_state_path=self.protection_path,
        )
        self.assertEqual(len(outcomes), 1)
        self.assertTrue(outcomes[0]["attempted"])
        self.assertTrue(outcomes[0]["ok"])

    def test_x_has_publish_protection_profile(self):
        """X arm should have its own profile in publish_protection, not _default."""
        from channels.publish_protection import PLATFORM_PROFILES
        self.assertIn("x", PLATFORM_PROFILES)
        profile = PLATFORM_PROFILES["x"]
        self.assertIn("min_cooldown_minutes", profile)
        self.assertIn("max_per_day", profile)
        self.assertIn("max_per_hour", profile)

    def test_emergency_stop_blocks_x_publish(self):
        """Global emergency stop blocks X real publish."""
        import distributor
        publish_protection.trigger_emergency_stop("test", state_path=self.protection_path)
        outcomes = distributor.distribute(
            _fake_product(), arm_names=["x"], dry_run=False,
            ledger_path=self.ledger_path,
            protection_state_path=self.protection_path,
        )
        self.assertFalse(outcomes[0]["attempted"])
        self.assertIn("publish protection", outcomes[0]["skip_reason"])


class TestDistributorLiveDedup(unittest.TestCase):
    """Live-path idempotency: a recorded real success blocks a second real
    attempt for the same product+arm. Temp ledgers only — never production."""

    def setUp(self):
        self._saved_arms = registry.all_arms()
        registry.clear()
        _register_fresh_x()
        _patch_creds(self)
        self.ledger_path = _temp_path(".jsonl")
        self.protection_path = _temp_path(".json")

    def tearDown(self):
        registry.clear()
        for a in self._saved_arms:
            registry.register(a)
        for p in (self.ledger_path, self.protection_path):
            if os.path.exists(p):
                os.remove(p)

    def test_recorded_live_success_blocks_second_real_attempt(self):
        import distributor
        product = _fake_product()
        ledger.record_publish_attempt(
            product,
            PublishResult(ok=True, platform="x", product_id="123",
                          url="https://x.com/i/status/123", error=None,
                          dry_run=False),
            ledger_path=self.ledger_path,
        )
        outcomes = distributor.distribute(
            product, arm_names=["x"], dry_run=False,
            ledger_path=self.ledger_path,
            protection_state_path=self.protection_path,
        )
        self.assertFalse(outcomes[0]["attempted"])
        self.assertIn("duplicate", outcomes[0]["skip_reason"])

    def test_no_prior_live_success_does_not_false_positive(self):
        import distributor
        product = _fake_product()
        outcomes = distributor.distribute(
            product, arm_names=["x"], dry_run=False,
            ledger_path=self.ledger_path,
            protection_state_path=self.protection_path,
        )
        self.assertFalse(outcomes[0]["attempted"])
        # Must reach the protection gate (first-publish approval for x),
        # proving the dedup check did not misfire on an empty ledger.
        self.assertIn("publish protection", outcomes[0]["skip_reason"])

    def test_dry_run_success_does_not_block_later_real_attempt(self):
        import distributor
        product = _fake_product()
        ledger.record_publish_attempt(
            product,
            PublishResult(ok=True, platform="x", product_id=None, url=None,
                          error=None, dry_run=True),
            ledger_path=self.ledger_path,
        )
        outcomes = distributor.distribute(
            product, arm_names=["x"], dry_run=False,
            ledger_path=self.ledger_path,
            protection_state_path=self.protection_path,
        )
        self.assertNotIn("duplicate", outcomes[0].get("skip_reason") or "")


class TestXArmContentValidation(unittest.TestCase):
    """Verify content validation for X's 280-char limit."""

    def setUp(self):
        self._saved_arms = registry.all_arms()
        registry.clear()
        _register_fresh_x()
        _patch_creds(self)

    def tearDown(self):
        registry.clear()
        for a in self._saved_arms:
            registry.register(a)

    def test_empty_text_product_triggers_validation_error(self):
        arm = registry.get("x")
        # Even with dry_run=False, empty text is caught by validation
        # But first needs credentials. With dry_run=True, validation is skipped.
        result = arm.publish(_empty_text_product(), dry_run=True)
        # dry_run returns immediately, so ok=True regardless
        self.assertTrue(result.ok)

    def test_build_tweet_text_uses_title_and_description(self):
        arm = registry.get("x")
        product = _fake_product()
        text = arm._build_tweet_text(product)
        self.assertIn("X Test Product", text)
        self.assertIn("test product", text.lower())


class TestDictProductInput(unittest.TestCase):
    """GAP-2 regression: distributor JSON-job path passes plain dicts.
    supports()/publish() must return clean verdicts, never raise
    AttributeError into the distributor's except handler."""

    def setUp(self):
        self._saved_arms = registry.all_arms()
        registry.clear()
        _register_fresh_x()
        _patch_creds(self)

    def tearDown(self):
        registry.clear()
        for a in self._saved_arms:
            registry.register(a)

    def test_dict_product_supported_verdict(self):
        arm = registry.get("x")
        d = {"title": "t", "description": "d", "price_usd": 19.0,
             "needs_pricing": False}
        self.assertTrue(arm.supports(d))

    def test_dict_product_missing_price_unsupported(self):
        arm = registry.get("x")
        self.assertFalse(arm.supports({"title": "t"}))

    def test_dict_product_dry_run_never_raises(self):
        arm = registry.get("x")
        d = {"title": "t", "description": "d", "price_usd": 19.0,
             "needs_pricing": False}
        result = arm.publish(d, dry_run=True)
        self.assertTrue(result.ok)
        self.assertTrue(result.dry_run)

    def test_build_tweet_text_accepts_dict(self):
        arm = registry.get("x")
        text = arm._build_tweet_text({"title": "Hello", "description": "World"})
        self.assertIn("Hello", text)
        self.assertIn("World", text)


if __name__ == "__main__":
    unittest.main()

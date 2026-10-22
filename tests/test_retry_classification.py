"""Failed real publishes are queued for retry only when a retry can help.

Live evidence (data/sales_ledger.jsonl): X returned "HTTP 402: credits
depleted"; Paddle returned "403 Client Error: Forbidden"; Gumroad returned its
daily creation cap. channels/error_classification.py labelled all of them
UNKNOWN, so distributor.py queued every one for a retry that could never
succeed. These tests pin the classification of those real messages and the
distributor's resulting retry decision.

    python -m pytest tests/test_retry_classification.py -q
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import distributor  # noqa: E402
import factory_state  # noqa: E402
from channels import registry  # noqa: E402
from channels.adapter_contract import ErrorClass  # noqa: E402
from channels.base_arm import PublishResult  # noqa: E402
from channels.error_classification import classify_error, is_retryable  # noqa: E402
from schemas.product import Product  # noqa: E402


def _c(msg):
    return classify_error(Exception(msg))


class TestClassificationOfRealMessages(unittest.TestCase):
    def test_x_credits_depleted_is_a_payment_block(self):
        self.assertEqual(_c('HTTP 402: {"detail":"credits depleted"}'), ErrorClass.PAYMENT_BLOCK)

    def test_paddle_403_is_an_auth_error(self):
        self.assertEqual(
            _c("Paddle get_transactions request failed: 403 Client Error: Forbidden for url"),
            ErrorClass.AUTH_ERROR)
        self.assertEqual(_c("You aren't permitted to perform this request."), ErrorClass.AUTH_ERROR)

    def test_gumroad_daily_cap_is_a_rate_limit(self):
        self.assertEqual(
            _c("Gumroad create_product failed: Sorry, you can only create 10 products per day"),
            ErrorClass.RATE_LIMIT)

    def test_server_errors_are_retryable_platform_errors(self):
        for msg in ("HTTP 500: Internal Server Error", "HTTP 503: Service Unavailable",
                    "502 Bad Gateway"):
            self.assertEqual(_c(msg), ErrorClass.PLATFORM_ERROR, msg)
            self.assertTrue(is_retryable(_c(msg)))

    def test_status_codes_need_a_word_boundary(self):
        # A plain number that merely contains 402/403/5xx digits is not one.
        self.assertEqual(_c("error 4021 in parser"), ErrorClass.UNKNOWN_ERROR)
        self.assertEqual(_c("HTTP 5031"), ErrorClass.UNKNOWN_ERROR)
        self.assertEqual(_c("price 500 USD"), ErrorClass.UNKNOWN_ERROR)


def _product():
    return Product(title="t", subtitle="", description="d", price_usd=19.0,
                   file_path=__file__, cover_path=None, tags=[], language="en",
                   source_id="P-RETRY", raw_price_hint=19.0, needs_pricing=False,
                   price_source="profit_raw")


import os as _gf_os  # noqa: E402  (2026-10-22 live-path opt-in)
from unittest import mock as _gf_mock  # noqa: E402
_gf_patch = _gf_mock.patch


# 2026-10-22: exercises the mocked live distribution path; distributor.py
# and channels/write_gate.py fail closed by default, so it opts in explicitly.
@_gf_patch.dict(_gf_os.environ, {"FACTORY_LIVE_PUBLISH": "true"})
class TestDistributorRetryDecision(unittest.TestCase):
    def setUp(self):
        self._saved = registry.all_arms()
        registry.clear()
        fd, self.ledger = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        fd, self.state = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(self.state)
        self._orig = factory_state.enqueue_retry
        self.queued = []
        factory_state.enqueue_retry = lambda task, error, path=None: self.queued.append(str(error))

    def tearDown(self):
        factory_state.enqueue_retry = self._orig
        registry.clear()
        for a in self._saved:
            registry.register(a)
        for p in (self.ledger, self.state):
            if os.path.exists(p):
                os.remove(p)

    def _publish_failing_with(self, error):
        arm = MagicMock()
        arm.name = "gumroad"  # a proven arm: a new one is (correctly) gated on first publish
        arm.supports.return_value = True
        arm.publish.return_value = PublishResult(ok=False, platform="gumroad", product_id=None,
                                                 url=None, error=error, dry_run=False)
        registry.register(arm)
        distributor.distribute(_product(), arm_names=["gumroad"], dry_run=False,
                               ledger_path=self.ledger, protection_state_path=self.state,
                               allow_protected=True, allow_claim_risk=True,
                               allow_file_defects=True,
                               quality_gate=lambda product, **kw: {"allowed": True, "reason": None})

    def test_credits_depleted_is_not_queued(self):
        self._publish_failing_with('HTTP 402: {"detail":"credits depleted"}')
        self.assertEqual(self.queued, [])

    def test_forbidden_is_not_queued(self):
        self._publish_failing_with("403 Client Error: Forbidden")
        self.assertEqual(self.queued, [])

    def test_server_error_is_still_queued(self):
        self._publish_failing_with("HTTP 503: Service Unavailable")
        self.assertEqual(len(self.queued), 1)

    def test_unknown_error_is_still_queued(self):
        self._publish_failing_with("something nobody has classified yet")
        self.assertEqual(len(self.queued), 1)


if __name__ == "__main__":
    unittest.main()

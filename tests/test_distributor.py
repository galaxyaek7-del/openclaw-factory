"""Tests for distributor.py's real-failed-publish retry-enqueue (Unified
Recovery System §3, 2026-07-18). Never touches the real
data/sales_ledger.jsonl or data/factory_state.json — every test passes
explicit temp paths.

    python -m unittest tests.test_distributor -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import distributor
import factory_state
from channels import registry
from channels.base_arm import PublishResult
from schemas.product import Product


def _temp_path(suffix=".jsonl"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


def _fake_product(source_id="PROD-test-1"):
    return Product(
        title="t", subtitle="", description="d", price_usd=19.0, file_path="/fake/path.pdf",
        cover_path=None, tags=[], language="ar", source_id=source_id, raw_price_hint=19.0,
        needs_pricing=False, price_source="profit_raw",
    )


class TestDistributeRetryEnqueue(unittest.TestCase):
    def setUp(self):
        self._saved_arms = registry.all_arms()
        registry.clear()
        self.ledger_path = _temp_path(".jsonl")
        self.state_path = _temp_path(".json")
        self._orig_enqueue_retry = factory_state.enqueue_retry
        self._enqueued = []
        factory_state.enqueue_retry = lambda task, error, path=None: self._enqueued.append((task, str(error)))

    def tearDown(self):
        factory_state.enqueue_retry = self._orig_enqueue_retry
        registry.clear()
        for a in self._saved_arms:
            registry.register(a)
        for p in (self.ledger_path, self.state_path):
            if os.path.exists(p):
                os.remove(p)

    def _register_fake_arm(self, name, publish_result):
        fake_arm = MagicMock()
        fake_arm.name = name
        fake_arm.supports.return_value = True
        fake_arm.publish.return_value = publish_result
        registry.register(fake_arm)
        return fake_arm

    def test_real_failed_publish_is_enqueued_for_retry(self):
        self._register_fake_arm("gumroad", PublishResult(
            ok=False, platform="gumroad", product_id=None, url=None,
            error="Gumroad API request failed: timeout", dry_run=False,
        ))
        distributor.distribute(_fake_product(), ledger_path=self.ledger_path)
        self.assertEqual(len(self._enqueued), 1)
        self.assertEqual(self._enqueued[0][0], "arm_publish:gumroad:PROD-test-1")

    def test_dry_run_failure_is_never_enqueued(self):
        self._register_fake_arm("gumroad", PublishResult(
            ok=False, platform="gumroad", product_id=None, url=None,
            error="whatever", dry_run=True,
        ))
        distributor.distribute(_fake_product(), dry_run=True, ledger_path=self.ledger_path)
        self.assertEqual(self._enqueued, [])

    def test_arm_not_ready_failure_is_never_enqueued(self):
        """Retrying can't fix a missing API key -- only a real connectivity/
        transient failure is worth remembering."""
        self._register_fake_arm("paddle", PublishResult(
            ok=False, platform="paddle", product_id=None, url=None,
            error="arm not ready: unavailable", dry_run=False,
        ))
        distributor.distribute(_fake_product(), ledger_path=self.ledger_path)
        self.assertEqual(self._enqueued, [])

    def test_successful_publish_is_never_enqueued(self):
        self._register_fake_arm("gumroad", PublishResult(
            ok=True, platform="gumroad", product_id="p1", url="http://x",
            error=None, dry_run=False,
        ))
        distributor.distribute(_fake_product(), ledger_path=self.ledger_path)
        self.assertEqual(self._enqueued, [])


if __name__ == "__main__":
    unittest.main()

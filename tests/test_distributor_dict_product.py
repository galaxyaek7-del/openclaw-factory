"""distribute() must accept a plain dict product without any arm raising.

Live evidence (data/sales_ledger.jsonl, 2026-10-01): a dict job made
gumroad, etsy, payhip and paddle each record "arm raised unexpectedly:
'dict' object has no attribute 'file_path'", because BaseArm.supports()
reads attributes. distribute() now converts a dict to a Product at the
boundary. The stub arm below is READY regardless of environment, so the
supports() path really runs in CI too (with no credentials every real arm
would stop at "not ready" and the test would prove nothing).

    python -m pytest tests/test_distributor_dict_product.py -q
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import distributor  # noqa: E402
from channels import registry  # noqa: E402
from channels.base_arm import ArmStatus, BaseArm, PublishResult  # noqa: E402
from schemas.product import Product  # noqa: E402


class _ReadyStubArm(BaseArm):
    """Uses BaseArm.supports() unchanged: the exact code that crashed."""
    name = "stub_ready"

    def __init__(self):
        super().__init__()
        self.seen = []

    def status(self):
        return ArmStatus.READY

    def publish(self, product, dry_run=True):
        self.seen.append(product)
        return PublishResult(ok=True, platform=self.name, product_id=None, url=None,
                             error=None, dry_run=dry_run)


class TestDictProduct(unittest.TestCase):
    def setUp(self):
        self._saved = registry.all_arms()
        registry.clear()
        self.arm = _ReadyStubArm()
        registry.register(self.arm)
        fd, self.ledger = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)

    def tearDown(self):
        registry.clear()
        for a in self._saved:
            registry.register(a)
        os.remove(self.ledger)

    def _run(self, product):
        return distributor.distribute(product, arm_names=["stub_ready"], dry_run=True,
                                      ledger_path=self.ledger)

    def test_dict_job_gets_an_honest_outcome_not_an_exception(self):
        # A raw "price" in a record is only a hint until economics resolves
        # it (no arm may invent a price), so this job is honestly
        # "unsupported product" -- what matters is that no arm raised.
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4 test")
        try:
            out = self._run({"title": "Dict Job", "path": f.name, "price": 12})
        finally:
            os.remove(f.name)
        blob = repr(out)
        self.assertNotIn("raised unexpectedly", blob)
        self.assertNotIn("has no attribute", blob)
        self.assertEqual(out[0]["skip_reason"], "unsupported product")

    def test_malformed_dict_is_unsupported_not_an_exception(self):
        out = self._run({"unexpected": "shape"})
        self.assertEqual(len(out), 1)
        blob = repr(out)
        self.assertNotIn("raised unexpectedly", blob)
        self.assertNotIn("has no attribute", blob)
        self.assertEqual(self.arm.seen, [])

    def test_product_objects_are_untouched(self):
        p = Product(title="t", subtitle="", description="d", price_usd=19.0,
                    file_path=__file__, cover_path=None, tags=[], language="en",
                    source_id="P1", raw_price_hint=19.0, needs_pricing=False,
                    price_source="profit_raw")
        self._run(p)
        self.assertIs(self.arm.seen[0], p)


if __name__ == "__main__":
    unittest.main()

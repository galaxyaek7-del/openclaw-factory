
import sys
from pathlib import Path
_FACTORY_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_FACTORY_ROOT))

import unittest
from unittest.mock import MagicMock, patch
from channels.gumroad_arm import GumroadArm
from channels.base_arm import ArmStatus

class TestGumroadTruthfulGate(unittest.TestCase):
    
    @patch('channels.gumroad_publisher.load_token')
    def test_credential_isolation_in_error_message(self, mock_load):
        # Prove the token does not leak into error messages
        mock_load.return_value = "SECRET_TOKEN_123"
        import os
        os.environ["GUMROAD_ACCESS_TOKEN"] = "SECRET_TOKEN_123"
        
        from channels.gumroad_publisher import _safe_err
        err = Exception("Failed with token SECRET_TOKEN_123")
        safe_err = _safe_err(err)
        
        self.assertNotIn("SECRET_TOKEN_123", safe_err)
        self.assertIn("***REDACTED***", safe_err)

    @patch('channels.gumroad_publisher.create_product')
    def test_dry_run_is_default_and_safe(self, mock_create):
        arm = GumroadArm()
        arm.supports = MagicMock(return_value=True)
        # Mock status as ready
        arm.status = MagicMock(return_value=ArmStatus.READY)
        
        product = MagicMock()
        product.file_path = "test.pdf"
        product.price_usd = 10.0
        product.needs_pricing = False
        product.source_id = "test"

        # Should not call create_product if dry_run=True
        result = arm.publish(product, dry_run=True)
        
        self.assertTrue(result.ok)
        mock_create.assert_not_called()

    @patch('channels.publish_protection.check_publish_allowed')
    @patch('channels.ledger.record_publish_attempt')
    @patch('channels.gumroad_publisher.load_token')
    @patch('channels.gumroad_publisher.create_product')
    def test_founder_gate_enforced(self, mock_create, mock_load, mock_ledger, mock_gate):
        # Ensure that non-dry-run requires gate approval
        arm = GumroadArm()
        # Ensure arm.supports returns True for our test product
        product = MagicMock()
        product.file_path = "test.pdf"
        product.price_usd = 10.0
        product.needs_pricing = False
        product.source_id = "test"
        
        arm.status = MagicMock(return_value=ArmStatus.READY)
        
        # Gate blocks
        mock_gate.return_value = {"allowed": False, "reason": "test gate", "risk_score": 0}
        
        from distributor import distribute
        
        # Test distribute which calls gate
        outcomes = distribute(product, arm_names=["gumroad"], dry_run=False, ledger_path="test_ledger.jsonl")
        
        # Should NOT be ok
        self.assertFalse(outcomes[0]["attempted"])
        self.assertIn("blocked", outcomes[0]["skip_reason"])
        mock_create.assert_not_called()
        mock_ledger.assert_called()

if __name__ == '__main__':
    unittest.main()

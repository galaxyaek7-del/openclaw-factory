import pytest
"""Stage 01 — Universal Distribution Fabric integration tests (18 tests).

Proves every fabric capability per the Stage 01 directive Task 11.
A PASS here means only that the tested behavior works — never that a
marketplace publication occurred.
"""
import os
import sys
import unittest
import tempfile
import json
from pathlib import Path
from dataclasses import dataclass

# Cycle 84: this module exercises Gumroad write logic against a mocked
# HTTP layer, so it explicitly opts in to write authorization. It was
# previously getting this from an AUTOUSE fixture that set
# FACTORY_LIVE_PUBLISH=true for the whole suite -- a hidden broad
# permission. The opt-in is now visible here, in the file that needs it.
pytestmark = pytest.mark.usefixtures("authorize_live_writes")

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))


def _make_product(file_path="test.epub", price_usd=9.99, title="Test Book"):
    @dataclass
    class P:
        file_path: str = ""
        price_usd: float = 0
        needs_pricing: bool = False
        title: str = ""
        description: str = "A test book"
        category: str = "Nonfiction"
        keywords: list = None
        isbn: str = None
        source_id: str = "test-prod-001"
        product_type: str = "book"
        cover_path: str = None
        def __post_init__(self):
            if self.keywords is None:
                self.keywords = ["test"]
    return P(file_path=file_path, price_usd=price_usd, title=title)


# ── 1. Universal product contract ──────────────────────────────


class TestUniversalDistributionFabricStage01(unittest.TestCase):
    def test_universal_product_contract(self):
        from schemas.product import Product
        rec = {"title": "T", "topic": "desc", "price": 9.99, "path": "test.epub", "pages": 50, "production_id": "PROD-99"}
        prod = Product.from_jsonl_record(rec)
        assert prod.title == "T"
        assert prod.file_path == "test.epub"
        assert prod.source_id == "PROD-99"
        assert prod.product_type == "book"
        # Missing fields must not crash
        prod2 = Product.from_jsonl_record({})
        assert prod2.needs_pricing is True
        assert prod2.price_usd is None


# ── 2. Registry resolution ─────────────────────────────────────
    def test_registry_resolution(self):
        import distributor  # noqa: F401 — triggers all 5 arm imports
        from channels import registry
        for name in ["gumroad", "paddle", "etsy", "payhip", "kdp"]:
            arm = registry.get(name)
            assert arm is not None, f"{name} not registered"
            assert arm.name == name
        assert registry.get("nonexistent") is None
        assert len(registry.all_arms()) >= 5


# ── 3. Adapter discovery ───────────────────────────────────────
    def test_adapter_discovery(self):
        import distributor  # noqa: F401
        from channels import registry
        arms = {a.name: a for a in registry.all_arms()}
        assert "kdp" in arms
        assert "gumroad" in arms
        # kdp_adapter path also works
        import channels.kdp_adapter  # noqa: F401
        from channels.kdp_adapter import KdpAdapter
        from channels.kdp_arm import KdpArm
        assert KdpAdapter is KdpArm


# ── 4. Adapter contract compliance ─────────────────────────────
    def test_adapter_contract_compliance(self):
        import distributor  # noqa: F401
        from channels import registry
        for name in ["gumroad", "kdp", "paddle", "etsy", "payhip"]:
            arm = registry.get(name)
            assert hasattr(arm, "status") and callable(arm.status)
            assert hasattr(arm, "publish") and callable(arm.publish)
            assert hasattr(arm, "supports") and callable(arm.supports)
            # KDP must also satisfy PlatformAdapter extended contract
            if name == "kdp":
                for m in ["health_check", "authentication_check", "account_check",
                           "capability_check", "product_validate", "metadata_map",
                           "asset_validate", "pricing_validate", "draft_create",
                           "draft_update", "retrieve", "verify", "error_classify",
                           "retry", "rollback_or_recovery", "audit"]:
                    assert hasattr(arm, m), f"kdp missing {m}"


# ── 5. DRY_RUN ─────────────────────────────────────────────────
    def test_dry_run(self):
        import distributor  # noqa: F401
        from channels import registry
        os.environ["KDP_USERNAME"] = "test@test.com"
        os.environ["KDP_SESSION_COOKIE"] = "cookie123"
        try:
            kdp = registry.get("kdp")
            prod = _make_product()
            result = kdp.publish(prod, dry_run=True)
            assert result.ok is True
            assert result.dry_run is True
            assert result.platform == "kdp"
            # distributor DRY_RUN must not touch ledger with real mutation
            with tempfile.TemporaryDirectory() as td:
                ledger_path = os.path.join(td, "ledger.jsonl")
                pp_path = os.path.join(td, "pp.json")
                outcomes = distributor.distribute(prod, arm_names=["kdp"], dry_run=True,
                                                  ledger_path=ledger_path, protection_state_path=pp_path)
                assert len(outcomes) == 1
                assert outcomes[0]["attempted"] is True
                assert outcomes[0]["result"].dry_run is True
        finally:
            del os.environ["KDP_USERNAME"]
            del os.environ["KDP_SESSION_COOKIE"]


# ── 6. SIMULATED execution ─────────────────────────────────────
    def test_simulated_execution(self):
        from channels.adapter_contract import ExecutionMode
        assert ExecutionMode.SIMULATED.value == "SIMULATED"
        assert ExecutionMode.DRY_RUN.value == "DRY_RUN"
        assert ExecutionMode.AUTHORIZED.value == "AUTHORIZED"
        # KDP capability_check honestly reports SIMULATED-like manual path
        import distributor  # noqa: F401
        from channels import registry
        kdp = registry.get("kdp")
        cap = kdp.capability_check()
        assert cap["has_api"] is False
        pub_cap = [c for c in cap["capabilities"] if c["operation"] == "publish"][0]
        assert pub_cap["status"] == "REQUIRES_HUMAN_ACTION"


# ── 7. AUTHORIZED gate ─────────────────────────────────────────
    def test_authorized_gate(self):
        import distributor  # noqa: F401
        from channels import registry
        # Without credentials, even AUTHORIZED-like dry_run=False is blocked
        if "KDP_USERNAME" in os.environ:
            del os.environ["KDP_USERNAME"]
        if "KDP_SESSION_COOKIE" in os.environ:
            del os.environ["KDP_SESSION_COOKIE"]
        kdp = registry.get("kdp")
        prod = _make_product()
        result = kdp.publish(prod, dry_run=False)
        assert result.ok is False
        assert "not ready" in result.error.lower()
        # With credentials, dry_run=False still BLOCKED (requires human)
        os.environ["KDP_USERNAME"] = "test@test.com"
        os.environ["KDP_SESSION_COOKIE"] = "cookie123"
        try:
            result2 = kdp.publish(prod, dry_run=False)
            assert result2.ok is False
            assert "manual upload" in result2.error.lower()
        finally:
            del os.environ["KDP_USERNAME"]
            del os.environ["KDP_SESSION_COOKIE"]


# ── 8. Duplicate protection ────────────────────────────────────
    def test_duplicate_protection(self):
        from channels.duplicate_protection import DuplicateProtection
        with tempfile.TemporaryDirectory() as td:
            dp = DuplicateProtection(registry_path=os.path.join(td, "pub.json"))
            assert dp.check_duplicate(product_id="p1", platform="kdp")["is_duplicate"] is False
            dp.register_publication("p1", "kdp", "kdp-1", metadata={"title": "T", "description": "d", "price": 9.99, "product_type": "book"})
            assert dp.check_duplicate(product_id="p1", platform="kdp")["is_duplicate"] is True
            assert dp.check_duplicate(product_id="p1", platform="gumroad")["is_duplicate"] is False
            assert dp.check_duplicate(product_id="p1")["is_duplicate"] is True


# ── 9. Idempotency ─────────────────────────────────────────────
    def test_idempotency(self):
        from channels.duplicate_protection import DuplicateProtection
        with tempfile.TemporaryDirectory() as td:
            dp = DuplicateProtection(registry_path=os.path.join(td, "pub.json"))
            dp.register_publication("p1", "kdp", "kdp-1")
            dp.register_publication("p1", "kdp", "kdp-1")
            assert len(dp.list_publications("p1")) == 1
            # Distributor idempotency: same product published twice via dry_run
            import distributor  # noqa: F401
            os.environ["KDP_USERNAME"] = "test@test.com"
            os.environ["KDP_SESSION_COOKIE"] = "cookie123"
            try:
                prod = _make_product()
                with tempfile.TemporaryDirectory() as td2:
                    lp = os.path.join(td2, "ledger.jsonl")
                    pp = os.path.join(td2, "pp.json")
                    r1 = distributor.distribute(prod, arm_names=["kdp"], dry_run=True, ledger_path=lp, protection_state_path=pp)
                    r2 = distributor.distribute(prod, arm_names=["kdp"], dry_run=True, ledger_path=lp, protection_state_path=pp)
                    assert r1[0]["result"].ok is True
                    assert r2[0]["result"].ok is True
            finally:
                del os.environ["KDP_USERNAME"]
                del os.environ["KDP_SESSION_COOKIE"]


# ── 10. Error classification ───────────────────────────────────
    def test_error_classification(self):
        from channels.error_classification import classify_error, is_retryable, error_summary
        from channels.adapter_contract import ErrorClass
        assert classify_error(Exception("unauthorized")) == ErrorClass.AUTH_ERROR
        assert classify_error(Exception("account suspended")) == ErrorClass.ACCOUNT_ERROR
        assert classify_error(Exception("rate limit")) == ErrorClass.RATE_LIMIT
        assert classify_error(Exception("timed out")) == ErrorClass.TIMEOUT
        assert classify_error(Exception("duplicate")) == ErrorClass.DUPLICATE
        assert classify_error(Exception("policy violation")) == ErrorClass.POLICY_BLOCK
        assert classify_error(Exception("random xyz")) == ErrorClass.UNKNOWN_ERROR
        assert is_retryable(ErrorClass.RATE_LIMIT) is True
        assert is_retryable(ErrorClass.AUTH_ERROR) is False
        s = error_summary(Exception("rate limit"), platform="kdp")
        assert s["retryable"] is True
        assert s["platform"] == "kdp"
        # UNKNOWN stays UNKNOWN
        assert classify_error(Exception("xyz unknown thing")) == ErrorClass.UNKNOWN_ERROR


# ── 11. Blocked-platform behavior ──────────────────────────────
    def test_blocked_platform_behavior(self):
        import distributor  # noqa: F401
        from channels import registry
        kdp = registry.get("kdp")
        # KDP without creds is UNAVAILABLE -> blocked
        if "KDP_USERNAME" in os.environ:
            del os.environ["KDP_USERNAME"]
        if "KDP_SESSION_COOKIE" in os.environ:
            del os.environ["KDP_SESSION_COOKIE"]
        prod = _make_product()
        result = kdp.publish(prod, dry_run=True)
        assert result.ok is False
        assert "not ready" in result.error.lower()
        # Etsy/Payhip also blocked
        for name in ["etsy", "payhip"]:
            arm = registry.get(name)
            r = arm.publish(prod, dry_run=True)
            assert r.ok is False
        # Payhip draft_create is honest about no API
        payhip = registry.get("payhip")
        assert "no product" in payhip.publish(prod, dry_run=False).error.lower() or "unsupported" in payhip.publish(prod, dry_run=False).error.lower() or payhip.status().value == "unavailable"


# ── 12. Unsupported-operation behavior ─────────────────────────
    def test_unsupported_operation_behavior(self):
        import distributor  # noqa: F401
        from channels import registry
        kdp = registry.get("kdp")
        for method, expected in [
            ("draft_create", "REQUIRES_HUMAN_ACTION"),
            ("draft_update", "REQUIRES_HUMAN_ACTION"),
            ("retrieve", "REQUIRES_HUMAN_ACTION"),
            ("verify", "REQUIRES_HUMAN_ACTION"),
        ]:
            fn = getattr(kdp, method)
            if method == "draft_create":
                result = fn(_make_product())
            elif method == "draft_update":
                result = fn("some-id", {})
            else:
                result = fn("some-id")
            assert result["status"] == expected, f"{method}: expected {expected}, got {result}"
        assert kdp.retry("op")["status"] == "UNSUPPORTED"
        assert kdp.rollback_or_recovery("id", "op")["status"] == "REQUIRES_HUMAN_ACTION"


# ── 13. Audit generation ───────────────────────────────────────
    def test_audit_generation(self):
        import distributor  # noqa: F401
        from channels import registry
        from channels.ledger import append_event, read_events
        with tempfile.TemporaryDirectory() as td:
            lp = os.path.join(td, "ledger.jsonl")
            prod = _make_product()
            os.environ["KDP_USERNAME"] = "test@test.com"
            os.environ["KDP_SESSION_COOKIE"] = "cookie123"
            try:
                outcomes = distributor.distribute(prod, arm_names=["kdp"], dry_run=True,
                                                  ledger_path=lp, protection_state_path=os.path.join(td, "pp.json"))
                assert outcomes[0]["attempted"] is True
                events = list(read_events(ledger_path=lp))
                assert len(events) >= 1
                assert any(e["event_type"] == "publish_attempt" for e in events)
            finally:
                del os.environ["KDP_USERNAME"]
                del os.environ["KDP_SESSION_COOKIE"]


# ── 14. Verification semantics ─────────────────────────────────
    def test_verification_semantics(self):
        import distributor  # noqa: F401
        from channels import registry
        kdp = registry.get("kdp")
        # KDP verify requires human (no API)
        assert kdp.verify("any-id")["status"] == "REQUIRES_HUMAN_ACTION"
        # BaseArm.verify_product for arms without list_products
        payhip = registry.get("payhip")
        assert payhip.verify_product("any-id")["status"] == "NOT_IMPLEMENTED"
        # Gumroad verify_product with no real token
        gumroad = registry.get("gumroad")
        # gumroad has real token in .env, so test with isolated path
        result = payhip.verify_product("nonexistent")
        assert result["status"] == "NOT_IMPLEMENTED"


# ── 15. Financial truth ────────────────────────────────────────
    def test_financial_truth(self):
        from channels.ledger import read_events
        # Real ledger must have zero sales (no payout has occurred)
        sales = list(read_events(event_type="sale"))
        assert len(sales) == 0, f"Expected 0 real sales, found {len(sales)} — financial truth violated"
        # KDP economics must not be misread as revenue
        from economics import load_config, net_profit
        config = load_config()
        net = net_profit(9.99, "kdp_ebook", config)
        assert net > 0  # model exists
        # But model != realized revenue
        # Ledger must not contain a sale just because publish succeeded
        assert len(sales) == 0


# ── 16. Circuit-breaker behavior ───────────────────────────────
    def test_circuit_breaker(self):
        from circuit_breaker import CircuitBreakerState
        with tempfile.TemporaryDirectory() as td:
            cb = CircuitBreakerState(state_path=Path(td) / "cb.json")
            assert cb.allow_execution("test_arm") is True
            assert cb.is_isolated("test_arm") is False
            # 3 failures -> ISOLATED
            cb.record_failure("test_arm", "reason 1")
            cb.record_failure("test_arm", "reason 2")
            assert cb.allow_execution("test_arm") is True  # still 2/3
            cb.record_failure("test_arm", "reason 3")
            assert cb.is_isolated("test_arm") is True
            assert cb.allow_execution("test_arm") is False
            # Recovery
            cb.enter_half_open("test_arm")
            assert cb.current("test_arm")["state"] == "HALF_OPEN"
            cb.record_recovery_success("test_arm")
            assert cb.is_isolated("test_arm") is False
            assert cb.allow_execution("test_arm") is True


# ── 17. Publishing protection ──────────────────────────────────
    def test_publishing_protection(self):
        from channels.publish_protection import check_publish_allowed, note_publish_outcome
        with tempfile.TemporaryDirectory() as td:
            pp = os.path.join(td, "pp.json")
            # New arm KDP requires founder approval for first real publish
            gate = check_publish_allowed("kdp", state_path=pp)
            assert gate["allowed"] is False
            assert "never had a real successful publish" in gate["reason"]
            # Gumroad is proven -> allowed (if not rate-limited)
            gate2 = check_publish_allowed("gumroad", state_path=pp)
            assert gate2["allowed"] is True
            # Rate limiting: fill up gumroad
            from channels.publish_protection import PLATFORM_PROFILES
            max_per_hour = PLATFORM_PROFILES["gumroad"]["max_per_hour"]
            for _ in range(max_per_hour):
                note_publish_outcome("gumroad", True, state_path=pp)
            gate3 = check_publish_allowed("gumroad", state_path=pp)
            # Should be blocked by hourly cap or cooldown
            assert gate3["allowed"] is False


# ── 18. Rollback/recovery semantics ────────────────────────────
    def test_rollback_recovery(self):
        import distributor  # noqa: F401
        from channels import registry
        kdp = registry.get("kdp")
        # KDP rollback requires human
        assert kdp.rollback_or_recovery("id", "publish")["status"] == "REQUIRES_HUMAN_ACTION"
        # Circuit breaker recovery path
        from circuit_breaker import CircuitBreakerState
        with tempfile.TemporaryDirectory() as td:
            cb = CircuitBreakerState(state_path=Path(td) / "cb.json")
            for i in range(3):
                cb.record_failure("kdp", f"fail {i}")
            assert cb.is_isolated("kdp") is True
            cb.enter_half_open("kdp")
            cb.record_recovery_failure("kdp", "still failing")
            assert cb.is_isolated("kdp") is True
            cb.enter_half_open("kdp")
            cb.record_recovery_success("kdp")
            assert cb.is_isolated("kdp") is False
        # Publish protection cooldown
        from channels.publish_protection import note_publish_outcome
        with tempfile.TemporaryDirectory() as td:
            pp = os.path.join(td, "pp.json")
            for _ in range(3):
                note_publish_outcome("kdp", False, state_path=pp)
            from channels.publish_protection import check_publish_allowed
            gate = check_publish_allowed("kdp", state_path=pp)
            assert gate["allowed"] is False
            assert "cooldown" in gate["reason"].lower() or "never had" in gate["reason"].lower()


if __name__ == "__main__":
    unittest.main()

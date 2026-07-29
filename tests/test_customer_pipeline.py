"""Tests for customer_pipeline.py (ADR-130).

Every network-touching real call (decision_engine.evaluate_and_decide,
profit_oracle.butter_price, channels.paddle_publisher.create_checkout_transaction,
Telegram) is mocked or injected throughout -- this suite never depends on
live API availability and never spends a real Groq/Paddle call.

    python -m unittest tests.test_customer_pipeline -v
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import customer_pipeline as cp


def _temp_path(suffix=".json"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.remove(path)
    return path


class _FakeDecision:
    def __init__(self, **kwargs):
        self._d = kwargs

    def to_dict(self):
        return self._d


def _accepted_decision(**overrides):
    d = {
        "decision_id": "dec_test123", "status": "ACCEPTED", "ai_ceo_decision": "BUILD",
        "opportunity_score": 82.5, "reasoning": ["real evidence one", "real evidence two"],
    }
    d.update(overrides)
    return _FakeDecision(**d)


class BasePipelineTest(unittest.TestCase):
    def setUp(self):
        self.requests_path = _temp_path(".jsonl")  # _temp_path already leaves this absent
        self.state_path = _temp_path(".json")
        self.paddle_products_path = _temp_path(".json")
        self._notify_patcher = patch.object(cp, "_notify_founder")
        self._notify_patcher.start()
        self.addCleanup(self._notify_patcher.stop)

    def tearDown(self):
        for p in (self.requests_path, self.state_path, self.paddle_products_path):
            if os.path.exists(p):
                os.remove(p)

    def _write_request(self, request_id="req_abc123", **overrides):
        record = {
            "request_id": request_id, "submitted_at": "2026-07-25T00:00:00Z",
            "name": "Test Customer", "email": "test@example.com", "company": "Test Co",
            "description": "a real customer test request description", "budget_range": "$500-$2000",
            "status": "NEW",
        }
        record.update(overrides)
        with open(self.requests_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        return record

    def _write_paddle_products(self, products):
        with open(self.paddle_products_path, "w", encoding="utf-8") as f:
            json.dump(products, f)


class TestAdvanceRequest(BasePipelineTest):
    def test_missing_request_reports_honest_error(self):
        result = cp.advance_request("req_does_not_exist", requests_path=self.requests_path, state_path=self.state_path)
        self.assertFalse(result["success"])
        self.assertIn("no such customer request", result["error"])

    def test_accepted_path_reaches_proposed_with_real_price(self):
        self._write_request()
        result = cp.advance_request(
            "req_abc123", requests_path=self.requests_path, state_path=self.state_path,
            evaluate_fn=lambda *a, **k: _accepted_decision(), price_fn=lambda *a, **k: 199.0,
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["stage"], "PROPOSED")
        self.assertEqual(result["proposal"]["price"], 199.0)
        self.assertEqual(result["decision_id"], "dec_test123")

    def test_rejected_path_stops_at_rejected_at_qualification(self):
        self._write_request()
        result = cp.advance_request(
            "req_abc123", requests_path=self.requests_path, state_path=self.state_path,
            evaluate_fn=lambda *a, **k: _accepted_decision(status="REJECTED", reasoning=["no real evidence of demand"]),
        )
        self.assertEqual(result["stage"], "REJECTED_AT_QUALIFICATION")
        self.assertIsNone(result["proposal"])

    def test_research_required_path_is_not_treated_as_rejection(self):
        """Unknown must never automatically behave like False (ADR-127) --
        applies the same way to a real customer request."""
        self._write_request()
        result = cp.advance_request(
            "req_abc123", requests_path=self.requests_path, state_path=self.state_path,
            evaluate_fn=lambda *a, **k: _accepted_decision(status="RESEARCH_REQUIRED"),
        )
        self.assertEqual(result["stage"], "RESEARCH_REQUIRED")

    def test_deferred_path_routes_to_pending_founder_review(self):
        self._write_request()
        result = cp.advance_request(
            "req_abc123", requests_path=self.requests_path, state_path=self.state_path,
            evaluate_fn=lambda *a, **k: _accepted_decision(status="DEFERRED"),
        )
        self.assertEqual(result["stage"], "PENDING_FOUNDER_REVIEW")

    def test_second_call_is_idempotent_never_re_evaluates(self):
        self._write_request()
        call_count = {"n": 0}

        def counting_evaluate(*a, **k):
            call_count["n"] += 1
            return _accepted_decision()

        cp.advance_request("req_abc123", requests_path=self.requests_path, state_path=self.state_path,
                            evaluate_fn=counting_evaluate, price_fn=lambda *a, **k: 199.0)
        result2 = cp.advance_request("req_abc123", requests_path=self.requests_path, state_path=self.state_path,
                                      evaluate_fn=counting_evaluate, price_fn=lambda *a, **k: 199.0)
        self.assertEqual(call_count["n"], 1)
        self.assertTrue(result2["already_advanced"])

    def test_evaluation_exception_is_captured_never_crashes(self):
        self._write_request()

        def boom(*a, **k):
            raise RuntimeError("simulated real network failure")

        result = cp.advance_request("req_abc123", requests_path=self.requests_path, state_path=self.state_path, evaluate_fn=boom)
        self.assertEqual(result["stage"], "FAILED")
        self.assertIn("simulated real network failure", result["error"])


class TestApproveAndReject(BasePipelineTest):
    def _propose(self, price=199.0):
        self._write_request()
        return cp.advance_request(
            "req_abc123", requests_path=self.requests_path, state_path=self.state_path,
            evaluate_fn=lambda *a, **k: _accepted_decision(), price_fn=lambda *a, **k: price,
        )

    def test_cannot_approve_before_proposed(self):
        self._write_request()
        result = cp.approve_request("req_abc123", state_path=self.state_path)
        self.assertFalse(result["success"])

    def test_approve_with_matching_price_reaches_awaiting_payment(self):
        self._propose(price=126.0)
        self._write_paddle_products([{"title": "match", "price_id": "pri_match", "price": 126.0}])
        result = cp.approve_request(
            "req_abc123", accepted_name="Test Customer", state_path=self.state_path, paddle_products_path=self.paddle_products_path,
            checkout_fn=lambda api_key, price_id: ({"id": "txn_1"}, "https://checkout.paddle.com/real"),
            api_key_loader=lambda: "fake-key",
        )
        self.assertEqual(result["stage"], "AWAITING_PAYMENT")
        self.assertEqual(result["payment"]["checkout_url"], "https://checkout.paddle.com/real")

    def test_approve_blocked_by_paddle_onboarding_gate(self):
        self._propose(price=126.0)
        self._write_paddle_products([{"title": "match", "price_id": "pri_match", "price": 126.0}])

        def blocked(api_key, price_id):
            raise RuntimeError("Checkouts aren't enabled for this account.")

        result = cp.approve_request(
            "req_abc123", accepted_name="Test Customer", state_path=self.state_path, paddle_products_path=self.paddle_products_path,
            checkout_fn=blocked, api_key_loader=lambda: "fake-key",
        )
        self.assertEqual(result["stage"], "PAYMENT_BLOCKED_PADDLE_ONBOARDING")

    def test_approve_with_no_matching_product_is_honestly_pending(self):
        self._propose(price=9999.0)
        self._write_paddle_products([{"title": "no match", "price_id": "pri_x", "price": 50.0}])
        result = cp.approve_request(
            "req_abc123", accepted_name="Test Customer", state_path=self.state_path, paddle_products_path=self.paddle_products_path,
        )
        self.assertEqual(result["stage"], "PENDING_CUSTOM_PRODUCT_SETUP")

    def test_reject_from_proposed_succeeds(self):
        self._propose()
        result = cp.reject_request("req_abc123", reason="too expensive", state_path=self.state_path)
        self.assertEqual(result["stage"], "REJECTED_BY_CUSTOMER")

    def test_cannot_reject_twice(self):
        self._propose()
        cp.reject_request("req_abc123", state_path=self.state_path)
        result = cp.reject_request("req_abc123", state_path=self.state_path)
        self.assertFalse(result["success"])


class TestRetryPaymentVerification(BasePipelineTest):
    def test_retry_after_paddle_unblocks(self):
        self._write_request()
        cp.advance_request("req_abc123", requests_path=self.requests_path, state_path=self.state_path,
                            evaluate_fn=lambda *a, **k: _accepted_decision(), price_fn=lambda *a, **k: 126.0)
        self._write_paddle_products([{"title": "match", "price_id": "pri_match", "price": 126.0}])
        cp.approve_request("req_abc123", accepted_name="Test Customer", state_path=self.state_path, paddle_products_path=self.paddle_products_path,
                            checkout_fn=lambda k, p: (_ for _ in ()).throw(RuntimeError("checkout not enabled for this account")))
        blocked_state = cp._load_state(self.state_path)
        self.assertEqual(blocked_state["req_abc123"]["stage"], "PAYMENT_BLOCKED_PADDLE_ONBOARDING")

        result = cp.retry_payment_verification(
            "req_abc123", state_path=self.state_path, paddle_products_path=self.paddle_products_path,
            checkout_fn=lambda k, p: ({"id": "txn_1"}, "https://checkout.paddle.com/real"),
            api_key_loader=lambda: "fake-key",
        )
        self.assertEqual(result["stage"], "AWAITING_PAYMENT")

    def test_retry_refuses_from_a_stage_never_approved(self):
        self._write_request()
        cp.advance_request("req_abc123", requests_path=self.requests_path, state_path=self.state_path,
                            evaluate_fn=lambda *a, **k: _accepted_decision(), price_fn=lambda *a, **k: 126.0)
        result = cp.retry_payment_verification("req_abc123", state_path=self.state_path)
        self.assertFalse(result["success"])


class TestStatusAndOverview(BasePipelineTest):
    def test_get_pipeline_status_never_leaks_email(self):
        self._write_request()
        result = cp.get_pipeline_status("req_abc123", requests_path=self.requests_path, state_path=self.state_path)
        self.assertTrue(result["success"])
        self.assertNotIn("email", result["request"])
        self.assertEqual(result["status"], "NEW")

    def test_get_pipeline_status_missing_request(self):
        result = cp.get_pipeline_status("req_nope", requests_path=self.requests_path, state_path=self.state_path)
        self.assertFalse(result["success"])

    def test_overview_reports_real_stage_distribution(self):
        self._write_request("req_one")
        self._write_request("req_two")
        cp.advance_request("req_one", requests_path=self.requests_path, state_path=self.state_path,
                            evaluate_fn=lambda *a, **k: _accepted_decision(), price_fn=lambda *a, **k: 100.0)
        overview = cp.list_pipeline_overview(requests_path=self.requests_path, state_path=self.state_path)
        self.assertEqual(overview["total_requests"], 2)
        self.assertEqual(overview["stage_distribution"].get("PROPOSED"), 1)
        self.assertEqual(overview["stage_distribution"].get("NEW"), 1)

    def test_overview_needs_attention_flags_blocked_requests(self):
        self._write_request()
        cp.advance_request("req_abc123", requests_path=self.requests_path, state_path=self.state_path,
                            evaluate_fn=lambda *a, **k: _accepted_decision(), price_fn=lambda *a, **k: 126.0)
        self._write_paddle_products([{"title": "match", "price_id": "pri_match", "price": 126.0}])
        cp.approve_request("req_abc123", accepted_name="Test Customer", state_path=self.state_path, paddle_products_path=self.paddle_products_path,
                            checkout_fn=lambda k, p: (_ for _ in ()).throw(RuntimeError("checkout not enabled for this account")))
        overview = cp.list_pipeline_overview(requests_path=self.requests_path, state_path=self.state_path)
        self.assertEqual(len(overview["needs_attention"]), 1)
        self.assertEqual(overview["needs_attention"][0]["stage"], "PAYMENT_BLOCKED_PADDLE_ONBOARDING")


class TestCatalogPriceLock(BasePipelineTest):
    """Commercial Readiness Report (2026-07-25), finding P1: a request for
    an existing catalog item must be quoted EXACTLY the catalog's real
    price, never re-derived via evaluate_and_decide()/butter_price()."""

    def test_catalog_match_skips_evaluation_and_pricing_entirely(self):
        self._write_request(catalog_product_id="pro_real123")
        self._write_paddle_products([{"title": "Real Catalog Item", "product_id": "pro_real123", "price_id": "pri_real123", "price": 126.0}])

        def boom_evaluate(*a, **k):
            raise AssertionError("evaluate_and_decide must never be called for a catalog-matched request")

        def boom_price(*a, **k):
            raise AssertionError("butter_price must never be called for a catalog-matched request")

        result = cp.advance_request(
            "req_abc123", requests_path=self.requests_path, state_path=self.state_path,
            paddle_products_path=self.paddle_products_path, evaluate_fn=boom_evaluate, price_fn=boom_price,
        )
        self.assertEqual(result["stage"], "PROPOSED")
        self.assertEqual(result["proposal"]["price"], 126.0)
        self.assertIn("live catalog price", result["proposal"]["price_basis"])

    def test_catalog_price_matches_exactly_even_with_odd_cents(self):
        self._write_request(catalog_product_id="pro_odd")
        self._write_paddle_products([{"title": "Odd Cents Item", "product_id": "pro_odd", "price_id": "pri_odd", "price": 149.99}])
        result = cp.advance_request(
            "req_abc123", requests_path=self.requests_path, state_path=self.state_path,
            paddle_products_path=self.paddle_products_path,
        )
        self.assertEqual(result["proposal"]["price"], 149.99)

    def test_unknown_catalog_product_id_falls_back_to_full_evaluation(self):
        """A stale/bad product_id (e.g. the item was removed after the
        page loaded) must never silently drop the request -- it falls
        back to the real evaluation path instead."""
        self._write_request(catalog_product_id="pro_does_not_exist")
        self._write_paddle_products([{"title": "Unrelated", "product_id": "pro_other", "price_id": "pri_other", "price": 50.0}])
        result = cp.advance_request(
            "req_abc123", requests_path=self.requests_path, state_path=self.state_path,
            paddle_products_path=self.paddle_products_path,
            evaluate_fn=lambda *a, **k: _accepted_decision(), price_fn=lambda *a, **k: 199.0,
        )
        self.assertEqual(result["stage"], "PROPOSED")
        self.assertEqual(result["proposal"]["price"], 199.0)

    def test_no_catalog_product_id_uses_normal_evaluation_path(self):
        self._write_request()  # no catalog_product_id at all -- freeform custom request
        result = cp.advance_request(
            "req_abc123", requests_path=self.requests_path, state_path=self.state_path,
            evaluate_fn=lambda *a, **k: _accepted_decision(), price_fn=lambda *a, **k: 199.0,
        )
        self.assertEqual(result["proposal"]["price"], 199.0)

    def test_approval_uses_exact_catalog_price_id_not_tolerance_search(self):
        self._write_request(catalog_product_id="pro_real123")
        self._write_paddle_products([
            {"title": "Real Catalog Item", "product_id": "pro_real123", "price_id": "pri_real123", "price": 126.0},
            {"title": "Decoy — same price, different product", "product_id": "pro_decoy", "price_id": "pri_decoy", "price": 126.0},
        ])
        cp.advance_request("req_abc123", requests_path=self.requests_path, state_path=self.state_path, paddle_products_path=self.paddle_products_path)
        captured = {}

        def capture_checkout(api_key, price_id):
            captured["price_id"] = price_id
            return ({"id": "txn_1"}, "https://checkout.paddle.com/real")

        result = cp.approve_request(
            "req_abc123", accepted_name="Test Customer", state_path=self.state_path, paddle_products_path=self.paddle_products_path,
            checkout_fn=capture_checkout, api_key_loader=lambda: "fake-key",
        )
        self.assertEqual(result["stage"], "AWAITING_PAYMENT")
        self.assertEqual(captured["price_id"], "pri_real123")


class TestContractGeneration(BasePipelineTest):
    """Customer Platform Round 2 (2026-07-29): a real, deterministic
    contract is generated alongside every proposal, and approval now
    doubles as contract acceptance (a typed-name e-signature)."""

    def test_proposal_includes_a_real_contract(self):
        self._write_request()
        result = cp.advance_request(
            "req_abc123", requests_path=self.requests_path, state_path=self.state_path,
            evaluate_fn=lambda *a, **k: _accepted_decision(), price_fn=lambda *a, **k: 199.0,
        )
        self.assertIn("contract", result)
        contract = result["contract"]
        self.assertEqual(contract["price"]["amount"], 199.0)
        self.assertFalse(contract["accepted"])
        self.assertIsNone(contract["accepted_name"])
        self.assertIn("Draft", contract["governing_law"])

    def test_catalog_match_also_gets_a_real_contract(self):
        self._write_request(catalog_product_id="pro_real123")
        self._write_paddle_products([{"title": "Real Catalog Item", "product_id": "pro_real123", "price_id": "pri_real123", "price": 126.0}])
        result = cp.advance_request(
            "req_abc123", requests_path=self.requests_path, state_path=self.state_path,
            paddle_products_path=self.paddle_products_path,
        )
        self.assertIn("contract", result)
        self.assertEqual(result["contract"]["scope"], "Real Catalog Item")
        self.assertEqual(result["contract"]["price"]["amount"], 126.0)

    def test_approve_without_accepted_name_is_rejected(self):
        self._write_request()
        cp.advance_request("req_abc123", requests_path=self.requests_path, state_path=self.state_path,
                            evaluate_fn=lambda *a, **k: _accepted_decision(), price_fn=lambda *a, **k: 199.0)
        result = cp.approve_request("req_abc123", state_path=self.state_path)
        self.assertFalse(result["success"])
        self.assertIn("accept the contract", result["error"])
        # Still PROPOSED -- a rejected approve attempt must not advance the stage.
        state = cp._load_state(self.state_path)
        self.assertEqual(state["req_abc123"]["stage"], "PROPOSED")

    def test_approve_with_accepted_name_records_real_acceptance(self):
        self._write_request()
        cp.advance_request("req_abc123", requests_path=self.requests_path, state_path=self.state_path,
                            evaluate_fn=lambda *a, **k: _accepted_decision(), price_fn=lambda *a, **k: 126.0)
        self._write_paddle_products([{"title": "match", "price_id": "pri_match", "price": 126.0}])
        result = cp.approve_request(
            "req_abc123", accepted_name="  Jane Customer  ", state_path=self.state_path, paddle_products_path=self.paddle_products_path,
            checkout_fn=lambda k, p: ({"id": "txn_1"}, "https://checkout.paddle.com/real"), api_key_loader=lambda: "fake-key",
        )
        self.assertTrue(result["success"])
        self.assertTrue(result["contract"]["accepted"])
        self.assertEqual(result["contract"]["accepted_name"], "Jane Customer")
        self.assertIsNotNone(result["contract"]["accepted_at"])


class TestPaymentCompletionAndInvoice(BasePipelineTest):
    """Customer Platform Round 3 (2026-07-29): a real Paddle transaction
    object is persisted (not discarded) and check_payment_status() can
    confirm real completion + generate a real invoice."""

    def _awaiting_payment(self, price=126.0, txn_id="txn_real1"):
        self._write_request()
        cp.advance_request("req_abc123", requests_path=self.requests_path, state_path=self.state_path,
                            evaluate_fn=lambda *a, **k: _accepted_decision(), price_fn=lambda *a, **k: price)
        self._write_paddle_products([{"title": "match", "price_id": "pri_match", "price": price}])
        cp.approve_request(
            "req_abc123", accepted_name="Test Customer", state_path=self.state_path, paddle_products_path=self.paddle_products_path,
            checkout_fn=lambda k, p: ({"id": txn_id, "status": "draft"}, "https://checkout.paddle.com/real"),
            api_key_loader=lambda: "fake-key",
        )

    def test_approve_persists_full_transaction_object(self):
        self._awaiting_payment()
        state = cp._load_state(self.state_path)
        self.assertEqual(state["req_abc123"]["payment"]["transaction"]["id"], "txn_real1")

    def test_check_payment_status_wrong_stage_is_rejected(self):
        self._write_request()
        result = cp.check_payment_status("req_abc123", state_path=self.state_path)
        self.assertFalse(result["success"])

    def test_check_payment_status_transaction_not_yet_visible(self):
        self._awaiting_payment()
        result = cp.check_payment_status(
            "req_abc123", state_path=self.state_path, api_key_loader=lambda: "fake-key",
            get_transactions_fn=lambda k: [],
        )
        self.assertTrue(result["success"])
        self.assertFalse(result["already_paid"])
        state = cp._load_state(self.state_path)
        self.assertEqual(state["req_abc123"]["stage"], "AWAITING_PAYMENT")

    def test_check_payment_status_still_pending_does_not_advance(self):
        self._awaiting_payment()
        result = cp.check_payment_status(
            "req_abc123", state_path=self.state_path, api_key_loader=lambda: "fake-key",
            get_transactions_fn=lambda k: [{"id": "txn_real1", "status": "draft"}],
        )
        self.assertTrue(result["success"])
        self.assertFalse(result["already_paid"])
        self.assertEqual(result["paddle_status"], "draft")

    def test_check_payment_status_completed_transitions_to_paid_with_real_invoice(self):
        self._awaiting_payment(price=126.0, txn_id="txn_real1")
        result = cp.check_payment_status(
            "req_abc123", state_path=self.state_path, api_key_loader=lambda: "fake-key",
            get_transactions_fn=lambda k: [{"id": "txn_real1", "status": "completed"}],
        )
        self.assertTrue(result["success"])
        self.assertTrue(result["already_paid"])
        self.assertEqual(result["stage"], "PAID")
        self.assertIsNotNone(result["invoice"])
        self.assertEqual(result["invoice"]["total"], 126.0)
        self.assertEqual(result["invoice"]["payment_reference"], "txn_real1")
        self.assertTrue(result["invoice"]["invoice_number"].startswith("INV-"))

    def test_check_all_awaiting_payments_sweeps_only_that_stage(self):
        self._awaiting_payment(price=126.0, txn_id="txn_real1")
        self._write_request("req_new_one")  # stays NEW -- never advanced
        with patch("channels.paddle_publisher.load_api_key", return_value="fake-key"), \
             patch("channels.paddle_publisher.get_transactions", return_value=[{"id": "txn_real1", "status": "completed"}]):
            result = cp.check_all_awaiting_payments(requests_path=self.requests_path, state_path=self.state_path)
        self.assertEqual(result["checked_count"], 1)
        self.assertEqual(result["checked"][0]["request_id"], "req_abc123")
        state = cp._load_state(self.state_path)
        self.assertEqual(state["req_abc123"]["stage"], "PAID")


class TestCustomerSafeCopy(BasePipelineTest):
    """Commercial Readiness Report (2026-07-25), finding PY1: the
    customer's own status page must never show internal function names
    or module-style jargon."""

    def _assert_no_leaked_identifiers(self, text):
        self.assertNotIn("(", text)
        self.assertNotIn(")", text)
        for leaked in ("advance_request", "retry_payment_verification", "ADR-", "vendors.paddle.com"):
            self.assertNotIn(leaked, text)

    def test_customer_status_recovery_text_has_no_function_names(self):
        self._write_request()
        result = cp.get_pipeline_status("req_abc123", requests_path=self.requests_path, state_path=self.state_path)
        self._assert_no_leaked_identifiers(result["recovery"])

    def test_customer_status_recovery_text_clean_for_every_real_stage(self):
        for stage in cp._CUSTOMER_RECOVERY_HINTS:
            self._assert_no_leaked_identifiers(cp._CUSTOMER_RECOVERY_HINTS[stage])

    def test_internal_mission_control_view_is_unaffected_still_technical(self):
        """The internal dict is allowed to keep function names -- only the
        customer-facing one had to change."""
        self.assertIn("retry_payment_verification()", cp._RECOVERY_HINTS["PAYMENT_BLOCKED_PADDLE_ONBOARDING"])

    def test_missing_request_error_is_customer_friendly(self):
        result = cp.get_pipeline_status("req_totally_made_up", requests_path=self.requests_path, state_path=self.state_path)
        self.assertFalse(result["success"])
        self.assertNotIn("!r", result["error"])
        self.assertNotIn("'req_totally_made_up'", result["error"])

    def test_approve_reject_errors_are_customer_friendly(self):
        self._write_request()
        result = cp.approve_request("req_abc123", state_path=self.state_path)
        self.assertFalse(result["success"])
        self.assertNotIn("!r", result["error"])
        self.assertNotIn("'req_abc123'", result["error"])


class TestAdvanceAllNewRequests(BasePipelineTest):
    def test_advances_only_new_requests(self):
        self._write_request("req_one")
        self._write_request("req_two")
        cp.advance_request("req_one", requests_path=self.requests_path, state_path=self.state_path,
                            evaluate_fn=lambda *a, **k: _accepted_decision(), price_fn=lambda *a, **k: 100.0)
        with patch("decision_engine.engine.evaluate_and_decide", return_value=_accepted_decision()), \
             patch("profit_oracle.butter_price", return_value=150.0):
            result = cp.advance_all_new_requests(requests_path=self.requests_path, state_path=self.state_path)
        self.assertEqual(result["advanced_count"], 1)
        self.assertEqual(result["advanced"][0]["request_id"], "req_two")


if __name__ == "__main__":
    unittest.main()

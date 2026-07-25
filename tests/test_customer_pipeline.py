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
            "req_abc123", state_path=self.state_path, paddle_products_path=self.paddle_products_path,
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
            "req_abc123", state_path=self.state_path, paddle_products_path=self.paddle_products_path,
            checkout_fn=blocked, api_key_loader=lambda: "fake-key",
        )
        self.assertEqual(result["stage"], "PAYMENT_BLOCKED_PADDLE_ONBOARDING")

    def test_approve_with_no_matching_product_is_honestly_pending(self):
        self._propose(price=9999.0)
        self._write_paddle_products([{"title": "no match", "price_id": "pri_x", "price": 50.0}])
        result = cp.approve_request(
            "req_abc123", state_path=self.state_path, paddle_products_path=self.paddle_products_path,
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
        cp.approve_request("req_abc123", state_path=self.state_path, paddle_products_path=self.paddle_products_path,
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
        cp.approve_request("req_abc123", state_path=self.state_path, paddle_products_path=self.paddle_products_path,
                            checkout_fn=lambda k, p: (_ for _ in ()).throw(RuntimeError("checkout not enabled for this account")))
        overview = cp.list_pipeline_overview(requests_path=self.requests_path, state_path=self.state_path)
        self.assertEqual(len(overview["needs_attention"]), 1)
        self.assertEqual(overview["needs_attention"][0]["stage"], "PAYMENT_BLOCKED_PADDLE_ONBOARDING")


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

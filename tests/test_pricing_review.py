import json
import os
import tempfile
import unittest

import pricing_review as pr


class TestPricingReviewReadiness(unittest.TestCase):
    def test_no_state_no_reviews_not_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = os.path.join(tmp, "state.json")
            reviews_path = os.path.join(tmp, "reviews.jsonl")
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump({}, f)
            open(reviews_path, "w", encoding="utf-8").close()
            result = pr.check_pricing_review_readiness("pro_x", state_path=state_path, reviews_path=reviews_path)
            self.assertFalse(result["ready_for_elite_tier_review"])
            self.assertEqual(result["real_paid_customers"], 0)

    def test_paid_customer_without_review_not_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = os.path.join(tmp, "state.json")
            reviews_path = os.path.join(tmp, "reviews.jsonl")
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump({"req_1": {"stage": "DELIVERED", "catalog_match": {"product_id": "pro_x"}}}, f)
            open(reviews_path, "w", encoding="utf-8").close()
            result = pr.check_pricing_review_readiness("pro_x", state_path=state_path, reviews_path=reviews_path)
            self.assertEqual(result["real_paid_customers"], 1)
            self.assertEqual(result["real_reviews_on_paid_requests"], 0)
            self.assertFalse(result["ready_for_elite_tier_review"])

    def test_paid_customer_with_review_is_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = os.path.join(tmp, "state.json")
            reviews_path = os.path.join(tmp, "reviews.jsonl")
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump({"req_1": {"stage": "DELIVERED", "catalog_match": {"product_id": "pro_x"}}}, f)
            with open(reviews_path, "w", encoding="utf-8") as f:
                f.write(json.dumps({"request_id": "req_1", "rating": 5}) + "\n")
            result = pr.check_pricing_review_readiness("pro_x", state_path=state_path, reviews_path=reviews_path)
            self.assertTrue(result["ready_for_elite_tier_review"])

    def test_wrong_product_id_not_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = os.path.join(tmp, "state.json")
            reviews_path = os.path.join(tmp, "reviews.jsonl")
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump({"req_1": {"stage": "DELIVERED", "catalog_match": {"product_id": "pro_other"}}}, f)
            with open(reviews_path, "w", encoding="utf-8") as f:
                f.write(json.dumps({"request_id": "req_1", "rating": 5}) + "\n")
            result = pr.check_pricing_review_readiness("pro_x", state_path=state_path, reviews_path=reviews_path)
            self.assertEqual(result["real_paid_customers"], 0)
            self.assertFalse(result["ready_for_elite_tier_review"])

    def test_early_stage_not_counted_as_paid(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = os.path.join(tmp, "state.json")
            reviews_path = os.path.join(tmp, "reviews.jsonl")
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump({"req_1": {"stage": "PROPOSED", "catalog_match": {"product_id": "pro_x"}}}, f)
            open(reviews_path, "w", encoding="utf-8").close()
            result = pr.check_pricing_review_readiness("pro_x", state_path=state_path, reviews_path=reviews_path)
            self.assertEqual(result["real_paid_customers"], 0)

    def test_never_fabricates_elite_evaluation_when_not_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = os.path.join(tmp, "state.json")
            reviews_path = os.path.join(tmp, "reviews.jsonl")
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump({}, f)
            open(reviews_path, "w", encoding="utf-8").close()
            result = pr.check_pricing_review_readiness(
                "pro_x", state_path=state_path, reviews_path=reviews_path, elite_price=310.0,
            )
            self.assertNotIn("elite_tier_evaluation", result)

    def test_real_elite_evaluation_computed_when_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = os.path.join(tmp, "state.json")
            reviews_path = os.path.join(tmp, "reviews.jsonl")
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump({"req_1": {"stage": "PAID", "catalog_match": {"product_id": "pro_x"}}}, f)
            with open(reviews_path, "w", encoding="utf-8") as f:
                f.write(json.dumps({"request_id": "req_1", "rating": 5}) + "\n")
            result = pr.check_pricing_review_readiness(
                "pro_x", state_path=state_path, reviews_path=reviews_path,
                elite_price=310.0, elite_platform="gumroad_elite", page_count=31,
            )
            self.assertIn("elite_tier_evaluation", result)
            self.assertTrue(result["elite_tier_evaluation"]["market_realistic"])


if __name__ == "__main__":
    unittest.main()

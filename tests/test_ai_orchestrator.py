"""Tests for ai_capability/orchestrator.py (Galaxy Forge Strategic Principle,
2026-07-23 — "loyal to results, not models").

Every test mocks book_generator.groq_chat (the one real, working
provider implementation) or ai_capability.evaluator.recommend_for_task
directly — no live network calls, no live Groq call.

    python -m unittest tests.test_ai_orchestrator -v
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from ai_capability import orchestrator


class TestSelectProvider(unittest.TestCase):
    def test_a_real_measured_recommendation_is_used(self):
        with patch("ai_capability.evaluator.recommend_for_task", return_value={"recommendation": "groq", "reason": "x"}):
            provider, recommendation = orchestrator.select_provider("query_reformulation")
        self.assertEqual(provider, "groq")
        self.assertEqual(recommendation["recommendation"], "groq")

    def test_no_real_measured_recommendation_honestly_defaults_to_groq(self):
        """groq is this factory's one real, always-available provider --
        the honest default, not a guess, when evaluator.recommend_for_task()
        found nothing measured for this exact task_type."""
        with patch("ai_capability.evaluator.recommend_for_task", return_value={"recommendation": None, "reason": "x"}):
            provider, recommendation = orchestrator.select_provider("a task type nothing serves yet")
        self.assertEqual(provider, "groq")


class TestGenerate(unittest.TestCase):
    def test_a_real_groq_call_is_dispatched_and_its_content_returned(self):
        with patch("ai_capability.evaluator.recommend_for_task", return_value={"recommendation": "groq", "reason": "x"}), \
             patch("book_generator.groq_chat", return_value="real generated text") as mock_groq:
            result = orchestrator.generate("query_reformulation", "system prompt", "user prompt", max_tokens=40)
        self.assertEqual(result["content"], "real generated text")
        self.assertEqual(result["provider"], "groq")
        mock_groq.assert_called_once_with("system prompt", "user prompt", max_tokens=40)

    def test_kwargs_are_forwarded_to_the_real_provider_caller_unchanged(self):
        with patch("ai_capability.evaluator.recommend_for_task", return_value={"recommendation": "groq", "reason": "x"}), \
             patch("book_generator.groq_chat", return_value="x") as mock_groq:
            orchestrator.generate("query_reformulation", "sys", "user", max_tokens=40, retries=1, cost_context={"niche": "n"})
        mock_groq.assert_called_once_with("sys", "user", max_tokens=40, retries=1, cost_context={"niche": "n"})

    def test_an_unimplemented_selected_provider_raises_honestly_never_silently_substitutes(self):
        """The real, deliberate safety property: even if evaluator ever
        recommended a provider with no real integration here, generate()
        must refuse loudly rather than quietly falling back to Groq and
        pretending multi-model orchestration happened."""
        with patch("ai_capability.evaluator.recommend_for_task", return_value={"recommendation": "anthropic", "reason": "x"}):
            with self.assertRaises(NotImplementedError):
                orchestrator.generate("reasoning", "sys", "user")

    def test_a_real_groq_failure_propagates_never_silently_swallowed(self):
        """generate() itself does not add a fallback layer -- callers
        (e.g. market_intelligence_engine.reformulate_pain_query()) keep
        their own existing, already-tested fallback chain around this
        call, unchanged."""
        with patch("ai_capability.evaluator.recommend_for_task", return_value={"recommendation": "groq", "reason": "x"}), \
             patch("book_generator.groq_chat", side_effect=RuntimeError("Groq down")):
            with self.assertRaises(RuntimeError):
                orchestrator.generate("query_reformulation", "sys", "user")


class TestResourceAllocationStatus(unittest.TestCase):
    """Autonomous Global Execution Engine (2026-07-23): a real, zero-cost
    read of which provider each of the 9 named task categories currently
    resolves to -- never a live generation call."""

    def test_all_9_named_categories_are_covered(self):
        with patch("ai_capability.evaluator.recommend_for_task", return_value={"recommendation": None, "reason": "x"}):
            status = orchestrator.resource_allocation_status()
        self.assertEqual(set(status), set(orchestrator.RESOURCE_ALLOCATION_TASK_TYPES))
        self.assertEqual(len(status), 9)

    def test_honest_groq_fallback_when_nothing_measured_for_any_category(self):
        with patch("ai_capability.evaluator.recommend_for_task", return_value={"recommendation": None, "reason": "x"}):
            status = orchestrator.resource_allocation_status()
        for task_type in orchestrator.RESOURCE_ALLOCATION_TASK_TYPES:
            self.assertEqual(status[task_type]["provider"], "groq")

    def test_never_a_live_generation_call(self):
        """resource_allocation_status() must be safe to call freely --
        zero cost, zero network side effect -- so it can back a real-time
        Mission Control view without spending anything."""
        with patch("ai_capability.evaluator.recommend_for_task", return_value={"recommendation": "groq", "reason": "x"}), \
             patch("book_generator.groq_chat") as mock_groq:
            orchestrator.resource_allocation_status()
        mock_groq.assert_not_called()


if __name__ == "__main__":
    unittest.main()

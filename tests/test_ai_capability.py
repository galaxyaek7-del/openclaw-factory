"""Tests for ai_capability/ (Autonomous Digital Company v1, Track B2,
2026-07-19): the real AI provider capability registry and its evaluator.

Every test uses a temp cost-log fixture, never the real
data/ai_cost_log.jsonl, and a temp requests-log path, never the real
data/ai_capability_requests.jsonl. Credential env vars are read via
os.environ -- tests patch os.environ directly rather than requiring real
API keys.

    python -m unittest tests.test_ai_capability -v
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

from ai_capability import registry, evaluator


def _write_jsonl(path, records):
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


class TestRegistryListProviders(unittest.TestCase):
    def setUp(self):
        fd, self.cost_log = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        os.remove(self.cost_log)

    def tearDown(self):
        if os.path.exists(self.cost_log):
            os.remove(self.cost_log)

    def test_all_nine_providers_present(self):
        providers = registry.list_providers(self.cost_log)
        names = {p["provider"] for p in providers}
        self.assertEqual(names, {
            "groq", "anthropic", "openai", "google", "xai",
            "deepseek", "alibaba_qwen", "mistral", "local",
        })

    def test_non_groq_providers_are_always_discovery_level_never_fabricated(self):
        providers = registry.list_providers(self.cost_log)
        for p in providers:
            if p["provider"] == "groq":
                continue
            self.assertIsNone(p["real_stats"])
            for metric_name, metric in p["metrics"].items():
                self.assertEqual(metric["level"], "DISCOVERY", f"{p['provider']}.{metric_name} must be DISCOVERY, not fabricated")
                self.assertIsNone(metric["value"])

    def test_groq_with_no_log_history_is_honestly_discovery_too(self):
        providers = registry.list_providers(self.cost_log)
        groq = next(p for p in providers if p["provider"] == "groq")
        self.assertEqual(groq["real_stats"]["calls"], 0)
        self.assertEqual(groq["metrics"]["speed"]["level"], "DISCOVERY")
        self.assertEqual(groq["metrics"]["cost"]["level"], "DISCOVERY")

    def test_groq_real_stats_computed_from_real_log_entries(self):
        _write_jsonl(self.cost_log, [
            {"timestamp": "2026-07-19T10:00:00", "model": "llama-3.1-8b-instant", "cost_usd": 0.0001, "latency_ms": 800},
            {"timestamp": "2026-07-19T11:00:00", "model": "llama-3.1-8b-instant", "cost_usd": 0.0003, "latency_ms": 1200},
        ])
        providers = registry.list_providers(self.cost_log)
        groq = next(p for p in providers if p["provider"] == "groq")
        self.assertEqual(groq["real_stats"]["calls"], 2)
        self.assertAlmostEqual(groq["real_stats"]["avg_cost_usd_per_call"], 0.0002, places=6)
        self.assertAlmostEqual(groq["real_stats"]["avg_latency_ms"], 1000.0, places=1)
        self.assertEqual(groq["metrics"]["speed"]["level"], "REAL")
        self.assertEqual(groq["metrics"]["cost"]["level"], "REAL")
        # quality/availability/context_size/reasoning/multimodal are never
        # measured by this log, regardless of call volume -- still DISCOVERY.
        self.assertEqual(groq["metrics"]["quality"]["level"], "DISCOVERY")
        self.assertEqual(groq["metrics"]["availability"]["level"], "DISCOVERY")

    def test_groq_entries_missing_latency_ms_field_stay_discovery_for_speed(self):
        # Simulates real, pre-2026-07-19 log lines written before latency_ms existed.
        _write_jsonl(self.cost_log, [
            {"timestamp": "2026-07-18T10:00:00", "model": "llama-3.1-8b-instant", "cost_usd": 0.0001},
        ])
        providers = registry.list_providers(self.cost_log)
        groq = next(p for p in providers if p["provider"] == "groq")
        self.assertEqual(groq["real_stats"]["calls"], 1)
        self.assertIsNone(groq["real_stats"]["avg_latency_ms"])
        self.assertEqual(groq["metrics"]["speed"]["level"], "DISCOVERY")
        # cost_usd IS present on this older-shaped line -> still REAL.
        self.assertEqual(groq["metrics"]["cost"]["level"], "REAL")

    def test_configured_reflects_real_environment_credential(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-key"}):
            providers = registry.list_providers(self.cost_log)
            claude = next(p for p in providers if p["provider"] == "anthropic")
            self.assertTrue(claude["configured"])
            # Still DISCOVERY -- configured but never actually called.
            self.assertEqual(claude["metrics"]["speed"]["level"], "DISCOVERY")

    def test_local_provider_has_no_credential_env_var_and_is_never_configured(self):
        providers = registry.list_providers(self.cost_log)
        local = next(p for p in providers if p["provider"] == "local")
        self.assertIsNone(local["credential_env_var"])
        self.assertFalse(local["configured"])


class TestRenderMarkdown(unittest.TestCase):
    """EOS Phase 1 (2026-07-19): the markdown renderer feeding the
    combined executive report's new AI Capability section."""

    def setUp(self):
        fd, self.cost_log = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        os.remove(self.cost_log)

    def tearDown(self):
        if os.path.exists(self.cost_log):
            os.remove(self.cost_log)

    def test_renders_a_row_per_provider(self):
        providers = registry.list_providers(self.cost_log)
        md = registry.render_markdown(providers)
        for p in providers:
            self.assertIn(p["display_name"], md)

    def test_configured_providers_show_a_check_mark(self):
        with patch.dict(os.environ, {"GROQ_KEY": "test-key"}):
            providers = registry.list_providers(self.cost_log)
        md = registry.render_markdown(providers)
        self.assertIn("✅", md)

    def test_never_throws_on_empty_provider_list(self):
        md = registry.render_markdown([])
        self.assertIsInstance(md, str)


class TestCapabilityRequestLog(unittest.TestCase):
    def setUp(self):
        fd, self.requests_log = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        os.remove(self.requests_log)

    def tearDown(self):
        if os.path.exists(self.requests_log):
            os.remove(self.requests_log)

    def test_record_and_read_round_trip(self):
        registry.record_capability_request(
            department="builder", task_type="reasoning", requested_provider="anthropic",
            reason="test request", path=self.requests_log,
        )
        entries = registry.read_capability_requests(self.requests_log)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["department"], "builder")
        self.assertEqual(entries[0]["requested_provider"], "anthropic")
        self.assertIn("timestamp", entries[0])

    def test_missing_file_reads_as_empty_never_raises(self):
        entries = registry.read_capability_requests(os.path.join(tempfile.gettempdir(), "does-not-exist.jsonl"))
        self.assertEqual(entries, [])

    def test_append_only_never_overwrites_prior_requests(self):
        registry.record_capability_request("builder", "reasoning", "anthropic", "r1", path=self.requests_log)
        registry.record_capability_request("design", "multimodal", "openai", "r2", path=self.requests_log)
        entries = registry.read_capability_requests(self.requests_log)
        self.assertEqual(len(entries), 2)


class TestEvaluatorRecommendForTask(unittest.TestCase):
    def setUp(self):
        fd, self.cost_log = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        os.remove(self.cost_log)

    def tearDown(self):
        if os.path.exists(self.cost_log):
            os.remove(self.cost_log)

    def test_no_measured_provider_for_task_returns_no_recommendation(self):
        result = evaluator.recommend_for_task("reasoning", self.cost_log)
        self.assertIsNone(result["recommendation"])
        self.assertIn("anthropic", result["candidates_awaiting_configuration"])

    def test_groq_recommended_once_it_has_real_usage_for_a_task_it_serves(self):
        _write_jsonl(self.cost_log, [
            {"timestamp": "2026-07-19T10:00:00", "model": "llama-3.1-8b-instant", "cost_usd": 0.0001, "latency_ms": 800},
        ])
        result = evaluator.recommend_for_task("content_generation", self.cost_log)
        self.assertEqual(result["recommendation"], "groq")
        self.assertEqual(result["measured_providers"], ["groq"])

    def test_task_type_no_provider_serves_returns_no_recommendation(self):
        result = evaluator.recommend_for_task("task_type_nobody_serves", self.cost_log)
        self.assertIsNone(result["recommendation"])
        self.assertEqual(result["candidates_awaiting_configuration"], [])


if __name__ == "__main__":
    unittest.main()

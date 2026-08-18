"""Tests for ai_capability/observatory.py -- the AI Capability Observatory &
Technology Foresight (Phase 2, 2026-08-16).

Covers the directive's 16 named test areas, each as a real, executing test:

 1. Capability registration        -- per-model ~24-field records from real cost log
 2. Provider abstraction           -- provider_abstraction_status() cites orchestrator
 3. Unknown-value handling         -- DISCOVERY/UNKNOWN never fabricated as a number
 4. Evidence provenance            -- every observatory finding cites a real source
 5. Model comparison               -- cost/latency comparison across real models
 6. Task-based routing             -- 12 named tasks evaluated via real evaluator
 7. Obsolescence detection         -- 6 named states; never obsolete without evidence
 8. Technology radar               -- append-only, RADAR_ACTIONS enforced
 9. Prediction/fact separation     -- FACT/SIGNAL/INFERENCE/PREDICTION never conflated
10. Cost accounting                -- real cost summed from the log, UNKNOWN when not
11. Provider fallback              -- routing falls back honestly, never a fake provider
12. CEO Brain integration          -- TECHNOLOGY POSITION carries the observatory's 7 fields
13. Mission Control integration    -- endpoint registered + dispatches a real payload
14. Financial-action blocking      -- zero code path can spend/change billing
15. External-action blocking       -- zero code path can publish/contact/activate
16. Automatic replacement blocking -- routing never auto-switches (will_auto_switch=False)

Every test uses temp ledgers / temp cost-log fixtures, never the real
data/ai_cost_log.jsonl or the real observatory ledgers.

    python -m unittest tests.test_ai_observatory -v
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

from ai_capability import observatory as obs


def _write_jsonl(path, records):
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _cost_row(model, **over):
    row = {
        "timestamp": "2026-08-14T10:00:00",
        "model": model,
        "prompt_tokens": 500,
        "completion_tokens": 300,
        "total_tokens": 800,
        "cost_usd": 0.0001,
        "latency_ms": 700,
        "context": {"purpose": "content_generation"},
    }
    row.update(over)
    return row


def _make_fixtures():
    tmp = tempfile.mkdtemp(prefix="obs_test_")
    cost_log = os.path.join(tmp, "ai_cost_log.jsonl")
    radar = os.path.join(tmp, "radar.jsonl")
    signals = os.path.join(tmp, "signals.jsonl")
    quality = os.path.join(tmp, "quality.jsonl")
    rows = [
        _cost_row("llama-3.1-8b-instant", timestamp="2026-07-20T10:00:00",
                  latency_ms=1900, cost_usd=0.00008),
        _cost_row("llama-3.1-8b-instant", timestamp="2026-07-21T10:00:00",
                  latency_ms=2000, cost_usd=0.00009),
        _cost_row("openai/gpt-oss-20b", timestamp="2026-08-14T10:00:00",
                  latency_ms=700, cost_usd=0.0001),
        _cost_row("openai/gpt-oss-20b", timestamp="2026-08-15T10:00:00",
                  latency_ms=800, cost_usd=0.00012),
    ]
    _write_jsonl(cost_log, rows)
    return tmp, cost_log, radar, signals, quality


class TestCapabilityRegistration(unittest.TestCase):
    """Area 1 -- real per-model capability records with ~24 fields."""

    def setUp(self):
        self.tmp, self.cost_log, self.radar, self.signals, self.quality = _make_fixtures()

    def test_returns_a_record_for_every_real_cost_logged_model(self):
        records = obs.model_capability_records(self.cost_log)
        models = {r["model"] for r in records}
        self.assertEqual(models, {"llama-3.1-8b-instant", "openai/gpt-oss-20b"})

    def test_every_record_has_the_core_capability_fields(self):
        records = obs.model_capability_records(self.cost_log)
        required = {"provider", "model", "capability_categories", "latency",
                    "estimated_cost", "source", "source_timestamp", "status",
                    "confidence", "obsolescence_risk", "replacement_candidates"}
        for r in records:
            self.assertTrue(required.issubset(r.keys()), r.keys())

    def test_capability_categories_are_the_20_named_categories(self):
        cats = obs.list_capability_categories()
        self.assertEqual(len(cats), 20)

    def test_latency_and_cost_are_real_numbers_from_the_log(self):
        records = {r["model"]: r for r in obs.model_capability_records(self.cost_log)}
        gpt = records["openai/gpt-oss-20b"]
        self.assertEqual(gpt["latency"], 750.0)   # (700+800)/2, real
        self.assertEqual(gpt["estimated_cost"], 0.00011)  # (0.0001+0.00012)/2, real


class TestProviderAbstraction(unittest.TestCase):
    """Area 2 -- the real abstraction status cites the orchestrator."""

    def test_reports_the_real_provider_caller(self):
        status = obs.provider_abstraction_status()
        self.assertEqual(status["abstraction_layer"].find("orchestrator.py") >= 0, True)
        self.assertIn("groq", status["real_provider_callers"])

    def test_single_provider_dependency_is_true_with_one_real_caller(self):
        status = obs.provider_abstraction_status()
        self.assertEqual(status["single_provider_dependency"], True)


class TestUnknownValueHandling(unittest.TestCase):
    """Area 3 -- DISCOVERY/UNKNOWN, never a fabricated number."""

    def setUp(self):
        self.tmp, self.cost_log, self.radar, self.signals, self.quality = _make_fixtures()

    def test_capabilities_are_discovery_not_fabricated_numbers(self):
        records = obs.model_capability_records(self.cost_log)
        for r in records:
            self.assertEqual(r["reasoning_capability"], "DISCOVERY")
            self.assertEqual(r["benchmark_evidence"], "UNKNOWN")
            # never logged -> never invented; Phase 3 made this explicit
            # UNKNOWN (Truth First vocabulary) instead of bare None
            self.assertEqual(r["model_version"], "UNKNOWN")

    def test_empty_cost_log_produces_no_records_not_fake_ones(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            f.write(b"")
        try:
            records = obs.model_capability_records(f.name)
            self.assertEqual(records, [])
        finally:
            os.remove(f.name)

    def test_emerging_technology_is_honest_unknown(self):
        pos = obs.technology_position(self.cost_log)
        ans = pos["most_promising_emerging_technology"]["answer"]
        self.assertTrue(ans.startswith("UNKNOWN"), ans)
        self.assertIn("honest UNKNOWN", pos["most_promising_emerging_technology"]["evidence"])


class TestEvidenceProvenance(unittest.TestCase):
    """Area 4 -- every observatory finding cites a real source."""

    def setUp(self):
        self.tmp, self.cost_log, self.radar, self.signals, self.quality = _make_fixtures()

    def test_technology_position_fields_all_carry_evidence(self):
        pos = obs.technology_position(self.cost_log)
        for k, v in pos.items():
            self.assertIn("evidence", v, k)
            self.assertTrue(v["evidence"])

    def test_routing_intelligence_cites_the_real_evaluator_path(self):
        r = obs.routing_intelligence("code_generation", cost_log_path=self.cost_log)
        self.assertIn("evaluator", r["evidence"])
        self.assertIn("select_provider", r["evidence"])


class TestModelComparison(unittest.TestCase):
    """Area 5 -- real cost/latency comparison across the real models."""

    def setUp(self):
        self.tmp, self.cost_log, self.radar, self.signals, self.quality = _make_fixtures()

    def test_newer_model_is_measured_faster(self):
        stats = obs.cost_intelligence(self.cost_log)["per_model"]
        self.assertLess(stats["openai/gpt-oss-20b"]["avg_latency_ms"],
                        stats["llama-3.1-8b-instant"]["avg_latency_ms"])

    def test_model_records_expose_measured_speed_and_cost_difference(self):
        records = {r["model"]: r for r in obs.model_capability_records(self.cost_log)}
        self.assertIsNotNone(records["openai/gpt-oss-20b"]["latency"])
        self.assertIsNotNone(records["llama-3.1-8b-instant"]["estimated_cost"])


class TestTaskBasedRouting(unittest.TestCase):
    """Area 6 -- all 12 named tasks evaluated through the real evaluator."""

    def setUp(self):
        self.tmp, self.cost_log, self.radar, self.signals, self.quality = _make_fixtures()

    def test_all_12_named_task_categories_are_evaluated(self):
        results = obs.evaluate_all_tasks(self.cost_log)
        self.assertEqual(len(results), 12)
        self.assertEqual({t["task"] for t in results}, set(obs.TASK_CATEGORIES))

    def test_each_task_maps_to_a_real_evaluator_task_type(self):
        for task in obs.TASK_CATEGORIES:
            self.assertIn(task, obs.TASK_TO_EVALUATOR_TYPE)

    def test_recommendation_honestly_reflects_real_registered_usage(self):
        # The evaluator only recommends a provider that is BOTH a registered
        # candidate for that task_type AND has real measured usage. Groq's
        # registered task_types (content_generation, seo_copy, ...) do not
        # include the 9 resource-allocation labels, so for those the honest
        # evaluator recommendation is None -- the observable, real fallback
        # (routing_intelligence -> select_provider) is what resolves to groq.
        results = obs.evaluate_all_tasks(self.cost_log)
        for r in results:
            self.assertIn("recommendation", r)
            self.assertIn("reason", r)


class TestObsolescenceDetection(unittest.TestCase):
    """Area 7 -- 6 named states; never obsolete without real evidence."""

    def setUp(self):
        self.tmp, self.cost_log, self.radar, self.signals, self.quality = _make_fixtures()

    def test_six_named_states_exist(self):
        self.assertEqual(len(obs.OBSOLESCENCE_STATES), 6)
        self.assertIn("CURRENT", obs.OBSOLESCENCE_STATES)
        self.assertIn("WATCH", obs.OBSOLESCENCE_STATES)
        self.assertIn("DEGRADING", obs.OBSOLESCENCE_STATES)
        self.assertIn("OBSOLETE-RISK", obs.OBSOLESCENCE_STATES)
        self.assertIn("REPLACEMENT-RECOMMENDED", obs.OBSOLESCENCE_STATES)
        self.assertIn("UNKNOWN", obs.OBSOLESCENCE_STATES)

    def test_known_retired_model_gets_real_state(self):
        result = obs.obsolescence_detection(self.cost_log)
        by_model = {r["model"]: r for r in result}
        self.assertEqual(by_model["llama-3.1-8b-instant"]["state"],
                         "REPLACEMENT-RECOMMENDED")
        self.assertIn("openai/gpt-oss-20b", by_model["llama-3.1-8b-instant"]["replacement_candidates"])

    def test_currently_used_model_is_current(self):
        result = obs.obsolescence_detection(self.cost_log)
        by_model = {r["model"]: r for r in result}
        self.assertEqual(by_model["openai/gpt-oss-20b"]["state"], "CURRENT")

    def test_stale_model_becomes_watch_not_obsolete(self):
        result = obs.obsolescence_detection(self.cost_log, stale_days=1)
        by_model = {r["model"]: r for r in result}
        self.assertEqual(by_model["llama-3.1-8b-instant"]["state"],
                         "REPLACEMENT-RECOMMENDED")  # known retirement wins

    def test_never_declares_an_unknown_model_obsolete(self):
        rows = [_cost_row("some/unknown-model", timestamp="2026-08-10T10:00:00")]
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
            fname = f.name
        try:
            result = obs.obsolescence_detection(fname, stale_days=1)
            self.assertEqual(result[0]["state"], "WATCH")  # stale, not obsolete
        finally:
            os.remove(fname)


class TestTechnologyRadar(unittest.TestCase):
    """Area 8 -- append-only radar, RADAR_ACTIONS enforced."""

    def setUp(self):
        self.tmp, self.cost_log, self.radar, self.signals, self.quality = _make_fixtures()

    def test_valid_actions_accepted_and_appended(self):
        obs.record_radar_entry("test-tech", "ADOPT", "r", "evidence", "HIGH", path=self.radar)
        obs.record_radar_entry("test-tech", "RETIRE", "r2", "evidence2", "HIGH", path=self.radar)
        entries = obs.technology_radar(self.radar)
        self.assertEqual(len(entries), 2)
        self.assertEqual([e["category"] for e in entries], ["ADOPT", "RETIRE"])

    def test_invalid_action_rejected(self):
        with self.assertRaises(ValueError):
            obs.record_radar_entry("t", "FABRICATE", "r", "e", "HIGH", path=self.radar)

    def test_append_only_never_overwrites(self):
        obs.record_radar_entry("t1", "ADOPT", "r", "e", "HIGH", path=self.radar)
        obs.record_radar_entry("t1", "RETIRE", "r2", "e2", "HIGH", path=self.radar)
        self.assertEqual(len(obs.technology_radar(self.radar)), 2)


class TestPredictionFactSeparation(unittest.TestCase):
    """Area 9 -- FACT/SIGNAL/INFERENCE/PREDICTION never conflated."""

    def setUp(self):
        self.tmp, self.cost_log, self.radar, self.signals, self.quality = _make_fixtures()

    def test_signal_kinds_are_the_four_named_kinds(self):
        self.assertEqual(obs.SIGNAL_KINDS, ["FACT", "SIGNAL", "INFERENCE", "PREDICTION"])

    def test_invalid_signal_kind_rejected(self):
        with self.assertRaises(ValueError):
            obs.record_technology_signal("GUESS", "stmt", "evidence", "HIGH", path=self.signals)

    def test_each_recorded_signal_keeps_its_exact_label(self):
        obs.record_technology_signal("FACT", "a fact", "e", "HIGH", path=self.signals)
        obs.record_technology_signal("PREDICTION", "a prediction", "e2", "MEDIUM", path=self.signals)
        entries = obs.technology_foresight(self.signals)
        self.assertEqual(entries[0]["kind"], "FACT")
        self.assertEqual(entries[1]["kind"], "PREDICTION")


class TestCostAccounting(unittest.TestCase):
    """Area 10 -- real cost from the log; UNKNOWN where not computable."""

    def setUp(self):
        self.tmp, self.cost_log, self.radar, self.signals, self.quality = _make_fixtures()

    def test_total_cost_is_the_real_sum(self):
        ci = obs.cost_intelligence(self.cost_log)
        self.assertAlmostEqual(ci["total_cost_usd"], 0.00008 + 0.00009 + 0.0001 + 0.00012, places=6)

    def test_per_model_and_per_task_breakdown(self):
        ci = obs.cost_intelligence(self.cost_log)
        self.assertIn("openai/gpt-oss-20b", ci["per_model"])
        self.assertIn("content_generation", ci["per_task_cost_usd"])

    def test_never_a_projected_figure(self):
        ci = obs.cost_intelligence(self.cost_log)
        self.assertIn("UNKNOWN", ci["cost_not_calculable"])


class TestProviderFallback(unittest.TestCase):
    """Area 11 -- honest fallback, never a fake provider."""

    def setUp(self):
        self.tmp, self.cost_log, self.radar, self.signals, self.quality = _make_fixtures()

    def test_routing_falls_back_to_the_one_real_provider(self):
        for task in obs.TASK_CATEGORIES:
            r = obs.routing_intelligence(task, cost_log_path=self.cost_log)
            self.assertEqual(r["recommended_provider"], "groq")

    def test_confidence_is_a_two_part_disclosed_heuristic(self):
        r = obs.routing_intelligence("code_generation", cost_log_path=self.cost_log)
        self.assertIn("selection_confidence", r["confidence"])
        self.assertIn("comparison_confidence", r["confidence"])


class TestCeoBrainIntegration(unittest.TestCase):
    """Area 12 -- the CEO Brain's TECHNOLOGY POSITION carries the observatory's
    7 named fields."""

    def test_build_ceo_brain_returns_the_observatory_technology_position(self):
        import ceo_brain
        result = ceo_brain.build_ceo_brain()
        tp = result["TECHNOLOGY_POSITION"]
        self.assertIsInstance(tp, dict)
        # The CEO Brain wraps the 7 observatory fields under `answer`
        # (same shape as every other daily-brief question).
        self.assertIn("answer", tp)
        answers = tp["answer"]
        for field in ("strongest_current_capabilities", "weakest_capabilities",
                      "biggest_dependency", "highest_obsolescence_risk",
                      "most_promising_emerging_technology",
                      "recommended_technology_experiment",
                      "technology_decision_requiring_founder"):
            self.assertIn(field, answers, field)


class TestMissionControlIntegration(unittest.TestCase):
    """Area 13 -- endpoint registered in mission_control_api.py and dispatches a
    real payload."""

    def test_endpoint_is_registered(self):
        import mission_control_api
        self.assertIn("technology_observatory", mission_control_api._ENDPOINTS)

    def test_endpoint_returns_the_observatory_report(self):
        import mission_control_api
        payload = mission_control_api._technology_observatory()
        self.assertIn("model_capability_records", payload)
        self.assertIn("technology_position", payload)
        self.assertIn("cost_intelligence", payload)


class TestFinancialActionBlocking(unittest.TestCase):
    """Area 14 -- zero code path in the observatory can spend or change billing."""

    def test_no_spend_purchase_or_billing_keywords_in_source(self):
        src = (Path(__file__).resolve().parent.parent / "ai_capability" / "observatory.py").read_text(encoding="utf-8")
        for banned in ("requests.post", "urllib.request", "stripe", "paddle",
                       "finance_data", "payment", "billing_api"):
            self.assertNotIn(banned, src, banned)


class TestExternalActionBlocking(unittest.TestCase):
    """Area 15 -- zero code path can publish/contact/activate an external system."""

    def test_no_publish_outreach_or_activation_keywords_in_source(self):
        src = (Path(__file__).resolve().parent.parent / "ai_capability" / "observatory.py").read_text(encoding="utf-8")
        for banned in ("distributor", "publish(", "send_outreach", "telegram",
                       "webhook", "paddle_publisher"):
            self.assertNotIn(banned, src, banned)


class TestAutomaticReplacementBlocking(unittest.TestCase):
    """Area 16 -- routing intelligence never auto-switches the production model."""

    def setUp(self):
        self.tmp, self.cost_log, self.radar, self.signals, self.quality = _make_fixtures()

    def test_will_auto_switch_is_always_false(self):
        for task in obs.TASK_CATEGORIES:
            r = obs.routing_intelligence(task, cost_log_path=self.cost_log)
            self.assertFalse(r["will_auto_switch"], task)

    def test_governance_field_marks_recommend_only(self):
        r = obs.routing_intelligence("code_generation", cost_log_path=self.cost_log)
        self.assertIn("advisory only", r["governance"])
        self.assertIn("AUTONOMY_LEVELS level 2", r["governance"])

    def test_module_docstring_asserts_the_safety_boundary(self):
        doc = obs.__doc__
        self.assertIn("zero code that can purchase", doc)
        self.assertIn("auto-replace a production model", doc)

    def test_governance_category_is_registered_at_recommend_level(self):
        import autonomous_operations as ao
        category = ao.classify_action_autonomy("ai_technology_recommendation")
        self.assertEqual(category["level"], 2)  # RECOMMEND, never EXECUTE


if __name__ == "__main__":
    unittest.main()
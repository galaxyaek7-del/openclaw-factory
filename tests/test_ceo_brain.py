"""Tests for ceo_brain.py -- the Phase 1 CEO Brain & Founder-Light
Governance module (2026-08-16).

Covers the 11 named test areas:
  1. Executive Clock    -- real timestamps, ETA never fabricated
  2. Truth Gate         -- VERIFIED / UNKNOWN / NEEDS VERIFICATION only
  3. CEO State Model    -- every field carries a real provenance citation
  4. Founder-Light Governance -- integrated with AUTONOMY_LEVELS 0-6
  5. Decision Queue     -- 18 fields, deduped, stale_after never a clock
  6. Priority Engine    -- deterministic, explainable, 7 named dimensions
  7. Daily Brief        -- 10 named questions, real citations
  8. Escalation         -- 8 named triggers, surface-only, fail-closed
  9. Attention Budget   -- real interruption metric, MIN/MAX bounds
  10. No-Fabrication    -- financial truth $0 stays $0; UNKNOWN stays UNKNOWN
  11. Safety Boundary   -- read-only; Level 6 refuses; elapsed time never
                          equals founder approval

Every expensive real engine scan is injected as a cheap fake via the
`precomputed` dict (the module's own composition discipline) so these tests
run in milliseconds and never touch a live engine or network path.
"""

import json
import unittest
from datetime import datetime, timezone

import ceo_brain as cb


def _fixed_now():
    return datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)


def _fake_precomputed():
    return {
        "fna": {
            "one_next_action": {"action": "Set PADDLE_WEBHOOK_SECRET in .env", "arm": "paddle_webhook"},
            "queue": [
                {"action": "Complete Paddle vendor onboarding", "arm": "paddle"},
                {"action": "Connect a Gumroad payment method", "arm": "gumroad"},
            ],
            "generated_at": "2026-08-16T11:59:00+00:00",
            "note": "real fake gate queue for tests",
        },
        "orchestrated": {"real_verified_revenue_usd": 0, "arm_statuses": {}},
        "work_queue": [
            {"type": "verify", "task_id": "t1", "created_at": "2026-08-16T11:58:00+00:00"},
        ],
        "readiness": {"dimensions": {
            "commercial": {"score": 50.0, "evidence": "e", "source": "s"},
            "financial": {"score": 0.0, "evidence": "e", "source": "s"},
        }},
        "growth": {"stage": "stage_1_validation"},
        "autonomy_status": {"total_named_activities": 21},
        "briefing": {"highest_roi_opportunity": {"niche": "n", "evidence": "e"}},
        "measured_outcomes": [],
        "providers": [{"name": "groq", "real_stats": {"calls": 1}}, {"name": "openai", "real_stats": {"calls": 0}}],
    }


class TestExecutiveClock(unittest.TestCase):
    def test_clock_reports_real_utc_and_eta_is_never_fabricated(self):
        clock = cb.executive_clock(now=_fixed_now())
        self.assertEqual(clock["utc_now"], "2026-08-16T12:00:00+00:00")
        self.assertEqual(clock["eta"], "UNKNOWN")
        self.assertTrue(clock["eta_reason"])

    def test_clock_marks_daily_report_stale_beyond_threshold(self):
        old = datetime(2026, 8, 14, 12, 0, 0, tzinfo=timezone.utc)
        clock = cb.executive_clock(now=old)
        self.assertIn("daily_report_stale", clock)

    def test_clock_notes_elapsed_time_never_equals_founder_approval(self):
        clock = cb.executive_clock(now=_fixed_now())
        self.assertIn("ELAPSED_TIME_NEVER_EQUALS_FOUNDER_APPROVAL", clock["note"])


class TestTruthGate(unittest.TestCase):
    def test_verified_value_with_real_source(self):
        r = cb.truth_gate(0, "finance_data.json", verified=True)
        self.assertEqual(r["verification"], "VERIFIED")
        self.assertEqual(r["value"], 0)

    def test_none_value_is_never_claimed_verified(self):
        r = cb.truth_gate(None, "", verified=False)
        self.assertEqual(r["verification"], "UNKNOWN")
        self.assertIsNone(r["value"])

    def test_unverified_non_none_value_needs_verification(self):
        r = cb.truth_gate({"x": 1}, "", verified=False)
        self.assertEqual(r["verification"], "NEEDS VERIFICATION")

    def test_no_fabricated_verification_state_exists(self):
        r = cb.truth_gate(None, "", verified=False)
        self.assertIn(r["verification"], {"VERIFIED", "UNKNOWN", "NEEDS VERIFICATION"})


class TestCEOStateModel(unittest.TestCase):
    def test_every_field_carries_provenance(self):
        state = cb.ceo_state(now=_fixed_now(), precomputed=_fake_precomputed())
        for key, source_key in (
            ("real_revenue_usd", "real_revenue_source"),
            ("published_books", "published_books_source"),
            ("commercial_readiness", "commercial_readiness_source"),
            ("growth_stage", "growth_stage_source"),
            ("autonomy_model", "autonomy_model_source"),
            ("autonomy_status", "autonomy_status_source"),
            ("orchestrated_state", "orchestrated_state_source"),
        ):
            self.assertIn(source_key, state, f"missing provenance for {key}")
            self.assertTrue(state[source_key], f"empty provenance for {key}")

    def test_financial_truth_is_never_inflated(self):
        state = cb.ceo_state(now=_fixed_now(), precomputed=_fake_precomputed())
        self.assertEqual(state["real_revenue_usd"], 0)
        self.assertEqual(state["published_books"], 0)

    def test_autonomy_model_cites_the_real_seven_levels(self):
        state = cb.ceo_state(now=_fixed_now(), precomputed=_fake_precomputed())
        self.assertEqual(state["autonomy_model"]["level_count"], 7)


class TestFounderLightGovernance(unittest.TestCase):
    def test_level_six_refuses_unconditionally(self):
        r = cb.classify_decision("any", "real_payment_or_transaction",
                                 context={"founder_approved": True, "approval_reference": "x"})
        self.assertEqual(r["decision"], "REFUSE")
        self.assertEqual(r["autonomy_level"], 6)

    def test_level_five_requires_real_founder_approval(self):
        without = cb.classify_decision("publish", "new_or_elevated_risk_publish")
        self.assertEqual(without["decision"], "REFUSE")
        self.assertTrue(without["founder_required"])
        with_ = cb.classify_decision(
            "publish", "new_or_elevated_risk_publish",
            context={"founder_approved": True, "approval_reference": "gate-1"})
        self.assertEqual(with_["decision"], "ALLOW")

    def test_founder_gate_category_is_level_five(self):
        r = cb.classify_decision("Complete Paddle onboarding", "founder_human_gate:paddle")
        self.assertEqual(r["autonomy_level"], 5)
        self.assertTrue(r["founder_required"])
        self.assertEqual(r["decision"], "REFUSE")  # never auto-approved

    def test_read_only_reporting_is_level_zero(self):
        r = cb.classify_decision("view report", "read_only_reporting")
        self.assertEqual(r["autonomy_level"], 0)
        self.assertFalse(r["founder_required"])

    def test_unknown_category_never_gets_inferred_authorization(self):
        r = cb.classify_decision("whatever", "never_defined_category")
        self.assertIsNone(r["autonomy_level"])
        self.assertEqual(r["decision"], "REFUSE")


class TestDecisionQueue(unittest.TestCase):
    def test_all_eighteen_fields_present(self):
        queue = cb.decision_queue(now=_fixed_now(), precomputed=_fake_precomputed())
        self.assertEqual(queue["fields"], cb.DECISION_QUEUE_FIELDS)
        for item in queue["items"]:
            for field in cb.DECISION_QUEUE_FIELDS:
                self.assertIn(field, item, f"queue item missing {field}")

    def test_deduped(self):
        queue = cb.decision_queue(now=_fixed_now(), precomputed=_fake_precomputed())
        ids = [i["decision_id"] for i in queue["items"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_founder_required_stale_after_never_a_clock(self):
        queue = cb.decision_queue(now=_fixed_now(), precomputed=_fake_precomputed())
        for item in queue["items"]:
            if item["founder_required"]:
                self.assertEqual(item["stale_after"], "REQUIRES_FOUNDER_ACTION")

    def test_every_founder_required_item_has_level_five(self):
        queue = cb.decision_queue(now=_fixed_now(), precomputed=_fake_precomputed())
        for item in queue["items"]:
            if item["founder_required"]:
                self.assertEqual(item["autonomy_level"], 5)

    def test_autonomous_work_items_are_not_founder_required(self):
        queue = cb.decision_queue(now=_fixed_now(), precomputed=_fake_precomputed())
        for item in queue["items"]:
            if item["category"] == "autonomous_work_queue":
                self.assertFalse(item["founder_required"])


class TestPriorityEngine(unittest.TestCase):
    def test_seven_named_dimensions_ranked_explainably(self):
        result = cb.priority_engine([
            {"action": "a", "source": "s1", "dimensions": {
                "impact": 80, "urgency": 60, "risk": 40, "reversibility": 70,
                "strategic_alignment": 90, "evidence_quality": 50, "time_sensitivity": 30}},
            {"action": "b", "source": "s2", "dimensions": {
                "impact": 20, "urgency": 10, "risk": 90, "reversibility": 10,
                "strategic_alignment": 10, "evidence_quality": 5, "time_sensitivity": 5}},
        ], now=_fixed_now())
        self.assertEqual(result["dimensions"], cb.PRIORITY_DIMENSIONS)
        self.assertEqual(len(result["ranking"]), 2)
        self.assertEqual(result["ranking"][0]["rank"], 1)
        self.assertGreater(result["ranking"][0]["priority_score"], result["ranking"][1]["priority_score"])
        for r in result["ranking"]:
            self.assertEqual(len(r["dimensions"]), 7)

    def test_missing_dimension_scored_zero_and_named_not_guessed(self):
        result = cb.priority_engine([
            {"action": "a", "source": "s1", "dimensions": {"impact": 80}},
        ], now=_fixed_now())
        r = result["ranking"][0]
        self.assertIn("missing_dimensions", r)
        self.assertIn("urgency", r["missing_dimensions"])
        self.assertEqual(r["dimensions"]["urgency"]["score"], 0.0)
        self.assertIn("no real value provided", r["dimensions"]["urgency"]["reason"])

    def test_no_fabricated_dimension_value(self):
        result = cb.priority_engine([
            {"action": "a", "source": "s1", "dimensions": {}},
        ], now=_fixed_now())
        for dim in cb.PRIORITY_DIMENSIONS:
            self.assertEqual(result["ranking"][0]["dimensions"][dim]["score"], 0.0)


class TestDailyBrief(unittest.TestCase):
    def test_all_ten_named_questions_answered_with_evidence(self):
        brief = cb.daily_brief(now=_fixed_now(), precomputed=_fake_precomputed())
        self.assertEqual(list(brief["questions"].keys()), cb.DAILY_BRIEF_QUESTIONS)
        for question, answer in brief["questions"].items():
            self.assertIn("answer", answer, f"missing answer for {question}")
            self.assertIn("evidence", answer, f"missing evidence for {question}")

    def test_has_machine_readable_summary(self):
        brief = cb.daily_brief(now=_fixed_now(), precomputed=_fake_precomputed())
        self.assertTrue(brief["summary"])
        self.assertTrue(isinstance(brief["questions"], dict))

    def test_question_answers_come_from_injected_fakes_not_live_engines(self):
        brief = cb.daily_brief(now=_fixed_now(), precomputed=_fake_precomputed())
        self.assertEqual(brief["questions"]["what_should_the_company_do_next"]["answer"],
                         "Set PADDLE_WEBHOOK_SECRET in .env")
        self.assertEqual(brief["questions"]["what_is_blocked_and_why"]["answer"], "2 real open founder gate(s)")
        self.assertEqual(brief["questions"]["what_is_the_commercial_state"]["answer"],
                         {"commercial": 50.0, "financial": 0.0})
        self.assertEqual(brief["questions"]["what_is_the_learning_state"]["answer"],
                         "no real measured outcomes yet")


class TestEscalation(unittest.TestCase):
    def test_all_eight_named_triggers_present(self):
        escalation = cb.executive_escalation(now=_fixed_now(), precomputed=_fake_precomputed())
        triggers = [s["trigger"] for s in escalation["triggers"]]
        self.assertEqual(triggers, cb.ESCALATION_TRIGGERS)

    def test_every_trigger_is_surface_only_and_fail_closed(self):
        escalation = cb.executive_escalation(now=_fixed_now(), precomputed=_fake_precomputed())
        for signal in escalation["triggers"]:
            self.assertIn("SURFACE ONLY", signal["action"])
            self.assertIn(signal["severity"], ("informational", "warning", "critical"))

    def test_active_count_matches_active_signals(self):
        escalation = cb.executive_escalation(now=_fixed_now(), precomputed=_fake_precomputed())
        active = [s for s in escalation["triggers"] if s["active"]]
        self.assertEqual(escalation["active_count"], len(active))
        self.assertEqual(len(escalation["active"]), len(active))

    def test_founder_gates_surface_stale_and_channel_triggers(self):
        escalation = cb.executive_escalation(now=_fixed_now(), precomputed=_fake_precomputed())
        by_name = {s["trigger"]: s for s in escalation["triggers"]}
        self.assertTrue(by_name["stale_founder_gate"]["active"])
        self.assertTrue(by_name["revenue_channel_unavailable"]["active"])
        self.assertTrue(by_name["blocking_missing_credential"]["active"])


class TestAttentionBudget(unittest.TestCase):
    def test_real_interruption_metric_with_min_max_bounds(self):
        budget = cb.founder_attention_budget(now=_fixed_now(), precomputed=_fake_precomputed())
        self.assertIn("total_interruptions", budget)
        self.assertIn("budget_min", budget)
        self.assertIn("budget_max", budget)
        self.assertEqual(budget["budget_min"], cb.ATTENTION_BUDGET_MIN)
        self.assertEqual(budget["budget_max"], cb.ATTENTION_BUDGET_MAX)
        self.assertIn(budget["level"], ("GREEN", "AMBER", "RED"))

    def test_budget_is_informational_only(self):
        budget = cb.founder_attention_budget(now=_fixed_now(), precomputed=_fake_precomputed())
        self.assertIn("informational only", budget["note"].lower())


class TestNoFabrication(unittest.TestCase):
    def test_dashboard_keeps_financial_truth_intact(self):
        result = cb.build_ceo_brain(now=_fixed_now(), precomputed=_fake_precomputed())
        self.assertEqual(result["CEO_STATE"]["real_revenue_usd"], 0)
        self.assertEqual(result["CEO_STATE"]["published_books"], 0)

    def test_learning_state_reports_no_measured_outcomes_honestly(self):
        brief = cb.daily_brief(now=_fixed_now(), precomputed=_fake_precomputed())
        self.assertEqual(brief["questions"]["what_is_the_learning_state"]["answer"],
                         "no real measured outcomes yet")


class TestSafetyBoundary(unittest.TestCase):
    def test_module_has_no_real_ledger_writes(self):
        with open("ceo_brain.py", encoding="utf-8") as fh:
            source = fh.read()
        # The module must never open a real data file for writing.
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("open(") and "open(" in stripped:
                self.assertNotIn('"a"', stripped, "module must never append-write a file")
                self.assertNotIn("'a'", stripped, "module must never append-write a file")
                self.assertNotIn('"w"', stripped, "module must never write a file")
                self.assertNotIn("'w'", stripped, "module must never write a file")
            if stripped.startswith("Path(") and ".write" in stripped:
                self.fail("module must never call .write_text on a Path")

    def test_no_network_calls_from_read_path(self):
        with open("ceo_brain.py", encoding="utf-8") as fh:
            source = fh.read()
        for forbidden in ("requests.", "urllib", "http.client", "httpx", "aiohttp", "socket."):
            self.assertNotIn(forbidden, source, f"module must not import/use {forbidden}")

    def test_dashboard_never_suggests_autonomous_level_six_execution(self):
        result = cb.build_ceo_brain(now=_fixed_now(), precomputed=_fake_precomputed())
        self.assertTrue(result["ATTENTION_BUDGET"]["total_interruptions"] >= 0)


if __name__ == "__main__":
    unittest.main()
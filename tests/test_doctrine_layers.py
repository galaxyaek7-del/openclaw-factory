# -*- coding: utf-8 -*-
"""Doctrine-layer regression tests (Permanent Operating Doctrine sections 3-5).

Each layer gets tests for the rule it enforces, plus tests over the real
repository records the doctrine is supposed to describe. Synthetic fixtures go
to temporary directories; no production ledger is written here.
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import business_arms  # noqa: E402
import cycle_metrics  # noqa: E402
import doctrine_review  # noqa: E402
import handoffs  # noqa: E402
import incident_memory  # noqa: E402
import operational_history  # noqa: E402
import weak_signals  # noqa: E402


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                    encoding="utf-8", newline="\n")


class TestIncidentMemory(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.path = self.tmp / "incidents.jsonl"
        self.record = json.loads(json.dumps(incident_memory.SEED_INCIDENTS[0]))

    def test_every_seed_validates_against_the_real_repository(self):
        for record in incident_memory.SEED_INCIDENTS:
            self.assertEqual([], incident_memory.validate_record(record), record["incident_id"])

    def test_missing_required_field_is_reported(self):
        self.record.pop("root_cause")
        problems = incident_memory.validate_record(self.record)
        self.assertTrue(any("root_cause" in p for p in problems))

    def test_invalid_severity_is_reported(self):
        self.record["severity"] = "catastrophic"
        self.assertTrue(any("severity" in p for p in incident_memory.validate_record(self.record)))

    def test_preventive_control_must_point_at_a_real_artifact(self):
        self.record["preventive_control"]["ref"] = "tests/does_not_exist_doctrine.py"
        problems = incident_memory.validate_record(self.record)
        self.assertTrue(any("does not exist" in p for p in problems))

    def test_explicit_none_control_is_admissible_but_audited(self):
        self.record["preventive_control"]["ref"] = "none"
        self.assertEqual([], incident_memory.validate_record(self.record))
        incident_memory.record_incident(self.record, path=self.path)
        audit = incident_memory.audit(path=self.path)
        self.assertFalse(audit["ok"])
        self.assertTrue(any("no preventive control" in f["problem"] for f in audit["findings"]))

    def test_empty_root_cause_is_rejected(self):
        self.record["root_cause"] = {"verified": [], "hypothesis": []}
        self.assertTrue(any("root_cause" in p
                            for p in incident_memory.validate_record(self.record)))

    def test_duplicate_incident_id_is_not_written_twice(self):
        first = incident_memory.record_incident(self.record, path=self.path)
        second = incident_memory.record_incident(self.record, path=self.path)
        self.assertTrue(first["written"])
        self.assertFalse(second["written"])
        self.assertEqual(1, len(incident_memory.list_incidents(path=self.path)))

    def test_dry_run_writes_nothing(self):
        result = incident_memory.record_incident(self.record, path=self.path, dry_run=True)
        self.assertFalse(result["written"])
        self.assertEqual([], incident_memory.list_incidents(path=self.path))

    def test_search_finds_by_body_text(self):
        incident_memory.record_incident(self.record, path=self.path)
        hits = incident_memory.search_incidents("number format", path=self.path)
        self.assertEqual(1, len(hits))

    def test_real_incident_store_is_clean(self):
        audit = incident_memory.audit()
        self.assertTrue(audit["ok"], audit["findings"])


class TestCycleMetrics(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.path = self.tmp / "cycles.jsonl"

    def test_every_seed_validates(self):
        for record in cycle_metrics.SEED_CYCLES:
            self.assertEqual([], cycle_metrics.validate_cycle(record), record["cycle"])

    def test_rework_ratio_separates_new_from_preexisting(self):
        self.assertEqual(1.0, cycle_metrics.rework_ratio(
            {"rework": {"new_defects": 7, "preexisting": 0}}))
        self.assertEqual(0.0, cycle_metrics.rework_ratio(
            {"rework": {"new_defects": 0, "preexisting": 2}}))
        self.assertIsNone(cycle_metrics.rework_ratio(
            {"rework": {"new_defects": 0, "preexisting": 0}}))

    def test_unmeasured_time_must_state_a_reason(self):
        record = json.loads(json.dumps(cycle_metrics.SEED_CYCLES[0]))
        record["time"] = {"measured": False, "reason": ""}
        self.assertTrue(any("reason" in p for p in cycle_metrics.validate_cycle(record)))

    def test_repeated_deliverables_are_flagged(self):
        record = json.loads(json.dumps(cycle_metrics.SEED_CYCLES[0]))
        cycle_metrics.record_cycle(record, path=self.path)
        repeat = json.loads(json.dumps(record))
        repeat["cycle"] = record["cycle"] + 1
        cycle_metrics.record_cycle(repeat, path=self.path)
        audit = cycle_metrics.repetition_audit(path=self.path)
        self.assertFalse(audit["ok"])
        self.assertTrue(any("identical deliverables" in f["finding"] for f in audit["findings"]))

    def test_empty_cycle_is_flagged_as_unproductive(self):
        record = json.loads(json.dumps(cycle_metrics.SEED_CYCLES[0]))
        record.update({"changed_since_previous": {"files": 0},
                       "defects": {"critical": 0, "high": 0, "medium": 0, "low": 0},
                       "new_capability": None,
                       "no_new_capability_reason": "verification-only cycle",
                       "deliverables": ["repeat"],
                       "checks_new": [], "checks_repeated": []})
        cycle_metrics.record_cycle(record, path=self.path)
        audit = cycle_metrics.repetition_audit(path=self.path)
        self.assertTrue(any("no artifact" in f["finding"] for f in audit["findings"]))

    def test_seed_is_idempotent(self):
        first = cycle_metrics.seed(path=self.path)
        second = cycle_metrics.seed(path=self.path)
        self.assertEqual(2, first["written"])
        self.assertEqual(0, second["written"])

    def test_real_cycle_history_is_consistent(self):
        audit = cycle_metrics.repetition_audit()
        self.assertTrue(audit["ok"], audit["findings"])
        summary = cycle_metrics.summary()
        self.assertGreaterEqual(summary["cycles"], 2)
        self.assertEqual(summary["cycles"],
                         summary["time_measured_cycles"] + summary["time_unmeasured_cycles"])


class TestHandoffs(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.path = self.tmp / "handoffs.jsonl"
        self.record = json.loads(json.dumps(handoffs.seed_records()[0]))

    def test_every_seed_validates(self):
        for record in handoffs.seed_records():
            self.assertEqual([], handoffs.validate_handoff(record), record["handoff_id"])

    def test_blocked_handoff_must_name_the_delay(self):
        self.record.update({"status": "BLOCKED", "delay_reason": None})
        self.assertTrue(any("delay_reason" in p
                            for p in handoffs.validate_handoff(self.record)))

    def test_accepted_handoff_requires_existing_evidence(self):
        self.record.update({"status": "ACCEPTED", "evidence": ["reports/does-not-exist.json"]})
        self.assertTrue(any("does not exist" in p
                            for p in handoffs.validate_handoff(self.record)))

    def test_accepted_handoff_with_real_evidence_passes(self):
        self.record.update({"status": "ACCEPTED", "evidence": ["operational_history.py"]})
        self.assertEqual([], handoffs.validate_handoff(self.record))

    def test_latest_state_replaces_open_status(self):
        handoffs.record_handoff(self.record, path=self.path)
        update = json.loads(json.dumps(self.record))
        update.update({"status": "ACCEPTED", "evidence": ["operational_history.py"]})
        handoffs.record_handoff(update, path=self.path)
        latest = handoffs.latest_by_id(path=self.path)
        self.assertEqual("ACCEPTED", latest[self.record["handoff_id"]]["status"])
        self.assertEqual([], handoffs.open_handoffs(path=self.path))

    def test_real_handoff_store_has_no_invalid_records(self):
        for record in handoffs.latest_by_id().values():
            self.assertEqual([], handoffs.validate_handoff(record), record["handoff_id"])


class TestWeakSignals(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.path = self.tmp / "signals.jsonl"

    def _signal(self, index, group):
        return {
            "signal_id": "S-%02d" % index,
            "observed_at": "2026-10-19T00:00:00+00:00",
            "source": "test-source-%d" % index,
            "source_date": "2026-10-19",
            "independent_group": group,
            "topic": "topic-a",
            "summary": "observation %d" % index,
            "relevance": "medium",
            "confidence": "OBSERVED",
        }

    def test_every_seed_validates(self):
        for record in weak_signals.SEED_SIGNALS:
            self.assertEqual([], weak_signals.validate_signal(record), record["signal_id"])

    def test_two_signals_are_not_enough(self):
        for i in range(2):
            weak_signals.record_signal(self._signal(i, "g%d" % i), path=self.path)
        result = weak_signals.review_triggers(path=self.path)
        self.assertEqual([], result["triggered"])
        self.assertEqual("NOT_ENOUGH_EVIDENCE", result["topics"][0]["verdict"])

    def test_three_signals_from_one_group_are_not_enough(self):
        for i in range(3):
            weak_signals.record_signal(self._signal(i, "same"), path=self.path)
        result = weak_signals.review_triggers(path=self.path)
        self.assertEqual([], result["triggered"])

    def test_three_signals_from_two_independent_groups_trigger_review(self):
        for i, group in enumerate(("ledger", "ledger", "external")):
            weak_signals.record_signal(self._signal(i, group), path=self.path)
        result = weak_signals.review_triggers(path=self.path)
        self.assertEqual(["topic-a"], result["triggered"])

    def test_invalid_confidence_is_rejected(self):
        bad = self._signal(0, "g")
        bad["confidence"] = "CERTAIN"
        self.assertTrue(any("confidence" in p for p in weak_signals.validate_signal(bad)))


class TestBusinessArms(unittest.TestCase):
    def test_state_vocabulary_is_the_doctrine_vocabulary(self):
        self.assertEqual(("READY", "PARTIAL", "PLANNED", "BLOCKED", "REVENUE_VERIFIED"),
                         business_arms.STATUSES)

    def test_no_arm_claims_ready_while_naming_a_blocker(self):
        state = business_arms.arm_status()
        self.assertEqual([], business_arms.validate_arm_states(state))

    def test_revenue_verified_is_unreachable_without_arm_attribution(self):
        self.assertEqual(0, business_arms.arm_status()["counts"]["REVENUE_VERIFIED"])

    def test_planned_arms_have_no_implementation_evidence(self):
        state = business_arms.arm_status()
        for arm in state["arms"].values():
            if arm["status"] == "PLANNED":
                self.assertEqual([], arm["implementation_present"])

    def test_real_evidence_arms_are_not_planned(self):
        arms = business_arms.arm_status()["arms"]
        self.assertIn(arms["digital_products"]["status"], ("PARTIAL", "BLOCKED"))
        self.assertIn(arms["childrens_media_studio"]["status"], ("PARTIAL", "BLOCKED"))


class TestClaimAudit(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_registry_behind_evidence_is_flagged(self):
        _write_json(self.tmp / "data" / "product_batch_12.json",
                    {"products": [{"id": "B12-001", "status": "READY_FOR_REVIEW"}]})
        _write_json(self.tmp / "data" / "operational_history.json",
                    {"products": [{"product_id": "B12-001",
                                   "highest_contiguous_verified": "CHECKOUT_VERIFIED"}]})
        findings = doctrine_review.audit_registry_drift(root=self.tmp)
        self.assertEqual(1, len(findings))
        self.assertEqual("REGISTRY_BEHIND_EVIDENCE", findings[0]["code"])

    def test_advanced_registry_state_is_not_flagged(self):
        _write_json(self.tmp / "data" / "product_batch_12.json",
                    {"products": [{"id": "B12-001", "status": "READY_FOR_AUTHORIZATION"}]})
        _write_json(self.tmp / "data" / "operational_history.json",
                    {"products": [{"product_id": "B12-001",
                                   "highest_contiguous_verified": "READY_FOR_AUTHORIZATION"}]})
        self.assertEqual([], doctrine_review.audit_registry_drift(root=self.tmp))

    def test_task_title_naming_another_product_is_flagged(self):
        _write_json(self.tmp / "data" / "first_sale_tasks_b12-004.json",
                    {"tasks": {"publish": {"id": "publish",
                                           "title": "Publish B12-001 (requires founder phrase)"}}})
        findings = doctrine_review.audit_task_titles(root=self.tmp)
        self.assertEqual(1, len(findings))
        self.assertEqual("TASK_TITLE_MISMATCH", findings[0]["code"])

    def test_manifest_status_contradicting_evidence_is_critical(self):
        _write_json(self.tmp / "data" / "operational_history.json",
                    {"products": [{"product_id": "B12-010",
                                   "highest_contiguous_verified": "READY_FOR_AUTHORIZATION"}]})
        _write_json(self.tmp / "reports" / "B12-010" / "MANIFEST_2026-10-19.json",
                    {"product_id": "B12-010", "status": "CHECKOUT_VERIFIED"})
        findings = doctrine_review.audit_release_records(root=self.tmp)["findings"]
        self.assertTrue(any(f["code"] == "MANIFEST_STATUS_CONTRADICTS_STATE" for f in findings))

    def test_pass_row_citing_a_missing_path_is_critical(self):
        _write_json(self.tmp / "reports" / "B12-010" / "RELEASE_BASELINE_2026-10-19.json",
                    {"product_id": "B12-010",
                     "verification": [{"check": "x", "status": "PASS",
                                       "evidence": "reports/B12-010/NOPE.json"}]})
        result = doctrine_review.audit_release_records(root=self.tmp)
        self.assertEqual(1, result["claims_checked"])
        self.assertTrue(any(f["code"] == "EVIDENCE_PATH_MISSING" for f in result["findings"]))

    def test_pass_row_disclaiming_its_own_check_is_critical(self):
        _write_json(self.tmp / "reports" / "B12-010" / "RELEASE_BASELINE_2026-10-19.json",
                    {"product_id": "B12-010",
                     "verification": [{"check": "x", "status": "PASS",
                                       "evidence": "not run in this environment"}]})
        findings = doctrine_review.audit_release_records(root=self.tmp)["findings"]
        self.assertTrue(any(f["code"] == "PASS_CONTRADICTED_BY_ITS_OWN_EVIDENCE"
                            for f in findings))

    def test_unlinked_prose_evidence_is_a_warning_not_a_critical(self):
        _write_json(self.tmp / "reports" / "B12-010" / "RELEASE_BASELINE_2026-10-19.json",
                    {"product_id": "B12-010",
                     "verification": [{"check": "x", "status": "PASS",
                                       "evidence": "recalculated independently and matched"}]})
        result = doctrine_review.audit_release_records(root=self.tmp)
        self.assertEqual(0, sum(1 for f in result["findings"] if f["severity"] == "CRITICAL"))
        self.assertEqual(1, sum(1 for f in result["findings"] if f["severity"] == "WARNING"))

    def test_real_repository_has_zero_critical_unsupported_claims(self):
        result = doctrine_review.audit_structured_claims()
        self.assertEqual(0, result["critical"], result["findings"])

    def test_real_registry_drift_is_the_three_known_products(self):
        findings = doctrine_review.audit_registry_drift()
        flagged = {f["product_id"] for f in findings}
        self.assertEqual({"B12-001", "B12-003", "B12-004"}, flagged)


class TestDoctrineLayerMatrix(unittest.TestCase):
    def test_every_doctrine_layer_has_a_module_and_a_test(self):
        matrix = doctrine_review.layer_matrix()
        for key, layer in matrix["layers"].items():
            self.assertIn(layer["status"], ("EXISTS", "PARTIAL"), key)
            self.assertEqual([], layer["modules_missing"], key)

    def test_all_layers_are_fully_proven(self):
        matrix = doctrine_review.layer_matrix()
        self.assertEqual(0, matrix["counts"]["MISSING"])
        self.assertEqual(0, matrix["counts"]["PARTIAL"])

    def test_review_answers_six_questions_with_a_status(self):
        review = doctrine_review.build_doctrine_review()
        self.assertEqual(6, len(review["questions"]))
        for item in review["questions"]:
            self.assertIn(item["status"],
                          ("OBSERVED", "DERIVED", "INFERRED", "ESTIMATED",
                           "UNKNOWN", "BLOCKED", "NOT_ENOUGH_EVIDENCE"))

    def test_review_status_never_claims_pass_while_minus_one_hold(self):
        review = doctrine_review.build_doctrine_review()
        self.assertEqual(set(review["status"]),
                         {"claim_audit", "incident_memory", "repetition", "layers"})

    def test_markdown_render_includes_every_arm(self):
        text = doctrine_review.render_markdown(doctrine_review.build_doctrine_review())
        for cfg in business_arms.ARMS.values():
            self.assertIn(cfg["name"], text)


class TestReleaseAndHistoryInvariants(unittest.TestCase):
    def test_release_price_history_names_each_candidate(self):
        baseline = json.loads((ROOT / "reports" / "B12-010" /
                               "RELEASE_BASELINE_2026-10-19.json")
                              .read_text(encoding="utf-8"))
        price = baseline["price"]
        tested = {row["price_usd"] for row in price["candidates_tested"]}
        named = {row["price_usd"] for row in price["candidate_outcomes"]}
        self.assertEqual(tested, named)
        selected = [row for row in price["candidate_outcomes"]
                    if row["outcome"] == "SELECTED"]
        self.assertEqual([price["usd"]], [row["price_usd"] for row in selected])
        for row in price["candidate_outcomes"]:
            self.assertTrue(row["reason"], row)
        self.assertEqual([39.0], [row["price_usd"] for row in price["withdrawn"]])
        self.assertIn("39.00", price["history_note"])

    def test_operational_history_labels_use_the_extended_vocabulary(self):
        self.assertIn("ESTIMATED", operational_history.LABELS)
        self.assertIn("BLOCKED", operational_history.LABELS)

    def test_verified_milestones_are_a_prefix(self):
        snapshot = json.loads((ROOT / "data" / "operational_history.json")
                              .read_text(encoding="utf-8"))
        for product in snapshot["products"]:
            flags = [product["milestones"][m]["status"] == "VERIFIED"
                     for m in operational_history.MILESTONES]
            seen_gap = False
            for flag in flags:
                if not flag:
                    seen_gap = True
                elif seen_gap:
                    self.fail("%s has a gap before a verified milestone" % product["product_id"])

    def test_highest_contiguous_verified_matches_the_prefix(self):
        snapshot = json.loads((ROOT / "data" / "operational_history.json")
                              .read_text(encoding="utf-8"))
        for product in snapshot["products"]:
            verified = [m for m in operational_history.MILESTONES
                        if product["milestones"][m]["status"] == "VERIFIED"]
            expected = verified[-1] if verified else None
            self.assertEqual(expected, product["highest_contiguous_verified"],
                             product["product_id"])

    def test_no_product_claims_a_first_sale(self):
        snapshot = json.loads((ROOT / "data" / "operational_history.json")
                              .read_text(encoding="utf-8"))
        for product in snapshot["products"]:
            self.assertNotEqual("VERIFIED",
                                product["milestones"]["FIRST_SALE_VERIFIED"]["status"],
                                product["product_id"])
        self.assertEqual(0, snapshot["summary"]["first_sale_verified"])

    def test_verified_milestones_carry_evidence_and_a_valid_label(self):
        snapshot = json.loads((ROOT / "data" / "operational_history.json")
                              .read_text(encoding="utf-8"))
        for product in snapshot["products"]:
            for name, entry in product["milestones"].items():
                self.assertIn(entry["label"], operational_history.LABELS, name)
                if entry["status"] == "VERIFIED":
                    self.assertTrue(entry["evidence"], (product["product_id"], name))
                    self.assertTrue(entry["source"], (product["product_id"], name))


if __name__ == "__main__":
    unittest.main()

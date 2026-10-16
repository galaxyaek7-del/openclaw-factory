"""Phase 4 integration: BKL-002/003/004 pieces and the dynamic measurement status.

Offline. Temp paths for anything written. No network, no Gumroad call.
"""
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


EVAL = _load("cycle81_eval_p4", "scripts/cycle81_product_evaluation.py")
CSV = _load("gumroad_csv_parser_p4", "src/measurement/gumroad_csv_parser.py")
VALID_STATUSES = ["LEGACY_HARDCODED", "MINIMAL_CONNECTED", "LIVE_PARTIAL", "FULLY_CONNECTED"]


class TestPhase4Integration(unittest.TestCase):
    def test_evidence_gate_modes(self):
        from affiliate import opportunities as opp
        fields = {g: "x" for g in opp.EVIDENCE_GATES}
        self.assertFalse(opp.evidence_gate_check(fields)["pass"])                      # strict default
        # A synthetic mode cannot wave an unlabelled entry through.
        self.assertFalse(opp.evidence_gate_check(fields, mode="SIMULATION")["pass"])
        sim = opp.evidence_gate_check(dict(fields, SIMULATED=True), mode="SIMULATION")
        self.assertTrue(sim["pass"])
        self.assertFalse(sim["real_evidence"])
        # The queue writer keeps the strict gate even for a labelled simulation.
        with tempfile.TemporaryDirectory() as d:
            full = {f: "value" for f in opp.REQUIRED_FIELDS}
            full.update(fields, SIMULATED=True)
            r = opp.add_opportunity(full, queue_path=str(Path(d) / "q.jsonl"))
            self.assertEqual(r["status"], "OPPORTUNITY_CANDIDATE")
        self.assertFalse(opp.validate_evidence({"source": "x", "timestamp": "t", "confidence": 0.5,
                                                "data_url": "u"})["valid"])          # placeholder source

    def test_pagevisit_receiver_ready(self):
        if not shutil.which("node"):
            self.skipTest("node not available")
        with tempfile.TemporaryDirectory() as d:
            code = ("const {PageVisitReceiver}=require(process.argv[1]);"
                    "const r=new PageVisitReceiver({log_path:process.argv[2]+'/l.jsonl',stats_path:process.argv[2]+'/s.json'});"
                    "console.log(JSON.stringify(r.to_evidence()));")
            out = subprocess.run(["node", "-e", code, str(ROOT / "src/measurement/pagevisit_receiver.js"), d],
                                 capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        ev = json.loads(out.stdout.strip().splitlines()[-1])
        self.assertEqual(ev["status"], "RECEIVER_READY_NO_VISITS_YET")
        self.assertFalse(ev["real_evidence"])
        self.assertFalse(ev["public_route_registered"])

    def test_gumroad_csv_fallback_ready(self):
        with tempfile.TemporaryDirectory() as d:
            p = CSV.GumroadCSVParser(csv_dir=str(Path(d) / "e"), parsed_path=str(Path(d) / "p.json"))
            self.assertEqual(p.get_latest_analytics()["status"], "AWAITING_EXPORT")
            ev = p.to_evidence()
            self.assertFalse(ev["real_evidence"])
            self.assertFalse(ev["format_verified"])

    def test_measurement_status_dynamic(self):
        status = EVAL.compute_measurement_status()
        self.assertIn(status["status"], VALID_STATUSES)
        self.assertEqual(len(status["connected_sources"]) + len(status["blocked_sources"]), 4)
        # Not hard-coded: the result follows the recorded evidence.
        on, off = (lambda: {"connected": True}), (lambda: {"connected": False})
        for n_on, expected in ((0, "LEGACY_HARDCODED"), (1, "MINIMAL_CONNECTED"),
                               (2, "LIVE_PARTIAL"), (4, "FULLY_CONNECTED")):
            checks = {k: (on if i < n_on else off) for i, k in enumerate(("a", "b", "c", "d"))}
            self.assertEqual(EVAL.compute_measurement_status(checks)["status"], expected)
        # Nothing is connected without a file behind it.
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(EVAL.check_gumroad_csv_parser(str(Path(d) / "none.json"))["connected"])
            self.assertFalse(EVAL.check_utm_tracker(str(Path(d) / "a"), str(Path(d) / "b"), str(Path(d) / "c"))["connected"])

    @unittest.skipIf(os.environ.get("GITHUB_ACTIONS") == "true",
                     "sprint-local check: compares this machine's working copy with the baseline "
                     "taken at sprint start; a CI checkout has no such working copy")
    def test_governance_unchanged(self):
        # Protected files must be byte-identical to the baseline recorded at
        # sprint start (reports/phase4_governance_baseline.json). A plain
        # `git diff` cannot answer "changed in this sprint", because two of
        # these files already carried another tool's uncommitted edits.
        baseline = json.loads((ROOT / "reports" / "phase4_governance_baseline.json").read_text(encoding="utf-8"))
        for rel, rec in baseline["files"].items():
            digest = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
            self.assertEqual(digest, rec["sha256"], f"{rel} changed during Phase 4")
        self.assertIn("server.js", baseline["files"])


if __name__ == "__main__":
    unittest.main()

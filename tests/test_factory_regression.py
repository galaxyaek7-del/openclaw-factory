import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import factory_regression as fr  # noqa: E402


def test_pytest_summary_is_parsed_with_failing_ids():
    out = "FAILED tests/test_a.py::T::test_x - boom\nFAILED tests/test_b.py::test_y\n2 failed, 40 passed in 3s"
    assert fr.parse_pytest(out) == (40, 2, ["tests/test_a.py::T::test_x", "tests/test_b.py::test_y"])
    assert fr.parse_pytest("12 passed in 1s") == (12, 0, [])
    assert fr.parse_pytest("1 error in 0.5s")[1] == 1


def fake_runner(py_out, py_rc, node_rc):
    def runner(cmd, timeout):
        if "pytest" in cmd:
            return SimpleNamespace(stdout=py_out, stderr="", returncode=py_rc), 1.0
        return SimpleNamespace(stdout="", stderr="", returncode=node_rc), 0.1
    return runner


def make_tests(tmp, py, js):
    d = tmp / "tests"; d.mkdir()
    for n in py:
        (d / f"{n}.py").write_text("")
    for n in js:
        (d / f"{n}.js").write_text("")
    return d


def test_a_green_run_and_missing_files_are_reported(tmp_path):
    d = make_tests(tmp_path, ["a"], ["j"])
    r = fr.run_gate(py=["a", "gone"], js=["j"], tests_dir=d, runner=fake_runner("5 passed in 1s", 0, 0))
    assert r["failed"] == 0 and r["python"]["passed"] == 5 and r["skipped_missing"] == ["gone.py"]


def test_failures_from_pytest_and_node_are_counted_and_named(tmp_path):
    d = make_tests(tmp_path, ["a"], ["j"])
    r = fr.run_gate(py=["a"], js=["j"], tests_dir=d, runner=fake_runner("FAILED tests/a.py::t\n1 failed, 4 passed in 1s", 1, 1))
    assert r["failed"] == 2 and "tests/a.py::t" in r["failures"] and "j.js" in r["failures"]


def test_a_pytest_crash_without_a_summary_is_still_a_failure(tmp_path):
    d = make_tests(tmp_path, ["a"], [])
    r = fr.run_gate(py=["a"], js=[], tests_dir=d, runner=fake_runner("Traceback ...", 2, 0))
    assert r["failed"] >= 1


def test_once_a_day_and_result_file(tmp_path):
    out, st = tmp_path / "o.json", tmp_path / "s.json"
    gate = lambda: {"python": {"files": 1, "passed": 3, "failed": 0}, "node": {"files": 1, "passed_files": 1, "failed_files": 0}, "failed": 0, "failures": [], "skipped_missing": [], "seconds": {}}  # noqa: E731
    now = datetime(2026, 11, 6, 3, 0, tzinfo=timezone.utc)
    assert fr.run_once(now, out=out, state=st, gate=gate)["action"] == "ok" and json.loads(out.read_text())["failed"] == 0
    assert fr.run_once(now, out=out, state=st, gate=gate)["action"] == "none"
    assert fr.run_once(now, force=True, out=out, state=st, gate=gate)["action"] == "ok"

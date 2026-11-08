import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import doctor_round_periodic as dp  # noqa: E402

NOW = datetime(2026, 11, 8, 6, tzinfo=timezone.utc)


def run(tmp_path, now, problems, sent):
    return dp.run_once(now, tmp_path / "s.json", tmp_path / "l.json", runner=lambda: {"agent_problems": problems, "needs_founder": []},
                       sender=lambda t: sent.append(t) or {"sent": True})


def test_clean_round_saves_the_report_and_sends_nothing(tmp_path):
    sent = []
    r = run(tmp_path, NOW, [], sent)
    assert r["action"] == "ran" and sent == []
    assert json.loads((tmp_path / "l.json").read_text(encoding="utf-8"))["problems"] == []


def test_a_new_problem_set_alerts_once_and_the_same_set_never_repeats(tmp_path):
    sent = []
    r1 = run(tmp_path, NOW, ["regression gate: 2 failing"], sent)
    assert "founder alerted" in r1["detail"] and len(sent) == 1 and "regression gate" in sent[0]
    run(tmp_path, NOW + timedelta(hours=7), ["regression gate: 2 failing"], sent)
    assert len(sent) == 1, "same problem set: no second message"
    run(tmp_path, NOW + timedelta(hours=14), ["regression gate: 2 failing", "pin B18-006 broken"], sent)
    assert len(sent) == 2, "a changed set alerts again"


def test_runs_at_most_every_six_hours_and_a_failing_sender_does_not_stop_it(tmp_path):
    sent = []
    run(tmp_path, NOW, [], sent)
    assert run(tmp_path, NOW + timedelta(hours=5), [], sent)["action"] == "none"
    boom = lambda t: (_ for _ in ()).throw(RuntimeError("telegram down"))  # noqa: E731
    r = dp.run_once(NOW + timedelta(hours=7), tmp_path / "s.json", tmp_path / "l.json", runner=lambda: {"agent_problems": ["x"]}, sender=boom)
    assert r["action"] == "ran" and "alert failed" in r["detail"]

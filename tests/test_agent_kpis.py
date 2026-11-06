import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import agent_kpis as ak  # noqa: E402

NOW = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)


def task(agent, status, at="2026-11-05T08:00:00", error=None):
    return {"agent": agent, "status": status, "at": at, "error": error}


def rows(tasks, execs=(), costs=()):
    return {r["agent"]: r for r in ak.compute(list(execs), tasks, list(costs), NOW)["agents"]}


def test_success_rate_and_degraded_flag_need_enough_tasks():
    few = rows([task("a", "done"), task("a", "stopped")])
    assert few["a"]["task_success_rate"] == 0.5 and "DEGRADED" not in few["a"]["flags"]
    many = rows([task("b", "done")] * 6 + [task("b", "stopped", error="qa REVISE: unfocused")] * 4)
    assert many["b"]["flags"] == ["DEGRADED"] and many["b"]["top_stop_reason"].startswith("qa REVISE")


def test_contract_failures_and_timeouts_are_named_separately():
    r = rows([task("s", "failed", error="output did not satisfy the step contract"), task("s", "failed", error="Request timed out."), task("s", "done")])
    assert r["s"]["contract_failures"] == 1 and r["s"]["timeouts"] == 1
    assert {"CONTRACT_FAILURES", "TIMEOUTS"} <= set(r["s"]["flags"])


def test_idle_after_a_week_and_cost_totals():
    d = ak.compute([{"agent": "old", "started_at": "2026-10-20T00:00:00+00:00", "duration_ms": 900, "prompt_tokens": 10, "completion_tokens": 5}], [],
                   [{"cost_usd": 0.01, "total_tokens": 100}, {"cost_usd": 0.02, "total_tokens": 50}], NOW)
    assert d["agents"][0]["flags"] == ["IDLE"] and d["agents"][0]["tokens"] == 15
    assert d["total_cost_usd"] == 0.03 and d["total_tokens"] == 150 and d["llm_calls"] == 2


def test_an_agent_active_today_is_not_idle():
    assert rows([task("x", "done", at="2026-11-06T07:00:00+00:00")])["x"]["flags"] == []


def test_old_failures_do_not_degrade_an_agent_that_recovered():
    from datetime import timedelta
    now = datetime(2026, 11, 6, tzinfo=timezone.utc)
    old = (now - timedelta(days=40)).isoformat()
    new = (now - timedelta(days=2)).isoformat()
    tasks = [{"agent": "scout", "status": "failed", "at": old} for _ in range(10)] +             [{"agent": "scout", "status": "done", "at": new} for _ in range(9)]
    assert "DEGRADED" not in ak.compute([], tasks, [], now=now)["agents"][0]["flags"]
    bad = [{"agent": "scout", "status": "failed", "at": new} for _ in range(10)]
    assert "DEGRADED" in ak.compute([], bad, [], now=now)["agents"][0]["flags"]

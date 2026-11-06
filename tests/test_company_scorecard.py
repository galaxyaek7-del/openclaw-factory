import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import company_scorecard as cs  # noqa: E402

STEPS = {k: ["none"] for k in ("demand_sensing", "market_evidence", "golden_hunter", "agent_product_chain", "publish_approved", "site_publish", "sales_poll", "autonomy_daily", "n8n_watchdog")}


def levels(steps=STEPS, stages=None, demand=False, facts=None):
    rows = cs.evaluate(steps, stages if stages is not None else {"9": "OK"}, demand, facts or {"inspectors_exist": True, "trust_draft": True})
    return {r["capability"]: r["level"] for r in rows}


def test_levels_follow_evidence_not_hope():
    lv = levels()
    assert lv["Demand sensing"] == "AUTOMATIC" and lv["Production of new products"] == "AUTOMATIC_GATED"
    assert lv["Social distribution (Pinterest)"] == "HUMAN_GATE" and lv["Legal entity and policies"] == "BLOCKED_FOUNDER"
    assert lv["Localisation (other languages)"] == "NOT_BUILT" and lv["Payout and finance truth"] == "UNKNOWN"


def test_a_step_that_never_ran_or_whose_last_run_failed_is_not_automatic():
    steps = dict(STEPS); steps["sales_poll"] = ["none", "failed"]; steps.pop("golden_hunter")
    lv = levels(steps)
    assert lv["Sales measurement"] == "UNKNOWN" and lv["Opportunity selection"] == "UNKNOWN"


def test_unlinked_telegram_blocks_monitoring_and_score_counts_only_automatic():
    lv = levels(stages={"9": "BLOCKED"})
    assert lv["Monitoring, alerts, self-check"] == "BLOCKED_FOUNDER"
    sc = cs.score(cs.evaluate(STEPS, {"9": "OK"}, False, {"inspectors_exist": True, "trust_draft": True}))
    assert sc["automatic_or_gated"] == sum(1 for l in levels().values() if l in ("AUTOMATIC", "AUTOMATIC_GATED"))


def test_loop_steps_window(tmp_path):
    import json
    log = tmp_path / "l.log"
    log.write_text(json.dumps({"timestamp": "2026-11-06T10:00:00Z", "actions": [{"step": "a", "action": "ok"}]}) + "\n" +
                   json.dumps({"timestamp": "2026-11-01T10:00:00Z", "actions": [{"step": "old", "action": "ok"}]}) + "\n")
    s = cs.loop_steps(log, datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc))
    assert "a" in s and "old" not in s

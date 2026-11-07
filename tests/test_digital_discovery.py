import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from golden_hunter import digital_discovery as dd  # noqa: E402

GOOD = "##TITLE##\nRental Property Cash Flow Analyzer\n##TYPE##\nexcel_workbook\n##TOPIC##\nWhether a rental deal covers its costs.\n##AUDIENCE##\nsmall landlords\n##PRICE##\n$24"
DECLINE = "##TITLE##\nNONE\n##TYPE##\nnone\n##TOPIC##\nno recurring decision behind this signal\n##AUDIENCE##\nnone\n##PRICE##\n0"
NOW = datetime(2026, 11, 6, 12, tzinfo=timezone.utc)


def test_parse_accepts_a_valid_proposal_and_a_decline():
    p = dd.parse(GOOD)
    assert p == {"title": "Rental Property Cash Flow Analyzer", "type": "excel_workbook", "topic": "Whether a rental deal covers its costs.",
                 "audience": "small landlords", "price": 24}
    assert dd.parse(DECLINE)["declined"] is True


def test_parse_rejects_contract_violations():
    assert dd.parse("nothing useful") is None
    assert dd.parse(GOOD.replace("excel_workbook", "video_course")) is None, "type outside the allowed list"
    assert dd.parse(GOOD.replace("$24", "$99")) is None, "price outside 9-49"
    assert dd.parse(GOOD.replace("$24", "$5")) is None
    assert dd.parse(GOOD.replace("Rental Property Cash Flow Analyzer", "abc")) is None


def test_duplicate_of_live_titles():
    live = ["Rental Property Deal Analyzer", "Debt Payoff Planner (Avalanche or Snowball)"]
    d = dd.duplicate_of("Rental Property Cash Flow Analyzer", live)
    assert d and d[0] == "Rental Property Deal Analyzer"
    assert dd.duplicate_of("Wedding Budget Vendor Planner", live) is None
    assert dd.duplicate_of("x", live) is None


def test_headline_detection_matches_the_hunter_rule():
    assert dd.looks_like_headline("Can I stop Google search results from showing my site?")
    assert dd.looks_like_headline("How do I price a project")
    assert not dd.looks_like_headline("However this works")
    assert not dd.looks_like_headline("Break-even calculator for a small shop")


def test_run_proposes_declines_dedupes_and_is_idempotent(tmp_path):
    replies = {"signal one": GOOD, "signal two": DECLINE, "signal three": GOOD.replace("Cash Flow Analyzer", "Deal Analyzer Pro"), "signal four": "garbage"}
    calls = []

    def gen(system, user):
        calls.append(user)
        sig = user.split("\n")[0].replace("Signal: ", "")
        if sig == "signal five":
            raise RuntimeError("network")
        return replies[sig]

    signals = [("hunter_headline", s) for s in ("signal one", "signal two", "signal three", "signal four", "signal five")]
    kw = dict(generate=gen, signals=signals, titles=["Rental Property Deal Analyzer"], now=NOW,
              candidates_path=tmp_path / "c.json", state_path=tmp_path / "s.json")
    r = dd.run(max_signals=10, **kw)
    assert r["processed"] == 4 and r["errors"] == 1
    assert r["proposed"] == 0 and r["declined"] == 1 and r["contract_failed"] == 1 and r["duplicate"] == 2, r
    kw["titles"] = []
    r2 = dd.run(max_signals=10, **kw)  # signals 1-4 are already processed; the errored one is retried
    assert r2["processed"] == 0 or r2["errors"] == 1
    # with an empty catalog a fresh signal is proposed and stored with its source and type
    kw2 = dict(kw, signals=[("sensing_trend", "signal six")], generate=lambda s, u: GOOD.replace("Rental Property Cash Flow Analyzer", "Wedding Vendor Payment Planner"))
    r3 = dd.run(max_signals=10, **kw2)
    cands = json.loads((tmp_path / "c.json").read_text(encoding="utf-8"))
    assert r3["proposed"] == 1 and cands[-1]["niche"] == "Wedding Vendor Payment Planner" and cands[-1]["source"] == "sensing_trend"
    assert cands[-1]["product_type"] == "excel_workbook" and cands[-1]["status"] == "candidate"


def test_max_signals_limits_the_cost_of_one_run(tmp_path):
    n = []
    signals = [("sensing_trend", f"s{i}") for i in range(30)]
    dd.run(max_signals=7, generate=lambda s, u: n.append(1) or DECLINE, signals=signals, titles=[], now=NOW,
           candidates_path=tmp_path / "c.json", state_path=tmp_path / "s.json")
    assert len(n) == 7


def test_daily_wrapper_runs_at_most_every_four_hours(tmp_path):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    import digital_discovery_daily as w
    calls = []
    fake = lambda: calls.append(1) or {"processed": 3, "proposed": 1, "declined": 2, "duplicate": 0, "contract_failed": 0, "errors": 0, "signals_waiting": 5, "candidates_total": 1}
    sp = tmp_path / "run.json"
    t0 = datetime(2026, 11, 6, 8, tzinfo=timezone.utc)
    a = w.run_once(t0, sp, runner=fake)
    assert a["action"] == "ran" and "1 proposed" in a["detail"]
    assert w.run_once(datetime(2026, 11, 6, 11, 59, tzinfo=timezone.utc), sp, runner=fake)["action"] == "none"
    assert w.run_once(datetime(2026, 11, 6, 12, 1, tzinfo=timezone.utc), sp, runner=fake)["action"] == "ran"
    assert len(calls) == 2


def test_quality_is_a_deterministic_buyer_relevance_check():
    assert dd.quality({"niche": "Escrow Review Window Calculator Workbook", "topic": "how long a client review window should be"}) == "strong"
    assert dd.quality({"niche": "Currency Transfer Cost Calculator", "topic": "cost of a CAD to USD transfer"}) == "strong"
    assert dd.quality({"niche": "FAANG Interview Prep Checklist Kit", "topic": "preparing for interviews"}) == "weak"
    assert dd.quality({"niche": "Professional Response Templates for Manager Accusations", "topic": "reply to a manager"}) == "weak"
    assert dd.quality({"niche": "Leadership Accountability Checklist", "topic": "team leader price of delays"}) == "weak", "personal workplace advice wins over a money word"
    assert dd.quality({"niche": "Pseudonym Playbook", "topic": "no money or operations decision here"}) == "weak"


def test_three_errors_in_a_row_abort_the_run_instead_of_burning_the_queue(tmp_path):
    n = []

    def boom(system, user):
        n.append(1)
        raise RuntimeError("429")
    r = dd.run(max_signals=10, generate=boom, signals=[("sensing_trend", f"s{i}") for i in range(10)], titles=[], now=NOW,
               candidates_path=tmp_path / "c.json", state_path=tmp_path / "s.json")
    assert len(n) == 3 and r["errors"] == 3 and r.get("aborted_after_errors") is True and r["processed"] == 0
    # errored signals are not recorded as processed: they are retried by the next run
    ok = dd.run(max_signals=10, generate=lambda s, u: DECLINE, signals=[("sensing_trend", f"s{i}") for i in range(10)], titles=[], now=NOW,
                candidates_path=tmp_path / "c.json", state_path=tmp_path / "s.json")
    assert ok["processed"] == 10

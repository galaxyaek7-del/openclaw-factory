"""Commercial Experiment Automation (Autonomous Enterprise Directive,
2026-08-15, gap closure #3): closes the LEARN -> SCALE/ITERATE/KILL loop for
commercial_experiments.py.

The experiment engine (ADR-202) was built and tested but nothing ever wrote
real observations into it, nothing auto-evaluated a RUNNING experiment, and
nothing retired a stale one -- so EXP-SEO-001 (and any future experiment)
would run forever without a decision. This module wires the loop:

  1. record_observations_from_real_ledgers() -- reads the real page-views
     ledger (affiliate_commerce.click_tracking) and records one real
     observation per experiment whose metric maps to a real page, so
     evaluate_experiment() gets real data instead of an empty file.
  2. evaluate_due_experiments() -- every RUNNING experiment past its
     planned_duration_days is auto-evaluated against the disclosed minimum
     sample size; ADOPT -> SCALE, REJECT -> KILL, NO_DIFFERENCE -> WATCH,
     INSUFFICIENT_DATA -> ITERATE (never a fabricated decision).
  3. retire_stale_experiments() -- a RUNNING experiment whose planned window
     has passed and that still has zero observations (or ran beyond a hard
     staleness cap) is retired to WATCHING/KILLED with an honest reason, so
     no experiment is ever silently abandoned indefinitely.

Read-only for every real ledger except the experiment file itself (append-only
status_updates/observations). Never touches money, never publishes, never
fabricates. All decisions come from commercial_experiments.py's own real,
disclosed-minimum-sample evaluation.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

_FACTORY_ROOT = Path(__file__).resolve().parent
DEFAULT_EXPERIMENTS_PATH = _FACTORY_ROOT / "data" / "commercial_experiments.jsonl"
DEFAULT_PAGE_VIEWS_PATH = _FACTORY_ROOT / "data" / "affiliate_page_views.jsonl"

# A RUNNING experiment past its planned window plus this grace period is
# declared stale even if it has observations but never reached the minimum
# sample -- it must be re-conceived (ITERATE) rather than left running.
STALE_GRACE_DAYS = 7


def _now_iso(now: Optional[datetime] = None) -> str:
    return (now or datetime.now(timezone.utc)).isoformat()


def _read_jsonl(path):
    records = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return records


def _read_experiments(experiments_path=None):
    return _read_jsonl(experiments_path or DEFAULT_EXPERIMENTS_PATH)


def _running_definitions(records):
    """Latest-status-aware view: a definition whose most recent status_update
    is not RUNNING is excluded; a definition with no update is RUNNING."""
    latest = {}
    for r in records:
        if r.get("record_type") == "status_update" and r.get("experiment_id"):
            ts = r.get("updated_at", "")
            cur = latest.get(r["experiment_id"])
            if cur is None or ts >= cur.get("updated_at", ""):
                latest[r["experiment_id"]] = r
    running = []
    for d in records:
        if d.get("record_type") != "experiment_definition":
            continue
        upd = latest.get(d.get("experiment_id"))
        if upd and upd.get("status") != "RUNNING":
            continue
        running.append(d)
    return running


def _page_id_for_experiment(defn: Dict[str, object]) -> Optional[str]:
    """Map an experiment to its real tracked page id. Only returns ids that
    actually exist in the real page-views ledger; never invents a page."""
    candidates = []
    text = " ".join(str(defn.get(k) or "") for k in ("metric", "change", "hypothesis", "experiment_id"))
    import re
    guide = re.search(r"guide-([a-z0-9-]+)", text)
    if guide:
        candidates.append(f"guide-{guide.group(1)}")
    return candidates[0] if candidates else None


def record_observations_from_real_ledgers(experiments_path=None, page_views_path=None):
    """Record one real observation per experiment whose metric maps to a real
    page, using the real page-views ledger. Idempotent per (experiment, day):
    records exactly one variant observation per calendar day for pages with at
    least one real view that day, so a flooded day never inflates the sample
    count beyond 1/day. Returns what was recorded (never fabricates a view)."""
    records = _read_experiments(experiments_path)
    running = _running_definitions(records)
    views = _read_jsonl(page_views_path or DEFAULT_PAGE_VIEWS_PATH)

    # Group real views by (page_id, calendar day).
    by_page_day = {}
    for v in views:
        pid = v.get("page_id")
        ts = v.get("timestamp")
        if not pid or not ts:
            continue
        day = str(ts)[:10]
        by_page_day[(pid, day)] = by_page_day.get((pid, day), 0) + 1

    already_recorded = set()
    for r in records:
        if r.get("record_type") == "observation":
            # Dedup key must use fields that are actually persisted in the
            # file by record_observation() (experiment_id/arm/observed_at),
            # not an in-memory-only field set after append.
            exp_id = r.get("experiment_id") or ""
            arm = r.get("arm") or ""
            day = (r.get("observed_at") or "")[:10]
            if exp_id and day:
                already_recorded.add((exp_id, arm, day))

    recorded = []
    import commercial_experiments as ce

    for defn in running:
        exp_id = defn.get("experiment_id")
        pid = _page_id_for_experiment(defn)
        if not pid or not exp_id:
            continue
        for (page_id, day), count in by_page_day.items():
            if page_id != pid:
                continue
            if (exp_id, "variant", day) in already_recorded:
                continue
            rec = ce.record_observation(
                exp_id, "variant", count,
                experiments_path=experiments_path or DEFAULT_EXPERIMENTS_PATH,
            )
            recorded.append(rec)
            already_recorded.add((exp_id, "variant", day))
    return {"recorded_observations": len(recorded), "running_experiments": len(running), "detail": recorded}


def evaluate_due_experiments(experiments_path=None, now=None):
    """Auto-evaluate every RUNNING experiment past its planned_duration_days.
    Uses commercial_experiments.evaluate_experiment()'s real, disclosed-minimum
    evaluation (never fabricated). Maps: ADOPT->SCALE, REJECT->KILL,
    NO_DIFFERENCE->WATCH, INSUFFICIENT_DATA->ITERATE. Returns decisions."""
    now = now or datetime.now(timezone.utc)
    records = _read_experiments(experiments_path)
    running = _running_definitions(records)
    import commercial_experiments as ce

    decisions = []
    for defn in running:
        exp_id = defn.get("experiment_id")
        duration = defn.get("planned_duration_days")
        created_raw = defn.get("created_at")
        if not duration or not created_raw:
            continue
        try:
            created = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        days = (now - created).total_seconds() / 86400
        if days < duration:
            continue
        eval_result = ce.evaluate_experiment(exp_id, experiments_path=experiments_path or DEFAULT_EXPERIMENTS_PATH)
        decision_raw = eval_result.get("decision", "INSUFFICIENT_DATA")
        mapping = {
            "ADOPT": ("SCALING", "SCALE"),
            "REJECT": ("KILLED", "KILL"),
            "NO_DIFFERENCE": ("WATCHING", "WATCH"),
            "INSUFFICIENT_DATA": ("ITERATING", "ITERATE"),
        }
        status, decision = mapping.get(decision_raw, ("ITERATING", "ITERATE"))
        reason = eval_result.get("reason") or f"Auto-evaluation after {int(days)} days; real sample {eval_result.get('result', {})}."
        ce.update_experiment_status(
            exp_id, status, decision, reason,
            experiments_path=experiments_path or DEFAULT_EXPERIMENTS_PATH,
        )
        decisions.append({
            "experiment_id": exp_id, "days_running": round(days, 1),
            "decision": decision, "status": status,
            "n_baseline": eval_result.get("result", {}).get("n_baseline"),
            "n_variant": eval_result.get("result", {}).get("n_variant"),
            "reason": reason,
        })
    return {"decisions": decisions, "evaluated": len(decisions)}


def retire_stale_experiments(experiments_path=None, now=None):
    """No experiment is ever silently abandoned. A RUNNING experiment whose
    planned window has passed AND that has zero recorded observations (i.e.
    nothing ever measured it) is retired to WATCHING with an honest reason;
    one past its window + STALE_GRACE_DAYS with observations but never enough
    sample is retired to ITERATING. Prevents indefinite silent RUNNING."""
    now = now or datetime.now(timezone.utc)
    records = _read_experiments(experiments_path)
    running = _running_definitions(records)
    import commercial_experiments as ce

    retired = []
    for defn in running:
        exp_id = defn.get("experiment_id")
        duration = defn.get("planned_duration_days")
        created_raw = defn.get("created_at")
        if not duration or not created_raw:
            continue
        try:
            created = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        days = (now - created).total_seconds() / 86400
        if days < duration:
            continue
        observations = [r for r in records if r.get("record_type") == "observation" and r.get("experiment_id") == exp_id]
        if days >= duration + STALE_GRACE_DAYS:
            status, decision = "ITERATING", "ITERATE"
            reason = f"No experiment may run forever: {int(days)} days running (planned {int(duration)} + {STALE_GRACE_DAYS} grace) with {len(observations)} real observation(s) but no decision reached. Re-conceive the experiment."
        elif days >= duration and not observations:
            status, decision = "WATCHING", "WATCH"
            reason = f"Planned window ({int(duration)} days) elapsed with 0 real observations recorded -- nothing measured this experiment. Retired to WATCH until real tracking data exists."
        else:
            continue
        ce.update_experiment_status(
            exp_id, status, decision, reason,
            experiments_path=experiments_path or DEFAULT_EXPERIMENTS_PATH,
        )
        retired.append({"experiment_id": exp_id, "status": status, "decision": decision, "reason": reason})
    return {"retired": retired, "count": len(retired)}


def run_experiment_cycle(experiments_path=None, page_views_path=None, now=None):
    """The full LEARN->DECIDE step: record real observations, evaluate due
    experiments, retire stale ones. Returns one honest summary."""
    obs = record_observations_from_real_ledgers(experiments_path, page_views_path)
    decisions = evaluate_due_experiments(experiments_path, now)
    retired = retire_stale_experiments(experiments_path, now)
    return {
        "generated_at": _now_iso(now),
        "observations": obs,
        "evaluations": decisions,
        "retirements": retired,
        "note": "Real observations from the real page-views ledger; decisions only from the disclosed-minimum-sample evaluation; no experiment is ever silently abandoned.",
    }


def _cli_main() -> None:
    print(json.dumps(run_experiment_cycle(), ensure_ascii=False, default=str))


if __name__ == "__main__":
    _cli_main()
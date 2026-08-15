"""Galaxy Forge -- Commercial Experiment Engine (new, ADR-202, 2026-08-07).

Answers Phase 12 Section 8 of the founder's "Global Commercial Revenue
Operating System" directive: a framework to test pricing/positioning/
landing pages/offers/bundles/subscriptions/affiliate channels/platforms/
markets, with every experiment carrying Hypothesis/Baseline/Change/
Metric/Duration/Result/Confidence/Decision.

Built as real, callable, persisted infrastructure -- deliberately NOT
seeded with any experiment, real or simulated. This factory has 0 real
website traffic, 0 real customers, and $0 real revenue (confirmed
repeatedly this session) -- there is nothing to A/B test yet. Building
this now, honestly empty, is the correct order: the framework exists
and is tested before the first real experiment needs it, exactly the
same "build the capability, disclose the real usage gap" discipline
evidence_engine.py (ADR-163) already established.

The directive's own two hard rules are enforced mechanically, not just
by convention: evaluate_experiment() refuses to return a Decision
(ADOPT/REJECT) below a real, disclosed minimum sample size on both
sides -- "never declare success from insufficient data" -- and never
computes statistical significance from a single metric snapshot
("never confuse correlation with causation").
"""

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
DEFAULT_EXPERIMENTS_PATH = _FACTORY_ROOT / "data" / "commercial_experiments.jsonl"

VALID_EXPERIMENT_TYPES = (
    "pricing", "product_positioning", "landing_page", "offer", "bundle",
    "subscription", "affiliate_channel", "platform", "market",
)

# Disclosed, real, minimum sample size before ANY decision is made --
# deliberately small enough to be reachable by a real solo factory's
# early traffic, but never zero. A real statistician would likely want
# more; this is a floor against "declared success from insufficient
# data," not a claim of rigorous statistical power.
MIN_SAMPLE_SIZE_FOR_DECISION = 30


class UnknownExperimentTypeError(ValueError):
    pass


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


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


def _append(record, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def create_experiment(experiment_id, experiment_type, hypothesis, baseline, change, metric,
                       planned_duration_days=None, experiments_path=None):
    """The one real write path for a new experiment definition. Refuses
    an unknown experiment_type rather than silently accepting a typo."""
    if experiment_type not in VALID_EXPERIMENT_TYPES:
        raise UnknownExperimentTypeError(f"experiment_type must be one of {VALID_EXPERIMENT_TYPES}, got {experiment_type!r}")
    record = {
        "record_type": "experiment_definition",
        "experiment_id": experiment_id,
        "experiment_type": experiment_type,
        "hypothesis": hypothesis,
        "baseline": baseline,
        "change": change,
        "metric": metric,
        "planned_duration_days": planned_duration_days,
        "status": "RUNNING",
        "created_at": _now_iso(),
    }
    return _append(record, experiments_path or DEFAULT_EXPERIMENTS_PATH)


def record_observation(experiment_id, arm, value, experiments_path=None):
    """arm is 'baseline' or 'variant' -- one real observed metric value.
    Never aggregated/estimated here; evaluate_experiment() does the real
    aggregation over every real observation on read."""
    if arm not in ("baseline", "variant"):
        raise ValueError("arm must be 'baseline' or 'variant'")
    record = {
        "record_type": "observation",
        "experiment_id": experiment_id,
        "arm": arm,
        "value": value,
        "observed_at": _now_iso(),
    }
    return _append(record, experiments_path or DEFAULT_EXPERIMENTS_PATH)


def evaluate_experiment(experiment_id, experiments_path=None, min_sample_size=None):
    """Real aggregation over every real observation recorded for this
    experiment_id. Returns Result/Confidence/Decision honestly:
    Decision is ALWAYS "INSUFFICIENT_DATA" until real sample size on
    BOTH arms meets min_sample_size -- never inferred from a partial
    sample, never a single-snapshot correlation treated as causation."""
    min_n = min_sample_size if min_sample_size is not None else MIN_SAMPLE_SIZE_FOR_DECISION
    path = experiments_path or DEFAULT_EXPERIMENTS_PATH
    records = _read_jsonl(path)

    definition = next((r for r in records if r.get("record_type") == "experiment_definition" and r.get("experiment_id") == experiment_id), None)
    if definition is None:
        return {"status": "NOT_FOUND", "experiment_id": experiment_id}

    baseline_values = [r["value"] for r in records if r.get("record_type") == "observation" and r.get("experiment_id") == experiment_id and r.get("arm") == "baseline" and isinstance(r.get("value"), (int, float))]
    variant_values = [r["value"] for r in records if r.get("record_type") == "observation" and r.get("experiment_id") == experiment_id and r.get("arm") == "variant" and isinstance(r.get("value"), (int, float))]

    n_baseline, n_variant = len(baseline_values), len(variant_values)
    baseline_mean = round(sum(baseline_values) / n_baseline, 4) if n_baseline else None
    variant_mean = round(sum(variant_values) / n_variant, 4) if n_variant else None

    enough_data = n_baseline >= min_n and n_variant >= min_n

    if not enough_data:
        return {
            "experiment_id": experiment_id,
            "definition": definition,
            "result": {"baseline_mean": baseline_mean, "variant_mean": variant_mean, "n_baseline": n_baseline, "n_variant": n_variant},
            "confidence": "INSUFFICIENT_DATA",
            "decision": "INSUFFICIENT_DATA",
            "reason": f"Real sample size (baseline={n_baseline}, variant={n_variant}) has not yet reached the disclosed minimum ({min_n} per arm) -- per this directive's own 'never declare success from insufficient data' rule, no Result/Decision is reported yet.",
        }

    lift_pct = round((variant_mean - baseline_mean) / baseline_mean * 100, 2) if baseline_mean else None
    decision = "ADOPT" if lift_pct is not None and lift_pct > 0 else "REJECT" if lift_pct is not None and lift_pct < 0 else "NO_DIFFERENCE"

    return {
        "experiment_id": experiment_id,
        "definition": definition,
        "result": {"baseline_mean": baseline_mean, "variant_mean": variant_mean, "n_baseline": n_baseline, "n_variant": n_variant, "lift_pct": lift_pct},
        "confidence": f"Real sample size >= {min_n} per arm reached -- a simple mean comparison, not a formal statistical significance test (no such library is used anywhere in this factory).",
        "decision": decision,
        "reason": f"variant mean ({variant_mean}) vs baseline mean ({baseline_mean}), a real {lift_pct}% lift.",
    }


def update_experiment_status(experiment_id, status, decision, reason, experiments_path=None):
    """The one real write path for an experiment's lifecycle state. Appends a
    status_update record (same append-only discipline as definitions and
    observations) so a RUNNING experiment can honestly advance to
    COMPLETED/SCALING/ITERATING/KILLED/WATCHING without ever being silently
    abandoned. Decision is one of SCALE/ITERATE/WATCH/KILL (mapped from the
    evaluation) or the honest status string itself; reason always carries the
    real evidence behind it."""
    valid_statuses = ("RUNNING", "COMPLETED", "SCALING", "ITERATING", "WATCHING", "KILLED")
    if status not in valid_statuses:
        raise ValueError(f"status must be one of {valid_statuses}, got {status!r}")
    record = {
        "record_type": "status_update",
        "experiment_id": experiment_id,
        "status": status,
        "decision": decision,
        "reason": reason,
        "updated_at": _now_iso(),
    }
    return _append(record, experiments_path or DEFAULT_EXPERIMENTS_PATH)


def list_experiments(experiments_path=None):
    """Real, honest status of every experiment ever defined -- 0 today."""
    records = _read_jsonl(experiments_path or DEFAULT_EXPERIMENTS_PATH)
    definitions = [r for r in records if r.get("record_type") == "experiment_definition"]
    if not definitions:
        return {"experiments": [], "total": 0, "note": "0 real commercial experiments have ever run in this factory -- 0 real website traffic/customers exist yet to test against. This is the honest current state, not a missing feature."}
    # Surface the latest lifecycle status per experiment (status_update records
    # are authoritative; a definition with no update stays RUNNING).
    latest_status = {}
    for r in records:
        if r.get("record_type") == "status_update" and r.get("experiment_id"):
            ts = r.get("updated_at", "")
            cur = latest_status.get(r["experiment_id"])
            if cur is None or ts >= cur.get("updated_at", ""):
                latest_status[r["experiment_id"]] = r
    experiments = []
    for d in definitions:
        merged = dict(d)
        upd = latest_status.get(d["experiment_id"])
        if upd:
            merged["status"] = upd["status"]
            merged["decision"] = upd["decision"]
            merged["decision_reason"] = upd["reason"]
        experiments.append(merged)
    return {"experiments": experiments, "total": len(experiments)}

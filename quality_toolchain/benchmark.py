# -*- coding: utf-8 -*-
"""Controlled benchmark framework for the quality toolchain (v2: large corpus).

Purpose: satisfy the founder directive's benchmark-before-value rule on a
larger, more diverse controlled corpus — multiple writing styles, short/long,
clean/weak, near-duplicate, and edge cases — and to measure detection
consistency, false positives, false negatives, threshold sensitivity, runtime,
failure behavior, and reproducibility.

GROUND-TRUTH LIMITATION (per directive rule 7): the ground-truth labels in
corpus_v2 are the author's deterministic *judgment* applied while building a
synthetic corpus — DERIVED/ESTIMATED, not independently OBSERVED. Real Arabic
product text with independently-verified defect labels does not exist in this
factory today (zero real published books, config/reality.json). All benchmark
output therefore labels this limitation explicitly. No ground truth is
invented; where a label is a judgment it is disclosed as such.

Backward compatibility: the V1 function names (run_readability_benchmark,
run_distinctiveness_benchmark, summarize, run_full_benchmark) are re-exported
so the existing 23 unit tests stay green. The v2 functions below are the
authoritative measurement for the newer report.
"""

import json
import os
import time

# --- V1 backward-compatible re-exports (existing unit tests rely on these) ---
from .benchmark_v1 import (  # noqa: F401
    run_readability_benchmark as run_readability_benchmark,
    run_distinctiveness_benchmark as run_distinctiveness_benchmark,
    summarize as summarize,
    run_full_benchmark as run_full_benchmark,
    ARABIC_READABILITY_CASES as _V1_READ,
    DISTINCTIVENESS_CASES as _V1_DIST,
)
from . import corpus_v2 as C2


# ---------------------------------------------------------------------------
# v2 READABILITY measurement over the large corpus
# ---------------------------------------------------------------------------

def _classify_readability_verdict(v):
    """Map an adapter result + ground truth to a defect/pass verdict for
    numeric scoring. Returns (tool_says_clean, ground_truth_category)."""
    passed = bool(v["passed"])
    return passed


def _readability_one_case(case, min_osman_score):
    from quality_toolchain.adapters.textstat_osman import check_readability
    v = check_readability(case["text"], min_osman_score=min_osman_score)
    return {
        "id": case["id"],
        "style": case.get("style"),
        "length": case.get("length"),
        "ground_truth": case["ground_truth"],
        "tool_pass": bool(v["passed"]),
        "status": v["status"],
        "score": v.get("score"),
        "threshold_info": v.get("threshold_info"),
    }


def run_readability_benchmark_v2(min_osman_score=55.0):
    """Run readability adapter over the large v2 corpus (all labels)."""
    results = {}
    for case in C2.ARABIC_READABILITY_CASES_V2:
        results[case["id"]] = _readability_one_case(case, min_osman_score)
    return {"spec": {"min_osman_score": min_osman_score,
                     "cases": len(C2.ARABIC_READABILITY_CASES_V2)},
            "results": results}


def _readability_confusion(results, dense_keys=("dense",)):
    """TP/FP/FN/TN counting *only* over cases with an affirmatively 'dense'
    ground truth (clean) vs cases meaningfully 'natural' (non-dense).
    Edge/empty/non-arabic/unknown labels are excluded and reported separately,
    because we refuse to invent ground truth for them (directive rule 7)."""
    conf = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    skipped = []
    for r in results.values():
        gt = r["ground_truth"]
        if gt in dense_keys:
            flagged = not r["tool_pass"]
            if flagged:
                conf["tp"] += 1
            else:
                conf["fn"] += 1
        elif gt in ("natural",) or (gt == "mixed" and "natural" in dense_keys):
            flagged = not r["tool_pass"]
            if flagged:
                conf["fp"] += 1
            else:
                conf["tn"] += 1
        else:
            skipped.append(r["id"])
    prec = conf["tp"] / (conf["tp"] + conf["fp"]) if (conf["tp"] + conf["fp"]) else None
    rec = conf["tp"] / (conf["tp"] + conf["fn"]) if (conf["tp"] + conf["fn"]) else None
    f1 = (2 * prec * rec / (prec + rec)) if (prec is not None and rec and (prec + rec)) else None
    return {
        "confusion": conf,
        "precision": round(prec, 3) if prec is not None else None,
        "recall": round(rec, 3) if rec is not None else None,
        "f1": round(f1, 3) if f1 is not None else None,
        "excluded_reason_labels": {"no_label_judgment": sorted(skipped)},
        "excluded_count": len(skipped),
    }


# ---------------------------------------------------------------------------
# v2 DISTINCTIVENESS measurement over the large corpus
# ---------------------------------------------------------------------------

def _refs():
    return [{"label": "reference-pack", "text": C2.DISTINCTIVENESS_REFERENCE}]


def run_distinctiveness_benchmark_v2(max_overlap=0.5, max_lcs=0.25,
                                     max_contamination=0.5):
    from quality_toolchain.adapters.distinctiveness import check_distinctiveness
    results = {}
    refs = _refs()
    for case in C2.DISTINCTIVENESS_CASES_V2:
        v = check_distinctiveness(case["text"], references=refs,
                                  max_overlap=max_overlap, max_lcs_ratio=max_lcs,
                                  max_contamination=max_contamination)
        results[case["id"]] = {
            "id": case["id"],
            "style": case.get("style"),
            "length": case.get("length"),
            "ground_truth": case["ground_truth"],
            "tool_pass": bool(v["passed"]),
            "status": v["status"],
            "verdict": v.get("verdict"),
            "max_overlap": v.get("max_overlap"),
            "max_lcs_ratio": v.get("max_lcs_ratio"),
            "max_contamination": v.get("max_contamination"),
            # FOUNDER-APPROVED roles: contamination PRIMARY, jaccard secondary.
            "primary_contamination_passed": bool(v.get("primary_signal", {}).get("passed")),
            "secondary_jaccard_passed": bool(v.get("secondary_signal", {}).get("passed")),
            "threshold_info": v.get("threshold_info"),
        }
    return {"spec": {"max_overlap": max_overlap, "max_lcs": max_lcs,
                     "max_contamination": max_contamination,
                     "cases": len(C2.DISTINCTIVENESS_CASES_V2)},
            "results": results}


def _distinctiveness_confusion(results, pass_field="tool_pass"):
    """Scoring over copy/distinctive ground-truth cases. `pass_field` selects
    which result field denotes 'clean/distinctive' — default the adapter's
    `tool_pass`; a contamination threshold alternative is scored via
    _contamination_confusion below (never auto-applied)."""
    conf = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    skipped = []
    for r in results.values():
        gt = r["ground_truth"]
        if gt == "copy":
            if not r[pass_field]:
                conf["tp"] += 1
            else:
                conf["fn"] += 1
        elif gt == "distinctive":
            if not r[pass_field]:
                conf["fp"] += 1
            else:
                conf["tn"] += 1
        else:
            skipped.append(r["id"])
    prec = conf["tp"] / (conf["tp"] + conf["fp"]) if (conf["tp"] + conf["fp"]) else None
    rec = conf["tp"] / (conf["tp"] + conf["fn"]) if (conf["tp"] + conf["fn"]) else None
    f1 = (2 * prec * rec / (prec + rec)) if (prec is not None and rec and (prec + rec)) else None
    return {
        "confusion": conf,
        "precision": round(prec, 3) if prec is not None else None,
        "recall": round(rec, 3) if rec is not None else None,
        "f1": round(f1, 3) if f1 is not None else None,
        "excluded_reason_labels": {"no_label_judgment": sorted(skipped)},
        "excluded_count": len(skipped),
    }


def contamination_alternative_sweep(thresholds=(0.3, 0.4, 0.5, 0.6, 0.7)):
    """DERIVED, never-automatically-applied alternative: score what a gate
    based purely on `max_contamination` (recognizing a long near-duplicate
    that the Jaccard-diluted signal misses) would achieve at each threshold.
    This is a *computed alternative* for founder review, NOT a behavior
    change: the current adapter `passed` still uses max_overlap/max_lcs."""
    out = {}
    for thr in thresholds:
        run = run_distinctiveness_benchmark_v2()
        # predicted 'distinctive' (clean) iff max_contamination <= thr
        for r in run["results"].values():
            r["tool_pass"] = (r.get("max_contamination") or 0.0) <= thr
        m = _distinctiveness_confusion(run["results"], pass_field="tool_pass")
        missed = [r["id"] for r in run["results"].values()
                  if r["ground_truth"] == "copy" and r["tool_pass"]]
        fps = [r["id"] for r in run["results"].values()
               if r["ground_truth"] == "distinctive" and not r["tool_pass"]]
        out[str(thr)] = {"precision": m["precision"], "recall": m["recall"],
                         "f1": m["f1"], "confusion": m["confusion"],
                         "copy_missed": missed,
                         "distinctive_flagellated": fps}
    return out
    conf = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    skipped = []
    for r in results.values():
        gt = r["ground_truth"]
        if gt == "copy":
            if not r["tool_pass"]:
                conf["tp"] += 1
            else:
                conf["fn"] += 1
        elif gt == "distinctive":
            if not r["tool_pass"]:
                conf["fp"] += 1
            else:
                conf["tn"] += 1
        else:
            skipped.append(r["id"])
    prec = conf["tp"] / (conf["tp"] + conf["fp"]) if (conf["tp"] + conf["fp"]) else None
    rec = conf["tp"] / (conf["tp"] + conf["fn"]) if (conf["tp"] + conf["fn"]) else None
    f1 = (2 * prec * rec / (prec + rec)) if (prec is not None and rec and (prec + rec)) else None
    return {
        "confusion": conf,
        "precision": round(prec, 3) if prec is not None else None,
        "recall": round(rec, 3) if rec is not None else None,
        "f1": round(f1, 3) if f1 is not None else None,
        "excluded_reason_labels": {"no_label_judgment": sorted(skipped)},
        "excluded_count": len(skipped),
    }


# ---------------------------------------------------------------------------
# Threshold sensitivity (stability of clean/dense and copy/distinctive split)
# ---------------------------------------------------------------------------

def readability_threshold_sweep(thresholds=(35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85)):
    """Evaluate F1-sensitive metrics + per-case pass/fail at each threshold of
    the OSMAN score, to locate a stable decision region. Only labeled
    (dense/natural) cases are scored; edge labels are reported per threshold
    as 'other' but never scored."""
    out = {}
    for thr in thresholds:
        run = run_readability_benchmark_v2(min_osman_score=thr)
        m = _readability_confusion(run["results"])
        # track which dense cases got missed / natural cases got flagged at
        # this threshold (helps read threshold sensitivity)
        misses = [r["id"] for r in run["results"].values()
                  if r["ground_truth"] == "dense" and r["tool_pass"]]
        fps = [r["id"] for r in run["results"].values()
               if r["ground_truth"] == "natural" and not r["tool_pass"]]
        out[str(thr)] = {
            "precision": m["precision"],
            "recall": m["recall"],
            "f1": m["f1"],
            "confusion": m["confusion"],
            "dense_missed": misses,
            "natural_flagellated": fps,
        }
    return out


def distinctiveness_threshold_sweep(overlaps=(0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8),
                                    lcs=(0.1, 0.15, 0.2, 0.25, 0.3, 0.4)):
    """Sweep over the two distinctiveness guards. Reports F1 + which copy
    cases slip and which distinctive cases are falsely flagged."""
    out = {}
    for ov in overlaps:
        for lc in lcs:
            run = run_distinctiveness_benchmark_v2(max_overlap=ov, max_lcs=lc)
            m = _distinctiveness_confusion(run["results"])
            missed = [r["id"] for r in run["results"].values()
                      if r["ground_truth"] == "copy" and r["tool_pass"]]
            fps = [r["id"] for r in run["results"].values()
                   if r["ground_truth"] == "distinctive" and not r["tool_pass"]]
            out[f"{ov}/{lc}"] = {
                "precision": m["precision"],
                "recall": m["recall"],
                "f1": m["f1"],
                "confusion": m["confusion"],
                "copy_missed": missed,
                "distinctive_flagellated": fps,
            }
    return out


# ---------------------------------------------------------------------------
# Runtime measurement
# ---------------------------------------------------------------------------

def measure_runtime(corpus_fn, runs=5):
    """Median wall-clock over `runs` invocations of a benchmark function."""
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        corpus_fn()
        times.append(time.perf_counter() - t0)
    times.sort()
    n = len(times)
    median = times[n // 2] if n else 0.0
    return {"runs": runs, "median_s": round(median, 4),
            "min_s": round(times[0], 4) if times else None,
            "max_s": round(times[-1], 4) if times else None,
            "all_s": [round(t, 4) for t in times]}


# ---------------------------------------------------------------------------
# Reproducibility (determinism) — the adapter output must be byte-repeatable
# ---------------------------------------------------------------------------

def reproducibility_check(fn, runs=3):
    """Verify a corpus function yields identical tool_pass + score over
    repeated runs. Distinctiveness uses a seeded internal; equality asserted
    on serialized results."""
    first = None
    identical = True
    for i in range(runs):
        snap = json.dumps(fn(), ensure_ascii=False, sort_keys=True)
        if first is None:
            first = snap
        elif snap != first:
            identical = False
    return {"runs": runs, "reproducible": identical}


# ---------------------------------------------------------------------------
# Failure behavior
# ---------------------------------------------------------------------------

def failure_behavior_checks():
    """Prove fail-closed: a disabled tool and an absent capability must not
    yield a PASS. Uses runner internals to construct deterministic cases."""
    from quality_toolchain import runner as R
    probes = {}

    # 1. Unknown tool id -> fail-closed (registry treats it as disabled)
    res_unknown = R._run_tool("no_such_tool", {"text": "أي"})
    probes["unknown_tool"] = {"passed": bool(res_unknown.get("passed")),
                              "status": res_unknown.get("status"),
                              "expect_no_pass": not res_unknown.get("passed")}

    # 2. Distinctiveness on empty reference list (no comparison)
    from quality_toolchain.adapters.distinctiveness import check_distinctiveness
    v_empty = check_distinctiveness("", references=[])
    probes["empty_refs_no_pass_or_explicitly_noted"] = {
        "passed": bool(v_empty["passed"]),
        "status": v_empty["status"],
        "threshold_info": v_empty.get("threshold_info"),
    }
    return probes


def _edge_case_report(read_results, dist_results):
    """Surface how edge/empty/non-arabic cases were handled, WITHOUT scoring
    them (rule 7: no invented ground truth). Reports the observed status and
    pass/not-applicable behavior credibly."""
    out = {"readability_edge_cases": {}, "distinctiveness_edge_cases": {}}
    for r in read_results.values():
        if r["ground_truth"] in ("no_arabic", "empty"):
            out["readability_edge_cases"][r["id"]] = {
                "ground_truth": r["ground_truth"],
                "status": r["status"],
                "tool_pass": r["tool_pass"],
                "product_aware_no_arabic": (r["status"] == "not_applicable"),
            }
    for r in dist_results.values():
        if r["ground_truth"] in ("no_arabic", "empty"):
            out["distinctiveness_edge_cases"][r["id"]] = {
                "ground_truth": r["ground_truth"],
                "status": r["status"],
                "tool_pass": r["tool_pass"],
            }
    return out


# ---------------------------------------------------------------------------
# Master v2 benchmark
# ---------------------------------------------------------------------------

def run_full_benchmark_v2(record_evidence=True, out_dir=None):
    out_dir = out_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence")
    os.makedirs(out_dir, exist_ok=True)

    read_run = run_readability_benchmark_v2(min_osman_score=55.0)
    dist_run = run_distinctiveness_benchmark_v2()
    read_metrics = _readability_confusion(read_run["results"])
    dist_metrics = _distinctiveness_confusion(dist_run["results"])
    sweep_read = readability_threshold_sweep()
    sweep_dist = distinctiveness_threshold_sweep()
    contam_alt = contamination_alternative_sweep()
    edge_report = _edge_case_report(read_run["results"], dist_run["results"])
    rt_read_ms = measure_runtime(
        lambda: run_readability_benchmark_v2())
    rt_dist_ms = measure_runtime(
        lambda: run_distinctiveness_benchmark_v2())
    reprod_read = reproducibility_check(lambda: run_readability_benchmark_v2())
    reprod_dist = reproducibility_check(lambda: run_distinctiveness_benchmark_v2())
    fail_checks = failure_behavior_checks()

    report = {
        "benchmark": "FACTORY_QUALITY_TOOLCHAIN_BENCHMARK_V2_2026-09-02",
        "version": "2.0.0",
        "evidence_classification": "OBSERVED",
        "ground_truth_limitation": (
            "Labels are author's deterministic judgment on a synthetic corpus "
            "(DERIVED/ESTIMATED), not independently OBSERVED ground truth. "
            "Edge/empty/non-arabic cases carry no scored label and are excluded "
            "from confusion metrics; they are listed separately."),
        "metrics": {
            "readability_v2": {"report": read_run, "metrics": read_metrics},
            "distinctiveness_v2": {"report": dist_run, "metrics": dist_metrics},
            "readability_threshold_sensitivity": sweep_read,
            "distinctiveness_threshold_sensitivity": sweep_dist,
            "contamination_alternative_(derived)": contam_alt,
            "edge_case_report": edge_report,
            "runtime": {
                "readability_corpus_median_s": rt_read_ms["median_s"],
                "distinctiveness_corpus_median_s": rt_dist_ms["median_s"],
                "readability_detail": rt_read_ms,
                "distinctiveness_detail": rt_dist_ms,
            },
            "reproducibility": {
                "readability_reproducible": reprod_read["reproducible"],
                "distinctiveness_reproducible": reprod_dist["reproducible"],
            },
            "failure_behavior": fail_checks,
        },
    }

    report_path = os.path.join(out_dir, "benchmark_report_v2.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    if record_evidence:
        from quality_toolchain import evidence as ev
        ev.record_tool_invocation({
            "tool": "quality-toolchain-benchmark-v2",
            "version": "2.0.0",
            "product": "benchmark-corpus-arabic-v2-2026-09-02",
            "input_class": "large_controlled_readability_and_distinctiveness_corpus",
            "result": {
                "readability_metrics": read_metrics,
                "distinctiveness_metrics": dist_metrics,
                "runtime_s": {"readability": rt_read_ms["median_s"],
                              "distinctiveness": rt_dist_ms["median_s"]},
                "reproducible": {"readability": reprod_read["reproducible"],
                                 "distinctiveness": reprod_dist["reproducible"]},
            },
            "timestamp": None,
            "status": "ok",
            "evidence_classification": "OBSERVED",
            "failure": None,
        })
    return report


if __name__ == "__main__":
    rep = run_full_benchmark_v2()
    print(json.dumps(rep["metrics"]["readability_v2"]["metrics"],
                     ensure_ascii=False, indent=2))
    print(json.dumps(rep["metrics"]["distinctiveness_v2"]["metrics"],
                     ensure_ascii=False, indent=2))
    print("runtime:", rep["metrics"]["runtime"])
    print("reproducible:", rep["metrics"]["reproducibility"])
    print("failure:", rep["metrics"]["failure_behavior"])
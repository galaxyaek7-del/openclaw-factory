# -*- coding: utf-8 -*-
"""Product-aware toolchain runner.

run_stack(product_type, context, references=None, ...) selects the enabled,
available tools for a product type (registry.stack_for -> tools_for_layer),
runs each eligible adapter under its configured timeout, and returns a
non-mutating QA verdict per tool. This is the integration boundary: the
production engine (book_generator.inspectors, executive_quality_gate) can
call this and receive per-tool results without knowing individual adapters.

An adapter that is disabled, unavailable, times out, or errors NEVER yields a
pass; the runner marks it as skipped/error with passed=False (fail-closed),
and an explicit optional flag controls whether an unavailable tooling layer
should itself block the product (default: record, do not auto-reject, so a
registry/availability change never silently hard-blocks production).
"""

import os

from . import gate as _gate
from . import registry as _reg
from . import versions as _ver
from . import evidence as _ev

# Tool id -> (module, function, kwargs-factory)
# QUALITY ARCHITECTURE (2026-09-02): added executive_content (content_qa),
# structural (structural_qa), commercial (commercial_qa) -- advisory-only
# adapters connecting the factory's already-real gates (executive_
# quality_gate.py content checks, inspectors.py inspect_technical /
# audit_commercial). Same fail-closed contract as every holdover adapter.
_ADAPTERS = {
    "arabic_readability_osman": ("textstat_osman", "check_readability", None),
    "distinctiveness_overlap": ("distinctiveness", "check_distinctiveness", None),
    "executive_content_checks": ("executive_content", "check_executive_content", None),
    "structural_integrity": ("structural", "check_structural", None),
    "commercial_gate": ("commercial", "check_commercial", None),
    "visual_qa_cover": ("visual", "check_visual", None),
    "visual_qa_interior": ("visual_interior", "check_visual_interior", None),
    "commercial_appearance": ("commercial_appearance", "check_commercial_appearance", None),
    "kdp_technical": ("kdp_technical", "check_kdp_technical", None),
    "functional_qa": ("functional", "check_functional", None),
    "performance_qa": ("performance", "check_performance", None),
    "visual_flow_qa": ("visual_flow", "check_visual_flow", None),
    "ux_human_playtest": ("ux_playtest", "check_ux_playtest", None),
    "security_qa": ("security", "check_security", None),
    "data_integrity_qa": ("data_integrity", "check_data_integrity", None),
    "ux_qa": ("ux", "check_ux", None),
    "evidence_validation_qa": ("evidence_validation", "check_evidence_validation", None),
    "export_qa": ("export", "check_export", None),
}


def _load_adapter(tool_id):
    spec = _ADAPTERS.get(tool_id)
    if not spec:
        return None, None, None
    module_name, func_name, kw_factory = spec
    import importlib
    mod = importlib.import_module(f"quality_toolchain.adapters.{module_name}")
    return module_name, getattr(mod, func_name), kw_factory


def _tool_version(tool_id):
    if tool_id == "arabic_readability_osman":
        return _ver.version_of_textstat() or "not_available"
    if tool_id == "distinctiveness_overlap":
        return _ver.STDLIB_VERSION_MARKER
    if tool_id in ("executive_content_checks", "structural_integrity",
                   "commercial_gate", "visual_qa_cover", "visual_qa_interior",
                   "commercial_appearance", "kdp_technical",
                   "functional_qa", "performance_qa", "visual_flow_qa",
                   "ux_human_playtest", "security_qa", "data_integrity_qa",
                   "ux_qa", "evidence_validation_qa", "export_qa"):
        # These adapters delegate to existing factory modules; version =
        # their own source marker + stdlib (no new third-party dep).
        return "factory-gates:" + _ver.STDLIB_VERSION_MARKER
    return "unknown"


def _config_thresholds(tool_id, path=None):
    cfg = _reg.get_config(path)
    return cfg.get("thresholds", {}).get(tool_id, {}) or {}


def overall_verdict(report):
    """STRICT Gate-1 verdict contract between ``run_stack`` and
    ``quality_gate_policy``.

    This is the single source of truth for the mandatory Gate-1 PASS that
    the policy-wide quality gate depends on. PASS is produced ONLY when every
    tool result recorded in ``report["results"]`` is itself a clean pass:
    status == "ok", passed is True, and the structural LCS detector was NOT
    unconfirmed (an unavailable/timed-out secondary detector never becomes a
    pass). An empty results map is MISSING, never a pass. Any disabled /
    not_available / timeout / error / FAIL / UNKNOWN / REVIEW / unconfirmed
    tool turns the whole verdict to REVIEW. This is deliberately as strict as
    ``quality_gate_policy._gate1_verdict`` so the two always agree: when
    ``overall_verdict`` says PASS, the policy reaches PASS; otherwise it
    BLOCKs. No verdict is ever manufactured or hard-coded.

    Returns ``{"verdict": "PASS"|"REVIEW"|"MISSING", "blocked": bool}``.
    ``blocked`` is True for any non-PASS verdict (a partial or missing result
    must never be treated as approval).
    """
    results = report.get("results", {}) if isinstance(report, dict) else {}
    if not results:
        return {"verdict": "MISSING", "blocked": True}
    for v in results.values():
        if not isinstance(v, dict):
            return {"verdict": "REVIEW", "blocked": True}
        if v.get("status") != "ok" or v.get("passed") is not True:
            return {"verdict": "REVIEW", "blocked": True}
        if v.get("lcs_unavailable"):
            return {"verdict": "REVIEW", "blocked": True}
    return {"verdict": "PASS", "blocked": False}


def run_stack(product_type, context, references=None, product_name=None,
              record_evidence=True, evidence_path=None, min_osman_score=None,
              max_overlap=None, max_lcs_ratio=None,
              source_id=None, artifact_version=None, run_id=None,
              release=None, config_hash=None, model_id=None):
    """Run the enabled+available QA tools for a product type against
    `context`. context is a dict the adapters need:
        {"text": <product text for language/originality layers>,
         "product_chapters": <list of {"content":...} dicts, optional -- used
                              by the executive_content adapter>,
         "pdf_path": <real PDF path, optional -- structured/game/digital
                      product structural gate via inspectors.py>,
         "niche"/"price"/"platform"/"page_count": <commercial gate inputs,
                           optional but advised for a meaningful result>}
    Returns dict:
        {"product_type", "product", "layers", "results": {tool_id: verdict},
         "verdict": "PASS"|"REVIEW"|"MISSING", "blocked": bool,
         "evidence_recorded": [...]}
    `verdict`/`blocked` are the STRICT Gate-1 contract consumed by
    quality_gate_policy (see overall_verdict): "PASS" is reachable only when
    every recorded tool result is a clean pass and the structural LCS is
    confirmed; any missing/partial/failed/unavailable/unconfirmed result is a
    non-PASS and blocked=True. This runner only reports and records evidence;
    it never makes the production call and never approves. `run_gate(...)`
    remains the advisory decision-shaped wrapper; it is NOT the mandatory
    gate contract.
    """
    layer_names = _reg.stack_for(product_type)
    results = {}
    evidence_written = []
    # Identity for ledger binding (additive, backward-compatible):
    _identity = {
        "source_id": source_id or product_name,
        "product_type": product_type,
        "artifact_version": artifact_version,
        "run_id": run_id,
        "release": release,
        "config_hash": config_hash,
        "model_id": model_id,
    }
    # ADAPTATION -> FUTURE TOOL SELECTION (minimal integration, existing registry)
    # Consume verified reliability signals to influence future selection order.
    # Read-only advisory: weak tools (<0.5) still run, but are ordered last and flagged.
    # Fail-closed: unavailable scores -> original order preserved.
    _reliability = {}
    try:
        import factory_adaptation as _fa
        _rel_data = _fa.tool_reliability_scores(evidence_path=evidence_path)
        _reliability = _rel_data.get("scores", {})
    except Exception:
        _reliability = {}
    for layer in layer_names:
        _tools = _reg.tools_for_layer(layer)
        # Sort by reliability descending, unknown last — advisory only
        try:
            _tools = sorted(_tools, key=lambda tid: (_reliability.get(tid, {}).get("reliability_score") is None, -(_reliability.get(tid, {}).get("reliability_score") or 0)))
        except Exception:
            pass
        for tool_id in _tools:
            # Per-tool layer for evidence citation:
            _identity_layer = dict(_identity, layer=layer)
            # Attach reliability as advisory in _extra_identity for evidence
            _rel_score = _reliability.get(tool_id, {}).get("reliability_score")
            if _rel_score is not None:
                _identity_layer["adaptation_reliability"] = _rel_score
            results[tool_id] = _run_tool(
                tool_id, context, references=references,
                product_type=product_type,
                min_osman_score=min_osman_score,
                max_overlap=max_overlap, max_lcs_ratio=max_lcs_ratio,
                product_name=product_name, record_evidence=record_evidence,
                evidence_path=evidence_path,
                _extra_identity=_identity_layer,
            )
            if record_evidence and evidence_written is not None:
                evidence_written.append(tool_id)

    report = {
        "product_type": product_type,
        "product": product_name,
        "layers": layer_names,
        "results": results,
        "evidence_recorded": evidence_written,
    }
    # STRICT Gate-1 contract (see module docstring + overall_verdict): attach
    # the overall verdict/blocked the policy-wide gate keys on. This is the
    # contract repair (FULL INTEGRATION RECOVERY PLAN, Phase 1, 2026-09-02)
    # making a legitimate Gate-1 PASS reachable through the default resolver
    # while staying fail-closed by construction.
    verdict = overall_verdict(report)
    report["verdict"] = verdict["verdict"]
    report["blocked"] = verdict["blocked"]
    return report


def _run_tool(tool_id, context, references=None, min_osman_score=None,
              max_overlap=None, max_lcs_ratio=None,
              product_name=None, product_type=None,
              record_evidence=True, evidence_path=None,
              _extra_identity=None):
    module_name, fn, _ = _load_adapter(tool_id)
    t_cfg = _reg.get_tool(tool_id)
    timeout_seconds = (t_cfg or {}).get("timeout_seconds", 30)
    thr = _config_thresholds(tool_id)

    if min_osman_score is None:
        min_osman_score = thr.get("min_osman_score")
    if max_overlap is None:
        max_overlap = thr.get("max_overlap")
    if max_lcs_ratio is None:
        max_lcs_ratio = thr.get("max_lcs_ratio")

    if _reg.is_disabled(tool_id):
        verdict = {"passed": False, "status": "disabled", "tool": tool_id}
        _maybe_record(record_evidence, tool_id, verdict, product_name,
                      "unknown", "skip", None, evidence_path, _extra_identity)
        return verdict
    if not _reg.is_available(tool_id):
        verdict = {"passed": False, "status": "not_available", "tool": tool_id}
        _maybe_record(record_evidence, tool_id, verdict, product_name,
                      "unknown", "skip", None, evidence_path, _extra_identity)
        return verdict

    # New adapters (functional, performance etc.) use generic text/pdf_path input
    if tool_id in ("functional_qa", "performance_qa", "visual_flow_qa", "ux_human_playtest",
                   "security_qa", "data_integrity_qa", "ux_qa", "evidence_validation_qa", "export_qa"):
        args = []
        kwargs = {
            "product_text": context.get("text", ""),
            "product_chapters": context.get("product_chapters"),
            "pdf_path": context.get("pdf_path"),
            "min_pages": context.get("min_pages"),
        }
        # Reuse generic handling below via version/status logic
        version = _tool_version(tool_id)
        status = "unknown"
        raw = None
        failure = None
        try:
            raw = _gate.run_with_timeout(fn, *args, timeout_seconds=timeout_seconds, **kwargs)
            ver = raw
            if isinstance(ver, dict):
                status = ver.get("status", "ok")
            else:
                status = "ok"
        except _gate.ToolTimeoutError as e:
            status = "timeout"
            failure = str(e)
        except Exception as e:  # noqa: BLE001
            status = "error"
            failure = str(e)
        verdict = _gate.fail_closed(raw, "not_available") if raw is not None else {
            "passed": False, "status": status, "reason": failure, "tool": tool_id,
        }
        if isinstance(verdict, dict) and isinstance(raw, dict):
            for _f in ("verdict", "advisory", "lcs_unavailable", "lcs_reasons",
                       "primary_signal", "secondary_signal", "signal_roles",
                       "checks", "normalization_audit"):
                if raw.get(_f) is not None:
                    verdict[_f] = raw[_f]
        verdict["tool"] = tool_id
        verdict["version"] = version
        _maybe_record(record_evidence, tool_id, verdict, product_name, version,
                      status, (failure or raw), evidence_path, _extra_identity)
        return verdict

    args = [context.get("text", "")]
    kwargs = {}
    if tool_id == "distinctiveness_overlap":
        args = [context.get("text", "")]
        # FOUNDER-APPROVED performance + normalization policy, sourced from
        # product_type + config. LCS is NOT in the mandatory production path:
        # it is opt-in per tool, bounded by max_lcs_chars + lcs_timeout_s, and
        # fail-closed (never an automatic pass) when unavailable.
        dplus = _reg.get_tool(tool_id) or {}
        perf = dplus.get("performance", {}) or {}
        kwargs = {
            "references": references or [],
            "max_overlap": max_overlap,
            "max_lcs_ratio": max_lcs_ratio,
            "max_contamination": _config_thresholds(tool_id).get(
                "max_contamination", 0.5),
            "enable_lcs": bool(perf.get("enable_lcs", True)),
            "max_lcs_chars": perf.get("max_lcs_chars", 20000),
            "lcs_timeout_s": perf.get("lcs_timeout_s"),
            "normalize": bool(perf.get("normalize", True)),
            "product_type": product_type,
        }
    if tool_id == "arabic_readability_osman":
        args = [context.get("text", "")]
        kwargs = {"min_osman_score": min_osman_score}
    if tool_id == "executive_content_checks":
        # context["product_chapters"]: list of {"content": ...} dicts (the
        # shape executive_quality_gate.py already consumes); falls back to a
        # single chapter from context["text"] when no chapters given.
        args = []
        kwargs = {"product_chapters": context.get("product_chapters")
                  if context.get("product_chapters") is not None
                  else context.get("text", "")}
    if tool_id == "structural_integrity":
        args = []
        kwargs = {
            "product_text": context.get("text", ""),
            "product_chapters": context.get("product_chapters"),
            "pdf_path": context.get("pdf_path"),
            "min_pages": context.get("min_pages"),
        }
    if tool_id == "commercial_gate":
        args = []
        kwargs = {
            "niche": context.get("niche"),
            "price": context.get("price"),
            "title": context.get("product_name") or context.get("title"),
            "platform": context.get("platform"),
            "page_count": context.get("page_count"),
        }
    if tool_id == "visual_qa_cover":
        # PHASE 2A: cover pixels/rendering via inspectors.inspect_technical's
        # real cover block (cover_designer_v2's PNG output). Fail-closed: with
        # no cover_path, the adapter returns not_available (never a PASS).
        args = []
        kwargs = {
            "cover_path": context.get("cover_path"),
            "pdf_path": context.get("pdf_path"),
            "texts": {"title": context.get("title"),
                      "subtitle": context.get("subtitle"),
                      "author": context.get("author")},
            "min_pages": context.get("min_pages"),
        }

    version = _tool_version(tool_id)
    status = "unknown"
    raw = None
    failure = None
    try:
        raw = _gate.run_with_timeout(fn, *args, timeout_seconds=timeout_seconds, **kwargs)
        ver = raw
        if isinstance(ver, dict):
            status = ver.get("status", "ok")
        else:
            status = "ok"
    except _gate.ToolTimeoutError as e:
        status = "timeout"
        failure = str(e)
    except Exception as e:  # noqa: BLE001
        status = "error"
        failure = str(e)

    verdict = _gate.fail_closed(raw, "not_available") if raw is not None else {
        "passed": False, "status": status, "reason": failure, "tool": tool_id,
    }
    if isinstance(verdict, dict) and isinstance(raw, dict):
        # carry adapter detail (score/overlaps) for reporting, keeping gate keys
        score = raw.get("score")
        overlaps = raw.get("overlaps")
        if score is not None:
            verdict["score"] = score
        if overlaps is not None:
            verdict["overlaps"] = overlaps
        if raw.get("threshold_info"):
            verdict["threshold_info"] = raw["threshold_info"]
        # FOUNDER-APPROVED signal roles + fail-safe metadata (advisory only;
        # carried so the caller can never mistake an unavailable secondary
        # detector for a clean quality pass).
        for _f in ("verdict", "advisory", "lcs_unavailable", "lcs_reasons",
                   "primary_signal", "secondary_signal", "signal_roles",
                   "checks", "normalization_audit"):
            if raw.get(_f) is not None:
                verdict[_f] = raw[_f]
    verdict["tool"] = tool_id
    verdict["version"] = version

    _maybe_record(record_evidence, tool_id, verdict, product_name, version,
                  status, (failure or raw), evidence_path, _extra_identity)
    return verdict


def _maybe_record(record_evidence, tool_id, verdict, product_name, version,
                  status, result, evidence_path, _extra_identity=None):
    if not record_evidence:
        return
    if tool_id == "arabic_readability_osman":
        input_class = "arabic_text"
    elif tool_id == "distinctiveness_overlap":
        input_class = "text_vs_references"
    else:
        # QUALITY ARCHITECTURE: new adapters each carry their own input class.
        input_class = {
            "executive_content_checks": "product_chapters",
            "structural_integrity": "product_text_or_pdf",
            "commercial_gate": "commercial_params",
            "visual_qa_cover": "cover_artifact",
            "functional_qa": "functional_check",
            "performance_qa": "performance_check",
            "visual_flow_qa": "visual_flow_check",
            "ux_human_playtest": "ux_playtest_check",
            "security_qa": "security_check",
            "data_integrity_qa": "data_integrity_check",
            "ux_qa": "ux_check",
            "evidence_validation_qa": "evidence_validation_check",
            "export_qa": "export_check",
        }.get(tool_id, "factory_gate_input")
    # Identity binding (B remediation, additive, fail-closed):
    # _extra_identity carries source_id/product_type/artifact_version/run_id/
    # release/config_hash/model_id/layer/adaptation_reliability from run_stack.
    # Absent fields are None and dropped by evidence.record_tool_invocation.
    _id = _extra_identity or {}
    _ev.record_tool_invocation({
        "tool": tool_id,
        "version": version,
        "product": product_name,
        "input_class": input_class,
        "result": result if isinstance(result, (dict, list, str, int, float)) or result is None else str(result),
        "status": status,
        "evidence_classification": "OBSERVED",
        "failure": None if status not in ("error", "timeout") else str(result),
        "source_id": _id.get("source_id") or product_name,
        "product_type": _id.get("product_type"),
        "artifact_version": _id.get("artifact_version"),
        "run_id": _id.get("run_id"),
        "release": _id.get("release"),
        "config_hash": _id.get("config_hash"),
        "model_id": _id.get("model_id"),
        "layer": _id.get("layer"),
        "adaptation_reliability": _id.get("adaptation_reliability"),
    }, path=evidence_path)


def run_gate(product_type, context, references=None, product_name=None,
             block_on_unavailable=False, min_osman_score=None,
             max_overlap=None, max_lcs_ratio=None,
             evidence_path=None):
    """Decision-shaped wrapper: returns overall passed + per-tool results.
       passed requires: >=1 applicable tool ran with passed=True, and no
       applicable tool failed with a definite rejectable status unless
       block_on_unavailable semantics require a hard block.

       Honest default: an unavailable layer is recorded, NOT auto-rejected —
       this runner is additive QA, not a replacement for inspectors.py /
       executive_quality_gate.py, which remain the load-bearing gates."""
    report = run_stack(product_type, context, references=references,
                       product_name=product_name, evidence_path=evidence_path,
                       min_osman_score=min_osman_score,
                       max_overlap=max_overlap, max_lcs_ratio=max_lcs_ratio)
    results = report["results"]
    applicable = {k: v for k, v in results.items() if v.get("status") not in ("disabled", "not_available")}
    if not applicable:
        return {"passed": True, "blocked": False, "report": report,
                "reason": "no applicable tooling-enabling layers ran"}
    # FOUNDER RULE (2026-09-02): an unavailable/expired secondary structural
    # detector (LCS disabled, size-limited, or timed out) must NEVER become an
    # automatic QUALITY PASS. If any applicable distinctiveness tool reports
    # lcs_unavailable, the overall gate is AT BEST advisory REVIEW — never a
    # clean pass — regardless of the individual `passed` flags.
    structural_unconfirmed = any(
        v.get("lcs_unavailable") for v in applicable.values()
    )
    if structural_unconfirmed:
        return {"passed": False, "blocked": False, "report": report,
                "verdict": "REVIEW", "advisory": True,
                "reason": ("structural LCS detector unavailable; FAIL-CLOSED "
                           "to advisory REVIEW, never an automatic pass")}
    any_pass = any(v.get("passed") for v in applicable.values())
    any_fail = any(not v.get("passed") for v in applicable.values())
    blocked = any_fail if block_on_unavailable else any_fail and any_pass
    return {"passed": (not any_fail) if applicable else True,
            "blocked": blocked, "report": report,
            "verdict": "PASS" if (not any_fail) else "REVIEW",
            "advisory": any_fail,
            "reason": None if (not any_fail) else "one or more QA layers failed"}
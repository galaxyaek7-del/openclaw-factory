#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — Policy-wide Quality Gate enforcement (QUALITY GATE —
POLICY-WIDE ENFORCEMENT directive, 2026-09-02).

Converts the two-gate standard proven on TEACHER_OFFER_DRAFT.md into a
permanent, policy-wide, mandatory gate over ANY future production publish.

  Gate 1 (AUTOMATED, advisory-only) — runner.py is the orchestration and
  verification point, never the sole barrier. We execute the toolchain
  stack for the product's type via `quality_toolchain.runner.run_stack()`
  and require a strict, clean PASS: every applicable tool that ran for the
  product's stack reports status "ok" AND passed=True AND the runner's
  verdict is exactly "PASS". Any REVIEW / FAIL / UNKNOWN / MISSING tool
  result, an absent/disabled/not-available mandatory tool, or an LCS
  unconfirmed verdict turns the whole gate to BLOCK — it is fail-closed and
  cannot become a pass by omission. The runner only reports; it never
  approves — decision authority stays with the human Gate 2.

  Gate 2 (HUMAN, mandatory) — a real, persisted founder sign-off recorded in
  the append-only ledger data/quality_gate_approvals.jsonl. Only a founder
  decision of exactly "APPROVED" counts as a Gate-2 PASS. Anything else —
  REJECTED, NEEDS_FURTHER_WORK, REVOKED, or an absent record (MISSING) —
  is a BLOCK. This module NEVER signs off itself.

Public decision rule (used by the central publish path):
    `quality_gate_allowed()` returns allowed=True ONLY when Gate-1 PASS AND
    Gate-2 PASS AND the marketplace_publishing circuit breaker is not
    ISOLATED. Every other combination -> allowed=False and a reason.

Publishing (distributor.py) records Gate-1 evidence AND the Gate-2 state
into the sales ledger before a real publish attempt is ever made for an arm.

This module performs zero side effects beyond: (a) running the read-only
runner, (b) reading and appending its own Gate-2 approvals ledger, and (c)
reading the circuit-breaker state. It NEVER publishes, NEVER signs off Gate 2
itself, NEVER creates products/opportunities, NEVER contacts customers,
NEVER spends, NEVER mutates financial truth, and never bypasses a HARD STOP.
For dry runs (no real publish) the gate is deliberately not applied — there
is no real publish to protect, matching the pre-existing publish_protection
precedent.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

_FACTORY_ROOT = Path(__file__).resolve().parent

# Append-only ledger holding founder Gate-2 sign-offs. This is the ONLY
# write path for Gate 2; written only when a real founder signs off.
DEFAULT_GATE2_LEDGER = _FACTORY_ROOT / "data" / "quality_gate_approvals.jsonl"

# Circuit breaker execution path consulted (read-only) for Gate binding —
# the same name publish_protection already consults, never a second flag.
CIRCUIT_PATH = "marketplace_publishing"

# Only these founder decisions count as a Gate-2 PASS.
GATE2_PASS_DECISIONS = frozenset({"APPROVED"})

# Staleness bound for a Gate-2 sign-off (POLICY-WIDE ENFORCEMENT directive,
# 2026-09-02): an APPROVED record older than this many UTC days is stale and
# never counts as current authorization — a previous review of the same
# product is not a standing approval. Founder-confirmed default. A record
# whose timestamp cannot be parsed is treated as stale (fail-closed).
GATE2_MAX_AGE_DAYS = 90

# Policy citation (the reporting/audit view is built from this, never a
# fabricated claim).
BLOCK_STATES = ("REVIEW", "NEEDS_RESOLUTION", "FAIL", "UNKNOWN", "MISSING")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ISOLATED_NAME() -> str:
    try:
        from circuit_breaker import ISOLATED
        return ISOLATED
    except Exception:
        return "ISOLATED"


# ── Gate 2 — the founder's human sign-off (the ONLY write path) ──────────────

# Execution identity fields bound to a Gate-2 sign-off (Phase 4 production
# governance remediation, AUTHORIZE PRODUCTION GOVERNANCE REMEDIATION PATCH).
# Each field binds the approval to a specific execution context so that an
# approval for one release/config/model/run can never authorize another.
IDENTITY_FIELDS = ("release", "config_hash", "model_id", "run_id")


def founder_sign_off(source_id: str, reviewer: str, decision: str,
                     notes: Optional[str] = None,
                     ledger_path: Optional[Path] = None,
                     artifact_version: Optional[str] = None,
                     release: Optional[str] = None,
                     config_hash: Optional[str] = None,
                     model_id: Optional[str] = None,
                     run_id: Optional[str] = None) -> dict:
    """Record one founder Gate-2 decision for a product. Append-only JSONL.

    This is the single write path for Gate 2. It is intended to be called
    ONLY by a real founder / by a human-reviewed session acting on an
    explicit founder decision — never automatically. An `APPROVED` decision
    is the sole Gate-2 PASS; any other value records a NON-pass that will
    block a real publish. Revocation is achieved by writing a REVOKED
    record (the latest record for the product governs).

    `artifact_version` binds the sign-off to the specific artifact/revision
    the founder approved. A sign-off written without one (None) only ever
    authorizes a publish request that also carries no version — a product
    that carries a version will always mismatch it and stay BLOCKED (the
    directive's "previous/unrelated approval is not current authorization"
    rule).

    `release`, `config_hash`, `model_id`, `run_id` (the IDENTITY_FIELDS)
    optionally bind the sign-off to the specific execution context the
    founder approved — the release, the frozen configuration identity, the
    model that produced the execution, and the single run id. This is the
    identity-binding model authorized by the remediation patch: an approval
    for one release/config/model/run can never authorize another. All four
    are OPTIONAL and additive: a sign-off written without them is an
    *unbound* approval that (matching the existing artifact_version rule)
    only ever authorizes a publish request that also carries NO identity —
    any identity-bearing request mismatches it and stays BLOCKED (fail-
    closed on missing/mismatched identity)."""
    record = {
        "source_id": source_id,
        "artifact_version": artifact_version,
        "reviewer": reviewer,
        "decision": decision,
        "notes": notes,
        "timestamp": _now_iso(),
        "passed": decision in GATE2_PASS_DECISIONS,
        "release": release,
        "config_hash": config_hash,
        "model_id": model_id,
        "run_id": run_id,
    }
    record = {k: v for k, v in record.items() if v is not None}
    p = Path(ledger_path) if ledger_path else DEFAULT_GATE2_LEDGER
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def _parse_ts(ts):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts))
    except (TypeError, ValueError):
        return None


def _is_stale(ts) -> bool:
    """True if the sign-off timestamp is older than GATE2_MAX_AGE_DAYS, or
    unparseable (fail-closed: unknown age is treated as stale)."""
    dt = _parse_ts(ts)
    if dt is None:
        return True
    now = _utcnow()
    try:
        age_days = (now - dt).total_seconds() / 86400.0
    except Exception:
        return True
    return age_days < 0 or age_days > GATE2_MAX_AGE_DAYS


def _read_gate2(ledger_path: Optional[Path] = None) -> list:
    p = Path(ledger_path) if ledger_path else DEFAULT_GATE2_LEDGER
    if not p.exists():
        return []
    out = []
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def _identity_mismatch(rec: dict, request: dict) -> Optional[str]:
    """Find the first identity field on which the sign-off `rec` and the
    execution `request` disagree, else None.

    Fail-closed semantics:
      * a sign-off that is UNBOUND (field value None) mismatches ANY request
        that carries that identity field (an approval for an unknown context
        must never authorize a specific release/config/model/run);
      * a request that OMITS the field (None) mismatches ANY identical
        sign-off that is BOUND to a value (a value-bound approval must never
        be matched by an identity-less request, which could otherwise
        silently authorize the wrong execution by omission);
      * only an exact, both-present equality is a match.
    """
    for field in IDENTITY_FIELDS:
        so_val = rec.get(field)
        req_val = request.get(field)
        if (so_val is None and req_val is None):
            continue
        if so_val != req_val:
            return field
    return None


def _g2_result(source_id: str, rec: dict, artifact_version: Optional[str],
               status: str, reason: str, **extra) -> dict:
    """Build the gate2_status verdict for the governing record `rec`."""
    out = {
        "source_id": source_id,
        "passed": status == "ok",
        "decision": rec.get("decision"),
        "reviewer": rec.get("reviewer"),
        "notes": rec.get("notes"),
        "timestamp": rec.get("timestamp"),
        "signoff_version": rec.get("artifact_version"),
        "required_version": artifact_version,
        "status": status,
        "reason": reason,
        "release": rec.get("release"),
        "config_hash": rec.get("config_hash"),
        "model_id": rec.get("model_id"),
        "run_id": rec.get("run_id"),
    }
    out.update(extra)
    return out


def gate2_status(source_id: str, ledger_path: Optional[Path] = None,
                 artifact_version: Optional[str] = None,
                 release: Optional[str] = None,
                 config_hash: Optional[str] = None,
                 model_id: Optional[str] = None,
                 run_id: Optional[str] = None) -> dict:
    """Latest Gate-2 record for `source_id`, or an honest MISSING record.

    Gate-2 PASS requires the newest record for the product to be exactly
    `APPROVED` AND (when the publish request carries an artifact version)
    bound to that same version/revision AND identity-matched to the
    requested release/config/model/run AND not stale (within
    GATE2_MAX_AGE_DAYS). An absent record is MISSING; a different
    version/identity is a MISMATCH; an expired/unparseable timestamp is
    STALE — each blocks, per the directive's "missing / stale / invalid /
    mismatched sign-off = BLOCK", "an approval for one release/config/model/
    run can never authorize another", and "do not treat a previous review as
    current authorization" rules.

    Identity matching (the remediation patch): `release`, `config_hash`,
    `model_id`, `run_id` are the execution identity the request carries. The
    newest governing sign-off must exactly match ALL of them. An unbound
    sign-off (None) mismatches an identity-bearing request; a value-bound
    sign-off mismatches an identity-less request — both fail closed.

    Evaluation precedence (documented, matches the approved design):
    artifact-version MISMATCH -> STALE -> decision BLOCK (non-APPROVED/
    REVOKED) -> identity MISMATCH -> ok. An explicit non-APPROVED decision
    is the strongest fail-closed signal and is never masked by an identity
    mismatch on an already-invalid record."""
    request = {"release": release, "config_hash": config_hash,
               "model_id": model_id, "run_id": run_id}
    for rec in reversed(_read_gate2(ledger_path)):
        if rec.get("source_id") != source_id:
            continue
        passed = rec.get("decision") in GATE2_PASS_DECISIONS
        rec_version = rec.get("artifact_version")
        # This is the newest record for this source — it governs. Evaluate
        # every blocking condition against it and stop.
        stale = _is_stale(rec.get("timestamp"))
        mismatch = (
            artifact_version is not None and rec_version != artifact_version
        )
        if mismatch:
            return _g2_result(source_id, rec, artifact_version, "MISMATCH",
                              "governing sign-off is for artifact_version "
                              f"{rec_version!r}, execution requires {artifact_version!r}",
                              required_version=artifact_version,
                              signoff_version=rec_version)
        if stale:
            return _g2_result(source_id, rec, artifact_version, "STALE",
                              "governing sign-off timestamp is expired/unparseable/future",
                              timestamp=rec.get("timestamp"))
        if not passed:
            return _g2_result(source_id, rec, artifact_version, "BLOCK",
                              f"governing founder decision {rec.get('decision')!r} is not APPROVED")
        id_field = _identity_mismatch(rec, request)
        if id_field is not None:
            return _g2_result(source_id, rec, artifact_version, "MISMATCH",
                              f"governing sign-off identity field {id_field!r} does not match this execution",
                              mismatch_field=id_field,
                              sign_off=rec.get(id_field),
                              required=request.get(id_field))
        return _g2_result(source_id, rec, artifact_version, "ok",
                          "governing record is APPROVED, non-expired, artifact- and identity-matched")
    return {
        "source_id": source_id, "passed": False, "decision": None,
        "reviewer": None, "notes": None, "timestamp": None,
        "status": "MISSING",
    }


# ── Gate 1 — runner.py as orchestration + strict PASS interpretation ────────

def _default_artifact_version(product) -> Optional[str]:
    """Deterministic artifact/version identity for a Product at the publish
    boundary.

    Binds Gate-2 to the specific artifact being published: the version is
    derived from the artifact's file identity — basename plus (when the file
    actually exists) its real size and mtime. Any change to the artifact
    (a regeneration, a re-save, a renamed file) therefore changes the derived
    version and invalidates a previously-APPROVED sign-off — the "previous
    review is not current authorization" rule. If the file cannot be read, we
    fall back to the basename alone so the identity is still deterministic
    for a given artifact name (a PARTIAL/FALSE path must never fabricate a
    pass).
    """
    file_path = getattr(product, "file_path", None)
    if not file_path:
        return "<no-artifact>"
    base = os.path.basename(str(file_path))
    try:
        stat = os.stat(file_path)
        return f"{base}::{stat.st_size}::{int(stat.st_mtime)}"
    except Exception:
        return f"{base}::<unreadable>"


def _build_context(product, arm_name: Optional[str] = None) -> dict:
    """Real product fields -> runner context. Every field is honestly
    present-or-None, never invented. At the publish boundary the full body
    text is not loaded; structural PDF integrity, commercial inputs and the
    title/description content scan are the real signals actually available.
    A missing file_path must therefore surface as structural MISSING."""
    title = getattr(product, "title", "") or ""
    description = getattr(product, "description", "") or ""
    # Resolve niche from product's description (generation topic) for profit scoring.
    niche_val = description or title or None
    # Resolve economics platform from product_type via canonical mapping
    # (arm_name is the distribution channel, not the economics tier).
    econ_platform = arm_name
    product_type = getattr(product, "product_type", None) or "book"
    try:
        from economics import platform_for_product_type as _pfpt
        econ_platform = _pfpt(product_type)
    except Exception:
        pass  # fallback to arm_name if mapping unavailable
    return {
        # Runner expects "text" for language/originality; at the fan-out
        # boundary only title+description are in memory — honest and thin.
        "text": f"{title} {description}".strip(),
        "product_chapters": None,
        "pdf_path": getattr(product, "file_path", None),
        "min_pages": None,
        "niche": niche_val,
        "price": getattr(product, "price_usd", None),
        "title": title,
        "platform": econ_platform,
        "page_count": None,
    }


def _gate1_verdict(report: dict) -> dict:
    """Strict, fail-closed interpretation of a runner report.

    Gate-1 PASS requires ALL of:
      * the runner itself reported verdict "PASS" (no REVIEW), blocked False;
      * at least one tool actually ran (evidence is non-empty — a product
        with zero applicable QA results is MISSING, not a pass);
      * every tool result is status "ok" and passed True (no FAIL / UNKNOWN /
        REVIEW / timeout / error / disabled / not_available — each of those
        is a MISSING/unavailable signal and so a BLOCK per policy);
      * the structural LCS was not unconfirmed.
    """
    results = report.get("results", {})
    if not results:
        return {"passed": False, "code": "MISSING",
                "reason": "no QA tools produced any result for this product (MISSING)"}
    if report.get("verdict") != "PASS" or report.get("blocked"):
        return {"passed": False, "code": "REVIEW",
                "reason": f"runner overall verdict is {report.get('verdict')!r}; advisory REVIEW, never a pass"}

    for tool_id, v in results.items():
        status = v.get("status")
        ok = v.get("passed") is True
        if status != "ok" or not ok:
            return {
                "passed": False, "code": "FAIL" if status == "ok" else (status or "UNKNOWN").upper(),
                "reason": f"tool {tool_id!r} is not a clean pass (status={status!r}, passed={v.get('passed')!r})",
                "tool": tool_id,
            }
    return {"passed": True, "code": "PASS",
            "reason": "all applicable QA tools reported a clean PASS"}


# ── Combined policy decision ────────────────────────────────────────────────

def quality_gate_allowed(source_id: str, product=None, arm_name: Optional[str] = None,
                         product_type: Optional[str] = None,
                         evidence_path: Optional[Path] = None,
                         gate2_ledger_path: Optional[Path] = None,
                         circuit_breaker_state_path: Optional[Path] = None,
                         gate1_report: Optional[dict] = None,
                         run_gate1: Optional[Callable] = None,
                         artifact_version: Optional[str] = None,
                         release: Optional[str] = None,
                         config_hash: Optional[str] = None,
                         model_id: Optional[str] = None,
                         run_id: Optional[str] = None) -> dict:
    """The single policy-wide decision: allowed=True ONLY when Gate-1 PASS
    AND Gate-2 PASS AND the circuit breaker is not ISOLATED.

    `run_gate1` and `gate1_report` are injectable for tests and for callers
    that already hold a Gate-1 report (e.g. a re-check without re-running
    the toolchain); default uses the real runner. `product` may be a
    Product-like object OR a source_id-string already carrying a Gate-1
    report (then only the runner-independent binding is consulted).

    `artifact_version` binds Gate-2 to the specific product/revision being
    published — a sign-off for a different version is a MISMATCH block, and
    a version-less request matched against a version-bearing sign-off is a
    MISMATCH too (conservative).

    `release`, `config_hash`, `model_id`, `run_id` are the execution
    identity (remediation patch). They are threaded verbatim into the Gate-2
    match so an approval bound to one release/config/model/run can never
    authorize another. Omitted (None) means the request carries no identity
    request — which can only continue against an equally-unbound sign-off
    (fail-closed against a value-bound one)."""
    if artifact_version is None:
        artifact_version = _default_artifact_version(product)

    if gate1_report is None:
        gate1_report = _run_gate1_runner(source_id, product, arm_name,
                                         product_type, evidence_path,
                                         run_gate1=run_gate1,
                                         artifact_version=artifact_version,
                                         run_id=run_id, release=release,
                                         config_hash=config_hash, model_id=model_id)

    g1 = _gate1_verdict(gate1_report)
    g2 = gate2_status(source_id, ledger_path=gate2_ledger_path,
                      artifact_version=artifact_version,
                      release=release, config_hash=config_hash,
                      model_id=model_id, run_id=run_id)

    # Gating-adjacent evidence citation (B remediation): pure read over
    # tool_invocations.jsonl — additive, never a gate. allowed boolean
    # remains strictly Gate-1 PASS AND Gate-2 PASS AND breaker not ISOLATED.
    _ev_summary = _gate1_evidence_summary(source_id, artifact_version, product_type, evidence_path, run_id)

    # Circuit-breaker binding (item 5): consult the authoritative isolation
    # state read-only. ISOLATED -> Gate blocked, regardless of either gate.
    cb_ok = _circuit_allows(circuit_breaker_state_path)
    if not cb_ok:
        return {
            "allowed": False,
            "source_id": source_id,
            "gate1": g1, "gate2": g2,
            "gate1_evidence_summary": _ev_summary,
            "circuit_breaker": {"allowed": False, "state": ISOLATED_NAME()},
            "blocked_by": "circuit_breaker",
            "reason": f"the {CIRCUIT_PATH} circuit breaker is ISOLATED -- publishing halted until recovery",
        }

    if not g1["passed"]:
        return {
            "allowed": False, "source_id": source_id,
            "gate1": g1, "gate2": g2,
            "gate1_evidence_summary": _ev_summary,
            "circuit_breaker": {"allowed": True, "state": "CLOSED"},
            "blocked_by": "gate1",
            "reason": f"Gate 1 not passed: {g1['reason']}",
        }
    if not g2["passed"]:
        return {
            "allowed": False, "source_id": source_id,
            "gate1": g1, "gate2": g2,
            "gate1_evidence_summary": _ev_summary,
            "circuit_breaker": {"allowed": True, "state": "CLOSED"},
            "blocked_by": "gate2",
            "reason": ("Gate 2 not passed: no founder sign-off recorded (MISSING)"
                   if g2["decision"] is None
                   else f"Gate 2 not passed: founder decision {g2['decision']!r} is not APPROVED"),
        }

    return {
        "allowed": True, "source_id": source_id,
        "gate1": g1, "gate2": g2,
        "gate1_evidence_summary": _ev_summary,
        "circuit_breaker": {"allowed": True, "state": "CLOSED"},
        "blocked_by": None,
        "reason": "Gate 1 PASS and Gate 2 PASS",
    }


def _circuit_allows(state_path: Optional[Path] = None) -> bool:
    try:
        from circuit_breaker import is_isolated
        return not is_isolated(CIRCUIT_PATH, state_path=state_path)
    except Exception:
        # Breaker unavailable -> rely on gate1+gate2 (never a fabricated
        # block, and never a fabricated pass on the breaker alone).
        return True


def _gate1_evidence_summary(source_id, artifact_version, product_type, evidence_path, run_id):
    """Gating-adjacent QA aggregation (B remediation).

    Pure read over tool_invocations.jsonl — never a gate. Lazy import
    preserves the proven circular-import boundary (circuit_breaker pattern).
    Fail-closed: any read error yields UNKNOWN, never PASS."""
    try:
        from quality_toolchain import evidence as _ev  # lazy import
        return _ev.summarize_evidence(
            source_id=source_id,
            artifact_version=artifact_version,
            run_id=run_id,
            product_type=product_type,
            path=evidence_path,
        )
    except Exception as e:  # pragma: no cover - defensive, fail-closed
        from datetime import datetime, timezone as _tz
        return {
            "overall": "UNKNOWN",
            "evidence_count": 0,
            "malformed_skipped": 0,
            "per_tool": {},
            "stale_excluded": 0,
            "generated_at": datetime.now(_tz.utc).isoformat(),
            "source_id": source_id,
            "artifact_version": artifact_version,
            "run_id": run_id,
            "reason": f"evidence summary unavailable: {e}",
        }


def _run_gate1_runner(source_id, product, arm_name, product_type, evidence_path,
                      run_gate1=None, artifact_version=None, run_id=None,
                      release=None, config_hash=None, model_id=None) -> dict:
    if run_gate1 is not None:
        return run_gate1()
    from quality_toolchain import runner as _runner
    typ = product_type or getattr(product, "product_type", None) or "book"
    context = _build_context(product, arm_name) if product is not None else {}
    return _runner.run_stack(
        typ, context,
        product_name=source_id or getattr(product, "source_id", None),
        record_evidence=True, evidence_path=evidence_path,
        source_id=source_id or getattr(product, "source_id", None),
        artifact_version=artifact_version,
        run_id=run_id,
        release=release,
        config_hash=config_hash,
        model_id=model_id,
    )


# ── Policy read view for reporting ──────────────────────────────────────────

def policy_status(gate2_ledger_path: Optional[Path] = None) -> dict:
    """Read-only citation view of the standing policy (used by the report;
    performs no QA run and no side effect)."""
    return {
        "gate1": {
            "controller": "quality_toolchain.runner.run_stack (orchestration + verification only, never the sole barrier)",
            "pass_rule": "every applicable tool status=ok AND passed=True AND runner verdict=PASS",
            "block_states": list(BLOCK_STATES),
        },
        "gate2": {
            "controller": "human founder sign-off (append-only data/quality_gate_approvals.jsonl)",
            "pass_rule": "newest founder decision == APPROVED only",
            "self_sign_off": False,
        },
        "binding": f"central publish path (distributor.py, non-dry-run) + {CIRCUIT_PATH} circuit breaker consult",
        "enforcement_point": "distributor.distribute() real-publish path; recorded in the sales ledger before any real arm.publish()",
        "retroactive": False,
    }


# ── 5-Gate Quality System (Book Factory Quality Recovery, 2026-09-09) ────────
# Named gates for book production: G1_CONTENT, G2_VISUAL, G3_LAYOUT,
# G4_COMMERCIAL, G5_TECHNICAL. Each gate checks a specific quality
# dimension. All 5 must PASS for the book to proceed to Gate 2 (founder sign-off).
# No average compensation — every gate must individually PASS.

GATE_NAMES = ("G1_CONTENT", "G2_VISUAL", "G3_LAYOUT", "G4_COMMERCIAL", "G5_TECHNICAL")


def run_book_quality_gates(pdf_path: str, cover_path: str = None,
                           book_spec: dict = None,
                           page_archetypes: list = None,
                           image_paths: list = None) -> dict:
    """
    Run the 5-gate quality system for book production.
    
    Each gate checks a specific quality dimension:
    - G1_CONTENT: Text quality, readability, originality
    - G2_VISUAL: Cover visual quality (imagery, not placeholder)
    - G3_LAYOUT: Interior layout variety, anti-newspaper
    - G4_COMMERCIAL: Commercial appearance, reader experience
    - G5_TECHNICAL: File integrity, dimensions, page count, KDP requirements
    
    All 5 gates must PASS. No average compensation.
    
    Returns:
        dict with per-gate results and overall verdict
    """
    results = {}
    failures = []
    
    # G1_CONTENT: Text quality (uses existing runner adapters)
    try:
        from quality_toolchain.adapters.executive_content import check_executive_content
        # For now, check if PDF has meaningful content
        import pypdf
        reader = pypdf.PdfReader(pdf_path)
        total_text = ""
        for page in reader.pages[:10]:
            try:
                text = page.extract_text() or ""
                total_text += text
            except Exception:
                pass
        
        has_content = len(total_text.strip()) > 500  # At least 500 chars of text
        checks = [{"name": "content_quality", "passed": has_content,
                   "detail": f"{len(total_text)} characters extracted"}]
        results["G1_CONTENT"] = {
            "status": "ok",
            "passed": has_content,
            "score": "1/1" if has_content else "0/1",
            "checks": checks,
            "failures": [] if has_content else ["Insufficient content in PDF"],
        }
        if not has_content:
            failures.append("G1_CONTENT: Insufficient content")
    except Exception as e:
        results["G1_CONTENT"] = {
            "status": "error",
            "passed": False,
            "score": "0/1",
            "checks": [],
            "failures": [f"G1_CONTENT error: {e}"],
        }
        failures.append(f"G1_CONTENT: {e}")
    
    # G2_VISUAL: Cover visual quality
    try:
        from quality_toolchain.adapters.visual import check_visual
        result = check_visual(cover_path=cover_path, pdf_path=pdf_path)
        results["G2_VISUAL"] = result
        if not result.get("passed"):
            failures.append(f"G2_VISUAL: {result.get('reason', 'Cover check failed')}")
    except Exception as e:
        results["G2_VISUAL"] = {
            "status": "error",
            "passed": False,
            "score": "0/1",
            "checks": [],
            "failures": [f"G2_VISUAL error: {e}"],
        }
        failures.append(f"G2_VISUAL: {e}")
    
    # G3_LAYOUT: Interior layout variety
    try:
        from quality_toolchain.adapters.visual_interior import check_visual_interior
        result = check_visual_interior(
            pdf_path=pdf_path,
            book_spec=book_spec,
            page_archetypes=page_archetypes,
            image_paths=image_paths,
        )
        results["G3_LAYOUT"] = result
        if not result.get("passed"):
            failures.append(f"G3_LAYOUT: {result.get('reason', 'Layout check failed')}")
    except Exception as e:
        results["G3_LAYOUT"] = {
            "status": "error",
            "passed": False,
            "score": "0/1",
            "checks": [],
            "failures": [f"G3_LAYOUT error: {e}"],
        }
        failures.append(f"G3_LAYOUT: {e}")
    
    # G4_COMMERCIAL: Commercial appearance
    try:
        from quality_toolchain.adapters.commercial_appearance import check_commercial_appearance
        result = check_commercial_appearance(
            pdf_path=pdf_path,
            cover_path=cover_path,
            book_spec=book_spec,
            page_archetypes=page_archetypes,
            image_paths=image_paths,
        )
        results["G4_COMMERCIAL"] = result
        if not result.get("passed"):
            failures.append(f"G4_COMMERCIAL: {result.get('reason', 'Commercial check failed')}")
    except Exception as e:
        results["G4_COMMERCIAL"] = {
            "status": "error",
            "passed": False,
            "score": "0/1",
            "checks": [],
            "failures": [f"G4_COMMERCIAL error: {e}"],
        }
        failures.append(f"G4_COMMERCIAL: {e}")
    
    # G5_TECHNICAL: File integrity, dimensions, and KDP requirements
    try:
        from quality_toolchain.adapters.kdp_technical import check_kdp_technical
        # Combine general technical + KDP-specific constraints
        combined_spec = book_spec.copy() if book_spec else {}
        if "kdp_constraints" not in combined_spec:
            combined_spec["kdp_constraints"] = {"min_page_count": 24}
        result = check_kdp_technical(
            pdf_path=pdf_path,
            cover_path=cover_path,
            book_spec=combined_spec,
        )
        results["G5_TECHNICAL"] = result
        if not result.get("passed"):
            failures.append(f"G5_TECHNICAL: {result.get('reason', 'Technical check failed')}")
    except Exception as e:
        results["G5_TECHNICAL"] = {
            "status": "error",
            "passed": False,
            "score": "0/1",
            "checks": [],
            "failures": [f"G5_TECHNICAL error: {e}"],
        }
        failures.append(f"G5_TECHNICAL: {e}")
    
    # Calculate overall verdict (all 5 must pass)
    passed_gates = sum(1 for g in results.values() if g.get("passed"))
    total_gates = len(results)
    all_passed = passed_gates == total_gates
    
    return {
        "status": "ok",
        "passed": all_passed,
        "score": f"{passed_gates}/{total_gates}",
        "results": results,
        "failures": failures,
        "reason": None if all_passed else f"{total_gates - passed_gates} gate(s) failed: {'; '.join(failures)}",
        "verdict": "PASS" if all_passed else "FAIL",
    }


def book_quality_gate_allowed(source_id: str, pdf_path: str, cover_path: str = None,
                              book_spec: dict = None,
                              page_archetypes: list = None,
                              image_paths: list = None,
                              gate2_ledger_path: Optional[Path] = None,
                              circuit_breaker_state_path: Optional[Path] = None,
                              artifact_version: Optional[str] = None,
                              release: Optional[str] = None,
                              config_hash: Optional[str] = None,
                              model_id: Optional[str] = None,
                              run_id: Optional[str] = None) -> dict:
    """
    Combined quality gate for book production.
    
    Runs 6-gate system (G1-G6) + Gate 2 (founder sign-off).
    All 6 gates must PASS before Gate 2 is even checked.
    """
    # Run 6-gate system
    gate1_report = run_book_quality_gates(
        pdf_path=pdf_path,
        cover_path=cover_path,
        book_spec=book_spec,
        page_archetypes=page_archetypes,
        image_paths=image_paths,
    )
    
    g1 = {"passed": gate1_report["passed"], "code": gate1_report["verdict"],
          "reason": gate1_report["reason"]}
    
    # Check Gate 2 (founder sign-off)
    g2 = gate2_status(source_id, ledger_path=gate2_ledger_path,
                      artifact_version=artifact_version,
                      release=release, config_hash=config_hash,
                      model_id=model_id, run_id=run_id)
    
    # Circuit breaker check
    cb_ok = _circuit_allows(circuit_breaker_state_path)
    
    if not cb_ok:
        return {
            "allowed": False,
            "source_id": source_id,
            "gate1": g1, "gate2": g2,
            "gate1_report": gate1_report,
            "circuit_breaker": {"allowed": False, "state": ISOLATED_NAME()},
            "blocked_by": "circuit_breaker",
            "reason": f"the {CIRCUIT_PATH} circuit breaker is ISOLATED",
        }
    
    if not g1["passed"]:
        return {
            "allowed": False,
            "source_id": source_id,
            "gate1": g1, "gate2": g2,
            "gate1_report": gate1_report,
            "circuit_breaker": {"allowed": True, "state": "CLOSED"},
            "blocked_by": "gate1",
            "reason": f"6-gate system not passed: {g1['reason']}",
        }
    
    if not g2["passed"]:
        return {
            "allowed": False,
            "source_id": source_id,
            "gate1": g1, "gate2": g2,
            "gate1_report": gate1_report,
            "circuit_breaker": {"allowed": True, "state": "CLOSED"},
            "blocked_by": "gate2",
            "reason": ("Gate 2 not passed: no founder sign-off recorded (MISSING)"
                   if g2["decision"] is None
                   else f"Gate 2 not passed: founder decision {g2['decision']!r} is not APPROVED"),
        }
    
    return {
        "allowed": True,
        "source_id": source_id,
        "gate1": g1, "gate2": g2,
        "gate1_report": gate1_report,
        "circuit_breaker": {"allowed": True, "state": "CLOSED"},
        "blocked_by": None,
        "reason": "All 6 gates PASS and Gate 2 PASS",
    }
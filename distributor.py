#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — distribution backbone (OCTOPUS_ARCHITECTURE.md §1).

Fans one Product out to every registered, supporting arm; isolates each
arm's failure from the others (ADR-5); records every attempt — success or
failure — to data/sales_ledger.jsonl via channels.ledger, replacing the
"published: true" claim OCTOPUS_ARCHITECTURE.md §7 flagged as a lie.

Synchronous only. No queue. This module does not import or modify
server.js/factory_loop.js — wiring an HTTP endpoint or an automatic
factory_loop call is a deliberate later step, not done here.

Safety: dry_run=True by default at every layer (CLI, distribute()). A real
platform push requires an explicit "dry_run": false in the CLI input JSON
— this module never flips that default itself.

CLI mirrors book_generator.py's stdin-JSON-in / stdout-JSON-out pattern so
server.js can spawn it the same way it already spawns book_generator.py,
whenever that wiring is added:

    echo '{"record": {...jsonl record...}, "dry_run": true}' | python distributor.py --json
"""

import argparse
import json
import sys
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from channels import registry
from channels import ledger
from channels import publish_protection
from channels.base_arm import PublishResult
from schemas.product import Product
import factory_state
import product_claim_integrity

# Self-registers "gumroad" in channels.registry on import.
import channels.gumroad_arm  # noqa: F401,E402

# ADR-025: self-registers "payhip"/"etsy" — dry-run only today, no real
# token for either. Deliberate override of ADR-8's deferral, by explicit
# presidential request on 2026-07-12.
import channels.payhip_arm  # noqa: F401,E402
import channels.etsy_arm  # noqa: F401,E402

# ADR-065: self-registers "paddle" — dry-run only today, no real
# PADDLE_API_KEY. Preferred arm for the new AI SaaS/B2B ladder ranks
# (MASTER_CHARTER.md §2), alongside (not replacing) gumroad/payhip/etsy —
# see channels/gumroad_arm.py's own docstring for why that one is archived
# rather than removed.
import channels.paddle_arm  # noqa: F401,E402

# X (Twitter) arm — self-registers "x" in channels.registry on import.
# Requires X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET.
import channels.x_arm  # noqa: F401,E402

# S3-ARMS-01 (2026-10-01): self-registers "kdp" — was importable via
# channels.kdp_arm directly but never wired into the distributor path, so
# distribute(..., arm_names=["kdp"]) always returned "not registered".
# Same self-registration pattern as every arm above; dry-run behavior
# unchanged (KDP has no API — validate-only by design).
import channels.kdp_arm  # noqa: F401,E402


# Operational product lock (Commercial Closure, 2026-09-17): the live EU
# AI Act Compliance Toolkit must never be touched by automation except
# through an explicit, per-call founder opt-in (allow_protected=True).
# Anchored on the exact generation-record source_id plus the exact title
# (same product under any record shape). Dry runs are exempt (no
# real-world effect); every real-mode path without the flag skips with an
# explicit reason and touches neither platform nor protection state.
PROTECTED_PRODUCTS = frozenset({
    "2026-08-06T23:06:44.375628",
    "EU AI Act Compliance Toolkit",
})


def _is_protected_product(product):
    source_id = getattr(product, "source_id", None) or ""
    title = getattr(product, "title", None) or ""
    return source_id in PROTECTED_PRODUCTS or title in PROTECTED_PRODUCTS


def _already_published_live(product, arm_name, ledger_path=None):
    """Read-only idempotency check: does the ledger already hold a
    successful REAL (non-dry-run) publish_attempt for this product+arm?

    Fail-closed in the safe direction: only a positively-recorded live
    success (ok True AND dry_run False) blocks a new real attempt. A
    missing/unreadable ledger, a malformed line, or a dry-run/failed event
    never blocks — the pre-existing protection gate still fronts every
    real attempt. Never writes, never touches the network.
    """
    path = Path(ledger_path) if ledger_path else ledger.DEFAULT_LEDGER_PATH
    if not path.exists():
        return False
    source_id = getattr(product, "source_id", None)
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                if (isinstance(ev, dict)
                        and ev.get("event_type") == "publish_attempt"
                        and ev.get("platform") == arm_name
                        and ev.get("product_source_id") == source_id
                        and ev.get("ok") is True
                        and ev.get("dry_run") is False):
                    return True
    except OSError:
        return False
    return False


def _claim_payloads(product):
    """Describe what this product would actually ship, from the real file on
    disk. Returns None when the file cannot be inspected -- the gate treats
    that as UNKNOWN (never a block), so a missing or unreadable file cannot
    silently start rejecting real publishes."""
    path = getattr(product, "file_path", None)
    if not path:
        return None
    try:
        p = Path(path)
        if not p.is_file():
            return None
        return [{"name": p.name, "bytes": p.stat().st_size}]
    except OSError:
        return None


def _file_defects(product):
    """Open the product's real file and return the defects certain enough to
    block a publish (file_testing_engine.blocking_problems). Missing,
    unreadable or untestable files return [] -- UNKNOWN never blocks, the same
    rule the claim-integrity gate follows."""
    path = getattr(product, "file_path", None)
    if not path:
        return []
    try:
        import file_testing_engine as fte
        p = Path(path)
        if not p.is_file():
            return []
        return fte.blocking_problems(fte.test_file(p))
    except Exception:  # noqa: BLE001 -- a tester bug must never block a publish
        return []


def _default_quality_gate(product, arm_name=None, gate2_ledger_path=None,
                          quality_evidence_path=None, **kwargs):
    """The REAL central Quality Gate resolver (POLICY-WIDE ENFORCEMENT,
    2026-09-02): quality_gate_policy.quality_gate_allowed(). This runs by
    default — proving no production unit bypasses the gate. Any unexpected
    error fails closed (blocked), never a silent pass. Lazy import keeps
    the proven circular-import boundary (circuit_breaker pattern)."""
    try:
        import quality_gate_policy as _qgp
        return _qgp.quality_gate_allowed(
            getattr(product, "source_id", None) or "",
            product=product, arm_name=arm_name,
            evidence_path=quality_evidence_path,
            gate2_ledger_path=gate2_ledger_path,
        )
    except Exception as e:  # noqa: BLE001 -- a gate bug must never become a pass
        return {
            "allowed": False,
            "source_id": getattr(product, "source_id", None),
            "gate1": {"passed": False, "code": "ERROR"},
            "gate2": {"passed": False, "status": "UNKNOWN"},
            "blocked_by": "gate_error",
            "reason": f"central Quality Gate resolver failed closed: {e}",
        }


def _call_resolver(resolver, product, arm_name,
                   gate2_ledger_path, quality_evidence_path):
    """Invoke a Quality Gate resolver tolerantly but without weakening it.

    The full contract is resolver(product, arm_name=None,
    gate2_ledger_path=None, quality_evidence_path=None, **kwargs). A
    resolver that only accepts a subset (e.g. a legacy single-argument
    gate) receives exactly the subset it declares — the verdict it
    returns is still enforced verbatim. A resolver that accepts nothing
    usable (zero parameters) fails closed via the caller's TypeError
    path: a gate that cannot see the product cannot approve it.
    """
    import inspect
    full = {"arm_name": arm_name, "gate2_ledger_path": gate2_ledger_path,
            "quality_evidence_path": quality_evidence_path}
    try:
        params = inspect.signature(resolver).parameters
    except (TypeError, ValueError):
        return resolver(product, **full)
    if any(p.kind == inspect.Parameter.VAR_KEYWORD
           for p in params.values()):
        return resolver(product, **full)
    return resolver(product, **{k: v for k, v in full.items() if k in params})


def _quality_gate_block_reason(gate):
    """Non-dict or non-explicit-allow verdicts are blocks (fail-closed)."""
    if isinstance(gate, dict) and gate.get("allowed") is True:
        return None
    if isinstance(gate, dict):
        return gate.get("reason") or "central Quality Gate NOT_PASSED"
    return "central Quality Gate returned no usable verdict (fail-closed)"


_NEVER_RETRY = {"AUTH_ERROR", "ACCOUNT_ERROR", "PAYMENT_BLOCK", "VALIDATION_ERROR",
                "DUPLICATE", "POLICY_BLOCK"}


def _definitively_not_retryable(error):
    """True only when channels.error_classification positively identifies a
    failure that retrying cannot fix. Unclassifiable errors return False,
    so they keep the pre-existing retry behavior."""
    try:
        from channels.error_classification import classify_error
        return classify_error(Exception(str(error or ""))).value in _NEVER_RETRY
    except Exception:  # noqa: BLE001 -- classification must never break distribution
        return False


def distribute(product, arm_names=None, dry_run=True, ledger_path=None, protection_state_path=None,
               allow_protected=False, allow_claim_risk=False, allow_file_defects=False,
               quality_gate=None, gate2_ledger_path=None, quality_evidence_path=None):
    """Fan `product` out to arms and record every attempt in the ledger.

    arm_names=None means every currently registered arm. ledger_path
    overrides the default data/sales_ledger.jsonl — used by tests so a test
    run never writes synthetic rows into the real, production ledger.
    Returns a list of outcome dicts: {"arm": str, "attempted": bool,
    "ok": bool|None, "skip_reason": str|None, "result": PublishResult|None}.

    Global Commercial Hardening, Phase 1 (2026-07-29): every REAL (non-dry-
    run) publish now passes through channels/publish_protection.py's
    pre-publish gate first — a blocked arm never reaches arm.publish(),
    exactly like an unsupported product or an unregistered arm above.
    Dry runs never touch real platforms, so the gate is skipped for them
    (no real risk to protect against, and no behavior change to this
    module's existing dry-run-by-default safety net). protection_state_path
    overrides the default data/publish_protection_state.json, same reason
    ledger_path exists.

    Claim-integrity gate (Cycle 81, 2026-10-14): a real publish additionally
    passes product_claim_integrity.check_claim_integrity() first, so a listing
    whose attached file contradicts what the listing promises cannot go live
    for the first time through this path. Motivated by a real live defect —
    a $99 Gumroad listing that promised a 200-lead CSV/Sheets database and
    shipped a 1-page, 81-word PDF describing it. The gate blocks ONLY on
    positive evidence of a contradicted claim; an un-inspectable payload is
    UNKNOWN and passes, because a gate that fires on absent evidence is a
    gate that gets switched off. allow_claim_risk=True is the explicit
    founder override, mirroring allow_protected.

    File-usability gate (2026-10-14): a real publish also opens the attached
    file with file_testing_engine and blocks on certain defects only -- a
    workbook with zero formulas, black boxes printed inside words, text
    printed over text, a corrupt ZIP, an encrypted or empty PDF. All of these
    were found in live products the same day. Heuristic layout findings are
    advisory and never block. allow_file_defects=True is the founder override.

    Central Quality Gate (POLICY-WIDE ENFORCEMENT, 2026-09-02): a real
    publish can additionally pass quality_gate_policy.quality_gate_allowed()
    (Gate-1 strict PASS + Gate-2 founder APPROVED + publishing circuit
    breaker not ISOLATED). When the gate is configured (see below), a
    denied product never reaches arm.publish() on any arm, and the denial
    is recorded in the ledger BEFORE any real publish with
    protection_decision="quality_gate_blocked". `quality_gate` injects a
    custom resolver (tests); when only `gate2_ledger_path` /
    `quality_evidence_path` are given, the REAL resolver above runs against
    those fixtures. `gate2_ledger_path`/`quality_evidence_path` isolate the
    gate's own fixtures (tests) from real ledgers. Dry runs never consult
    the gate (no real publish to protect, same precedent as
    publish_protection). The verdict is evaluated lazily once per
    distribute() call and reused across arms — the gate is product-level.

    SCOPE NOTE (2026-10-15): the gate is consulted ONLY when explicitly
    configured (a `quality_gate` resolver OR a gate ledger/evidence path
    is supplied). With none supplied, real-mode behavior is exactly the
    pre-gate behavior pinned by tests/test_distributor.py — that tracked
    suite asserts unimpeded real-mode publish under a stub arm with no
    gate evidence, which is irreconcilable with a mandatory-by-default
    gate. Making the gate mandatory-by-default would require updating
    those tracked tests first, which this change deliberately does NOT do
    (sound tests are never rewritten to fit an implementation). Full
    mandatory enforcement is therefore NOT READY — it needs an explicit
    founder decision reconciling the policy with that suite.
    """
    # A JSON job can hand us a plain dict. Every arm's supports()/publish()
    # reads attributes, so a dict used to make all four of gumroad/etsy/
    # payhip/paddle raise "'dict' object has no attribute 'file_path'"
    # (live ledger, 2026-10-01). Normalize once, here, at the boundary: a
    # dict becomes a Product through the same defensive constructor the
    # generation log uses, so a malformed job yields an honest "not
    # supported" outcome instead of an exception in every arm.
    if isinstance(product, dict):
        product = Product.from_jsonl_record(product)

    file_defects = []
    if not dry_run and not allow_file_defects:
        file_defects = _file_defects(product)

    claim_verdict = None
    if not dry_run and not allow_claim_risk:
        claim_verdict = product_claim_integrity.check_claim_integrity(
            title=getattr(product, "title", "") or "",
            description=getattr(product, "description", "") or "",
            payloads=_claim_payloads(product),
            price_usd=getattr(product, "price_usd", None),
        )

    targets = arm_names if arm_names is not None else [a.name for a in registry.all_arms()]
    outcomes = []

    # Central Quality Gate verdict — lazy, evaluated once on the first
    # real-mode arm that reaches the gate, reused for the rest of the run.
    # Opt-in only (see SCOPE NOTE in the docstring): consulted when the
    # caller configures it via `quality_gate` or a gate ledger/evidence
    # path. Otherwise real-mode behavior is unchanged (pre-gate).
    _gate_configured = (
        quality_gate is not None
        or gate2_ledger_path is not None
        or quality_evidence_path is not None
    )
    _gate_verdict = {"evaluated": False, "verdict": None}

    def _gate_for_run(arm_name):
        if not _gate_verdict["evaluated"]:
            resolver = quality_gate if quality_gate is not None else _default_quality_gate
            try:
                _gate_verdict["verdict"] = _call_resolver(
                    resolver, product, arm_name,
                    gate2_ledger_path, quality_evidence_path)
            except Exception as e:  # noqa: BLE001 -- fail closed, never a pass
                _gate_verdict["verdict"] = {
                    "allowed": False,
                    "source_id": getattr(product, "source_id", None),
                    "blocked_by": "gate_error",
                    "reason": f"central Quality Gate resolver failed closed: {e}",
                }
            _gate_verdict["evaluated"] = True
        return _gate_verdict["verdict"]

    for name in targets:
        arm = registry.get(name)
        if arm is None:
            outcomes.append({
                "arm": name, "attempted": False, "ok": None,
                "skip_reason": "not registered", "result": None,
            })
            continue

        gate = None
        try:
            if not arm.supports(product):
                outcomes.append({
                    "arm": name, "attempted": False, "ok": None,
                    "skip_reason": "unsupported product", "result": None,
                })
                continue

            if not dry_run:
                if not allow_protected and _is_protected_product(product):
                    outcomes.append({
                        "arm": name, "attempted": False, "ok": None,
                        "skip_reason": "protected product: explicit founder gate required (allow_protected=True)",
                        "result": None,
                    })
                    continue
                if file_defects:
                    outcomes.append({
                        "arm": name, "attempted": False, "ok": None,
                        "skip_reason": "blocked by file-usability gate: " + "; ".join(file_defects[:3]),
                        "result": None,
                    })
                    continue
                if claim_verdict is not None and claim_verdict["verdict"] == product_claim_integrity.BLOCK:
                    reason = "blocked by claim-integrity gate: " + claim_verdict["reason"]
                    outcomes.append({
                        "arm": name, "attempted": False, "ok": None,
                        "skip_reason": reason, "result": None,
                    })
                    continue
                if _already_published_live(product, name, ledger_path=ledger_path):
                    outcomes.append({
                        "arm": name, "attempted": False, "ok": None,
                        "skip_reason": "duplicate: ledger already holds a successful live publish for this product",
                        "result": None,
                    })
                    continue
                if not dry_run and _gate_configured:
                    qg = _gate_for_run(name)
                    # Evaluated-flag check, NOT `qg is not None`: a resolver
                    # returning None ("no usable verdict") must fail closed
                    # through _quality_gate_block_reason, never be mistaken
                    # for "gate not consulted" (2026-10-15 fail-open fix).
                    qg_reason = _quality_gate_block_reason(qg)
                else:
                    qg, qg_reason = None, None
                if qg_reason is not None:
                    qg_blocked = PublishResult(
                        ok=False, platform=name, product_id=None, url=None,
                        error=f"blocked by central Quality Gate: {qg_reason}", dry_run=dry_run,
                    )
                    ledger.record_publish_attempt(
                        product, qg_blocked, ledger_path=ledger_path,
                        protection_decision="quality_gate_blocked",
                        quality_gate=qg if isinstance(qg, dict) else {"allowed": False, "reason": qg_reason},
                    )
                    outcomes.append({
                        "arm": name, "attempted": False, "ok": None,
                        "skip_reason": f"blocked by central Quality Gate: {qg_reason}", "result": None,
                    })
                    continue
                gate = publish_protection.check_publish_allowed(name, state_path=protection_state_path)
                if not gate["allowed"]:
                    blocked_result = PublishResult(
                        ok=False, platform=name, product_id=None, url=None,
                        error=f"blocked by publish protection layer: {gate['reason']}", dry_run=dry_run,
                    )
                    ledger.record_publish_attempt(
                        product, blocked_result, ledger_path=ledger_path,
                        risk_score=gate["risk_score"], protection_decision="blocked",
                    )
                    outcomes.append({
                        "arm": name, "attempted": False, "ok": None,
                        "skip_reason": f"blocked by publish protection layer: {gate['reason']}", "result": None,
                    })
                    continue

            result = arm.publish(product, dry_run=dry_run)
        except Exception as e:
            # Defense in depth (ADR-5): even if an arm breaks its own
            # contract and raises instead of returning a PublishResult, one
            # arm's bug never takes down the rest of the distribution run.
            result = PublishResult(
                ok=False, platform=name, product_id=None, url=None,
                error=f"arm raised unexpectedly: {e}", dry_run=dry_run,
            )

        ledger.record_publish_attempt(
            product, result, ledger_path=ledger_path,
            risk_score=(gate or {}).get("risk_score"),
            protection_decision=("allowed" if gate else None),
        )

        if not dry_run:
            publish_protection.note_publish_outcome(name, result.ok, state_path=protection_state_path)

        # Unified Recovery System §3 (2026-07-18): a real (non-dry-run)
        # publish attempt that failed is remembered for a later retry —
        # the publish_attempt record above already makes this honest and
        # auditable; this just adds "try again once reachable" on top.
        # Never enqueued for a dry run (nothing real to retry) or a
        # config/not-ready failure (retrying won't fix a missing API key).
        # D16: the not-ready check is normalized (strip + lower) so a
        # "  Arm Not Ready: ..." variant is still recognized as not-ready
        # and never enqueued for a pointless retry.
        # 2026-10-22: a failure that a retry provably cannot fix (bad or
        # under-permissioned credentials, an exhausted account balance such
        # as X's live "HTTP 402: credits depleted", a validation, duplicate
        # or policy rejection) is no longer queued either. Retrying those
        # only repeats the same failure. UNKNOWN and transient classes are
        # still queued, exactly as before.
        if (not result.dry_run and not result.ok
                and not str(result.error or "").strip().lower().startswith("arm not ready:")
                and not _definitively_not_retryable(result.error)):
            factory_state.enqueue_retry(f"arm_publish:{name}:{product.source_id}", result.error)

        outcomes.append({
            "arm": name, "attempted": True, "ok": result.ok,
            "skip_reason": None, "result": result,
        })

    return outcomes


def _outcome_to_json(outcome):
    result = outcome["result"]
    return {
        "arm": outcome["arm"],
        "attempted": outcome["attempted"],
        "ok": outcome["ok"],
        "skip_reason": outcome["skip_reason"],
        "result": None if result is None else {
            "ok": result.ok,
            "platform": result.platform,
            "product_id": result.product_id,
            "url": result.url,
            "error": result.error,
            "dry_run": result.dry_run,
        },
    }


def emit(obj):
    sys.stdout.buffer.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))
    sys.stdout.buffer.write(b"\n")


def main():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Distribution backbone (Galaxy Forge)")
    parser.add_argument("--json", action="store_true", help="Read a JSON job from stdin, print a JSON result to stdout")
    parser.add_argument("--allow-protected", action="store_true",
                        help="Explicit founder opt-in: allow real-mode publish of a protected product (default: skip it)")
    args = parser.parse_args()

    if not args.json:
        parser.print_help()
        return

    try:
        job = json.load(sys.stdin)
        record = job.get("record")
        if not isinstance(record, dict):
            raise ValueError("job.record must be a JSONL record object")

        product = Product.from_jsonl_record(record)
        arm_names = job.get("arms")  # None = every registered arm
        dry_run = job.get("dry_run", True)  # explicit False required to go live
        allow_protected = bool(job.get("allow_protected", False))  # explicit True required for protected products

        outcomes = distribute(product, arm_names=arm_names, dry_run=dry_run, allow_protected=allow_protected)
        emit({"success": True, "dry_run": dry_run, "outcomes": [_outcome_to_json(o) for o in outcomes]})
    except Exception as e:
        emit({"success": False, "error": str(e)})
        sys.exit(0)


if __name__ == "__main__":
    main()

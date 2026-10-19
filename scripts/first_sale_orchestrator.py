#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""First-Sale Orchestrator (Cycle 118).

ROOT CAUSE THIS MODULE REPAIRS
------------------------------
Cycles 109-116 each re-derived state by hand, produced a report, hit a blocked
step, and handed the *rest* of the pipeline to the founder. The factory already
has an orchestrator (`orchestrator/`) and a state manager (`factory_state.py`),
but both are wired to the Golden Hunter *production* pipeline -- there was no
orchestrator for the *commercial / first-sale* path. That absence is the
repeated founder-dependency: nothing classified a blocker, nothing kept running
the independent work, and nothing distinguished "our code is incomplete"
(repairable) from "the platform cannot do this" (external) from "only the
founder can authorize this" (authority).

WHAT IT DOES
------------
A small, bounded, auditable task orchestrator over a persistent JSON state
file, in the same atomic-write style as `factory_state.py`. It:
  * keeps one task per concrete first-sale step, with a real status;
  * runs every currently-eligible task, simplest first;
  * never re-runs a completed task without a reason;
  * resumes safely after interruption;
  * classifies failures (transient / authorization / capability / founder /
    permanent / uncertain) and retries only transient ones, with bounded
    backoff;
  * refuses to re-issue a consequential external action whose outcome is
    unknown (reconciliation, never a blind retry);
  * chooses the next action automatically, and keeps independent tasks moving
    even when one is blocked;
  * makes progress observable (`--status`).

It performs NO network activity on the default path and NEVER publishes,
creates a live product, or spends. The one external task (`create_draft`) is
capability-blocked and refuses by default.

This is local orchestration only. A green local run is NOT evidence of remote
commercial success.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

FACTORY_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = FACTORY_DIR / "scripts"
STATE_PATH = FACTORY_DIR / "data" / "first_sale_tasks.json"

# ---------------------------------------------------------------------------
# Statuses / blocker kinds / work kinds
# ---------------------------------------------------------------------------
PENDING = "PENDING"
EXECUTABLE = "EXECUTABLE"
RUNNING = "RUNNING"
COMPLETED = "COMPLETED"
BLOCKED = "BLOCKED"
EXTERNALLY_VERIFIED = "EXTERNALLY_VERIFIED"
FAILED_RETRYABLE = "FAILED_RETRYABLE"
NEEDS_RECONCILIATION = "NEEDS_RECONCILIATION"

BLOCKER_DEPENDENCY = "BLOCKED_BY_DEPENDENCY"
BLOCKER_EXTERNAL_CAPABILITY = "BLOCKED_BY_EXTERNAL_CAPABILITY"
BLOCKER_AUTHORIZATION = "BLOCKED_BY_AUTHORIZATION"
BLOCKER_FOUNDER_AUTHORITY = "BLOCKED_BY_FOUNDER_AUTHORITY"
BLOCKER_TRANSIENT_EXHAUSTED = "BLOCKED_BY_TRANSIENT_EXHAUSTED"
BLOCKER_RECONCILIATION = "NEEDS_RECONCILIATION"
BLOCKER_PERMANENT = "BLOCKED_PERMANENT"

# The four work classes from the cycle directive.
WORK_AUTONOMOUS = "AUTONOMOUS"
WORK_ENGINEERING = "ENGINEERING"
WORK_EXTERNAL_CAPABILITY = "EXTERNAL_CAPABILITY"
WORK_FOUNDER_AUTHORITY = "FOUNDER_AUTHORITY"

# Draft-creation capability states (directive's exact vocabulary).
CAP_SUPPORTED_AND_IMPLEMENTED = "SUPPORTED_AND_IMPLEMENTED"
CAP_DOCUMENTED_BUT_NOT_IMPLEMENTED = "DOCUMENTED_BUT_NOT_IMPLEMENTED"
CAP_IMPLEMENTED_BUT_REMOTE_BEHAVIOR_UNVERIFIED = "IMPLEMENTED_BUT_REMOTE_BEHAVIOR_UNVERIFIED"
CAP_UNSUPPORTED_BY_AVAILABLE_PLATFORM_CAPABILITY = "UNSUPPORTED_BY_AVAILABLE_PLATFORM_CAPABILITY"
CAP_BLOCKED_BY_AUTHORIZATION = "BLOCKED_BY_AUTHORIZATION"
CAP_UNKNOWN = "UNKNOWN"

# Price bases this factory treats as authoritative when recorded with a dated
# founder decision in the product manifest / gate record.
AUTHORIZED_PRICE_BASES = (
    "FOUNDER_DECISION_BELOW_COMPARABLE",
    "FOUNDER_APPROVED_BELOW_COMPARABLE_2026-10-18",
    "MARKET_MINUS_10_PERCENT",
    "MARGIN_FLOOR",
)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class TaskError(Exception):
    blocker = BLOCKER_PERMANENT


class TransientError(TaskError):
    """Network/timeout-style failure -- retryable under a bounded policy."""


class AuthorizationError(TaskError):
    blocker = BLOCKER_AUTHORIZATION


class CapabilityError(TaskError):
    blocker = BLOCKER_EXTERNAL_CAPABILITY


class FounderAuthorityError(TaskError):
    """A task waiting on explicit founder authorization.

    ``ctx_key``/``required`` (both optional) record *which* authorization was
    missing when the task blocked, so a later run can re-open it if and only
    if that exact authorization has since arrived. See
    ``reset_founder_authority()``.
    """
    blocker = BLOCKER_FOUNDER_AUTHORITY

    def __init__(self, message, ctx_key=None, required=None):
        super().__init__(message)
        self.ctx_key = ctx_key
        self.required = required


class PermanentError(TaskError):
    blocker = BLOCKER_PERMANENT


class UncertainOutcomeError(TaskError):
    """A consequential external action was sent but its result is unknown."""


# ---------------------------------------------------------------------------
# Time / id helpers
# ---------------------------------------------------------------------------
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse(ts):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def _new_run_id() -> str:
    return f"{os.getpid()}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"


_MAX_BACKOFF_SECONDS = 3600


def _backoff_seconds(attempt: int) -> int:
    if attempt <= 1:
        return 0
    return min(60 * (2 ** (attempt - 2)), _MAX_BACKOFF_SECONDS)


# ---------------------------------------------------------------------------
# Persistent state (atomic, factory_state.py's pattern)
# ---------------------------------------------------------------------------
def _task(tid, title, kind, depends=None, external=False, max_attempts=3):
    return {
        "id": tid,
        "title": title,
        "kind": kind,
        "depends_on": list(depends or []),
        "external": bool(external),
        "max_attempts": max_attempts,
        "status": PENDING,
        "blocker": None,
        "attempts": 0,
        "last_error": None,
        "last_error_kind": None,
        "authority_requirement": None,
        "next_retry_at": None,
        "run_id": None,
        "result": None,
        "updated_at": None,
    }


def build_task_graph(product=None):
    """The concrete first-sale pipeline as tasks. Ordering is by dependency."""
    pid = product or "B12-001"
    return [
        _task("package_validate", f"Validate {pid} package (sha/size/cover)", WORK_AUTONOMOUS),
        _task("price_authority", f"Confirm {pid} price is authorized", WORK_AUTONOMOUS),
        _task("catalog_duplicate_check", "Read-only duplicate scan of the live catalog", WORK_AUTONOMOUS),
        _task("draft_capability", "Determine draft-creation capability state", WORK_ENGINEERING),
        _task("create_draft", "Create the unpublished Gumroad draft",
              WORK_EXTERNAL_CAPABILITY,
              depends=["package_validate", "price_authority", "catalog_duplicate_check", "draft_capability"],
              external=True, max_attempts=1),
        _task("verify_remote_draft", "Verify the draft is unpublished and matches",
              WORK_AUTONOMOUS, depends=["create_draft"], external=True, max_attempts=1),
        _task("resolve_utm", "Resolve UTM links against the verified draft URL",
              WORK_AUTONOMOUS, depends=["verify_remote_draft"]),
        _task("sales_ledger_check", "Reconcile sales / refunds (read-only)", WORK_AUTONOMOUS),
        _task("journey_check", "Validate the customer page state (read-only)", WORK_AUTONOMOUS),
        _task("publish", f"Publish {pid} (requires founder phrase)",
              WORK_FOUNDER_AUTHORITY, depends=["verify_remote_draft"]),
    ]


def default_state():
    return {
        "run_id": None,
        "tasks": {t["id"]: t for t in build_task_graph()},
        "events": [],
        "next_action": None,
        "updated_at": None,
    }


def _state_path():
    env = os.environ.get("FIRST_SALE_TASKS_PATH")
    return Path(env) if env else STATE_PATH


def load_state(path=None):
    p = Path(path) if path else _state_path()
    if not p.exists():
        return default_state()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default_state()
    if not isinstance(data, dict) or not isinstance(data.get("tasks"), dict):
        return default_state()
    # Merge in any task added to the graph since this state was written.
    base = default_state()
    for tid, t in base["tasks"].items():
        data["tasks"].setdefault(tid, t)
    data.setdefault("events", [])
    data.setdefault("run_id", None)
    data.setdefault("next_action", None)
    return data


def save_state(state, path=None):
    p = Path(path) if path else _state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now()
    tmp = p.parent / f"{p.name}.tmp-{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, p)
    return state


# ---------------------------------------------------------------------------
# Lazy import of the draft orchestrator (paths differ when run as a script)
# ---------------------------------------------------------------------------
def _load_gdo():
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(
        "gumroad_draft_orchestrator", SCRIPTS_DIR / "gumroad_draft_orchestrator.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gumroad_draft_orchestrator"] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Capability + price authority
# ---------------------------------------------------------------------------
DRAFT_EVIDENCE_PATH = FACTORY_DIR / "data" / "first_sale_draft_evidence.json"
PUBLISH_PHRASE = "APPROVE B12-001 PUBLISH"

# ---------------------------------------------------------------------------
# Per-product commercial config (Cycle 98).
#
# The historical orchestrator was hard-coded to B12-001. The create inputs live
# in the shared `gumroad_draft_orchestrator.PROFILES` registry; this table adds
# only the *first-sale-path* locations that are specific to this orchestrator.
# `product_config(None)` resolves to B12-001, so every existing behavior is
# preserved exactly.
# ---------------------------------------------------------------------------
_EXTRA = {
    "B12-001": {
        "gate": FACTORY_DIR / "reports" / "B12-001" / "GATE_FINAL_2026-10-17.json",
        "customer_page": FACTORY_DIR / "customer_site" / "b12-freelancer-rate-calculator.html",
        "evidence": DRAFT_EVIDENCE_PATH,
        "listing_copy": FACTORY_DIR / "reports" / "B12-001" / "listing_copy.prepared.md",
        "listing_evidence": FACTORY_DIR / "data" / "first_sale_listing_update_evidence.json",
        "utm_template": FACTORY_DIR / "reports" / "B12-001" / "utm_links.json",
        "utm_resolved": FACTORY_DIR / "reports" / "B12-001" / "utm_links.resolved.json",
        "cover_evidence": FACTORY_DIR / "data" / "first_sale_cover_evidence.json",
        # B12-001's prepared description clears the legacy 300-word bar.
        "min_description_words": 300,
    },
    "B12-004": {
        "gate": FACTORY_DIR / "reports" / "B12-004" / "GATE_FINAL_2026-10-18.json",
        "customer_page": FACTORY_DIR / "customer_site" / "b12-meeting-cost-calculator.html",
        "evidence": FACTORY_DIR / "data" / "first_sale_draft_evidence_b12_004.json",
        "listing_copy": FACTORY_DIR / "drafts" / "b12_004_listing_copy.txt",
        "listing_evidence": FACTORY_DIR / "data" / "first_sale_listing_update_evidence_b12_004.json",
        "utm_template": None,
        "utm_resolved": FACTORY_DIR / "reports" / "B12-004" / "utm_links.resolved.json",
        "cover_evidence": FACTORY_DIR / "data" / "first_sale_cover_evidence_b12_004.json",
        # B12-004's founder-authored copy is 233 words: a complete one-page
        # listing, below B12-001's legacy 300-word bar. Disclosed per-product
        # floor (still well above a thin stub); B12-001's 300 is unchanged.
        "min_description_words": 200,
    },
    "B12-003": {
        "gate": FACTORY_DIR / "reports" / "B12-003" / "GATE_FINAL_2026-10-19.json",
        "customer_page": FACTORY_DIR / "customer_site" / "b12-access-continuity-organizer.html",
        "evidence": FACTORY_DIR / "data" / "first_sale_draft_evidence_b12_003.json",
        "listing_copy": FACTORY_DIR / "drafts" / "b12_003_listing_copy.txt",
        "listing_evidence": FACTORY_DIR / "data" / "first_sale_listing_update_evidence_b12_003.json",
        "utm_template": None,
        "utm_resolved": FACTORY_DIR / "reports" / "B12-003" / "utm_links.resolved.json",
        "cover_evidence": FACTORY_DIR / "data" / "first_sale_cover_evidence_b12_003.json",
        # B12-003's listing copy is 346 words -- above B12-001's 300-word bar,
        # so it uses the same floor (no per-product relaxation needed).
        "min_description_words": 300,
    },
}


def product_config(product=None) -> dict:
    """Merge a product's create profile with its first-sale path table."""
    gdo = _load_gdo()
    profile = gdo.get_profile(product)  # raises gdo.DraftBlocked on an unknown id
    pid = profile["id"]
    cfg = dict(profile)
    cfg.update(_EXTRA.get(pid, {}))
    cfg["id"] = pid
    cfg["phrase"] = f"APPROVE {pid} PUBLISH"
    return cfg


def publish_phrase(product=None) -> str:
    """The exact founder phrase for a product (B12-001 by default)."""
    return product_config(product)["phrase"]


def _expected_price_for_path(p) -> int:
    """The price a recorded evidence file for this path must carry.

    Resolves the path against every known product's evidence path; an
    unrecognized path falls back to B12-001's $14.99 so ad-hoc temp files in
    tests keep the historical behavior."""
    try:
        key = str(Path(p).resolve())
    except Exception:  # noqa: BLE001
        key = str(p)
    for pid in sorted(set(_EXTRA) | {"B12-001"}):
        try:
            if str(Path(product_config(pid)["evidence"]).resolve()) == key:
                return int(product_config(pid)["price_cents"])
        except Exception:  # noqa: BLE001
            continue
    return 1499


def _evidence_path(path=None, product=None) -> Path:
    if path:
        return Path(path)
    if product:
        return Path(product_config(product)["evidence"])
    env = os.environ.get("FIRST_SALE_DRAFT_EVIDENCE_PATH")
    return Path(env) if env else DRAFT_EVIDENCE_PATH


def read_draft_evidence(path=None, product=None) -> dict:
    """Read a REAL, previously verified unpublished-draft observation."""
    p = _evidence_path(path, product=product)
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(d, dict) or not d.get("product_id"):
        return {}
    if d.get("published") is not False:
        return {}
    try:
        if int(d.get("price_cents", -1)) != _expected_price_for_path(p):
            return {}
    except (TypeError, ValueError):
        return {}
    return d


def record_draft_evidence(product: dict, path=None, product_id=None) -> dict:
    """Persist a real, verified unpublished-draft observation (atomic)."""
    p = _evidence_path(path, product=product_id)
    fallback = _expected_price_for_path(p)
    payload = {
        "product_id": product.get("id"),
        "title": product.get("name"),
        "price_cents": int(product.get("price", fallback)),
        "published": product.get("published"),
        "url": product.get("short_url") or product.get("url"),
        "verified_at": _now(),
        "source": "create response + GET read-back (OBSERVED)",
    }
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.parent / f"{p.name}.tmp-{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, p)
    return payload


def live_flag_enabled() -> bool:
    return str(os.environ.get("FACTORY_LIVE_PUBLISH", "")).strip().lower() in (
        "1", "true", "yes", "on")


def _write_authorized(operation="create_product") -> bool:
    """Pure check against the central fail-closed write gate."""
    try:
        if str(FACTORY_DIR) not in sys.path:
            sys.path.insert(0, str(FACTORY_DIR))
        from channels import write_gate
        return bool(write_gate.check_write_authorization(operation).allowed)
    except Exception:  # noqa: BLE001 -- any failure means deny
        return False


def _real_disable_fn(token, product_id):
    """Revert a listing to unpublished via the DOCUMENTED route
    `PUT /v2/products/:id/disable` (live-verified by an earlier cycle; the
    same verb as `enable`). Never invents an endpoint, never retries blindly,
    and always confirms the change with a read-back."""
    if str(FACTORY_DIR) not in sys.path:
        sys.path.insert(0, str(FACTORY_DIR))
    from channels import gumroad_publisher as gp

    r = gp._request_with_retry(
        "PUT", f"{gp.GUMROAD_API_BASE}/products/{product_id}/disable",
        data={"access_token": token}, timeout=60)
    try:
        body = r.json()
    except Exception:  # noqa: BLE001
        raise UncertainOutcomeError(f"disable returned non-JSON: HTTP {r.status_code}")
    if r.status_code != 200 or not isinstance(body, dict) or body.get("success") is not True:
        raise PermanentError(f"disable failed: HTTP {r.status_code} {str(body)[:200]}")
    fresh = gp.get_product(token, product_id)
    if not isinstance(fresh, dict) or fresh.get("published") is not False:
        raise UncertainOutcomeError("disable not confirmed by read-back")
    return {"disabled": True, "product_id": product_id, "published": False}


def _rollback(reason="manual rollback", product=None):
    """Founder/operator-triggered revert to unpublished. Requires the live
    write gate; never runs automatically."""
    ev_path = _evidence_path(product=product) if product else None
    evidence = read_draft_evidence(ev_path) if ev_path else read_draft_evidence()
    if not evidence:
        raise PermanentError("no recorded draft evidence to roll back")
    if not live_flag_enabled() or not _write_authorized("create_product"):
        raise AuthorizationError(
            "rollback requires FACTORY_LIVE_PUBLISH=true and a fresh VERIFIED "
            "auth state (write gate)")
    if str(FACTORY_DIR) not in sys.path:
        sys.path.insert(0, str(FACTORY_DIR))
    from channels import gumroad_publisher as gp
    return _real_disable_fn(gp.load_token(), evidence["product_id"])


def _real_create_draft_fn(ctx):
    """The real, fail-closed create. Only reachable when capability is
    SUPPORTED_AND_IMPLEMENTED and explicit draft authorization is supplied."""
    gdo = _load_gdo()
    if str(FACTORY_DIR) not in sys.path:
        sys.path.insert(0, str(FACTORY_DIR))
    from channels import gumroad_publisher as gp

    if ctx.get("dry_run") is not False:
        raise PermanentError("live create requires ctx['dry_run'] is False")

    product = ctx.get("product")
    pid = product or "B12-001"
    slug = gdo.get_profile(pid).get("slug") or pid.lower()
    token = gp.load_token()
    spec = gdo.build_spec(product)

    def post(url, data):
        r = gp._request_with_retry("POST", url, data=data, timeout=120)
        try:
            return r.json()
        except Exception:  # noqa: BLE001
            raise gdo.DraftBlocked(f"non-JSON create response: HTTP {r.status_code}")

    def _scope_for(path):
        # The upload helper fails closed without a single-use scope bound to
        # this exact file. Mint one for this one upload only; it is consumed
        # by the call below and can never be replayed.
        from channels import write_scope
        return write_scope.issue_scope(
            product_id=gp.NEW_PRODUCT,
            slug=slug,
            payload={"file_path": str(path)},
            operation="upload_file",
            note=f"{pid} first verified draft create (founder-authorized)",
        )

    def upload(t, s):
        scope = _scope_for(s["file_path"])
        return gp._upload_file(t, s["file_path"], scope_id=scope.scope_id,
                               product_id=gp.NEW_PRODUCT)

    def upload_many(t, s, paths):
        urls = []
        for path in paths:
            scope = _scope_for(path)
            urls.append(gp._upload_file(t, path, scope_id=scope.scope_id,
                                        product_id=gp.NEW_PRODUCT))
        return urls

    try:
        res = gdo.create_draft_live(
            token, spec,
            list_products_fn=lambda: gp.list_products(token),
            get_product_fn=gp.get_product,
            post_fn=post,
            upload_fn=upload,
            upload_many_fn=upload_many,
            disable_fn=lambda t, pid_: _real_disable_fn(t, pid_),
            draft_authorized=True,
        )
    except gdo.DraftBlocked as exc:
        msg = str(exc)
        if "UNCERTAIN" in msg or "CREATED_BUT_STATE_UNVERIFIED" in msg:
            raise UncertainOutcomeError(msg)
        raise PermanentError(msg)

    created = (res or {}).get("product") or {}
    evidence = record_draft_evidence(created, product_id=product) if product \
        else record_draft_evidence(created)
    return {"created": True, "state": (res or {}).get("state"), "draft": evidence}


def _real_verify_draft(ctx, evidence):
    """Read-only read-back of the recorded draft."""
    if str(FACTORY_DIR) not in sys.path:
        sys.path.insert(0, str(FACTORY_DIR))
    from channels import gumroad_publisher as gp

    product = ctx.get("product")
    expected_price = int(product_config(product)["price_cents"]) if product else 1499
    token = gp.load_token()
    pid = evidence.get("product_id")
    fresh = gp.get_product(token, pid)
    if not isinstance(fresh, dict):
        return {"verified": False, "reason": "read-back returned no product"}
    problems = []
    if fresh.get("published") is not False:
        problems.append("read-back published != false")
    if str(fresh.get("id")) != str(pid):
        problems.append("id mismatch")
    try:
        if int(float(fresh.get("price"))) != expected_price:
            problems.append("price mismatch")
    except (TypeError, ValueError):
        problems.append("price unreadable")
    return {
        "verified": not problems,
        "problems": problems,
        "product_id": pid,
        "url": fresh.get("short_url") or fresh.get("url"),
        "externally_verified": not problems,
    }


def _assert_listing_copy_is_live(gp, token, product_id, product=None) -> dict:
    """Durable pre-publish guard (Cycle 99).

    Refuse to publish a listing whose prepared description/tags are not
    actually live. The mis-sequenced 2026-10-19 run published B12-003 before
    `--apply-listing` had run, leaving a live listing with zero tags. This makes
    "publish a half-configured listing" impossible for every product.

    Raises CapabilityError -- a re-checkable block -- so the run simply retries
    once the listing copy is applied, rather than a permanent, hand-editable
    block.
    """
    try:
        _, prepared_tags = _prepared_listing_copy(product)
    except TaskError:
        # No prepared copy for this product -> preserve the historical behaviour.
        return {"checked": False, "reason": "no prepared listing copy"}
    live = gp.get_product(token, product_id)
    if not isinstance(live, dict):
        raise UncertainOutcomeError("could not read the listing back before publishing")
    live_tags = set(live.get("tags") or [])
    missing = sorted(set(prepared_tags) - live_tags)
    try:
        min_words = int(product_config(product).get("min_description_words") or 0)
    except Exception:  # noqa: BLE001
        min_words = 0
    live_words = len((live.get("description") or "").split())
    if missing or (min_words and live_words < min_words):
        raise CapabilityError(
            "refusing to publish: the prepared listing copy is not live yet "
            f"(missing_tags={missing}, description_words={live_words}"
            + (f", required>={min_words}" if min_words else "")
            + "); run --apply-listing first")
    return {"checked": True, "tags": sorted(live_tags), "description_words": live_words}


def republish(product=None, publish_authorization=None) -> dict:
    """Re-enable an existing, verified listing via the DOCUMENTED route.

    The counterpart to `--rollback`: after a rollback (disable) the listing can
    be brought back live without creating a second product. Requires BOTH the
    live write gate and the exact per-product phrase, and shares
    `_real_publish_fn`'s guards -- including the listing-copy precheck -- so a
    republish can never go out ahead of the listing copy.
    """
    phrase = publish_phrase(product) if product else PUBLISH_PHRASE
    if publish_authorization != phrase:
        raise FounderAuthorityError(f"republish requires '{phrase}'",
                                    ctx_key="publish_authorization", required=phrase)
    if not live_flag_enabled() or not _write_authorized("create_product"):
        raise AuthorizationError(
            "republish requires FACTORY_LIVE_PUBLISH=true and a fresh VERIFIED "
            "auth state (write gate)")
    return _real_publish_fn({"product": product,
                             "publish_authorization": publish_authorization})


def _real_publish_fn(ctx):
    """Publish an already-verified draft. Only reachable with the exact phrase."""
    product = ctx.get("product")
    phrase = publish_phrase(product) if product else PUBLISH_PHRASE
    if ctx.get("publish_authorization") != phrase:
        raise FounderAuthorityError(f"requires '{phrase}'",
                                    ctx_key="publish_authorization", required=phrase)
    ev_path = _evidence_path(product=product) if product else None
    evidence = read_draft_evidence(ev_path) if ev_path else read_draft_evidence()
    if not evidence:
        raise PermanentError("no verified draft evidence to publish")
    if str(FACTORY_DIR) not in sys.path:
        sys.path.insert(0, str(FACTORY_DIR))
    from channels import gumroad_publisher as gp

    token = gp.load_token()
    pid = evidence["product_id"]
    _assert_listing_copy_is_live(gp, token, pid, product)
    try:
        gp.enable_product(token, pid)
    except Exception as exc:  # noqa: BLE001
        raise UncertainOutcomeError(f"publish call failed/ambiguous: {exc!r}")
    fresh = gp.get_product(token, pid)
    if not isinstance(fresh, dict) or fresh.get("published") is not True:
        raise UncertainOutcomeError("publish outcome unverified; reconcile before retry")
    return {
        "published": True,
        "product_id": pid,
        "url": fresh.get("short_url") or fresh.get("url"),
        "externally_verified": True,
    }


def draft_capability_state(evidence_path=None) -> dict:
    """Map the draft orchestrator's findings onto the directive's vocabulary."""
    gdo = _load_gdo()
    cap = gdo.draft_creation_capability()
    documented = bool(cap.get("platform_documented"))
    implemented = True  # create_draft_live() exists in gumroad_draft_orchestrator.py
    evidence = read_draft_evidence(evidence_path)
    remote_verified = bool(cap.get("live_verified") or evidence)
    authorized = bool(live_flag_enabled() and _write_authorized("create_product"))

    if not documented:
        state = CAP_UNSUPPORTED_BY_AVAILABLE_PLATFORM_CAPABILITY
    elif not implemented:
        state = CAP_DOCUMENTED_BUT_NOT_IMPLEMENTED
    elif not remote_verified:
        state = CAP_IMPLEMENTED_BUT_REMOTE_BEHAVIOR_UNVERIFIED
    elif not authorized:
        state = CAP_BLOCKED_BY_AUTHORIZATION
    else:
        state = CAP_SUPPORTED_AND_IMPLEMENTED

    return {
        "state": state,
        "authorization": (CAP_BLOCKED_BY_AUTHORIZATION if not authorized else "AUTHORIZED"),
        "documented": documented,
        "implemented": implemented,
        "remote_verified": remote_verified,
        "evidence": evidence or None,
        "required_guarantees": cap.get("required_guarantees"),
        "documented_reversibility": cap.get("documented_reversibility"),
        "unknowns": cap.get("unknowns"),
        "reason": cap.get("reason"),
    }


def price_authority(manifest_path=None, gate_path=None, product=None) -> dict:
    """Read the authoritative price from the manifest + gate record (no network)."""
    pid = product or "B12-001"
    mp = Path(manifest_path) if manifest_path else FACTORY_DIR / "data" / "product_batch_12.json"
    gp = Path(gate_path) if gate_path else Path(product_config(pid)["gate"])
    out = {"authorized": False, "price_usd": None, "basis": None, "sources": []}
    try:
        manifest = json.loads(mp.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        out["reason"] = f"manifest unreadable: {e!r}"
        return out
    product_entry = next((p for p in manifest.get("products", []) if p.get("id") == pid), None)
    if not product_entry:
        out["reason"] = f"{pid} not present in manifest"
        return out
    basis = product_entry.get("price_basis")
    price = product_entry.get("price_usd", product_entry.get("price"))
    out["basis"] = basis
    out["price_usd"] = price
    out["sources"].append(str(mp))
    if basis not in AUTHORIZED_PRICE_BASES:
        out["reason"] = f"price_basis {basis!r} is not an authorized basis"
        return out
    if not product_entry.get("pricing_date"):
        out["reason"] = "authorized basis but no dated pricing decision"
        return out
    try:
        gate = json.loads(gp.read_text(encoding="utf-8"))
        verdict = str(gate.get("verdict", ""))
        if verdict.upper().startswith("APPROVED"):
            out["sources"].append(str(gp))
        else:
            out["reason"] = f"gate verdict is {verdict!r}, not APPROVED"
            return out
    except (OSError, json.JSONDecodeError):
        out["reason"] = "gate record unreadable"
        return out
    out["authorized"] = True
    return out


# ---------------------------------------------------------------------------
# Workbook structural validation (Phase 7) -- local, no network
# ---------------------------------------------------------------------------
EXPECTED_RECALC = {
    "Inputs!D8": 120285.714286,
    "Inputs!D9": 104.60,
    "Inputs!D10": 120.29,
    "RaisePlanner!D2": 132.31,
    "RaisePlanner!D3": 138.33,
}


def _workbook_validate_profile(gdo, product) -> dict:
    """Structural validation of a non-B12-001 product's primary workbook file.

    Pins the profile's own sha256/size and confirms the file opens and carries
    formulas. Product-specific sheet names / recalculated values are honestly
    NOT checked here (no per-product expectation is recorded in the profile)."""
    profile = gdo.get_profile(product)
    primary = profile["files"][0]
    expected = (profile.get("expected") or {}).get(primary) or {}
    out = {
        "path": str(primary),
        "sha256": None,
        "bytes": None,
        "sheets": [],
        "formula_cells": None,
        "cached_verification": "NOT_CHECKED_FOR_PRODUCT",
        "checks": [],
    }

    def add(name, ok, detail):
        out["checks"].append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    p = Path(primary)
    add("workbook exists", p.is_file(), str(p))
    if not p.is_file():
        out["structural_ok"] = False
        return out
    raw = p.read_bytes()
    import hashlib
    out["sha256"] = hashlib.sha256(raw).hexdigest()
    out["bytes"] = len(raw)
    if expected.get("sha256"):
        add("sha256 matches profile", out["sha256"] == expected["sha256"], out["sha256"][:16] + "...")
    if expected.get("bytes"):
        add("size matches profile", len(raw) == expected["bytes"], f"{len(raw)} bytes")
    try:
        import openpyxl
        wb = openpyxl.load_workbook(p, data_only=False)
    except Exception as exc:  # noqa: BLE001
        out["reason"] = f"workbook did not open: {exc!r}"
        add("workbook opens", False, repr(exc))
        out["structural_ok"] = False
        return out
    out["sheets"] = list(wb.sheetnames)
    formulas = 0
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    formulas += 1
    out["formula_cells"] = formulas
    add("formula cells present", formulas > 0, f"{formulas} formula cells")
    out["structural_ok"] = all(c["status"] != "FAIL" for c in out["checks"])
    return out


def workbook_validate(workbook=None, product=None) -> dict:
    """Validate the B12-001 workbook structurally, without inventing anything.

    openpyxl can read formulas but cannot calculate them. If the file carries no
    cached calculated values, the recalculation check is reported as honestly
    UNVERIFIED -- the prior real evidence is a C114 Excel COM recalculation,
    cited, never re-fabricated.

    For a non-B12-001 product the file is validated against that product's own
    pinned sha256/size; the B12-001 sheet-name/recalc expectations (which are
    product-specific) are not applied.
    """
    gdo = _load_gdo()
    if product and product != "B12-001":
        return _workbook_validate_profile(gdo, product)
    p = Path(workbook) if workbook else gdo.WORKBOOK
    out = {
        "path": str(p),
        "sha256": None,
        "bytes": None,
        "sheets": [],
        "formula_cells": None,
        "expected_sheets": ["Inputs", "ClientMix", "RaisePlanner", "README"],
        "cached_values": "UNKNOWN",
        "cached_verification": "NOT_VERIFIED",
        "expected_recalc": dict(EXPECTED_RECALC),
        "prior_recalc_evidence": "C114 Excel COM recalculation (Inputs!D9=$104.60, RaisePlanner!D2=$132.31)",
        "checks": [],
    }

    def add(name, ok, detail):
        out["checks"].append({
            "check": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    add("workbook exists", p.is_file(), str(p))
    if not p.is_file():
        out["structural_ok"] = False
        return out

    raw = p.read_bytes()
    import hashlib
    sha = hashlib.sha256(raw).hexdigest()
    out["sha256"] = sha
    out["bytes"] = len(raw)
    add("sha256 matches canonical", sha == gdo.WORKBOOK_SHA256, sha[:16] + "...")
    add("size matches canonical", len(raw) == gdo.WORKBOOK_BYTES, f"{len(raw)} bytes")

    try:
        import openpyxl
    except ImportError:
        out["reason"] = "openpyxl not installed; structural checks incomplete"
        out["structural_ok"] = False
        return out

    try:
        wb = openpyxl.load_workbook(p, data_only=False)
    except Exception as exc:  # noqa: BLE001
        out["reason"] = f"workbook did not open: {exc!r}"
        add("workbook opens", False, repr(exc))
        out["structural_ok"] = False
        return out

    out["sheets"] = list(wb.sheetnames)
    add("expected sheets", wb.sheetnames == out["expected_sheets"], str(wb.sheetnames))

    formulas = 0
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    formulas += 1
    out["formula_cells"] = formulas
    add("formula cells present", formulas > 0, f"{formulas} formula cells")

    try:
        wb_cached = openpyxl.load_workbook(p, data_only=True)
        observed = {}
        for ref in EXPECTED_RECALC:
            sheet, cell = ref.split("!")
            observed[ref] = wb_cached[sheet][cell].value
        out["cached_values"] = observed
        if all(v is None for v in observed.values()):
            out["cached_verification"] = "UNVERIFIED_NO_CACHED_VALUES"
            out["checks"].append({
                "check": "recalculated values", "status": "UNKNOWN",
                "detail": "no cached values in file; openpyxl cannot calculate "
                          "(prior C114 Excel COM evidence cited instead)"})
        else:
            mismatches = []
            for ref, want in EXPECTED_RECALC.items():
                got = observed.get(ref)
                if got is None or abs(float(got) - want) > 0.01:
                    mismatches.append(f"{ref}: {got!r} != {want}")
            out["cached_verification"] = "VERIFIED" if not mismatches else "MISMATCH"
            add("recalculated values", not mismatches, "; ".join(mismatches) or "all match")
    except Exception as exc:  # noqa: BLE001
        out["cached_verification"] = "UNVERIFIED_READ_ERROR"
        out["checks"].append({
            "check": "recalculated values", "status": "UNKNOWN", "detail": repr(exc)})

    out["structural_ok"] = all(c["status"] != "FAIL" for c in out["checks"])
    return out


# ---------------------------------------------------------------------------
# UTM links (Phase 8) -- resolves the real Plan against a verified base URL
# ---------------------------------------------------------------------------
UTM_TEMPLATE_PATH = FACTORY_DIR / "reports" / "B12-001" / "utm_links.json"
UTM_RESOLVED_PATH = FACTORY_DIR / "reports" / "B12-001" / "utm_links.resolved.json"


def _utm_source():
    try:
        return json.loads(UTM_TEMPLATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _valid_base_url(base_url) -> bool:
    if not base_url or "[base_url]" in str(base_url):
        return False
    from urllib.parse import urlsplit
    parts = urlsplit(str(base_url))
    return bool(parts.scheme in ("http", "https") and parts.netloc)


def build_utm_map(base_url) -> dict:
    """Return the resolved link map. Pure: never writes, never invents a slug."""
    if not _valid_base_url(base_url):
        raise PermanentError("a real, absolute base_url is required")
    src = _utm_source()
    links = src.get("utm_links", {})
    if not links:
        raise PermanentError("no UTM link template available")
    resolved = {}
    for key, entry in links.items():
        url = str(entry.get("url", ""))
        if not url:
            continue
        resolved[key] = {
            "url": url.replace("[base_url]", str(base_url)),
            "source": entry.get("source"),
            "use_case": entry.get("use_case"),
        }
    return {"base_url": str(base_url), "utm_links": resolved,
            "unresolved": [k for k, v in resolved.items() if "[base_url]" in v["url"]]}


def resolve_utm_links(base_url, out_path=None) -> dict:
    """Resolve the template to a NEW file. Never overwrites the source."""
    resolved = build_utm_map(base_url)
    dst = Path(out_path) if out_path else UTM_RESOLVED_PATH
    dst.parent.mkdir(parents=True, exist_ok=True)
    payload = {"product": "B12-001", "base_url": str(base_url),
               "utm_links": resolved["utm_links"],
               "note": "Generated by scripts/first_sale_orchestrator.py against a "
                       "verified listing URL. Source template left untouched."}
    tmp = dst.parent / f"{dst.name}.tmp-{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, dst)
    return {"resolved": len(resolved["utm_links"]), "out": str(dst),
            "unresolved": resolved["unresolved"]}



# ---------------------------------------------------------------------------
# Task implementations (all local/read-only unless injected)
# ---------------------------------------------------------------------------
def _task_package_validate(ctx):
    gdo = _load_gdo()
    product = ctx.get("product")
    rep = gdo.validate_spec(gdo.build_spec(product)) if product else gdo.validate_package()
    failed = [c["check"] for c in rep["checks"] if c["status"] != "PASS"]
    if not rep["ready"]:
        raise PermanentError("package not ready: " + ", ".join(failed))
    wb = workbook_validate(product=product)
    if not wb.get("structural_ok"):
        raise PermanentError("workbook structural validation failed")
    return {"ready": True, "failed": failed,
            "workbook": {"sha256": wb.get("sha256"), "sheets": wb.get("sheets"),
                         "formula_cells": wb.get("formula_cells"),
                         "cached_verification": wb.get("cached_verification")}}


def _task_price_authority(ctx):
    fn = ctx.get("price_authority_fn", price_authority)
    product = ctx.get("product")
    pa = fn(product=product) if product else fn()
    if not pa["authorized"]:
        raise PermanentError(f"price not authorized: {pa.get('reason')}")
    return {"price_usd": pa["price_usd"], "basis": pa["basis"], "sources": pa["sources"]}


def _task_catalog_duplicate_check(ctx):
    reader = ctx.get("catalog_reader")
    if reader is None:
        return {"duplicate": "UNKNOWN", "reason": "no read-only catalog reader injected"}
    gdo = _load_gdo()
    try:
        dup = gdo.duplicate_scan(gdo.build_spec(ctx.get("product")), reader)
    except Exception as exc:  # noqa: BLE001
        # A read failure must not halt the pipeline. It also must never be read
        # as "no duplicate": create_draft_live() re-runs duplicate_scan itself,
        # fail-closed, before any create.
        return {"duplicate": "UNKNOWN", "reason": f"catalog unreadable: {exc!r}"[:300]}
    if dup["found"]:
        raise PermanentError(f"a listing already exists for this title ({dup['match']})")
    return {"duplicate": "NONE", "match": None}


def _task_draft_capability(ctx):
    return draft_capability_state()


def _create_route_allowed(cap, ctx) -> bool:
    """Normal path: capability must be live-verified. The ONLY other path is an
    explicit, founder-authorized first live verification: both the real write
    gate and draft_authorized must also agree. Never loosens anything by default.
    """
    if cap.get("state") == CAP_SUPPORTED_AND_IMPLEMENTED:
        return True
    return bool(
        ctx.get("first_live_verification") is True
        and cap.get("state") == CAP_IMPLEMENTED_BUT_REMOTE_BEHAVIOR_UNVERIFIED
        and ctx.get("draft_authorized") is True
        and _write_authorized("create_product")
    )


def _task_create_draft(ctx):
    """Never re-creates an existing draft; otherwise refuses unless a
    live-verified, authorized route AND an injected create function exist.
    Never publishes; never assumes the flag is honoured."""
    product = ctx.get("product")
    ev_path = _evidence_path(product=product) if product else None
    evidence = read_draft_evidence(ev_path) if ev_path else read_draft_evidence()
    if evidence:
        return {"created": False, "already_exists": True, "draft": evidence}
    cap = draft_capability_state(ev_path) if ev_path else draft_capability_state()
    fn = ctx.get("create_draft_fn")
    if not _create_route_allowed(cap, ctx) or fn is None:
        raise CapabilityError(
            f"{cap['state']}: no live-verified, authorized draft-creation route "
            f"({cap.get('reason')})")
    if ctx.get("draft_authorized") is not True:
        raise AuthorizationError("explicit draft authorization not supplied")
    res = fn(ctx)  # may raise UncertainOutcomeError / TransientError (injected)
    return res or {"created": True}


def _task_verify_remote_draft(ctx):
    product = ctx.get("product")
    ev_path = _evidence_path(product=product) if product else None
    evidence = read_draft_evidence(ev_path) if ev_path else read_draft_evidence()
    if not evidence:
        raise CapabilityError("no recorded draft evidence to verify")
    fn = ctx.get("verify_draft_fn")
    if fn is None:
        # The stored evidence is itself a create-response + read-back observation.
        return {"verified": True, "source": "recorded create + read-back evidence",
                "product_id": evidence.get("product_id"),
                "url": evidence.get("url")}
    res = fn(ctx, evidence)
    if not res.get("verified"):
        raise PermanentError(res.get("reason") or "draft could not be verified")
    return res


def _task_resolve_utm(ctx):
    product = ctx.get("product")
    if product and not product_config(product).get("utm_template"):
        raise PermanentError(f"no UTM template configured for {product}")
    base_url = ctx.get("base_url")
    if not base_url:
        ev_path = _evidence_path(product=product) if product else None
        base_url = (read_draft_evidence(ev_path) if ev_path else read_draft_evidence()).get("url")
    if not base_url:
        raise PermanentError("no verified base_url available")
    fn = ctx.get("utm_fn", build_utm_map)
    return fn(base_url)


def _task_sales_ledger_check(ctx):
    reader = ctx.get("sales_reader")
    if reader is None:
        return {"verdict": "UNKNOWN", "sales": None,
                "note": "no read-only sales reader injected"}
    try:
        sales = reader() or []
    except Exception as exc:  # noqa: BLE001
        return {"verdict": "UNKNOWN", "sales": None,
                "reason": f"sales reader failed: {exc!r}"[:300]}
    return {"verdict": "ZERO_CONFIRMED" if len(sales) == 0 else "SALES_PRESENT",
            "sales": len(sales)}


def _task_journey_check(ctx):
    product = ctx.get("product")
    if product:
        page = Path(product_config(product)["customer_page"])
    else:
        page = FACTORY_DIR / "customer_site" / "b12-freelancer-rate-calculator.html"
    if not page.is_file():
        raise PermanentError("customer page missing")
    html = page.read_text(encoding="utf-8", errors="replace").lower()
    return {
        "page_exists": True,
        "has_draft_banner": "draft — not yet listed" in html or "draft" in html,
        "has_buy_link": ("gumroad.com" in html) or ("buy now" in html),
        "has_beacon": "page-view" in html,
    }


def _task_publish(ctx):
    product = ctx.get("product")
    phrase = publish_phrase(product) if product else PUBLISH_PHRASE
    if ctx.get("publish_authorization") != phrase:
        raise FounderAuthorityError(
            f"publishing requires the exact founder authorization '{phrase}'",
            ctx_key="publish_authorization", required=phrase)
    fn = ctx.get("publish_fn")
    if fn is None:
        raise CapabilityError("no publish implementation injected")
    return fn(ctx)


DEFAULT_REGISTRY = {
    "package_validate": _task_package_validate,
    "price_authority": _task_price_authority,
    "catalog_duplicate_check": _task_catalog_duplicate_check,
    "draft_capability": _task_draft_capability,
    "create_draft": _task_create_draft,
    "verify_remote_draft": _task_verify_remote_draft,
    "resolve_utm": _task_resolve_utm,
    "sales_ledger_check": _task_sales_ledger_check,
    "journey_check": _task_journey_check,
    "publish": _task_publish,
}


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
def _deps_completed(state, t) -> bool:
    return all(state["tasks"].get(d, {}).get("status") in (COMPLETED, EXTERNALLY_VERIFIED)
               for d in t["depends_on"])


def _event(state, t, kind, detail=None):
    state["events"].append({
        "at": _now(), "task": t["id"], "event": kind, "status": t["status"],
        "attempts": t["attempts"], "detail": detail,
    })
    # keep the event log small and bounded
    if len(state["events"]) > 500:
        del state["events"][:-500]


def _set(state, t, status, blocker=None, error=None, run_id=None):
    t["status"] = status
    t["blocker"] = blocker
    t["run_id"] = run_id
    t["updated_at"] = _now()
    if blocker != BLOCKER_RECONCILIATION:
        t.setdefault("needs_reconciliation", False)
    _event(state, t, "STATUS", error or blocker)


def _resume_interrupted(state, run_id):
    for t in state["tasks"].values():
        if t["status"] == RUNNING and t.get("run_id") != run_id:
            if t.get("external"):
                t["needs_reconciliation"] = True
                _set(state, t, NEEDS_RECONCILIATION, BLOCKER_RECONCILIATION,
                     "interrupted after an external action; reconcile before retry")
            else:
                _set(state, t, FAILED_RETRYABLE, None, "interrupted mid-run; safe to retry")


def _retry_due(t, now) -> bool:
    due = _parse(t.get("next_retry_at"))
    return due is None or due <= now


def _execute(state, t, registry, ctx, now, run_id):
    if t.get("external") and t.get("last_error_kind") == "UNCERTAIN":
        t["needs_reconciliation"] = True
        _set(state, t, NEEDS_RECONCILIATION, BLOCKER_RECONCILIATION,
             "prior create outcome unknown; reconcile before retry")
        return
    t["attempts"] += 1
    _set(state, t, RUNNING, None, None, run_id=run_id)
    fn = registry.get(t["id"])
    try:
        if fn is None:
            raise PermanentError("no implementation registered")
        res = fn(ctx)
        t["result"] = res
        t["last_error"] = None
        t["last_error_kind"] = None
        t["authority_requirement"] = None
        verified = bool(isinstance(res, dict) and res.get("externally_verified"))
        _set(state, t, EXTERNALLY_VERIFIED if verified else COMPLETED, None, None)
    except UncertainOutcomeError as e:
        t["last_error"] = str(e)
        t["last_error_kind"] = "UNCERTAIN"
        t["needs_reconciliation"] = True
        _set(state, t, NEEDS_RECONCILIATION, BLOCKER_RECONCILIATION, str(e))
    except TransientError as e:
        t["last_error"] = str(e)
        t["last_error_kind"] = "TRANSIENT"
        if t["attempts"] >= t["max_attempts"]:
            _set(state, t, BLOCKED, BLOCKER_TRANSIENT_EXHAUSTED, str(e))
        else:
            t["next_retry_at"] = (now + timedelta(seconds=_backoff_seconds(t["attempts"]))).isoformat()
            _set(state, t, FAILED_RETRYABLE, None, str(e))
    except (AuthorizationError, CapabilityError, FounderAuthorityError, PermanentError) as e:
        t["last_error"] = str(e)
        t["last_error_kind"] = "BLOCKED"
        # Remember exactly which authorization was missing (founder-authority
        # only), so a later run carrying it can re-open this task. Any other
        # block clears a stale requirement.
        if (isinstance(e, FounderAuthorityError) and getattr(e, "ctx_key", None)
                and getattr(e, "required", None) is not None):
            t["authority_requirement"] = {"ctx_key": e.ctx_key, "required": e.required}
        else:
            t["authority_requirement"] = None
        _set(state, t, BLOCKED, getattr(e, "blocker", BLOCKER_PERMANENT), str(e))
    except Exception as e:  # noqa: BLE001
        t["last_error"] = f"{type(e).__name__}: {e}"
        t["last_error_kind"] = "BLOCKED"
        t["authority_requirement"] = None
        _set(state, t, BLOCKED, BLOCKER_PERMANENT, t["last_error"])


def _step(state, registry, ctx, now, run_id) -> bool:
    for t in state["tasks"].values():
        st = t["status"]
        if st in (RUNNING, COMPLETED, EXTERNALLY_VERIFIED, BLOCKED, NEEDS_RECONCILIATION):
            continue
        if not _deps_completed(state, t):
            if st != PENDING or t.get("blocker") != BLOCKER_DEPENDENCY:
                _set(state, t, PENDING, BLOCKER_DEPENDENCY, "waiting on prerequisites")
            continue
        if st == FAILED_RETRYABLE and not _retry_due(t, now):
            continue
        _execute(state, t, registry, ctx, now, run_id)
        return True
    return False


def next_action(state) -> dict:
    tasks = state["tasks"]
    retryable = sorted(t["id"] for t in tasks.values() if t["status"] == FAILED_RETRYABLE)
    if retryable:
        return {"kind": "RETRY", "action": retryable[0], "reason": "transient retry due"}
    eligible = sorted(
        t["id"] for t in tasks.values()
        if t["status"] in (PENDING, EXECUTABLE) and _deps_completed(state, t))
    if eligible:
        return {"kind": "EXECUTE", "action": eligible[0], "reason": "next eligible task"}
    blocked = sorted(t["id"] for t in tasks.values() if t["status"] in (BLOCKED, NEEDS_RECONCILIATION))
    if blocked:
        summary = {}
        for tid in blocked:
            t = tasks[tid]
            summary[tid] = t.get("blocker") or t["status"]
        return {"kind": "BLOCKED", "action": None,
                "reason": "all remaining work is blocked or awaiting reconciliation",
                "blocked_by": summary}
    return {"kind": "DONE", "action": None, "reason": "all tasks completed"}


RECHECKABLE_BLOCKERS = (BLOCKER_EXTERNAL_CAPABILITY, BLOCKER_AUTHORIZATION)


def reset_recheckable(state) -> list:
    """Re-open tasks blocked on capability/authorization so a later run can
    re-evaluate them. Permanent and founder-authority blocks are never reset.
    """
    changed = []
    for t in state["tasks"].values():
        if t["status"] == BLOCKED and t.get("blocker") in RECHECKABLE_BLOCKERS:
            t["attempts"] = 0
            t["last_error"] = None
            t["last_error_kind"] = None
            _set(state, t, PENDING, BLOCKER_DEPENDENCY,
                 "re-checked on a new run (capability/authorization may have changed)")
            changed.append(t["id"])
    return changed


def reset_founder_authority(state, ctx) -> list:
    """Re-open a task blocked on BLOCKER_FOUNDER_AUTHORITY only when this run
    actually carries the authorization that task demanded.

    A founder-authority block is deliberately NOT in RECHECKABLE_BLOCKERS: a
    routine recheck must never clear it. This is the narrow, correct exception
    -- the block is lifted only by the arrival of the *specific* authorization
    recorded on the task when it blocked (``authority_requirement``). With no
    recorded requirement, or a mismatch, the block is left exactly as it is, so
    this can never bypass founder authorization. It only permits re-evaluation;
    the task function itself still enforces the requirement.
    """
    changed = []
    ctx = ctx or {}
    for t in state["tasks"].values():
        if t["status"] != BLOCKED or t.get("blocker") != BLOCKER_FOUNDER_AUTHORITY:
            continue
        req = t.get("authority_requirement") or {}
        key, required = req.get("ctx_key"), req.get("required")
        if not key or required is None or ctx.get(key) != required:
            continue
        t["attempts"] = 0
        t["last_error"] = None
        t["last_error_kind"] = None
        _set(state, t, PENDING, BLOCKER_DEPENDENCY,
             "re-checked on a new run carrying the founder authorization it required")
        changed.append(t["id"])
    return changed


def run(state=None, registry=None, ctx=None, now=None, max_steps=200, run_id=None,
        persist=True) -> dict:
    state = state if state is not None else load_state()
    registry = DEFAULT_REGISTRY if registry is None else registry
    ctx = ctx or {}
    now = now or datetime.now(timezone.utc)
    run_id = run_id or _new_run_id()
    state["run_id"] = run_id
    _resume_interrupted(state, run_id)
    reset_recheckable(state)
    reset_founder_authority(state, ctx)
    for _ in range(max_steps):
        if not _step(state, registry, ctx, now, run_id):
            break
    state["next_action"] = next_action(state)
    if persist:
        save_state(state)
    return state


def reconcile(state, task_id, resolution, note=None):
    """Resolve a task left in NEEDS_RECONCILIATION after an uncertain outcome.

    resolution: "COMPLETED" (the action did land) or "RETRYABLE"/"BLOCKED".
    Never mutates any remote object.
    """
    t = state["tasks"][task_id]
    if t["status"] != NEEDS_RECONCILIATION:
        raise TaskError(f"{task_id} is {t['status']}, not {NEEDS_RECONCILIATION}")
    t["needs_reconciliation"] = False
    if resolution == "COMPLETED":
        t["last_error"] = None
        t["last_error_kind"] = None
        _set(state, t, COMPLETED, None, note or "reconciled: action had landed")
    elif resolution == "RETRYABLE":
        t["last_error_kind"] = "TRANSIENT"
        _set(state, t, FAILED_RETRYABLE, None, note or "reconciled: action had not landed")
    else:
        _set(state, t, BLOCKED, BLOCKER_PERMANENT, note or "reconciled: blocked")
    state["next_action"] = next_action(state)
    return t


def summarize(state=None) -> dict:
    state = state if state is not None else load_state()
    counts = {}
    for t in state["tasks"].values():
        counts[t["status"]] = counts.get(t["status"], 0) + 1
    return {
        "run_id": state.get("run_id"),
        "updated_at": state.get("updated_at"),
        "counts": counts,
        "next_action": state.get("next_action"),
        "tasks": {
            tid: {"status": t["status"], "blocker": t["blocker"],
                  "kind": t["kind"], "attempts": t["attempts"]}
            for tid, t in state["tasks"].items()
        },
    }


# ---------------------------------------------------------------------------
# Read-only publishing-authority audit (Phase 6)
# ---------------------------------------------------------------------------
def publish_authority_audit() -> dict:
    """Read-only scan for paths that create-then-publish or bypass the gate.
    Never executes anything; only reads source text."""
    findings = []
    targets = {
        "affiliate/publish_queue.py": "create-then-enable (parallel-owned)",
        "src/publish/auto_publisher.py": "batch glob over data/product_batch_*.json (parallel-owned)",
    }
    for rel, what in targets.items():
        p = FACTORY_DIR / rel
        if not p.is_file():
            findings.append({"file": rel, "present": False})
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        findings.append({
            "file": rel,
            "present": True,
            "what": what,
            "creates_then_publishes": ("enable_product(" in text and "create_product(" in text),
            "checks_live_flag": "FACTORY_LIVE_PUBLISH" in text,
        })
    return {
        "live_flag": os.environ.get("FACTORY_LIVE_PUBLISH", "<unset>"),
        "findings": findings,
        "note": "Read-only. Parallel-owned files are never modified.",
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _real_ctx(authorize_draft=False, publish_authorization=None, product=None):
    """Build the real context. Read-only by default; the write path is only
    attached when an explicit authorization is supplied on the command line.
    Never prints secrets."""
    ctx = {"dry_run": True}
    if product:
        ctx["product"] = product
    try:
        if str(FACTORY_DIR) not in sys.path:
            sys.path.insert(0, str(FACTORY_DIR))
        from channels import gumroad_publisher as gp
        token = gp.load_token()
        ctx["catalog_reader"] = lambda: gp.list_products(token)
        ctx["sales_reader"] = lambda: gp.get_sales(token)
        ctx["verify_draft_fn"] = _real_verify_draft
    except Exception:  # noqa: BLE001
        pass

    evidence = read_draft_evidence(product=product) if product else read_draft_evidence()
    if evidence:
        ctx["base_url"] = evidence.get("url")

    if authorize_draft:
        ctx["create_draft_fn"] = _real_create_draft_fn
        ctx["draft_authorized"] = True
        ctx["first_live_verification"] = True
        ctx["dry_run"] = False
    if publish_authorization:
        ctx["publish_authorization"] = publish_authorization
        ctx["publish_fn"] = _real_publish_fn
    return ctx


LISTING_COPY_PATH = FACTORY_DIR / "reports" / "B12-001" / "listing_copy.prepared.md"
LISTING_TAGS = ("freelancing", "pricing", "rate calculator", "consultant",
                "spreadsheet", "raise", "excel template", "solo consultant")
LISTING_EVIDENCE_PATH = FACTORY_DIR / "data" / "first_sale_listing_update_evidence.json"


def _prepared_listing_copy(product=None):
    """Parse a product's prepared listing copy into (description, tags).

    Two real on-disk formats are supported, chosen by the file's own content
    (never guessed):
      * B12-001's marker format (`## \\`description\\` (ready to send)` +
        `## \\`tags\\``); tags come from the product profile.
      * the plain "COPY-PASTE LISTING" format
        (`DESCRIPTION:` / `TAGS:` / `FILES TO UPLOAD:`), tags parsed inline.
    Raises if the file or a block is missing, so a caller can never write an
    accidental empty/partial description to a live listing."""
    cfg = product_config(product) if product else None
    path = Path(cfg["listing_copy"]) if cfg else LISTING_COPY_PATH
    if not path.exists():
        raise PermanentError(f"prepared copy missing: {path}")
    text = path.read_text(encoding="utf-8")
    b12_marker = "## `description` (ready to send)"
    if b12_marker in text:
        if "## `tags`" not in text:
            raise PermanentError("prepared copy is missing its description/tags blocks")
        desc = text.split(b12_marker, 1)[1].split("## `tags`", 1)[0].strip()
        tags = list(cfg["tags"]) if cfg else list(LISTING_TAGS)
        if not desc:
            raise PermanentError("prepared description block is empty")
        return desc, tags
    if "DESCRIPTION:" in text and "TAGS:" in text:
        desc = text.split("DESCRIPTION:", 1)[1].split("\nTAGS:", 1)[0].strip()
        tags_raw = text.split("TAGS:", 1)[1].split("FILES TO UPLOAD:", 1)[0].strip()
        tags = [t.strip() for t in tags_raw.replace("\n", ",").split(",") if t.strip()]
        if not desc:
            raise PermanentError("prepared description block is empty")
        if not tags:
            raise PermanentError("prepared tags block is empty")
        return desc, tags
    raise PermanentError("prepared copy is missing its description/tags blocks")


def _prepared_description(product=None):
    """The exact prepared description text (B12-001 by default)."""
    return _prepared_listing_copy(product)[0]


def apply_listing_copy(*, dry_run=True, evidence_path=None, product=None):
    """Send the prepared description + tags to the LIVE listing.

    Never touches price, files, or publication state. Verifies by read-back
    that the description and tags actually persisted AND that the product is
    still unpublished and still costs the authorized price; any silent no-op
    or any change to publication state raises instead of reporting success."""
    desc, tags = _prepared_listing_copy(product)
    min_words = int(product_config(product).get("min_description_words", 300)) \
        if product else 300
    expected_price = int(product_config(product)["price_cents"]) if product else 1499
    slug = product_config(product)["slug"] if product else "b12-001"
    words = len(desc.split())
    if words < min_words:
        raise PermanentError(
            f"prepared description is only {words} words (<{min_words})")
    if dry_run:
        return {"applied": False, "reason": "dry_run", "description_words": words,
                "tags": list(tags)}

    if not live_flag_enabled() or not _write_authorized("update_product"):
        raise AuthorizationError(
            "applying listing copy requires FACTORY_LIVE_PUBLISH=true and a "
            "fresh VERIFIED auth state (write gate)")

    ev_path = _evidence_path(product=product) if product else None
    evidence = read_draft_evidence(ev_path) if ev_path else read_draft_evidence()
    if not evidence:
        raise PermanentError("no recorded draft evidence to update")
    product_id = evidence["product_id"]

    if str(FACTORY_DIR) not in sys.path:
        sys.path.insert(0, str(FACTORY_DIR))
    from channels import gumroad_publisher as gp
    from channels import write_scope as ws

    token = gp.load_token()
    scope = ws.issue_scope(product_id=product_id, slug=slug,
                           payload={"description": desc},
                           operation="update_description")
    # The library's own post-write verification is authoritative for a
    # PARTIAL claim only. Handled by explicit class, never blanket-swallowed:
    #   * VERIFICATION_UNKNOWN  -> the library could not read back at all;
    #     state is unestablished, so fail closed immediately.
    #   * VERIFICATION_FAILED   -> the library claims a field did not persist;
    #     that claim is recorded as unproven-by-library and the INDEPENDENT
    #     read-back below must still prove every field, or this raises.
    #   * anything else (auth denial, explicit platform rejection, network
    #     error) -> propagate; that is a real BLOCKED write, not a nuance.
    library_unproven = {}
    writes = (
        ("description", lambda: gp.update_product_description_scoped(
            token, product_id, desc, scope_id=scope.scope_id)),
        ("tags", lambda: gp.update_product(token, product_id,
                                           {"tags": list(tags)})),
    )
    for field, write in writes:
        try:
            write()
        except RuntimeError as e:
            text = str(e)
            if "VERIFICATION_UNKNOWN" in text:
                raise UncertainOutcomeError(
                    f"{field}: library could not establish the post-write state "
                    f"({text[:200]})")
            if "VERIFICATION_FAILED" not in text:
                raise
            library_unproven[field] = text[:300]

    fresh = gp.get_product(token, product_id)
    if not isinstance(fresh, dict):
        raise UncertainOutcomeError("post-update read-back returned non-product")
    got_desc = (fresh.get("description") or "")
    got_tags = set(fresh.get("tags") or [])
    problems = []
    if len(got_desc.split()) < min_words:
        problems.append(f"description_words={len(got_desc.split())} (<{min_words})")
    if not set(tags) <= got_tags:
        problems.append(f"tags_missing={sorted(set(tags) - got_tags)}")
    if fresh.get("published") is not False:
        problems.append(f"published=={fresh.get('published')!r} (must stay False)")
    if fresh.get("price") != expected_price:
        problems.append(f"price=={fresh.get('price')!r} (must stay {expected_price})")
    if problems:
        raise UncertainOutcomeError("listing update not proven: " + "; ".join(problems))

    result = {
        "applied": True,
        "product_id": product_id,
        "description_words": len(got_desc.split()),
        "tags": sorted(got_tags),
        "published": fresh.get("published"),
        "price_cents": fresh.get("price"),
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cover_present": bool(fresh.get("thumbnail_url") or fresh.get("cover_url")),
        "library_unproven": library_unproven,
    }
    if evidence_path:
        path = Path(evidence_path)
    elif product:
        path = Path(product_config(product)["listing_evidence"])
    else:
        path = LISTING_EVIDENCE_PATH
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    return result


COVER_LOCAL_PATH = FACTORY_DIR / "reports" / "B12-001" / "cover.png"
COVER_PUBLIC_URL = ("https://raw.githubusercontent.com/galaxyaek7-del/"
                    "openclaw-factory/main/reports/B12-001/cover.png")
COVER_EVIDENCE_PATH = FACTORY_DIR / "data" / "first_sale_cover_evidence.json"


def _write_json_atomic(path, payload):
    """Write JSON via a temp file + fsync + os.replace. Never leaves a
    half-written evidence file behind."""
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    return path


def verify_cover_source(url=None, local_path=None, timeout=30, product=None):
    """Prove, read-only, that the public cover URL serves the byte-identical
    canonical cover, and that the canonical cover itself is a usable image.

    The covers endpoint makes Gumroad fetch this URL server-side, so the URL
    must be publicly reachable and must carry OUR asset -- not a placeholder.
    Returns {public_status, public_bytes, public_sha256, local_sha256,
    identical, width, height} with width/height UNKNOWN if Pillow is absent."""
    import hashlib
    if product:
        cfg = product_config(product)
        url = url or cfg["cover_public_url"]
        local = Path(local_path) if local_path else Path(cfg["cover_local_path"])
    else:
        url = url or COVER_PUBLIC_URL
        local = Path(local_path) if local_path else COVER_LOCAL_PATH
    out = {"url": url, "local_path": str(local)}
    if not local.exists():
        out["error"] = "local cover missing"
        return out
    local_bytes = local.read_bytes()
    out["local_bytes"] = len(local_bytes)
    out["local_sha256"] = hashlib.sha256(local_bytes).hexdigest()
    try:
        import requests
        r = requests.get(url, timeout=timeout)
        out["public_status"] = r.status_code
        out["public_bytes"] = len(r.content)
        out["public_sha256"] = hashlib.sha256(r.content).hexdigest()
        out["public_content_type"] = r.headers.get("content-type")
        out["identical"] = (r.status_code == 200 and
                            out["public_sha256"] == out["local_sha256"])
    except Exception as e:  # noqa: BLE001
        out["error"] = repr(e)[:200]
        out["identical"] = False
    try:
        from PIL import Image
        with Image.open(local) as im:
            out["width"], out["height"] = im.size
            out["mode"] = im.mode
    except Exception:  # noqa: BLE001
        out["width"] = out["height"] = "UNKNOWN"
    return out


def attach_cover(*, dry_run=True, url=None, evidence_path=None, product=None):
    """Attach the cover to the LIVE listing from its public URL.

    Uses the real documented endpoint (POST /v2/products/:id/covers), which
    makes Gumroad fetch the image itself, and proves the attach with a
    read-back. Never touches price, files, name or publication state."""
    if product:
        url = url or product_config(product)["cover_public_url"]
    else:
        url = url or COVER_PUBLIC_URL
    expected_price = int(product_config(product)["price_cents"]) if product else 1499
    if dry_run:
        return {"attached": False, "reason": "dry_run", "url": url}
    if not live_flag_enabled() or not _write_authorized("update_product"):
        raise AuthorizationError(
            "attaching the cover requires FACTORY_LIVE_PUBLISH=true and a "
            "fresh VERIFIED auth state (write gate)")

    source = verify_cover_source(url, product=product)
    if not source.get("identical"):
        raise PermanentError(
            f"refusing to attach: the public cover URL is not proven to serve "
            f"the canonical cover ({ {k: source.get(k) for k in ('public_status','public_bytes','error')} })")

    ev_path = _evidence_path(product=product) if product else None
    evidence = read_draft_evidence(ev_path) if ev_path else read_draft_evidence()
    if not evidence:
        raise PermanentError("no recorded draft evidence to attach a cover to")
    product_id = evidence["product_id"]
    if evidence_path:
        out_path = Path(evidence_path)
    elif product:
        out_path = Path(product_config(product)["cover_evidence"])
    else:
        out_path = COVER_EVIDENCE_PATH

    if str(FACTORY_DIR) not in sys.path:
        sys.path.insert(0, str(FACTORY_DIR))
    from channels import gumroad_publisher as gp

    token = gp.load_token()
    before = gp.get_product(token, product_id) or {}
    if before.get("published") is not False:
        raise PermanentError(
            f"refusing to attach a cover while published={before.get('published')!r}")
    before_covers = len(before.get("covers") or [])
    if before_covers >= 1:
        # Idempotent: never stack a duplicate cover on the listing.
        result = {
            "attached": False,
            "already_attached": True,
            "product_id": product_id,
            "covers_count": before_covers,
            "main_cover_id": before.get("main_cover_id"),
            "cover_url": url,
            "title": before.get("name"),
            "price_cents": before.get("price"),
            "published": before.get("published"),
            "observed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "note": "a cover is already present; no second cover was added",
        }
        _write_json_atomic(out_path, result)
        return result

    fresh = gp.add_product_cover(token, product_id, url,
                                 expected_cover_count=before_covers)
    if not isinstance(fresh, dict):
        raise UncertainOutcomeError("cover read-back returned non-product")
    problems = []
    covers = fresh.get("covers") or []
    if not covers:
        problems.append("covers empty after attach")
    if fresh.get("published") is not False:
        problems.append(f"published=={fresh.get('published')!r} (must stay False)")
    if fresh.get("price") != expected_price:
        problems.append(f"price=={fresh.get('price')!r} (must stay {expected_price})")
    if problems:
        raise UncertainOutcomeError("cover attach not proven: " + "; ".join(problems))

    result = {
        "attached": True,
        "product_id": product_id,
        "cover_url": url,
        "covers_count": len(covers),
        "main_cover_id": fresh.get("main_cover_id"),
        "cover_sha256": source.get("local_sha256"),
        "published": fresh.get("published"),
        "price_cents": fresh.get("price"),
        "attached_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    _write_json_atomic(out_path, result)
    return result


def listing_projection(product=None):
    """Read-only projection of the live draft. Never returns a secret."""
    try:
        if str(FACTORY_DIR) not in sys.path:
            sys.path.insert(0, str(FACTORY_DIR))
        from channels import gumroad_publisher as gp
        ev_path = _evidence_path(product=product) if product else None
        pid = (read_draft_evidence(ev_path) if ev_path else read_draft_evidence()).get("product_id")
        if not pid:
            return {"error": "no recorded draft id"}
        p = gp.get_product(gp.load_token(), pid) or {}
        desc = p.get("description") or ""
        return {
            "id": p.get("id"),
            "name": p.get("name"),
            "price_cents": p.get("price"),
            "published": p.get("published"),
            "short_url": p.get("short_url"),
            "currency": p.get("currency"),
            "sales_count": p.get("sales_count"),
            "description_words": len(desc.split()),
            "tags": p.get("tags") or [],
            "files": [{"size": f.get("size"), "filetype": f.get("filetype")}
                      for f in (p.get("files") or [])],
            "cover_present": bool(p.get("thumbnail_url") or p.get("cover_url")
                                  or (p.get("covers") or [])),
            "covers_count": len(p.get("covers") or []),
            "main_cover_id": p.get("main_cover_id"),
            "cover_urls": [c.get("url") for c in (p.get("covers") or []) if isinstance(c, dict)],
        }
    except Exception as e:  # noqa: BLE001
        return {"error": repr(e)[:200]}


def main():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description="First-Sale task orchestrator (no publishing by default)")
    ap.add_argument("--status", action="store_true", help="print state summary (default)")
    ap.add_argument("--run", action="store_true", help="run all eligible local tasks once")
    ap.add_argument("--audit", action="store_true", help="read-only publishing-authority audit")
    ap.add_argument("--workbook", action="store_true", help="validate the B12-001 workbook (local)")
    ap.add_argument("--resolve-utm", metavar="BASE_URL",
                    help="resolve the UTM template against a verified listing URL")
    ap.add_argument("--authorize-draft", action="store_true",
                    help="supply explicit authorization for the (real) draft create task")
    ap.add_argument("--publish-authorization", metavar="PHRASE",
                    help="the exact founder phrase required for the publish task")
    ap.add_argument("--listing", action="store_true",
                    help="read-only projection of the live draft listing")
    ap.add_argument("--apply-listing", action="store_true",
                    help="send the prepared description+tags to the live listing "
                         "(needs the write gate; never publishes)")
    ap.add_argument("--cover-source", action="store_true",
                    help="read-only: prove the public cover URL serves the canonical cover")
    ap.add_argument("--attach-cover", action="store_true",
                    help="attach the cover to the live listing (needs the write gate)")
    ap.add_argument("--rollback", action="store_true",
                    help="revert the listing to unpublished (needs the write gate)")
    ap.add_argument("--republish", action="store_true",
                    help="re-enable an existing verified listing after a rollback "
                         "(needs the write gate AND --publish-authorization)")
    ap.add_argument("--product", default=None,
                    help="product id (e.g. B12-004); default is B12-001")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    # A non-default product keeps its own task state file so a real run never
    # mixes one product's completed tasks with another's.
    if args.product and args.product != "B12-001":
        slug = args.product.lower()
        os.environ.setdefault(
            "FIRST_SALE_TASKS_PATH",
            str(FACTORY_DIR / "data" / f"first_sale_tasks_{slug}.json"))

    if args.listing:
        out = listing_projection(product=args.product)
    elif args.apply_listing:
        try:
            out = apply_listing_copy(dry_run=False, product=args.product)
        except TaskError as e:
            out = {"applied": False, "error": str(e)}
    elif args.cover_source:
        out = verify_cover_source(product=args.product)
    elif args.attach_cover:
        try:
            out = attach_cover(dry_run=False, product=args.product)
        except TaskError as e:
            out = {"attached": False, "error": str(e)}
    elif args.rollback:
        try:
            out = _rollback(product=args.product)
        except TaskError as e:
            out = {"error": str(e), "rolled_back": False}
    elif args.republish:
        try:
            out = republish(product=args.product,
                            publish_authorization=args.publish_authorization)
        except TaskError as e:
            out = {"published": False, "error": str(e)}
    elif args.workbook:
        out = workbook_validate(product=args.product)
    elif args.resolve_utm:
        try:
            out = resolve_utm_links(args.resolve_utm)
        except TaskError as e:
            out = {"error": str(e), "resolved": 0}
    elif args.audit:
        out = publish_authority_audit()
    elif args.run:
        ctx = _real_ctx(authorize_draft=args.authorize_draft,
                        publish_authorization=args.publish_authorization,
                        product=args.product)
        out = summarize(run(ctx=ctx))
    else:
        out = summarize()

    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

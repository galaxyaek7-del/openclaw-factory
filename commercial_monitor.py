"""Galaxy Forge — COMMERCIAL MONITORING.

Lightweight commercial health checks that fill the gaps between the existing
infrastructure health checks (`lib/health_checks.js`) and the commercial
alerting system (`commercial_alerts.py`).

What this module adds:
  A) PAGE AVAILABILITY — check customer-facing pages exist and are valid
  B) CHECKOUT READINESS — track Paddle/Gumroad checkout status transitions
  C) ERROR RATE MONITORING — threshold-based alerting on route error rates
  D) PRODUCT HEALTH — per-product readiness and blocking gate status
  E) COMMERCIAL DASHBOARD — unified view of all commercial health signals

All checks are real, mechanical, and read-only. No fabricated metrics.
"""

from __future__ import annotations

import json
import os
import time as _time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_FACTORY_ROOT = Path(__file__).resolve().parent
MONITOR_STATE_PATH = _FACTORY_ROOT / "data" / "commercial_monitor_state.json"
REALITY_PATH = _FACTORY_ROOT / "config" / "reality.json"
FINANCE_PATH = _FACTORY_ROOT / "finance_data.json"
PADDLE_PRODUCTS_PATH = _FACTORY_ROOT / "data" / "paddle_products.json"
ASSET_REGISTRY_PATH = _FACTORY_ROOT / "data" / "asset_registry.json"
REVENUE_STATE_PATH = _FACTORY_ROOT / "data" / "revenue_engine_state.json"

# Customer-facing pages that should be accessible
CUSTOMER_PAGES = [
    {"path": "customer_site/index.html", "url": "/site/", "name": "Home"},
    {"path": "customer_site/catalog.html", "url": "/site/catalog.html", "name": "Catalog"},
    {"path": "customer_site/login.html", "url": "/site/login.html", "name": "Login"},
    {"path": "customer_site/status.html", "url": "/site/status.html", "name": "Status"},
    {"path": "customer_site/eu-ai-act-compliance-toolkit.html", "url": "/site/eu-ai-act-compliance-toolkit.html", "name": "EU AI Act Toolkit"},
    {"path": "customer_site/affiliate-standing-desks.html", "url": "/site/affiliate-standing-desks.html", "name": "Affiliate Standing Desks"},
]

# Error rate thresholds
ERROR_RATE_WARNING = 5.0   # percent
ERROR_RATE_CRITICAL = 20.0  # percent


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> Any:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _load_state() -> Dict[str, Any]:
    default = {"last_check": None, "checks_run": 0, "findings": []}
    data = _load_json(MONITOR_STATE_PATH)
    if data:
        default.update(data)
    return default


def _save_state(state: Dict[str, Any]) -> None:
    state["last_check"] = _now_iso()
    state["checks_run"] = state.get("checks_run", 0) + 1
    MONITOR_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MONITOR_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# A) PAGE AVAILABILITY — check customer-facing pages exist
# ---------------------------------------------------------------------------

def check_page_availability() -> Dict[str, Any]:
    """Check that all customer-facing pages exist on disk.

    This is a structural check (file exists), not an HTTP uptime check.
    For HTTP availability, the existing `lib/health_checks.js` network
    reachability check covers the server level.
    """
    results = []
    for page in CUSTOMER_PAGES:
        page_path = _FACTORY_ROOT / page["path"]
        exists = page_path.exists()
        size = page_path.stat().st_size if exists else 0
        results.append({
            "name": page["name"],
            "url": page["url"],
            "path": page["path"],
            "exists": exists,
            "size_bytes": size,
            "status": "OK" if exists and size > 0 else "MISSING" if not exists else "EMPTY",
        })

    missing = [r for r in results if r["status"] != "OK"]
    return {
        "checked_at": _now_iso(),
        "total_pages": len(results),
        "available": len(results) - len(missing),
        "missing": len(missing),
        "pages": results,
        "status": "HEALTHY" if not missing else "DEGRADED",
    }


# ---------------------------------------------------------------------------
# B) CHECKOUT READINESS — track Paddle/Gumroad status
# ---------------------------------------------------------------------------

def check_checkout_readiness() -> Dict[str, Any]:
    """Check checkout readiness across all payment channels."""
    paddle_products = _load_json(PADDLE_PRODUCTS_PATH)
    if isinstance(paddle_products, dict):
        paddle_products = paddle_products.get("products", [])

    paddle_status = []
    for p in paddle_products:
        paddle_status.append({
            "product_id": p.get("product_id", "unknown"),
            "title": p.get("title", "Unknown"),
            "price": p.get("price", 0),
            "checkout_ready": p.get("checkout_ready", False),
            "has_price_id": bool(p.get("price_id")),
        })

    ready_count = sum(1 for p in paddle_status if p["checkout_ready"])
    blocked_count = len(paddle_status) - ready_count

    # Gumroad status (from asset registry)
    #
    # Evidence-integrity fix (2026-10-12, cycle 109). This block read ONLY a
    # local snapshot file and then emitted a hard BLOCKED verdict from it:
    #     products=20  published=0
    #     status="BLOCKED"
    #     blocking_note="All channels blocked - founder action required"
    # while the live Gumroad API reported published=True for every product
    # checked, with real delivery files attached. The registry entries are all
    # still at production_status="PRODUCED" and the file was 21.6 days stale,
    # so `is_published` was False BY CONSTRUCTION - it could never be anything
    # else, no matter what was actually live on Gumroad.
    #
    # That manufactured a false blocker and pointed the founder at a channel
    # that was working. The snapshot is still reported (it is a real local
    # fact) but it may no longer assert a BLOCKED verdict, because a stale
    # local file is not evidence about the live platform.
    assets = _load_json(ASSET_REGISTRY_PATH)
    if isinstance(assets, dict):
        assets = assets.get("assets", [])

    registry_age_days = None
    try:
        registry_age_days = round(
            (_time.time() - os.path.getmtime(ASSET_REGISTRY_PATH)) / 86400.0, 1)
    except (OSError, TypeError):
        registry_age_days = None

    gumroad_status = []
    for a in assets:
        if a.get("product_genome", {}).get("platform") == "gumroad_digital":
            gumroad_status.append({
                "asset_id": a.get("asset_id", "unknown"),
                "name": a.get("product_name", "Unknown"),
                "is_published": a.get("production_status") == "PUBLISHED",
                "has_file": bool(a.get("product_genome", {}).get("file")),
                "local_production_status": a.get("production_status"),
            })

    gumroad_published = sum(1 for g in gumroad_status if g["is_published"])
    # A snapshot can never assert a blocker. It can only raise a question.
    gumroad_snapshot_stale = (registry_age_days is None) or (registry_age_days > 1.0)

    return {
        "checked_at": _now_iso(),
        "paddle": {
            "total_products": len(paddle_status),
            "checkout_ready": ready_count,
            "blocked": blocked_count,
            "products": paddle_status,
        },
        "gumroad": {
            "total_products": len(gumroad_status),
            "published": gumroad_published,
            "products": gumroad_status,
            "evidence_source": "LOCAL_SNAPSHOT_ONLY",
            "registry_age_days": registry_age_days,
            "snapshot_is_stale": gumroad_snapshot_stale,
            "snapshot_caveat": (
                "Counts come from a local asset registry, NOT the live Gumroad API. "
                "They describe what the factory recorded, not what Gumroad is "
                "currently serving. Do not read them as platform state."
            ),
            "live_platform_state": (
                "UNKNOWN from this function - verify with GET /v2/products before "
                "claiming anything about live Gumroad."
            ),
        },
        "status": "READY" if ready_count > 0 or gumroad_published > 0 else "BLOCKED",
        "blocking_note": (
            "Local snapshot shows no published Gumroad asset AND no ready Paddle "
            "product. This is NOT evidence that Gumroad is blocked: it is a stale "
            "local file. Verify against the live API before treating this as a "
            "blocker or asking the founder to act."
        ) if ready_count == 0 and gumroad_published == 0 else None,
    }


# ---------------------------------------------------------------------------
# C) ERROR RATE MONITORING — threshold-based alerting
# ---------------------------------------------------------------------------

def check_error_rates(metrics_summary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Check route error rates against thresholds.

    Args:
        metrics_summary: Output from lib/metrics.js summarizeRoutes().
            If None, reads from a cached file if available.
    """
    if metrics_summary is None:
        # Try to read from a cached metrics file
        metrics_path = _FACTORY_ROOT / "data" / "metrics_summary.json"
        if metrics_path.exists():
            metrics_summary = _load_json(metrics_path)

    if not metrics_summary:
        return {
            "checked_at": _now_iso(),
            "status": "NO_DATA",
            "note": "No metrics data available — metrics_summary not provided",
        }

    routes = metrics_summary.get("routes", {})
    warnings = []
    criticals = []

    for route, data in routes.items():
        error_rate = data.get("error_rate_pct", 0)
        if error_rate >= ERROR_RATE_CRITICAL:
            criticals.append({
                "route": route,
                "error_rate_pct": error_rate,
                "last_failure_at": data.get("last_failure_at"),
            })
        elif error_rate >= ERROR_RATE_WARNING:
            warnings.append({
                "route": route,
                "error_rate_pct": error_rate,
                "last_failure_at": data.get("last_failure_at"),
            })

    status = "HEALTHY"
    if criticals:
        status = "CRITICAL"
    elif warnings:
        status = "WARNING"

    return {
        "checked_at": _now_iso(),
        "total_routes": len(routes),
        "warning_threshold": ERROR_RATE_WARNING,
        "critical_threshold": ERROR_RATE_CRITICAL,
        "warnings": warnings,
        "criticals": criticals,
        "status": status,
    }


# ---------------------------------------------------------------------------
# D) PRODUCT HEALTH — per-product readiness
# ---------------------------------------------------------------------------

def check_product_health() -> Dict[str, Any]:
    """Check health of all products in the revenue engine."""
    state = _load_json(REVENUE_STATE_PATH)
    products = state.get("products", {})

    from revenue_engine import STAGE_ORDER

    health = []
    for pid, product in products.items():
        stage = product.get("current_stage", "SENSE")
        stage_idx = STAGE_ORDER.index(stage) if stage in STAGE_ORDER else 0
        history = product.get("stage_history", [])

        # How long at current stage?
        days_at_stage = 0
        if history:
            last = history[-1]
            try:
                entered = datetime.fromisoformat(last["entered_at"])
                if entered.tzinfo is None:
                    entered = entered.replace(tzinfo=timezone.utc)
                days_at_stage = (datetime.now(timezone.utc) - entered).days
            except (ValueError, KeyError):
                pass

        # Is it stuck?
        is_stuck = days_at_stage > 7

        health.append({
            "product_id": pid,
            "name": product.get("product_name", "Unknown"),
            "stage": stage,
            "stage_index": stage_idx,
            "days_at_stage": days_at_stage,
            "is_stuck": is_stuck,
            "evidence_count": len(product.get("evidence_trail", [])),
        })

    stuck_count = sum(1 for h in health if h["is_stuck"])
    selling = sum(1 for h in health if h["stage_index"] >= 8)

    return {
        "checked_at": _now_iso(),
        "total_products": len(health),
        "selling": selling,
        "stuck": stuck_count,
        "products": health,
        "status": "HEALTHY" if stuck_count == 0 else "DEGRADED",
    }


# ---------------------------------------------------------------------------
# E) COMMERCIAL DASHBOARD — unified view
# ---------------------------------------------------------------------------

def commercial_health_dashboard(metrics_summary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Unified commercial health dashboard combining all checks."""
    pages = check_page_availability()
    checkout = check_checkout_readiness()
    errors = check_error_rates(metrics_summary)
    products = check_product_health()
    reality = _load_json(REALITY_PATH)
    finance = _load_json(FINANCE_PATH)

    # Overall status: worst of all checks
    statuses = [pages["status"], checkout["status"], errors["status"], products["status"]]
    if "CRITICAL" in statuses:
        overall = "CRITICAL"
    elif "DEGRADED" in statuses or "WARNING" in statuses or "BLOCKED" in statuses:
        overall = "DEGRADED"
    elif "NO_DATA" in statuses:
        overall = "UNKNOWN"
    else:
        overall = "HEALTHY"

    return {
        "generated_at": _now_iso(),
        "overall_status": overall,
        "page_availability": pages,
        "checkout_readiness": checkout,
        "error_rates": errors,
        "product_health": products,
        "ground_truth": {
            "revenue": finance.get("totalSales", 0),
            "sales": len(finance.get("sales", [])),
            "published": len(reality.get("published_books", [])),
        },
        "action_required": _compile_action_list(pages, checkout, errors, products),
    }


def _compile_action_list(pages: Dict, checkout: Dict, errors: Dict, products: Dict) -> List[str]:
    """Compile a list of required actions from all checks."""
    actions = []

    if pages.get("missing", 0) > 0:
        actions.append(f"Fix {pages['missing']} missing customer-facing pages")

    if checkout.get("status") == "BLOCKED":
        actions.append("Complete Paddle onboarding OR publish to Gumroad")

    if errors.get("criticals"):
        actions.append(f"Fix {len(errors['criticals'])} critical error rate alerts")

    if products.get("stuck", 0) > 0:
        actions.append(f"Unstick {products['stuck']} products stuck in early stages")

    return actions


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    result = commercial_health_dashboard()
    print(json.dumps(result, indent=2, ensure_ascii=False))

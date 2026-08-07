"""Galaxy Forge -- Commercial Revenue Reconciliation (new, ADR-202, 2026-08-07).

Answers Phase 12 Section 5 of the founder's "Global Commercial Revenue
Operating System" directive: compare platform-reported revenue against
this factory's internal records and detect discrepancies automatically.

Real sources compared, nothing invented: Paddle is the only platform with
both a real internal ledger AND a real, live transactions API today
(channels/paddle_arm.py::get_sales() -> paddle_publisher.get_transactions())
-- Gumroad/Etsy/Payhip have no real credential configured in this
factory, so they honestly report NOT_RECONCILABLE rather than a
fabricated zero-discrepancy match. Never writes to finance_data.json or
any ledger -- a real discrepancy is reported for a human to act on,
never silently corrected (Section 5's own "never silently modify
financial records" rule).
"""

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
_FINANCE_PATH = _FACTORY_ROOT / "finance_data.json"
_TEST_RECORD_MARKER = "DELETE-ME"


def _read_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _internal_sales_for_platform(platform_display, finance_path=None):
    finance = _read_json(Path(finance_path) if finance_path else _FINANCE_PATH, {})
    return [
        s for s in finance.get("sales", [])
        if s.get("platform") == platform_display and _TEST_RECORD_MARKER not in str(s.get("product", ""))
    ]


def _discrepancy(difference, cause, impact, confidence, action):
    return {
        "difference_usd": round(difference, 2),
        "possible_cause": cause,
        "financial_impact": impact,
        "confidence": confidence,
        "recommended_action": action,
    }


def reconcile_paddle(finance_path=None, now=None):
    """The one real, live-capable reconciliation this factory can run
    today. Never silently modifies finance_data.json or the ledger --
    read-only comparison, report only."""
    now = now or datetime.now(timezone.utc)

    try:
        import channels.paddle_arm  # noqa: F401  -- self-registers
        from channels import registry, ledger as ledger_module
        from channels.base_arm import ArmStatus
        arm = registry.get("paddle")
    except Exception as e:
        return {
            "platform": "paddle", "status": "ERROR", "error": str(e),
            "generated_at": now.isoformat(),
        }

    if arm is None or arm.status() != ArmStatus.READY:
        return {
            "platform": "paddle", "status": "NOT_RECONCILABLE",
            "reason": "Paddle arm not ready (no real PADDLE_API_KEY configured) -- cannot compare against a live platform figure.",
            "generated_at": now.isoformat(),
        }

    real_transactions, error = arm.get_sales()
    if error:
        return {
            "platform": "paddle", "status": "ERROR", "error": error,
            "generated_at": now.isoformat(),
        }

    platform_total = 0.0
    platform_count = 0
    for txn in real_transactions:
        amount = ledger_module._extract_sale_amount(txn, "paddle")
        if amount is not None:
            platform_total += amount
            platform_count += 1

    internal_sales = _internal_sales_for_platform("Paddle", finance_path=finance_path)
    internal_total = round(sum(float(s.get("amount", 0)) for s in internal_sales), 2)
    internal_count = len(internal_sales)

    difference = round(platform_total - internal_total, 2)
    discrepancies = []

    if platform_count != internal_count:
        discrepancies.append(_discrepancy(
            difference=platform_count - internal_count,
            cause="Real Paddle transaction count differs from internal finance_data.json record count -- likely reconcile_ledger_to_finance() has not yet run against every real ledger event, or a transaction exists on Paddle that was never captured internally.",
            impact=f"${abs(difference):.2f} of {'unreported' if difference > 0 else 'over-reported'} revenue exposure" if difference else "count mismatch with $0 amount exposure",
            confidence="HIGH -- both counts come from a real, live API call and a real, DELETE-ME-filtered internal record" if platform_count > 0 or internal_count > 0 else "LOW -- both sides are $0, difference is definitional not evidentiary",
            action="Run channels.ledger.reconcile_ledger_to_finance() and re-check; if the gap persists, a real Paddle transaction was never recorded by scripts/poll_sales.py and needs manual investigation.",
        ))
    elif abs(difference) > 0.01:
        discrepancies.append(_discrepancy(
            difference=difference,
            cause="Same transaction count on both sides, but real amounts differ -- possible currency/rounding mismatch in channels/ledger.py::_extract_sale_amount(), or a real Paddle amount adjustment (refund/chargeback) not reflected internally.",
            impact=f"${abs(difference):.2f}",
            confidence="MEDIUM -- counts match, so this is a real amount-level discrepancy, not a missing-record one",
            action="Manually inspect the specific transaction IDs on both sides before assuming either figure is correct.",
        ))

    return {
        "platform": "paddle",
        "status": "RECONCILED" if not discrepancies else "DISCREPANCY_FOUND",
        "platform_reported": {"total_usd": round(platform_total, 2), "transaction_count": platform_count},
        "internal_reported": {"total_usd": internal_total, "record_count": internal_count},
        "discrepancies": discrepancies,
        "generated_at": now.isoformat(),
    }


def reconcile_all(finance_path=None, now=None):
    """Every platform this factory can attempt reconciliation for.
    Gumroad/Etsy/Payhip are honestly NOT_RECONCILABLE (no real
    credential configured) -- never a fabricated 'reconciled, no
    discrepancy' for a platform with zero real data to compare."""
    now = now or datetime.now(timezone.utc)
    results = {"paddle": reconcile_paddle(finance_path=finance_path, now=now)}

    for platform_key in ("gumroad", "etsy", "payhip"):
        results[platform_key] = {
            "platform": platform_key, "status": "NOT_RECONCILABLE",
            "reason": f"No real credential configured for {platform_key} in this factory today.",
            "generated_at": now.isoformat(),
        }

    total_discrepancies = sum(len(r.get("discrepancies", [])) for r in results.values())
    return {
        "generated_at": now.isoformat(),
        "platforms": results,
        "total_discrepancies_found": total_discrepancies,
        "note": "Read-only comparison. No financial record was modified by this function -- a found discrepancy is reported for a human to act on, per Section 5's own rule.",
    }

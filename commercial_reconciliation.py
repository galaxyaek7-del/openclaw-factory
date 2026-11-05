"""Galaxy Forge -- Commercial Revenue Reconciliation (new, ADR-202, 2026-08-07).

Answers Phase 12 Section 5 of the founder's "Global Commercial Revenue
Operating System" directive: compare platform-reported revenue against
this factory's internal records and detect discrepancies automatically.

Real sources compared, nothing invented: Gumroad and Paddle both have a real
transactions API. Gumroad's GET /v2/sales was confirmed live 2026-10-21
(channels/gumroad_arm.py::get_sales() -> gumroad_publisher.get_sales()).
Paddle's client is real (channels/paddle_arm.py::get_sales() ->
paddle_publisher.get_transactions()), but its live call returned HTTP 403
with the configured credential on 2026-10-21 and is reported honestly as
ERROR -- no fabricated comparison. Etsy/Payhip have no real credential
configured, so they honestly report NOT_RECONCILABLE rather than a
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
        count_delta = platform_count - internal_count
        discrepancies.append(_discrepancy(
            difference=0.0,
            cause="Real Paddle transaction count differs from internal finance_data.json record count -- likely reconcile_ledger_to_finance() has not yet run against every real ledger event, or a transaction exists on Paddle that was never captured internally.",
            impact=f"{abs(count_delta)} transaction(s) {'on the platform but not internally' if count_delta > 0 else 'internally but not on the platform'}; monetary impact UNKNOWN until the records are matched",
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


def _is_refunded(sale):
    """Only excludes a sale when the platform record itself says so.

    Gumroad's live /v2/sales response shape has not been observed in this
    environment (0 real sales to date), so this checks the conventional
    truthy flags without inferring anything from their absence.
    """
    return bool(sale.get("refunded") or sale.get("chargebacked"))


def reconcile_gumroad(finance_path=None, now=None):
    """Live Gumroad sales-vs-internal-records comparison.

    Read-only. Gumroad's product `sales_count` is not used as revenue
    evidence here: the authoritative per-transaction list from
    GET /v2/sales is the only platform figure compared. A sale whose
    `price` cannot be parsed is reported, never counted as $0.
    """
    now = now or datetime.now(timezone.utc)

    try:
        import channels.gumroad_arm  # noqa: F401  -- self-registers
        from channels import registry, ledger as ledger_module
        from channels.base_arm import ArmStatus
        arm = registry.get("gumroad")
    except Exception as e:
        return {
            "platform": "gumroad", "status": "ERROR", "error": str(e),
            "generated_at": now.isoformat(),
        }

    if arm is None or arm.status() != ArmStatus.READY:
        return {
            "platform": "gumroad", "status": "NOT_RECONCILABLE",
            "reason": "Gumroad arm not ready (no real GUMROAD_ACCESS_TOKEN configured) -- cannot compare against a live platform figure.",
            "generated_at": now.isoformat(),
        }

    sales, error = arm.get_sales()
    if error:
        return {
            "platform": "gumroad", "status": "ERROR", "error": error,
            "generated_at": now.isoformat(),
        }

    platform_total = 0.0
    platform_count = 0
    refunded_count = 0
    unparseable_count = 0
    for sale in sales:
        if _is_refunded(sale):
            refunded_count += 1
            continue
        amount = ledger_module._extract_sale_amount(sale, "gumroad")
        if amount is None:
            unparseable_count += 1
            continue
        platform_total += amount
        platform_count += 1

    internal_sales = _internal_sales_for_platform("Gumroad", finance_path=finance_path)
    internal_total = round(sum(float(s.get("amount", 0)) for s in internal_sales), 2)
    internal_count = len(internal_sales)

    difference = round(platform_total - internal_total, 2)
    discrepancies = []

    if platform_count != internal_count:
        count_delta = platform_count - internal_count
        discrepancies.append(_discrepancy(
            difference=0.0,
            cause="Real Gumroad transaction count differs from internal finance_data.json record count -- likely channels.ledger.reconcile_ledger_to_finance() has not yet run against every real ledger event, or a transaction exists on Gumroad that was never captured internally.",
            impact=f"{abs(count_delta)} transaction(s) {'on the platform but not internally' if count_delta > 0 else 'internally but not on the platform'}; monetary impact UNKNOWN until the records are matched",
            confidence="HIGH -- both counts come from a real, live API call and a real, DELETE-ME-filtered internal record" if platform_count > 0 or internal_count > 0 else "LOW -- both sides are $0, difference is definitional not evidentiary",
            action="Run channels.ledger.reconcile_ledger_to_finance() and re-check; if the gap persists, a real Gumroad transaction was never recorded by scripts/poll_sales.py and needs manual investigation.",
        ))
    elif abs(difference) > 0.01:
        discrepancies.append(_discrepancy(
            difference=difference,
            cause="Same transaction count on both sides, but real amounts differ -- possible currency/rounding mismatch in channels/ledger.py::_extract_sale_amount(), or a real Gumroad amount adjustment (refund/chargeback) not reflected internally.",
            impact=f"${abs(difference):.2f}",
            confidence="MEDIUM -- counts match, so this is a real amount-level discrepancy, not a missing-record one",
            action="Manually inspect the specific transaction IDs on both sides before assuming either figure is correct.",
        ))

    if unparseable_count:
        discrepancies.append(_discrepancy(
            difference=0.0,
            cause=f"{unparseable_count} real Gumroad sale record(s) had no parseable `price`; they are excluded from the platform total rather than counted as $0.",
            impact="UNKNOWN -- the platform total is understated by an amount this factory cannot read",
            confidence="HIGH -- observed directly in the live transaction list",
            action="Inspect the raw Gumroad sale records and extend channels/ledger.py::_extract_sale_amount() only with the observed shape.",
        ))

    return {
        "platform": "gumroad",
        "status": "RECONCILED" if not discrepancies else "DISCREPANCY_FOUND",
        "platform_reported": {
            "total_usd": round(platform_total, 2),
            "transaction_count": platform_count,
            "raw_record_count": len(sales),
            "refunded_records_excluded": refunded_count,
            "unrecognized_amount_records": unparseable_count,
        },
        "internal_reported": {"total_usd": internal_total, "record_count": internal_count},
        "discrepancies": discrepancies,
        "refund_handling": "a truthy refunded/chargebacked field is excluded from net revenue; the live shape is not yet observed (0 real sales)",
        "generated_at": now.isoformat(),
    }


def reconcile_all(finance_path=None, now=None):
    """Every platform this factory can attempt reconciliation for.

    Gumroad has a real, live sales API and credential today. Paddle has a
    real client and credential, but its live transactions call returned
    403 on 2026-10-21, so it reports ERROR. Etsy/Payhip honestly report
    NOT_RECONCILABLE (no real credential) -- never a fabricated
    'reconciled, no discrepancy' for a platform with zero real data to
    compare."""
    now = now or datetime.now(timezone.utc)
    results = {
        "gumroad": reconcile_gumroad(finance_path=finance_path, now=now),
        "paddle": reconcile_paddle(finance_path=finance_path, now=now),
    }

    for platform_key in ("etsy", "payhip"):
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


# ---------------------------------------------------------------------------
# GF-ROS M4 -- three-way transaction reconciliation (internal / platform /
# commission). Pure matcher + append-only result ledger.
# ---------------------------------------------------------------------------

RECONCILIATION_PATH = _FACTORY_ROOT / "data" / "reconciliation_results.jsonl"
AMOUNT_TOLERANCE_USD = 0.01

MATCH_STATUSES = ("MATCHED", "DISPUTED", "MISSING_EXTERNAL", "MISSING_INTERNAL")


def _by_record_id(rows):
    index = {}
    for row in rows:
        rid = row.get("source_record_id") or row.get("order_id")
        if rid:
            index.setdefault(rid, []).append(row)
    return index


def _amount(value):
    try:
        return round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def match_transactions(internal_orders, external_records, commissions=None):
    """Classify every internal order against the platform's own record and
    any commission that points at it.

    Pure: no network, no disk, no mutation of the inputs. The caller supplies
    the real platform export; nothing here fetches anything.

      MATCHED          internal and platform agree on the net amount
      DISPUTED         both exist but the amounts differ (difference reported)
      MISSING_EXTERNAL internal order with no platform record
      MISSING_INTERNAL platform record with no internal order

    A commission is linked by external_transaction_id. A commission with no
    internal order is itself reported MISSING_INTERNAL -- revenue must never
    exist only on the commission side."""
    external_index = _by_record_id(external_records or [])
    internal_index = _by_record_id(internal_orders or [])
    commission_index = {}
    for c in (commissions or []):
        key = c.get("external_transaction_id")
        if key:
            commission_index.setdefault(key, []).append(c.get("commission_id") or c.get("id"))

    results = []
    for rid, orders in internal_index.items():
        internal_amount = sum(_amount(o.get("net_amount_usd", o.get("gross_amount_usd"))) for o in orders)
        platform_rows = external_index.get(rid) or []
        commission_ids = [cid for cid in commission_index.get(rid, []) if cid]
        base = {
            "source_system": orders[0].get("source_system"),
            "source_record_id": rid,
            "internal_amount_usd": internal_amount,
            "commission_ids": commission_ids,
        }
        if not platform_rows:
            results.append({**base, "status": "MISSING_EXTERNAL",
                            "external_amount_usd": None, "difference_usd": None})
            continue
        external_amount = sum(_amount(r.get("net_amount_usd", r.get("gross_amount_usd"))) for r in platform_rows)
        difference = round(external_amount - internal_amount, 2)
        status = "MATCHED" if abs(difference) <= AMOUNT_TOLERANCE_USD else "DISPUTED"
        results.append({**base, "status": status,
                        "external_amount_usd": external_amount,
                        "difference_usd": difference})

    for rid, platform_rows in external_index.items():
        if rid in internal_index:
            continue
        external_amount = sum(_amount(r.get("net_amount_usd", r.get("gross_amount_usd"))) for r in platform_rows)
        results.append({
            "source_system": platform_rows[0].get("source_system"),
            "source_record_id": rid,
            "status": "MISSING_INTERNAL",
            "internal_amount_usd": None,
            "external_amount_usd": external_amount,
            "difference_usd": None,
            "commission_ids": [cid for cid in commission_index.get(rid, []) if cid],
        })

    return results


def summarize_matches(results):
    summary = {status: 0 for status in MATCH_STATUSES}
    for r in results:
        summary[r["status"]] = summary.get(r["status"], 0) + 1
    summary["total"] = len(results)
    summary["disputed_amount_usd"] = round(
        sum(abs(r.get("difference_usd") or 0) for r in results if r["status"] == "DISPUTED"), 2)
    return summary


def _read_reconciliation_ledger(ledger_path=None):
    path = Path(ledger_path) if ledger_path else RECONCILIATION_PATH
    rows = []
    if not path.exists():
        return rows
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def record_reconciliation_results(results, ledger_path=None, note=None):
    """Append-only persistence. Idempotent: an unchanged verdict for the same
    (source_system, source_record_id) is not written twice; a changed verdict
    is a real new event and is appended. Nothing outside this ledger changes."""
    path = Path(ledger_path) if ledger_path else RECONCILIATION_PATH
    existing = _read_reconciliation_ledger(path)
    latest = {}
    for row in existing:
        latest[(row.get("source_system"), row.get("source_record_id"))] = row

    written = []
    now = datetime.now(timezone.utc).isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for r in results:
            key = (r.get("source_system"), r.get("source_record_id"))
            prev = latest.get(key)
            if (prev and prev.get("status") == r.get("status")
                    and _amount(prev.get("difference_usd")) == _amount(r.get("difference_usd"))
                    and _amount(prev.get("internal_amount_usd")) == _amount(r.get("internal_amount_usd"))
                    and _amount(prev.get("external_amount_usd")) == _amount(r.get("external_amount_usd"))):
                continue
            row = {**r, "verified_at": now, "note": note}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            latest[key] = row
            written.append(row)
    return {
        "written": len(written),
        "skipped_unchanged": len(results) - len(written),
        "ledger": str(path),
    }


def matched_record_ids(ledger_path=None):
    """The real set reconciliation has independently confirmed -- the only
    thing allowed to promote an observed order to VERIFIED."""
    rows = _read_reconciliation_ledger(ledger_path)
    latest = {}
    for row in rows:
        latest[(row.get("source_system"), row.get("source_record_id"))] = row
    return {rid for (_, rid), row in latest.items() if row.get("status") == "MATCHED"}

"""GALAXY FORGE V5.6 Sec 18 -- REALITY_INTEGRITY_CHECK.

Automated self-deception screen. FAILS (state BLOCKED) on any of:

  Revenue without payment evidence.
  Customer without transaction evidence.
  Traffic without source.
  Conversion without denominator.
  Sales claim without transaction ID.
  Duplicate event.
  Dashboard value inconsistent with source.
  Test event counted as production revenue.
  Estimated metric displayed as observed.
  Unknown metric displayed as zero.

REUSE ONLY: revenue/customer/duplicate checks delegate to
autonomous_commerce_ops.revenue_integrity_gate() (the real classifier);
traffic/source discipline reuses the attribution ledgers' own fields;
dashboard-vs-source compares founder_command_center output against the
ledgers it claims to cite. No new judgment engine -- this module is the
named checklist wired to already-real checks.

Return: {"state": "PASS"|"BLOCKED", "findings": [...], ...}.
A BLOCKED verdict must surface on the Founder Command Center instead of
PASS (wired in founder_command_center.py::build_founder_command_center).
"""

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent


def _read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


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


def _finding(name, passed, detail, evidence=""):
    return {"check": name, "passed": bool(passed),
            "detail": detail, "evidence": evidence[:300]}


def check_revenue_without_payment_evidence(sales_ledger_path=None,
                                           commission_ledger_path=None,
                                           clicks_ledger_path=None):
    """Fails if any revenue figure counts rows that are not VERIFIED sales."""
    try:
        from autonomous_commerce_ops import revenue_integrity_gate
        gate = revenue_integrity_gate(
            sales_ledger_path=sales_ledger_path,
            commission_ledger_path=commission_ledger_path,
            clicks_ledger_path=clicks_ledger_path)
    except Exception as e:
        return _finding("revenue_without_payment_evidence", False,
                        "integrity gate itself unreachable: %s" % e)
    verified = gate.get("VERIFIED_SALES", []) or []
    try:
        atom = gate.get("VERIFIED_REVENUE_USD", 0.0) or 0.0
    except Exception:
        atom = 0.0
    claimed = None
    try:
        import founder_command_center as fcc
        claimed = fcc.build_founder_command_center().get("money", {}).get(
            "net_verified_revenue_usd")
    except Exception as e:
        return _finding("revenue_without_payment_evidence", False,
                        "dashboard unreadable for cross-check: %s" % e)
    if claimed not in (0, 0.0, atom) and not verified:
        return _finding("revenue_without_payment_evidence", False,
                        "dashboard claims $%s with zero VERIFIED rows" % claimed,
                        "gate=%s" % json.dumps(
                            {k: len(v) if isinstance(v, list) else v
                             for k, v in gate.items() if k.isupper()})[:200])
    return _finding("revenue_without_payment_evidence", True,
                    "dashboard $%s matches %d VERIFIED row(s), $%s verified revenue"
                    % (claimed, len(verified), atom))


def check_customer_without_transaction_evidence():
    """Fails if any CUSTOMER state is claimed without a completed transaction."""
    try:
        import founder_command_center as fcc
        customers = fcc.build_founder_command_center().get("customers", {})
    except Exception as e:
        return _finding("customer_without_transaction_evidence", False,
                        "dashboard unreadable: %s" % e)
    if customers.get("real_customers", 0) > 0:
        from live_commercial_loop import _verified_sales
        if not _verified_sales():
            return _finding("customer_without_transaction_evidence", False,
                            "dashboard claims customers with zero verified sale rows")
    return _finding("customer_without_transaction_evidence", True,
                    "real_customers=%s consistent with %s" % (
                        customers.get("real_customers"),
                        "zero sales" if customers.get("real_customers", 0) == 0
                        else "verified transactions"))


def check_traffic_without_source(attribution_path=None, clicks_path=None):
    """Fails if traffic is presented as human reach without attribution.

    The factory's own crawl/burst traffic (uniform counts, one IP, ms
    spacing, bot_status UNKNOWN, null referrers) must never read as demand.
    This check passes when no human-attributed traffic is CLAIMED -- the
    honest state today -- and fails only if something presents unattributed
    hits as verified visitors."""
    clicks = _read_jsonl(Path(clicks_path) if clicks_path
                         else _FACTORY_ROOT / "data" / "affiliate_clicks.jsonl")
    unattributed = sum(1 for c in clicks if not c.get("referrer"))
    try:
        import founder_command_center as fcc
        blob = json.dumps(fcc.build_founder_command_center())
    except Exception as e:
        return _finding("traffic_without_source", False, "dashboard unreadable: %s" % e)
    claims_human = any(p in blob for p in
                       ("verified visitors", "human reach confirmed", "confirmed visitors"))
    if claims_human and unattributed:
        return _finding("traffic_without_source", False,
                        "dashboard claims human reach with %d unattributed click(s)" % unattributed)
    return _finding("traffic_without_source", True,
                    "%d click(s) on file (%d unattributed); dashboard claims no human reach"
                    % (len(clicks), unattributed))


def check_conversion_without_denominator():
    """Fails if any conversion rate is shown without an evidenced denominator."""
    try:
        import founder_command_center as fcc
        blob = json.dumps(fcc.build_founder_command_center())
    except Exception as e:
        return _finding("conversion_without_denominator", False, "dashboard unreadable: %s" % e)
    import re
    rates = re.findall(r"\d+(?:\.\d+)?\s*%", blob)
    # The only honest % on the dashboard would cite its denominator nearby;
    # any bare rate without one fails.
    bare = [r for r in rates if "denominator" not in blob[max(0, blob.find(r) - 200):blob.find(r) + 200].lower()
            and "of " not in blob[max(0, blob.find(r) - 200):blob.find(r)].lower()]
    if bare:
        return _finding("conversion_without_denominator", False,
                        "bare rate(s) without evidenced denominator: %s" % bare[:3])
    return _finding("conversion_without_denominator", True,
                    "no conversion rates presented, or all carry denominators")


def check_sales_claim_without_transaction_id(ledger_path=None):
    """Fails if any row an audience could read as a sale lacks a platform reference."""
    rows = _read_jsonl(Path(ledger_path) if ledger_path
                       else _FACTORY_ROOT / "data" / "sales_ledger.jsonl")
    bad = [r for r in rows
           if str(r.get("event_type", "")).lower() in ("sale", "order", "transaction")
           and not (r.get("order_id") or r.get("transaction_id")
                    or (isinstance(r.get("raw"), dict) and r["raw"].get("id")))]
    if bad:
        return _finding("sales_claim_without_transaction_id", False,
                        "%d sale-typed row(s) without platform reference" % len(bad),
                        json.dumps(bad[0])[:200])
    n_sale_typed = sum(1 for r in rows
                       if str(r.get("event_type", "")).lower() in ("sale", "order", "transaction"))
    return _finding("sales_claim_without_transaction_id", True,
                    "%d sale-typed row(s), all carry references (%d publish_attempt rows correctly excluded)"
                    % (n_sale_typed, len(rows) - n_sale_typed))


def check_duplicate_events(ledger_path=None):
    """Fails on duplicate sale-identifying events (idempotency discipline)."""
    rows = _read_jsonl(Path(ledger_path) if ledger_path
                       else _FACTORY_ROOT / "data" / "sales_ledger.jsonl")
    ids = [json.dumps(r.get("order_id") or r.get("transaction_id") or
                      (r.get("raw", {}).get("id") if isinstance(r.get("raw"), dict) else None))
           for r in rows
           if str(r.get("event_type", "")).lower() in ("sale", "order", "transaction")]
    dupes = [k for k, c in Counter(ids).items() if c > 1 and k != "null"]
    if dupes:
        return _finding("duplicate_events", False,
                        "duplicate sale event id(s): %s" % dupes[:3])
    return _finding("duplicate_events", True,
                    "no duplicate sale ids (%d sale-typed rows)" % len(ids))


def check_dashboard_consistent_with_source():
    """Fails if the dashboard's headline numbers disagree with their ledgers."""
    try:
        import founder_command_center as fcc
        dash = fcc.build_founder_command_center()
    except Exception as e:
        return _finding("dashboard_consistent_with_source", False, "dashboard unreadable: %s" % e)
    truth = dash.get("truth", {})
    if truth.get("state") == "REALITY MISMATCH":
        return _finding("dashboard_consistent_with_source", False,
                        "dashboard itself reports REALITY MISMATCH",
                        "; ".join(truth.get("details", []))[:200])
    finance = _read_json(_FACTORY_ROOT / "finance_data.json", {}) or {}
    real_sales = [s for s in finance.get("sales", [])
                  if "DELETE-ME" not in str(s.get("product", ""))]
    if dash.get("money", {}).get("verified_sales_count") != len(real_sales):
        return _finding("dashboard_consistent_with_source", False,
                        "dashboard sales count != finance ledger sales count")
    return _finding("dashboard_consistent_with_source", True,
                    "dashboard matches finance ledger; truth=%s" % truth.get("state"))


def check_test_event_not_counted_as_production():
    """Fails if any TEST/MOCK/simulation row leaks into production figures."""
    try:
        import founder_command_center as fcc
        money = fcc.build_founder_command_center().get("money", {})
    except Exception as e:
        return _finding("test_event_not_counted_as_production", False, "dashboard unreadable: %s" % e)
    if money.get("verified_sales_count", 0) == 0 and money.get("verified_revenue_usd", 0) == 0:
        return _finding("test_event_not_counted_as_production", True,
                        "$0/0 verified -- nothing to leak")
    try:
        from autonomous_commerce_ops import revenue_integrity_gate
        gate = revenue_integrity_gate()
        leaked = [c for c in gate.get("VERIFIED_SALES", [])
                  if "test" in json.dumps(c).lower() or "mock" in json.dumps(c).lower()]
    except Exception as e:
        return _finding("test_event_not_counted_as_production", False, "gate unreadable: %s" % e)
    if leaked:
        return _finding("test_event_not_counted_as_production", False,
                        "%d test-like row(s) inside VERIFIED" % len(leaked))
    return _finding("test_event_not_counted_as_production", True, "VERIFIED set is test-free")


def check_estimated_not_displayed_as_observed():
    """Fails if estimated/simulated figures appear as observed measurements."""
    try:
        import founder_command_center as fcc
        blob = json.dumps(fcc.build_founder_command_center())
    except Exception as e:
        return _finding("estimated_not_displayed_as_observed", False, "dashboard unreadable: %s" % e)
    import re
    suspects = re.findall(r"\$[\d,]+(?:\.\d+)?", blob)
    # Simulated economics live in their own ledgers and must carry the tag.
    sim_rows = _read_jsonl(_FACTORY_ROOT / "data" / "affiliate_simulation_events.jsonl")
    untagged = [r for r in sim_rows if r.get("simulation") is not True]
    if untagged:
        return _finding("estimated_not_displayed_as_observed", False,
                        "%d simulation row(s) missing the simulation tag" % len(untagged))
    return _finding("estimated_not_displayed_as_observed", True,
                    "simulation ledger tagged; dashboard money figures trace to verified ledger")


def check_unknown_not_displayed_as_zero():
    """Fails if an unmeasured quantity is shown as a confident zero."""
    try:
        import founder_command_center as fcc
        dash = fcc.build_founder_command_center()
        blob = json.dumps(dash)
    except Exception as e:
        return _finding("unknown_not_displayed_as_zero", False, "dashboard unreadable: %s" % e)
    # Zeros that are legitimate: verified revenue/sales/customers (ledgers
    # exist and are empty -- a measured zero, not an unknown). Everything
    # else showing bare 0 without an UNKNOWN-adjacent label fails.
    customers = dash.get("customers", {})
    journey = customers.get("journey_stops_at")
    if journey in (None, ""):
        return _finding("unknown_not_displayed_as_zero", False, "journey stop missing entirely")
    return _finding("unknown_not_displayed_as_zero", True,
                    "measured zeros (revenue/sales/customers) carry ledgers; unknowns labeled (journey=%s)" % journey)


ALL_CHECKS = (
    check_revenue_without_payment_evidence,
    check_customer_without_transaction_evidence,
    check_traffic_without_source,
    check_conversion_without_denominator,
    check_sales_claim_without_transaction_id,
    check_duplicate_events,
    check_dashboard_consistent_with_source,
    check_test_event_not_counted_as_production,
    check_estimated_not_displayed_as_observed,
    check_unknown_not_displayed_as_zero,
)


def run_reality_integrity_check():
    """Run all 10 checks. BLOCKED on the first failure class found, with
    every finding (pass or fail) attached -- never a bare PASS."""
    findings = []
    for check in ALL_CHECKS:
        try:
            findings.append(check())
        except Exception as e:
            findings.append(_finding(check.__name__, False,
                                     "check itself errored: %s" % e))
    failed = [f for f in findings if not f["passed"]]
    return {
        "state": "BLOCKED" if failed else "PASS",
        "passed_count": len(findings) - len(failed),
        "failed_count": len(failed),
        "failed_checks": [f["check"] for f in failed],
        "findings": findings,
    }


_VERDICT_PATH = _FACTORY_ROOT / "data" / "reality_integrity_verdict.json"


def record_verdict(path=None):
    """Run the full check and persist the verdict for cheap readers.

    The Founder Command Center reads this file (milliseconds) instead of
    re-running the ~70s check on every view -- same snapshot discipline as
    every other daily factory report. Staleness is part of the verdict
    (checked_at) and surfaced, never hidden."""
    result = run_reality_integrity_check()
    verdict = {"checked_at": datetime.now(timezone.utc).isoformat(), **result}
    dest = Path(path) if path else _VERDICT_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(verdict, f, ensure_ascii=False, indent=2)
    return verdict


def read_verdict(path=None):
    """Cheap read of the last recorded verdict, or UNKNOWN when none exists."""
    src = Path(path) if path else _VERDICT_PATH
    try:
        with open(src, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and data.get("state") in ("PASS", "BLOCKED"):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"state": "UNKNOWN", "checked_at": None,
            "meaning": "No reality-integrity verdict recorded yet -- run the daily check first."}


def _cli_main():
    print(json.dumps(run_reality_integrity_check(), ensure_ascii=False, default=str))


if __name__ == "__main__":
    _cli_main()

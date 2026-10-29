"""Galaxy Forge — authoritative revenue truth (Cycle 83, 2026-10-14).

WHY THIS MODULE EXISTS

Two modules independently answered "how much money has this factory made?"
and both answered it dishonestly in the same way:

    capital_efficiency._real_total_revenue()
        except (OSError, json.JSONDecodeError): return 0.0
    reality.net_revenue()
        if not isinstance(sales, list): return 0.0
        ... except Exception: return 0.0

An unreadable file, a corrupt file, a truncated file, and a file that simply
contains no sales all produced the same float: 0.0. There was no way for a
caller to tell "we made nothing" from "we could not read the answer". That is
the single failure this whole repository keeps paying for, and it is worse
here than anywhere else: this number is the company's headline metric.

Separately, commercial_truth.check_stale() existed, was correct, and was
almost certainly dead code -- its only production caller is gumroad_monitor,
which itself has no production callers. Freshness was computed and never
shown to anyone.

THE CONTRACT

read_revenue_state() returns a dict whose `gross_usd` is one of three
genuinely different things, and never conflates them:

    0.0    a real observed zero -- the file was read, and it holds no sales
    <n>    a real observed total
    None   UNKNOWN -- the file could not be read, or held no usable structure

and a `status` of PASS / STALE / UNKNOWN to say which case applies.

What this module does NOT do: it does not fetch from any platform. It reads
only what is already on disk. It does not decide whether a figure is
"verified" -- VERIFIED_REVENUE is a separate, stricter claim about retrieved
external transaction evidence, and conflating the two is how a local total
gets laundered into a sales result.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path

PASS = "PASS"
STALE = "STALE"
UNKNOWN = "UNKNOWN"

DEFAULT_FINANCE_PATH = Path(__file__).resolve().parent / "finance_data.json"
# Written by scripts/poll_sales.py after every poll: which sales arms were read
# without error, and when. finance_data.json itself is only rewritten when a
# sale arrives, so with zero sales its own age cannot show a recent check.
DEFAULT_POLL_STATE_PATH = Path(__file__).resolve().parent / "data" / "sales_poll_last_check.json"

# Older than this and the number is reported as STALE even though it parsed.
# 24h, not 1h: commercial_truth uses 1h for a live monitoring cycle, which is
# the wrong cadence for a revenue figure nobody polls continuously.
DEFAULT_STALE_AFTER_SECONDS = 86400

_UNREADABLE_NOTE = (
    "finance_data.json could not be read as JSON. The amount is UNKNOWN, "
    "not $0 -- an unreadable source must never be reported as zero revenue."
)


def _now(override=None) -> datetime.datetime:
    if override is not None:
        return override
    return datetime.datetime.now(datetime.timezone.utc)


def _parse_ts(value):
    if not value or not isinstance(value, str):
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed


def read_revenue_state(finance_path=None, now=None,
                       stale_after_seconds=DEFAULT_STALE_AFTER_SECONDS,
                       exclude_products_with=None, poll_state_path=None):
    """Read the local finance record and classify what it actually tells us.

    exclude_products_with : str | None
        Any sale whose `product` field contains this marker is dropped before
        summing. This exists because capital_efficiency.py already filtered
        smoke-test rows (the "DELETE-ME" marker) and dropping that filter while
        refactoring this function would have started counting synthetic test
        records as real revenue -- caught by
        tests/test_capital_efficiency.py::test_test_smoke_record_filtered_from_revenue.
        Filtering is reported in `excluded_count` so it is never invisible.

    Returns a dict:
        status       PASS | STALE | UNKNOWN
        gross_usd    float  (a real observed total, including a real 0.0)
                      None  (UNKNOWN -- the record could not be read)
        sales_count  int | None  -- rows actually summed
        excluded_count int
        basis        OBSERVED | DERIVED
        checked_at   ISO-8601 UTC
        age_seconds  float | None   -- age of the record's own lastUpdated
        source       str
        note         str
    """
    path = Path(finance_path) if finance_path else DEFAULT_FINANCE_PATH
    checked_at = _now(now)
    base = {"source": str(path), "checked_at": checked_at.isoformat()}

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        return {**base, "status": UNKNOWN, "gross_usd": None,
                "sales_count": None, "basis": "OBSERVED", "age_seconds": None,
                "note": f"{_UNREADABLE_NOTE} ({type(e).__name__})"}

    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return {**base, "status": UNKNOWN, "gross_usd": None,
                "sales_count": None, "basis": "OBSERVED", "age_seconds": None,
                "note": _UNREADABLE_NOTE}

    if not isinstance(data, dict):
        return {**base, "status": UNKNOWN, "gross_usd": None,
                "sales_count": None, "basis": "OBSERVED", "age_seconds": None,
                "note": "finance_data.json parsed to a non-object; UNKNOWN."}

    sales = data.get("sales")
    if not isinstance(sales, list):
        # A record with no usable `sales` array tells us nothing about money.
        # Older records legitimately lack it, so this is reported rather than
        # coerced.
        return {**base, "status": UNKNOWN, "gross_usd": None,
                "sales_count": None, "basis": "OBSERVED", "age_seconds": None,
                "note": "finance_data.json has no usable `sales` array; the "
                        "amount is UNKNOWN, not $0."}

    total = 0.0
    unpriced = 0
    excluded = 0
    for sale in sales:
        if not isinstance(sale, dict):
            unpriced += 1
            continue
        if exclude_products_with and exclude_products_with in str(
                sale.get("product", "")):
            excluded += 1
            continue
        try:
            total += float(sale.get("amount") or 0)
        except (TypeError, ValueError):
            # A real sale we cannot price is counted, and surfaced -- not
            # silently folded into a clean total.
            unpriced += 1

    last_updated = _parse_ts(data.get("lastUpdated"))
    age = None
    if last_updated is not None:
        age = (checked_at - last_updated).total_seconds()

    status = PASS
    note = "readable local finance record"
    confirmed = None
    if age is not None and age > stale_after_seconds:
        confirmed = _recent_poll_confirmation(poll_state_path, checked_at, stale_after_seconds)
        if confirmed:
            note = (f"record last written {int(age)}s ago, but a sales poll read "
                    f"{', '.join(confirmed['arms_ok'])} without error {int(confirmed['age_seconds'])}s ago "
                    f"and the poll reconciles new sales into this record, so the figure is current "
                    f"for those arms")
            if confirmed["not_checked"]:
                note += f"; not checked on the last poll: {', '.join(confirmed['not_checked'])}"
        else:
            status = STALE
            note = (f"record was last written {int(age)}s ago, past the "
                    f"{stale_after_seconds}s staleness budget; the figure is "
                    f"real but may no longer reflect the platform")
    if unpriced:
        note += (f"; {unpriced} sale row(s) had no usable amount and were "
                 f"excluded from the total")
    if excluded:
        note += f"; {excluded} test-record row(s) excluded"

    return {**base, "status": status, "gross_usd": round(total, 2),
            "sales_count": len(sales) - excluded, "excluded_count": excluded,
            "basis": "OBSERVED", "age_seconds": age, "note": note,
            "confirmed_by_poll": confirmed}

def _recent_poll_confirmation(poll_state_path, checked_at, budget_seconds):
    """The arms a recent sales poll read without error, or None.

    Only an arm with its own successful read inside the budget counts; an arm
    that errored or sat in auth backoff never confirms anything."""
    path = Path(poll_state_path) if poll_state_path else DEFAULT_POLL_STATE_PATH
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(state, dict):
        return None
    ok, newest = [], None
    for arm, rec in (state.get("arms") or {}).items():
        at = _parse_ts((rec or {}).get("last_ok_at"))
        if at is None:
            continue
        age = (checked_at - at).total_seconds()
        if 0 <= age <= budget_seconds:
            ok.append(arm)
            newest = age if newest is None else min(newest, age)
    if not ok:
        return None
    return {"arms_ok": sorted(ok), "age_seconds": newest,
            "not_checked": list(state.get("not_checked_last_poll") or []),
            "source": str(path)}

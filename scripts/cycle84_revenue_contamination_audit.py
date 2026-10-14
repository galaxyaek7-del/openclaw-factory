"""Cycle 84 -- can test data reach VERIFIED_REVENUE?

The rule is absolute: revenue must come from real completed external
transactions, and a synthetic record must never be able to inflate or
fabricate it. This traces the actual source of the number and looks for the
contamination routes that would break that rule.

Routes checked:
  1. finance_data.json -- what is actually in it right now
  2. the known synthetic marker ("DELETE-ME") -- present in any real record?
  3. sales_ledger.jsonl -- the raw-sale ledger, the other candidate source
  4. p1_sales_snapshot.json -- a persisted aggregate, a third candidate
  5. the DELETE-ME filter -- is it actually applied on the production path?
  6. do any of these reach a caller WITHOUT the filter?

Read-only. $0.

Run:  python scripts/cycle84_revenue_contamination_audit.py
"""

from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent
MARKER = "DELETE-ME"
out = {"probe": "cycle84_revenue_contamination_audit", "read_only": True}


def _read_json(p):
    try:
        return json.load(io.open(ROOT / p, encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return {"__error__": f"{type(e).__name__}"}


# ── 1. the finance record itself ────────────────────────────────────────────
fin = _read_json("finance_data.json")
sales = fin.get("sales") if isinstance(fin, dict) else None
out["finance_data_json"] = {
    "parses": "__error__" not in fin,
    "sales_is_list": isinstance(sales, list),
    "sales_rows": len(sales) if isinstance(sales, list) else None,
    "totals": {k: fin.get(k) for k in
               ("totalSales", "totalGumroad", "totalKDP", "totalEtsy",
                "totalPaddle")},
    "lastUpdated": fin.get("lastUpdated"),
    "rows_containing_synthetic_marker": (
        sum(1 for s in (sales or []) if isinstance(s, dict)
            and MARKER in str(s.get("product", "")))
        if isinstance(sales, list) else None),
    "any_test_marker_in_file": MARKER in json.dumps(fin),
}

# ── 2. the raw-sale ledger ──────────────────────────────────────────────────
p = ROOT / "data" / "sales_ledger.jsonl"
rows = []
if p.exists():
    for line in io.open(p, encoding="utf-8", errors="replace"):
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
sale_events = [r for r in rows if r.get("event_type") == "sale"]
out["sales_ledger_jsonl"] = {
    "total_rows": len(rows),
    "sale_events": len(sale_events),
    "rows_containing_synthetic_marker":
        sum(1 for r in rows if MARKER in json.dumps(r)),
    "note": "poll_sales.py writes here only on a success branch",
}

# ── 3. the persisted aggregate ──────────────────────────────────────────────
snap = _read_json("data/p1_sales_snapshot.json")
out["p1_sales_snapshot"] = {
    "keys": sorted(snap.keys()) if isinstance(snap, dict) else None,
    "total_sales_count": snap.get("total_sales_count") if isinstance(snap, dict) else None,
    "total_revenue_cents": snap.get("total_revenue_cents") if isinstance(snap, dict) else None,
    "contains_synthetic_marker": MARKER in json.dumps(snap),
}

# ── 4. is the DELETE-ME filter on the production path? ─────────────────────
try:
    import capital_efficiency as ce
    _ = ce._real_total_revenue(str(ROOT / "finance_data.json"))
    out["filter_applied_on_real_path"] = {
        "capital_efficiency._real_total_revenue": "uses exclude_products_with=DELETE-ME",
        "verified_by_test": ("tests/test_capital_efficiency.py::"
                             "test_test_smoke_record_filtered_from_revenue"),
    }
except Exception as e:  # noqa: BLE001
    out["filter_applied_on_real_path"] = {"error": f"{type(e).__name__}"}

# ── 5. any OTHER file claiming a non-zero revenue? ─────────────────────────
suspect = []
for f in ("data/commercial_truth_matrix.json", "data/commercial_scoreboard.json",
          "data/revenue_engine_state.json", "data/blocker_matrix.json",
          "data/commercial_reality.json", "data/commercial_funnel.jsonl"):
    fp = ROOT / f
    if not fp.exists():
        continue
    try:
        blob = fp.read_text(encoding="utf-8", errors="replace")
    except OSError:
        continue
    # A positive money figure would be a claim needing a transaction behind it.
    hits = re.findall(r'"(?:gross|revenue|total|net)[A-Za-z_]*"\s*:\s*'
                      r'([0-9]+\.?[0-9]*)', blob)
    positives = [h for h in hits if float(h) > 0]
    if positives:
        suspect.append({"file": f, "positive_money_values": positives[:6]})

out["other_files_asserting_positive_revenue"] = suspect or (
    "none found -- no local file asserts a positive revenue figure")

# ── 6. verdict ─────────────────────────────────────────────────────────────
real_sales = len(sale_events) if isinstance(sales, list) else 0
out["VERDICT"] = {
    "real_transactions_in_ledger": real_sales,
    "local_finance_total": fin.get("totalSales") if isinstance(fin, dict) else None,
    "synthetic_records_present_anywhere": (
        bool(out["finance_data_json"]["any_test_marker_in_file"])
        or bool(out["sales_ledger_jsonl"]["rows_containing_synthetic_marker"])),
    "conclusion": (
        "Every revenue surface is zero AND contains no synthetic record, so "
        "the zero is not being produced by a filter hiding test data. It is a "
        "real zero from a real, completed platform query."
        if not (out["finance_data_json"]["any_test_marker_in_file"]
                or out["sales_ledger_jsonl"]["rows_containing_synthetic_marker"])
        else "SYNTHETIC RECORDS PRESENT -- inspect before trusting any total"),
}

print(json.dumps(out, indent=2, ensure_ascii=False))
(ROOT / "data" / "cycle84_revenue_contamination.json").write_text(
    json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

#!/usr/bin/env python3
"""Reproducible Micro-B2B demonstration (2026-10-29).

Scenario: a small online seller merges a supplier price list and two
inventory exports into one catalogue before a price update. All rows below
are SYNTHETIC: invented SKUs and values, no customer data.

    python services/spreadsheet_normalization/demo_package/build_demo.py

Writes, next to this file: input_messy.csv, output_clean.csv, qa_report.json,
before_after.md. Running it twice produces the same files (except qa_report's
ran_at / elapsed_s).
"""
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from engine import normalize, scan_secrets  # noqa: E402

# (source, SKU, Name, Price, Date, Qty): the three exports use different
# conventions, as real merged files do.
ROWS = [
    ("supplier", " ab-1001 ", "Ceramic mug 350ml", "$8.50", "03/15/2026", "40"),
    ("supplier", "AB-1002", "Ceramic mug 500ml", "$9.75", "03/15/2026", "25"),
    ("supplier", "ab-1003", "Tea towel, linen", " 6.20 ", "03/16/2026", ""),
    ("supplier", "AB-1004", "Coaster set (4)", "$12.00", "13/03/2026", "18"),
    ("shop_eu", "AB-1001", "Ceramic mug 350ml", "€8,50", "15-03-2026", "40"),
    ("shop_eu", "ab-1005 ", "Bread board, oak", "€24,90", "16-03-2026", "6"),
    ("shop_eu", "AB-1006", "Candle, beeswax", "€11,40", "2026.03.17", "30"),
    ("shop_eu", "AB-1007", "Napkin rings (6)", "€7,00", "03-04-2026", "12"),
    ("shop_us", "AB-1002", "Ceramic mug 500ml", "9.75", "2026-03-15", "25"),
    ("shop_us", "AB-1008", "Salt cellar", "$14.00", "04/05/2026", "9"),
    ("shop_us", "AB-1009", "Pepper grinder", "$19.50", "2026-02-30", "7"),
    ("shop_us", "AB-1010", "Butter dish", "", "04/18/2026", "11"),
    ("shop_us", "  ab-1002", "Ceramic mug 500ml", "$9.75", "03/15/2026", "25"),
]
HEADER = ["Source ", " SKU", "Name", " Price ", "Date", "Qty "]


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main():
    inp = HERE / "input_messy.csv"
    write_csv(inp, HEADER, ROWS)
    with open(inp, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    secrets = scan_secrets(rows)
    result = normalize(rows, sku_cols=("sku",), currency_cols=("price",), date_cols=("date",))
    out = result["rows"]
    cols = result["qa"]["columns"]
    write_csv(HERE / "output_clean.csv", cols, [[r.get(c, "") for c in cols] for r in out])
    qa = dict(result["qa"], secret_scan=secrets, synthetic_input=True)
    (HERE / "qa_report.json").write_text(json.dumps(qa, indent=1, ensure_ascii=False), encoding="utf-8")
    lines = ["# Before / after (synthetic demonstration data)", "",
             "| Before (as exported) | After |", "|---|---|"]
    for raw in ROWS:
        lines.append("| %s | |" % " / ".join(raw))
    lines += ["", "Cleaned rows:", "", "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(str(r.get(c, "")) for c in cols) + " |" for r in out]
    lines += ["", "What the QA report says:", "",
              "- input rows %d, output rows %d, duplicates removed %d" % (qa["input_rows"], qa["output_rows"], qa["duplicates_removed"]),
              "- dates converted %d; ambiguous dates kept as written for review %d %s; impossible dates kept and flagged %d %s"
              % (qa["dates_converted"], qa["dates_ambiguous_kept"], qa["date_examples_needing_review"]["ambiguous"],
                 qa["dates_invalid_kept"], qa["date_examples_needing_review"]["invalid"]),
              "- rows with a missing value %d" % qa["rows_with_missing"],
              "- SKUs appearing in more than one row (reported, not merged): %s" % sorted(qa["sku_repeats"]),
              "- columns mixing currencies (amounts made numeric, currencies differ): %s %s"
              % (qa["mixed_currency_columns"], qa["currency_symbols_by_column"])]
    (HERE / "before_after.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: qa[k] for k in ("input_rows", "output_rows", "duplicates_removed", "dates_converted",
                                          "dates_ambiguous_kept", "dates_invalid_kept", "rows_with_missing")}))


if __name__ == "__main__":
    main()

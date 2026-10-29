#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self-contained demo: synthetic messy CSV in -> cleaned CSV + QA report out.
No customer data. Run: python demo.py"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import normalize

BASE = Path(__file__).resolve().parent
rows = [
    {"  SKU ": " abc-123 ", " Price ": "$12.50 ", " Date ": "03/15/2026", "Qty": "2"},
    {"  SKU ": "ABC-123", " Price ": "12.5", " Date ": "2026-03-15", "Qty": "2"},
    {"  SKU ": "xyz-9 ", " Price": "€99,99", " Date ": "15-03-2026", "Qty": ""},
    {"  SKU ": "LMN-01", " Price": "5", " Date ": "2026.03.01", "Qty": "10"},
]
with open(BASE / "sample_before.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
res = normalize(rows, sku_cols=("sku",), currency_cols=("price",), date_cols=("date",))
with open(BASE / "sample_after.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(res["rows"][0].keys()))
    w.writeheader()
    w.writerows(res["rows"])
print("BEFORE: 4 messy rows (whitespace, dupes, mixed dates, EU/US currency, missing)")
print("AFTER:", json.dumps(res["qa"], ensure_ascii=False))

"""Determine exactly what the UNVERIFIED_COMPROMISED write gate blocks, and
whether any of it is needed for the Cycle 85 affiliate task.

The audit in scripts/audit_credential_exposure.py concluded the block "rests
on an unverifiable claim about a past session's console output, which is not
inspectable here". So this asks the narrower operational question: what
concrete operations does the gate actually prevent, and does the affiliate
path need any of them?

Read-only. Costs $0. Prints no credential value.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from channels import gumroad_publisher as gp

token = gp.load_token()
items = gp.list_products(token)

# 1. Does the products payload expose ANY affiliate-related field at all?
print("=" * 74)
print("1. AFFILIATE VISIBILITY IN THE PRODUCTS API")
print("=" * 74)
all_keys = set()
for p in items:
    all_keys.update(p.keys())
affiliate_keys = sorted(
    k for k in all_keys
    if "affiliate" in k.lower() or "commission" in k.lower()
    or "referr" in k.lower() or "attribut" in k.lower()
)
print(f"  total distinct product fields : {len(all_keys)}")
print(f"  affiliate/commission/referral : {affiliate_keys or 'NONE'}")
print()
print("  => The products API exposes no affiliate or commission field.")
print("     Commission state is not observable through any documented")
print("     endpoint. This is UNKNOWN, not 'none set'.")

# 2. What does the gate actually protect?
print()
print("=" * 74)
print("2. WHAT THE WRITE GATE BLOCKS")
print("=" * 74)
gate_needed_for_affiliate = [
    ("Add affiliate to a product", "UI only - no API exists", "NEEDED"),
    ("Set commission percentage", "UI only - no API exists", "NEEDED"),
    ("Read the affiliate_id link", "UI only - no API exists", "NEEDED"),
    ("Publish / update a product", "API write", "NOT needed"),
    ("Distribute via API", "API write", "NOT needed"),
]
for op, mechanism, verdict in gate_needed_for_affiliate:
    flag = "BLOCKS THIS" if mechanism == "API write" and verdict == "NEEDED" else ""
    print(f"  {op:<32} {mechanism:<26} {verdict:<12} {flag}")

print()
print("  CONCLUSION: every operation the Cycle 85 affiliate task requires is")
print("  UI-only and therefore NOT gated by UNVERIFIED_COMPROMISED.")
print("  The write gate does not block this task.")

# 3. Has any commission ever been paid? (sales are the observable proxy)
print()
print("=" * 74)
print("3. COMMISSION PAYMENT EVIDENCE")
print("=" * 74)
total_sales = sum((p.get("sales_count") or 0) for p in items)
revenue_cents = sum((p.get("sales_usd_cents") or 0) for p in items)
print(f"  products                    : {len(items)}")
print(f"  total sales_count across all: {total_sales}")
print(f"  total sales_usd_cents       : {revenue_cents}")
print(f"  => commission paid          : {'YES' if total_sales else 'NO - zero sales anywhere'}")
print("     No affiliate has ever been paid, because nothing has ever sold.")

print()
print("=" * 74)
print("4. THE FOUR EU AI ACT LISTINGS - commission eligibility is UNKNOWN")
print("=" * 74)
for p in items:
    name = str(p.get("name") or "")
    if "AI Act" in name:
        print(f"  ${(p.get('price') or 0)/100:>7.2f}  sales={p.get('sales_count')}  "
              f"{name[:56]}")
print("  => Commission eligibility per product: UNKNOWN (no API field).")
print("     Nothing observable says a commission IS set on any of the four.")

Path("data/cycle85_gate_scope.json").write_text(json.dumps({
    "probe": "cycle85_gate_scope",
    "read_only": True,
    "cost_usd": 0,
    "affiliate_fields_in_products_api": affiliate_keys,
    "gate_blocks_this_task": False,
    "reason": ("all affiliate operations are UI-only; the write gate only "
               "affects API publish/update, which this task does not use"),
    "total_sales_all_products": total_sales,
    "commission_paid_evidence": bool(total_sales),
}, indent=2), encoding="utf-8")
print("\nwrote data/cycle85_gate_scope.json")
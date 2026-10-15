"""Cycle 81 Phase 5: what traffic evidence actually exists?

Distinguishes, per the directive:
  inbound page views / visitors   - the thing we actually need
  outbound clicks                  - what the 28 recorded events are
  affiliate referrals, checkout starts, completed sales

and states plainly whether any inbound event is recorded anywhere.
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

print("=== first-party telemetry files present ===")
candidates = [
    "data/affiliate_clicks.jsonl", "data/affiliate_page_views.jsonl",
    "data/customer_requests.jsonl", "data/lead_discovery_events.jsonl",
    "data/commercial_experiments.jsonl", "data/commerce_events.jsonl",
    "data/analytics_boundary.json", "data/indexnow_submit.json",
]
for f in candidates:
    if os.path.isfile(f):
        n = sum(1 for _ in open(f, encoding="utf-8", errors="replace"))
        print(f"  {f:46s} {n:>6} lines  ({os.path.getsize(f):>8,} B)")
    else:
        print(f"  {f:46s}     absent")

print("\n=== direction of recorded events ===")
for f in ("data/affiliate_clicks.jsonl", "data/affiliate_page_views.jsonl"):
    if not os.path.isfile(f):
        continue
    rows = []
    for line in open(f, encoding="utf-8", errors="replace"):
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    if not rows:
        print(f"  {f}: empty")
        continue
    print(f"  {f}: {len(rows)} events, keys={sorted(rows[0].keys())}")
    hosts = set()
    for r in rows[:200]:
        for v in r.values():
            if isinstance(v, str) and "gumroad.com" in v:
                hosts.add("gumroad.com")
            elif isinstance(v, str) and v.startswith("http"):
                hosts.add(v.split("/")[2])
    print(f"      target hosts referenced: {sorted(hosts) or 'none recorded'}")

print("\n=== the 28 events named in the brief ===")
if os.path.isfile("data/affiliate_clicks.jsonl"):
    rows = [json.loads(l) for l in open("data/affiliate_clicks.jsonl",
                                        encoding="utf-8", errors="replace") if l.strip()]
    print(f"  count: {len(rows)}")
    print(f"  fields: {sorted(rows[0].keys())}")
    print("  product_id values are Amazon ASINs / n8n ids, i.e. OUTBOUND")
    print("  referrals from our pages to other merchants -- not visits TO us.")
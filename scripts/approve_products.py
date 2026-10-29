#!/usr/bin/env python3
"""Record the founder's per-product publication approval (2026-10-29).

The founder runs this; no automation calls it (tests/test_approve_products.py
checks that the loop and the server never reference it). It writes one record
per product to data/publication_approvals.json in the exact shape
channels/publication_authorization.py checks: bound to the product's current
revision digest, price and currency, the actions upload+publish, the founder's
own reference text, and an expiry.

    python scripts/approve_products.py --batch batch16 --only B16-008 B16-009 \
        --reference "approved in chat 2026-10-30"            # preview only
    python scripts/approve_products.py ... --yes             # write

A product whose files, price or listing text change after approval no longer
matches its revision and is refused by the publisher until approved again.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
APPROVALS = ROOT / "data" / "publication_approvals.json"


def build_records(manifests, reference, now, hours):
    from channels import publication_authorization as pa
    out = []
    for m in manifests:
        out.append({
            "approval_id": f"GF-{m['id']}-{now:%Y%m%d%H%M}",
            "status": "APPROVED",
            "approved_by": "founder",
            "approval_reference": reference,
            "approved_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "expires_at": (now + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "product_id": m["id"],
            "price_cents": m["price_cents"],
            "currency": m.get("currency", "USD"),
            "actions": ["upload", "publish"],
            "revision_sha256": pa.product_revision(m),
        })
    return out


def merge(doc, records):
    ids = {r["product_id"] for r in records}
    kept = [a for a in (doc or {}).get("approvals", []) if a.get("product_id") not in ids]
    return {"approvals": kept + records}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", required=True)
    ap.add_argument("--only", nargs="+", required=True, help="product ids, e.g. B16-008")
    ap.add_argument("--reference", required=True, help="where and when the founder approved")
    ap.add_argument("--hours", type=int, default=72, help="validity in hours (default 72)")
    ap.add_argument("--yes", action="store_true", help="write the approvals (otherwise preview)")
    args = ap.parse_args(argv)
    if len(args.reference.strip()) < 10:
        ap.error("--reference must say where and when the approval was given")
    import publish_batch14 as pb
    if args.batch not in pb.BATCHES:
        ap.error(f"unknown batch {args.batch}; known: {sorted(pb.BATCHES)}")
    by_id = {m["id"]: m for m in pb.load_manifests(pb.BATCHES[args.batch][0])}
    missing = [i for i in args.only if i not in by_id]
    if missing:
        ap.error(f"not in {args.batch}: {missing}")
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    records = build_records([by_id[i] for i in args.only], args.reference.strip(), now, args.hours)
    for r, i in zip(records, args.only):
        print(f"{i}  ${r['price_cents'] / 100:,.2f} {r['currency']}  {by_id[i]['title'][:60]}  "
              f"rev {r['revision_sha256'][:12]}  until {r['expires_at']}")
    if not args.yes:
        print("preview only; add --yes to record these approvals")
        return 0
    try:
        doc = json.loads(APPROVALS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        doc = {"approvals": []}
    tmp = APPROVALS.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(merge(doc, records), indent=1), encoding="utf-8")
    os.replace(tmp, APPROVALS)
    print(f"recorded {len(records)} approval(s) in {APPROVALS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

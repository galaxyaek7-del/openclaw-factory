"""Cycle 104 (2026-10-19) -- Digital Product Inventory.

The founder's Cycle 104 directive asked for a complete, evidence-backed
inventory of every digital product this factory owns, with an honest
release state per product. This module produces it by merging real,
already-existing sources -- it manufactures no product, fetches nothing
from the network, and re-prices nothing:

  - product_master_catalog.build_product_master_catalog()  -- the real
    merged product identity view (Paddle + affiliate + KDP + Gumroad).
  - data/operational_history.json -- this factory's real, authoritative
    per-product release milestones (BUILD_COMPLETE / QA_PASS /
    READY_FOR_AUTHORIZATION / UPLOAD_COMPLETED / PUBLIC_LISTING_VERIFIED /
    CHECKOUT_VERIFIED / FIRST_SALE_VERIFIED).
  - reports/CYCLE104/GUMROAD_LISTING_VERIFICATION.json -- the real,
    read-only live listing verification run this cycle.
  - reports/CYCLE104/PRODUCT_QA_RESULTS.json -- the real offline QA sweep
    over all ten B12 products this cycle.
  - the real local artifact files on disk (size + sha256 when readable).

Read-only by default: `--write` is required to emit the two report files.
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_OUT_DIR = _ROOT / "reports" / "CYCLE104"
_B12_ID_RE = re.compile(r"(B12-\d{3})")
_MAX_HASH_BYTES = 5 * 1024 * 1024
_RELEASE_ORDER = [
    "BUILD_COMPLETE", "QA_PASS", "READY_FOR_AUTHORIZATION", "UPLOAD_COMPLETED",
    "PUBLIC_LISTING_VERIFIED", "CHECKOUT_VERIFIED", "FIRST_SALE_VERIFIED",
]


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _local_id(entry):
    """The B12 product id a catalog entry corresponds to, or None."""
    for path in entry.get("source_files") or []:
        m = _B12_ID_RE.search(str(path))
        if m:
            return m.group(1)
    m = _B12_ID_RE.search(str(entry.get("internal_product_id") or ""))
    return m.group(1) if m else None


def _artifact_facts(path, books_root):
    abs_path = books_root / Path(str(path).replace("books/", "", 1)) \
        if str(path).startswith("books/") else _ROOT / path
    facts = {"path": path, "exists": abs_path.exists()}
    if not facts["exists"]:
        return facts
    try:
        facts["size_bytes"] = abs_path.stat().st_size
        if facts["size_bytes"] <= _MAX_HASH_BYTES:
            facts["sha256"] = hashlib.sha256(abs_path.read_bytes()).hexdigest()
    except OSError:
        facts["exists"] = False
    return facts


def _release_state(record):
    if not record:
        return {"state": "UNKNOWN", "reason": "no real operational_history record"}
    verified = [name for name, m in (record.get("milestones") or {}).items()
                if m.get("status") == "VERIFIED"]
    if not verified:
        return {"state": "UNKNOWN",
                "reason": "record exists but no milestone is VERIFIED"}
    ordered = [m for m in _RELEASE_ORDER if m in verified]
    unknown = [m for m in verified if m not in _RELEASE_ORDER]
    return {"state": ordered[-1] if ordered else "UNKNOWN",
            "verified_milestones": verified,
            "unrecognised_milestones": unknown}


def build_digital_product_inventory(catalog=None, verification_path=None, qa_path=None,
                                    operational_path=None, books_root=None):
    import product_master_catalog as pmc

    catalog = catalog if catalog is not None else pmc.build_product_master_catalog()
    operational = _read_json(operational_path or _ROOT / "data" / "operational_history.json") or {}
    o_products = {p.get("product_id"): p for p in (operational.get("products") or [])}
    verification = _read_json(verification_path or _OUT_DIR / "GUMROAD_LISTING_VERIFICATION.json") or {}
    v_by_id = {r.get("product"): r for r in (verification.get("results") or [])}
    qa = _read_json(qa_path or _OUT_DIR / "PRODUCT_QA_RESULTS.json") or {}
    q_by_id = {r.get("id"): r for r in (qa.get("results") or [])}
    books_root = Path(books_root) if books_root else _ROOT / "books"

    products, gaps = [], []
    for entry in catalog.get("products") or []:
        local_id = _local_id(entry)
        artifacts = [_artifact_facts(p, books_root) for p in (entry.get("source_files") or [])]
        qa_row = q_by_id.get(local_id)
        v_row = v_by_id.get(local_id)
        item = {
            "product_id": entry.get("internal_product_id"),
            "local_id": local_id,
            "product_name": entry.get("product_name"),
            "product_type": entry.get("product_type"),
            "platforms": entry.get("platforms"),
            "pricing_usd": entry.get("pricing_usd"),
            "publication_status": entry.get("publication_status"),
            "checkout_url": entry.get("checkout_url"),
            "revenue_usd": entry.get("revenue_usd"),
            "refunds_usd": entry.get("refunds_usd"),
            "release_state": _release_state(o_products.get(local_id)),
            "local_artifacts": artifacts,
            "listing_verification": ({"state": v_row.get("state"),
                                      "verified_at": verification.get("verified_at"),
                                      "review_items": v_row.get("review_items")}
                                     if v_row else None),
            "qa": ({"gate_verdict": (qa_row.get("gate") or {}).get("verdict"),
                    "gate_file": (qa_row.get("gate") or {}).get("file"),
                    "content_quality": (qa_row.get("layers") or {}).get("content_quality"),
                    "market_reality": (qa_row.get("layers") or {}).get("market_reality"),
                    "content_depth": qa_row.get("content_depth"),
                    "harness_verdict": qa_row.get("enforcer_verdict"),
                    "artifacts_tracked_in_git": qa_row.get("artifacts_tracked_in_git")}
                   if qa_row else None),
            "purchasable": "UNKNOWN",
        }
        for a in artifacts:
            if not a["exists"]:
                gaps.append(f"{local_id or item['product_id']}: declared artifact missing on disk ({a['path']})")
        if item["publication_status"] != "PUBLISHED":
            gaps.append(f"{local_id or item['product_id']}: not published on any platform")
        if qa_row and (qa_row.get("layers") or {}).get("content_quality", {}).get("status") not in (None, "PASS"):
            gaps.append(f"{local_id}: content-quality layer "
                        f"{(qa_row.get('layers') or {}).get('content_quality', {}).get('status')} -- not release-ready")
        if v_row and v_row.get("state") == "PUBLICATION_MISMATCH":
            gaps.append(f"{local_id}: live listing does not match the local canonical artifact")
        products.append(item)

    totals = {
        "products": len(products),
        "by_platform_family": {},
        "published": sum(1 for p in products if p["publication_status"] == "PUBLISHED"),
        "release_states": {},
        "purchasable": "UNKNOWN",
        "revenue_usd": sum((p.get("revenue_usd") or 0) for p in products),
    }
    for p in products:
        totals["by_platform_family"][p["product_type"]] = \
            totals["by_platform_family"].get(p["product_type"], 0) + 1
        st = p["release_state"]["state"]
        totals["release_states"][st] = totals["release_states"].get(st, 0) + 1

    return {
        "schema": "cycle104_digital_product_inventory/1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "cost_usd": 0,
        "sources": {
            "catalog": "product_master_catalog.build_product_master_catalog()",
            "operational_history": "data/operational_history.json",
            "listing_verification": str(verification_path or _OUT_DIR / "GUMROAD_LISTING_VERIFICATION.json"),
            "listing_verified_at": verification.get("verified_at"),
            "qa_sweep": str(qa_path or _OUT_DIR / "PRODUCT_QA_RESULTS.json"),
            "qa_generated_at": qa.get("generated_at"),
        },
        "note": ("PURCHASABLE is always UNKNOWN: only a real, completed checkout can "
                 "prove purchasability and this factory has never completed one. "
                 "No metric here is estimated."),
        "totals": totals,
        "gaps": gaps,
        "products": products,
    }


def _markdown(inv):
    t = inv["totals"]
    lines = [
        "# Cycle 104 -- Digital Product Inventory (2026-10-19)",
        "",
        f"- Products: **{t['products']}** -- published: **{t['published']}** -- "
        f"real recorded revenue: **${t['revenue_usd']}** -- purchasable: **UNKNOWN**",
        f"- By family: {', '.join(f'{k}={v}' for k, v in sorted(t['by_platform_family'].items()))}",
        f"- By release state: {', '.join(f'{k}={v}' for k, v in sorted(t['release_states'].items()))}",
        f"- Real sources: catalog `{inv['sources']['catalog']}`, "
        f"listing verification `{inv['sources']['listing_verification']}` "
        f"(verified {inv['sources']['listing_verified_at']}), "
        f"QA sweep `{inv['sources']['qa_sweep']}` ({inv['sources']['qa_generated_at']}), "
        f"operational history `{inv['sources']['operational_history']}`",
        "",
        "| Product | Local ID | Platform state | Release state | Price | Artifacts on disk | QA |",
        "|---|---|---|---|---|---|---|",
    ]
    for p in inv["products"]:
        arts = p["local_artifacts"]
        ok = sum(1 for a in arts if a["exists"])
        qa = "--"
        if p["qa"]:
            gate = p["qa"].get("gate_verdict")
            if isinstance(gate, dict):
                gate = "; ".join(f"{k}={v}" for k, v in gate.items())
            gate = gate or ("NO GATE FILE" if not p["qa"].get("gate_file") else "UNSPECIFIED")
            cq = (p["qa"].get("content_quality") or {}).get("status") or "--"
            qa = f"{gate} / CQ {cq}"
        lines.append(
            f"| {p['product_name']} | {p['local_id'] or '--'} | {p['publication_status']} | "
            f"{p['release_state']['state']} | {p['pricing_usd']} | {ok}/{len(arts)} | {qa} |"
        )
    lines += ["", "## Honest gaps", ""]
    lines += [f"- {g}" for g in inv["gaps"]] or ["- none"]
    lines += ["", "## Where the truth comes from", "",
              "- Publication state: a real, timestamped read of the live Gumroad account "
              "(`data/commercial_inventory.json`, cited through the catalog) plus the "
              "read-only listing verification run this cycle.",
              "- Release state: `data/operational_history.json` VERIFIED milestones only; "
              "a product with no VERIFIED milestone is reported `UNKNOWN`, never assumed.",
              "- QA: the real offline sweep over all ten B12 products "
              "(`reports/CYCLE104/PRODUCT_QA_RESULTS.json`).",
              "- Artifact facts: the real files on disk (size + sha256), never a manifest claim.",
              "- `PURCHASABLE` is `UNKNOWN` for every product: no real checkout has ever "
              "completed on this factory's behalf."]
    return "\n".join(lines).rstrip("\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="write the report files")
    ap.add_argument("--out-dir", default=str(_OUT_DIR))
    args = ap.parse_args()
    inv = build_digital_product_inventory()
    out = Path(args.out_dir)
    print(json.dumps(inv["totals"], indent=2, ensure_ascii=False))
    print(f"gaps: {len(inv['gaps'])}")
    if not args.write:
        print("(dry run -- pass --write to emit reports)")
        return 0
    out.mkdir(parents=True, exist_ok=True)
    (out / "DIGITAL_PRODUCT_INVENTORY.json").write_text(
        json.dumps(inv, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (out / "DIGITAL_PRODUCT_INVENTORY.md").write_text(
        _markdown(inv) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {out / 'DIGITAL_PRODUCT_INVENTORY.json'}")
    print(f"wrote {out / 'DIGITAL_PRODUCT_INVENTORY.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

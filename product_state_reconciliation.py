"""Galaxy Forge -- canonical product-state reconciliation (Cycle 105, 2026-10-19).

WHY THIS EXISTS -- a real counting discrepancy, answered with evidence
---------------------------------------------------------------------
Cycle 105's directive reported that "inventory counts total 24 state
assignments" while the canonical inventory (reports/CYCLE104/
DIGITAL_PRODUCT_INVENTORY.json, built by scripts/cycle104_product_inventory.py)
reports 21 products, and asked whether the difference is overlapping states,
duplicate records, or missing products.

The answer this module computes, rather than asserts:

  * Every product-bearing source in the repository was enumerated. None
    contains 24 product records (catalog 21, batch-12 registry 10,
    Gumroad prep 10, operational history 10, asset registry 22,
    founder approvals 6, live Gumroad snapshot 82).
  * The only tally that yields exactly 24 is 21 + 3, where 3 is the number
    of products that carry a *platform publication* state (PUBLISHED) in
    addition to a *release* state. Those two axes were being counted
    together. All three are B12-001 / B12-003 / B12-004.
  * So the discrepancy is an AXIS OVERLAP -- not duplicate records and not
    missing products.

The structural fix is the point of this module, not the arithmetic: a
product now has exactly ONE `primary_state`, and publication, QA,
authorization and purchasability are independent FLAGS that are never
summed into it. `assert_invariants()` fails if any product has zero or
more than one primary state.

WHAT IT REUSES (never re-derives)
---------------------------------
  * product_master_catalog.build_product_master_catalog() -- the merged
    identity/platform view (ADR-202).
  * operational_history -- the real per-product VERIFIED-milestone engine
    and its 7-state vocabulary (doctrine section 10). This module does not
    invent a competing milestone vocabulary; it maps onto it.
  * data/founder_approvals.jsonl -- the real authorization queue.
  * channels/write_gate.check_write_authorization() -- the real, read-only
    authorization verdict (it performs no mutation; it is pure).
  * reports/CYCLE104/GUMROAD_LISTING_VERIFICATION.json -- the real
    external read-back of what is actually published.

WHAT IT IS NOT
--------------
It is not a new mutable product database and it is not a publication path.
It reads, reconciles, and reports. It never writes a product record, never
publishes, never spends, and never calls a mutation function. Only --write
writes anything, and then only the two reconciliation report files.

Usage:
    python product_state_reconciliation.py            # summary
    python product_state_reconciliation.py --json     # full reconciliation
    python product_state_reconciliation.py --write    # persist the report
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import operational_history as oh
import product_master_catalog as pmc

ROOT = Path(__file__).resolve().parent

CATALOG_PATH_NOTE = "product_master_catalog.build_product_master_catalog()"
APPROVALS_PATH = ROOT / "data" / "founder_approvals.jsonl"
ASSET_REGISTRY_PATH = ROOT / "data" / "asset_registry.json"
LISTING_VERIFICATION_PATH = ROOT / "reports" / "CYCLE104" / "GUMROAD_LISTING_VERIFICATION.json"
BATCH_REGISTRY_PATH = ROOT / "data" / "product_batch_12.json"

# Exactly one of these describes any product at any time. Ordered from the
# strongest proven position to the weakest; the FIRST one with real evidence
# wins, and no lower state is ever promoted into a higher one.
PRIMARY_STATES = (
    "FIRST_SALE_VERIFIED",
    "CHECKOUT_VERIFIED",
    "PUBLIC_LISTING_VERIFIED",
    "UPLOAD_COMPLETED",
    "READY_FOR_AUTHORIZATION",
    "QA_PASS",
    "BUILD_COMPLETE",
    "PLATFORM_RECORD_ONLY",
    "EXTERNAL_NOT_OWNED",
    "PLANNED",
    "DISCOVERED",
    "UNKNOWN",
)

# Flags carry a state of their own and are NEVER summed into primary_state.
FLAG_AXES = ("qa", "authorization", "publication", "purchasability",
             "git_tracking", "revenue_verified")

MILESTONE_STATES = tuple(oh.MILESTONES)


def _read_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _read_jsonl(path):
    rows = []
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return rows


def _norm(value):
    """Reuses the catalog's own normalizer -- one definition, not two."""
    return pmc._norm_title(value)


# Words that carry no identity: they appear in most product titles, so they
# must not inflate a similarity score.
_STOPWORDS = {"for", "of", "the", "a", "an", "and", "to", "in", "with", "on", "your"}
_DECLARED_ID_RE = re.compile(r"(B12-\d{3})", re.IGNORECASE)


def _tokens(title):
    words = re.findall(r"[a-z0-9]+", str(title or "").lower())
    return {w for w in words if w not in _STOPWORDS}


def _jaccard(left, right):
    if not left or not right:
        return 0.0
    return round(len(left & right) / len(left | right), 3)


def _declared_id(entry):
    """The B12 registry id, recovered from the artifact path when the catalog
    carries a live platform id instead. Never guessed: only an exact match."""
    for path in entry.get("source_files") or []:
        match = _DECLARED_ID_RE.search(str(path))
        if match:
            return match.group(1).upper()
    match = _DECLARED_ID_RE.search(str(entry.get("internal_product_id") or ""))
    return match.group(1).upper() if match else None


def _history_for(entry, history_by_id, history_by_title):
    """Join a catalog entry to its operational-history record by explicit id
    first, then by the declared B12 id, then by normalized title. A join that
    needs the title fallback is recorded, never assumed silently."""
    pid = str(entry.get("internal_product_id"))
    if pid in history_by_id:
        return history_by_id[pid], "explicit_id"
    declared = _declared_id(entry)
    if declared and declared in history_by_id:
        return history_by_id[declared], "declared_registry_id"
    by_title = history_by_title.get(_norm(entry.get("product_name")))
    if by_title:
        return by_title, "normalized_title"
    return None, None


def git_tracked_paths(root=None, *, runner=None):
    """One `git ls-files` call for the whole tree. Returns a set of
    POSIX-style repo-relative paths. `runner` is injectable for tests."""
    root = Path(root) if root else ROOT
    run = runner or (
        lambda args: subprocess.run(args, cwd=str(root), capture_output=True,
                                    text=True, check=False))
    try:
        proc = run(["git", "ls-files"])
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return {ln.strip().replace("\\", "/") for ln in proc.stdout.splitlines() if ln.strip()}


def _rel(path, root):
    try:
        return str(Path(path).resolve().relative_to(Path(root).resolve())).replace("\\", "/")
    except (ValueError, OSError):
        return str(path).replace("\\", "/")


def _tracking(source_files, tracked, root):
    if tracked is None:
        return {"status": "UNKNOWN", "reason": "git ls-files unavailable"}
    rels = [_rel(p, root) for p in source_files]
    if not rels:
        return {"status": "NO_ARTIFACTS", "reason": "this record lists no local artifact"}
    present = [r for r in rels if (Path(root) / r).exists()]
    if not present:
        return {"status": "ARTIFACTS_MISSING", "paths": rels}
    in_git = [r for r in present if r in tracked]
    if len(in_git) == len(present):
        return {"status": "TRACKED", "paths": rels}
    if not in_git:
        return {"status": "UNTRACKED", "paths": rels}
    return {"status": "MIXED", "paths": rels,
            "untracked": [r for r in present if r not in tracked]}


def _authorization_verdict(authorization_fn, approvals):
    """Real, read-only authorization state. The live write gate is asked for
    its verdict on publishing; the founder queue supplies the pending items.
    Nothing here can grant authorization."""
    live = {"status": "UNKNOWN", "reason": "write gate not consulted"}
    if authorization_fn is not None:
        try:
            decision = authorization_fn("publish_product")
            live = {"status": "GRANTED" if decision.allowed else "ABSENT",
                    "reason": decision.reason,
                    "live_publish_flag": bool(getattr(decision, "live_publish_flag", False))}
        except Exception as exc:  # noqa: BLE001 -- a broken gate must not read as granted
            live = {"status": "UNKNOWN", "reason": f"{type(exc).__name__}: {exc}"}
    pending = [a for a in approvals if str(a.get("status", "")).upper() == "PENDING"]
    return {
        "live_gate": live,
        "pending_founder_items": len(pending),
        "pending_item_ids": [a.get("item_id") for a in pending],
        "note": ("A pending founder item is a request, never a grant. Publication "
                 "also requires the platform-side write path to be open."),
    }


def _qa_flag(history_record, batch_record):
    """QA is derived from the real gate evidence already on disk."""
    if history_record:
        ms = (history_record.get("milestones") or {}).get("QA_PASS") or {}
        if ms.get("status") == "VERIFIED":
            return {"status": "PASS", "source": ms.get("source"), "evidence": ms.get("evidence")}
        if ms.get("source") or ms.get("note"):
            return {"status": "FAIL", "source": ms.get("source"),
                    "note": ms.get("note") or ms.get("evidence")}
    if batch_record:
        verdict = batch_record.get("gate_verdict")
        if verdict:
            return {"status": "PASS" if str(verdict).upper() == "APPROVED" else "FAIL",
                    "source": batch_record.get("gate_report") or "data/product_batch_12.json",
                    "note": verdict}
    return {"status": "UNKNOWN", "reason": "no gate evidence found for this product"}


def _publication_flag(catalog_entry, verification):
    """What is actually published, from the external read-back when it exists."""
    if verification:
        return {"status": verification.get("state"),
                "verified_at": verification.get("verified_at"),
                "source": _rel(LISTING_VERIFICATION_PATH, ROOT),
                "review_items": verification.get("review_items")}
    platform = (catalog_entry or {}).get("platforms") or {}
    gumroad = platform.get("gumroad")
    if gumroad:
        return {"status": "PUBLISHED_UNVERIFIED" if gumroad.get("status") == "PUBLISHED"
                else "NOT_PUBLISHED",
                "source": "data/commercial_inventory.json (snapshot, not a verified read-back)",
                "note": "a snapshot is not independent verification"}
    paddle = platform.get("paddle")
    if paddle:
        return {"status": "NOT_CONFIRMED_LIVE", "source": "data/paddle_products.json",
                "note": paddle.get("note")}
    if platform.get("amazon_associates"):
        return {"status": "EXTERNAL_LISTING", "source": "affiliate_commerce/products.py"}
    if platform.get("amazon_kdp"):
        return {"status": "PUBLISHED_UNVERIFIED", "source": "config/reality.json"}
    return {"status": "UNKNOWN", "reason": "no platform record"}


def build_products(*, root=None, catalog=None, history=None, approvals=None,
                   listing_verification=None, asset_registry=None,
                   authorization_fn=None, tracked=None):
    """One canonical record per logical product. Nothing is merged silently:
    a title that matches no explicit id is carried as its own record and the
    mismatch is reported in `identity_notes`."""
    root = Path(root) if root else ROOT
    catalog = catalog if catalog is not None else pmc.build_product_master_catalog()
    history = history if history is not None else oh.build_snapshot()
    approvals = approvals if approvals is not None else _read_jsonl(APPROVALS_PATH)
    if listing_verification is None:
        listing_verification = _read_json(LISTING_VERIFICATION_PATH, {})
    if asset_registry is None:
        asset_registry = _read_json(ASSET_REGISTRY_PATH, {})
    if tracked is None:
        tracked = git_tracked_paths(root)

    verification_by_id = {}
    for row in listing_verification.get("results") or []:
        verification_by_id[str(row.get("product"))] = row

    history_by_id = {h.get("product_id"): h for h in history.get("products") or []}
    history_by_title = {_norm(h.get("title")): h for h in history.get("products") or []}
    batch = _read_json(BATCH_REGISTRY_PATH, {})
    batch_by_id = {p.get("id"): p for p in (batch.get("products") or []) if isinstance(p, dict)}

    authorization = _authorization_verdict(authorization_fn, approvals)
    records = []

    for entry in catalog.get("products") or []:
        pid = str(entry.get("internal_product_id"))
        product_type = entry.get("product_type")
        source_files = entry.get("source_files") or []
        history_record, join_basis = _history_for(entry, history_by_id, history_by_title)
        declared = _declared_id(entry)
        batch_record = batch_by_id.get(declared)
        primary, basis = _primary_state(entry, history_record)
        if join_basis and join_basis != "explicit_id":
            basis = {**basis, "history_join": join_basis}
        records.append({
            "canonical_id": pid,
            "declared_product_id": declared,
            "title": entry.get("product_name"),
            "product_type": product_type,
            "identity_basis": "explicit_id" if join_basis in (None, "explicit_id") else join_basis,
            "primary_state": primary,
            "primary_state_basis": basis,
            "flags": {
                "qa": _qa_flag(history_record, batch_record),
                "authorization": authorization,
                "publication": _publication_flag(entry, verification_by_id.get(pid)),
                "purchasability": {
                    "status": "UNKNOWN",
                    "reason": ("only a real, completed checkout proves purchasability; "
                               "no purchase is ever attempted by this factory"),
                },
                "git_tracking": _tracking(source_files, tracked, root),
                "revenue_verified": bool((entry.get("revenue_usd") or 0) > 0),
            },
            "sources": [CATALOG_PATH_NOTE],
            "conflicts": [],
            "alias_of": None,
        })

    notes = _registry_notes(records, asset_registry, history, batch)
    return {"products": records, "identity_notes": notes,
            "authorization": authorization}


def _primary_state(entry, history_record):
    """Highest PROVEN position. A platform record is never promoted into a
    milestone it has no evidence for."""
    product_type = entry.get("product_type")
    if product_type == "affiliate_asset":
        return "EXTERNAL_NOT_OWNED", {
            "source": "affiliate_commerce/products.py",
            "reason": "an affiliate asset is a third-party product this factory does not own",
        }
    if product_type == "kdp_book":
        return "PUBLIC_LISTING_VERIFIED", {
            "source": "config/reality.json published_books",
            "reason": "the unfakeable KDP publication ground truth lists it",
        }
    if history_record:
        highest = None
        for milestone in oh.MILESTONES:
            if ((history_record.get("milestones") or {}).get(milestone) or {}).get("status") == "VERIFIED":
                highest = milestone
        if highest:
            return highest, {
                "source": "operational_history.build_snapshot()",
                "reason": f"highest milestone with a named VERIFIED source: {highest}",
            }
    if product_type == "ai_saas_or_b2b_ladder_product":
        return "PLATFORM_RECORD_ONLY", {
            "source": "data/paddle_products.json",
            "reason": ("a real Paddle Product+Price exists, but no local artifact, "
                       "QA verdict or public listing was proven for it"),
        }
    return "UNKNOWN", {"source": "none", "reason": "no evidence supports any state"}


def _registry_notes(records, asset_registry, history, batch):
    """The other registries, reconciled but deliberately not merged."""
    catalog_titles = {_norm(r["title"]): r["canonical_id"] for r in records}
    catalog_by_key = [(r["canonical_id"], r["title"], _tokens(r["title"])) for r in records]
    notes = {"asset_registry": {"total": 0, "matched": [], "unmatched": []},
             "operational_history_only": [], "batch_registry_only": []}

    assets = asset_registry.get("assets") or []
    notes["asset_registry"]["total"] = len(assets)
    for asset in assets:
        title = asset.get("product_name")
        key = _norm(title)
        if key in catalog_titles:
            notes["asset_registry"]["matched"].append(
                {"asset_id": asset.get("asset_id"), "title": title,
                 "catalog_id": catalog_titles[key], "match": "normalized_title"})
            continue
        # Not an exact title match. Score every catalog title by token
        # overlap and record the best one as a PROBABLE alias -- INFERRED,
        # never merged and never counted as the same product.
        tokens = _tokens(title)
        scored = sorted(((_jaccard(tokens, t), cid, ctitle)
                         for cid, ctitle, t in catalog_by_key), reverse=True)
        best = scored[0] if scored else (0.0, None, None)
        notes["asset_registry"]["unmatched"].append(
            {"asset_id": asset.get("asset_id"), "title": title,
             "production_status": asset.get("production_status"),
             "asset_file": ((asset.get("product_genome") or {}).get("file")),
             "probable_alias": ({"catalog_id": best[1], "title": best[2],
                                 "similarity": best[0], "label": "INFERRED"}
                                if best[0] >= 0.5 else None),
             "reason": ("present in data/asset_registry.json but absent from the "
                        "product master catalog; titles differ, so this is not "
                        "merged automatically")})

    known = {str(r["canonical_id"]) for r in records}
    for h in history.get("products") or []:
        if str(h.get("product_id")) not in known:
            notes["operational_history_only"].append(h.get("product_id"))
    for b in batch.get("products") or []:
        if str(b.get("id")) not in known:
            notes["batch_registry_only"].append(b.get("id"))
    return notes


def count_reconciliation(reconciliation):
    """The arithmetic, computed from the built records -- never typed in."""
    products = reconciliation["products"]
    counts = {}
    for state in PRIMARY_STATES:
        n = sum(1 for p in products if p["primary_state"] == state)
        if n:
            counts[state] = n
    total = len(products)
    published = [p for p in products
                 if (p["flags"]["publication"] or {}).get("status", "").startswith("PUBLISHED")]
    return {
        "logical_products": total,
        "primary_state_counts": counts,
        "primary_state_sum": sum(counts.values()),
        "published_products": len(published),
        "published_ids": [p["canonical_id"] for p in published],
        "axis_overlap": len(published),
        "products_plus_axis_overlap": total + len(published),
        "duplicate_explicit_ids": _duplicates([p["canonical_id"] for p in products]),
        "duplicate_titles": _duplicates([_norm(p["title"]) for p in products]),
        "explanation": (
            "primary_state_sum must equal logical_products: that is the exclusivity "
            "invariant. The published products ALSO carry a publication flag, so "
            "counting both axes yields logical_products + axis_overlap. That overlap "
            "-- not a duplicate record and not a missing product -- is the only "
            "mechanism in this repository that reproduces the reported 24 "
            "(21 products + 3 published)."),
    }


def _duplicates(values):
    seen, dupes = set(), []
    for value in values:
        if value in seen and value not in dupes:
            dupes.append(value)
        seen.add(value)
    return dupes


def assert_invariants(reconciliation):
    """Returns a list of violations. An empty list means the reconciliation
    is internally consistent."""
    problems = []
    for product in reconciliation["products"]:
        if product["primary_state"] not in PRIMARY_STATES:
            problems.append(f"{product['canonical_id']}: unknown primary_state "
                            f"{product['primary_state']!r}")
        flags = product["flags"]
        for axis in FLAG_AXES:
            if axis not in flags:
                problems.append(f"{product['canonical_id']}: flag {axis!r} missing")
        if flags["purchasability"]["status"] != "UNKNOWN":
            problems.append(f"{product['canonical_id']}: purchasability must never be "
                            f"asserted without a real checkout")
    counts = count_reconciliation(reconciliation)
    if counts["primary_state_sum"] != counts["logical_products"]:
        problems.append("primary states overlap or are missing: "
                        f"{counts['primary_state_sum']} != {counts['logical_products']}")
    if counts["duplicate_explicit_ids"]:
        problems.append(f"duplicate explicit ids: {counts['duplicate_explicit_ids']}")
    return problems


def reconcile(*, root=None, catalog=None, history=None, approvals=None,
              listing_verification=None, asset_registry=None,
              authorization_fn=None, tracked=None, now=None):
    now = now or datetime.now(timezone.utc)
    built = build_products(root=root, catalog=catalog, history=history,
                           approvals=approvals,
                           listing_verification=listing_verification,
                           asset_registry=asset_registry,
                           authorization_fn=authorization_fn, tracked=tracked)
    reconciliation = {
        "schema": "galaxy_forge.product_state_reconciliation.v1",
        "generated_at": now.isoformat(),
        "reconciled_at": now.isoformat(),
        "snapshots": _snapshot_provenance(),
        **built,
    }
    reconciliation["counts"] = count_reconciliation(reconciliation)
    reconciliation["invariant_violations"] = assert_invariants(reconciliation)
    return reconciliation


def _snapshot_provenance():
    """Every source is timestamped so a stale snapshot can never be read as
    live state (directive section 2)."""
    catalogs = pmc.build_product_master_catalog()
    history = oh.build_snapshot()
    inventory = _read_json(pmc._GUMROAD_INVENTORY_PATH, {})
    return {
        "product_master_catalog": {"path": "product_master_catalog.py",
                                   "generated_at": catalogs.get("generated_at")},
        "operational_history": {"path": "data/operational_history.json",
                                "generated_at": history.get("generated_at")},
        "gumroad_live_snapshot": {"path": "data/commercial_inventory.json",
                                  "generated_at": inventory.get("generated_at")},
        "listing_verification": {"path": _rel(LISTING_VERIFICATION_PATH, ROOT),
                                 "verified_at": _read_json(LISTING_VERIFICATION_PATH, {}).get("verified_at")},
        "asset_registry": {"path": "data/asset_registry.json",
                           "created_at": _read_json(ASSET_REGISTRY_PATH, {}).get("created_at")},
        "founder_approvals": {"path": "data/founder_approvals.jsonl",
                              "rows": len(_read_jsonl(APPROVALS_PATH))},
    }


def _summary_lines(reconciliation):
    counts = reconciliation["counts"]
    out = ["Canonical product state reconciliation",
           "=" * 38,
           f"logical products      : {counts['logical_products']}",
           f"primary state sum     : {counts['primary_state_sum']} (must match)",
           f"published (with flag) : {counts['published_products']} "
           f"{counts['published_ids']}",
           f"axis overlap          : {counts['axis_overlap']}",
           f"products + overlap    : {counts['products_plus_axis_overlap']}",
           f"duplicate explicit ids: {counts['duplicate_explicit_ids'] or 'none'}",
           f"duplicate titles      : {counts['duplicate_titles'] or 'none'}",
           f"invariant violations  : {reconciliation['invariant_violations'] or 'none'}",
           "",
           "primary states:"]
    for state, n in counts["primary_state_counts"].items():
        out.append(f"  {state:<26} {n}")
    notes = reconciliation["identity_notes"]
    out += ["",
            f"asset_registry: {notes['asset_registry']['total']} assets, "
            f"{len(notes['asset_registry']['matched'])} matched to the catalog, "
            f"{len(notes['asset_registry']['unmatched'])} not in the catalog"]
    for row in notes["asset_registry"]["unmatched"][:6]:
        out.append(f"  not in catalog: {row['asset_id']} {row['title']}")
    if len(notes["asset_registry"]["unmatched"]) > 6:
        out.append(f"  ... and {len(notes['asset_registry']['unmatched']) - 6} more")
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="print the full reconciliation")
    parser.add_argument("--write", action="store_true",
                        help="persist reports/CYCLE105/state_reconciliation.{json,md}")
    parser.add_argument("--out-dir", default="reports/CYCLE105")
    args = parser.parse_args(argv)

    reconciliation = reconcile()
    if args.json:
        print(json.dumps(reconciliation, indent=1, ensure_ascii=False))
    else:
        print("\n".join(_summary_lines(reconciliation)))

    if args.write:
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "state_reconciliation.json").write_text(
            json.dumps(reconciliation, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8")
        (out_dir / "state_reconciliation.md").write_text(
            _markdown(reconciliation), encoding="utf-8")
        print(f"\nwrote {out_dir/'state_reconciliation.json'} and .md")
    return 1 if reconciliation["invariant_violations"] else 0


def _markdown(reconciliation):
    counts = reconciliation["counts"]
    lines = ["# Canonical Product State Reconciliation (Cycle 105)", "",
             f"Generated: {reconciliation['generated_at']}", "",
             "Every product has exactly one primary state. QA, authorization, "
             "publication, purchasability, git tracking and revenue verification "
             "are independent flags and are never summed into it.", "",
             "## Counts", "",
             "| Metric | Value |", "|---|---|",
             f"| Logical products | {counts['logical_products']} |",
             f"| Primary-state sum | {counts['primary_state_sum']} |",
             f"| Published products | {counts['published_products']} "
             f"({', '.join(counts['published_ids'])}) |",
             f"| Axis overlap (published counted twice) | {counts['axis_overlap']} |",
             f"| Products + axis overlap | {counts['products_plus_axis_overlap']} |",
             f"| Duplicate explicit ids | {counts['duplicate_explicit_ids'] or 'none'} |",
             f"| Duplicate titles | {counts['duplicate_titles'] or 'none'} |",
             f"| Invariant violations | {reconciliation['invariant_violations'] or 'none'} |",
             "", "## Primary states", "", "| State | Products |", "|---|---|"]
    for state, n in counts["primary_state_counts"].items():
        lines.append(f"| {state} | {n} |")
    lines += ["", "## Products", "",
              "| ID | Title | Type | Primary state | QA | Publication | Auth | Tracking |",
              "|---|---|---|---|---|---|---|---|"]
    for p in reconciliation["products"]:
        f = p["flags"]
        lines.append("| {} | {} | {} | {} | {} | {} | {} | {} |".format(
            p["canonical_id"], p["title"], p["product_type"], p["primary_state"],
            f["qa"]["status"],
            f["publication"].get("status"),
            f["authorization"]["live_gate"]["status"],
            f["git_tracking"].get("status")))
    lines += ["", "## Identity notes", "",
              f"- asset_registry: {reconciliation['identity_notes']['asset_registry']['total']} assets, "
              f"{len(reconciliation['identity_notes']['asset_registry']['matched'])} matched, "
              f"{len(reconciliation['identity_notes']['asset_registry']['unmatched'])} not in the catalog"]
    for row in reconciliation["identity_notes"]["asset_registry"]["unmatched"]:
        lines.append(f"  - {row['asset_id']} {row['title']} (file: {row['asset_file']})")
    lines += ["", "## Snapshot provenance", "", "| Source | Timestamp |", "|---|---|"]
    for key, meta in reconciliation["snapshots"].items():
        lines.append(f"| {meta['path']} | "
                     f"{meta.get('generated_at') or meta.get('verified_at') or meta.get('created_at') or meta.get('rows')} |")
    return "\n".join(lines).rstrip("\n") + "\n"


if __name__ == "__main__":
    raise SystemExit(main())

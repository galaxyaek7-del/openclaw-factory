"""Galaxy Forge — OPERATIONAL HISTORY.

Derives a per-product production-to-publishing state from evidence that
already exists on disk, and keeps an append-only record of the transitions
it can actually prove.

Design rules (Founder directive, 2026-10-19):
  - Every claim carries a label: OBSERVED / DERIVED / INFERRED / UNKNOWN.
  - The 7 milestones are distinct and are never collapsed:
        BUILD_COMPLETE
        QA_PASS
        READY_FOR_AUTHORIZATION
        UPLOAD_COMPLETED
        PUBLIC_LISTING_VERIFIED
        CHECKOUT_VERIFIED
        FIRST_SALE_VERIFIED
  - A milestone is VERIFIED only when a named source supports it. No source
    means UNKNOWN. A partial source means NOT_VERIFIED with the reason.
  - Upload is not a public listing. A public listing is not a checkout.
    A checkout is not a sale. Each is derived independently.
  - This module never publishes, never spends, never mutates any product
    record, and never writes the ledger unless --write is passed.

Reused, not duplicated:
  - commercial_reality.py owns the transaction-level evidence vocabulary
    (PUBLISH_STATE_VERIFIED, PUBLIC_PAGE_VERIFIED, CHECKOUT_VERIFIED,
    TRANSACTION_VERIFIED). MILESTONE_TO_COMMERCIAL_REALITY below cites that
    mapping rather than inventing a competing vocabulary.
  - product_batch_12.json is the product registry.
  - reports/<id>/GATE_FINAL_*.json is the QA/quality verdict.
  - data/first_sale_*_evidence*.json is the upload/create read-back.
  - data/cycle*_live_verification*.json is the external read-back.
  - data/sales_ledger.jsonl / data/gumroad_sales.json / finance_data.json
    are the only accepted first-sale evidence.

Usage:
    python operational_history.py                 # summary table
    python operational_history.py --json          # full snapshot
    python operational_history.py --product B12-010
    python operational_history.py --write         # persist state + transitions
    python operational_history.py --check         # invariants; exit 1 on failure
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent

MILESTONES = [
    "BUILD_COMPLETE",
    "QA_PASS",
    "READY_FOR_AUTHORIZATION",
    "UPLOAD_COMPLETED",
    "PUBLIC_LISTING_VERIFIED",
    "CHECKOUT_VERIFIED",
    "FIRST_SALE_VERIFIED",
]

LABELS = ("OBSERVED", "DERIVED", "INFERRED", "ESTIMATED", "UNKNOWN", "BLOCKED")
STATUSES = ("VERIFIED", "NOT_VERIFIED", "UNKNOWN")

MILESTONE_TO_COMMERCIAL_REALITY = {
    "UPLOAD_COMPLETED": "PUBLISH_STATE_VERIFIED",
    "PUBLIC_LISTING_VERIFIED": "PUBLIC_PAGE_VERIFIED",
    "CHECKOUT_VERIFIED": "CHECKOUT_VERIFIED",
    "FIRST_SALE_VERIFIED": "TRANSACTION_VERIFIED + PAYMENT_VERIFIED",
}

STATE_PATH = ROOT / "data" / "operational_history.json"
LEDGER_PATH = ROOT / "data" / "operational_history.jsonl"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, OSError):
        return default


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _newest(paths: Iterable[Path]) -> Optional[Path]:
    existing = [p for p in paths if p.exists()]
    if not existing:
        return None
    return max(existing, key=lambda p: p.stat().st_mtime)


@dataclass
class Milestone:
    name: str
    status: str = "UNKNOWN"
    label: str = "UNKNOWN"
    at: Optional[str] = None
    source: Optional[str] = None
    evidence: List[str] = field(default_factory=list)
    note: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "label": self.label,
            "at": self.at,
            "source": self.source,
            "evidence": list(self.evidence),
            "note": self.note,
        }


def _verified(name: str, label: str, at: Optional[str], source: Optional[str],
              evidence: List[str], note: Optional[str] = None) -> Milestone:
    return Milestone(name, "VERIFIED", label, at, source, evidence, note)


def _not_verified(name: str, label: str, source: Optional[str],
                  evidence: List[str], note: Optional[str] = None) -> Milestone:
    return Milestone(name, "NOT_VERIFIED", label, None, source, evidence, note)


def _unknown(name: str, note: str) -> Milestone:
    return Milestone(name, "UNKNOWN", "UNKNOWN", None, None, [], note)


# ---------------------------------------------------------------------------
# Evidence indexing
# ---------------------------------------------------------------------------

def _gumroad_id_map(data_dir: Path, products: List[Dict[str, Any]]) -> Dict[str, str]:
    """Map a Gumroad product id to a B12 id using the recorded product title."""
    by_title = {str(p.get("title", "")).strip().lower(): p["id"] for p in products}
    mapping: Dict[str, str] = {}
    for path in data_dir.glob("first_sale_draft_evidence*.json"):
        record = _read_json(path, {}) or {}
        gumroad_id = record.get("product_id")
        title = str(record.get("title", "")).strip().lower()
        if gumroad_id and title in by_title:
            mapping[gumroad_id] = by_title[title]
    return mapping


def _live_records(data_dir: Path, product: Dict[str, Any],
                  gumroad_ids: Dict[str, str]) -> List[Tuple[Path, Dict[str, Any]]]:
    """Every external read-back that can be tied to this product by id or title."""
    title = str(product.get("title", "")).strip().lower()
    wanted_gumroad = {gid for gid, pid in gumroad_ids.items() if pid == product["id"]}
    found: List[Tuple[Path, Dict[str, Any]]] = []
    for path in sorted(data_dir.glob("*live_verification*.json")):
        record = _read_json(path, {}) or {}
        blob = json.dumps(record, ensure_ascii=False).lower()
        direct = product["id"].lower() in blob
        by_gid = any(gid.lower() in blob for gid in wanted_gumroad)
        by_title = bool(title) and title in blob
        if direct or by_gid or by_title:
            found.append((path, record))
    return found


def _sales_for(product_id: str, data_dir: Path, root: Path) -> Tuple[int, List[str], List[str]]:
    """Return (real sale count, evidence lines, sources)."""
    sources: List[str] = []
    evidence: List[str] = []
    count = 0

    ledger_path = data_dir / "sales_ledger.jsonl"
    sale_events = [
        row for row in _read_jsonl(ledger_path)
        if str(row.get("event_type", "")).lower() in {"sale", "sale_verified", "purchase", "transaction"}
    ]
    if sale_events:
        sources.append(_rel(ledger_path, root))
        matching = [r for r in sale_events if product_id in json.dumps(r, ensure_ascii=False)]
        count += len(matching)
        evidence.append(f"{len(sale_events)} sale event(s) in sales_ledger; {len(matching)} match {product_id}")

    gumroad_path = data_dir / "gumroad_sales.json"
    gumroad = _read_json(gumroad_path, {}) or {}
    transactions = gumroad.get("sales") or gumroad.get("transactions") or []
    if isinstance(transactions, list) and transactions:
        sources.append(_rel(gumroad_path, root))
        matching = [r for r in transactions if product_id in json.dumps(r, ensure_ascii=False)]
        count += len(matching)
        evidence.append(f"{len(transactions)} recorded Gumroad transaction(s); {len(matching)} match {product_id}")

    finance_path = root / "finance_data.json"
    finance = _read_json(finance_path, {}) or {}
    finance_sales = finance.get("sales") or []
    if isinstance(finance_sales, list) and finance_sales:
        sources.append(_rel(finance_path, root))
        matching = [r for r in finance_sales if product_id in json.dumps(r, ensure_ascii=False)]
        count += len(matching)
        evidence.append(f"{len(finance_sales)} finance sale record(s); {len(matching)} match {product_id}")

    if not sources:
        evidence.append("no sale ledger, Gumroad transaction record, or finance sale record exists")
    return count, evidence, sources


# ---------------------------------------------------------------------------
# Milestone derivation
# ---------------------------------------------------------------------------

def _derive_build(product: Dict[str, Any], books_dir: Path, reports_dir: Path,
                  root: Path) -> Milestone:
    files = list(product.get("files") or [])
    if not files:
        return _unknown("BUILD_COMPLETE", "the registry declares no deliverable files")

    observed: List[str] = []
    missing: List[str] = []
    for name in files:
        path = books_dir / name
        if path.exists() and path.stat().st_size > 0:
            observed.append(f"{_rel(path, root)} ({path.stat().st_size} bytes, sha256 {_sha256(path)[:16]}...)")
        else:
            missing.append(name)

    if missing:
        return _not_verified(
            "BUILD_COMPLETE", "OBSERVED", _rel(books_dir, root),
            observed, f"missing or empty: {', '.join(missing)}",
        )

    note = None
    manifest_path = _newest((reports_dir / product["id"]).glob("MANIFEST_*.json"))
    if manifest_path:
        manifest = _read_json(manifest_path, {}) or {}
        declared = json.dumps(manifest, ensure_ascii=False).lower()
        matched = sum(1 for name in files if name.lower() in declared)
        if matched == len(files):
            observed.append(f"{_rel(manifest_path, root)} declares all {matched} artifact(s)")
            note = "artifact set matches the recorded manifest"
        else:
            note = f"manifest found but only {matched}/{len(files)} artifact names were present in it"

    return _verified("BUILD_COMPLETE", "OBSERVED", None, _rel(books_dir, root), observed, note)


def _gate_verdict(gate: Dict[str, Any], price: Optional[float]) -> str:
    """Read a top-level verdict, or the block for the product's approved price."""
    verdict = str(gate.get("verdict") or "").strip()
    if verdict:
        return verdict
    blocks = [
        (key, value) for key, value in gate.items()
        if key.startswith("gate_at_") and isinstance(value, dict) and value.get("verdict")
    ]
    if not blocks:
        return ""

    def distance(item: Tuple[str, Dict[str, Any]]) -> float:
        try:
            return abs(float(item[1].get("price")) - float(price))
        except (TypeError, ValueError):
            return 1e9

    if price is not None:
        blocks.sort(key=distance)
    key, block = blocks[0]
    return f"{block['verdict']} (from {key} at ${block.get('price')})"


def _derive_qa(product: Dict[str, Any], reports_dir: Path, root: Path) -> Milestone:
    gate_path = _newest((reports_dir / product["id"]).glob("GATE_FINAL_*.json"))
    if gate_path is None:
        return _unknown("QA_PASS", "no GATE_FINAL record exists for this product")

    gate = _read_json(gate_path, {}) or {}
    price = product.get("price_usd", product.get("price"))
    verdict = _gate_verdict(gate, price)
    evidence = [f"verdict: {verdict or 'missing'}"]
    if gate.get("price_usd") is not None:
        evidence.append(f"gate price: ${gate['price_usd']}")

    qa_facts_path = _newest((reports_dir / product["id"]).glob("QA_FACTS_*.json"))
    if qa_facts_path is None:
        qa_facts_path = _newest((reports_dir / product["id"]).glob("QA_*.json"))
    qa_verdict = None
    if qa_facts_path:
        qa_facts = _read_json(qa_facts_path, {}) or {}
        qa_verdict = qa_facts.get("verdict")
        evidence.append(f"QA_FACTS verdict: {qa_verdict or 'missing'}")

    recalc_path = _newest((reports_dir / product["id"]).glob("NATIVE_RECALC_*.json"))
    if recalc_path:
        recalc = _read_json(recalc_path, {}) or {}
        evidence.append(
            f"native recalc: {len(recalc.get('error_cells') or [])} error cell(s), "
            f"verdict {recalc.get('verdict', 'missing')}"
        )

    if verdict.upper().startswith("APPROVED"):
        note = None
        if qa_verdict and not str(qa_verdict).upper().startswith(("PASS", "OK")):
            note = f"gate approved but the QA record's verdict is {qa_verdict}"
        return _verified("QA_PASS", "DERIVED", gate.get("run_at"), _rel(gate_path, root), evidence, note)

    return _not_verified(
        "QA_PASS", "DERIVED", _rel(gate_path, root), evidence,
        f"gate verdict is not an approval: {verdict or 'missing'}",
    )


def _derive_authorization(product: Dict[str, Any], data_dir: Path,
                          reports_dir: Path, qa: Milestone, root: Path) -> Milestone:
    if qa.status != "VERIFIED":
        return _not_verified(
            "READY_FOR_AUTHORIZATION", "DERIVED", None,
            ["QA_PASS is not verified"],
            "a product cannot be ready for authorization before QA passes",
        )

    approvals_path = data_dir / "founder_approvals.jsonl"
    approvals = [
        row for row in _read_jsonl(approvals_path)
        if product["id"] in json.dumps(row, ensure_ascii=False)
    ]
    if approvals:
        latest = approvals[-1]
        return _verified(
            "READY_FOR_AUTHORIZATION", "OBSERVED", latest.get("at") or latest.get("timestamp"),
            _rel(approvals_path, root),
            [f"founder approval record: {json.dumps(latest, ensure_ascii=False)[:240]}"],
        )

    publish_runs = sorted(data_dir.glob("cycle9*_*publish_run.json"))
    for path in publish_runs:
        record = _read_json(path, {}) or {}
        blob = json.dumps(record, ensure_ascii=False)
        if product["id"] not in blob:
            continue
        if "publish-authorization" in blob or "APPROVE " + product["id"] in blob:
            return _verified(
                "READY_FOR_AUTHORIZATION", "OBSERVED", record.get("updated_at"), _rel(path, root),
                ["the recorded publish run carried an explicit --publish-authorization argument"],
            )

    live = _live_records(data_dir, product, _gumroad_id_map(data_dir, [product]))
    published = _published_readback(live)
    if published is not None:
        path, evidence = published
        return _verified(
            "READY_FOR_AUTHORIZATION", "INFERRED", None, _rel(path, root),
            ["a real publish exists: " + evidence[0]],
            "no standalone authorization artifact was found; authorization is inferred from the "
            "recorded founder-authority publish, not observed directly",
        )

    gate_path = _newest((reports_dir / product["id"]).glob("GATE_FINAL_*.json"))
    gate = _read_json(gate_path, {}) or {} if gate_path else {}
    founder_decision = gate.get("founder_decision")
    if isinstance(founder_decision, dict) and founder_decision.get("price_usd") is not None:
        return _verified(
            "READY_FOR_AUTHORIZATION", "DERIVED", gate.get("run_at"), _rel(gate_path, root),
            [f"founder price decision: ${founder_decision.get('price_usd')}"],
            "priced and QA-approved; publication authorization itself is not recorded",
        )

    return _verified(
        "READY_FOR_AUTHORIZATION", "DERIVED", gate.get("run_at") if gate_path else None,
        _rel(gate_path, root) if gate_path else None,
        ["gate approved; no publication authorization is recorded"],
        "ready and awaiting a product-specific authorization; nothing has been published",
    )


def _normalize_readback(record: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize the three real read-back shapes used in data/ (no new format)."""
    api = (
        record.get("api_readback")
        or record.get("live")
        or record.get("gumroad")
        or (record.get("facts") or {}).get("product")
        or {}
    )
    public = (
        record.get("public_page")
        or record.get("checkout_page")
        or record.get("checkout")
        or record.get("facts")
        or {}
    )
    facts = record.get("facts") or {}

    published = api.get("published")
    http_status = public.get("http_status") or public.get("status") or facts.get("public_http_status")
    price = (
        public.get("price_cents") or public.get("product_price_amount")
        or facts.get("public_price") or api.get("price_cents") or api.get("price")
    )
    currency = public.get("currency") or facts.get("public_currency") or api.get("currency")
    sales_count = api.get("sales_count")
    if sales_count is None:
        sales_count = facts.get("sales_count_total")

    for check in record.get("checks") or []:
        name = str(check.get("check", "")).lower()
        if check.get("status") != "PASS":
            continue
        if "published" in name:
            published = True
        if "http 200" in name:
            http_status = 200
        if "displayed price" in name:
            parts = str(check.get("detail", "")).split()
            if parts and parts[0].isdigit():
                price = int(parts[0])

    return {
        "published": published,
        "http_status": http_status,
        "price": price,
        "currency": currency,
        "price_meta": public.get("price_meta_present"),
        "purchase_prop": public.get("has_purchase_prop"),
        "sales_count": sales_count,
        "at": record.get("verified_at_utc") or record.get("checked_at_utc") or record.get("verified_at"),
    }


def _published_readback(live: List[Tuple[Path, Dict[str, Any]]]) -> Optional[Tuple[Path, List[str]]]:
    """Return the strongest read-back that states published=true, if any."""
    best: Optional[Tuple[Path, List[str]]] = None
    for path, record in live:
        if _normalize_readback(record)["published"] is True:
            line = f"{_rel(path, ROOT)}: published=true"
            if best is None:
                best = (path, [line])
            else:
                best[1].append(line)
    return best


def _derive_upload(product: Dict[str, Any], data_dir: Path, root: Path) -> Milestone:
    evidence: List[str] = []
    drafts = sorted(data_dir.glob("first_sale_draft_evidence*.json"))
    for path in drafts:
        record = _read_json(path, {}) or {}
        if str(record.get("title", "")).strip().lower() != str(product.get("title", "")).strip().lower():
            continue
        return _verified(
            "UPLOAD_COMPLETED", "OBSERVED", record.get("verified_at"), _rel(path, root),
            [f"create response + GET read-back for {record.get('product_id')} at ${(record.get('price_cents') or 0)/100:.2f}"],
        )

    for path in sorted(data_dir.glob("cycle9*_*publish_run.json")):
        record = _read_json(path, {}) or {}
        blob = json.dumps(record, ensure_ascii=False)
        if product["id"] not in blob:
            continue
        tasks = record.get("tasks") or {}
        draft = tasks.get("verify_remote_draft") or {}
        if str(draft.get("status", "")) == "EXTERNALLY_VERIFIED":
            return _verified(
                "UPLOAD_COMPLETED", "DERIVED", record.get("updated_at"), _rel(path, root),
                ["verify_remote_draft: EXTERNALLY_VERIFIED"],
            )
        if draft:
            evidence.append(f"{_rel(path, root)} verify_remote_draft: {draft.get('status')}")

    return _not_verified(
        "UPLOAD_COMPLETED", "OBSERVED", None, evidence or ["no draft/create read-back exists"],
        "no upload has been observed for this product",
    )


def _derive_listing(product: Dict[str, Any], data_dir: Path, root: Path) -> Tuple[Milestone, Optional[str]]:
    live = _live_records(data_dir, product, _gumroad_id_map(data_dir, [product]))
    if not live:
        return _unknown("PUBLIC_LISTING_VERIFIED", "no external read-back exists for this product"), None

    evidence: List[str] = []
    for path, record in live:
        facts = _normalize_readback(record)
        if facts["published"] is True and facts["http_status"] == 200:
            evidence.append(f"{_rel(path, root)}: published=true and public HTTP 200")
            if facts["price"] is not None:
                evidence.append(f"{_rel(path, root)}: public price={facts['price']}, currency={facts['currency']}")
            if facts["sales_count"] is not None:
                evidence.append(f"{_rel(path, root)}: sales_count={facts['sales_count']}")
            if str(record.get("all_pass", "")).lower() == "true":
                evidence.append(f"{_rel(path, root)}: all_pass=true")
            if record.get("overall"):
                evidence.append(f"{_rel(path, root)}: overall={record['overall']}")
            return _verified(
                "PUBLIC_LISTING_VERIFIED", "OBSERVED", facts["at"], _rel(path, root), evidence,
                "an external read-back confirms the listing is public; checkout is assessed separately",
            ), _rel(path, root)

        if facts["published"] is False:
            evidence.append(f"{_rel(path, root)}: published=false (not public yet)")

    if evidence:
        return _not_verified(
            "PUBLIC_LISTING_VERIFIED", "OBSERVED", None,
            evidence, "external read-backs exist but none proves a published public listing",
        ), None
    return _unknown("PUBLIC_LISTING_VERIFIED", "external read-backs exist but carry no usable publish signal"), None


def _derive_checkout(product: Dict[str, Any], data_dir: Path, root: Path) -> Milestone:
    live = _live_records(data_dir, product, _gumroad_id_map(data_dir, [product]))
    evidence: List[str] = []
    for path, record in live:
        facts = _normalize_readback(record)
        if facts["http_status"] == 200 and facts["price"] and facts["currency"]:
            evidence.append(
                f"{_rel(path, root)}: checkout page HTTP 200, price {facts['price']}, "
                f"currency {facts['currency']}"
            )
            if facts["price_meta"] is not None:
                evidence.append(f"{_rel(path, root)}: price meta present={facts['price_meta']}")
            if facts["purchase_prop"] is not None:
                evidence.append(f"{_rel(path, root)}: purchase prop present={facts['purchase_prop']}")
            return _verified(
                "CHECKOUT_VERIFIED", "DERIVED", facts["at"], _rel(path, root), evidence,
                "the checkout page renders the approved price and currency; this is not a completed "
                "transaction and does not prove a payment can succeed",
            )
        if facts["http_status"] is not None:
            evidence.append(
                f"{_rel(path, root)}: checkout HTTP {facts['http_status']}, "
                f"price={facts['price']}, currency={facts['currency']}"
            )

    if evidence:
        return _not_verified(
            "CHECKOUT_VERIFIED", "DERIVED", None, evidence,
            "no read-back shows the checkout page rendering the approved price and currency",
        )
    return _unknown("CHECKOUT_VERIFIED", "no external read-back exists for this product")


def _derive_first_sale(product: Dict[str, Any], data_dir: Path, root: Path) -> Milestone:
    count, evidence, sources = _sales_for(product["id"], data_dir, root)
    if count > 0:
        return _verified(
            "FIRST_SALE_VERIFIED", "OBSERVED", None,
            sources[0] if sources else None, evidence,
        )
    return _not_verified(
        "FIRST_SALE_VERIFIED", "OBSERVED", sources[0] if sources else None, evidence,
        "no real transaction exists for this product",
    )


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------

def build_record(product: Dict[str, Any], root: Path = ROOT) -> Dict[str, Any]:
    data_dir = root / "data"
    reports_dir = root / "reports"
    books_dir = root / "books" / "batch12"

    build = _derive_build(product, books_dir, reports_dir, root)
    qa = _derive_qa(product, reports_dir, root)
    authorization = _derive_authorization(product, data_dir, reports_dir, qa, root)
    upload = _derive_upload(product, data_dir, root)
    listing, _ = _derive_listing(product, data_dir, root)
    checkout = _derive_checkout(product, data_dir, root)
    first_sale = _derive_first_sale(product, data_dir, root)

    milestones = {m.name: m for m in (build, qa, authorization, upload, listing, checkout, first_sale)}

    verified = [name for name in MILESTONES if milestones[name].status == "VERIFIED"]
    highest = -1
    for index, name in enumerate(MILESTONES):
        if milestones[name].status == "VERIFIED":
            highest = index
        else:
            break

    out_of_order = [
        name for name in verified
        if MILESTONES.index(name) > highest
    ]
    next_required = MILESTONES[highest + 1] if highest + 1 < len(MILESTONES) else None

    return {
        "product_id": product["id"],
        "title": product.get("title"),
        "registry_price_usd": product.get("price_usd", product.get("price")),
        "milestones": {name: milestones[name].as_dict() for name in MILESTONES},
        "highest_contiguous_verified": MILESTONES[highest] if highest >= 0 else None,
        "next_required": next_required,
        "verified_count": len(verified),
        "out_of_order": out_of_order,
        "registry_state": product.get("state"),
    }


def load_products(root: Path = ROOT) -> List[Dict[str, Any]]:
    payload = _read_json(root / "data" / "product_batch_12.json", {}) or {}
    products = payload.get("products") or []
    return [p for p in products if isinstance(p, dict) and p.get("id")]


def build_snapshot(root: Path = ROOT) -> Dict[str, Any]:
    products = load_products(root)
    records = [build_record(product, root) for product in products]
    return {
        "schema": "operational_history/v1",
        "generated_at": _now_iso(),
        "milestones": MILESTONES,
        "labels": list(LABELS),
        "milestone_to_commercial_reality": MILESTONE_TO_COMMERCIAL_REALITY,
        "products": records,
        "summary": {
            "products": len(records),
            "by_highest": {
                milestone: sum(1 for r in records if r["highest_contiguous_verified"] == milestone)
                for milestone in [None] + MILESTONES
            },
            "first_sale_verified": sum(
                1 for r in records if r["milestones"]["FIRST_SALE_VERIFIED"]["status"] == "VERIFIED"
            ),
        },
    }


# ---------------------------------------------------------------------------
# Invariants + persistence
# ---------------------------------------------------------------------------

def validate_snapshot(snapshot: Dict[str, Any]) -> List[str]:
    problems: List[str] = []
    for record in snapshot.get("products", []):
        pid = record.get("product_id", "?")
        milestones = record.get("milestones", {})
        if list(milestones) != MILESTONES:
            problems.append(f"{pid}: milestones are missing, extra, or out of order")
        for name, entry in milestones.items():
            status = entry.get("status")
            label = entry.get("label")
            if status not in STATUSES:
                problems.append(f"{pid}/{name}: invalid status {status!r}")
            if label not in LABELS:
                problems.append(f"{pid}/{name}: invalid label {label!r}")
            if status == "VERIFIED" and not entry.get("evidence"):
                problems.append(f"{pid}/{name}: VERIFIED with no evidence")
            if status == "VERIFIED" and label == "UNKNOWN":
                problems.append(f"{pid}/{name}: VERIFIED while labelled UNKNOWN")
            if status == "UNKNOWN" and entry.get("evidence"):
                problems.append(f"{pid}/{name}: UNKNOWN with evidence")
        if record.get("out_of_order"):
            problems.append(
                f"{pid}: out-of-order verified milestones {record['out_of_order']} "
                "(an earlier milestone is not verified)"
            )
        if record.get("milestones", {}).get("FIRST_SALE_VERIFIED", {}).get("status") == "VERIFIED":
            listing = record["milestones"].get("PUBLIC_LISTING_VERIFIED", {}).get("status")
            checkout = record["milestones"].get("CHECKOUT_VERIFIED", {}).get("status")
            if listing != "VERIFIED" or checkout != "VERIFIED":
                problems.append(f"{pid}: FIRST_SALE_VERIFIED without a verified listing and checkout")
    return problems


def write_snapshot(snapshot: Dict[str, Any], state_path: Path = STATE_PATH,
                   ledger_path: Path = LEDGER_PATH) -> Dict[str, int]:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with open(state_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(snapshot, handle, indent=1, ensure_ascii=False)
        handle.write("\n")

    existing = {
        (row.get("product_id"), row.get("milestone"))
        for row in _read_jsonl(ledger_path)
    }
    appended = 0
    with open(ledger_path, "a", encoding="utf-8", newline="\n") as handle:
        for record in snapshot.get("products", []):
            for name in MILESTONES:
                entry = record["milestones"][name]
                key = (record["product_id"], name)
                if entry.get("status") != "VERIFIED" or key in existing:
                    continue
                row = {
                    "at": _now_iso(),
                    "product_id": record["product_id"],
                    "milestone": name,
                    "label": entry.get("label"),
                    "observed_at": entry.get("at"),
                    "source": entry.get("source"),
                    "evidence": entry.get("evidence", []),
                    "recorded_by": "operational_history.py",
                }
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                existing.add(key)
                appended += 1
    return {"transitions_appended": appended, "products": len(snapshot.get("products", []))}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _format_table(snapshot: Dict[str, Any]) -> str:
    lines = [
        "PRODUCT   HIGHEST VERIFIED        NEXT REQUIRED              SALE",
        "--------  ----------------------  -------------------------  ----------",
    ]
    for record in snapshot["products"]:
        highest = record["highest_contiguous_verified"] or "NONE"
        nxt = record["next_required"] or "DONE"
        sale = record["milestones"]["FIRST_SALE_VERIFIED"]["status"]
        lines.append(f"{record['product_id']:<8}  {highest:<22}  {nxt:<25}  {sale}")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Derive per-product operational state from evidence.")
    parser.add_argument("--root", default=str(ROOT), help="factory root (testing)")
    parser.add_argument("--product", help="limit to one product id")
    parser.add_argument("--json", action="store_true", help="print the full snapshot")
    parser.add_argument("--write", action="store_true", help="persist the snapshot and new transitions")
    parser.add_argument("--check", action="store_true", help="exit 1 if an invariant is violated")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    snapshot = build_snapshot(root)
    if args.product:
        snapshot["products"] = [r for r in snapshot["products"] if r["product_id"] == args.product]
        snapshot["summary"]["products"] = len(snapshot["products"])

    problems = validate_snapshot(snapshot)

    if args.json:
        print(json.dumps(snapshot, indent=1, ensure_ascii=False))
    elif not args.check:
        print(_format_table(snapshot))
        print()
        for record in snapshot["products"]:
            print(f"{record['product_id']}  {record['title']}")
            for name in MILESTONES:
                entry = record["milestones"][name]
                print(f"  {name:<26} {entry['status']:<12} {entry['label']:<8} {entry.get('note') or ''}")
            print()

    if problems:
        for problem in problems:
            print(f"INVARIANT: {problem}", file=sys.stderr)
    elif args.check:
        print("operational history: OK")

    if args.write:
        counts = write_snapshot(snapshot, root / "data" / "operational_history.json",
                                root / "data" / "operational_history.jsonl")
        print(f"wrote snapshot; transitions appended: {counts['transitions_appended']}")

    if args.check and problems:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

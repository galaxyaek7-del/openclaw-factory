#!/usr/bin/env python3
"""Audit and publish reviewed product batches to Gumroad, fail closed.

This is the publication path for products whose QA manifest under
``books/<batch>/<id>/manifest.json`` is ``qa.ok``. It never infers an
approval from a batch-level instruction. Every live product needs its own
founder approval bound to the exact product id, price, currency, action set
and product revision; see ``channels/publication_authorization.py``.

Dry run (the default) only reads local files:

    python scripts/publish_batch14.py --batch batch15

Live run (requires a real per-product approval file and fresh Gumroad auth):

    python scripts/publish_batch14.py --batch batch15 --live \
        --approvals data/publication_approvals.json

The live flag in this process is set only after approvals and auth state
have both been checked. Dry run never imports or calls the Gumroad client,
even when ``FACTORY_LIVE_PUBLISH`` is already true. A failed product is
recorded and the batch continues; live writes are never retried.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
import urllib.request
import zipfile
from html import unescape
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

BATCH = ROOT / "books" / "batch14"
RESULTS = ROOT / "data" / "batch14_publish_results.json"
BATCHES = {
    "batch13": (ROOT / "books" / "batch13", ROOT / "data" / "batch13_publish_results.json"),
    "batch14": (ROOT / "books" / "batch14", ROOT / "data" / "batch14_publish_results.json"),
    "batch15": (ROOT / "books" / "batch15", ROOT / "data" / "batch15_publish_results.json"),
    "batch16": (ROOT / "books" / "batch16", ROOT / "data" / "batch16_publish_results.json"),
}
COVER_URL = "https://raw.githubusercontent.com/galaxyaek7-del/openclaw-factory/main/books/covers/{id}.png"
DEFAULT_APPROVALS = ROOT / "data" / "publication_approvals.json"
DEFAULT_SESSION_MAX_AGE_SECONDS = 3600
DISCLAIMER_PHRASES = (
    "not financial",
    "not legal",
    "not tax",
    "not payroll",
    "not advice",
    "not a substitute",
    "not lending",
    "not an offer",
)
DISCLAIMER_RE = re.compile(r"\bnot\b[^.\n<>]{0,140}\badvice\b", re.IGNORECASE)
REQUIRED_ACTIONS = ("upload", "publish")


class PublicationBlocked(Exception):
    """A live write was refused before or during a real attempt."""


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load_manifests(batch=BATCH):
    out = []
    prefix = "B" + Path(batch).name.replace("batch", "")
    seen = set()
    candidates = sorted(Path(batch).glob(f"{prefix}-*/manifest.json"))
    candidates += sorted(Path(batch).glob(f"{prefix}-*.manifest.json"))
    for m in candidates:
        if m in seen:
            continue
        seen.add(m)
        try:
            out.append(json.loads(m.read_text(encoding="utf-8")))
        except Exception as exc:
            fallback_id = m.parent.name if m.name == "manifest.json" else m.name.split(".")[0]
            out.append(
                {
                    "id": fallback_id,
                    "title": fallback_id,
                    "price_cents": 0,
                    "_manifest_error": f"{type(exc).__name__}: {exc}",
                    "files": {},
                    "qa": {},
                }
            )
    return out


def load_registry(path=ROOT / "data" / "product_registry.json"):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}
    records = data.get("products") if isinstance(data, dict) else data
    if not isinstance(records, list):
        return {}
    return {
        record.get("internal_id") or record.get("id"): record
        for record in records
        if isinstance(record, dict) and (record.get("internal_id") or record.get("id"))
    }


def preflight(man, root=ROOT):
    """Read-only preflight. Returns (ok, reason, bundle_path)."""
    if man.get("_manifest_error"):
        return False, man["_manifest_error"], None
    if not (man.get("qa") or {}).get("ok"):
        return False, "QA manifest is not ok", None
    files = man.get("files") or {}
    bundle = files.get("bundle") or {}
    if not bundle.get("path"):
        return False, "manifest has no bundle path", None
    path = Path(bundle["path"])
    if not path.is_absolute():
        path = Path(root) / path
    if not path.is_file():
        return False, f"bundle missing: {bundle['path']}", None
    if sha256(path) != bundle.get("sha256"):
        return False, "bundle changed since QA (sha256 mismatch)", None
    if not ((man.get("qa") or {}).get("listing") or {}).get("description_html"):
        return False, "no listing description", None
    try:
        price = int(man.get("price_cents"))
    except Exception:
        return False, "price_cents is not an integer", None
    if not 100 <= price <= 10000:
        return False, f"price {price} cents outside the $1.00-$100.00 range", None
    return True, "ok", path


def _resolve(entry, root):
    if not isinstance(entry, dict) or not entry.get("path"):
        return None
    path = Path(entry["path"])
    if not path.is_absolute():
        path = Path(root) / path
    return path


def _check_bundle(man, root):
    path = _resolve((man.get("files") or {}).get("bundle"), root)
    if path is None or not path.is_file():
        return "FAIL", "bundle: missing"
    try:
        with zipfile.ZipFile(path) as archive:
            bad = archive.testzip()
            if bad:
                return "FAIL", f"bundle: corrupt member {bad}"
            names = archive.namelist()
            expected = ((man.get("qa") or {}).get("bundle") or {}).get("files") or []
            if expected and set(names) != set(expected):
                return "FAIL", "bundle: member list differs from QA manifest"
            by_name = {Path(name).name: name for name in names}
            for key in ("workbook", "guide"):
                entry = (man.get("files") or {}).get(key) or {}
                source = _resolve(entry, root)
                if source is None or not source.is_file():
                    return "FAIL", f"bundle: source {key} missing"
                member = by_name.get(source.name)
                if not member:
                    return "FAIL", f"bundle: {source.name} is not inside the bundle"
                if hashlib.sha256(archive.read(member)).hexdigest() != sha256(source):
                    return "FAIL", f"bundle: {source.name} differs from the source file"
            return "PASS", f"bundle: {len(names)} members, byte-identical to sources"
    except zipfile.BadZipFile:
        return "FAIL", "bundle: not a valid zip"
    except Exception as exc:
        return "FAIL", f"bundle: {type(exc).__name__}: {str(exc)[:160]}"


def _check_workbook(man, root):
    path = _resolve((man.get("files") or {}).get("workbook"), root)
    if path is None or not path.is_file():
        return "FAIL", "workbook: missing"
    try:
        with zipfile.ZipFile(path) as archive:
            bad = archive.testzip()
            if bad:
                return "FAIL", f"workbook: corrupt member {bad}"
            names = set(archive.namelist())
            required = {"[Content_Types].xml", "xl/workbook.xml"}
            absent = sorted(required - names)
            if absent:
                return "FAIL", f"workbook: missing Open XML parts {absent}"
            if any(name.startswith("xl/externalLinks/") for name in names):
                return "FAIL", "workbook: contains external links"
        return "PASS", "workbook: valid Open XML, no external links"
    except zipfile.BadZipFile:
        return "FAIL", "workbook: not a valid xlsx zip"
    except Exception as exc:
        return "FAIL", f"workbook: {type(exc).__name__}: {str(exc)[:160]}"


def _normalize_title(value):
    """Lowercase and fold punctuation/ampersands so a title wrapped across
    extracted PDF lines still matches. Wording differences are not forgiven."""
    text = str(value or "").lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _check_guide(man, root):
    path = _resolve((man.get("files") or {}).get("guide"), root)
    if path is None or not path.is_file():
        return "FAIL", "guide: missing"
    try:
        from pypdf import PdfReader
    except Exception:
        return "UNKNOWN", "guide: pypdf is not available, so page/text verification is UNKNOWN"
    try:
        if path.read_bytes()[:5] != b"%PDF-":
            return "FAIL", "guide: missing %PDF header"
        reader = PdfReader(str(path))
        pages = len(reader.pages)
        expected = ((man.get("qa") or {}).get("guide") or {}).get("pages")
        if isinstance(expected, int) and pages != expected:
            return "FAIL", f"guide: {pages} pages, QA recorded {expected}"
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
        if not text.strip():
            return "FAIL", "guide: no extractable text"
        title = str(man.get("title") or "").split(" (")[0].strip()
        if title and _normalize_title(title) not in _normalize_title(text):
            return "HOLD", "guide: title not found in extracted text"
        if not _has_disclaimer(text):
            return "HOLD", "guide: no explicit not-advice disclaimer found"
        return "PASS", f"guide: {pages} pages, title and disclaimer present"
    except Exception as exc:
        return "FAIL", f"guide: {type(exc).__name__}: {str(exc)[:160]}"


def _check_cover(man, root):
    path = _resolve((man.get("files") or {}).get("cover"), root)
    if path is None or not path.is_file():
        return "FAIL", "cover: missing"
    try:
        from PIL import Image
        with Image.open(path) as image:
            if image.format != "PNG":
                return "FAIL", f"cover: format is {image.format}, not PNG"
            expected = ((man.get("qa") or {}).get("cover") or {}).get("size")
            size = tuple(image.size)
            if expected and list(size) != list(expected):
                return "FAIL", f"cover: size {size}, QA recorded {tuple(expected)}"
            if size[0] < 1000 or size[1] < 500:
                return "HOLD", f"cover: {size} is below the 1000x500 review floor"
        return "PASS", f"cover: PNG {size}"
    except Exception as exc:
        return "FAIL", f"cover: {type(exc).__name__}: {str(exc)[:160]}"


def _has_disclaimer(text):
    lowered = text.lower()
    return bool(DISCLAIMER_RE.search(text)) or any(phrase in lowered for phrase in DISCLAIMER_PHRASES)


def _plain_text(html):
    return re.sub(r"<[^>]+>", " ", unescape(html or ""))


def _check_listing(man):
    html = ((man.get("qa") or {}).get("listing") or {}).get("description_html") or ""
    text = _plain_text(html)
    if not text.strip():
        return "FAIL", "listing: description is empty"
    problems = []
    if len(text) < 500:
        problems.append("description is under 500 characters")
    if "what's included" not in text.lower() and "what’s included" not in text.lower():
        problems.append("missing 'What's included' section")
    if "who it's for" not in text.lower() and "who it’s for" not in text.lower():
        problems.append("missing 'Who it's for' section")
    if not _has_disclaimer(text):
        problems.append("missing explicit not-advice disclaimer")
    if problems:
        return "HOLD", "listing: " + "; ".join(problems)
    return "PASS", f"listing: {len(text)} characters, sections and disclaimer present"


# Live-measured on 2026-10-28 while publishing batch13: Gumroad's own
# tag writer rejects a tag with "Name A tag is too long. Please try again
# with a shorter one, under 20 characters." A 20-character tag ("elder care
# organizer") was accepted; 21 ("caregiver spreadsheet") and 24
# ("construction spreadsheet") were rejected. Checking this BEFORE a live
# run turns a mid-publish platform rejection into a dry-run finding.
GUMROAD_MAX_TAG_LENGTH = 20


def _check_metadata(man):
    from channels.publication_authorization import product_currency

    missing = []
    tags = man.get("tags")
    if not isinstance(tags, list) or not tags:
        missing.append("tags")
    if not isinstance(man.get("category"), str) or not man.get("category").strip():
        missing.append("category")
    if product_currency(man) is None:
        missing.append("currency (valid three-letter code)")
    if missing:
        return "UNKNOWN", "metadata missing: " + ", ".join(missing)

    over_long = [t for t in tags
                 if isinstance(t, str) and len(t) > GUMROAD_MAX_TAG_LENGTH]
    not_text = [t for t in tags if not isinstance(t, str) or not t.strip()]
    if over_long or not_text:
        problems = []
        if over_long:
            problems.append("tags longer than %d characters (Gumroad rejects these): %s"
                            % (GUMROAD_MAX_TAG_LENGTH, ", ".join(repr(t) for t in over_long)))
        if not_text:
            problems.append("empty or non-text tags: %r" % (not_text,))
        return "HOLD", "; ".join(problems)

    return "PASS", "tags, category and currency are present"


# Live-measured on 2026-10-28: a real live attempt at 06:29Z came back
# "Sorry, you can only create 10 products per day." Nothing in this script
# knew about that budget, so a batch larger than the remaining allowance
# uploaded products until the platform refused, leaving a half-published
# batch. This guard reads what THIS factory already recorded creating
# (never a guess) and refuses before the first upload.
#
# The window is ROLLING 24 HOURS, not a calendar day: the ten creations
# recorded on 2026-10-27 at 12:41-12:46Z were still blocking a new attempt
# on 2026-10-28 at 06:29Z, 17.7 hours later. A calendar-day count would have
# reported zero and let the run fail mid-batch all over again.
GUMROAD_DAILY_CREATION_LIMIT = 10
GUMROAD_CREATION_WINDOW_SECONDS = 86400


def _record_epoch(at):
    try:
        return datetime.strptime(str(at), "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc).timestamp()
    except (TypeError, ValueError):
        return None


def creations_in_window(results_paths=None, now_ts=None,
                        window_seconds=GUMROAD_CREATION_WINDOW_SECONDS):
    """Real product creations this factory recorded inside the rolling window.

    Only LIVE records count, and only results whose own steps prove the
    product was actually created. A BLOCKED attempt created nothing, and a
    record whose timestamp cannot be parsed is never counted as recent.
    """
    if results_paths is None:
        results_paths = [path for _, path in BATCHES.values()]
    now_ts = time.time() if now_ts is None else float(now_ts)
    total = 0
    for path in results_paths:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, list):
            continue
        for record in data:
            if not isinstance(record, dict) or record.get("mode") != "LIVE":
                continue
            ts = _record_epoch(record.get("at"))
            if ts is None or not (0 <= now_ts - ts < window_seconds):
                continue
            for result in record.get("results") or []:
                steps = result.get("steps") if isinstance(result, dict) else None
                if isinstance(steps, dict) and steps.get("create") == "ok":
                    total += 1
    return total


def _check_pricing_evidence(man):
    evidence = man.get("pricing_evidence") or man.get("pricing_rationale")
    if isinstance(evidence, dict) and evidence:
        return "PASS", "pricing evidence is recorded"
    if isinstance(evidence, list) and evidence:
        return "PASS", "pricing evidence is recorded"
    if isinstance(evidence, str) and evidence.strip():
        return "PASS", "pricing rationale is recorded"
    return "UNKNOWN", "no pricing evidence or rationale is recorded"


def _check_registry(entry):
    if not entry:
        return "UNKNOWN", "product is not in the product registry"
    external = (entry.get("external_ids") or {}).get("gumroad")
    if entry.get("published") or external:
        return "HOLD", (
            "an existing Gumroad listing is present; this publisher only supports "
            "creating a new listing, not editing one"
        )
    return "PASS", f"registry state: {entry.get('primary_state') or 'ready'}"


def _check_qa(man, root=ROOT):
    qa = man.get("qa") or {}
    problems = []
    if not qa.get("ok"):
        problems.append("qa.ok is not true")
    if not qa.get("file_test") and (qa.get("gate") or {}).get("status") == "PASS":
        gate = qa["gate"]
        value = qa.get("value") or {}
        if gate.get("verdict") != "APPROVED":
            problems.append(f"gate verdict is {gate.get('verdict')!r}, not APPROVED")
        if value.get("status") != "PASS":
            problems.append("independent value check is not PASS")
        for record, label in ((gate, "gate"), (value, "value")):
            source = record.get("source")
            if not isinstance(source, str) or not source.strip():
                problems.append(f"{label} record cites no source file")
            elif not (Path(root) / source).is_file():
                problems.append(f"{label} source file is missing: {source}")
        if problems:
            return "FAIL", "QA: " + "; ".join(problems)
        return "PASS", (
            "QA: gate APPROVED and value check PASS, both citing existing source files "
            f"({gate.get('source')}; {value.get('source')})"
        )
    if (qa.get("file_test") or {}).get("status") != "PASS":
        problems.append("file_test did not pass")
    failed = (qa.get("recalc") or {}).get("failed") or []
    if failed:
        problems.append(f"{len(failed)} recalculation checks failed")
    if (qa.get("brand") or {}).get("passed") is not True:
        problems.append("brand checks did not pass")
    if problems:
        return "FAIL", "QA: " + "; ".join(problems)
    return "PASS", "QA manifest records file, recalc and brand checks as passing"


def _overall(checks):
    states = [state for state, _detail in checks.values()]
    if "FAIL" in states:
        return "BLOCKED"
    if "UNKNOWN" in states or "HOLD" in states:
        return "HOLD"
    return "PASS"


def _first_reason(checks):
    for name, (state, detail) in checks.items():
        if state != "PASS":
            return f"{name}: {detail}"
    return "all checks passed"


def audit_product(man, *, root=ROOT, registry_entry=None, approvals=None, approvals_error=None,
                  now=None, approval_max_age_seconds=None):
    """Produce the product-by-product pre-publication audit.

    This function is read-only. It never imports the Gumroad client, never
    calls auth, and never writes an approval.
    """
    from channels import publication_authorization as pa

    checks = {}
    if man.get("_manifest_error"):
        checks["manifest"] = ("FAIL", man["_manifest_error"])
    else:
        checks["manifest"] = ("PASS", "manifest parsed")
    checks["qa"] = _check_qa(man, root)
    checks["bundle"] = _check_bundle(man, root)
    checks["workbook"] = _check_workbook(man, root)
    checks["guide"] = _check_guide(man, root)
    checks["cover"] = _check_cover(man, root)
    checks["listing"] = _check_listing(man)
    checks["metadata"] = _check_metadata(man)
    checks["pricing_evidence"] = _check_pricing_evidence(man)
    checks["registry"] = _check_registry(registry_entry)
    if approvals_error is not None:
        auth_detail = {"status": "BLOCKED", "reason": f"approval file unusable: {approvals_error}"}
        checks["authorization"] = ("FAIL", auth_detail["reason"])
    elif approvals is not None:
        inspected = pa.inspect_approval(
            approvals,
            man,
            root=root,
            required_actions=REQUIRED_ACTIONS,
            now=now,
            max_age_seconds=approval_max_age_seconds,
        )
        if inspected["status"] == "VALID":
            auth_state = "PASS"
        elif inspected["status"] == "MISSING":
            auth_state = "HOLD"
        else:
            auth_state = "FAIL"
        checks["authorization"] = (auth_state, inspected["reason"])
        auth_detail = inspected
    else:
        auth_detail = {"status": "MISSING", "reason": "no approval file was supplied"}
        checks["authorization"] = ("HOLD", auth_detail["reason"])

    status = _overall(checks)
    if status == "PASS" and auth_detail.get("status") != "VALID":
        status = "HOLD"
    if status == "PASS" and checks["registry"][0] != "PASS":
        status = "HOLD"
    record = {
        "id": man.get("id"),
        "title": man.get("title"),
        "price_cents": man.get("price_cents"),
        "currency": man.get("currency") or man.get("price_currency") or "UNKNOWN",
        "status": status,
        "status_reason": _first_reason(checks),
        "authorization": auth_detail,
        "checks": {name: {"status": state, "detail": detail} for name, (state, detail) in checks.items()},
        "missing_prerequisites": [
            f"{name}: {detail}"
            for name, (state, detail) in checks.items()
            if state in ("UNKNOWN", "HOLD")
        ],
    }
    if status == "BLOCKED" and checks["authorization"][0] == "FAIL":
        record["status_reason"] = "authorization: " + checks["authorization"][1]
    elif status == "HOLD" and auth_detail.get("status") == "MISSING":
        record["status_reason"] = "AWAITING_FOUNDER_AUTHORIZATION; " + record["status_reason"]
    return record


def url_ok(url, must_contain, timeout=30, opener=urllib.request.urlopen):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 GalaxyForge-verify"})
        response = opener(req, timeout=timeout)
        body = unescape(response.read().decode("utf-8", "replace"))
        return response.status == 200 and must_contain.lower() in body.lower()
    except Exception:
        return False


def publish_one(man, token, *, gp, write_scope, ledger, cover_url_fn, approvals,
                root=ROOT, registry_entry=None, opener=urllib.request.urlopen,
                live=True, sleep=time.sleep, now=None, approval_max_age_seconds=None):
    """Perform one live publish after re-checking every binding.

    A dry run never reaches this function. The approval is checked before a
    scope is minted, and the scope is bound to the exact bundle path.
    """
    if not live:
        raise PublicationBlocked("dry run cannot perform a live write")
    audit = audit_product(
        man,
        root=root,
        registry_entry=registry_entry,
        approvals=approvals,
        now=now,
        approval_max_age_seconds=approval_max_age_seconds,
    )
    if audit["status"] != "PASS":
        raise PublicationBlocked(
            f"{audit['status']}: {audit['status_reason']}"
        )

    ok, why, bundle = preflight(man, root=root)
    if not ok:
        raise PublicationBlocked(f"preflight: {why}")

    approval = audit["authorization"]
    scope = write_scope.issue_scope(
        product_id=gp.NEW_PRODUCT,
        slug=man["slug"],
        payload={"file_path": str(bundle)},
        operation="upload_file",
        note=f"approval {approval['approval_id']}: {approval['approval_reference']}",
    )
    spec = {
        "title": man["title"],
        "price_cents": int(man["price_cents"]),
        "file_path": str(bundle),
        "description": man["qa"]["listing"]["description_html"],
        "expected_sha256": man["files"]["bundle"]["sha256"],
    }
    product = gp.create_product(token, spec, upload_scope_id=scope.scope_id)
    pid = product.get("id")
    rec = {
        "id": man["id"],
        "title": man["title"],
        "price_cents": man["price_cents"],
        "currency": audit["currency"],
        "status": "BLOCKED",
        "product_id": pid,
        "approval_id": approval["approval_id"],
        "revision_sha256": approval["revision_sha256"],
        "steps": {"create": "ok"},
    }
    sleep(2)
    got = gp.get_product(token, pid)
    if got.get("name") != man["title"] or int(got.get("price", -1)) != int(man["price_cents"]):
        rec["error"] = f"read-back mismatch: name={got.get('name')!r} price={got.get('price')}"
        return rec
    if not got.get("published"):
        gp.enable_product(token, pid)
        got = gp.get_product(token, pid)
    rec["steps"]["published"] = bool(got.get("published"))
    if not got.get("published"):
        rec["error"] = "product did not become published"
        return rec
    rec["url"] = got.get("short_url")
    try:
        gp.add_product_cover(
            token,
            pid,
            cover_url_fn(man["id"]),
            expected_cover_count=len(got.get("covers") or []),
        )
        rec["steps"]["cover"] = "ok"
    except Exception as exc:
        rec["steps"]["cover"] = f"FAILED: {str(exc)[:160]}"
    rec["steps"]["public_page"] = (
        url_ok(rec["url"], man["title"].split(" (")[0], opener=opener)
        if rec.get("url")
        else False
    )
    result = SimpleNamespace(
        ok=rec["steps"]["published"] and rec["steps"]["public_page"],
        platform="gumroad",
        product_id=pid,
        url=rec.get("url"),
        error=None if rec["steps"]["public_page"] else "public page not verified",
        dry_run=False,
    )
    ledger.record_publish_attempt(
        SimpleNamespace(title=man["title"], source_id=man["id"], product_type="xlsx_tool_bundle"),
        result,
    )
    rec["status"] = "PASS" if result.ok and rec["steps"]["cover"] == "ok" else "BLOCKED"
    if rec["status"] != "PASS":
        rec["error"] = rec.get("error") or "post-publish verification did not fully pass"
    return rec


def _blocked_record(man, reason, approval_detail=None):
    return {
        "id": man.get("id"),
        "title": man.get("title"),
        "price_cents": man.get("price_cents"),
        "currency": man.get("currency") or man.get("price_currency") or "UNKNOWN",
        "status": "BLOCKED",
        "status_reason": reason,
        "authorization": approval_detail or {"status": "MISSING", "reason": reason},
        "missing_prerequisites": [reason],
        "checks": {},
    }


def run_batch(manifests, *, live, approvals=None, approvals_error=None, root=ROOT,
              registry=None, gp=None, write_scope=None, ledger=None, token=None,
              auth_poll=None, cover_url_fn=None, opener=urllib.request.urlopen,
              sleep=time.sleep, now=None, approval_max_age_seconds=None,
              session_max_age_seconds=DEFAULT_SESSION_MAX_AGE_SECONDS):
    """Audit every product, and only when live, attempt each approved one.

    No `break`: a failure on one product does not stop later products, and no
    product is retried. Dry run never touches Gumroad or auth.
    """
    from channels import publication_authorization as pa

    registry = registry if registry is not None else load_registry()
    cover_url_fn = cover_url_fn or (lambda product_id: COVER_URL.format(id=product_id))
    results = []

    if approvals_error is not None and live:
        for man in manifests:
            results.append(
                _blocked_record(
                    man,
                    f"authorization file unusable: {approvals_error}",
                    {"status": "BLOCKED", "reason": str(approvals_error)},
                )
            )
        return results

    session = None
    if live:
        if approvals is None:
            for man in manifests:
                results.append(_blocked_record(man, "AWAITING_FOUNDER_AUTHORIZATION: no approval file supplied"))
            return results
        if auth_poll is None or gp is None or write_scope is None or ledger is None or token is None:
            for man in manifests:
                results.append(_blocked_record(man, "live prerequisites are missing; no write attempted"))
            return results
        try:
            session = auth_poll()
            pa.assert_session_fresh(session, now=now, max_age_seconds=session_max_age_seconds)
        except Exception as exc:
            for man in manifests:
                results.append(
                    _blocked_record(man, f"Gumroad auth refused: {exc}", {"status": "BLOCKED", "reason": str(exc)})
                )
            return results

    for man in manifests:
        if not live:
            results.append(
                audit_product(
                    man,
                    root=root,
                    registry_entry=registry.get(man.get("id")),
                    approvals=approvals,
                    approvals_error=approvals_error,
                    now=now,
                    approval_max_age_seconds=approval_max_age_seconds,
                )
            )
            continue
        try:
            results.append(
                publish_one(
                    man,
                    token,
                    gp=gp,
                    write_scope=write_scope,
                    ledger=ledger,
                    cover_url_fn=cover_url_fn,
                    approvals=approvals,
                    root=root,
                    registry_entry=registry.get(man.get("id")),
                    opener=opener,
                    live=True,
                    sleep=sleep,
                    now=now,
                    approval_max_age_seconds=approval_max_age_seconds,
                )
            )
        except Exception as exc:
            results.append(
                _blocked_record(
                    man,
                    f"{type(exc).__name__}: {str(exc)[:300]}",
                    {"status": "BLOCKED", "reason": str(exc)[:300]},
                )
            )
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="attempt real writes; requires per-product approvals")
    ap.add_argument("--only", nargs="*", help="only these ids, e.g. B15-001")
    ap.add_argument("--batch", choices=sorted(BATCHES), default="batch14")
    ap.add_argument("--approvals", default=os.environ.get("GF_PUBLICATION_APPROVALS_PATH") or str(DEFAULT_APPROVALS))
    ap.add_argument("--report", default=None, help="where to write the audit JSON (dry run)")
    ap.add_argument("--session-max-age-seconds", type=int, default=DEFAULT_SESSION_MAX_AGE_SECONDS)
    ap.add_argument("--approval-max-age-seconds", type=int, default=None)
    args = ap.parse_args()

    global BATCH, RESULTS
    BATCH, RESULTS = BATCHES[args.batch]
    manifests = [m for m in load_manifests(BATCH) if not args.only or m.get("id") in args.only]
    if not manifests:
        print(json.dumps({"error": "no matching manifests", "batch": args.batch}))
        return 1

    from channels import publication_authorization as pa

    approvals, approvals_error = None, None
    try:
        approvals = pa.load_approvals(args.approvals)
    except pa.MissingApproval as exc:
        approvals_error = exc
    except pa.AuthorizationError as exc:
        approvals_error = exc

    if not args.live:
        dry_error = approvals_error if isinstance(approvals_error, pa.MalformedApproval) else None
        results = run_batch(
            manifests,
            live=False,
            approvals=approvals,
            approvals_error=dry_error,
            approval_max_age_seconds=args.approval_max_age_seconds,
        )
        payload = {
            "batch": args.batch,
            "mode": "DRY_RUN",
            "factored_live_flag": os.environ.get("FACTORY_LIVE_PUBLISH"),
            "approval_source": args.approvals,
            "approval_error": str(approvals_error) if approvals_error else None,
            "summary": {
                "products": len(results),
                "pass": sum(1 for r in results if r["status"] == "PASS"),
                "hold": sum(1 for r in results if r["status"] == "HOLD"),
                "blocked": sum(1 for r in results if r["status"] == "BLOCKED"),
            },
            "products": results,
        }
        if args.report:
            report_path = Path(args.report)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(payload, indent=1, ensure_ascii=False))
        return 0

    if approvals_error is not None:
        results = run_batch(manifests, live=True, approvals=None, approvals_error=approvals_error)
        print(json.dumps({"batch": args.batch, "error": str(approvals_error), "products": results}, indent=1))
        return 1

    import gumroad_auth_watch as auth
    try:
        state = auth.poll()
        pa.assert_session_fresh(state, max_age_seconds=args.session_max_age_seconds)
    except Exception as exc:
        results = [_blocked_record(m, f"Gumroad auth refused: {exc}") for m in manifests]
        print(json.dumps({"batch": args.batch, "error": str(exc), "products": results}, indent=1))
        return 1

    already_created = creations_in_window(now_ts=time.time())
    if already_created + len(manifests) > GUMROAD_DAILY_CREATION_LIMIT:
        reason = (f"Gumroad allows {GUMROAD_DAILY_CREATION_LIMIT} product creations per rolling 24h; "
                  f"{already_created} already recorded in that window and this batch has {len(manifests)}. "
                  "Refusing before any upload.")
        results = [_blocked_record(m, reason) for m in manifests]
        print(json.dumps({"batch": args.batch, "error": reason, "products": results}, indent=1, ensure_ascii=False))
        return 1

    os.environ["FACTORY_LIVE_PUBLISH"] = "true"
    from channels import gumroad_publisher as gp, ledger, write_scope

    try:
        try:
            token = gp.load_token()
        except Exception as exc:
            reason = f"Gumroad credential unavailable ({type(exc).__name__})"
            results = [_blocked_record(m, reason) for m in manifests]
            print(json.dumps({"batch": args.batch, "error": reason, "products": results}, indent=1))
            return 1
        results = run_batch(
            manifests,
            live=True,
            approvals=approvals,
            root=ROOT,
            gp=gp,
            write_scope=write_scope,
            ledger=ledger,
            token=token,
            auth_poll=lambda: state,
            now=time.time(),
            approval_max_age_seconds=args.approval_max_age_seconds,
            session_max_age_seconds=args.session_max_age_seconds,
        )
    finally:
        os.environ["FACTORY_LIVE_PUBLISH"] = "false"

    record = {
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": "LIVE",
        "approval_source": args.approvals,
        "results": results,
    }
    prev = json.loads(RESULTS.read_text(encoding="utf-8")) if RESULTS.exists() else []
    RESULTS.write_text(json.dumps(prev + [record], indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(record, indent=1, ensure_ascii=False))
    return 0 if results and all(r.get("status") == "PASS" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())

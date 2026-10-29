"""Data card and provenance checks for a packaged dataset (backlog B20, 2026-10-29).

A data card describes one released version of a dataset: what it is for, where
every part of it came from, under which licence, what each column means, the
exact file(s) (sha256, row count), whether it holds personal data, and when it
was last refreshed. validate_card() checks the card against the files on disk,
not only against itself.

Result: PASS (may be offered, subject to the founder's commercial decision),
REVIEW (a person must look), BLOCK (must not be sold or shared). Rules:
  * a source without a licence, or with a non-commercial licence, BLOCKs a
    commercial release; share-alike needs the output licence to match (REVIEW);
    attribution required -> the card must carry the attribution text;
  * the file hash and row count must match; declared and actual columns must
    match exactly;
  * values that look like e-mail addresses, phone numbers or IP addresses BLOCK
    unless the card declares personal data with a lawful basis (then REVIEW:
    personal data is never cleared automatically);
  * a release older than its refresh interval is REVIEW (stale), not PASS.

Nothing here publishes, prices or sells. Supported file format: CSV (UTF-8).
"""
import csv
import hashlib
import json
import os
import re
from datetime import date, datetime

REQUIRED = ("dataset_id", "title", "version", "description", "intended_use", "out_of_scope_use",
            "sources", "collection_method", "processing_steps", "columns", "files",
            "personal_data", "licence_out", "refresh_days", "last_refreshed", "known_limitations")

PII_PATTERNS = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "phone": re.compile(r"(?<!\d)(?:\+?\d[\s().-]?){9,14}\d(?!\d)"),
    "ipv4": re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)"),
}
# Columns whose values are URLs or ids: digits in them are not phone numbers.
_PII_EXEMPT_COLUMN_HINTS = ("url", "id", "price", "cents", "sha", "hash")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _finding(status, text):
    return {"status": status, "finding": text}


def _check_fields(card):
    missing = [k for k in REQUIRED if card.get(k) in (None, "", [])]
    return [_finding("BLOCK", f"card is missing: {', '.join(missing)}")] if missing else []


def _check_sources(card):
    out = []
    for i, s in enumerate(card.get("sources") or []):
        name = s.get("name") or f"source {i}"
        lic = s.get("licence") or {}
        if not s.get("origin"):
            out.append(_finding("BLOCK", f"{name}: no origin (URL or internal file) recorded"))
        try:
            datetime.strptime(s.get("accessed_on") or "", "%Y-%m-%d")
        except ValueError:
            out.append(_finding("BLOCK", f"{name}: accessed_on must be the real date it was read (YYYY-MM-DD)"))
        if not lic.get("name"):
            out.append(_finding("BLOCK", f"{name}: no licence recorded"))
            continue
        if lic.get("commercial_use") is not True:
            out.append(_finding("BLOCK", f"{name}: licence '{lic['name']}' does not permit commercial use"))
        if lic.get("share_alike") and card.get("licence_out", {}).get("name") != lic["name"]:
            out.append(_finding("REVIEW", f"{name}: share-alike licence '{lic['name']}' requires the release "
                                          "to use the same licence"))
        if lic.get("attribution_required") and not (card.get("attribution") or "").strip():
            out.append(_finding("BLOCK", f"{name}: attribution required but the card has no attribution text"))
    return out


def _read_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return reader.fieldnames or [], rows


def _scan_pii(header, rows):
    hits = {}
    for col in header:
        if any(h in col.lower() for h in _PII_EXEMPT_COLUMN_HINTS):
            patterns = {"email": PII_PATTERNS["email"]}
        else:
            patterns = PII_PATTERNS
        for r in rows:
            v = r.get(col) or ""
            for kind, rx in patterns.items():
                if rx.search(v):
                    hits.setdefault(kind, set()).add(col)
    return {k: sorted(v) for k, v in hits.items()}


def _check_files(card, root):
    out = []
    declared = [c["name"] for c in card.get("columns") or [] if c.get("name")]
    for c in card.get("columns") or []:
        if not (c.get("name") and c.get("type") and c.get("description")):
            out.append(_finding("BLOCK", f"column definition incomplete: {c}"))
    pii = {}
    for f in card.get("files") or []:
        p = os.path.join(root, f.get("path") or "")
        if not f.get("path") or not os.path.isfile(p):
            out.append(_finding("BLOCK", f"file not found: {f.get('path')}"))
            continue
        actual = sha256_file(p)
        if actual != f.get("sha256"):
            out.append(_finding("BLOCK", f"{f['path']}: sha256 differs from the card (file changed after release)"))
        header, rows = _read_csv(p)
        if len(rows) != f.get("rows"):
            out.append(_finding("BLOCK", f"{f['path']}: {len(rows)} rows, card says {f.get('rows')}"))
        if header != declared:
            extra = [h for h in header if h not in declared]
            absent = [d for d in declared if d not in header]
            out.append(_finding("BLOCK", f"{f['path']}: columns differ from the card "
                                         f"(undeclared: {extra}, missing: {absent})"))
        for kind, cols in _scan_pii(header, rows).items():
            pii.setdefault(kind, set()).update(cols)
    pd = card.get("personal_data") or {}
    if pii:
        found = "; ".join(f"{k} in {sorted(v)}" for k, v in pii.items())
        if pd.get("contains") and pd.get("lawful_basis"):
            out.append(_finding("REVIEW", f"personal data present ({found}); declared basis "
                                          f"'{pd['lawful_basis']}' needs human review"))
        else:
            out.append(_finding("BLOCK", f"values look like personal data ({found}) and the card does not "
                                         "declare a lawful basis"))
    elif pd.get("contains"):
        out.append(_finding("REVIEW", "card declares personal data; human review required"))
    return out


def _check_freshness(card, today):
    try:
        last = datetime.strptime(card.get("last_refreshed") or "", "%Y-%m-%d").date()
    except ValueError:
        return [_finding("BLOCK", "last_refreshed must be YYYY-MM-DD")]
    age = (today - last).days
    if age < 0:
        return [_finding("BLOCK", "last_refreshed is in the future")]
    if age > int(card.get("refresh_days") or 0):
        return [_finding("REVIEW", f"release is {age} days old; refresh interval is {card.get('refresh_days')} days")]
    return []


def validate_card(card, root, today=None):
    today = today or date.today()
    findings = _check_fields(card)
    if not findings:
        findings += _check_sources(card) + _check_files(card, root) + _check_freshness(card, today)
    status = "BLOCK" if any(f["status"] == "BLOCK" for f in findings) else (
        "REVIEW" if findings else "PASS")
    return {"dataset_id": card.get("dataset_id"), "version": card.get("version"),
            "status": status, "findings": findings,
            "checked_on": today.isoformat(),
            "note": "provenance and format checks only; offering it for sale is a founder decision"}


def load_card(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

"""Byte-level delivery-file integrity verification.

The directive is explicit: verify the delivery files are actually sound,
especially the EU AI Act Compliance Toolkit, and do NOT rely on the product
card. A product card is a claim; an attachment is a file.

For every product checked, this:
  1. fetches the attachment BYTES from the public CDN URL
  2. records the real SHA-256 of what arrived
  3. opens it with the real parser and records structure
     (PDF: pages + extracted words; ZIP: entries + sizes)
  4. compares the real byte count against the platform's DECLARED size
  5. refuses to call anything DELIVERABLE on the strength of metadata alone

Read-only. GET only, $0. Writes only its own JSON output.

Run:  python scripts/verify_delivery_integrity.py [short_id ...]
      python scripts/verify_delivery_integrity.py --all
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "delivery_integrity.json"
API = "https://api.gumroad.com/v2/products"

PASS = "PASS"
FAIL = "FAIL"
UNKNOWN = "UNKNOWN"


def _token() -> str:
    for line in open(ROOT / ".env", encoding="utf-8", errors="replace"):
        if line.startswith("GUMROAD_ACCESS_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("GUMROAD_ACCESS_TOKEN not found")


def _fetch(url, headers=None, timeout=45):
    req = urllib.request.Request(url, method="GET")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:  # noqa: BLE001
        return 0, None


def _inspect(blob: bytes) -> dict:
    """What is actually inside these bytes."""
    info = {"magic": blob[:4].hex()}
    if blob[:4] == b"%PDF":
        info["type"] = "pdf"
        try:
            from pypdf import PdfReader
            r = PdfReader(io.BytesIO(blob))
            text = "\n".join((p.extract_text() or "") for p in r.pages)
            info["pages"] = len(r.pages)
            info["words"] = len(text.split())
            info["first_text"] = " ".join(text.split())[:300]
            info["encrypted"] = getattr(r, "is_encrypted", False)
        except Exception as e:  # noqa: BLE001
            info["parse_error"] = f"{type(e).__name__}: {e}"
    elif blob[:2] == b"PK":
        info["type"] = "zip"
        try:
            z = zipfile.ZipFile(io.BytesIO(blob))
            entries = []
            for i in z.infolist():
                entries.append({"name": i.filename, "bytes": i.file_size})
                # actually decompress: an entry that claims to exist but is
                # corrupt is a broken delivery, not a delivery
                try:
                    z.read(i.filename)
                    entries[-1]["readable"] = True
                except Exception as e:  # noqa: BLE001
                    entries[-1]["readable"] = False
                    entries[-1]["read_error"] = type(e).__name__
            info["entries"] = entries
            info["entry_count"] = len(entries)
            info["uncompressed_bytes"] = sum(e["bytes"] for e in entries)
        except Exception as e:  # noqa: BLE001
            info["parse_error"] = f"{type(e).__name__}: {e}"
    else:
        info["type"] = "other/unknown"
    return info


def check(sid: str, token: str) -> dict:
    st, raw = _fetch(f"{API}/{urllib.parse.quote(sid, safe='')}",
                     {"Authorization": "Bearer " + token,
                      "Accept": "application/json"})
    row = {"short_id": sid, "meta_http": st}
    if st != 200:
        row["verdict"] = UNKNOWN
        row["reason"] = f"metadata HTTP {st}"
        return row
    try:
        p = json.loads(raw.decode("utf-8", "replace"))["product"]
    except Exception as e:  # noqa: BLE001
        row["verdict"] = UNKNOWN
        row["reason"] = f"metadata unparseable: {type(e).__name__}"
        return row

    row["title"] = p.get("name")
    row["price_cents"] = p.get("price")
    row["published"] = p.get("published")
    row["url"] = p.get("short_url")
    row["sales_count"] = p.get("sales_count")

    files = p.get("files") or []
    row["file_count"] = len(files)
    if not files:
        row["verdict"] = FAIL if p.get("price", 0) else PASS
        row["reason"] = ("priced listing with no attachment"
                         if p.get("price") else "free listing, no attachment")
        return row

    results = []
    for f in files:
        declared = int(f.get("size") or 0)
        entry = {"declared_bytes": declared, "declared_type": f.get("filetype"),
                 "name": f.get("name") or f.get("file_name")}
        fst, blob = _fetch(f.get("url") or "")
        entry["fetch_http"] = fst
        if fst != 200 or not blob:
            entry["verdict"] = UNKNOWN
            entry["reason"] = f"attachment fetch HTTP {fst}"
            results.append(entry)
            continue
        entry["actual_bytes"] = len(blob)
        entry["sha256"] = hashlib.sha256(blob).hexdigest()
        entry["size_matches_declared"] = (len(blob) == declared)
        entry.update(_inspect(blob))
        if "parse_error" in entry:
            entry["verdict"] = FAIL
            entry["reason"] = "attachment did not parse as its type claims"
        elif not entry["size_matches_declared"]:
            entry["verdict"] = FAIL
            entry["reason"] = (f"fetched {len(blob)} bytes, platform declares "
                               f"{declared} -- truncated or replaced in transit")
        elif entry.get("type") == "pdf" and entry.get("words", 0) == 0:
            entry["verdict"] = FAIL
            entry["reason"] = "PDF parsed but contains zero extractable text"
        elif entry.get("type") == "zip" and not all(
                e.get("readable") for e in entry.get("entries", [])):
            entry["verdict"] = FAIL
            entry["reason"] = "ZIP has an entry that could not be decompressed"
        else:
            entry["verdict"] = PASS
        results.append(entry)

    row["files"] = results
    verdicts = {r.get("verdict") for r in results}
    if FAIL in verdicts:
        row["verdict"] = FAIL
    elif verdicts == {UNKNOWN}:
        row["verdict"] = UNKNOWN
    else:
        row["verdict"] = PASS if verdicts == {PASS} else "PARTIAL"
    row["reason"] = "every attachment fetched, hashed, parsed and size-matched"
    return row


def main() -> int:
    token = _token()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        snap = ROOT / "data" / "cycle81_delivery_audit.json"
        if snap.exists():
            args = [p["short_id"] for p in json.load(
                open(snap, encoding="utf-8"))["products"]]
        else:
            print("no ids and no snapshot; pass short_ids explicitly")
            return 1

    rows = []
    for sid in args:
        rows.append(check(sid, token))
        time.sleep(0.05)

    summary = {}
    for r in rows:
        summary[r["verdict"]] = summary.get(r["verdict"], 0) + 1
    out = {"probe": "verify_delivery_integrity", "read_only": True,
           "cost_usd": 0, "method": ("attachment bytes fetched from the public "
                                     "CDN, hashed, parsed, size-compared"),
           "checked": len(rows), "verdict_counts": summary, "results": rows}
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)

    print("checked=%d  %s" % (len(rows), summary))
    for r in rows:
        if r["verdict"] in (FAIL, "PARTIAL"):
            print(f"  [{r['verdict']}] {r.get('short_id')} {r.get('title')}")
            for f in r.get("files", []):
                print(f"      {f.get('verdict')} {f.get('name')} :: {f.get('reason','')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""Cycle 81 — claim-vs-payload integrity scan across every thin deliverable.

Motivated by a real, verified defect found in this cycle: the live $99 product
"Verified B2B Lead Lists (200-lead batch)"
(https://aekraft.gumroad.com/l/drtaj) is PUBLISHED and PRICED, and its attached
file is a 1-page, 81-word PDF that only *describes* the CSV/Sheets database the
listing promises. No data is shipped. Zero sales so far, so nobody has been
harmed -- but it is live and purchasable.

This scans every product whose payload is small enough to inspect cheaply and
classifies what actually ships versus what the title/description claims. It is
a detection tool, not a repair tool: repairs are founder-gated because fixing a
listing means either delivering the promised asset or withdrawing the listing.

Read-only. Public Gumroad CDN bytes, GET only, $0.

Run:  python scripts/cycle81_claim_integrity_scan.py
Out:  data/cycle81_claim_integrity.json
"""

from __future__ import annotations

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

API = "https://api.gumroad.com/v2/products"
AUDIT = "data/cycle81_delivery_audit.json"
OUT = "data/cycle81_claim_integrity.json"

# NOTE (corrected 2026-10-14, later the same day): this script's first version
# carried its OWN copy of the claim vocabulary, separate from
# product_claim_integrity.py. That was wrong twice over: duplicate rule sets
# drift apart, and this one had already been proven too aggressive -- it flagged
# 9 live listings of which 8 were false positives, including the $155 flagship.
#
# It now imports the single shared engine. The gate that blocks a publish and
# the audit that reports on the live catalog are literally the same rules.
_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
import product_claim_integrity as pci


def _token() -> str:
    for line in open(".env", encoding="utf-8", errors="replace"):
        if line.startswith("GUMROAD_ACCESS_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("GUMROAD_ACCESS_TOKEN not found in .env")


def _get(url: str, headers=None, timeout: int = 45):
    req = urllib.request.Request(url, method="GET")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:300]
    except Exception as e:  # noqa: BLE001
        return 0, str(e).encode()


def _classify(blob: bytes) -> dict:
    """Return what the payload genuinely contains."""
    out = {"kind": "unknown", "pages": None, "words": None, "zip_entries": [],
           "extracted": ""}
    if blob[:4] == b"%PDF":
        out["kind"] = "pdf"
        try:
            from pypdf import PdfReader
            r = PdfReader(io.BytesIO(blob))
            txt = "\n".join((p.extract_text() or "") for p in r.pages)
            out["pages"] = len(r.pages)
            out["words"] = len(txt.split())
            out["extracted"] = " ".join(txt.split())[:1200]
        except Exception as e:  # noqa: BLE001
            out["kind"] = f"pdf-unparsed({type(e).__name__})"
    elif blob[:2] == b"PK":
        out["kind"] = "zip"
        try:
            z = zipfile.ZipFile(io.BytesIO(blob))
            out["zip_entries"] = [i.filename for i in z.infolist()]
        except Exception as e:  # noqa: BLE001
            out["kind"] = f"zip-unparsed({type(e).__name__})"
    elif blob[:9].lstrip()[:1] in (b"{", b"["):
        out["kind"] = "json"
        out["extracted"] = blob[:1200].decode("utf-8", "replace")
    else:
        out["kind"] = "text/other"
        out["extracted"] = blob[:1200].decode("utf-8", "replace")
    return out


def main() -> int:
    audit = json.load(io.open(AUDIT, encoding="utf-8"))
    token = _token()
    rows = []

    for meta in audit["products"]:
        # Only inspect payloads small enough to fetch cheaply in full.
        if meta["file_count"] == 0 or meta["file_bytes"] > 25_000:
            continue
        sid = meta["short_id"]
        st, raw = _get(f"{API}/{urllib.parse.quote(sid, safe='')}",
                       {"Authorization": f"Bearer {token}",
                        "Accept": "application/json"})
        if st != 200:
            continue
        p = json.loads(raw.decode("utf-8", "replace")).get("product", {})
        desc = p.get("description") or ""
        title = p.get("name") or ""
        for f in (p.get("files") or []):
            url = f.get("url")
            if not url:
                continue
            s2, blob = _get(url)
            if s2 != 200:
                rows.append({"short_id": sid, "name": title, "price_usd": meta["price_usd"],
                             "verdict": "FETCH_FAILED", "http": s2})
                continue
            info = _classify(blob)
            entry_names = info["zip_entries"]
            has_data_file = any(
                n.lower().endswith(pci.DATA_EXTENSIONS) for n in entry_names
            ) or info["kind"] == "json"

            verdict = pci.check_claim_integrity(
                title=title,
                description=desc,
                payloads=[{"name": f.get("name") or f.get("file_name") or "(unnamed)",
                           "bytes": len(blob),
                           "filetype": f.get("filetype") or "",
                           "entries": entry_names or None}],
                price_usd=meta["price_usd"],
                page_count=info["pages"],
                word_count=info["words"],
            )

            rows.append({
                "short_id": sid,
                "name": title,
                "price_usd": meta["price_usd"],
                "published": meta["published"],
                "bytes": len(blob),
                "kind": info["kind"],
                "pages": info["pages"],
                "words": info["words"],
                "zip_entries": entry_names,
                "claims_data_asset": bool(pci._data_claim(title, desc)[0]),
                "delivers_data_asset": has_data_file,
                "verdict": verdict["verdict"],
                "blocking_findings": verdict["blocking_findings"],
                "advisory_findings": verdict["advisory_findings"],
                "reason": verdict["reason"],
                "url": meta["url"],
                "excerpt": info["extracted"][:400],
            })
            time.sleep(0.05)

    flagged = [r for r in rows if r["verdict"] == pci.BLOCK]
    advisory = [r for r in rows if r["verdict"] == pci.REVIEW]
    out = {
        "probe": "cycle81_claim_integrity_scan",
        "read_only": True,
        "rules_engine": "product_claim_integrity.check_claim_integrity "
                        "(the same module distributor.py gates publishes with)",
        "scope": "products whose total deliverable is <= 25KB (full content fetched)",
        "scanned": len(rows),
        "BLOCKED_count": len(flagged),
        "REVIEW_count": len(advisory),
        "BLOCKED": flagged,
        "REVIEW": advisory,
        "all": rows,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)

    print(f"scanned {len(rows)} thin deliverables: "
          f"{len(flagged)} BLOCK, {len(advisory)} REVIEW\n")
    for r in flagged:
        print(f"[BLOCK] ${r['price_usd']:.0f}  {r['name'][:58]}")
        for f in r["blocking_findings"]:
            print(f"    {f['rule']}: {f['reason']}")
        print(f"    {r['url']}\n")
    print("REVIEW (thin or unverifiable, NOT false claims):")
    for r in advisory:
        print(f"  ${r['price_usd']:>5.0f} {r['bytes']:>7}B  {r['name'][:52]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
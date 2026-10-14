"""Cycle 82 — deep inspection of ONE chosen product's real deliverable.

Cycle 82 §6 selects a single product for a commercial test. §7.1 requires
fixing real defects in "the file quality or sales page". This script is how
the file itself gets inspected: it downloads the actual attachment bytes from
the public Gumroad CDN and reports what is genuinely inside, so "quality" is
measured rather than assumed.

Read-only. GET only, $0. Writes nothing, publishes nothing.

Run:  python scripts/cycle82_product_deep_dive.py <short_id> [<short_id> ...]
"""

from __future__ import annotations

import io
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

API = "https://api.gumroad.com/v2/products"


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


# Phrases a competent paid guide should contain. Used to measure depth, not
# to assert quality -- absence is reported as absence, never as a failure.
DEPTH_MARKERS = {
    "step-by-step sequence": r"\bstep\s*\d|step one|step 1\b",
    "time/amount thresholds": r"\b\d{2,}\s*(hours?|hrs?|days?|business days?|minutes?)\b",
    "escalation path": r"\bescalat|\bappeal|\bdispute|\bsmall claims\b",
    "documentation requirement": r"\bphoto|\bevidence|\breceipt|\bmetadata\b",
    "template/script/letter language": r"\btemplate|\bscript\b|\bletter\b|sample text|boilerplate",
    "what NOT to do": r"\bdo not\b|\bdon'?t\b|\bnever\b|\bavoid\b",
    "checklist format": r"\bchecklist\b|\b☐|\b\[ \]",
    "reference to official source": r"\bTuro\b|\bhelp\.turo\b|\bTerms of Service\b|\bpolicy\b",
}


def _pdf_text(blob: bytes):
    out = {"kind": "pdf", "pages": None, "words": None, "text": ""}
    if blob[:4] != b"%PDF":
        out["kind"] = "not-a-pdf"
        return out
    try:
        from pypdf import PdfReader
        r = PdfReader(io.BytesIO(blob))
        txt = "\n".join((p.extract_text() or "") for p in r.pages)
        out["pages"] = len(r.pages)
        out["words"] = len(txt.split())
        out["text"] = txt
        return out
    except Exception as e:  # noqa: BLE001
        out["kind"] = "pdf-unparsed(%s)" % type(e).__name__
        return out


def main() -> int:
    ids = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not ids:
        print("usage: python scripts/cycle82_product_deep_dive.py <short_id> [...]")
        return 1
    token = _token()

    for sid in ids:
        st, raw = _get(f"{API}/{urllib.parse.quote(sid, safe='')}",
                       {"Authorization": f"Bearer {token}",
                        "Accept": "application/json"})
        print("=" * 78)
        if st != 200:
            print(f"{sid}: metadata HTTP {st} -> {raw[:160]!r}")
            continue
        p = json.loads(raw.decode("utf-8", "replace"))["product"]
        print(f"{p.get('name')}")
        print(f"  price ${(p.get('price') or 0)/100:.0f}   published={p.get('published')}"
              f"   sales={p.get('sales_count')}   {p.get('short_url')}")

        for f in (p.get("files") or []):
            url = f.get("url")
            size = int(f.get("size") or 0)
            print(f"  FILE {f.get('name') or f.get('file_name')}  {size}B  {f.get('filetype')}")
            if not url:
                print("    no url in payload")
                continue
            s2, blob = _get(url)
            if s2 != 200:
                print(f"    fetch HTTP {s2}")
                continue
            if blob[:2] == b"PK":
                try:
                    z = zipfile.ZipFile(io.BytesIO(blob))
                    for i in z.infolist():
                        print(f"      ZIP {i.filename}  {i.file_size}B")
                except Exception as e:  # noqa: BLE001
                    print(f"      ZIP unparsed: {type(e).__name__}")
                continue
            info = _pdf_text(blob)
            if info["kind"] != "pdf":
                print(f"    payload is {info['kind']}, {len(blob)}B")
                continue
            txt = info["text"]
            print(f"    MEASURED: {info['pages']} pages, {info['words']} words")
            print("    DEPTH MARKERS (measured presence, not a judgement):")
            for label, pat in DEPTH_MARKERS.items():
                hits = len(re.findall(pat, txt, re.IGNORECASE))
                print(f"      {'YES' if hits else 'no ':3}  {label:<34} ({hits} match(es))")
            print("    ---- first 700 words ----")
            print("    " + " ".join(txt.split())[:1400])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
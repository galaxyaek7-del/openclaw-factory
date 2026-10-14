"""Cycle 81 — inspect actual deliverables for the three highest-priced products.

The delivery audit shows real file sizes. Size alone is not a verdict: a
$99 CSV of 200 leads can legitimately be ~2KB, while a $399 "V2 Bundle" at
17KB deserves a real look. This fetches the actual attachment bytes (public
Gumroad CDN URL, GET only, $0) and reports what is genuinely inside.

Nothing is uploaded, published, or purchased. Read-only.

Run:  python scripts/cycle81_deliverable_inspect.py
"""

from __future__ import annotations

import io
import json
import sys
import urllib.error
import urllib.request
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API = "https://api.gumroad.com/v2/products"
TARGETS = ["jlxmez", "lrmgml", "drtaj"]  # $399 GCC, $327 Legal, $99 B2B leads


def _token() -> str:
    for line in open(".env", encoding="utf-8", errors="replace"):
        if line.startswith("GUMROAD_ACCESS_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("GUMROAD_ACCESS_TOKEN not found in .env")


def _get_bytes(url: str, headers: dict | None = None, timeout: int = 45):
    req = urllib.request.Request(url, method="GET")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:400]
    except Exception as e:  # noqa: BLE001
        return 0, str(e).encode()


def main() -> int:
    token = _token()
    for sid in TARGETS:
        st, raw = _get_bytes(f"{API}/{sid}",
                             {"Authorization": f"Bearer {token}",
                              "Accept": "application/json"})
        print("=" * 78)
        if st != 200:
            print(f"{sid}: metadata HTTP {st} -- {raw[:200]!r}")
            continue
        p = json.loads(raw.decode("utf-8", "replace"))["product"]
        print(f"{p.get('name')}  --  ${(p.get('price') or 0)/100:.0f}")
        for f in (p.get("files") or []):
            name = f.get("name") or f.get("file_name") or "(unnamed)"
            url = f.get("url")
            size = int(f.get("size") or 0)
            print(f"  file: {name}  declared={size}B  type={f.get('filetype')}")
            if not url:
                print("    no download url in payload")
                continue
            s2, body = _get_bytes(url)
            print(f"    fetch HTTP {s2}, got {len(body)} bytes")
            if s2 != 200 or len(body) < 200:
                print("    could not inspect content")
                continue
            if body[:4] == b"%PDF":
                try:
                    from pypdf import PdfReader
                    r = PdfReader(io.BytesIO(body))
                    txt = "\n".join((pg.extract_text() or "") for pg in r.pages)
                    words = len(txt.split())
                    print(f"    PDF: {len(r.pages)} pages, {words} words extracted")
                    print("    first 300 chars: " +
                          " ".join(txt.split())[:300])
                except Exception as e:  # noqa: BLE001
                    print(f"    PDF parse unavailable: {type(e).__name__}")
            elif body[:2] == b"PK":
                try:
                    z = zipfile.ZipFile(io.BytesIO(body))
                    infos = z.infolist()
                    print(f"    ZIP: {len(infos)} entries, "
                          f"{sum(i.file_size for i in infos)} bytes uncompressed")
                    for i in infos[:40]:
                        print(f"      - {i.filename}  ({i.file_size}B)")
                except Exception as e:  # noqa: BLE001
                    print(f"    ZIP parse failed: {type(e).__name__}: {e}")
            else:
                head = body[:600].decode("utf-8", "replace")
                lines = [ln for ln in head.splitlines() if ln.strip()]
                print(f"    text-ish payload, {len(lines)} lines in first 600B")
                for ln in lines[:6]:
                    print("      |", ln[:110])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
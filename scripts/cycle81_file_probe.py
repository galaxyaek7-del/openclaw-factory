"""Cycle 81 — verify whether the $155 flagship product really has no file.

`has_file` in gumroad_catalog_truth.py infers from the `files` / `file_info`
keys. Before calling that a delivery defect we must confirm it against the raw
payload rather than trust one inferred boolean. This prints the raw
file-related keys for a named product.

Read-only. Usage:
    python scripts/cycle81_file_probe.py <short_url_id> [more ids...]
    python scripts/cycle81_file_probe.py --list
"""

from __future__ import annotations

import io
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.gumroad.com/v2/products"


def _token() -> str:
    for line in open(".env", encoding="utf-8", errors="replace"):
        if line.startswith("GUMROAD_ACCESS_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("GUMROAD_ACCESS_TOKEN not found in .env")


def _get(url: str, token: str, timeout: int = 30):
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return 0, f"{type(e).__name__}: {e}"


def main() -> int:
    d = json.load(io.open("data/cycle81_gumroad_catalog_truth.json", encoding="utf-8-sig"))
    by_short = {p["url"].rstrip("/").split("/")[-1]: p for p in d["products"] if p["url"]}

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        args = [k for k, v in by_short.items() if not v["has_file"]]
        print("no ids given -- defaulting to every product with has_file == False")

    token = _token()
    for sid in args:
        meta = by_short.get(sid)
        print("=" * 78)
        print(f"short id : {sid}")
        print(f"listed as: {meta['name'] if meta else '(not in our snapshot)'}")
        st, body = _get(f"{API}/{urllib.parse.quote(sid, safe='')}", token)
        print(f"GET /v2/products/{sid} -> HTTP {st}")
        if st != 200:
            print(f"  body: {body[:300]}")
            continue
        p = json.loads(body).get("product", {})
        for key in ("files", "file_info", "require_shipping", "published",
                    "price", "formatted_price", "sales_count", "sales_usd_cents"):
            print(f"  {key:<18} = {json.dumps(p.get(key), ensure_ascii=False)[:400]}")
        n = len(p.get("files") or [])
        print(f"  --> ATTACHED FILES: {n}")
        for f in (p.get("files") or []):
            print(f"      {f.get('file_name')}  ({f.get('size')} bytes, "
                  f"status={f.get('status')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
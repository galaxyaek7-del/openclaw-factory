"""Fill the storefront's missing media from each product's own live listing.

Every product published before the manifest system has no ``files.cover`` in a
manifest, so ``lib/public_catalog.js`` cannot resolve a cover and the product
can never be featured on customer_site/products.html -- 79 of 102 published
products were invisible for exactly this reason (measured 2026-10-28).

This script reads nothing but the product's own public Gumroad page:

* the cover is that page's own ``og:image``, downloaded and stored under
  ``customer_site/assets/covers/``;
* the summary is that page's own ``og:description``, trimmed, never rewritten.

Nothing is generated, paraphrased or invented. A product whose page does not
expose an image or description is recorded with the field absent, and stays
unfeatured -- the same honest gap as before, never a placeholder.

    python scripts/backfill_public_media.py --limit 30        # bounded, resumable
    python scripts/backfill_public_media.py --dry-run         # report only
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "data" / "product_registry.json"
MEDIA = ROOT / "data" / "public_media.json"
COVERS = ROOT / "customer_site" / "assets" / "covers"
UA = "Mozilla/5.0 (compatible; GalaxyForgeCatalog/1.0)"
DELAY_SECONDS = 1.2
MAX_SUMMARY = 300


def load_media():
    try:
        data = json.loads(MEDIA.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"generated_at": None, "products": {}}
    if not isinstance(data, dict) or not isinstance(data.get("products"), dict):
        return {"generated_at": None, "products": {}}
    return data


def manifest_has_cover(product):
    rel = product.get("manifest")
    if not isinstance(rel, str):
        return False
    try:
        manifest = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    path = ((manifest.get("files") or {}).get("cover") or {}).get("path")
    return bool(path) and (ROOT / path).is_file()


def fetch(url, timeout=40):
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(request, timeout=timeout).read()


def fetch_page(url, attempts=3):
    """Read a public page, backing off on the platform's own rate limit."""
    delay = 5.0
    last = None
    for attempt in range(attempts):
        try:
            return fetch(url).decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code == 429 and attempt + 1 < attempts:
                time.sleep(delay)
                delay *= 2
                continue
            raise
        except Exception as exc:  # noqa: BLE001 - reported, never guessed
            last = exc
            if attempt + 1 < attempts:
                time.sleep(delay)
                delay *= 2
                continue
            raise
    raise last


def meta(html, prop):
    pattern = r'<meta[^>]+(?:property|name)="%s"[^>]+content="([^"]*)"' % re.escape(prop)
    hit = re.search(pattern, html)
    return hit.group(1).strip() if hit else None


def trim(text_value, limit=MAX_SUMMARY):
    clean = re.sub(r"\s+", " ", text_value or "").strip()
    if not clean:
        return None
    if len(clean) <= limit:
        return clean
    cut = clean[:limit]
    return cut[:cut.rfind(" ")] + "..." if " " in cut else cut + "..."


def image_extension(payload):
    if payload[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if payload[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if payload[:4] == b"RIFF" and payload[8:12] == b"WEBP":
        return ".webp"
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    products = [p for p in registry.get("products") or [] if p.get("published") is True]
    media = load_media()
    entries = media["products"]

    pending = []
    for product in products:
        pid = product.get("internal_id")
        url = product.get("url") or ""
        if not pid or not url.startswith("http"):
            continue
        if manifest_has_cover(product):
            continue
        existing = entries.get(pid) or {}
        cover = existing.get("cover")
        if cover and (ROOT / cover).is_file():
            continue
        pending.append(product)

    report = {
        "published": len(products),
        "already_resolved": len(products) - len(pending),
        "pending": len(pending),
        "attempted": 0,
        "cover_saved": 0,
        "summary_saved": 0,
        "failed": [],
        "dry_run": args.dry_run,
    }

    for product in pending[: max(0, args.limit)]:
        pid = product["internal_id"]
        url = product["url"]
        report["attempted"] += 1
        try:
            html = fetch_page(url)
        except Exception as exc:  # noqa: BLE001
            report["failed"].append({"id": pid, "stage": "page", "error": f"{type(exc).__name__}: {exc}"[:160]})
            time.sleep(DELAY_SECONDS)
            continue

        image_url = meta(html, "og:image")
        summary = trim(meta(html, "og:description") or meta(html, "description"))
        entry = {"source_url": url, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        if summary:
            entry["summary"] = summary
            report["summary_saved"] += 1

        if image_url:
            try:
                payload = fetch(image_url)
                ext = image_extension(payload)
                if ext is None:
                    raise ValueError("not a PNG/JPEG/WebP image")
                rel = f"customer_site/assets/covers/{pid}{ext}"
                if not args.dry_run:
                    COVERS.mkdir(parents=True, exist_ok=True)
                    (ROOT / rel).write_bytes(payload)
                entry["cover"] = rel
                report["cover_saved"] += 1
            except Exception as exc:  # noqa: BLE001
                report["failed"].append({"id": pid, "stage": "cover", "error": f"{type(exc).__name__}: {exc}"[:160]})

        if not args.dry_run and (entry.get("cover") or entry.get("summary")):
            entries[pid] = entry

        time.sleep(DELAY_SECONDS)

    if not args.dry_run:
        media["products"] = entries
        media["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        MEDIA.parent.mkdir(parents=True, exist_ok=True)
        MEDIA.write_text(json.dumps(media, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

    report["entries_total"] = len(entries)
    print(json.dumps(report, indent=1, ensure_ascii=False))
    return 0 if not report["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

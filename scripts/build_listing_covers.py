"""Covers (1280x720 PNG) for live Gumroad products that have none.

    python scripts/build_listing_covers.py [--catalog <gumroad products json>]

Reads the live catalog (Gumroad GET /v2/products, read-only) unless a saved
catalog is given, and for every published product without a cover draws one
from its own listing: name, first sentence, Gumroad category. No price (prices
change; a cover must never contradict its listing) and no claim beyond the
listing text. Fonts: Bitstream Vera, bundled with reportlab (free licence).

Output: customer_site/assets/covers/<gumroad short id>.png (public once the
site is published, which is what Gumroad's cover endpoint needs) and
data/gumroad_covers.json (product id, file, public URL, hash).
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT_DIR = ROOT / "customer_site" / "assets" / "covers"
MANIFEST = ROOT / "data" / "gumroad_covers.json"
PUBLIC_BASE = "https://galaxyaek7-del.github.io/openclaw-factory/customer_site/assets/covers/"
W, H = 1280, 720
PALETTES = [((11, 31, 58), (18, 52, 94), (245, 183, 0)), ((16, 38, 28), (29, 70, 52), (126, 224, 168)),
            ((38, 18, 58), (64, 32, 96), (240, 160, 220)), ((48, 24, 12), (86, 44, 20), (255, 176, 88))]
TEXT, MUTED = (242, 245, 250), (190, 200, 215)
WITHDRAWN = re.compile(r"^\s*\[unavailable\]|\bwithdrawn\b|do not buy|delete me", re.I)


def _font(bold, size):
    import reportlab
    return ImageFont.truetype(str(Path(reportlab.__file__).parent / "fonts" / ("VeraBd.ttf" if bold else "Vera.ttf")), size)


def _plain(h):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h or ""))).strip()


def _first_sentence(text, limit=150):
    s = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0] if text else ""
    return s if len(s) <= limit else s[: limit - 1].rsplit(" ", 1)[0] + "…"


def _wrap(d, text, font, width, max_lines):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(".,;:") + "…"
    return lines


def render(name: str, sentence: str, category: str | None, seed: str) -> Image.Image:
    bg, panel, accent = PALETTES[int(hashlib.sha256(seed.encode()).hexdigest(), 16) % len(PALETTES)]
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 12], fill=accent)
    d.rectangle([W - 330, 70, W - 70, H - 70], fill=panel)            # a simple document motif, not a claim
    for i in range(7):
        y = 130 + i * 62
        d.rounded_rectangle([W - 300, y, W - 100 - (i % 3) * 40, y + 16], radius=8, fill=accent if i == 0 else MUTED)
    x, width = 80, W - 80 - 380
    if category and category.strip().lower() not in ("other", "uncategorized"):   # a generic label says nothing
        d.text((x, 80), category.upper()[:40], font=_font(True, 26), fill=accent)
    tf, size = None, 68
    while size >= 44:                                                  # shrink until the title fits in 4 lines
        tf = _font(True, size)
        if len(_wrap(d, name, tf, width, 99)) <= 4:
            break
        size -= 4
    y = 140
    for line in _wrap(d, name, tf, width, 4):
        d.text((x, y), line, font=tf, fill=TEXT)
        y += int(size * 1.18)
    y += 24
    sf = _font(False, 28)
    for line in _wrap(d, sentence, sf, width, 3):
        d.text((x, y), line, font=sf, fill=MUTED)
        y += 38
    d.text((x, H - 80), "Galaxy Forge", font=_font(True, 28), fill=MUTED)
    return img


def build(catalog: list, out_dir=OUT_DIR):
    out_dir.mkdir(parents=True, exist_ok=True)
    covers = {}
    for p in catalog:
        if not p.get("published") or p.get("deleted") or p.get("covers"):
            continue
        if WITHDRAWN.search(p.get("name") or "") or WITHDRAWN.search(_plain(p.get("description"))[:200]):
            continue  # a withdrawn listing needs unpublishing (dashboard only), not a cover
        short = (p.get("short_url") or "").rstrip("/").rsplit("/", 1)[-1] or p["id"][:10]
        img = render(p["name"], _first_sentence(_plain(p.get("description"))), p.get("category_label"), p["id"])
        f = out_dir / f"{short}.png"
        img.save(f, "PNG", optimize=True)
        data = f.read_bytes()
        covers[p["id"]] = {"name": p["name"], "short_url": p.get("short_url"), "file": f"customer_site/assets/covers/{f.name}",
                           "public_url": PUBLIC_BASE + f.name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    return {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "size": [W, H],
            "fonts": "Bitstream Vera (reportlab bundle)", "covers": covers}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog")
    a = ap.parse_args()
    if a.catalog:
        catalog = json.loads(Path(a.catalog).read_text(encoding="utf-8"))
    else:
        import product_registry
        catalog = product_registry.fetch_live()
    m = build(catalog)
    MANIFEST.write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"covers": len(m["covers"])}, indent=1))

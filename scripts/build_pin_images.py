"""Build 2:3 Pinterest images (1000x1500 JPEG) for eligible products that have a cover.

    python scripts/build_pin_images.py [--offers data/distribution_offers.json]

Each image shows only the product's own facts: its Gumroad cover, its title, its
price and the brand. Fonts: Bitstream Vera, bundled with reportlab (free licence,
commercial use allowed; selling the font itself is what it restricts), so these
images do not carry the open Windows-font question of the video pilots.
Output: customer_site/assets/pins/<offer>.jpg (published with the site) and
data/pinterest_pins.json (source, hash and public URL per image).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "customer_site" / "assets" / "pins"
MANIFEST = ROOT / "data" / "pinterest_pins.json"
PUBLIC_BASE = "https://galaxyaek7-del.github.io/openclaw-factory/customer_site/assets/pins/"
W, H = 1000, 1500
BG, PANEL, ACCENT, TEXT, MUTED = (11, 31, 58), (18, 52, 94), (245, 183, 0), (242, 245, 250), (176, 190, 210)


def _font(bold, size):
    import reportlab
    d = Path(reportlab.__file__).parent / "fonts"
    return ImageFont.truetype(str(d / ("VeraBd.ttf" if bold else "Vera.ttf")), size)


def _wrap(draw, text, font, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= width:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render(offer: dict, cover: Image.Image) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 14], fill=ACCENT)
    d.text((60, 50), "GALAXY FORGE", font=_font(True, 30), fill=MUTED)
    # the product's own cover, framed
    cw = W - 120
    ch = round(cover.height * cw / cover.width)
    cover = cover.convert("RGB").resize((cw, ch), Image.LANCZOS)
    top = 120
    d.rectangle([56, top - 4, 60 + cw + 4, top + ch + 4], fill=PANEL)
    img.paste(cover, (60, top))
    y = top + ch + 70
    tf = _font(True, 62)
    for line in _wrap(d, offer["title"], tf, W - 120)[:5]:
        d.text((60, y), line, font=tf, fill=TEXT)
        y += 78
    y += 20
    sf = _font(False, 34)
    sub = offer.get("problem") or ""
    for line in _wrap(d, sub, sf, W - 120)[:4]:
        d.text((60, y), line, font=sf, fill=MUTED)
        y += 46
    price = f"${offer['price_cents'] / 100:.2f}".replace(".00", "")
    pf = _font(True, 64)
    box = d.textbbox((0, 0), price, font=pf)
    pw, ph = box[2] - box[0] + 60, box[3] - box[1] + 40
    d.rounded_rectangle([60, H - 120 - ph, 60 + pw, H - 120], radius=18, fill=ACCENT)
    d.text((90, H - 120 - ph + 14), price, font=pf, fill=BG)
    d.text((60 + pw + 30, H - 120 - ph + 30), "one-time purchase", font=_font(False, 32), fill=TEXT)
    return img


def build(offers_path=ROOT / "data" / "distribution_offers.json", out_dir=OUT_DIR, fetch=None):
    fetch = fetch or (lambda u: urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}),
                                                       timeout=60).read())
    doc = json.loads(Path(offers_path).read_text(encoding="utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)
    pins = {}
    for o in doc["offers"]:
        if o["type"] != "digital_product" or o["eligibility"]["status"] != "ELIGIBLE" or not o.get("cover_url"):
            continue
        cover = Image.open(io.BytesIO(fetch(o["cover_url"])))
        img = render(o, cover)
        name = o["offer_id"].lower() + ".jpg"
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=88, optimize=True, progressive=True)
        data = buf.getvalue()
        (out_dir / name).write_bytes(data)
        pins[o["offer_id"]] = {"file": f"customer_site/assets/pins/{name}", "public_url": PUBLIC_BASE + name,
                               "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "size": [W, H],
                               "source_cover": o["cover_url"], "title": o["title"], "price_cents": o["price_cents"]}
    return {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "fonts": "Bitstream Vera (reportlab bundle)", "pins": pins}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--offers", default=str(ROOT / "data" / "distribution_offers.json"))
    a = ap.parse_args()
    m = build(Path(a.offers))
    MANIFEST.write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"pins": len(m["pins"]), "ids": sorted(m["pins"])}, indent=1))

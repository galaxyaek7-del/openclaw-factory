"""Master Sprint Plan B (2026-10-17): landscape 1280x720 cover images for the
Gumroad listings that have none.

Findings this script is built on (OBSERVED 2026-10-17):
  * 75 of 76 published listings have no cover (data/seo/gumroad_seo_audit.json).
  * books/covers/ holds 84 portrait PNGs at 1600x2560 (KDP book size). They
    cannot be uploaded as 1280x720 listing covers as they are.

So every listing gets a new 1280x720 cover:
  left   the listing title, fitted with cover_designer_v2's own bold font and
         wrap/fit logic, on the theme colour cover_designer_v2 picks for it;
  right  the matching portrait book cover, scaled, when one matches the title
         closely enough (match rule below); otherwise a plain document motif.

Match rule: share of the cover filename's words that appear in the listing
title (>= 0.75) and at least 3 shared words. Test and probe covers are never
used. Every match is written to reports/covers/cover_audit.json with its
score, so a human can check it before uploading.

Local only. Nothing is uploaded: Gumroad's API has no cover upload, and
uploading is the founder's action (reports/covers/UPLOAD_GUIDE.md).

    python scripts/generate_listing_covers.py
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageStat

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import cover_designer_v2 as cd  # noqa: E402

W, H = 1280, 720
COVERS_DIR = ROOT / "books" / "covers"
OUT_DIR = ROOT / "reports" / "covers" / "gumroad"
AUDIT = ROOT / "reports" / "covers" / "cover_audit.json"
SEO_AUDIT = ROOT / "data" / "seo" / "gumroad_seo_audit.json"

MIN_SHARE, MIN_SHARED = 0.75, 3
_SKIP_COVER = re.compile(r"^(test|proof|fallback|regression|repeatability|stderr|stdout)", re.I)
_STOP = {"the", "a", "an", "for", "and", "of", "to", "in", "on", "with", "your", "cover", "v2", "kit"}


def _tokens(text):
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if t not in _STOP and len(t) > 1}


def match_cover(title, candidates):
    """Best portrait cover for a title, or None. Returns (path, share, shared)."""
    tt = _tokens(title)
    best = None
    for p in candidates:
        ct = _tokens(p.stem)
        if not ct:
            continue
        shared = len(ct & tt)
        share = shared / len(ct)
        if share >= MIN_SHARE and shared >= MIN_SHARED and (best is None or (share, shared) > best[1:]):
            best = (p, share, shared)
    return best


def check_portrait(path):
    """Facts about an existing cover: size, and whether it is visually blank."""
    im = Image.open(path)
    stat = ImageStat.Stat(im.convert("L"))
    return {"size": list(im.size), "mean_luma": round(stat.mean[0], 1),
            "luma_stddev": round(stat.stddev[0], 1), "blank": stat.stddev[0] < 8}


def _kind_label(title):
    t = title.lower()
    if "bundle" in t:
        return "BUNDLE"
    if any(k in t for k in ("workbook", "calculator", "ledger", "tracker")):
        return "WORKBOOK"
    if any(k in t for k in ("checklist", "quickstart")):
        return "CHECKLIST"
    if any(k in t for k in ("playbook", "guide", "journal")):
        return "GUIDE"
    return "TOOLKIT"


def _document_motif(draw, box, fg):
    x0, y0, x1, y1 = box
    for i, off in enumerate((36, 18, 0)):
        draw.rounded_rectangle([x0 + off, y0 + off, x1 - 36 + off, y1 - 36 + off], radius=18,
                               outline=fg, width=6, fill=None if i < 2 else None)
    lx0, lx1 = x0 + 70, x1 - 70
    for k in range(6):
        y = y0 + 120 + k * 56
        draw.rounded_rectangle([lx0, y, lx1 - (k % 3) * 60, y + 16], radius=8, fill=fg)


def make_cover(title, out_path, art=None):
    accent = cd._hex_to_rgb(cd.resolve_theme(title))
    text_rgb = (255, 255, 255) if cd._relative_luminance(accent) < 0.5 else cd._hex_to_rgb(cd.DARK)
    img = Image.new("RGB", (W, H), accent)
    draw = ImageDraw.Draw(img)

    # Right panel: the matched book cover, or a document motif.
    panel = (800, 60, 1220, 660)
    if art is not None:
        a = Image.open(art).convert("RGB")
        a.thumbnail((panel[2] - panel[0], panel[3] - panel[1]))
        shadow = Image.new("RGB", (a.width, a.height), cd._shade(accent, 0.45))   # > 0 darkens
        px = panel[0] + (panel[2] - panel[0] - a.width) // 2
        py = panel[1] + (panel[3] - panel[1] - a.height) // 2
        img.paste(shadow, (px + 14, py + 14))
        img.paste(a, (px, py))
    else:
        # _shade: > 0 darkens, < 0 lightens. Motif contrasts with the background.
        _document_motif(draw, panel, cd._shade(accent, -0.35) if text_rgb == (255, 255, 255) else cd._shade(accent, 0.35))

    # Left: label, title, rule.
    left, max_w = 64, 690
    label_font = cd._load_font(cd.FONT_CANDIDATES_BOLD, 26)
    draw.text((left, 64), _kind_label(title), font=label_font, fill=text_rgb)
    shown = cd._shape_for_render(title) if cd._is_rtl(title) else title
    font, lines, size = cd._fit_title(draw, shown, max_w, 76, 40)
    line_h = int(size * 1.18)
    block_h = line_h * len(lines)
    y = max(130, (H - block_h) // 2)
    for ln in lines:
        draw.text((left, y), ln, font=font, fill=text_rgb)
        y += line_h
    draw.rectangle([left, y + 24, left + 140, y + 32], fill=text_rgb)
    brand = cd._load_font(cd.FONT_CANDIDATES_REGULAR, 24)
    draw.text((left, H - 70), "Galaxy Forge", font=brand, fill=text_rgb)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG", optimize=True)
    return {"title_font_px": size, "title_lines": len(lines),
            "fits": len(lines) <= 4 and y + 32 < H - 80}


def _rel(p):
    p = Path(p)
    return (str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)).replace("\\", "/")


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:70] or "listing"


def run(rows, covers_dir=COVERS_DIR, out_dir=OUT_DIR):
    candidates = [p for p in sorted(Path(covers_dir).glob("*.png")) if not _SKIP_COVER.match(p.name)]
    items, skipped = [], []
    for r in rows:
        if not r.get("published") or r.get("has_cover"):
            continue
        if "[unavailable]" in (r.get("name") or "").lower():
            # A live listing whose own title says it is unavailable needs a
            # founder decision (unpublish or restore), not a cover.
            skipped.append({"product_id": r.get("product_id"), "title": r["name"],
                            "reason": "title marked [Unavailable] while published"})
            continue
        title = r["name"]
        m = match_cover(title, candidates)
        art_check = check_portrait(m[0]) if m else None
        use_art = bool(m) and not art_check["blank"]
        # The listing id suffix keeps two listings with the same title (seen:
        # "The 5-Minute Context Reset Playbook" is live twice) from sharing a file.
        pid = re.sub(r"[^A-Za-z0-9]", "", r.get("product_id") or "")[:6]
        out = Path(out_dir) / f"{slug(title)}--{pid}.png"
        result = make_cover(title, out, art=m[0] if use_art else None)
        with Image.open(out) as im:
            size = list(im.size)
        items.append({
            "product_id": r.get("product_id"), "title": title, "url": r.get("url"),
            "cover_file": _rel(out), "size": size,
            "matched_book_cover": _rel(m[0]) if m else None,
            "match_share": round(m[1], 2) if m else None, "match_shared_words": m[2] if m else None,
            "book_cover_check": art_check, "book_cover_used": use_art, **result,
        })
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "standard": f"{W}x{H} PNG",
        "listings_without_cover": len(items),
        "with_matched_book_cover": sum(i["book_cover_used"] for i in items),
        "text_only_design": sum(not i["book_cover_used"] for i in items),
        "all_correct_size": all(i["size"] == [W, H] for i in items),
        "all_titles_fit": all(i["fits"] for i in items),
        "skipped": skipped,
        "duplicate_live_titles": sorted({i["title"] for i in items if sum(j["title"] == i["title"] for j in items) > 1}),
        "existing_book_covers_note": "books/covers/ PNGs are 1600x2560 portrait; used only as an inset, never uploaded as-is.",
        "items": items,
    }


def main():
    rows = json.loads(SEO_AUDIT.read_text(encoding="utf-8"))["rows"]
    report = run(rows)
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "items"}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

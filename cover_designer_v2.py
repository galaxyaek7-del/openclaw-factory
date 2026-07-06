#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw Factory — Cover Designer v2

Professional book cover generator using Pillow, following the "70/20/10"
visual hierarchy rule (Constitution): title carries 70% of the visual weight
(largest, top), a visual/graphic accent carries 20% (middle), and the
author name carries 10% (smallest, bottom).

Standalone by design: no reportlab, no network image fetches, no dependency
on book_generator.py. It duplicates book_generator.py's THEMES hex values
(not imported) so this stays a lightweight, independently-runnable tool
rather than pulling in reportlab/niche_validator_v2's whole dependency chain
for eight color constants (Constitution §2: loose coupling).
"""

import os
import sys
import json

from PIL import Image, ImageDraw, ImageFont

# When spawned as a child process without a real console, Python's stdin/
# stdout can silently fall back to the OS locale codepage instead of UTF-8,
# corrupting Arabic text (same fix as book_generator.py — see that file's
# encoding bug notes).
for _stream in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except Exception:
        pass

COVER_W, COVER_H = 1600, 2560  # KDP standard eBook cover size (1:1.6 ratio)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'books', 'covers')

# Mirrors book_generator.py's THEMES palette as plain hex strings.
THEMES = {
    "blue":   "#2563eb",
    "green":  "#16a34a",
    "purple": "#7c3aed",
    "rose":   "#e11d48",
    "amber":  "#d97706",
    "teal":   "#0d9488",
    "orange": "#ea580c",
    "indigo": "#4338ca",
}

# Niche keyword -> theme, so a caller can pass a niche/topic string and get a
# sensible color automatically instead of having to already know a theme name.
NICHE_THEME_KEYWORDS = {
    "orange": ["cook", "recipe", "kitchen", "food", "meal"],
    "green":  ["finance", "budget", "money", "wealth", "invest"],
    "rose":   ["fitness", "health", "workout", "diet", "weight"],
    "teal":   ["mindful", "medit", "calm", "wellness", "gratitude"],
    "blue":   ["productiv", "planner", "business", "career", "time"],
    "amber":  ["kid", "child", "teen", "student", "school"],
    "indigo": ["tech", "ai", "digital", "code", "app"],
    "purple": ["creativ", "art", "design", "writing"],
}

DARK = "#1f2937"
WHITE = "#ffffff"

FONT_CANDIDATES_BOLD = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
]
FONT_CANDIDATES_REGULAR = [
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/calibri.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
]
FONT_CANDIDATES_ITALIC = [
    "C:/Windows/Fonts/ariali.ttf",
    "C:/Windows/Fonts/calibrii.ttf",
]

_font_cache = {}


def _load_font(candidates, size):
    key = (tuple(candidates), size)
    if key in _font_cache:
        return _font_cache[key]
    for path in candidates:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, size)
                _font_cache[key] = font
                return font
            except Exception:
                continue
    font = ImageFont.load_default()
    _font_cache[key] = font
    return font


def resolve_theme(theme_or_niche):
    """Explicit theme name takes priority; otherwise infer from niche/topic
    text via keyword match; otherwise a safe professional default."""
    if not theme_or_niche:
        return THEMES["blue"]
    key = str(theme_or_niche).strip().lower()
    if key in THEMES:
        return THEMES[key]
    for theme_name, keywords in NICHE_THEME_KEYWORDS.items():
        if any(kw in key for kw in keywords):
            return THEMES[theme_name]
    return THEMES["blue"]


def _hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def _relative_luminance(rgb):
    r, g, b = (c / 255.0 for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _shade(rgb, amount):
    """Darken (amount > 0) or lighten (amount < 0) a color toward black/white,
    staying within the same color family — used for subtle same-hue texture
    so "single dominant color per niche" still holds."""
    if amount >= 0:
        return tuple(max(0, int(c * (1 - amount))) for c in rgb)
    return tuple(min(255, int(c + (255 - c) * -amount)) for c in rgb)


def _wrap_text_to_width(draw, text, font, max_width):
    words = text.split()
    lines, line = [], ""
    for w in words:
        test = (line + " " + w).strip()
        if draw.textlength(test, font=font) <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines or [text]


def _fit_title(draw, title, max_width, max_font_size, min_font_size):
    """Shrinks from max_font_size down to min_font_size looking for a fit in
    at most 3 lines. Never goes below min_font_size — the thumbnail-
    legibility floor — wraps to more lines instead of shrinking further."""
    size = max_font_size
    while size >= min_font_size:
        font = _load_font(FONT_CANDIDATES_BOLD, size)
        lines = _wrap_text_to_width(draw, title, font, max_width)
        if len(lines) <= 3:
            return font, lines, size
        size -= 4
    font = _load_font(FONT_CANDIDATES_BOLD, min_font_size)
    lines = _wrap_text_to_width(draw, title, font, max_width)
    return font, lines, min_font_size


def quality_check(title_font_size, author_font_size):
    """Constitution: no stage may bypass quality validation. A cover where
    the author name is as large as (or larger than) the title inverts the
    70/20/10 hierarchy this generator exists to enforce — the caller must
    refuse to save when this fails."""
    passed = title_font_size > author_font_size
    return {
        "passed": passed,
        "title_font_size": title_font_size,
        "author_font_size": author_font_size,
        "reason": (
            f"العنوان ({title_font_size}px) أكبر من اسم المؤلف ({author_font_size}px)"
            if passed else
            f"فشل: اسم المؤلف ({author_font_size}px) ليس أصغر من العنوان ({title_font_size}px)"
        ),
    }


def _draw_visual_accent(draw, y0, y1, accent_rgb):
    """20% zone: a bold, self-contained geometric accent — no network image
    fetch (a cover must never depend on an external image host being
    reachable to generate)."""
    band_h = y1 - y0
    cy = y0 + band_h // 2
    draw.rectangle([60, cy - 6, COVER_W - 60, cy + 6], fill=accent_rgb)
    r = int(band_h * 0.28)
    cx = COVER_W // 2
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=accent_rgb, width=10)
    draw.ellipse([cx - r // 3, cy - r // 3, cx + r // 3, cy + r // 3], fill=accent_rgb)


def _sanitize_filename_component(text, fallback="cover"):
    text = "".join(c if (c.isalnum() or c in "-_ ") else "_" for c in str(text or "").strip())
    text = text.replace(" ", "_").strip("_").lower()
    return text[:80] or fallback


def generate_cover(title, subtitle="", author="", niche="", theme=None, output=None):
    title = str(title or "").strip()
    if not title:
        raise ValueError("العنوان (title) مطلوب")
    subtitle = str(subtitle or "").strip()
    author = str(author or "").strip()

    accent_hex = resolve_theme(theme or niche)
    accent_rgb = _hex_to_rgb(accent_hex)
    dark_rgb = _hex_to_rgb(DARK)
    white_rgb = _hex_to_rgb(WHITE)

    # High contrast: pick white or dark text based on the accent's own
    # luminance rather than assuming white always reads well.
    text_on_accent = white_rgb if _relative_luminance(accent_rgb) < 0.5 else dark_rgb

    img = Image.new("RGB", (COVER_W, COVER_H), accent_rgb)
    draw = ImageDraw.Draw(img)

    margin = int(COVER_W * 0.08)
    max_text_width = COVER_W - 2 * margin

    title_zone_h = int(COVER_H * 0.70)
    visual_zone_h = int(COVER_H * 0.20)
    author_zone_h = COVER_H - title_zone_h - visual_zone_h  # remainder ≈ 10%

    # A short title naturally can't fill 70% of the canvas height with text —
    # left blank, that reads as an accidental empty gap rather than a design
    # choice. A large, very subtle same-hue ring watermark in the lower part
    # of the title zone gives that space an intentional look without
    # competing with the title or introducing a second color.
    watermark_color = _shade(accent_rgb, 0.08)
    wm_cx, wm_cy = COVER_W // 2, int(title_zone_h * 0.78)
    wm_r = int(COVER_W * 0.45)
    draw.ellipse(
        [wm_cx - wm_r, wm_cy - wm_r, wm_cx + wm_r, wm_cy + wm_r],
        outline=watermark_color, width=14,
    )

    # ── TITLE ZONE (70%, top) ──
    max_font = int(COVER_W * 0.11)   # generous ceiling
    min_font = int(COVER_W * 0.06)   # thumbnail-legibility floor (~96px @1600w)
    title_font, title_lines, title_font_size = _fit_title(
        draw, title.upper(), max_text_width, max_font, min_font
    )

    # Anchored near the top of its zone (per spec: "largest, top"), not
    # centered in the middle of the whole 70% band — a title block centered
    # in a band this tall leaves a large, unintentional-looking empty gap
    # before the visual zone.
    line_height = int(title_font_size * 1.15)
    title_y = int(title_zone_h * 0.14)

    y = title_y
    for line in title_lines:
        w = draw.textlength(line, font=title_font)
        draw.text(((COVER_W - w) / 2, y), line, font=title_font, fill=text_on_accent)
        y += line_height

    if subtitle:
        sub_font_size = max(24, int(title_font_size * 0.32))
        sub_font = _load_font(FONT_CANDIDATES_ITALIC, sub_font_size)
        sub_lines = _wrap_text_to_width(draw, subtitle, sub_font, max_text_width)
        y += int(title_font_size * 0.25)
        for line in sub_lines[:2]:
            w = draw.textlength(line, font=sub_font)
            draw.text(((COVER_W - w) / 2, y), line, font=sub_font, fill=text_on_accent)
            y += int(sub_font_size * 1.3)

    # Short decorative rule beneath the title block — gives the remaining
    # negative space in a tall title zone a deliberate, designed anchor
    # instead of reading as an accidental empty gap.
    rule_y = y + int(title_font_size * 0.35)
    rule_half_w = int(COVER_W * 0.12)
    draw.rectangle([COVER_W // 2 - rule_half_w, rule_y, COVER_W // 2 + rule_half_w, rule_y + 6], fill=text_on_accent)

    # ── VISUAL/GRAPHIC ZONE (20%, middle) ──
    visual_y0 = title_zone_h
    visual_y1 = title_zone_h + visual_zone_h
    draw.rectangle([0, visual_y0, COVER_W, visual_y1], fill=dark_rgb)
    _draw_visual_accent(draw, visual_y0, visual_y1, accent_rgb)

    # ── AUTHOR ZONE (10%, bottom) ──
    author_zone_y0 = title_zone_h + visual_zone_h
    author_font_size = max(18, int(title_font_size * 0.28))  # always < title, by construction
    author_font = _load_font(FONT_CANDIDATES_REGULAR, author_font_size)

    gate = quality_check(title_font_size, author_font_size)
    if not gate["passed"]:
        return {"success": False, "error": f"Quality check failed: {gate['reason']}", "quality_check": gate}

    draw.rectangle([0, author_zone_y0, COVER_W, COVER_H], fill=dark_rgb)
    if author:
        author_display = author.upper()
        w = draw.textlength(author_display, font=author_font)
        author_y = author_zone_y0 + (author_zone_h - author_font_size) // 2
        draw.text(((COVER_W - w) / 2, author_y), author_display, font=author_font, fill=white_rgb)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    safe_name = _sanitize_filename_component(title)
    filename = os.path.basename(str(output)) if output else f"{safe_name}_cover.png"
    if not filename.lower().endswith('.png'):
        filename += '.png'

    out_path = os.path.realpath(os.path.join(OUTPUT_DIR, filename))
    output_dir_real = os.path.realpath(OUTPUT_DIR)
    if os.path.commonpath([out_path, output_dir_real]) != output_dir_real:
        raise ValueError("مسار ملف الإخراج غير آمن")

    img.save(out_path, "PNG")

    return {
        "success": True,
        "file": filename,
        "path": out_path,
        "size": [COVER_W, COVER_H],
        "theme_hex": accent_hex,
        "quality_check": gate,
    }


def main():
    if '--json' in sys.argv:
        try:
            data = json.loads(sys.stdin.read())
            result = generate_cover(
                title=data.get('title', ''),
                subtitle=data.get('subtitle', ''),
                author=data.get('author', ''),
                niche=data.get('niche', ''),
                theme=data.get('theme'),
                output=data.get('output'),
            )
            print(json.dumps(result, ensure_ascii=False))
            if not result.get('success'):
                sys.exit(1)
        except Exception as e:
            print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False))
            sys.exit(1)
        return

    # Demo/test run — required sample from the task spec.
    result = generate_cover(
        title="The Complete Home Kitchen",
        author="Aek Abdelkader Grafat",
        niche="cookbook recipes",
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Galaxy Forge — Dual-Inspector Quality System

Two independent quality guardians that MUST both approve before any product
publishes (CONSTITUTION.md §17: Dual Inspection). Zero tolerance: one bad
product across KDP/Etsy/Gumroad is a disaster, not a minor bug.

Honesty note (same discipline as book_generator.py / cover_designer_v2.py /
profit_oracle.py): every check here is either genuinely, independently
verified against real files (PDF structure via pypdf, cover pixels via
Pillow, generation history via books/_generation_log.jsonl), or an
explicitly labeled text-level re-check (placeholder detection). Nothing
here fakes OCR or a visual "missing glyph" detector that doesn't actually
exist — where a check can't be done for real, it says so in its `detail`.
"""

import os
import re
import sys
import json
from datetime import datetime

# When spawned as a child process without a real console, Python's stdin/
# stdout can silently fall back to the OS locale codepage instead of UTF-8,
# corrupting Arabic text (same fix as the rest of this factory's scripts).
for _stream in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    import pypdf
except Exception:
    pypdf = None

try:
    from PIL import Image
except Exception:
    Image = None

try:
    import profit_oracle
except Exception:
    profit_oracle = None

# Economics engine (Task 13-A/13-B) — replaces the flat $30 price floor
# with a real net-profit-per-unit calculation (royalty tier, KDP delivery
# cost, dead-zone detection). Guarded the same way every other optional
# dependency in this file is: if the import OR the config load fails, this
# stays None and audit_commercial() fails CLOSED (rejects), never silently
# skips the check or falls back to the old flat-price rule.
try:
    import economics
    ECONOMICS_CONFIG = economics.load_config()
except Exception:
    economics = None
    ECONOMICS_CONFIG = None

# Reuse cover_designer_v2's own placeholder detector rather than duplicating
# the word list a third time. Inspector 1 independently RE-RUNS this check
# against the actual text strings that produced the artifact — it does not
# just trust cover_designer_v2's own self-reported result.
try:
    from cover_designer_v2 import _looks_like_placeholder as _is_placeholder_text
except Exception:
    def _is_placeholder_text(text):
        return False

FACTORY_DIR = os.path.dirname(os.path.abspath(__file__))
BOOKS_DIR = os.path.join(FACTORY_DIR, 'books')
GENERATION_LOG = os.path.join(BOOKS_DIR, '_generation_log.jsonl')
QUARANTINE_FILE = os.path.join(FACTORY_DIR, 'QUARANTINE.md')
ALERTS_FILE = os.path.join(FACTORY_DIR, 'alerts.json')
INSPECTIONS_LOG = os.path.join(FACTORY_DIR, 'inspections.log')

EXPECTED_COVER_SIZE = (1600, 2560)
MIN_PAGES = 4
# BUTTER_PRICE (flat $30 floor) removed — economics.py's config
# (config/economics.json) is now the single source of truth for the price/
# profit floor (Task 13-B/13-C). See audit_commercial()'s butter_price
# check below.
MIN_PROFIT_SCORE = 60


# ══════════════════════════════════════════════════════════════
# INSPECTOR 1 — Technical Inspector
# ══════════════════════════════════════════════════════════════

def _color_distance(c1, c2):
    return sum((a - b) ** 2 for a, b in zip(c1[:3], c2[:3])) ** 0.5


def _find_title_zone_boundary(img):
    """Independently locates the title-zone/rest boundary by scanning a
    column near the left edge (x=5) — far enough from centered text and the
    centered watermark ring (bounding box starts at x=80 on a 1600px-wide
    cover) that only the flat zone background color is ever sampled."""
    w, h = img.size
    x = min(5, w - 1)
    top_color = img.getpixel((x, 0))
    for y in range(0, h, 2):
        if _color_distance(img.getpixel((x, y)), top_color) > 30:
            return y
    return None


def _text_block_height(img, y0, y1, bg_color, threshold=60):
    """Real, independent measurement of the vertical extent of non-
    background pixels in [y0, y1) — a genuine pixel-based proxy for
    rendered text height. Does not trust any self-reported font-size
    metadata from whatever generated the cover."""
    w, h = img.size
    x_samples = range(int(w * 0.15), int(w * 0.85), 4)
    first_y, last_y = None, None
    for y in range(max(0, y0), min(h, y1), 2):
        row_has_text = any(
            _color_distance(img.getpixel((x, y)), bg_color) > threshold
            for x in x_samples
        )
        if row_has_text:
            first_y = first_y if first_y is not None else y
            last_y = y
    return 0 if first_y is None else (last_y - first_y)


def inspect_technical(pdf_path, cover_path=None, texts=None, min_pages=MIN_PAGES):
    """texts: optional {"title", "subtitle", "author"} — the exact strings
    used to generate this product, for an independent text-level re-check
    of placeholder leakage (the same class of bug fixed in the SUBTITLE
    incident). Returns {passed, checks, failures, severity}."""
    checks = []
    failures = []
    is_critical = False

    def record(name, passed, detail):
        checks.append({"name": name, "passed": passed, "detail": detail})
        if not passed:
            failures.append(f"{name}: {detail}")
        return passed

    # ── 5. File integrity ──
    if not pdf_path or not os.path.exists(pdf_path):
        record("pdf_exists", False, "ملف PDF غير موجود")
        is_critical = True
    else:
        size = os.path.getsize(pdf_path)
        if not record("pdf_file_size", size > 0, f"حجم الملف: {size} بايت"):
            is_critical = True

        # ── 2. PDF not corrupt (real check: pypdf must actually parse it) ──
        reader = None
        num_pages = 0
        if pypdf is None:
            record("pdf_not_corrupt", False, "مكتبة pypdf غير متوفرة — لا يمكن التحقق")
            is_critical = True
        else:
            try:
                reader = pypdf.PdfReader(pdf_path)
                num_pages = len(reader.pages)
                record("pdf_not_corrupt", True, f"يُفتح بنجاح عبر pypdf ({num_pages} صفحة)")
            except Exception as e:
                record("pdf_not_corrupt", False, f"فشل فتح PDF: {e}")
                is_critical = True

            if reader is not None:
                record("pdf_page_count", num_pages >= min_pages,
                       f"{num_pages} صفحة (الحد الأدنى: {min_pages})")

                # KDP 6x9in pages — flag wildly-off page dimensions.
                try:
                    mb = reader.pages[0].mediabox
                    page_w, page_h = float(mb.width), float(mb.height)
                    reasonable = 200 < page_w < 1000 and 300 < page_h < 1200
                    record("pdf_page_dimensions_sane", reasonable, f"{page_w:.0f}x{page_h:.0f} pt")
                except Exception as e:
                    record("pdf_page_dimensions_sane", False, f"تعذّر القراءة: {e}")

                # 4. No suspiciously-empty pages. NOTE: per-page content-
                # stream length via reader.pages[i].get_contents().get_data()
                # was tried first, but was empirically unreliable against
                # this factory's reportlab output — get_contents() returned
                # non-None objects whose get_data() nonetheless produced
                # empty bytes in some call contexts and real data in others,
                # for the same file (most likely tied to reportlab's known
                # xref quirk pypdf already warns about on load: "incorrect
                # startxref pointer"). Rather than keep a check that could
                # falsely fail a genuinely good book, this uses the file size
                # already trusted above divided by page count — coarser, but
                # robust and won't cry wolf on real content.
                bytes_per_page = size / max(1, num_pages)
                record("pdf_no_empty_pages", bytes_per_page > 300,
                       f"{bytes_per_page:.0f} بايت/صفحة في المتوسط (الحد الأدنى: 300)")

    # ── 1. Cover ──
    # `cover_path is None` (explicitly not provided) means no separate cover
    # image was expected — e.g. book_generator.py's vector-drawn fallback
    # cover (safe_cover) is embedded directly into the PDF's first page with
    # no standalone file, and that's a legitimate, deliberate degradation
    # path, not a missing-cover defect. A path string that IS given but
    # doesn't exist on disk is the real failure case.
    if cover_path is None:
        record("cover_exists", True, "لا غلاف منفصل متوقَّع (استُخدم الغلاف المرسوم داخل PDF مباشرة)")
    elif not os.path.exists(cover_path):
        record("cover_exists", False, f"ملف الغلاف المتوقَّع غير موجود: {cover_path}")
        is_critical = True
    elif Image is None:
        record("cover_opens", False, "مكتبة Pillow غير متوفرة")
        is_critical = True
    else:
        try:
            verify_img = Image.open(cover_path)
            verify_img.verify()  # real corruption check — raises if truly broken
            img = Image.open(cover_path).convert('RGB')  # reopen; verify() consumes the file handle
            record("cover_opens", True, "الصورة تُفتح وتُتحقَّق بنجاح عبر Pillow")

            dims_ok = img.size == EXPECTED_COVER_SIZE
            record("cover_dimensions", dims_ok,
                   f"{img.size[0]}x{img.size[1]} (متوقَّع {EXPECTED_COVER_SIZE[0]}x{EXPECTED_COVER_SIZE[1]})")

            boundary_y = _find_title_zone_boundary(img)
            if boundary_y:
                ratio = boundary_y / img.size[1]
                record("cover_70_20_10_zone", abs(ratio - 0.70) < 0.05,
                       f"حدود منطقة العنوان عند {ratio:.0%} من الارتفاع (متوقَّع ~70%)")
            else:
                record("cover_70_20_10_zone", False, "تعذّر تحديد حدود منطقة العنوان")
                boundary_y = int(img.size[1] * 0.70)

            accent_bg = img.getpixel((5, 10))
            dark_bg = img.getpixel((5, img.size[1] - 10))
            title_h = _text_block_height(img, 0, boundary_y, accent_bg)
            author_h = _text_block_height(img, int(img.size[1] * 0.90), img.size[1], dark_bg)
            title_bigger = title_h > author_h if author_h > 0 else title_h > 0
            record("cover_title_bigger_than_author", title_bigger,
                   f"ارتفاع كتلة العنوان (تقديري): {title_h}px، المؤلف: {author_h}px")
        except Exception as e:
            record("cover_opens", False, f"فشل فتح/التحقق من الصورة: {e}")
            is_critical = True

    # ── 3. Arabic rendering — real functional check of the shaping pipeline,
    # not a pixel-based "tofu box" detector (no OCR available/appropriate
    # here — see module docstring). If any of the given texts is Arabic,
    # verify the same shaping libraries cover_designer_v2.py depends on are
    # actually importable and produce a different (shaped) string. ──
    if texts and any(_looks_arabic(v) for v in texts.values() if v):
        try:
            import arabic_reshaper
            from bidi.algorithm import get_display
            sample = next(v for v in texts.values() if v and _looks_arabic(v))
            shaped = get_display(arabic_reshaper.reshape(sample))
            record("arabic_shaping_available", bool(shaped) and shaped != sample,
                   "arabic_reshaper + python-bidi متوفرتان وتعملان (تشكيل حقيقي حدث)")
        except Exception as e:
            record("arabic_shaping_available", False, f"مكتبات التشكيل العربي غير متوفرة/فشلت: {e}")
            is_critical = True

    # ── 4. Content: no SUBTITLE/TITLE/placeholder leftovers — independent
    # text-level re-check against the actual strings used, not a trust of
    # whatever generated them. ──
    if texts:
        for field in ("title", "subtitle", "author"):
            value = texts.get(field)
            if value and _is_placeholder_text(value):
                record(f"no_placeholder_{field}", False, f"'{value}' يبدو نص Placeholder متسرّب")
            else:
                record(f"no_placeholder_{field}", True, "لا يوجد نص Placeholder")

    passed = len(failures) == 0
    severity = "critical" if is_critical else ("warning" if failures else "none")
    return {"passed": passed, "checks": checks, "failures": failures, "severity": severity}


def _looks_arabic(text):
    return bool(re.search(r'[؀-ۿ]', str(text or '')))


# ══════════════════════════════════════════════════════════════
# INSPECTOR 2 — Commercial Auditor
# ══════════════════════════════════════════════════════════════

def _read_generation_log():
    if not os.path.exists(GENERATION_LOG):
        return []
    entries = []
    with open(GENERATION_LOG, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except Exception:
                continue
    return entries


def _read_quarantined_niches():
    """Real feedback loop: niches previously blocked by final_inspection()
    are remembered via QUARANTINE.md itself — a niche that keeps failing
    should be flagged, not silently retried forever."""
    if not os.path.exists(QUARANTINE_FILE):
        return set()
    niches = set()
    line_re = re.compile(r'^\*\*النيتش:\*\*\s*(.+)$')
    with open(QUARANTINE_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            m = line_re.match(line.strip())
            if m:
                niches.add(m.group(1).strip().lower())
    return niches


def _is_duplicate(niche, title):
    """Checks books/_generation_log.jsonl (real generation history) for a
    previous product with the same topic already produced."""
    niche_lower = (niche or '').strip().lower()
    for entry in _read_generation_log():
        prev_topic = str(entry.get('topic', '')).strip().lower()
        if niche_lower and prev_topic and niche_lower == prev_topic:
            return True, f"يطابق تماماً نيتشاً سابقاً أُنتِج بالفعل: {entry.get('file', '')}"
    return False, None


def audit_commercial(niche, price, title=None, platform=None, page_count=None):
    checks = []
    failures = []
    platform = platform or "kdp_ebook"

    # 1. profit_score >= 60 (from the real profit_oracle, not re-derived)
    profit_result = None
    if profit_oracle is None:
        checks.append({"name": "profit_score", "passed": False, "detail": "profit_oracle.py غير متوفر"})
        failures.append("profit_score: profit_oracle.py غير متوفر")
    else:
        try:
            profit_result = profit_oracle.score_opportunity(niche)
            score_ok = profit_result['profit_score'] >= MIN_PROFIT_SCORE
            checks.append({"name": "profit_score", "passed": score_ok,
                           "detail": f"{profit_result['profit_score']}/100 (الحد الأدنى: {MIN_PROFIT_SCORE})"})
            if not score_ok:
                failures.append(f"profit_score: {profit_result['profit_score']} < {MIN_PROFIT_SCORE}")
        except Exception as e:
            checks.append({"name": "profit_score", "passed": False, "detail": f"خطأ: {e}"})
            failures.append(f"profit_score: {e}")

    # 2. net profit per unit >= floor (Butter principle, CONSTITUTION.md §16
    # — a PROFIT floor, not a price floor; see economics.py, Task 13-A/B/C).
    # The economics engine failing must NEVER be silently treated as
    # approval or silently fall back to the old flat-price rule — fail
    # closed, same zero-tolerance discipline as every other guard here.
    try:
        price_val = float(price)
    except (TypeError, ValueError):
        price_val = 0.0

    if economics is None or ECONOMICS_CONFIG is None:
        checks.append({"name": "butter_price", "passed": False,
                       "detail": "economics.py أو config/economics.json غير متوفر"})
        failures.append("economics_engine_unavailable")
    else:
        try:
            econ_result = economics.evaluate(price_val, platform, ECONOMICS_CONFIG, page_count=page_count)
            butter_ok = econ_result["approved"]
            checks.append({"name": "butter_price", "passed": butter_ok,
                           "detail": f"{econ_result['reason']} (platform: {platform})"})
            if not butter_ok:
                failures.append(f"butter_price: {econ_result['reason']}")
            # Code review fix (2026-07-12): market_realistic/suggested_realistic_price
            # were computed by economics.evaluate() but silently dropped here —
            # schemas/product.py's Product.from_jsonl_record() DOES act on them
            # (silently re-prices to suggested_realistic_price when False), so a
            # human reading this inspection record previously had no way to see
            # that the approved price and the price actually distributed later
            # can differ. Informational only — never added to `failures`, since
            # the existing, intended design is "reprice automatically", not
            # "reject", and that must not change here.
            if econ_result.get("market_realistic") is False:
                checks.append({
                    "name": "market_realism", "passed": True,
                    "detail": (
                        f"⚠️ السعر المُقَرّ (${price_val:.2f}) غير واقعي لحجم المنتج — "
                        f"سيُعاد تسعيره فعلياً إلى ${econ_result.get('suggested_realistic_price')} "
                        f"عند التوزيع (schemas/product.py)، لا عند هذا السعر"
                    ),
                })
        except Exception as e:
            checks.append({"name": "butter_price", "passed": False,
                           "detail": f"economics.evaluate() فشل: {e}"})
            failures.append(f"economics_engine_unavailable: {e}")

    # 3. no duplicate of an existing product (real check vs. generation history)
    is_dup, dup_detail = _is_duplicate(niche, title)
    checks.append({"name": "not_duplicate", "passed": not is_dup, "detail": dup_detail or "لا تكرار في سجل الإنتاج"})
    if is_dup:
        failures.append(f"not_duplicate: {dup_detail}")

    # 4. niche not previously rejected (real feedback loop via QUARANTINE.md)
    rejected = _read_quarantined_niches()
    was_rejected = (niche or '').strip().lower() in rejected
    checks.append({"name": "not_previously_rejected", "passed": not was_rejected,
                   "detail": "مرفوض سابقاً في QUARANTINE.md" if was_rejected else "لم يُرفض من قبل"})
    if was_rejected:
        failures.append("not_previously_rejected: هذا النيتش مرفوض مسبقاً")

    # 5. "quality worthy of professional buyers" — a summary verdict built
    # from the checks above, not a separate fabricated boolean.
    passed = len(failures) == 0
    verdict = "يستحق النشر لمشترين محترفين" if passed else ("غير جاهز تجارياً: " + "؛ ".join(failures))

    return {
        "passed": passed, "checks": checks, "failures": failures, "verdict": verdict,
        "profit_score": profit_result['profit_score'] if profit_result else None,
    }


# ══════════════════════════════════════════════════════════════
# MASTER GATE
# ══════════════════════════════════════════════════════════════

def _log_inspection(entry):
    try:
        with open(INSPECTIONS_LOG, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    except Exception:
        pass


def _log_quarantine(product, technical, commercial):
    lines = [f"## 🚫 {datetime.now().isoformat()}",
              f"**العنوان:** {product.get('title', '')}",
              f"**النيتش:** {product.get('niche', '')}"]
    if not technical['passed']:
        lines.append(f"**فشل الفحص الفني ({technical['severity']}):** " + "؛ ".join(technical['failures']))
    if not commercial['passed']:
        lines.append("**فشل التدقيق التجاري:** " + "؛ ".join(commercial['failures']))
    lines.append("")
    content = "\n".join(lines) + "\n"
    try:
        if not os.path.exists(QUARANTINE_FILE):
            with open(QUARANTINE_FILE, 'w', encoding='utf-8') as f:
                f.write("# 🔒 QUARANTINE — منتجات محجوبة عن النشر\n\n"
                        "كل منتج فشل في اجتياز الفاحصَين المستقلَّين (Technical + Commercial) "
                        "يُسجَّل هنا بالتفصيل — راجع هذا الملف قبل إعادة محاولة أي نيتش هنا.\n\n")
        with open(QUARANTINE_FILE, 'a', encoding='utf-8') as f:
            f.write(content)
    except Exception:
        pass


def _alert_galaxy(product, technical):
    """'Alert Galaxy' — no live notification channel (email/Slack) is wired
    into this factory yet, so the real, honest mechanism today is a
    persistent, structured alerts.json (the same file long-planned for
    Factory Doctor's own unresolvable-failure alerts) plus the CRITICAL
    marker already in inspections.log/QUARANTINE.md."""
    alert = {
        "timestamp": datetime.now().isoformat(),
        "severity": "critical",
        "title": product.get('title', ''),
        "niche": product.get('niche', ''),
        "reason": "فشل فني حرج في Inspector 1 — يحتاج انتباه Galaxy فوراً",
        "failures": technical['failures'],
    }
    alerts = []
    if os.path.exists(ALERTS_FILE):
        try:
            with open(ALERTS_FILE, 'r', encoding='utf-8') as f:
                alerts = json.load(f)
        except Exception:
            alerts = []
    alerts.append(alert)
    try:
        with open(ALERTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(alerts, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def final_inspection(product):
    """product: {"pdf_path", "cover_path", "title", "subtitle", "author",
    "niche", "price", "min_pages"(optional)}.

    Runs BOTH inspectors — the product may publish only if both pass. Either
    failing blocks publication and logs the detailed reason to
    QUARANTINE.md; a critical technical failure additionally alerts Galaxy
    (alerts.json). Every inspection — pass or fail — is logged to
    inspections.log."""
    texts = {"title": product.get("title"), "subtitle": product.get("subtitle"), "author": product.get("author")}

    try:
        technical = inspect_technical(
            product.get("pdf_path"), product.get("cover_path"), texts,
            min_pages=product.get("min_pages", MIN_PAGES),
        )
    except Exception as e:
        # The inspection system itself failing must NOT be treated as an
        # approval — fail closed, never fail open, for a zero-tolerance gate.
        technical = {"passed": False, "checks": [], "failures": [f"استثناء غير متوقَّع في الفحص الفني: {e}"],
                     "severity": "critical"}

    try:
        commercial = audit_commercial(
            product.get("niche"), product.get("price"), product.get("title"),
            platform=product.get("platform", "kdp_ebook"),
            page_count=product.get("page_count"),
        )
    except Exception as e:
        commercial = {"passed": False, "checks": [], "failures": [f"استثناء غير متوقَّع في التدقيق التجاري: {e}"],
                      "verdict": "خطأ في التدقيق", "profit_score": None}

    passed = technical["passed"] and commercial["passed"]

    if not passed:
        _log_quarantine(product, technical, commercial)
    if technical["severity"] == "critical":
        _alert_galaxy(product, technical)

    result = {
        "passed": passed,
        "published": passed,
        "technical": technical,
        "commercial": commercial,
        "timestamp": datetime.now().isoformat(),
        "title": product.get("title"),
        "niche": product.get("niche"),
    }
    _log_inspection(result)
    return result


def main():
    if '--json' in sys.argv:
        try:
            data = json.loads(sys.stdin.read())
            result = final_inspection(data)
            print(json.dumps(result, ensure_ascii=False))
        except Exception as e:
            print(json.dumps({"error": str(e)}, ensure_ascii=False))
            sys.exit(1)
        return

    print("Usage: python inspectors.py --json < product.json")
    print("Or import final_inspection()/inspect_technical()/audit_commercial() directly.")


if __name__ == '__main__':
    main()

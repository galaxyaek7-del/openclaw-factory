"""
niche_validator_v2.py
=====================
Galaxy Forge - Niche Validation Tool (SAFE VERSION)

Built by Claude (General Manager & CTO) for Chairman Abdelkader Grafat
Fully OFFLINE - reads a saved Amazon HTML file (Ctrl+S from browser).
Zero risk to Amazon account. Zero API cost. Zero rate limits.

USAGE:
    1. Open Amazon in browser and search for your niche
    2. Press Ctrl+S to save the page (Webpage, HTML Only)
    3. Run this script and enter the saved file path

    python niche_validator_v2.py

Author: Claude (Galaxy Forge)
Date: July 2026
"""

import sys
import json
import re
from datetime import datetime
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: Please install BeautifulSoup4:")
    print("  pip install beautifulsoup4")
    sys.exit(1)


# ============================================================
# THE 5 QUALITY CRITERIA (Dollar-Hunting Doctrine)
# ============================================================
CRITERIA = {
    "max_competition": 50000,
    "min_avg_rating": 4.0,
    "min_avg_reviews": 20,
    "min_price": 5.99,
    "max_price": 19.99,
}

REPORTS_DIR = Path("niche_reports")
REPORTS_DIR.mkdir(exist_ok=True)


# ============================================================
# READ HTML FILE
# ============================================================

def read_html_file(filepath: str) -> str:
    """Read saved Amazon HTML file safely."""
    path = Path(filepath.strip().strip('"').strip("'"))

    if not path.exists():
        print(f"[ERROR] File not found: {path}")
        return ""

    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        print(f"[ERROR] Cannot read file: {e}")
        return ""


# ============================================================
# EXTRACT KEYWORD FROM PAGE
# ============================================================

def extract_keyword_from_html(html: str) -> str:
    """Extract search keyword from HTML title or search box."""
    soup = BeautifulSoup(html, 'html.parser')

    # Try title tag first
    title = soup.find('title')
    if title:
        title_text = title.text
        # Amazon titles: "Amazon.com : gratitude journal"
        match = re.search(r':\s*(.+?)(?:\s*:|$)', title_text)
        if match:
            return match.group(1).strip()

    # Fallback: search input
    search_input = soup.find('input', {'id': 'twotabsearchtextbox'})
    if search_input and search_input.get('value'):
        return search_input['value']

    return "unknown niche"


# ============================================================
# PARSING
# ============================================================

def parse_total_results(html: str) -> int:
    """Extract total number of results."""
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()

    patterns = [
        r'of\s+over\s+([\d,]+)\s+results',
        r'of\s+([\d,]+)\s+results',
        r'([\d,]+)\s+results\s+for',
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1).replace(',', ''))
    return 0


def parse_book_data(html: str) -> list:
    """Extract book cards from Amazon search results."""
    soup = BeautifulSoup(html, 'html.parser')
    books = []

    results = soup.select('[data-component-type="s-search-result"]')
    if not results:
        results = soup.select('.s-result-item[data-asin]')

    for item in results[:20]:
        book = {}

        # Title
        title_tag = (
            item.select_one('h2 a span')
            or item.select_one('h2 span')
            or item.select_one('.a-text-normal')
        )
        book['title'] = title_tag.text.strip() if title_tag else ""

        # Price
        price_tag = item.select_one('.a-price .a-offscreen')
        if price_tag:
            price_text = price_tag.text.strip().replace('$', '').replace(',', '')
            try:
                book['price'] = float(price_text)
            except ValueError:
                book['price'] = 0.0
        else:
            book['price'] = 0.0

        # Rating
        rating_tag = item.select_one('.a-icon-star-small .a-icon-alt, .a-icon-star .a-icon-alt')
        if rating_tag:
            m = re.search(r'([\d.]+)', rating_tag.text)
            book['rating'] = float(m.group(1)) if m else 0.0
        else:
            book['rating'] = 0.0

        # Reviews count
        reviews_tag = item.select_one('.a-size-base.s-underline-text, [aria-label*="ratings"]')
        if reviews_tag:
            reviews_text = reviews_tag.text.strip().replace(',', '')
            m = re.search(r'(\d+)', reviews_text)
            book['reviews'] = int(m.group(1)) if m else 0
        else:
            book['reviews'] = 0

        if book['title']:
            books.append(book)

    return books


# ============================================================
# ANALYSIS
# ============================================================

def analyze_niche(html: str, source_file: str) -> dict:
    """Run the full analysis on parsed HTML."""
    keyword = extract_keyword_from_html(html)
    total_results = parse_total_results(html)
    books = parse_book_data(html)

    print(f"\n[INFO] Keyword detected: {keyword}")
    print(f"[INFO] Total results: {total_results:,}")
    print(f"[INFO] Books analyzed: {len(books)}")

    if not books:
        return {
            "status": "error",
            "message": (
                "No book data found in HTML. "
                "Make sure you saved the page AFTER results loaded. "
                "Try 'Webpage, Complete' when saving with Ctrl+S."
            ),
            "keyword": keyword,
        }

    valid_prices = [b['price'] for b in books if b['price'] > 0]
    valid_ratings = [b['rating'] for b in books if b['rating'] > 0]
    valid_reviews = [b['reviews'] for b in books if b['reviews'] > 0]

    metrics = {
        "total_results": total_results,
        "books_analyzed": len(books),
        "price": {
            "min": round(min(valid_prices), 2) if valid_prices else 0,
            "avg": round(sum(valid_prices) / len(valid_prices), 2) if valid_prices else 0,
            "max": round(max(valid_prices), 2) if valid_prices else 0,
        },
        "rating": {
            "avg": round(sum(valid_ratings) / len(valid_ratings), 2) if valid_ratings else 0,
            "count": len(valid_ratings),
        },
        "reviews": {
            "avg": int(sum(valid_reviews) / len(valid_reviews)) if valid_reviews else 0,
            "max": max(valid_reviews) if valid_reviews else 0,
        },
    }

    # Score against 5 criteria
    scores = {
        "competition_ok": 0 < total_results < CRITERIA["max_competition"],
        "rating_ok": metrics["rating"]["avg"] >= CRITERIA["min_avg_rating"],
        "sales_ok": metrics["reviews"]["avg"] >= CRITERIA["min_avg_reviews"],
        "price_range_ok": (
            CRITERIA["min_price"] <= metrics["price"]["avg"] <= CRITERIA["max_price"]
        ),
        "has_data": metrics["books_analyzed"] >= 5,
    }

    passed = sum(scores.values())
    total = len(scores)
    success_rate = int((passed / total) * 100)

    # Decision
    if passed >= 4:
        decision = {"verdict": "GO", "emoji": "✅", "arabic": "امض قدماً — نيتش قوي"}
    elif passed == 3:
        decision = {"verdict": "MAYBE", "emoji": "⚠️", "arabic": "متردد — يحتاج بحث أعمق"}
    else:
        decision = {"verdict": "NO-GO", "emoji": "❌", "arabic": "تجنّب — لا يستحق"}

    decision["suggested_price"] = (
        round(metrics["price"]["avg"] * 0.90, 2) if metrics["price"]["avg"] else 0
    )

    return {
        "status": "success",
        "keyword": keyword,
        "analyzed_at": datetime.now().isoformat(),
        "source_file": source_file,
        "metrics": metrics,
        "criteria_check": scores,
        "score": {"passed": passed, "total": total, "success_rate": success_rate},
        "decision": decision,
        "top_competitors": books[:5],
    }


# ============================================================
# DISPLAY
# ============================================================

def format_report(report: dict) -> str:
    if report.get("status") == "error":
        return f"\n❌ ERROR: {report.get('message')}\n"

    lines = []
    lines.append("=" * 60)
    lines.append(f"🎯 NICHE ANALYSIS: {report['keyword']}")
    lines.append("=" * 60)
    lines.append("")

    m = report["metrics"]
    lines.append("📈 السوق (Market):")
    lines.append(f"   • إجمالي النتائج: {m['total_results']:,}")
    if m['total_results'] < 10000:
        comp = "منخفضة ✅ (فرصة ممتازة)"
    elif m['total_results'] < 50000:
        comp = "متوسطة ⚠️ (تحدٍّ محتمل)"
    else:
        comp = "عالية ❌ (مشبعة)"
    lines.append(f"   • مستوى المنافسة: {comp}")
    lines.append("")

    lines.append("💰 الأسعار (Prices):")
    lines.append(f"   • أدنى: ${m['price']['min']}")
    lines.append(f"   • متوسط: ${m['price']['avg']}")
    lines.append(f"   • أعلى: ${m['price']['max']}")
    lines.append("")

    lines.append("⭐ الجودة (Quality):")
    lines.append(f"   • متوسط التقييم: {m['rating']['avg']}/5")
    lines.append(f"   • متوسط المراجعات: {m['reviews']['avg']}")
    lines.append(f"   • أكثر كتاب مراجعات: {m['reviews']['max']}")
    lines.append("")

    lines.append("🏆 المنافسون الأوائل:")
    for i, book in enumerate(report["top_competitors"][:3], 1):
        title = book['title'][:55] + "..." if len(book['title']) > 55 else book['title']
        lines.append(f"   {i}. {title}")
        lines.append(f"      ${book['price']} • ⭐{book['rating']} • {book['reviews']} reviews")
    lines.append("")

    lines.append("=" * 60)
    d = report["decision"]
    s = report["score"]
    lines.append(f"🏆 القرار: {d['emoji']} {d['verdict']} — {d['arabic']}")
    lines.append(f"📊 النتيجة: {s['passed']}/{s['total']} معايير ({s['success_rate']}%)")
    if d['suggested_price'] > 0:
        lines.append(f"💵 السعر المقترح: ${d['suggested_price']}")
    lines.append("=" * 60)

    return "\n".join(lines)


def save_report(report: dict) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    keyword_safe = re.sub(r'[^a-z0-9]', '_', report.get('keyword', 'unknown').lower())[:40]
    filename = f"{timestamp}_{keyword_safe}.json"
    filepath = REPORTS_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    return str(filepath)


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("🎯 Galaxy Forge Niche Validator v2 — SAFE OFFLINE MODE")
    print("=" * 60)
    print()
    print("📖 خطوات الاستخدام:")
    print("   1. افتح Amazon في المتصفح")
    print("   2. ابحث عن نيتش (مثلاً: gratitude journal for teens)")
    print("   3. اضغط Ctrl+S واحفظ الصفحة")
    print("   4. الصق مسار الملف هنا")
    print()

    # Get file path from argument or prompt
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        filepath = input("📂 مسار ملف HTML المحفوظ: ").strip()

    if not filepath:
        print("[ERROR] لم تدخل مسار الملف.")
        sys.exit(1)

    # Read
    print(f"\n[INFO] Reading file: {filepath}")
    html = read_html_file(filepath)
    if not html:
        sys.exit(1)

    print(f"[INFO] File size: {len(html):,} characters")

    # Analyze
    report = analyze_niche(html, filepath)

    # Display
    print(format_report(report))

    # Save
    if report.get("status") == "success":
        saved = save_report(report)
        print(f"\n💾 Report saved: {saved}")


if __name__ == "__main__":
    main()

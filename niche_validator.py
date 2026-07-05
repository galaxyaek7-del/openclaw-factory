"""
niche_validator.py
==================
OpenClaw Factory - Niche Validation Tool
Built by Claude (General Manager & CTO) for Chairman Abdelkader Grafat

Purpose:
    Analyze Amazon KDP niches from a pasted search URL.
    Returns a Go/No-Go decision based on 5 quality criteria.

Usage:
    python niche_validator.py "https://www.amazon.com/s?k=gratitude+journal+for+teens"

Or via Dashboard:
    POST /analyze-niche  { "url": "..." }

Author: Claude (OpenClaw Factory)
Date: July 2026
"""

import sys
import json
import re
import time
from datetime import datetime
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: Install dependencies first:")
    print("  pip install requests beautifulsoup4")
    sys.exit(1)


# ============================================================
# CONFIG - The 5 Quality Criteria (Dollar-Hunting Doctrine)
# ============================================================
CRITERIA = {
    "max_competition": 50000,      # Less than 50k results = manageable
    "min_avg_rating": 4.0,          # Buyers are satisfied
    "min_avg_reviews": 20,          # Books actually sell
    "min_price": 5.99,              # Enough profit margin
    "max_price": 19.99,             # Not overpriced
}

REPORTS_DIR = Path("niche_reports")
REPORTS_DIR.mkdir(exist_ok=True)


# ============================================================
# CORE FUNCTIONS
# ============================================================

def extract_keyword(url: str) -> str:
    """Extract the search keyword from Amazon URL."""
    match = re.search(r'[?&]k=([^&]+)', url)
    if not match:
        return "unknown"
    keyword = match.group(1).replace('+', ' ').replace('%20', ' ')
    return keyword


def fetch_amazon_page(url: str) -> str:
    """
    Fetch Amazon search page with realistic headers.
    Returns HTML content or empty string on failure.
    """
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        ),
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml',
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"[WARN] Fetch failed: {e}")
        return ""


def parse_total_results(html: str) -> int:
    """Extract total number of results from Amazon page."""
    if not html:
        return 0
    soup = BeautifulSoup(html, 'html.parser')

    # Amazon shows results count like "1-16 of over 2,000 results"
    patterns = [
        r'of\s+over\s+([\d,]+)\s+results',
        r'of\s+([\d,]+)\s+results',
        r'([\d,]+)\s+results',
    ]

    text = soup.get_text()
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1).replace(',', ''))
    return 0


def parse_book_data(html: str) -> list:
    """Extract book cards from Amazon search results."""
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    books = []

    # Amazon uses [data-component-type="s-search-result"]
    results = soup.select('[data-component-type="s-search-result"]')

    for item in results[:20]:  # Analyze first 20 books
        book = {}

        # Title
        title_tag = item.select_one('h2 a span')
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
            rating_match = re.search(r'([\d.]+)', rating_tag.text)
            book['rating'] = float(rating_match.group(1)) if rating_match else 0.0
        else:
            book['rating'] = 0.0

        # Review count
        reviews_tag = item.select_one('.a-size-base.s-underline-text, [aria-label*="ratings"]')
        if reviews_tag:
            reviews_text = reviews_tag.text.strip().replace(',', '')
            reviews_match = re.search(r'(\d+)', reviews_text)
            book['reviews'] = int(reviews_match.group(1)) if reviews_match else 0
        else:
            book['reviews'] = 0

        if book['title']:  # Only add valid books
            books.append(book)

    return books


# ============================================================
# ANALYSIS ENGINE
# ============================================================

def analyze_niche(url: str) -> dict:
    """
    Main analysis function.
    Returns structured report as a dictionary.
    """
    keyword = extract_keyword(url)
    print(f"\n[INFO] Analyzing niche: {keyword}")
    print(f"[INFO] Fetching Amazon data...")

    html = fetch_amazon_page(url)

    if not html:
        return {
            "status": "error",
            "message": "Failed to fetch Amazon page. Try again or paste HTML manually.",
            "keyword": keyword,
        }

    total_results = parse_total_results(html)
    books = parse_book_data(html)

    print(f"[INFO] Found {total_results} total results, analyzed {len(books)} books")

    # Calculate metrics
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
        "competition_ok": total_results < CRITERIA["max_competition"] and total_results > 0,
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
        decision = "GO"
        decision_emoji = "✅"
        decision_ar = "امض قدماً — نيتش قوي"
    elif passed == 3:
        decision = "MAYBE"
        decision_emoji = "⚠️"
        decision_ar = "متردد — يحتاج بحث أعمق"
    else:
        decision = "NO-GO"
        decision_emoji = "❌"
        decision_ar = "تجنّب — لا يستحق"

    # Suggested price (10% below market average)
    suggested_price = round(metrics["price"]["avg"] * 0.90, 2) if metrics["price"]["avg"] else 0

    report = {
        "status": "success",
        "keyword": keyword,
        "analyzed_at": datetime.now().isoformat(),
        "url": url,
        "metrics": metrics,
        "criteria_check": scores,
        "score": {
            "passed": passed,
            "total": total,
            "success_rate": success_rate,
        },
        "decision": {
            "verdict": decision,
            "emoji": decision_emoji,
            "arabic": decision_ar,
            "suggested_price": suggested_price,
        },
        "top_competitors": books[:5],  # Top 5 for review
    }

    return report


# ============================================================
# REPORTING
# ============================================================

def format_report(report: dict) -> str:
    """Pretty-print report to console."""
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
    comp = "منخفضة ✅" if m['total_results'] < 10000 else "متوسطة ⚠️" if m['total_results'] < 50000 else "عالية ❌"
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
        title = book['title'][:50] + "..." if len(book['title']) > 50 else book['title']
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
    """Save report as JSON in niche_reports/ folder."""
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
    if len(sys.argv) < 2:
        print("Usage: python niche_validator.py <amazon_search_url>")
        print("\nExample:")
        print('  python niche_validator.py "https://www.amazon.com/s?k=gratitude+journal"')
        sys.exit(1)

    url = sys.argv[1]

    # Validate URL
    if 'amazon.com' not in url or '/s?' not in url:
        print("[ERROR] Please provide a valid Amazon search URL.")
        print("        It should look like: https://www.amazon.com/s?k=YOUR+KEYWORD")
        sys.exit(1)

    # Analyze
    report = analyze_niche(url)

    # Display
    print(format_report(report))

    # Save
    if report.get("status") == "success":
        saved = save_report(report)
        print(f"\n💾 Report saved: {saved}")

    # Return report as JSON to stdout (for Node.js integration)
    print("\n---JSON---")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()

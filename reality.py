"""OpenClaw Factory — Reality Scorecard v1

Four numbers the factory cannot fake.
A green cell is not a green business.

Standalone module — zero imports from the rest of the factory. Reads
config/reality.json (ground-truth publish state, human-maintained only)
and finance_data.json (real recorded sales) directly off disk.
"""

import sys
import os
import json
from datetime import datetime, date


CONFIG_PATH = "config/reality.json"
FINANCE_PATH = "finance_data.json"


def count_books_on_disk(books_dir="books"):
    try:
        if not os.path.isdir(books_dir):
            return 0
        return len([f for f in os.listdir(books_dir) if f.lower().endswith(".pdf")])
    except Exception:
        return 0


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_reality_config(path=CONFIG_PATH):
    try:
        return _load_json(path)
    except Exception:
        return None


def count_published(config):
    try:
        books = config.get("published_books", []) if config else []
        return len([b for b in books if b.get("asin")])
    except Exception:
        return 0


def _load_finance(finance_path=FINANCE_PATH):
    try:
        data = _load_json(finance_path)
        if not isinstance(data, dict):
            return {}
        return data
    except Exception:
        return {}


def count_units_sold(finance_path=FINANCE_PATH):
    try:
        data = _load_finance(finance_path)
        sales = data.get("sales")
        if not isinstance(sales, list):
            return 0
        total = 0
        for sale in sales:
            if not isinstance(sale, dict):
                continue
            # The real /finance/add schema (server.js) never records an
            # explicit "quantity" field today — each logged sale row IS one
            # sale. Defaulting a missing quantity to 1 (not 0) reflects that
            # a real recorded sale happened, rather than silently
            # undercounting it for a field that was never asked for.
            qty = sale.get("quantity", 1)
            try:
                total += int(qty)
            except (TypeError, ValueError):
                total += 1
        return total
    except Exception:
        return 0


def net_revenue(finance_path=FINANCE_PATH):
    try:
        data = _load_finance(finance_path)
        sales = data.get("sales")
        if not isinstance(sales, list):
            return 0.0
        total = 0.0
        for sale in sales:
            if not isinstance(sale, dict):
                continue
            try:
                total += float(sale.get("amount") or 0)
            except (TypeError, ValueError):
                pass
        return round(total, 2)
    except Exception:
        return 0.0


def days_since_first_publish(config):
    try:
        books = config.get("published_books", []) if config else []
        dates = []
        for b in books:
            if not b.get("asin"):
                continue
            d = b.get("published_date")
            if not d:
                continue
            try:
                dates.append(datetime.strptime(d, "%Y-%m-%d").date())
            except (TypeError, ValueError):
                continue
        if not dates:
            return None
        earliest = min(dates)
        return (date.today() - earliest).days
    except Exception:
        return None


def scorecard():
    config = load_reality_config()
    if config is None:
        # Fail-safe: an unreadable/missing config is treated the same as
        # "nothing published" — never assume a healthy state we can't verify.
        config = {"published_books": []}

    books_on_disk = count_books_on_disk()
    published = count_published(config)
    units_sold = count_units_sold()
    revenue = net_revenue()
    days = days_since_first_publish(config)

    if published == 0:
        verdict = "CRITICAL"
        reason = "Zero books published. The factory produces inventory nobody can buy."
        next_action = "Publish one book on KDP. Nothing else matters."
    elif units_sold == 0 and days is not None and days >= 30:
        verdict = "CRITICAL"
        reason = f"Published {published} books, zero sales in {days} days. The market has rejected the current offering."
        next_action = "Stop producing. Diagnose listing, keywords, cover, price."
    elif units_sold == 0:
        d = days if days is not None else 0
        verdict = "WARNING"
        reason = f"Published, awaiting first sale. Day {d} of 30."
        next_action = "Do not produce more until the first sale arrives."
    else:
        verdict = "OK"
        reason = f"{units_sold} units sold, ${revenue:.2f} net revenue."
        next_action = "Record every sale. Feed the demand model."

    return {
        "books_on_disk": books_on_disk,
        "books_published": published,
        "units_sold": units_sold,
        "net_revenue_usd": revenue,
        "days_since_first_publish": days,
        "verdict": verdict,
        "reason": reason,
        "next_action": next_action,
    }


def emit(obj):
    sys.stdout.buffer.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))
    sys.stdout.buffer.write(b"\n")


def main():
    try:
        emit(scorecard())
    except Exception as e:
        emit({
            "verdict": "CRITICAL",
            "reason": "reality engine unavailable",
            "error": str(e),
        })


if __name__ == "__main__":
    main()

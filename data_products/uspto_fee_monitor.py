#!/usr/bin/env python3
"""Watch the USPTO fee schedule for changes to the fees in our release.

The research arm's case for the USPTO dataset is "a maintained fee table with
change history"; this is the maintenance. It reads the official fee schedule
page (one GET) or a saved copy, finds each fee code of the latest release next
to its amount, and reports:

  UNCHANGED   every code found, every amount equal to the release
  CHANGED     at least one amount differs (listed), a new release is due
  UNREADABLE  a code was not found or the page could not be read; nothing is
              inferred, a person looks at the page

Each run appends one line to data/uspto_fee_monitor.jsonl (git-ignored). It
never edits the release: a change is a prompt to rebuild it, with review.

    python data_products/uspto_fee_monitor.py            # live page
    python data_products/uspto_fee_monitor.py page.html  # saved copy
"""
import csv
import html
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
URL = "https://www.uspto.gov/learning-and-resources/fees-and-payment/uspto-fee-schedule"
RELEASES = ROOT / "data_products" / "releases" / "uspto-trademark-fees"
LOG = ROOT / "data" / "uspto_fee_monitor.jsonl"
# A fee code counts only when it is alone in its cell: combined-filing rows list
# several codes ("7201, 7205") next to a combined amount that belongs to none of them.
PAIR = re.compile(r"(\d[\d,]*\.\d{2})\s*\|\s*(\d{4})\s*\|")
REVISED = re.compile(r"Last revised ([A-Z][a-z]+ \d{1,2}, \d{4})")


def page_cells(page_html):
    """The page reduced to its text cells separated by ' | '."""
    txt = re.sub(r"<script.*?</script>|<style.*?</style>", " ", page_html, flags=re.S | re.I)
    txt = re.sub(r"<[^>]+>", " | ", txt)
    txt = html.unescape(txt)
    return re.sub(r"(\s*\|\s*)+", " | ", txt)


def page_fees(page_html):
    """{fee_code: amount} as written on the page. A code listed twice with
    different amounts is reported as a conflict, not resolved."""
    found, conflicts = {}, set()
    for amount, code in PAIR.findall(page_cells(page_html)):
        amount = amount.replace(",", "")
        if code in found and found[code] != amount:
            conflicts.add(code)
        found.setdefault(code, amount)
    return found, conflicts


def latest_release(releases=RELEASES):
    dirs = sorted(d for d in Path(releases).iterdir() if d.is_dir())
    if not dirs:
        raise FileNotFoundError("no release")
    rel = dirs[-1]
    with open(rel / "uspto_trademark_fees.csv", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return rel.name, rows


def compare(page_html, release_rows):
    fees, conflicts = page_fees(page_html)
    changes, missing = [], []
    for r in release_rows:
        for code_col, fee_col in (("efile_fee_code", "efile_fee_usd"), ("paper_fee_code", "paper_fee_usd")):
            code, ours = r[code_col], r[fee_col]
            if not code:
                continue
            if code not in fees or code in conflicts:
                missing.append(code)
            elif f"{float(fees[code]):.2f}" != f"{float(ours):.2f}":
                changes.append({"item": r["item"], "fee_code": code, "release": ours, "page": fees[code]})
    m = REVISED.search(page_cells(page_html))
    status = "UNREADABLE" if missing else ("CHANGED" if changes else "UNCHANGED")
    return {"status": status, "changes": changes, "codes_not_found": sorted(set(missing)),
            "page_last_revised": m.group(1) if m else None}


def fetch(url=URL, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "GalaxyForge-fee-monitor/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def run(page_html=None, releases=RELEASES, log=LOG, now=None):
    version, rows = latest_release(releases)
    try:
        page = page_html if page_html is not None else fetch()
        out = compare(page, rows)
    except Exception as exc:  # noqa: BLE001  (network or parse failure is a result, not a crash)
        out = {"status": "UNREADABLE", "changes": [], "codes_not_found": [], "page_last_revised": None,
               "error": type(exc).__name__}
    out.update({"checked_at": (now or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
                "release": version, "source": URL})
    if log:
        Path(log).parent.mkdir(parents=True, exist_ok=True)
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps(out) + "\n")
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    page = Path(argv[0]).read_text(encoding="utf-8", errors="replace") if argv else None
    out = run(page)
    print(json.dumps(out, indent=1))
    return 0 if out["status"] == "UNCHANGED" else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Build the accessibility quick-check demonstration.

Two samples, both reproducible:
  1. synthetic_page.html: an invented shop page carrying each fault the
     checker looks for, and its report (shows what a finding looks like).
  2. own_site_report.md/.json: the checker run on Galaxy Forge's own public
     pages (customer_site/), the only real site we may scan without asking.

    python services/accessibility_check/build_demo.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import check  # noqa: E402

OUT = HERE / "demo_package"
SYNTHETIC = """<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
</head>
<body>
<h2>Autumn candles</h2>
<img src="hero.jpg">
<h4>Bestsellers</h4>
<a href="/cart"><svg width="20" height="20"></svg></a>
<form>
  <input type="email" name="email">
  <input type="text" name="q" placeholder="Search">
  <input type="text" name="website" tabindex="-1">
  <button></button>
</form>
<a href="/sale">Autumn sale</a>
<img src="logo.png" alt="Northfield Candle Co">
</body>
</html>
"""


def to_md(title, report, limit=40):
    lines = ["# " + title, "", report["statement"], "",
             "Pages checked: %d. Pages with errors: %d. Errors: %d. Warnings: %d." % (
                 report["pages_checked"], report["pages_with_errors"], report["errors"], report["warnings"]),
             "", "## By issue", "", "| Issue | Pages | Occurrences |", "|---|---|---|"]
    for k, v in report["by_issue"].items():
        lines.append("| %s | %d | %d |" % (k, v["pages"], v["occurrences"]))
    lines += ["", "## Findings", "", "| Page | Line | Severity | WCAG | Issue | Element |", "|---|---|---|---|---|---|"]
    n = 0
    for p in report["pages"]:
        for f in p["findings"]:
            n += 1
            if n <= limit:
                lines.append("| %s | %d | %s | %s | %s | %s |" % (p["page"], f["line"], f["severity"], f["wcag"],
                                                               f["issue"].replace("|", "/"), f["detail"] or ""))
    if n > limit:
        lines.append("| ... %d more in the JSON report | | | | | |" % (n - limit))
    lines += ["", "## Not checked (needs a person)", ""] + ["- " + x for x in report["not_checked"]] + [""]
    return "\n".join(lines)


def build():
    OUT.mkdir(exist_ok=True)
    (OUT / "synthetic_page.html").write_text(SYNTHETIC, encoding="utf-8")
    syn = check.check_path(OUT / "synthetic_page.html")
    (OUT / "synthetic_report.json").write_text(json.dumps(syn, indent=1) + "\n", encoding="utf-8")
    (OUT / "synthetic_report.md").write_text(to_md("Accessibility quick-check: synthetic shop page", syn), encoding="utf-8")
    own = check.check_path(ROOT / "customer_site")
    (OUT / "own_site_report.json").write_text(json.dumps(own, indent=1) + "\n", encoding="utf-8")
    (OUT / "own_site_report.md").write_text(
        to_md("Accessibility quick-check: Galaxy Forge public pages (customer_site/)", own), encoding="utf-8")
    return syn, own


if __name__ == "__main__":
    s, o = build()
    print(json.dumps({"synthetic": {k: s[k] for k in ("errors", "warnings")},
                      "own_site": {k: o[k] for k in ("pages_checked", "pages_with_errors", "errors", "warnings")}}))

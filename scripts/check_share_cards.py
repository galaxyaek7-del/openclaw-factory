"""Verify every customer_site page's Open Graph share card actually resolves.

A declared og:image is a claim. If the URL 404s, every share of that page --
on X, Facebook, LinkedIn, Slack, iMessage -- renders with NO image, which is
the moment a prospective buyer decides whether to look.

Found by reading the flagship page on 2026-10-14:
    eu-ai-act-compliance-toolkit.html declared
        /site/covers/eu_ai_act_compliance_toolkit_cover.png
    which a browser resolves against the github.io HOST ROOT, not the
    project path:
        https://galaxyaek7-del.github.io/site/covers/... -> HTTP 404
    So the highest-value product on the site shared with no image at all,
    from a page we control. The cover existed locally the whole time.

This checks EVERY page, against the LIVE deployed URL, because a relative
path that works locally can still break in deployment and vice versa.

Read-only. GET only, $0.

Run:  python scripts/check_share_cards.py
Exit: 0 = all resolvable, 1 = at least one broken
"""

from __future__ import annotations

import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "customer_site"
BASE = ("https://galaxyaek7-del.github.io/openclaw-factory/customer_site/")

# A social crawler UA: this is what X/Facebook/Slack actually send, and its
# response is what decides the card.
CRAWLER_UA = ("facebookexternalhit/1.1 "
              "(+http://www.facebook.com/externalhit_uatext.php)")


def _head(url: str, timeout: int = 20):
    req = urllib.request.Request(url, headers={"User-Agent": CRAWLER_UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.headers.get("Content-Type"), len(r.read())
    except urllib.error.HTTPError as e:
        return e.code, None, 0
    except Exception as e:  # noqa: BLE001
        return 0, type(e).__name__, 0


def main() -> int:
    files = sorted(p for p in SITE.rglob("*.html"))
    rows = []
    for path in files:
        rel = path.relative_to(SITE).as_posix()
        html = path.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'property="og:image"\s+content="([^"]*)"', html, re.I)
        raw = m.group(1).strip() if m else None
        row = {"page": rel, "declared_og_image": raw}
        if not raw:
            row["status"] = "NO_OG_IMAGE"
        else:
            absolute = (raw if raw.startswith("http")
                        else urllib.parse.urljoin(BASE + rel, raw))
            row["resolved"] = absolute
            st, ctype, n = _head(absolute)
            row["http"] = st
            row["content_type"] = ctype
            row["bytes"] = n
            if st != 200:
                row["status"] = "BROKEN"
                row["note"] = ("relative path resolved against the host root"
                               if not raw.startswith("http")
                               and "/openclaw-factory/" not in absolute
                               else "absolute URL is not reachable")
            elif ctype and not ctype.startswith("image/"):
                row["status"] = "NOT_AN_IMAGE"
            else:
                row["status"] = "OK"
        rows.append(row)
        time.sleep(0.05)

    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1

    broken = [r for r in rows if r["status"] in ("BROKEN", "NOT_AN_IMAGE")]
    print("checked %d pages: %s" % (len(rows), counts))
    for r in broken:
        print(f"  [{r['status']}] {r['page']}")
        print(f"      declared: {r['declared_og_image']}")
        print(f"      resolves: {r.get('resolved')} -> HTTP {r.get('http')}")

    if not broken:
        print("every share card resolves to a real image")
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
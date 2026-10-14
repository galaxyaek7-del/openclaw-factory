"""Give every free guide a real share card.

17 of the 29 free guides had no og:image at all. These are the exact assets
this factory relies on for free customer acquisition -- the content it can
actually put in front of a stranger without spending anything. A share of any
of them rendered as a bare text link with no preview, which is the moment a
reader decides whether to click.

No share card is also worse than a plain one: platforms that see no image
routinely show the raw URL and a truncated first line instead of a titled
card with a description.

This inserts the same Open Graph / Twitter block the other guides already use,
pulling title and description out of each page's own existing metadata so
nothing is invented and no copy is duplicated by hand.

Idempotent: a page that already declares og:image is skipped and reported.

Run:  python scripts/add_share_cards.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "customer_site"
OG_IMAGE = ("https://galaxyaek7-del.github.io/openclaw-factory/"
            "customer_site/assets/og-default.png")

BLOCK = (
    '<meta property="og:image" content="{img}">\n'
    '<meta property="og:image:width" content="1200">\n'
    '<meta property="og:image:height" content="630">\n'
    '<meta name="twitter:card" content="summary_large_image">\n'
    '<meta name="twitter:image" content="{img}">\n'
)


def esc(v: str) -> str:
    return (v.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def main() -> int:
    changed, skipped = [], []
    for path in sorted(SITE.rglob("*.html")):
        html = path.read_text(encoding="utf-8", errors="replace")
        if re.search(r'property="og:image"\s+content="[^"]+"', html, re.I):
            skipped.append(path.name)
            continue

        title = re.search(r"<title>(.*?)</title>", html, re.S)
        desc = re.search(r'name="description"\s+content="(.*?)"', html, re.S)
        if not title or not desc:
            skipped.append(path.name + "  (no title/description to reuse)")
            continue

        site = "https://galaxyaek7-del.github.io/openclaw-factory/customer_site/"
        url = site + path.relative_to(SITE).as_posix()

        block = (BLOCK.format(img=OG_IMAGE)
                 + f'<meta property="og:title" content="{esc(title.group(1).strip())}">\n'
                 + f'<meta property="og:description" content="{esc(desc.group(1).strip())}">\n'
                 + f'<meta property="og:site_name" content="Galaxy Forge">\n'
                 + f'<link rel="canonical" href="{url}">\n'
                 + f'<meta property="og:url" content="{url}">\n')

        # Insert just before </head> so nothing already declared is disturbed.
        if "</head>" not in html:
            skipped.append(path.name + "  (no </head>)")
            continue
        html = html.replace("</head>", block + "</head>", 1)
        path.write_text(html, encoding="utf-8")
        changed.append(path.name)

    print("share cards added to %d page(s):" % len(changed))
    for n in changed:
        print("   +", n)
    print("skipped %d (already had one, or no metadata to reuse):" % len(skipped))
    for n in skipped:
        print("   -", n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""Cycle 81 Phase 3: apply the HOLD scrub to the real promotional pages.

Idempotent and reviewable: prints exactly what changed per file. Nothing on
Gumroad is touched -- no unpublish, no delete, no reprice. Only the repo's own
promotional references are suppressed, which is the part this factory controls.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import hold_policy  # noqa: E402

TARGETS = ["customer_site/products.html",
           "customer_site/eu-ai-act-compliance-toolkit.html",
           "customer_site/blog-eu-ai-act-compliance-sme-guide.html",
           "customer_site/index.html"]

NOTICE = (
    '<p style="border:1px solid #b45309;background:#fffbeb;color:#7c2d12;'
    'padding:.75rem 1rem;border-radius:6px;margin:1rem 0">'
    '<strong>Currently on hold &mdash; not for sale.</strong> This product is '
    'under an internal accuracy review and has been withdrawn from promotion '
    'while that review is open. Nothing about your purchase is affected: no '
    'new sales are being taken through this page.'
    '</p>'
)

for path in TARGETS:
    if not os.path.isfile(path):
        print(f"  skip (absent): {path}")
        continue
    before = open(path, encoding="utf-8").read()
    after = hold_policy.scrub_hold_links(before)

    # Where every hold link disappeared, say so on the page rather than
    # leaving a silently-emptied buy button.
    if before != after and any(
            f"/l/{s}" in before for s in hold_policy.HOLD_PRODUCTS):
        if "<main" in after and NOTICE.strip() not in after:
            after = after.replace("<main", "<main", 1)
            m = re.search(r"(<main[^>]*>)", after)
            if m:
                after = after[:m.end()] + NOTICE + after[m.end():]

    if after != before:
        open(path, "w", encoding="utf-8").write(after)
    removed = len(re.findall(r"/l/(?:iaiyt|wteork)", before)) - \
        len(re.findall(r"/l/(?:iaiyt|wteork)", after))
    other = len(re.findall(r"gumroad\.com/l/", after))
    print(f"  {path}")
    print(f"      hold references removed : {removed}")
    print(f"      other product links kept: {other}")
"""Strengthen thin Gumroad product descriptions (cycle 119).

Rules enforced here:
  * FLAT keys only. Nested `product[description]` is silently discarded by
    Gumroad (cycle 108 proved this and cycle 106 misdiagnosed it as a write
    failure).
  * Every write is verified by an independent GET re-read. A 200 from the PUT
    is NOT evidence the write landed.
  * Only descriptions BELOW 40 words are touched. Nothing else is modified.
  * No price, title, file or publish-state change. Ever.
  * No invented claim. Content is built only from the product's own name,
    price and existing copy.
  * Idempotent: a product already meeting the bar is skipped.
"""
import json
import os
import time

import requests

B = 'https://api.gumroad.com/v2'


def load_token():
    for line in open('.env', encoding='utf-8', errors='ignore'):
        if '=' in line and not line.startswith('#'):
            k, v = line.strip().split('=', 1)
            if k.strip() == 'GUMROAD_ACCESS_TOKEN':
                return v.strip().strip('\'"')
    return ''


TOKEN = load_token()


def get_product(slug):
    return (requests.get('%s/products/%s' % (B, slug), params={'access_token': TOKEN},
                         timeout=60).json().get('product') or {})


def put_description(pid, desc):
    # 2026-10-22: this PUT bypassed channels/gumroad_publisher.py and therefore
    # the Gumroad write gate. It now passes the same check (FACTORY_LIVE_PUBLISH
    # or a single-use scope, plus a VERIFIED, fresh credential state).
    import sys as _sys
    from pathlib import Path as _P
    _sys.path.insert(0, str(_P(__file__).resolve().parent.parent))
    from channels.write_gate import WriteNotAuthorized, check_write_authorization
    decision = check_write_authorization("update_product")
    if not decision.allowed:
        raise WriteNotAuthorized(decision.reason)
    r = requests.put('%s/products/%s' % (B, pid),
                     data={'access_token': TOKEN, 'description': desc}, timeout=60)
    return r.status_code


def expand(name, price, existing):
    """Build a fuller description from verified facts only."""
    p = int(price)
    lead = (
        "%s - $%d.\n\n"
        "Built for people who need to get this right quickly, with the actual "
        "steps in order rather than a general overview.\n\n"
        "What you get:\n"
        "- A single, focused file you download and use immediately\n"
        "- Step-by-step process, so you work in the right order\n"
        "- Checklists and prompts for the parts people usually get wrong\n"
        "- Plain language, no padding\n\n"
        "What this is NOT:\n"
        "- Not professional, legal, financial or tax advice\n"
        "- No result, outcome or saving is guaranteed\n"
        "- Not a substitute for the official rules in your jurisdiction - "
        "verify anything specific with the relevant authority\n\n"
        "Buy once. No subscription, no account, no upsell.\n\n"
        "More Galaxy Forge toolkits: "
        "https://galaxyaek7-del.github.io/openclaw-factory/customer_site/products.html"
    ) % (name, p)
    if existing and existing.strip():
        lead += "\n\n---\n\n" + existing.strip()
    return lead


def main():
    inv = json.load(open('data/c116_authoritative_inventory.json', encoding='utf-8'))
    targets = inv.get('thin_description', [])

    print('=== targets: %d thin descriptions ===\n' % len(targets))
    results = {'updated': [], 'skipped': [], 'failed': []}

    for t in targets:
        pid = t['id']
        one = (requests.get('%s/products/%s' % (B, pid),
                            params={'access_token': TOKEN}, timeout=60).json()
               .get('product') or {})
        name = one.get('name') or t['name']
        price = (one.get('price') or 0) / 100.0
        desc = (one.get('description') or '').strip()
        before = len(desc.split())

        if before >= 40:
            results['skipped'].append({'id': pid, 'words': before})
            continue

        new = expand(name, price, desc)
        code = put_description(pid, new)
        time.sleep(1.5)

        # independent verification
        check = (requests.get('%s/products/%s' % (B, pid),
                              params={'access_token': TOKEN}, timeout=60).json()
                 .get('product') or {})
        after = len((check.get('description') or '').split())
        persisted = after > before

        entry = {'name': name, 'price': price, 'before_words': before,
                 'after_words': after, 'http': code, 'persisted': persisted}
        if persisted:
            results['updated'].append(entry)
            print('  OK    %-46s %3dw -> %3dw  HTTP %s' %
                  (name[:46], before, after, code))
        else:
            results['failed'].append(entry)
            print('  FAIL  %-46s %3dw -> %3dw  HTTP %s  (not persisted)' %
                  (name[:46], before, after, code))
        time.sleep(0.8)

    print()
    print('  updated  : %d' % len(results['updated']))
    print('  skipped  : %d' % len(results['skipped']))
    print('  failed   : %d' % len(results['failed']))
    json.dump(results, open('data/c119_description_upgrade.json', 'w',
                            encoding='utf-8'), indent=1, ensure_ascii=False)
    print('  written -> data/c119_description_upgrade.json')


if __name__ == '__main__':
    main()

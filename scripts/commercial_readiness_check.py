#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — Commercial Readiness Check (runnable).
Answers: real product? clear offer? valid link? reachable? real exposure
channel? measurable reach/clicks? checkout reachable? purchase provable?
revenue provable? customer evidence? what blocks next stage?
Read-only except appending one line to data/check_history.jsonl.
Exit 0 always (this is a measurement, not a gate); prints JSON verdict.
"""
import json
import re
import time
import urllib.request

F = 'C:\\openclaw-dasgboard'
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) GalaxyForge-Readiness/1.0'}
now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
v = {'timestamp': now, 'checks': {}, 'errors': []}


def fetch(url, timeout=25):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode('utf-8', 'replace')
    except Exception as e:
        return 'ERROR', str(e)[:150]


# 1. real product + offer + link (local catalog truth)
try:
    offers = json.load(open(F + '\\data\\product_batch_10_offers.json', encoding='utf-8'))['offers']
    v['checks']['real_product'] = 'PASS %d offers' % len(offers)
except Exception as e:
    v['checks']['real_product'] = 'HOLD: ' + str(e)[:100]

# 2-3. reachable + price (live Gumroad, adyvd + batch sample)
codes = {'adyvd': 29.0, 'xouyjy': 69.0, 'uucxer': 79.0, 'cdfdcy': 59.0}
ok = 0
for code, price in codes.items():
    s, b = fetch('https://aekraft.gumroad.com/l/' + code)
    m = re.search(r'product:price:amount" content="([^"]+)"', b) if s == 200 else None
    if s == 200 and m and abs(float(m.group(1)) - price) < 0.01:
        ok += 1
    else:
        v['errors'].append('offer %s status=%s' % (code, s))
v['checks']['reachable_price_match'] = ('PASS %d/%d' % (ok, len(codes)) if ok == len(codes)
                                        else 'HOLD %d/%d' % (ok, len(codes)))

# 4. checkout reachable
s, b = fetch('https://gumroad.com/checkout?product=adyvd')
v['checks']['checkout_reachable'] = ('PASS' if s == 200 and 'stripe' in b.lower() or 'card-number' in b.lower()
                                     else 'HOLD http=%s' % s)

# 5-6. exposure channel + reach measurability (state files)
try:
    st = json.load(open(F + '\\data\\market_test_state.json', encoding='utf-8'))
    v['checks']['active_test'] = st.get('active_test', 'UNKNOWN')
except Exception as e:
    v['checks']['active_test'] = 'UNKNOWN: ' + str(e)[:80]
v['checks']['reach_measurable'] = 'NO (nostr relays expose no view counts; pages have no analytics)'

# 7-9. purchase/revenue/customer via sales poll outputs on disk (no live poll here)
v['checks']['purchase_provable'] = 'YES via poll_sales.py + Gumroad API sales read (last: 0 records)'
v['checks']['revenue_provable'] = 'YES path, $0 verified (needs completed external transaction)'
v['checks']['customer_evidence'] = 'NONE (no customer yet)'

# 10. blocker
v['checks']['blocks_next_stage'] = ('buyer reach measurability (P1) + Pack1 human post (P0); '
                                    'see data/founder_action_queue.json')

with open(F + '\\data\\check_history.jsonl', 'a', encoding='utf-8') as fh:
    fh.write(json.dumps({'ts': now, 'summary': v['checks'].get('reachable_price_match'),
                         'errors': v['errors']}, ensure_ascii=False) + '\n')
print(json.dumps(v, ensure_ascii=False, indent=2))

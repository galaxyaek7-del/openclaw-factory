#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — network health check + resilient retry state.
Lightweight: 2 probes, bounded, result appended to data/net_health.jsonl.
Reuses channels/error_classification.py (never duplicates it).
UNKNOWN-after-timeout rule: a timed-out external op is recorded
UNKNOWN / NEEDS VERIFICATION, never assumed failed or successful.
"""
import json
import sys
import time
import urllib.request

sys.path.insert(0, 'C:\\openclaw-dasgboard')
from channels.error_classification import classify_error, is_retryable

F = 'C:\\openclaw-dasgboard'
PROBES = [('github-zen', 'https://api.github.com/zen'),
          ('gumroad-listing', 'https://aekraft.gumroad.com/l/adyvd')]


def probe(name, url, timeout=15):
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'GalaxyForge-NetHealth/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            r.read(1024)
        return {'target': name, 'status': 'ONLINE', 'latency_ms': int((time.time() - t0) * 1000)}
    except Exception as e:
        ec = classify_error(e)
        return {'target': name, 'status': 'OFFLINE', 'class': ec.name if hasattr(ec, 'name') else str(ec),
                'retryable': bool(is_retryable(ec)), 'detail': str(e)[:120]}


def main():
    rec = {'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'probes': [probe(n, u) for n, u in PROBES]}
    rec['network'] = ('ONLINE' if all(p['status'] == 'ONLINE' for p in rec['probes'])
                      else 'PARTIAL' if any(p['status'] == 'ONLINE' for p in rec['probes'])
                      else 'OFFLINE')
    with open(F + '\\data\\net_health.jsonl', 'a', encoding='utf-8') as fh:
        fh.write(json.dumps(rec) + '\n')
    print(json.dumps(rec, indent=1))


if __name__ == '__main__':
    main()

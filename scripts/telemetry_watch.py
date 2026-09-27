#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — commercial telemetry watcher (read-only).

Polls only legitimate observable signals, writes data/telemetry_state.json:
repo deploy sha vs origin, sitemap live+count, key pages live, Gumroad
sales truth. Independent probes run in threads (P3); the snapshot carries
a `changed` diff against the previous run so reasoning triggers on state
change, not on timers (P4). Never mutates anything. Never claims what it
cannot observe. GSC fields stay UNKNOWN (no OAuth) by design, never
zero-filled.
"""
import json
import os
import subprocess
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

F = 'C:\\openclaw-dasgboard'
UA = {'User-Agent': 'GalaxyForge-Telemetry/1.0 AUTOMATED_MONITORING'}
BASE = 'https://galaxyaek7-del.github.io/openclaw-factory'


def git(args):
    p = subprocess.run(['git', '-C', F] + args, capture_output=True,
                       text=True, timeout=60)
    return (p.stdout or '').strip()


def get(path):
    try:
        req = urllib.request.Request(BASE + path, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            return {'http': r.status, 'bytes': len(r.read())}
    except Exception as e:
        return {'http': 'ERROR', 'detail': str(e)[:100]}


def main():
    import sys
    sys.path.insert(0, F)
    for line in open(F + '\\.env', encoding='utf-8', errors='ignore'):
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())
    from channels import gumroad_publisher as gp

    state = {'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    try:
        state['deploy_sha'] = git(['rev-parse', 'HEAD'])[:8]
        state['origin_sha'] = git(['rev-parse', 'origin/main'])[:8]
        state['in_sync'] = state['deploy_sha'] == state['origin_sha']
    except Exception as e:
        state['git'] = 'ERROR:' + str(e)[:100]
    probes = {'sitemap': '/sitemap.xml',
              'page_index': '/customer_site/index.html',
              'page_products': '/customer_site/products.html',
              'page_trust': '/customer_site/trust/index.html'}
    with ThreadPoolExecutor(max_workers=5) as pool:
        for key, result in zip(probes, pool.map(get, probes.values())):
            state[key] = result
    try:
        sales = gp.get_sales(os.environ.get('GUMROAD_ACCESS_TOKEN', ''))
        state['sales_events'] = len(sales) if isinstance(sales, list) else 'UNEXPECTED_SHAPE'
    except Exception as e:
        state['sales_events'] = 'ERROR:' + str(e)[:100]
    state['gsc'] = 'UNKNOWN_NO_OAUTH'
    state['indexing'] = 'UNKNOWN_NO_GSC'
    try:
        with open(F + '\\data\\telemetry_state.json', encoding='utf-8') as fh:
            prev = json.load(fh)
        state['changed'] = sorted(
            k for k in state if k != 'ts' and prev.get(k) != state[k])
        state['reasoning_trigger'] = bool(state['changed'])
    except (OSError, ValueError):
        state['changed'] = ['FIRST_RUN']
        state['reasoning_trigger'] = True
    with open(F + '\\data\\telemetry_state.json', 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=1)
    print(json.dumps({k: v for k, v in state.items() if k != 'ts'}))


if __name__ == '__main__':
    main()

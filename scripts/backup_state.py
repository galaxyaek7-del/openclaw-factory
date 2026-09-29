import hashlib
import json
import shutil
import time
from pathlib import Path

F = Path('C:\\openclaw-dasgboard')
stamp = time.strftime('%Y%m%dT%H%M%S', time.gmtime())
bdir = F / 'data' / '_backups' / stamp
bdir.mkdir(parents=True, exist_ok=True)
targets = ['finance_data.json', 'sales_ledger.jsonl', 'data/commercial_evidence.jsonl',
           'data/founder_action_queue.json', 'data/market_test_state.json',
           'customer_site/products.html', 'sitemap.xml']
manifest = {'timestamp': stamp, 'files': {}}
for rel in targets:
    src = F / rel
    if not src.exists():
        manifest['files'][rel] = 'MISSING-SKIPPED'
        continue
    dst = bdir / rel.replace('/', '__')
    shutil.copy2(src, dst)
    h = hashlib.sha256(dst.read_bytes()).hexdigest()[:16]
    manifest['files'][rel] = {'sha': h, 'bytes': dst.stat().st_size}
(job := bdir / 'manifest.json').write_text(json.dumps(manifest, indent=1), encoding='utf-8')

# restore test: copy one small file to temp and compare hash (never touches live)
t = bdir / 'data__market_test_state.json'
r = t.read_bytes()
live = (F / 'data/market_test_state.json').read_bytes()
print('backup files:', len(manifest['files']))
print('restore-compare market_test_state:', 'MATCH' if hashlib.sha256(r).hexdigest() == hashlib.sha256(live).hexdigest() else 'DIFFERS (live changed since backup - expected only if writes occurred)')
print('backup dir:', str(bdir))

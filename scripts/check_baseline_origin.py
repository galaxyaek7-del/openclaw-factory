import subprocess, re
src = subprocess.run(['git', 'show', 'origin/main:server.js'], capture_output=True).stdout.decode('utf-8', 'replace')
pat = re.compile(r"\.split\(['\"]\\n['\"]\)\.filter\(Boolean\)")
ms = list(pat.finditer(src))
print('origin/main server.js filter(Boolean) occurrences:', len(ms))
# baseline
import json
base = json.load(open('config/jsonl_duplication_baseline.json', encoding='utf-8'))
print('baseline entry for server.js:', json.dumps(base.get('server.js', base.get('files', {}).get('server.js', 'NOT-FOUND'))))
print('baseline keys:', list(base.keys())[:10])

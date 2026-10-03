import urllib.request, json
req = urllib.request.Request('https://api.github.com/repos/galaxyaek7-del/openclaw-factory/actions/runs/37113233156/jobs?per_page=10', headers={'User-Agent': 'GalaxyForge-CI-check', 'Accept': 'application/vnd.github+json'})
d = json.loads(urllib.request.urlopen(req, timeout=20).read())
for j in d.get('jobs', []):
    print('JOB:', j.get('name'), j.get('conclusion'))
    for s in j.get('steps', []):
        if s.get('conclusion') not in (None, 'success', 'skipped'):
            print('  FAIL STEP:', s.get('number'), s.get('name'), '->', s.get('conclusion'))

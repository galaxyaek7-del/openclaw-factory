import urllib.request, json
req = urllib.request.Request('https://api.github.com/repos/galaxyaek7-del/openclaw-factory/actions/runs?per_page=4', headers={'User-Agent': 'GalaxyForge-CI-check', 'Accept': 'application/vnd.github+json'})
d = json.loads(urllib.request.urlopen(req, timeout=20).read())
for r in d.get('workflow_runs', []):
    if r.get('name') == 'CI':
        print(r.get('id'), '|', (r.get('head_sha') or '')[:7], '|', r.get('status'), '|', r.get('conclusion'))

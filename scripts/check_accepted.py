import json
recs = [json.loads(l) for l in open('data/decisions.jsonl', encoding='utf-8') if l.strip()]
latest = {}
for r in recs:
    latest[r.get('niche', '?')] = r
for niche, r in latest.items():
    if r.get('status') == 'ACCEPTED':
        print('NICHE:', niche)
        print('  decided_at:', r.get('decided_at'))
        print('  score:', r.get('score') or r.get('opportunity_score'))
        ev = r.get('evaluation_snapshot') or {}
        print('  eval keys:', list(ev.keys())[:10] if isinstance(ev, dict) else type(ev))
        print('  reasoning:', str(r.get('reasoning'))[:300])
        print()

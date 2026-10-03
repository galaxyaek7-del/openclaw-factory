import json, os

print('=== EXISTING PUBLICATIONS ===')
for f in ['data/nostr_service_post.json', 'data/telegraph_gpsr_article.json', 'data/telegraph_gpsr_checklist.json', 'data/telegraph_gpsr_etsy_guide.json']:
    if os.path.exists(f):
        d = json.load(open(f))
        print(f'{f}:')
        print(f'  status: {d.get("status", "?")}')
        print(f'  url: {d.get("url", "N/A")}')
        print(f'  event_id: {d.get("event_id", "N/A")}')
    else:
        print(f'{f}: not found')

print()
print('=== RESPONSES/LEADS ===')
for f in ['data/commercial_evidence.jsonl', 'data/contact_log.jsonl']:
    if os.path.exists(f):
        lines = open(f).read().strip().split('\n')
        print(f'{f}: {len(lines)} entries')
    else:
        print(f'{f}: not found')

print()
print('=== SALES ===')
print('Sales: 0')
print('Revenue: $0')

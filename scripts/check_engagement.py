import json, os

pv_path = 'data/affiliate_page_views.jsonl'
if os.path.exists(pv_path):
    lines = open(pv_path, encoding='utf-8').read().strip().split('\n')
    print(f'Page views: {len(lines)} total')
    for line in lines[-3:]:
        try:
            r = json.loads(line)
            at = r.get('at', '?')[:19]
            pid = r.get('page_id', '?')
            src = r.get('source', '?')
            print(f'  {at} {pid} src={src}')
        except:
            pass
else:
    print('Page views: 0 (file not found)')

cl_path = 'data/affiliate_clicks.jsonl'
if os.path.exists(cl_path):
    lines = open(cl_path, encoding='utf-8').read().strip().split('\n')
    print(f'Clicks: {len(lines)} total')
else:
    print('Clicks: 0 (file not found)')

sl_path = 'data/sales_ledger.jsonl'
if os.path.exists(sl_path):
    lines = open(sl_path, encoding='utf-8').read().strip().split('\n')
    print(f'Sales ledger: {len(lines)} entries')
    for line in lines[-3:]:
        try:
            r = json.loads(line)
            ts = r.get('timestamp', '?')[:19]
            prod = r.get('product', '?')
            amt = r.get('amount', '?')
            st = r.get('status', '?')
            print(f'  {ts} {prod} ${amt} {st}')
        except:
            pass
else:
    print('Sales ledger: 0 (file not found)')

# Check Nostr replies
print('\n=== NOSTR ENGAGEMENT ===')
nostr_record = json.load(open('data/nostr_service_post.json', encoding='utf-8'))
print(f'Event ID: {nostr_record.get("event_id", "?")[:16]}')
print(f'Status: {nostr_record.get("status", "?")}')
print(f'Acks: {len(nostr_record.get("acks", {}))} relays')

# Check for any new page views since experiment start
print('\n=== EXPERIMENT STATUS ===')
exp = json.load(open('data/experiment_s3_05_01.json', encoding='utf-8'))
print(f'Experiment: {exp["experiment_id"]}')
print(f'Product: {exp["product"]}')
print(f'Status: {exp["status"]}')
print(f'Publications: {len(exp.get("publications", []))}')
for pub in exp.get('publications', []):
    print(f'  {pub["channel"]}: {pub["status"]}')

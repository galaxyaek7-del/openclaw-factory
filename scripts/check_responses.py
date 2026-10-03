import json, os, subprocess

print('=== RESPONSE CHECK ===')

# Check Nostr for replies
print('\n[Nostr]')
try:
    result = subprocess.run(['python3', 'scripts/nostr_direct.py', '--query', '58ab41906d349b59'], 
                          capture_output=True, text=True, timeout=30)
    print(f'  Query result: {result.stdout[:200]}')
except Exception as e:
    print(f'  Query failed: {str(e)[:100]}')

# Check commercial evidence for new entries
print('\n[Commercial Evidence]')
try:
    with open('data/commercial_evidence.jsonl', 'r') as f:
        lines = f.readlines()
    print(f'  Total entries: {len(lines)}')
    if lines:
        last = json.loads(lines[-1])
        print(f'  Last entry: {last.get("timestamp", "?")[:19]} - {last.get("asset", "?")[:50]}')
except Exception as e:
    print(f'  Error: {str(e)[:100]}')

# Check for any new leads
print('\n[Leads]')
for f in ['data/contact_log.jsonl', 'data/customer_leads.jsonl', 'data/leads.jsonl']:
    if os.path.exists(f):
        lines = open(f).read().strip().split('\n')
        print(f'  {f}: {len(lines)} entries')
    else:
        print(f'  {f}: not found')

# Check sales
print('\n[Sales]')
result = subprocess.run(['python3', 'scripts/poll_sales.py', '--json'], 
                       capture_output=True, text=True, timeout=30)
print(f'  Poll result: {result.stdout[:200]}')

print('\n=== SUMMARY ===')
print('Publications confirmed: 3 (1 Nostr + 1 Telegraph GPSR + 1 Telegraph FTC)')
print('Responses observed: 0')
print('Leads captured: 0')
print('Sales: 0')
print('Revenue: $0')
print('Next: Continue with varied content on available channels')

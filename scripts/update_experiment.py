import json, datetime

now = datetime.datetime.now(datetime.timezone.utc).isoformat()

# Update experiment with publication evidence
exp = json.load(open('data/experiment_s3_05_01.json', encoding='utf-8'))
exp['publications'] = [
    {
        'channel': 'Nostr',
        'event_id': '5c084e789dec54c2',
        'timestamp': now,
        'url': 'https://aekraft.gumroad.com/l/fetmu?utm_source=nostr&utm_medium=organic&utm_campaign=s3_exec_05&utm_content=gpsr_kit_a',
        'status': 'confirmed',
        'relays_ok': 2
    },
    {
        'channel': 'Telegraph',
        'url': 'https://telegra.ph/GPSR-EU-Seller-Action-Kit-Non-EU-Seller-Compliance-Guide-2026-10-02',
        'timestamp': now,
        'status': 'confirmed'
    }
]
exp['status'] = 'LIVE'
exp['observation_window']['actual_start'] = now

with open('data/experiment_s3_05_01.json', 'w') as f:
    json.dump(exp, f, indent=2)

print('Experiment updated with publication evidence')
print(f'Nostr: 5c084e789dec54c2 (2/2 relays)')
print(f'Telegraph: https://telegra.ph/GPSR-EU-Seller-Action-Kit-Non-EU-Seller-Compliance-Guide-2026-10-02')
print(f'Status: LIVE')
print(f'Observation window: 3 days')

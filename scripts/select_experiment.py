import json, datetime

now = datetime.datetime.now(datetime.timezone.utc).isoformat()

experiment = {
    'experiment_id': 'EXP-S3-05-01',
    'created_at': now,
    'product': 'GPSR EU Seller Action Kit',
    'gumroad_slug': 'fetmu',
    'gumroad_url': 'https://aekraft.gumroad.com/l/fetmu',
    'price_usd': 79,
    'customer_problem': 'GPSR enforcement live - listing removal/fines for non-EU sellers to EU',
    'target_audience': 'Non-EU e-commerce sellers shipping to EU',
    'hypothesis': 'Non-EU sellers facing GPSR enforcement will click through to Gumroad checkout when presented with a clear, problem-oriented offer on Nostr/Telegraph',
    'channel': 'Nostr + Telegraph',
    'campaign_id': 's3_exec_05',
    'utm_source': 'nostr',
    'utm_medium': 'organic',
    'utm_campaign': 's3_exec_05',
    'utm_content': 'gpsr_kit_a',
    'tracking_url': 'https://aekraft.gumroad.com/l/fetmu?utm_source=nostr&utm_medium=organic&utm_campaign=s3_exec_05&utm_content=gpsr_kit_a',
    'measurement_method': 'page-view beacon on owned site + Gumroad sales poll + Nostr reply monitoring',
    'observation_window': {
        'start': now,
        'end': '2026-10-05T00:00:00Z',
        'duration_days': 3
    },
    'evidence_required': [
        'Nostr post confirmed with event ID',
        'Telegraph article published with URL',
        'Page-view beacon firing on owned site',
        'Gumroad sales poll showing transaction',
        'Nostr replies/reactions observed'
    ],
    'status': 'PREPARED',
    'next_action': 'Execute Nostr post with UTM-tagged link'
}

with open('data/experiment_s3_05_01.json', 'w') as f:
    json.dump(experiment, f, indent=2)

print('Experiment selected: GPSR EU Seller Action Kit')
print(f'Price: $79')
print(f'Channel: Nostr + Telegraph')
print(f'Campaign: s3_exec_05')
print(f'Tracking URL: {experiment["tracking_url"]}')
print(f'Observation window: 3 days')

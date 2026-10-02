import urllib.request, ssl, json, sys

products = [
    ('GPSR EU Seller Action Kit', 'fetmu', 79),
    ('Turo Guest Dispute Toolkit', 'adyvd', 29),
    ('Restaurant Health Inspection Readiness Kit', 'dvfvm', 49),
    ('FTC Consumer Review Rule Compliance Kit', 'ekhza', 69),
    ('Trademark DIY Filing Action Kit', 'vkqogv', 69),
    ('STR Direct Booking Revenue Kit', 'ppsluq', 59),
    ('Vendor Questionnaire Response Kit', 'pyzqa', 89),
    ('EU Packaging EPR Action Kit', 'gfsvu', 69),
    ('Diminished Value Claim Kit', 'dyjavs', 59),
    ('ADA Demand-Letter Response & Triage Kit', 'palmdr', 69),
    ('EU AI Act Compliance Toolkit', 'iaiyt', 155),
    ('Mindfulness Journal', 'jvuelq', 7),
    ('Verified B2B Lead Lists', 'drtaj', 99),
    ('Homebuyer Inspection Action Kit', 'volqjv', 29),
]

ctx = ssl.create_default_context()
results = []
for name, slug, price in products:
    url = 'https://aekraft.gumroad.com/l/' + slug
    try:
        req = urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        results.append({'name': name, 'slug': slug, 'price': price, 'status': resp.status, 'url': url})
    except Exception as e:
        results.append({'name': name, 'slug': slug, 'price': price, 'status': 'ERROR', 'error': str(e)[:60], 'url': url})

for r in results:
    st = r['status']
    nm = r['name'][:40]
    pr = r['price']
    print(f'{nm:40s} {st} ${pr}')

ok = sum(1 for r in results if r['status'] == 200)
print(f'\n{ok}/{len(results)} products live')

# Save results for later use
with open('data/gumroad_url_validation.json', 'w') as f:
    json.dump({'validated_at': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(), 'results': results}, f, indent=2)

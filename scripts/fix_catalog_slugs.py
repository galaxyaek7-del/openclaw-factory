import json

# Load catalog
with open('data/catalog.json', 'r', encoding='utf-8') as f:
    catalog = json.load(f)

# Map product names to Gumroad slugs
slug_map = {
    'GPSR EU Seller Action Kit': 'fetmu',
    'Turo Guest Dispute Toolkit': 'adyvd',
    'Restaurant Health Inspection Readiness Kit': 'dvfvm',
    'FTC Consumer Review Rule Compliance Kit': 'ekhza',
    'Trademark DIY Filing Action Kit': 'vkqogv',
    'STR Direct Booking Revenue Kit': 'ppsluq',
    'Vendor Questionnaire Response Kit': 'pyzqa',
    'EU Packaging EPR Action Kit': 'gfsvu',
    'Diminished Value Claim Kit': 'dyjavs',
    'ADA Demand-Letter Response & Triage Kit': 'palmdr',
    'EU AI Act Compliance Toolkit': 'iaiyt',
    'Sell in Europe Without Getting Delisted (KDP book)': None,  # KDP, not Gumroad
}

# Update each product with correct slug and URL
for p in catalog['products']:
    name = p['name']
    if name in slug_map:
        slug = slug_map[name]
        if slug:
            p['gumroad_slug'] = slug
            p['gumroad_url'] = f'https://aekraft.gumroad.com/l/{slug}'
        else:
            p['gumroad_slug'] = None
            p['gumroad_url'] = None

# Save updated catalog
with open('data/catalog.json', 'w', encoding='utf-8') as f:
    json.dump(catalog, f, indent=2, ensure_ascii=False)

print('Catalog updated with correct Gumroad slugs')
for p in catalog['products']:
    slug = p.get('gumroad_slug', 'N/A')
    url = p.get('gumroad_url', 'N/A')
    print(f'  {p["name"][:40]:40s} {slug:10s} {url}')

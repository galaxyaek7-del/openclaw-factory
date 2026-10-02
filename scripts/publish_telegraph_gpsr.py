"""Publish a GPSR EU Seller Action Kit article to Telegraph."""
import json, urllib.request, urllib.parse, ssl, time, datetime

ctx = ssl.create_default_context()

title = "GPSR EU Seller Action Kit: Non-EU Seller Compliance Guide 2026"

content = """<p>The EU's General Product Safety Regulation (GPSR) is now fully enforced. Non-EU sellers shipping to the EU face listing removal, fines up to EUR 100,000 per product, and marketplace delisting.</p>

<h2>What GPSR Requires</h2>
<p>Every product sold to EU consumers must have:</p>
<ul>
<li>An EU-based responsible person (manufacturer, importer, or authorized representative)</li>
<li>Technical documentation proving compliance with applicable safety standards</li>
<li>Traceability information (batch/serial number, manufacturer details)</li>
<li>Safety warnings and instructions in the official language(s) of the destination member state</li>
</ul>

<h2>Who This Affects</h2>
<p>If you are a non-EU seller (US, UK, China, etc.) selling physical products to EU customers through any channel — Amazon, Etsy, Shopify, eBay, or your own site — GPSR applies to you.</p>

<h2>What the GPSR EU Seller Action Kit Includes</h2>
<ul>
<li>Step-by-step compliance checklist per product category</li>
<li>Required documentation templates (technical file, DoC, traceability record)</li>
<li>EU representative requirement guide and provider directory</li>
<li>Response templates for takedown notices and marketplace enforcement actions</li>
<li>Deadline calendar for 2026-2027 milestones</li>
</ul>

<h2>Get the Kit</h2>
<p>The GPSR EU Seller Action Kit is available on Gumroad for $79:</p>
<p><a href="https://aekraft.gumroad.com/l/fetmu?utm_source=telegraph&utm_medium=article&utm_campaign=s3_exec_05&utm_content=gpsr_kit_a">https://aekraft.gumroad.com/l/fetmu?utm_source=telegraph&utm_medium=article&utm_campaign=s3_exec_05&utm_content=gpsr_kit_a</a></p>

<p><em>Disclosure: This article contains a commercial link. The kit is a digital product delivered instantly after purchase.</em></p>
"""

# Telegraph API: create account (anonymous) then create page
# Step 1: Create anonymous account
try:
    data = urllib.parse.urlencode({'short_name': 'GalaxyForge', 'author_name': 'Galaxy Forge'}).encode()
    req = urllib.request.Request('https://api.telegra.ph/createAccount', data=data)
    resp = urllib.request.urlopen(req, timeout=15, context=ctx)
    acct = json.loads(resp.read())
    print('Account:', acct.get('result', {}).get('access_token', 'N/A')[:20] + '...')
    token = acct['result']['access_token']
except Exception as e:
    print(f'Account creation failed: {e}')
    token = None

if token:
    time.sleep(1)
    # Step 2: Create page
    page_data = urllib.parse.urlencode({
        'title': title,
        'author_name': 'Galaxy Forge',
        'content': json.dumps([
            {"tag": "p", "children": ["The EU's General Product Safety Regulation (GPSR) is now fully enforced. Non-EU sellers shipping to the EU face listing removal, fines up to EUR 100,000 per product, and marketplace delisting."]},
            {"tag": "h2", "children": ["What GPSR Requires"]},
            {"tag": "p", "children": ["Every product sold to EU consumers must have:"]},
            {"tag": "ul", "children": [
                {"tag": "li", "children": ["An EU-based responsible person (manufacturer, importer, or authorized representative)"]},
                {"tag": "li", "children": ["Technical documentation proving compliance with applicable safety standards"]},
                {"tag": "li", "children": ["Traceability information (batch/serial number, manufacturer details)"]},
                {"tag": "li", "children": ["Safety warnings and instructions in the official language(s) of the destination member state"]}
            ]},
            {"tag": "h2", "children": ["Who This Affects"]},
            {"tag": "p", "children": ["If you are a non-EU seller (US, UK, China, etc.) selling physical products to EU customers through any channel — Amazon, Etsy, Shopify, eBay, or your own site — GPSR applies to you."]},
            {"tag": "h2", "children": ["What the GPSR EU Seller Action Kit Includes"]},
            {"tag": "ul", "children": [
                {"tag": "li", "children": ["Step-by-step compliance checklist per product category"]},
                {"tag": "li", "children": ["Required documentation templates (technical file, DoC, traceability record)"]},
                {"tag": "li", "children": ["EU representative requirement guide and provider directory"]},
                {"tag": "li", "children": ["Response templates for takedown notices and marketplace enforcement actions"]},
                {"tag": "li", "children": ["Deadline calendar for 2026-2027 milestones"]}
            ]},
            {"tag": "h2", "children": ["Get the Kit"]},
            {"tag": "p", "children": ["The GPSR EU Seller Action Kit is available on Gumroad for $79:"]},
            {"tag": "p", "children": [{"tag": "a", "attrs": {"href": "https://aekraft.gumroad.com/l/fetmu?utm_source=telegraph&utm_medium=article&utm_campaign=s3_exec_05&utm_content=gpsr_kit_a"}, "children": ["https://aekraft.gumroad.com/l/fetmu"]}]},
            {"tag": "p", "children": [{"tag": "em", "children": ["Disclosure: This article contains a commercial link. The kit is a digital product delivered instantly after purchase."]}]}
        ]),
        'access_token': token,
        'return_content': 'false'
    }).encode()
    req = urllib.request.Request('https://api.telegra.ph/createPage', data=page_data)
    resp = urllib.request.urlopen(req, timeout=15, context=ctx)
    page = json.loads(resp.read())
    result = page.get('result', {})
    url = result.get('url', 'N/A')
    print(f'Page created: {url}')

    # Save record
    record = {
        'url': url,
        'path': result.get('path', ''),
        'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'title': title,
        'campaign': 's3_exec_05',
        'product': 'GPSR EU Seller Action Kit',
        'utm_source': 'telegraph'
    }
    with open('data/telegraph_gpsr_article.json', 'w') as f:
        json.dump(record, f, indent=2)
    print('Record saved to data/telegraph_gpsr_article.json')

"""Publish comprehensive GPSR guide to Telegraph."""
import json, urllib.request, urllib.parse, ssl, time, datetime

ctx = ssl.create_default_context()

title = "GPSR Compliance: Complete Guide for Etsy Sellers 2026"

content = """<p>Are you an Etsy seller confused about GPSR compliance? You're not alone. This guide answers the most common questions from real Etsy sellers.</p>

<h2>What is GPSR?</h2>
<p>The General Product Safety Regulation (GPSR) is EU law that applies to all consumer products sold in the EU. Since December 2024, Etsy requires sellers to provide GPSR information for listings visible to EU buyers.</p>

<h2>Do I Need to Comply?</h2>
<p><strong>Yes, if:</strong></p>
<ul>
<li>You sell physical products to EU customers</li>
<li>Your products are visible to EU buyers on Etsy</li>
<li>You sell handmade, vintage (as functional), or craft supplies</li>
</ul>
<p><strong>No, if:</strong></p>
<ul>
<li>You only sell digital downloads</li>
<li>You only sell to non-EU customers</li>
<li>Your products are exempt under Article 2</li>
</ul>

<h2>What Information Do I Need to Provide?</h2>
<p>Etsy requires:</p>
<ol>
<li><strong>Manufacturer information:</strong> Your name, address, email, phone</li>
<li><strong>EU Responsible Person:</strong> Required if you're based outside the EU</li>
<li><strong>Product safety information:</strong> Warnings, instructions, traceability</li>
</ol>

<h2>How to Fill Out Etsy's GPSR Fields</h2>
<p><strong>Option 1: Shop-Level Economic Operator</strong></p>
<ul>
<li>Go to Shop Manager > Settings > Partners you work with</li>
<li>Add your EU Responsible Person in the economic operator section</li>
</ul>
<p><strong>Option 2: Per-Listing GPSR Information</strong></p>
<ul>
<li>Edit each listing</li>
<li>Fill in the product safety section</li>
<li>Add manufacturer and EU RP details</li>
</ul>

<h2>Common Problems and Solutions</h2>

<p><strong>Problem 1: "Disabling GPSR disables my entire shop"</strong></p>
<p>This is a known Etsy system flaw. The solution is to add GPSR information to all listings, not disable it.</p>

<p><strong>Problem 2: "I don't know how to create technical documentation"</strong></p>
<p>For most handmade products, you need:</p>
<ul>
<li>Risk assessment (identify potential hazards)</li>
<li>Test reports (if applicable)</li>
<li>Declaration of Conformity</li>
<li>User instructions and safety warnings</li>
</ul>

<p><strong>Problem 3: "I can't afford an EU Responsible Person"</strong></p>
<p>Services like Euverify (EUR 500-2,000/year) and EaseCert (one-time EUR 400-500) offer affordable options.</p>

<h2>Step-by-Step Compliance Checklist</h2>
<ol>
<li>Determine if GPSR applies to your products</li>
<li>Appoint an EU Responsible Person (if non-EU)</li>
<li>Create technical documentation for each product</li>
<li>Update product labels with EU RP details</li>
<li>Fill in Etsy's GPSR fields for each listing</li>
<li>Store documentation for 10 years</li>
</ol>

<h2>Get the Complete Checklist</h2>
<p>This guide covers the basics. The complete GPSR Compliance Checklist with templates and detailed guidance is available on Gumroad for $79:</p>
<p><a href="https://aekraft.gumroad.com/l/fetmu?utm_source=telegraph&utm_medium=article&utm_campaign=s3_exec_05&utm_content=gpsr_etsy_guide">https://aekraft.gumroad.com/l/fetmu?utm_source=telegraph&utm_medium=article&utm_campaign=s3_exec_05&utm_content=gpsr_etsy_guide</a></p>

<p><em>Disclosure: This article contains a commercial link. The checklist is a digital product delivered instantly after purchase.</em></p>
"""

# Create anonymous account
try:
    data = urllib.parse.urlencode({'short_name': 'GalaxyForge', 'author_name': 'Galaxy Forge'}).encode()
    req = urllib.request.Request('https://api.telegra.ph/createAccount', data=data)
    resp = urllib.request.urlopen(req, timeout=15, context=ctx)
    acct = json.loads(resp.read())
    token = acct['result']['access_token']
    print('Account created')
except Exception as e:
    print(f'Account creation failed: {e}')
    token = None

if token:
    time.sleep(1)
    # Create page
    page_data = urllib.parse.urlencode({
        'title': title,
        'author_name': 'Galaxy Forge',
        'content': json.dumps([
            {"tag": "p", "children": ["Are you an Etsy seller confused about GPSR compliance? You're not alone. This guide answers the most common questions from real Etsy sellers."]},
            {"tag": "h2", "children": ["What is GPSR?"]},
            {"tag": "p", "children": ["The General Product Safety Regulation (GPSR) is EU law that applies to all consumer products sold in the EU. Since December 2024, Etsy requires sellers to provide GPSR information for listings visible to EU buyers."]},
            {"tag": "h2", "children": ["Do I Need to Comply?"]},
            {"tag": "p", "children": [{"tag": "strong", "children": ["Yes, if:"]}]},
            {"tag": "ul", "children": [
                {"tag": "li", "children": ["You sell physical products to EU customers"]},
                {"tag": "li", "children": ["Your products are visible to EU buyers on Etsy"]},
                {"tag": "li", "children": ["You sell handmade, vintage (as functional), or craft supplies"]}
            ]},
            {"tag": "p", "children": [{"tag": "strong", "children": ["No, if:"]}]},
            {"tag": "ul", "children": [
                {"tag": "li", "children": ["You only sell digital downloads"]},
                {"tag": "li", "children": ["You only sell to non-EU customers"]},
                {"tag": "li", "children": ["Your products are exempt under Article 2"]}
            ]},
            {"tag": "h2", "children": ["What Information Do I Need to Provide?"]},
            {"tag": "p", "children": ["Etsy requires:"]},
            {"tag": "ol", "children": [
                {"tag": "li", "children": [{"tag": "strong", "children": ["Manufacturer information:"]}, " Your name, address, email, phone"]},
                {"tag": "li", "children": [{"tag": "strong", "children": ["EU Responsible Person:"]}, " Required if you're based outside the EU"]},
                {"tag": "li", "children": [{"tag": "strong", "children": ["Product safety information:"]}, " Warnings, instructions, traceability"]}
            ]},
            {"tag": "h2", "children": ["How to Fill Out Etsy's GPSR Fields"]},
            {"tag": "p", "children": [{"tag": "strong", "children": ["Option 1: Shop-Level Economic Operator"]}]},
            {"tag": "ul", "children": [
                {"tag": "li", "children": ["Go to Shop Manager > Settings > Partners you work with"]},
                {"tag": "li", "children": ["Add your EU Responsible Person in the economic operator section"]}
            ]},
            {"tag": "p", "children": [{"tag": "strong", "children": ["Option 2: Per-Listing GPSR Information"]}]},
            {"tag": "ul", "children": [
                {"tag": "li", "children": ["Edit each listing"]},
                {"tag": "li", "children": ["Fill in the product safety section"]},
                {"tag": "li", "children": ["Add manufacturer and EU RP details"]}
            ]},
            {"tag": "h2", "children": ["Common Problems and Solutions"]},
            {"tag": "p", "children": [{"tag": "strong", "children": ["Problem 1: \"Disabling GPSR disables my entire shop\""]}]},
            {"tag": "p", "children": ["This is a known Etsy system flaw. The solution is to add GPSR information to all listings, not disable it."]},
            {"tag": "p", "children": [{"tag": "strong", "children": ["Problem 2: \"I don't know how to create technical documentation\""]}]},
            {"tag": "p", "children": ["For most handmade products, you need:"]},
            {"tag": "ul", "children": [
                {"tag": "li", "children": ["Risk assessment (identify potential hazards)"]},
                {"tag": "li", "children": ["Test reports (if applicable)"]},
                {"tag": "li", "children": ["Declaration of Conformity"]},
                {"tag": "li", "children": ["User instructions and safety warnings"]}
            ]},
            {"tag": "p", "children": [{"tag": "strong", "children": ["Problem 3: \"I can't afford an EU Responsible Person\""]}]},
            {"tag": "p", "children": ["Services like Euverify (EUR 500-2,000/year) and EaseCert (one-time EUR 400-500) offer affordable options."]},
            {"tag": "h2", "children": ["Step-by-Step Compliance Checklist"]},
            {"tag": "ol", "children": [
                {"tag": "li", "children": ["Determine if GPSR applies to your products"]},
                {"tag": "li", "children": ["Appoint an EU Responsible Person (if non-EU)"]},
                {"tag": "li", "children": ["Create technical documentation for each product"]},
                {"tag": "li", "children": ["Update product labels with EU RP details"]},
                {"tag": "li", "children": ["Fill in Etsy's GPSR fields for each listing"]},
                {"tag": "li", "children": ["Store documentation for 10 years"]}
            ]},
            {"tag": "h2", "children": ["Get the Complete Checklist"]},
            {"tag": "p", "children": ["This guide covers the basics. The complete GPSR Compliance Checklist with templates and detailed guidance is available on Gumroad for $79:"]},
            {"tag": "p", "children": [{"tag": "a", "attrs": {"href": "https://aekraft.gumroad.com/l/fetmu?utm_source=telegraph&utm_medium=article&utm_campaign=s3_exec_05&utm_content=gpsr_etsy_guide"}, "children": ["https://aekraft.gumroad.com/l/fetmu"]}]},
            {"tag": "p", "children": [{"tag": "em", "children": ["Disclosure: This article contains a commercial link. The checklist is a digital product delivered instantly after purchase."]}]}
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
    with open('data/telegraph_gpsr_etsy_guide.json', 'w') as f:
        json.dump(record, f, indent=2)
    print('Record saved')

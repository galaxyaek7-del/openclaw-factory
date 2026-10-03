"""Publish GPSR Compliance Checklist article to Telegraph."""
import json, urllib.request, urllib.parse, ssl, time, datetime

ctx = ssl.create_default_context()

title = "GPSR Compliance Checklist for Non-EU Sellers (Free 2026)"

content = """<p>The EU's General Product Safety Regulation (GPSR) is now fully enforced. Non-EU sellers face listing removal, fines up to EUR 600,000, and account suspension.</p>

<h2>1. EU Responsible Person Requirements</h2>
<p><strong>Who needs one:</strong> Any non-EU seller shipping physical products to EU customers.</p>
<p><strong>How to appoint one:</strong> Use a compliance service like Euverify, EaseCert, or Cert-Rep. Cost: EUR 500-2,000/year.</p>
<p><strong>What information to display:</strong> Name, EU address, email, and phone number on product/packaging and marketplace listings.</p>

<h2>2. Technical Documentation</h2>
<p><strong>What documents you need:</strong></p>
<ul>
<li>Risk assessment document</li>
<li>Test reports and certificates</li>
<li>Declaration of Conformity</li>
<li>Technical file (design, manufacturing, components)</li>
<li>User manuals and safety warnings</li>
</ul>
<p><strong>How to organize them:</strong> Create a digital folder with all documents. Back up regularly.</p>
<p><strong>10-year storage requirement:</strong> All technical documentation must be stored for 10 years after the product is placed on the market.</p>

<h2>3. Labeling Requirements</h2>
<p><strong>What must appear on product/packaging:</strong></p>
<ul>
<li>Manufacturer name and address</li>
<li>EU Responsible Person name and address</li>
<li>Product identifier (batch/serial number)</li>
<li>Safety warnings in official language(s) of destination member state</li>
</ul>
<p><strong>Language requirements:</strong> Warnings and instructions must be in the official language(s) of the destination member state.</p>
<p><strong>Traceability information:</strong> Batch/serial number must be visible on product or packaging.</p>

<h2>4. Marketplace Compliance</h2>
<p><strong>Amazon EU requirements:</strong></p>
<ul>
<li>EU Responsible Person name, address, email, phone in Seller Central</li>
<li>Product safety information in listing</li>
<li>Response to takedown notices within 7-14 days</li>
</ul>
<p><strong>Etsy GPSR fields:</strong></p>
<ul>
<li>Economic Operator section in Shop Manager</li>
<li>Product safety information in listing</li>
<li>EU Responsible Person details for non-EU sellers</li>
</ul>
<p><strong>eBay and Shopify:</strong></p>
<ul>
<li>Similar requirements for EU-facing listings</li>
<li>Check platform-specific compliance guides</li>
</ul>

<h2>5. Risk Assessment</h2>
<p><strong>How to conduct a risk assessment:</strong></p>
<ol>
<li>Identify potential hazards</li>
<li>Assess likelihood and severity</li>
<li>Document mitigation measures</li>
<li>Review and update regularly</li>
</ol>
<p><strong>What to document:</strong> Hazard identification, risk evaluation, mitigation measures, review dates.</p>
<p><strong>When to update:</strong> After any product change, incident, or regulatory update.</p>

<h2>6. Response Templates</h2>
<p><strong>Takedown notice response:</strong></p>
<ul>
<li>Acknowledge receipt within 24 hours</li>
<li>Provide requested documentation</li>
<li>Implement corrective actions</li>
<li>Document all communications</li>
</ul>
<p><strong>Authority inquiry response:</strong></p>
<ul>
<li>Respond within specified deadline</li>
<li>Provide complete documentation</li>
<li>Cooperate fully with investigation</li>
</ul>
<p><strong>Customer safety concern response:</strong></p>
<ul>
<li>Take all concerns seriously</li>
<li>Investigate promptly</li>
<li>Document findings and actions</li>
<li>Report to authorities if required</li>
</ul>

<h2>Get the Full Checklist</h2>
<p>This article covers the basics. The complete GPSR Compliance Checklist with templates and detailed guidance is available on Gumroad for $79:</p>
<p><a href="https://aekraft.gumroad.com/l/fetmu?utm_source=telegraph&utm_medium=article&utm_campaign=s3_exec_05&utm_content=gpsr_checklist">https://aekraft.gumroad.com/l/fetmu?utm_source=telegraph&utm_medium=article&utm_campaign=s3_exec_05&utm_content=gpsr_checklist</a></p>

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
            {"tag": "p", "children": ["The EU's General Product Safety Regulation (GPSR) is now fully enforced. Non-EU sellers face listing removal, fines up to EUR 600,000, and account suspension."]},
            {"tag": "h2", "children": ["1. EU Responsible Person Requirements"]},
            {"tag": "p", "children": [{"tag": "strong", "children": ["Who needs one:"]}, " Any non-EU seller shipping physical products to EU customers."]},
            {"tag": "p", "children": [{"tag": "strong", "children": ["How to appoint one:"]}, " Use a compliance service like Euverify, EaseCert, or Cert-Rep. Cost: EUR 500-2,000/year."]},
            {"tag": "p", "children": [{"tag": "strong", "children": ["What information to display:"]}, " Name, EU address, email, and phone number on product/packaging and marketplace listings."]},
            {"tag": "h2", "children": ["2. Technical Documentation"]},
            {"tag": "p", "children": [{"tag": "strong", "children": ["What documents you need:"]}]},
            {"tag": "ul", "children": [
                {"tag": "li", "children": ["Risk assessment document"]},
                {"tag": "li", "children": ["Test reports and certificates"]},
                {"tag": "li", "children": ["Declaration of Conformity"]},
                {"tag": "li", "children": ["Technical file (design, manufacturing, components)"]},
                {"tag": "li", "children": ["User manuals and safety warnings"]}
            ]},
            {"tag": "p", "children": [{"tag": "strong", "children": ["How to organize them:"]}, " Create a digital folder with all documents. Back up regularly."]},
            {"tag": "p", "children": [{"tag": "strong", "children": ["10-year storage requirement:"]}, " All technical documentation must be stored for 10 years after the product is placed on the market."]},
            {"tag": "h2", "children": ["3. Labeling Requirements"]},
            {"tag": "p", "children": [{"tag": "strong", "children": ["What must appear on product/packaging:"]}]},
            {"tag": "ul", "children": [
                {"tag": "li", "children": ["Manufacturer name and address"]},
                {"tag": "li", "children": ["EU Responsible Person name and address"]},
                {"tag": "li", "children": ["Product identifier (batch/serial number)"]},
                {"tag": "li", "children": ["Safety warnings in official language(s) of destination member state"]}
            ]},
            {"tag": "p", "children": [{"tag": "strong", "children": ["Language requirements:"]}, " Warnings and instructions must be in the official language(s) of the destination member state."]},
            {"tag": "p", "children": [{"tag": "strong", "children": ["Traceability information:"]}, " Batch/serial number must be visible on product or packaging."]},
            {"tag": "h2", "children": ["4. Marketplace Compliance"]},
            {"tag": "p", "children": [{"tag": "strong", "children": ["Amazon EU requirements:"]}]},
            {"tag": "ul", "children": [
                {"tag": "li", "children": ["EU Responsible Person name, address, email, phone in Seller Central"]},
                {"tag": "li", "children": ["Product safety information in listing"]},
                {"tag": "li", "children": ["Response to takedown notices within 7-14 days"]}
            ]},
            {"tag": "p", "children": [{"tag": "strong", "children": ["Etsy GPSR fields:"]}]},
            {"tag": "ul", "children": [
                {"tag": "li", "children": ["Economic Operator section in Shop Manager"]},
                {"tag": "li", "children": ["Product safety information in listing"]},
                {"tag": "li", "children": ["EU Responsible Person details for non-EU sellers"]}
            ]},
            {"tag": "p", "children": [{"tag": "strong", "children": ["eBay and Shopify:"]}]},
            {"tag": "ul", "children": [
                {"tag": "li", "children": ["Similar requirements for EU-facing listings"]},
                {"tag": "li", "children": ["Check platform-specific compliance guides"]}
            ]},
            {"tag": "h2", "children": ["5. Risk Assessment"]},
            {"tag": "p", "children": [{"tag": "strong", "children": ["How to conduct a risk assessment:"]}]},
            {"tag": "ol", "children": [
                {"tag": "li", "children": ["Identify potential hazards"]},
                {"tag": "li", "children": ["Assess likelihood and severity"]},
                {"tag": "li", "children": ["Document mitigation measures"]},
                {"tag": "li", "children": ["Review and update regularly"]}
            ]},
            {"tag": "p", "children": [{"tag": "strong", "children": ["What to document:"]}, " Hazard identification, risk evaluation, mitigation measures, review dates."]},
            {"tag": "p", "children": [{"tag": "strong", "children": ["When to update:"]}, " After any product change, incident, or regulatory update."]},
            {"tag": "h2", "children": ["6. Response Templates"]},
            {"tag": "p", "children": [{"tag": "strong", "children": ["Takedown notice response:"]}]},
            {"tag": "ul", "children": [
                {"tag": "li", "children": ["Acknowledge receipt within 24 hours"]},
                {"tag": "li", "children": ["Provide requested documentation"]},
                {"tag": "li", "children": ["Implement corrective actions"]},
                {"tag": "li", "children": ["Document all communications"]}
            ]},
            {"tag": "p", "children": [{"tag": "strong", "children": ["Authority inquiry response:"]}]},
            {"tag": "ul", "children": [
                {"tag": "li", "children": ["Respond within specified deadline"]},
                {"tag": "li", "children": ["Provide complete documentation"]},
                {"tag": "li", "children": ["Cooperate fully with investigation"]}
            ]},
            {"tag": "p", "children": [{"tag": "strong", "children": ["Customer safety concern response:"]}]},
            {"tag": "ul", "children": [
                {"tag": "li", "children": ["Take all concerns seriously"]},
                {"tag": "li", "children": ["Investigate promptly"]},
                {"tag": "li", "children": ["Document findings and actions"]},
                {"tag": "li", "children": ["Report to authorities if required"]}
            ]},
            {"tag": "h2", "children": ["Get the Full Checklist"]},
            {"tag": "p", "children": ["This article covers the basics. The complete GPSR Compliance Checklist with templates and detailed guidance is available on Gumroad for $79:"]},
            {"tag": "p", "children": [{"tag": "a", "attrs": {"href": "https://aekraft.gumroad.com/l/fetmu?utm_source=telegraph&utm_medium=article&utm_campaign=s3_exec_05&utm_content=gpsr_checklist"}, "children": ["https://aekraft.gumroad.com/l/fetmu"]}]},
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
    with open('data/telegraph_gpsr_checklist.json', 'w') as f:
        json.dump(record, f, indent=2)
    print('Record saved')

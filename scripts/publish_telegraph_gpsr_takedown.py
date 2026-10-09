"""S3 commercial experiment (2026-10-09): GPSR takedown-recovery article.

DIFFERS from the 2026-10-02 GPSR article in angle and CTA:
- angle: listing ALREADY removed (urgent recovery), not general compliance
- CTA: the free checklist funnel (gpsr-landing.html, UTM campaign s3_exec_06),
  NOT the Gumroad checkout (writes blocked) -- so every click is measurable in
  our own page-view ledger instead of vanishing into a dead purchase path.

Content rules: problem-first, no fabricated claims, commercial link disclosed.
Reuses the stored author identity in data/telegraph.json (no new account).
Records the publication to its own file; never overwrites existing records.
"""
import datetime
import io
import json
import sys
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

TOKEN = json.load(io.open('data/telegraph.json', encoding='utf-8'))['access_token']
BASE = 'https://galaxyaek7-del.github.io/openclaw-factory/customer_site/gpsr-landing.html'
CTA = (BASE + '?utm_source=telegraph&utm_medium=article'
       '&utm_campaign=s3_exec_06&utm_content=gpsr_takedown_recovery')

TITLE = 'Amazon Removed Your Listing Under GPSR? A 48-Hour Recovery Plan for Non-EU Sellers'

BODY = [
    {"tag": "p", "children": [
        "In January 2025 Amazon removed thousands of non-EU listings under the EU General "
        "Product Safety Regulation (GPSR). If yours was one of them, the listing stays down "
        "until the marketplace sees proof of compliance -- not just a promise to fix it."]},
    {"tag": "h2", "children": ["Hour 0-8: Diagnose the takedown notice"]},
    {"tag": "p", "children": [
        "Read the notice for the exact cited failure: missing EU Responsible Person, missing "
        "traceability data, or missing safety warnings in the destination language. Each one "
        "has a different fix, and appealing with the wrong evidence resets the clock."]},
    {"tag": "h2", "children": ["Hour 8-24: Assemble the three documents marketplaces ask for first"]},
    {"tag": "ul", "children": [
        {"tag": "li", "children": ["EU Responsible Person details (name, address, contact)"]},
        {"tag": "li", "children": ["Traceability record: batch/serial number plus manufacturer details"]},
        {"tag": "li", "children": ["Safety warnings in the official language of each destination member state"]},
    ]},
    {"tag": "h2", "children": ["Hour 24-48: File the appeal with evidence attached"]},
    {"tag": "p", "children": [
        "Submit through the marketplace's compliance portal with all three documents attached "
        "at once. Partial submissions are the most common reason appeals stall a second time."]},
    {"tag": "h2", "children": ["Prevent the next takedown"]},
    {"tag": "p", "children": [
        "Our free GPSR Compliance Checklist covers the Responsible Person requirement, "
        "technical documentation, labelling, and takedown-response templates:"]},
    {"tag": "p", "children": [
        {"tag": "a", "attrs": {"href": CTA}, "children": ["Get the free GPSR Compliance Checklist"]}]},
    {"tag": "p", "children": [
        {"tag": "em", "children": [
            "Disclosure: the checklist is free. Galaxy Forge also sells a $79 GPSR EU Seller "
            "Action Kit with full templates; the free checklist carries no purchase obligation."]}]},
]


def api(method, params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request('https://api.telegra.ph/' + method, data=data)
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


page = api('createPage', {
    'access_token': TOKEN,
    'title': TITLE,
    'author_name': 'Galaxy Forge',
    'content': json.dumps(BODY),
    'return_content': 'false',
})
res = page.get('result', {})
url = res.get('url', '')
print('PAGE:', url or page)
assert url.startswith('https://telegra.ph/'), 'publication failed: %s' % page

record = {
    'url': url,
    'path': res.get('path', ''),
    'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'title': TITLE,
    'campaign': 's3_exec_06',
    'product': 'GPSR EU Seller Action Kit (free-checklist funnel)',
    'utm_source': 'telegraph',
    'angle': 'takedown recovery (vs 2026-10-02 general compliance)',
    'cta_destination': CTA,
}
io.open('data/telegraph_gpsr_takedown_2026-10-09.json', 'w',
        encoding='utf-8').write(json.dumps(record, indent=2))
print('RECORDED: data/telegraph_gpsr_takedown_2026-10-09.json')

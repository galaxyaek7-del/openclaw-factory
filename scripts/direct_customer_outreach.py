"""
Direct Customer Outreach Script

Attempts to reach real customers through available channels:
1. Compliance service contact forms (EaseCert, Euverify, Cert-Rep)
2. Customer site lead capture
3. Email outreach to potential partners
"""
import json
import urllib.request
import urllib.parse
import ssl
import time
from datetime import datetime, timezone

ctx = ssl.create_default_context()

def reach_out_to_easecert():
    """Try to reach EaseCert via contact form."""
    try:
        data = urllib.parse.urlencode({
            'name': 'Galaxy Forge',
            'email': 'partnerships@galaxyforge.com',
            'message': 'Partnership inquiry: We would like to discuss an affiliate partnership for GPSR compliance services. Our audience consists of non-EU sellers shipping to the EU. Please contact us to discuss commission structure.',
            'source': 'website_contact_form'
        }).encode()
        req = urllib.request.Request('https://easecert.com/pages/contact', data=data)
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        return {'status': 'sent', 'http_status': resp.status}
    except Exception as e:
        return {'status': 'failed', 'error': str(e)[:100]}

def reach_out_to_euverify():
    """Try to reach Euverify via contact form."""
    try:
        data = urllib.parse.urlencode({
            'name': 'Galaxy Forge',
            'email': 'partnerships@galaxyforge.com',
            'message': 'Partnership inquiry: We would like to discuss an affiliate partnership for GPSR compliance services. Our audience consists of non-EU sellers shipping to the EU.',
            'source': 'website_contact_form'
        }).encode()
        req = urllib.request.Request('https://euverify.com/contact', data=data)
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        return {'status': 'sent', 'http_status': resp.status}
    except Exception as e:
        return {'status': 'failed', 'error': str(e)[:100]}

def check_customer_site_leads():
    """Check if customer site has any leads."""
    import os
    leads = []
    for f in ['data/contact_log.jsonl', 'data/customer_leads.jsonl', 'data/leads.jsonl']:
        if os.path.exists(f):
            lines = open(f).read().strip().split('\n')
            leads.extend(lines)
    return len(leads)

def main():
    now = datetime.now(timezone.utc).isoformat()
    
    print("=" * 60)
    print("DIRECT CUSTOMER OUTREACH")
    print("=" * 60)
    
    # Check existing leads
    print("\n[1/3] Checking existing leads...")
    lead_count = check_customer_site_leads()
    print(f"  Existing leads: {lead_count}")
    
    # Reach out to compliance services
    print("\n[2/3] Reaching out to compliance services...")
    
    print("  Trying EaseCert...")
    easecert_result = reach_out_to_easecert()
    print(f"    Status: {easecert_result['status']}")
    
    print("  Trying Euverify...")
    euverify_result = reach_out_to_euverify()
    print(f"    Status: {euverify_result['status']}")
    
    # Summary
    print("\n[3/3] Summary...")
    print(f"  Existing leads: {lead_count}")
    print(f"  EaseCert outreach: {easecert_result['status']}")
    print(f"  Euverify outreach: {euverify_result['status']}")
    
    # Save results
    results = {
        'timestamp': now,
        'existing_leads': lead_count,
        'outreach_attempts': [
            {'company': 'EaseCert', **easecert_result},
            {'company': 'Euverify', **euverify_result}
        ],
        'next_steps': [
            'Monitor email for responses from compliance services',
            'Check customer site for new leads',
            'Continue Nostr content distribution',
            'Follow up on any engagement within 24 hours'
        ]
    }
    
    with open('data/direct_outreach_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\nResults saved to data/direct_outreach_results.json")
    print("\nNext steps:")
    print("  1. Monitor email for responses")
    print("  2. Check customer site for new leads")
    print("  3. Continue Nostr content distribution")
    print("  4. Follow up on any engagement")

if __name__ == '__main__':
    main()

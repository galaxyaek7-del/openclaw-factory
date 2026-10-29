"""Distribution metrics poll (GF-AUTONOMY-EXPANSION-02).
Read-only: Telegraph getViews (own author identity), Gumroad --sales,
interest ledger line counts. Appends one JSONL record per run.
Safe to run repeatedly; never publishes, never spends, never notifies."""
import json, io, sys, subprocess, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'data' / 'distribution_metrics.jsonl'

ARTICLES = {
    'gpsr_takedown': 'Amazon-Removed-Your-Listing-Under-GPSR-A-48-Hour-Recovery-Plan-for-Non-EU-Sellers-10-09',
    'homebuyer_method': 'Your-Inspection-Report-Is-Long-Your-Contingency-Deadline-Is-Short-Here-Is-the-Math-First-Way-Through-It-10-09',
    'homebuyer_credit': 'Credit-or-Repair-Walking-One-Inspection-Finding-Through-the-Dollar-Math-10-09',
    'landlord_movein': 'The-Move-Out-Deposit-Fight-Is-Won-at-Move-In-A-Photo-and-Signature-Baseline-10-09',
    'cottage_food': 'Selling-Food-From-Your-Home-Kitchen-Your-State-Has-a-Cap-a-Label-Rule-and-a-Registration-10-09',
    'b2b_batch': 'What-a-Done-For-You-200-Lead-Batch-Should-Contain-and-How-Ordering-Works-10-09',
    'restaurant_foodcost': 'Your-Food-Cost-Is-4-Points-Too-High-The-Variance-Worksheet-Finds-Where-10-09',
    'dental_verify': 'Stop-Verifying-Dental-Benefits-at-the-Front-Desk-on-the-Day-of-the-Visit-10-09',
}

# Self-load separation: factory verification fetches inflate getViews totals.
# data/telegraph_own_loads.json counts our own page loads per article
# (priors are honestly ESTIMATED; counting is exact from 2026-10-10 on).
# net_estimate = gross - own (floor 0); external reach stays UNKNOWN-but-bounded.
OWN_LOADS_PATH = ROOT / 'data' / 'telegraph_own_loads.json'

rec = {'timestamp': datetime.now(timezone.utc).isoformat(), 'views': {},
       'views_status': {}, 'sales': 'UNKNOWN', 'sales_count': 'UNKNOWN',
       'interest_accepted': 'UNKNOWN', 'interest_rejected': 'UNKNOWN',
       # key -> Telegraph path, so a reading can be joined to the experiment
       # that names the article (added 2026-10-29).
       'articles': dict(ARTICLES)}

try:
    token = json.load(io.open(ROOT / 'data' / 'telegraph.json',
                              encoding='utf-8'))['access_token']
    for label, path in ARTICLES.items():
        try:
            data = urllib.parse.urlencode(
                {'access_token': token, 'path': path}).encode()
            req = urllib.request.Request('https://api.telegra.ph/getViews',
                                         data=data)
            res = json.loads(urllib.request.urlopen(req, timeout=25).read())
            if res.get('ok'):
                rec['views'][label] = res['result'].get('views')
                rec['views_status'][label] = 'ok'
            else:
                rec['views_status'][label] = 'api_not_ok'
        except Exception as e:
            rec['views_status'][label] = 'ERROR_%s' % type(e).__name__
except Exception as e:
    rec['views_status']['_token'] = 'ERROR_%s' % type(e).__name__

try:
    # Run as a module: as a plain script it cannot import its own package
    # (ModuleNotFoundError: channels), and sales read UNKNOWN on every run.
    out = subprocess.run([sys.executable, '-m', 'channels.gumroad_publisher', '--sales'],
                         capture_output=True, text=True, timeout=60, cwd=str(ROOT))
    d = json.loads(out.stdout)
    sales = d.get('sales', [])
    rec['sales'] = sales
    rec['sales_count'] = len(sales)
except Exception as e:
    rec['sales'] = 'ERROR_%s' % type(e).__name__

for key, rel in (('interest_accepted', 'data/customer_interest.jsonl'),
                 ('interest_rejected', 'data/customer_interest_rejected.jsonl')):
    p = ROOT / rel
    try:
        rec[key] = len(p.read_text(encoding='utf-8').splitlines()) if p.exists() else 0
    except Exception:
        pass

try:
    own = json.loads(OWN_LOADS_PATH.read_text(encoding='utf-8')) if OWN_LOADS_PATH.exists() else {}
    rec['own_loads'] = own.get('loads', {})
    rec['own_loads_quality'] = own.get('quality', 'UNKNOWN')
    net = {}
    for label, gross in rec['views'].items():
        if isinstance(gross, int):
            net[label] = max(0, gross - int(rec['own_loads'].get(label, 0)))
        else:
            net[label] = 'UNKNOWN'
    rec['net_external_estimate'] = net
except Exception as e:
    rec['own_loads'] = 'ERROR_%s' % type(e).__name__

with open(OUT, 'a', encoding='utf-8') as f:
    f.write(json.dumps(rec, ensure_ascii=False) + '\n')
print(json.dumps(rec, indent=1, ensure_ascii=False))

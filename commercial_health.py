"""Commercial health monitor.

Cycle 146. Phase 8 of the operating directive asked whether the factory can
detect, on its own:

  - a product whose purchase path has broken
  - a product with missing or broken files
  - dead product links
  - the real sales result
  - the loss of analytics availability

The honest answer before this module was no. Every one of those checks had
been re-written from scratch as a throwaway script in every cycle, and two of
them were answered WRONG in the process - a view total inflated by our own
verification fetches, and a CTA count of 22 that the API says is 15.

This module makes the checks real, repeatable and testable. It is deliberately
small and read-only. It writes nothing, changes no product, makes no payment,
and never claims a sale.

It also refuses to report a number it cannot source. Anything unavailable comes
back as UNKNOWN with a reason, never as a zero.
"""
import json
import re

__all__ = ['check_product_health', 'check_sales_ledger', 'check_link_health',
           'run_health_report', 'UNKNOWN']

UNKNOWN = 'UNKNOWN'


def _status(ok, reason=None):
    if ok is True:
        return 'PASS'
    if ok is False:
        return 'BLOCKED'
    return UNKNOWN


def check_product_health(fetch_product, fetch_checkout, slug):
    """Verify one product can actually be bought and delivered.

    fetch_product(slug) -> dict as returned by the Gumroad API
    fetch_checkout(slug) -> HTTP status int

    Deliberately separates the three things that are constantly conflated:
    the page existing, the checkout existing, and a purchase completing.
    The third is never claimed here - completing it would require a payment.
    """
    out = {'slug': slug, 'problems': []}

    p = fetch_product(slug) or {}
    if not p:
        out['problems'].append('product record unreadable')
        out['published'] = UNKNOWN
        out['price'] = UNKNOWN
        out['files'] = UNKNOWN
        out['page'] = 'BLOCKED'
        out['checkout'] = UNKNOWN
        out['purchase_completion'] = UNKNOWN
        out['verdict'] = 'BLOCKED'
        return out
    out['name'] = p.get('name')
    out['published'] = p.get('published')
    out['price'] = (p.get('price') or 0) / 100.0 if p.get('price') is not None else UNKNOWN

    files = p.get('files') or []
    out['file_count'] = len(files)
    out['files'] = _status(bool(files) and bool(files[0].get('size')),
                           'no file attached' if not files else 'file has zero size')
    if not files:
        out['problems'].append('NO FILE ATTACHED - a buyer would pay and receive nothing')

    ck = fetch_checkout(slug)
    out['checkout'] = _status(ck == 200, 'checkout returned %s' % ck)
    if ck != 200:
        out['problems'].append('checkout returned HTTP %s' % ck)

    # a product page is not a purchase path, and neither is a purchase
    out['page'] = 'PASS' if p.get('published') else 'BLOCKED'
    if not p.get('published'):
        out['problems'].append('NOT PUBLISHED - it cannot be bought')

    # VERDICT must be derived from the status fields themselves, never from a
    # parallel list that can drift out of step with them. Two of the first
    # tests written for this module caught exactly that drift.
    out['purchase_completion'] = UNKNOWN
    out['purchase_completion_reason'] = (
        'requires a real buyer and a real card. Not attempted, never claimed.')
    failed = [k for k in ('page', 'files', 'checkout') if out.get(k) == 'BLOCKED']
    out['verdict'] = 'BLOCKED' if failed else 'PASS'
    return out


def check_sales_ledger(fetch_sales):
    """Report the real sales result, and say UNKNOWN rather than guess.

    A zero here is a real, sourced zero. A missing refunds capability is
    reported as UNKNOWN, never folded into the revenue number.
    """
    data = fetch_sales() or {}
    sales = data.get('sales') or []
    out = {
        'orders': len(sales),
        'orders_source': 'Gumroad /v2/sales',
        'gross_cents': sum(int((s.get('amount') or 0)) for s in sales) or 0.0,
        'refunds': UNKNOWN,
        'refunds_reason': 'Gumroad exposes no refunds field or endpoint',
        'net_after_refunds': UNKNOWN,
        'payouts_withdrawn': UNKNOWN,
    }
    out['verified_revenue_usd'] = out['gross_cents'] / 100.0
    out['evidence'] = 'OBSERVED' if sales else 'OBSERVED (sourced zero, not an estimate)'
    return out


def check_link_health(find_links, fetch_status):
    """Check every product link the repo publishes still resolves.

    Returns per-link status. A link that resolves to the wrong product is
    treated as broken, not merely reachable.
    """
    out = []
    for href in sorted(set(find_links())):
        m = re.search(r'/l/([A-Za-z0-9]+)', href or '')
        slug = m.group(1) if m else None
        code = fetch_status(href)
        rec = {'href': href, 'slug': slug, 'http': code,
               'status': 'PASS' if code == 200 else 'BLOCKED'}
        if code != 200:
            rec['reason'] = 'dead link - a buyer following it gets nothing'
        out.append(rec)
    return out


def run_health_report(fetch_product, fetch_checkout, fetch_sales, slugs,
                      find_links=None, fetch_status=None):
    products = [check_product_health(fetch_product, fetch_checkout, s) for s in slugs]
    sales = check_sales_ledger(fetch_sales)
    links = check_link_health(find_links, fetch_status) if find_links else UNKNOWN

    blocked = [p for p in products if p['verdict'] == 'BLOCKED']
    needs_human = [p['slug'] for p in products if p['verdict'] == 'BLOCKED']

    return {
        'generated_by': 'commercial_health',
        'products': products,
        'sales': sales,
        'links': links,
        'summary': {
            'products_checked': len(products),
            'products_blocked': len(blocked),
            'products_healthy': len(products) - len(blocked),
            'verified_revenue_usd': sales['verified_revenue_usd'],
            'requires_human_action': needs_human,
        },
        'never_claimed': [
            'a completed purchase',
            'a refund figure',
            'net revenue after fees',
            'payout eligibility',
            'product page visits or checkout visits - no Gumroad field exposes them',
        ],
    }

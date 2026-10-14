"""Root-cause classification for the commercial funnel.

Cycle 147. The ad-hoc checks this replaces had been rewritten every cycle and
had produced two wrong answers (an inflated view total, and a CTA count of 22
that the API says is 15). The failure mode was never the checks - it was
re-deriving the same judgement by hand each time.

This module answers one question: WHERE is the funnel actually stopped?

  A. PRODUCT_BLOCKED      the product or its file or its page is broken
  B. CHECKOUT_BLOCKED     the purchase path cannot be completed
  C. PAYOUT_BLOCKED       no receiving method, or an account restriction
  D. ACQUISITION_BLOCKED  no evidence qualified buyers ever reached the offer
  E. CONVERSION_UNPROVEN  no completed, verified transaction
  F. TRACKING_UNRELIABLE  the counters do not represent real commercial activity

Each state carries its evidence and its status. Critically, none of them is
ever cleared by a weak signal. HTTP 200, a published article, or an existing
product is NOT evidence of revenue, and the tests enforce that.
"""
import json

PASS, HOLD, BLOCKED, UNKNOWN = 'PASS', 'HOLD', 'BLOCKED', 'UNKNOWN'
OBSERVED, DERIVED, INFERRED, ESTIMATED = 'OBSERVED', 'DERIVED', 'INFERRED', 'ESTIMATED'


def classify(health, sales, funnel):
    """Map a health report plus funnel evidence onto the A-F root causes.

    health  - output of commercial_health.run_health_report
    sales   - output of commercial_health.check_sales_ledger
    funnel  - {'unique_readers', 'outbound_clicks', 'product_visits',
               'checkout_visits', 'attribution_available'}
               UNKNOWN for any value that cannot be measured.
    """
    products = health.get('products') or []
    causes = {}

    # ---- A. PRODUCT_BLOCKED -------------------------------------------------
    broken = [p['slug'] for p in products if p.get('verdict') == 'BLOCKED']
    causes['A_PRODUCT_BLOCKED'] = {
        'status': BLOCKED if broken else PASS,
        'evidence': ('%d of %d products blocked: %s'
                     % (len(broken), len(products), ', '.join(broken))) if broken
                    else 'every checked product is published, has a file, and serves a page',
        'classification': OBSERVED,
        'note': 'a product existing is not a product selling. This state only covers'
                ' the product surface itself.',
    }

    # ---- B. CHECKOUT_BLOCKED -----------------------------------------------
    # A 200 checkout means the route responds. It is NOT checkout readiness.
    # Readiness would need a completed transaction, which is state E.
    unreachable = [p['slug'] for p in products if p.get('checkout') == 'BLOCKED']
    causes['B_CHECKOUT_BLOCKED'] = {
        'status': BLOCKED if unreachable else UNKNOWN,
        'evidence': ('checkout unreachable for %s' % ', '.join(unreachable)) if unreachable
                    else 'every checkout route returns 200 - which proves reachability only',
        'classification': OBSERVED,
        'why_not_PASS': 'HTTP 200 is not CHECKOUT_READY. Per the governing rules, '
                        'checkout readiness needs evidence a purchase can be '
                        'completed, and no purchase has ever been attempted.',
        'requires': 'one completed transaction, or a browser session',
    }

    # ---- C. PAYOUT_BLOCKED --------------------------------------------------
    causes['C_PAYOUT_BLOCKED'] = {
        'status': UNKNOWN,
        'evidence': 'Gumroad exposes no endpoint returning payout eligibility. '
                    '/payouts returns a valid empty list, which proves read scope '
                    'and nothing about whether a receiving method exists.',
        'classification': OBSERVED,
        'why_not_PASS': 'PAYOUT_READY is never granted merely because a settings '
                        'page exists or a payouts list is readable.',
        'requires': 'a logged-in visit to gumroad.com/settings/payouts',
        'not_blocking_sales_yet': 'with zero orders, payouts have never been '
                                  'exercised in either direction, so this is NOT '
                                  'demonstrated as the cause of zero sales.',
    }

    # ---- D. ACQUISITION_BLOCKED --------------------------------------------
    readers = funnel.get('unique_readers', UNKNOWN)
    visits = funnel.get('product_visits', UNKNOWN)
    if readers == 0 or visits == 0:
        status, evidence = BLOCKED, 'a measurable zero at a funnel stage'
    elif readers == UNKNOWN or visits == UNKNOWN:
        status, evidence = BLOCKED, ('no measurable qualified traffic: unique readers %s, '
                                     'product visits %s. No evidence any buyer reached the offer.'
                                     % (readers, visits))
    else:
        status, evidence = HOLD, 'traffic exists but has not yet converted'
    causes['D_ACQUISITION_BLOCKED'] = {
        'status': status,
        'evidence': evidence,
        'classification': OBSERVED if readers != UNKNOWN else DERIVED,
        'note': 'article reads are not buyers and are never summed with product visits.',
    }

    # ---- E. CONVERSION_UNPROVEN --------------------------------------------
    orders = sales.get('orders', 0)
    causes['E_CONVERSION_UNPROVEN'] = {
        'status': BLOCKED if orders == 0 else HOLD,
        'evidence': 'orders=%s from %s; verified revenue $%.2f'
                    % (orders, sales.get('orders_source'),
                       sales.get('verified_revenue_usd', 0.0)),
        'classification': OBSERVED,
        'rule': 'VERIFIED_REVENUE stays 0 until a completed external transaction '
                'is evidenced. No product, page, article or HTTP status may clear it.',
    }

    # ---- F. TRACKING_UNRELIABLE -------------------------------------------
    attribution = funnel.get('attribution_available', False)
    causes['F_TRACKING_UNRELIABLE'] = {
        'status': BLOCKED if not attribution else HOLD,
        'evidence': 'Gumroad exposes no visit, impression, click or session field, '
                    'and Telegraph article reads include this project own HTML '
                    'verification fetches. Article reads therefore cannot be used '
                    'as audience evidence.',
        'classification': OBSERVED,
        'proven': 'one HTML fetch of a Telegraph article increments its own view '
                  'counter by exactly 1; API reads move it by 0.',
        'mitigation': 'lib.telegraph_safe_edit.api_view_count and api_page_text '
                      'read through the API with zero inflation.',
    }

    blocking = [k for k, v in causes.items()
                if v['status'] == BLOCKED and k != 'C_PAYOUT_BLOCKED']
    return {
        'causes': causes,
        'root_cause_order': blocking,
        'single_root_cause': blocking[0] if blocking else None,
        'governing_rules': {
            'VERIFIED_REVENUE': sales.get('verified_revenue_usd', 0.0),
            'PAYOUT_READY': 'never granted without a dashboard read',
            'CHECKOUT_READY': 'never granted from an HTTP status alone',
        },
    }


if __name__ == '__main__':
    print(json.dumps(classify({}, {'orders': 0, 'orders_source': 'x',
                                   'verified_revenue_usd': 0.0},
                              {'unique_readers': UNKNOWN, 'product_visits': UNKNOWN,
                               'attribution_available': False}), indent=1))
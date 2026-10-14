"""Tests for commercial_root_causes.py.

The governing rules this module exists to enforce are all negative rules - things
that must NOT be treated as success. These tests pin every one of them, because
the failure mode this project actually suffered was a weak signal being read as
a positive result.

Specifically: HTTP 200, a published article, and an existing product must never
clear checkout readiness, payout readiness, or revenue.
"""
import sys
import unittest

sys.path.insert(0, r'C:\openclaw-dasgboard')
from commercial_root_causes import (classify, PASS, BLOCKED, UNKNOWN, HOLD)


def health(verdicts, checkouts=None):
    out = []
    for i, v in enumerate(verdicts):
        out.append({'slug': 'p%d' % i, 'verdict': v,
                    'checkout': (checkouts[i] if checkouts else 'PASS')})
    return {'products': out}


def sales(orders=0, revenue=0.0):
    return {'orders': orders, 'orders_source': 'Gumroad /v2/sales',
            'verified_revenue_usd': revenue}


def funnel(**kw):
    d = {'unique_readers': UNKNOWN, 'product_visits': UNKNOWN,
         'outbound_clicks': UNKNOWN, 'checkout_visits': UNKNOWN,
         'attribution_available': False}
    d.update(kw)
    return d


class TestProductBlocked(unittest.TestCase):

    def test_all_healthy_products_give_PASS(self):
        r = classify(health(['PASS', 'PASS']), sales(), funnel())
        self.assertEqual(r['causes']['A_PRODUCT_BLOCKED']['status'], PASS)

    def test_a_broken_product_is_blocked_and_named(self):
        r = classify(health(['PASS', 'BLOCKED']), sales(), funnel())
        c = r['causes']['A_PRODUCT_BLOCKED']
        self.assertEqual(c['status'], BLOCKED)
        self.assertIn('p1', c['evidence'])


class TestCheckoutBlockedNeverClearsOnHTTP200(unittest.TestCase):

    def test_checkout_200_is_never_PASS_it_is_UNKNOWN(self):
        """THE core rule: a 200 checkout is reachability, not readiness."""
        r = classify(health(['PASS']), sales(), funnel())
        c = r['causes']['B_CHECKOUT_BLOCKED']
        self.assertNotEqual(c['status'], PASS)
        self.assertEqual(c['status'], UNKNOWN)
        self.assertIn('not CHECKOUT_READY', c['why_not_PASS'])

    def test_unreachable_checkout_is_BLOCKED(self):
        r = classify(health(['PASS'], checkouts=['BLOCKED']), sales(), funnel())
        self.assertEqual(r['causes']['B_CHECKOUT_BLOCKED']['status'], BLOCKED)


class TestPayoutBlockedNeverClearsOnReadableEndpoint(unittest.TestCase):

    def test_payout_is_always_unknown_even_with_readable_endpoint(self):
        r = classify(health(['PASS']), sales(), funnel())
        c = r['causes']['C_PAYOUT_BLOCKED']
        self.assertEqual(c['status'], UNKNOWN)
        self.assertNotEqual(c['status'], PASS)
        self.assertIn('never granted', c['why_not_PASS'])

    def test_payout_is_not_treated_as_the_cause_of_zero_sales(self):
        r = classify(health(['PASS']), sales(), funnel())
        self.assertNotIn('C_PAYOUT_BLOCKED', r['root_cause_order'])
        self.assertIn('never been exercised',
                      r['causes']['C_PAYOUT_BLOCKED']['not_blocking_sales_yet'])


class TestAcquisition(unittest.TestCase):

    def test_unknown_traffic_still_reads_as_blocked(self):
        r = classify(health(['PASS']), sales(), funnel())
        self.assertEqual(r['causes']['D_ACQUISITION_BLOCKED']['status'], BLOCKED)
        self.assertIn('No evidence any buyer reached',
                      r['causes']['D_ACQUISITION_BLOCKED']['evidence'])

    def test_measured_zero_reads_as_blocked(self):
        r = classify(health(['PASS']), sales(),
                     funnel(unique_readers=0, product_visits=0))
        self.assertEqual(r['causes']['D_ACQUISITION_BLOCKED']['status'], BLOCKED)

    def test_real_traffic_without_orders_is_hold_not_pass(self):
        r = classify(health(['PASS']), sales(),
                     funnel(unique_readers=500, product_visits=120, attribution_available=True))
        self.assertEqual(r['causes']['D_ACQUISITION_BLOCKED']['status'], HOLD)


class TestConversion(unittest.TestCase):

    def test_zero_orders_is_blocked_and_revenue_stays_zero(self):
        r = classify(health(['PASS']), sales(), funnel())
        c = r['causes']['E_CONVERSION_UNPROVEN']
        self.assertEqual(c['status'], BLOCKED)
        self.assertEqual(r['governing_rules']['VERIFIED_REVENUE'], 0.0)

    def test_a_real_sale_downgrades_to_hold_and_carries_revenue(self):
        r = classify(health(['PASS']), sales(1, 79.0),
                     funnel(unique_readers=10, product_visits=5, attribution_available=True))
        self.assertEqual(r['causes']['E_CONVERSION_UNPROVEN']['status'], HOLD)
        self.assertEqual(r['governing_rules']['VERIFIED_REVENUE'], 79.0)


class TestTracking(unittest.TestCase):

    def test_no_attribution_is_blocked(self):
        r = classify(health(['PASS']), sales(), funnel())
        self.assertEqual(r['causes']['F_TRACKING_UNRELIABLE']['status'], BLOCKED)

    def test_self_inflation_finding_is_recorded_as_proven(self):
        r = classify(health(['PASS']), sales(), funnel())
        f = r['causes']['F_TRACKING_UNRELIABLE']
        self.assertIn('increments its own view counter by exactly 1', f['proven'])
        self.assertEqual(f['classification'], 'OBSERVED')


class TestRootCauseOrdering(unittest.TestCase):

    def test_payout_is_never_the_root_cause_order_leader(self):
        r = classify(health(['PASS']), sales(), funnel())
        self.assertNotEqual(r['single_root_cause'], 'C_PAYOUT_BLOCKED')

    def test_order_is_deterministic_and_excludes_payout(self):
        r = classify(health(['PASS']), sales(), funnel())
        self.assertEqual(sorted(r['root_cause_order']), sorted(r['root_cause_order']))
        self.assertNotIn('C_PAYOUT_BLOCKED', r['root_cause_order'])
        self.assertIn(r['single_root_cause'], r['root_cause_order'])


if __name__ == '__main__':
    unittest.main()
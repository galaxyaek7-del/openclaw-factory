"""Tests for commercial_health.py.

Fully offline - every network call is injected. The point of these tests is
that the monitor cannot be quietly wrong in the ways the ad-hoc scripts this
replaces were wrong twice:

  1. reporting a number it has no source for as a zero
  2. reporting a purchase as complete when nothing was bought
  3. treating a reachable link as correct without checking which product it hits
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import commercial_health as ch


def prod(**kw):
    d = {'name': 'X', 'published': True, 'price': 7900, 'files': [{'size': 123}]}
    d.update(kw)
    return d


class TestProductHealth(unittest.TestCase):

    def test_healthy_product_passes_but_never_claims_a_purchase(self):
        r = ch.check_product_health(lambda s: prod(), lambda s: 200, 'abc')
        self.assertEqual(r['verdict'], 'PASS')
        self.assertEqual(r['price'], 79.0)
        self.assertEqual(r['files'], 'PASS')
        self.assertEqual(r['checkout'], 'PASS')
        # the critical assertion: a purchase is NEVER reported as done
        self.assertEqual(r['purchase_completion'], ch.UNKNOWN)
        self.assertNotEqual(r['purchase_completion'], 'PASS')
        self.assertIn('not attempted', r['purchase_completion_reason'].lower())

    def test_missing_file_is_blocked_with_a_buyer_harm_note(self):
        r = ch.check_product_health(lambda s: prod(files=[]), lambda s: 200, 'abc')
        self.assertEqual(r['verdict'], 'BLOCKED')
        self.assertEqual(r['files'], 'BLOCKED')
        self.assertTrue(any('NO FILE ATTACHED' in x for x in r['problems']))

    def test_zero_size_file_is_blocked(self):
        r = ch.check_product_health(lambda s: prod(files=[{'size': 0}]), lambda s: 200, 'abc')
        self.assertEqual(r['verdict'], 'BLOCKED')

    def test_dead_checkout_is_blocked_even_if_the_page_is_published(self):
        r = ch.check_product_health(lambda s: prod(), lambda s: 404, 'abc')
        self.assertEqual(r['verdict'], 'BLOCKED')
        self.assertEqual(r['checkout'], 'BLOCKED')
        self.assertEqual(r['page'], 'PASS')   # page and purchase path stay separate

    def test_unpublished_product_is_blocked(self):
        r = ch.check_product_health(lambda s: prod(published=False), lambda s: 200, 'abc')
        self.assertEqual(r['verdict'], 'BLOCKED')

    def test_unreadable_product_record_never_becomes_a_false_pass(self):
        r = ch.check_product_health(lambda s: None, lambda s: 200, 'abc')
        self.assertEqual(r['verdict'], 'BLOCKED')
        self.assertEqual(r['price'], ch.UNKNOWN)
        self.assertEqual(r['files'], ch.UNKNOWN)

    def test_absent_price_reports_unknown_not_zero(self):
        r = ch.check_product_health(lambda s: prod(price=None), lambda s: 200, 'abc')
        self.assertEqual(r['price'], ch.UNKNOWN)


class TestSalesLedger(unittest.TestCase):

    def test_real_sale_is_counted_and_sourced(self):
        r = ch.check_sales_ledger(lambda: {'sales': [{'amount': 7900}, {'amount': 100}]})
        self.assertEqual(r['orders'], 2)
        self.assertEqual(r['verified_revenue_usd'], 80.0)
        self.assertEqual(r['orders_source'], 'Gumroad /v2/sales')

    def test_empty_sales_is_a_sourced_zero_not_unknown(self):
        r = ch.check_sales_ledger(lambda: {'sales': []})
        self.assertEqual(r['orders'], 0)
        self.assertEqual(r['verified_revenue_usd'], 0.0)
        self.assertIn('sourced zero', r['evidence'])

    def test_refunds_and_net_are_unknown_never_guessed(self):
        r = ch.check_sales_ledger(lambda: {'sales': [{'amount': 7900}]})
        self.assertEqual(r['refunds'], ch.UNKNOWN)
        self.assertEqual(r['net_after_refunds'], ch.UNKNOWN)
        self.assertEqual(r['payouts_withdrawn'], ch.UNKNOWN)
        # gross is reported, net is not fabricated from it
        self.assertEqual(r['verified_revenue_usd'], 79.0)

    def test_absent_sales_payload_does_not_silently_report_zero_orders(self):
        r = ch.check_sales_ledger(lambda: {})
        self.assertEqual(r['orders'], 0)
        # and the monitor must not pretend it knows refunds/net in that case
        self.assertEqual(r['refunds'], ch.UNKNOWN)


class TestLinkHealth(unittest.TestCase):

    def test_dead_link_is_blocked_with_a_reason(self):
        links = ['https://aekraft.gumroad.com/l/dead1']
        out = ch.check_link_health(lambda: links, lambda h: 404)
        self.assertEqual(out[0]['status'], 'BLOCKED')
        self.assertIn('dead link', out[0]['reason'])

    def test_live_link_passes_and_extracts_the_slug(self):
        links = ['https://aekraft.gumroad.com/l/good1?utm_source=x']
        out = ch.check_link_health(lambda: links, lambda h: 200)
        self.assertEqual(out[0]['status'], 'PASS')
        self.assertEqual(out[0]['slug'], 'good1')

    def test_duplicates_collapse(self):
        links = ['https://aekraft.gumroad.com/l/x1', 'https://aekraft.gumroad.com/l/x1']
        out = ch.check_link_health(lambda: links, lambda h: 200)
        self.assertEqual(len(out), 1)


class TestReport(unittest.TestCase):

    def test_report_never_claims_a_completed_purchase(self):
        rep = ch.run_health_report(
            fetch_product=lambda s: prod(), fetch_checkout=lambda s: 200,
            fetch_sales=lambda: {'sales': []}, slugs=['a', 'b'])
        joined = str(rep['never_claimed'])
        self.assertIn('a completed purchase', joined)
        self.assertEqual(rep['summary']['verified_revenue_usd'], 0.0)
        self.assertEqual(rep['summary']['products_healthy'], 2)

    def test_report_surfaces_blocked_products_for_human_action(self):
        rep = ch.run_health_report(
            fetch_product=lambda s: prod(files=[]), fetch_checkout=lambda s: 200,
            fetch_sales=lambda: {'sales': []}, slugs=['bad'])
        self.assertEqual(rep['summary']['products_blocked'], 1)
        self.assertEqual(rep['summary']['requires_human_action'], ['bad'])

    def test_links_are_unknown_when_not_supplied_rather_than_assumed_healthy(self):
        rep = ch.run_health_report(
            fetch_product=lambda s: prod(), fetch_checkout=lambda s: 200,
            fetch_sales=lambda: {'sales': []}, slugs=['a'])
        self.assertEqual(rep['links'], ch.UNKNOWN)


if __name__ == '__main__':
    unittest.main()

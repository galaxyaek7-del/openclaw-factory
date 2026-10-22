"""Network-only backoff in scripts/poll_sales.py (2026-10-22).

Only connection/DNS failures are retried; auth, payment and "arm not ready"
errors return after one call. Sleep and clock are injected, so nothing here
waits or touches the network.

    python -m pytest tests/test_sales_poll_network_retry.py -q
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.poll_sales import _get_sales_with_network_retry  # noqa: E402

# The real error text factory_loop.log recorded 1,131 times since 2026-10-15.
DNS_FAIL = ("Gumroad get_sales request failed: HTTPSConnectionPool(host='api.gumroad.com', port=443): "
            "Max retries exceeded with url: /v2/sales (Caused by NameResolutionError(\"<urllib3.connection."
            "HTTPSConnection object>: Failed to resolve 'api.gumroad.com' ([Errno 11001] getaddrinfo failed)\"))")


class FakeClock:
    def __init__(self):
        self.t = 0.0
        self.sleeps = []

    def clock(self):
        return self.t

    def sleep(self, s):
        self.sleeps.append(s)
        self.t += s


def scripted(*results):
    calls = []

    def fn():
        calls.append(1)
        return results[min(len(calls), len(results)) - 1]
    return fn, calls


class TestNetworkRetry(unittest.TestCase):
    def run_retry(self, fn, **kw):
        c = FakeClock()
        out = _get_sales_with_network_retry(fn, sleep=c.sleep, clock=c.clock, **kw)
        return out, c

    def test_network_error_then_success_is_retried(self):
        fn, calls = scripted(([], DNS_FAIL), ([{"id": "s1"}], None))
        (sales, error, attempts), c = self.run_retry(fn)
        self.assertIsNone(error)
        self.assertEqual(sales, [{"id": "s1"}])
        self.assertEqual(attempts, 2)
        self.assertEqual(c.sleeps, [2])

    def test_persistent_outage_gives_up_after_the_delays(self):
        fn, calls = scripted(([], DNS_FAIL))
        (sales, error, attempts), c = self.run_retry(fn)
        self.assertEqual(error, DNS_FAIL)
        self.assertEqual(attempts, 3)
        self.assertEqual(c.sleeps, [2, 4])

    def test_non_network_errors_are_not_retried(self):
        for err in ("arm not ready: unavailable",
                    "Paddle API error 403: You aren't permitted to perform this request.",
                    "Paddle API error 429: Too Many Requests"):
            fn, calls = scripted(([], err))
            (_s, error, attempts), c = self.run_retry(fn)
            self.assertEqual((error, attempts, c.sleeps), (err, 1, []), err)

    def test_budget_stops_retries_when_a_call_was_slow(self):
        c = FakeClock()

        def slow_fail():
            c.t += 9  # one attempt that took 9 s
            return [], DNS_FAIL
        sales, error, attempts = _get_sales_with_network_retry(slow_fail, sleep=c.sleep, clock=c.clock)
        # 9 s + 2 s delay = 11 s fits the 12 s budget; the next try (20 s + 4) does not.
        self.assertEqual(attempts, 2)
        self.assertEqual(c.sleeps, [2])


if __name__ == "__main__":
    unittest.main()

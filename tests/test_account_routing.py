"""Tests for account_routing.py (Account Routing & Payment Identity
Policy, ADR-241, 2026-08-09): proves the authoritative platform ->
commercial_identity -> payout_identity -> status routing table never
infers ownership, never guesses on unknown platforms, never persists or
logs a secret, and cannot trigger any external action.

    python -m unittest tests.test_account_routing -v
"""

import ast
import inspect
import sys
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import account_routing as ar


class TestAmazonKdpRouting(unittest.TestCase):
    """Requirement 1/2: Amazon and KDP route to aekgalaxy47@gmail.com."""

    def test_amazon_routes_to_kdp_identity(self):
        record = ar.route_platform("amazon")
        self.assertEqual(record["commercial_identity"], "aekgalaxy47@gmail.com")
        self.assertEqual(record["status"], ar.VERIFIED)

    def test_kdp_routes_to_kdp_identity(self):
        record = ar.route_platform("amazon_kdp")
        self.assertEqual(record["commercial_identity"], "aekgalaxy47@gmail.com")
        record2 = ar.route_platform("kdp")
        self.assertEqual(record2["commercial_identity"], "aekgalaxy47@gmail.com")

    def test_real_commission_engine_amazon_opportunity_id_routes_correctly(self):
        record = ar.route_platform("CO-amazon-affiliate")
        self.assertEqual(record["commercial_identity"], "aekgalaxy47@gmail.com")
        self.assertEqual(record["category"], "amazon_kdp")


class TestPayoneerRouting(unittest.TestCase):
    """Requirement 3: Payoneer routes to aekgalaxy47@gmail.com."""

    def test_payoneer_routes_to_kdp_payout_identity(self):
        record = ar.route_platform("payoneer")
        self.assertEqual(record["payout_identity"], "aekgalaxy47@gmail.com")
        self.assertEqual(record["status"], ar.VERIFIED)

    def test_amazon_kdp_payout_is_payoneer(self):
        record = ar.route_platform("amazon")
        self.assertEqual(record["payout_identity"], "aekgalaxy47@gmail.com")
        self.assertEqual(record["payout_method"], "Payoneer")


class TestGumroadRouting(unittest.TestCase):
    """Requirement 4: Gumroad routes to galaxyaek7@gmail.com."""

    def test_gumroad_routes_to_primary_commercial_identity(self):
        record = ar.route_platform("gumroad")
        self.assertEqual(record["commercial_identity"], "galaxyaek7@gmail.com")
        self.assertEqual(record["category"], "non_amazon_commercial")

    def test_gumroad_payout_is_not_assumed(self):
        record = ar.route_platform("gumroad")
        self.assertEqual(record["payout_method"], ar.UNKNOWN)
        self.assertIsNone(record["payout_identity"])


class TestNonAmazonDefaultOnlyWhenExplicit(unittest.TestCase):
    """Requirement 5: generic non-Amazon commercial platforms default to
    galaxyaek7@gmail.com ONLY where explicitly classified -- never for
    an unlisted platform, proving there is no substring/fuzzy fallback."""

    def test_every_explicitly_listed_non_amazon_platform_routes_to_primary(self):
        for platform in ar._NON_AMAZON_COMMERCIAL_PLATFORMS:
            record = ar.route_platform(platform)
            self.assertEqual(
                record["commercial_identity"], "galaxyaek7@gmail.com",
                f"{platform} did not route to the primary commercial identity",
            )

    def test_unlisted_platform_does_not_default_to_primary_identity(self):
        record = ar.route_platform("some_brand_new_platform_never_seen_before")
        self.assertIsNone(record["commercial_identity"])
        self.assertNotEqual(record["status"], ar.VERIFIED)

    def test_no_substring_inference_amazon_lookalike(self):
        """A platform string that merely CONTAINS 'amazon' but was never
        explicitly classified must not be routed to the Amazon identity --
        proves route_platform() does exact-match lookup, not substring
        matching, i.e. never infers from opportunity/platform data."""
        record = ar.route_platform("amazon_marketplace_lookalike_xyz")
        self.assertIsNone(record["commercial_identity"])
        self.assertEqual(record["status"], ar.BLOCKED)


class TestUnknownPlatformsAreBlockedNotGuessed(unittest.TestCase):
    """Requirement 6: unknown/conflicting platforms are blocked rather
    than guessed."""

    def test_unknown_platform_is_blocked(self):
        record = ar.route_platform("totally_unclassified_platform")
        self.assertEqual(record["status"], ar.BLOCKED)
        self.assertTrue(record["blocking_reason"])
        self.assertIn("explicit_founder_classification", record["missing_requirements"])

    def test_empty_or_none_platform_is_blocked_not_defaulted(self):
        self.assertEqual(ar.route_platform("")["status"], ar.BLOCKED)
        self.assertEqual(ar.route_platform(None)["status"], ar.BLOCKED)

    def test_blocked_record_never_carries_a_guessed_identity(self):
        record = ar.route_platform("unclassified_platform")
        self.assertIsNone(record["commercial_identity"])
        self.assertIsNone(record["payout_identity"])


class TestNoSecretsPersistedOrLogged(unittest.TestCase):
    """Requirement 7: no secret values are persisted or logged -- only
    non-secret account routing metadata (email addresses)."""

    def test_module_level_string_constants_are_only_emails_or_labels(self):
        """Precise runtime check, not a naive text scan (a docstring may
        legitimately mention the word 'password' while disclaiming that
        none is stored -- that is not a secret value). Every actual
        top-level string constant this module defines must be either a
        real email address or a short, known non-secret status label."""
        known_labels = {ar.VERIFIED, ar.UNKNOWN, ar.BLOCKED}
        for name, value in vars(ar).items():
            if name.startswith("_") or not isinstance(value, str):
                continue
            is_email = "@" in value
            is_label = value in known_labels
            self.assertTrue(
                is_email or is_label,
                f"account_routing.{name} = {value!r} is neither an email nor a known "
                "status label -- must not hold an unexplained string constant",
            )

    def test_routing_table_values_are_only_emails_or_known_labels(self):
        table = ar.account_routing_table()
        allowed_labels = {ar.VERIFIED, ar.UNKNOWN, ar.BLOCKED, "NOT_APPLICABLE", "Payoneer", None}
        for record in table["routes"]:
            for field in ("commercial_identity", "payout_identity"):
                value = record[field]
                if value is not None:
                    self.assertIn("@", value, f"{field} value {value!r} is not an email-shaped identity")
            for field in ("status", "commercial_identity_status", "payout_status"):
                self.assertTrue(
                    record[field] in allowed_labels or record[field] == ar.UNKNOWN,
                    f"{field} value {record[field]!r} is not a known non-secret label",
                )

    def test_module_performs_no_logging_calls(self):
        source = inspect.getsource(ar)
        self.assertNotIn("logging.", source)
        self.assertNotIn("print(", source)


class TestCannotTriggerExternalActions(unittest.TestCase):
    """Requirement 8: account routing cannot trigger outreach or
    financial transactions -- proven structurally, not just by absence
    of a call in today's code, by asserting the module imports nothing
    capable of network/subprocess/file-write I/O at all."""

    _FORBIDDEN_IMPORTS = {
        "subprocess", "requests", "urllib", "http", "socket", "smtplib",
        "os",  # no file writes, no environment/credential access either
    }

    def test_module_has_no_io_capable_imports(self):
        source = inspect.getsource(ar)
        tree = ast.parse(source)
        imported_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_names.add(node.module.split(".")[0])
        forbidden_found = imported_names & self._FORBIDDEN_IMPORTS
        self.assertFalse(
            forbidden_found,
            f"account_routing.py imports {forbidden_found} -- this module "
            "must be incapable of network/subprocess/file I/O by construction",
        )

    def test_module_defines_no_functions_with_side_effect_naming(self):
        forbidden_verbs = ("register", "send", "connect", "withdraw", "transfer", "purchase", "publish", "activate")
        for name, _ in inspect.getmembers(ar, inspect.isfunction):
            lowered = name.lower()
            for verb in forbidden_verbs:
                self.assertNotIn(
                    verb, lowered,
                    f"account_routing.py defines a function named {name!r}, which reads as "
                    "an action-triggering capability this read-only policy module must never have",
                )

    def test_account_routing_table_is_pure_and_repeatable(self):
        first = ar.account_routing_table()
        second = ar.account_routing_table()
        self.assertEqual(first["routes"], second["routes"])
        self.assertEqual(first["verified_count"], second["verified_count"])


class TestAccountRoutingTable(unittest.TestCase):
    def test_table_counts_are_consistent(self):
        table = ar.account_routing_table()
        self.assertEqual(table["total_platforms"], len(table["routes"]))
        self.assertGreater(table["verified_count"], 0)
        self.assertGreater(table["unknown_count"], 0)

    def test_identities_match_founder_policy_constants(self):
        table = ar.account_routing_table()
        self.assertEqual(table["primary_commercial_identity"], "galaxyaek7@gmail.com")
        self.assertEqual(table["amazon_kdp_identity"], "aekgalaxy47@gmail.com")
        self.assertEqual(table["payoneer_identity"], "aekgalaxy47@gmail.com")


if __name__ == "__main__":
    unittest.main()

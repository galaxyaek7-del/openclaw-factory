"""Cycle 81 tests — product_claim_integrity.py and its distributor wiring.

Every product name, price, byte count, page count and word count used here is
a real, live value read from the actual Gumroad account on 2026-10-14. The
descriptions are the real published copy, not paraphrases. The fixtures are
therefore regression evidence: if the catalog genuinely changes, these tests
are supposed to fail.

Naming: matches CI group pattern "test_[c-d]*.py" exactly once.

Run:  python -m unittest discover -s tests -p "test_cycle81.py" -v
"""

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import distributor
import product_claim_integrity as pci
from channels import registry
from schemas.product import Product

_REAL_TEXT = _FACTORY_ROOT / "data" / "cycle81_real_listing_text.json"


def _real_description(short_id, fallback=""):
    """The live published copy, read from the snapshot this cycle captured.
    Falls back to a caller-supplied string when the snapshot is absent (a
    clean CI checkout still has it committed; a partial tree must not make
    the suite error out for an unrelated reason)."""
    try:
        with io.open(_REAL_TEXT, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return fallback
    for row in data:
        if row.get("short_id") == short_id:
            return row.get("description") or fallback
    return fallback


class TestVerdictVocabulary(unittest.TestCase):
    """UNKNOWN must stay distinguishable from PASS. Collapsing them is how a
    gate silently stops meaning anything."""

    def test_four_distinct_verdicts(self):
        self.assertEqual(
            sorted([pci.PASS, pci.BLOCK, pci.REVIEW, pci.UNKNOWN]),
            ["BLOCK", "PASS", "REVIEW", "UNKNOWN"])

    def test_uninspected_payload_is_unknown_not_pass(self):
        r = pci.check_claim_integrity(
            "Anything", "Anything at all", payloads=None, price_usd=99.0)
        self.assertEqual(r["verdict"], pci.UNKNOWN)
        self.assertEqual(r["blocking_findings"], [])

    def test_unknown_never_blocks_even_for_a_real_data_claim(self):
        r = pci.check_claim_integrity(
            "Lead Lists", _real_description(
                "drtaj", "Delivery as CSV and Google Sheets within 6 days."),
            payloads=None, price_usd=99.0)
        self.assertEqual(r["verdict"], pci.UNKNOWN)
        self.assertEqual(r["blocking_findings"], [])


class TestTheOneRealFalseClaim(unittest.TestCase):
    """Verified live 2026-10-14. This is the single unambiguous case: the copy
    promises a CSV/Sheets dataset of 200 leads and the attachment is a
    1-page, 81-word PDF that only describes it."""

    def test_verified_b2b_lead_lists_99_usd(self):
        r = pci.check_claim_integrity(
            title="Verified B2B Lead Lists (200-lead batch)",
            description=_real_description("drtaj", ""),
            payloads=[{"name": "leads.pdf", "bytes": 2008, "filetype": "pdf"}],
            price_usd=99.0, page_count=1, word_count=81,
        )
        self.assertEqual(r["verdict"], pci.BLOCK, r)
        rules = {f["rule"] for f in r["blocking_findings"]}
        self.assertIn("CLAIMED_DATA_NOT_DELIVERED", rules)
        # The copy says "Delivery as CSV and Google Sheets", so the attachment
        # also only describes the deliverable rather than being it.
        self.assertIn("ATTACHMENT_DESCRIBES_RATHER_THAN_DELIVERS", rules)

    def test_priced_with_no_attachment_at_all(self):
        r = pci.check_claim_integrity(
            title="Some Kit", description="A kit.", payloads=[], price_usd=59.0)
        self.assertEqual(r["verdict"], pci.BLOCK)
        self.assertIn("PRICED_BUT_NO_PAYLOAD",
                      {f["rule"] for f in r["blocking_findings"]})


class TestRealListingsThatMustNotBeFalselyFlagged(unittest.TestCase):
    """The correction that matters most. A first draft of this gate matched
    a wide vocabulary including "templates"/"workbook"/"tracker" and flagged
    9 live listings; reading their actual copy proved 8 were false positives,
    and it falsely flagged the $155 flagship for the word "templates".

    Every case below is real live copy with its real measured payload. They
    must never be BLOCKed."""

    def test_five_boilerplate_kit_listings_are_not_false_claims(self):
        """All five say "A single, focused file you download and use
        immediately" -- and they do deliver that file. Only their TITLES carry
        a word like Workbook/Calculator/Kit. Thin, yes; false, no."""
        cases = [
            ("wteork", "Amazon FBA Reconciliation Workbook", 49.0, 3726, 331),
            ("ciowwm", "EU Late Payment Recovery Kit", 59.0, 3863, 392),
            ("ldrdm", "Food-Contact Materials Starter", 39.0, 2720, 272),
            ("hasjmp", "Etsy Ads ROI Playbook + Calculator", 39.0, 3000, 300),
            ("zjwpx", "Freelancer Scope-Creep Contract Kit", 29.0, 2530, 253),
        ]
        for sid, name, price, size, words in cases:
            with self.subTest(sid=sid):
                r = pci.check_claim_integrity(
                    title=name,
                    description=_real_description(sid, "What you get: - A single, focused file you download and use immediately"),
                    payloads=[{"name": name.split()[0].lower() + ".pdf",
                               "bytes": size, "filetype": "pdf"}],
                    price_usd=price, page_count=1, word_count=words,
                )
                self.assertNotEqual(
                    r["verdict"], pci.BLOCK,
                    "%s must not be blocked: %s" % (sid, r))

    def test_eu_ai_act_toolkit_155_usd_flagship(self):
        """The word "templates" in a PDF product's subtitle is not a data
        claim. The first draft blocked this listing; that was wrong."""
        r = pci.check_claim_integrity(
            title="EU AI Act Compliance Toolkit",
            description="Practical templates and implementation guide for SMEs.",
            payloads=[{"name": "preview.pdf", "bytes": 106314, "filetype": "pdf"},
                      {"name": "toolkit.pdf", "bytes": 139401, "filetype": "pdf"}],
            price_usd=155.0, page_count=31,
        )
        self.assertNotEqual(r["verdict"], pci.BLOCK, r)

    def test_automated_contract_review_327_usd_17_pages(self):
        r = pci.check_claim_integrity(
            title="Automated Contract Review System for Legal Departments",
            description="A 17-page implementation guide for AI contract review.",
            payloads=[{"name": "contract_review.pdf", "bytes": 118012,
                       "filetype": "pdf"}],
            price_usd=327.0, page_count=17, word_count=2924,
        )
        self.assertNotEqual(r["verdict"], pci.BLOCK, r)

    def test_gcc_bundle_399_usd_real_zip_with_xlsx_inside(self):
        """Real ZIP contents: gcc_payment_command_workbook_v2.xlsx, manual,
        templates, checklist. A "workbook" inside a zip IS delivered."""
        r = pci.check_claim_integrity(
            title="GCC Contractor Payment Command System (V2 Bundle)",
            description="Workbook, manual, bilingual templates and checklist.",
            payloads=[{"name": "gcc_v2_bundle.zip", "bytes": 17106,
                       "entries": ["gcc_payment_command_workbook_v2.xlsx",
                                   "gcc_payment_command_manual_v2.pdf",
                                   "gcc_templates_ar_en_v2.pdf",
                                   "gcc_implementation_checklist_v2.pdf"]}],
            price_usd=399.0,
        )
        # REVIEW, not PASS: a 17KB payload at $399 genuinely deserves a human
        # look. What must never happen is a BLOCK -- the workbook IS delivered.
        self.assertEqual(r["verdict"], pci.REVIEW, r)
        self.assertEqual(r["blocking_findings"], [])
        self.assertIn("THIN_FOR_PRICE",
                      {f["rule"] for f in r["advisory_findings"]})


class TestNoFalsePositives(unittest.TestCase):
    def test_unopened_archive_is_review_not_block(self):
        """A ZIP may legitimately contain the CSV we cannot see."""
        r = pci.check_claim_integrity(
            title="Lead Lists Bundle",
            description="Delivery as CSV, inside the bundle.",
            payloads=[{"name": "bundle.zip", "bytes": 17106}],
            price_usd=99.0)
        self.assertEqual(r["verdict"], pci.REVIEW, r)
        self.assertEqual(r["blocking_findings"], [])

    def test_word_substring_does_not_trip_the_gate(self):
        """"misleads" contains "leads". The first draft's substring matching
        blocked this innocent listing."""
        r = pci.check_claim_integrity(
            title="Copywriting Guide",
            description="This guide never misleads the reader.",
            payloads=[{"name": "g.pdf", "bytes": 900000, "filetype": "pdf"}],
            price_usd=19.0)
        self.assertEqual(r["verdict"], pci.PASS, r)

    def test_free_listing_with_no_file_is_not_a_block(self):
        r = pci.check_claim_integrity(
            title="Free Guide", description="A free guide.",
            payloads=[], price_usd=0.0)
        self.assertNotEqual(r["verdict"], pci.BLOCK, r)

    def test_thin_payload_is_advisory_not_a_block(self):
        """Thin-for-price is a pricing question, not a false statement, and
        this factory must not confuse the two."""
        r = pci.check_claim_integrity(
            title="Section 8 Notice Validity System (England)",
            description="A focused guide.",
            payloads=[{"name": "s8.pdf", "bytes": 13669, "filetype": "pdf"}],
            price_usd=99.0)
        self.assertEqual(r["verdict"], pci.REVIEW, r)
        self.assertEqual(r["blocking_findings"], [])
        self.assertIn("THIN_FOR_PRICE",
                      {f["rule"] for f in r["advisory_findings"]})

    def test_ada_kit_citing_research_datasets_is_not_a_data_claim(self):
        """https://aekraft.gumroad.com/l/palmdr — the second real false
        positive this cycle caught. The live copy says "Built from Seyfarth
        Shaw counts, UsableNet/EcomBack datasets". That cites the AUTHOR's
        research sources; it does not promise the buyer a dataset. A rule that
        cannot tell those apart will eventually block a good product."""
        desc = (
            "An ADA demand-letter response and triage system with decision "
            "math, a prevention cadence, and FAQ. Built from Seyfarth Shaw "
            "counts, UsableNet/EcomBack datasets, the CCDA California report, "
            "and 2026 enforcement coverage, checked September 2026. First "
            "draft included for reference only.")
        r = pci.check_claim_integrity(
            title="ADA Demand-Letter Response & Triage Kit",
            description=desc,
            payloads=[{"name": "ada.pdf", "bytes": 9588, "filetype": "pdf"}],
            price_usd=69.0, page_count=3, word_count=700,
        )
        self.assertNotEqual(r["verdict"], pci.BLOCK, r)

    def test_a_data_word_near_a_delivery_phrase_still_blocks(self):
        """The proximity rule must not simply switch the check off."""
        r = pci.check_claim_integrity(
            title="Leads Pack",
            description="What you get: 200 verified leads as a CSV, "
                        "deduped against the base list you supply.",
            payloads=[{"name": "pack.pdf", "bytes": 4000, "filetype": "pdf"}],
            price_usd=99.0, page_count=1, word_count=90)
        self.assertEqual(r["verdict"], pci.BLOCK, r)

    def test_thin_payload_below_the_advisory_floor_is_a_pass(self):
        """The advisory floor is disclosed, not arbitrary: below it a small
        file is normal for the price and firing would be noise."""
        r = pci.check_claim_integrity(
            title="Freelancer Scope-Creep Contract Kit",
            description="A focused guide.",
            payloads=[{"name": "k.pdf", "bytes": 2530, "filetype": "pdf"}],
            price_usd=29.0)
        self.assertEqual(r["verdict"], pci.PASS, r)

    def test_missing_size_does_not_crash(self):
        r = pci.check_claim_integrity(
            title="Kit", description="Desc",
            payloads=[{"name": "k.pdf"}], price_usd=19.0)
        self.assertIn(r["verdict"], (pci.PASS, pci.REVIEW, pci.BLOCK))


class TestDescribePayloads(unittest.TestCase):
    def test_gumroad_api_field_names(self):
        out = pci.describe_payloads([
            {"file_name": "a.csv", "size": "100", "filetype": "text/csv"},
            {"name": "b.pdf", "size": 200, "filetype": "application/pdf"},
            {"name": "c.zip", "size": 300, "filetype": "application/zip"},
        ])
        self.assertEqual([p["kind"] for p in out], ["data", "document", "archive"])
        self.assertEqual(out[0]["bytes"], 100)

    def test_tuple_pairs(self):
        self.assertEqual(pci.describe_payloads([("a.xlsx", 10)])[0]["kind"], "data")

    def test_none_stays_none(self):
        self.assertIsNone(pci.describe_payloads(None))


# ── distributor wiring ──────────────────────────────────────────────────────

def _fake_arm(name="gumroad"):
    from channels.base_arm import BaseArm, ArmStatus, PublishResult

    class _Arm(BaseArm):
        def status(self):
            return ArmStatus.READY

        def supports(self, product):
            return True

        def publish(self, product, dry_run=True):
            return PublishResult(ok=True, platform=name, product_id="p1",
                                 url="http://x", error=None, dry_run=dry_run)

    a = _Arm()
    a.name = name
    return a


def _product(title="t", description="d", price_usd=19.0,
             file_path="/fake/path.pdf"):
    return Product(title=title, subtitle="", description=description,
                   price_usd=price_usd, file_path=file_path, cover_path=None,
                   tags=[], language="ar", source_id="PROD-cycle81",
                   raw_price_hint=price_usd, needs_pricing=False,
                   price_source="profit_raw")


def _temp_file(suffix, payload):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.write(fd, payload)
    os.close(fd)
    return path


import os as _gf_os  # noqa: E402  (2026-10-22 live-path opt-in)
from unittest import mock as _gf_mock  # noqa: E402
_gf_patch = _gf_mock.patch


# 2026-10-22: exercises the mocked live distribution path; distributor.py
# and channels/write_gate.py fail closed by default, so it opts in explicitly.
@_gf_patch.dict(_gf_os.environ, {"FACTORY_LIVE_PUBLISH": "true"})
class TestDistributorWiring(unittest.TestCase):
    def setUp(self):
        self._saved = registry.all_arms()
        registry.clear()
        fd, self.ledger = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        os.remove(self.ledger)
        fd, self.state = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(self.state)

    def tearDown(self):
        registry.clear()
        for a in self._saved:
            registry.register(a)
        for p in (self.ledger, self.state):
            if os.path.exists(p):
                os.remove(p)

    def test_dry_run_is_never_gated(self):
        """Dry runs touch no real platform, so they stay untouched -- the same
        exemption publish_protection uses."""
        registry.register(_fake_arm())
        p = _product(title="Lead Lists",
                     description="Delivery as CSV and Google Sheets.",
                     price_usd=99.0)
        outcomes = distributor.distribute(
            p, arm_names=["gumroad"], dry_run=True,
            ledger_path=self.ledger, protection_state_path=self.state)
        self.assertEqual(outcomes[0]["attempted"], True)

    def test_real_publish_of_an_uninspectable_product_still_runs(self):
        """The file is not on disk -> payload UNKNOWN -> must NOT block. This
        is the regression that matters most: a gate that blocks on absent
        evidence would break every real publish whose source file lives
        elsewhere."""
        registry.register(_fake_arm())
        p = _product(title="Lead Lists",
                     description="Delivery as CSV and Google Sheets.",
                     price_usd=99.0, file_path="/definitely/not/here.pdf")
        outcomes = distributor.distribute(
            p, arm_names=["gumroad"], dry_run=False, allow_protected=True,
            ledger_path=self.ledger, protection_state_path=self.state)
        self.assertEqual(outcomes[0]["attempted"], True, outcomes[0])

    def test_real_publish_with_a_real_contradicting_pdf_is_blocked(self):
        """The live defect shape, end to end: a real file on disk, a data claim
        in the real copy, a PDF shipped."""
        pdf = _temp_file(".pdf", b"%PDF-1.4\n" + b"0" * 4000)
        try:
            registry.register(_fake_arm())
            p = _product(title="Verified B2B Lead Lists (200-lead batch)",
                         description=_real_description(
                             "drtaj", "Delivery as CSV and Google Sheets."),
                         price_usd=99.0, file_path=pdf)
            outcomes = distributor.distribute(
                p, arm_names=["gumroad"], dry_run=False, allow_protected=True,
                ledger_path=self.ledger, protection_state_path=self.state)
            self.assertEqual(outcomes[0]["attempted"], False)
            self.assertIn("claim-integrity gate", outcomes[0]["skip_reason"])
        finally:
            os.remove(pdf)

    def test_allow_claim_risk_is_an_explicit_override(self):
        pdf = _temp_file(".pdf", b"%PDF-1.4\n" + b"0" * 4000)
        try:
            registry.register(_fake_arm())
            p = _product(title="Verified B2B Lead Lists (200-lead batch)",
                         description=_real_description(
                             "drtaj", "Delivery as CSV and Google Sheets."),
                         price_usd=99.0, file_path=pdf)
            outcomes = distributor.distribute(
                p, arm_names=["gumroad"], dry_run=False, allow_protected=True,
                allow_claim_risk=True, ledger_path=self.ledger,
                protection_state_path=self.state)
            self.assertEqual(outcomes[0]["attempted"], True)
        finally:
            os.remove(pdf)

    def test_a_real_csv_publish_is_never_blocked(self):
        csv = _temp_file(".csv", b"name,email\n" + b"a,b\n" * 500)
        try:
            registry.register(_fake_arm())
            p = _product(title="Verified B2B Lead Lists",
                         description="Delivery as CSV and Google Sheets.",
                         price_usd=99.0, file_path=csv)
            outcomes = distributor.distribute(
                p, arm_names=["gumroad"], dry_run=False, allow_protected=True,
                ledger_path=self.ledger, protection_state_path=self.state)
            self.assertEqual(outcomes[0]["attempted"], True, outcomes[0])
        finally:
            os.remove(csv)

    def test_a_legitimate_pdf_product_is_never_blocked(self):
        """Regression guard for the false-positive class that the first draft
        of this gate produced on 8 real listings plus the flagship."""
        pdf = _temp_file(".pdf", b"%PDF-1.4\n" + b"0" * 120000)
        try:
            registry.register(_fake_arm())
            p = _product(
                title="EU AI Act Compliance Toolkit",
                description="Practical templates and implementation guide for SMEs.",
                price_usd=155.0, file_path=pdf)
            outcomes = distributor.distribute(
                p, arm_names=["gumroad"], dry_run=False, allow_protected=True,
                ledger_path=self.ledger, protection_state_path=self.state)
            self.assertEqual(outcomes[0]["attempted"], True, outcomes[0])
        finally:
            os.remove(pdf)


if __name__ == "__main__":
    unittest.main(verbosity=2)
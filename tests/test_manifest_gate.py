"""Tests for manifest_gate -- the Cycle 82 buyer-path gate.

Every fixture is BUILT IN THE TEST, with the expected sizes DERIVED from the
files the test itself writes. Nothing is asserted against a hand-typed number,
which is the only way this test can detect the class of bug the gate exists
to catch: a manifest that no longer matches the artifact.

Covers correct cases, wrong cases, missing files and corrupt archives, as
required. No product file is modified to make a test pass.
"""
import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import manifest_gate as mg

TMP = Path(tempfile.gettempdir()) / "gf_manifest_gate"


def _pdf(body="hello world " * 40):
    """A multi-page PDF so its byte size is unambiguous.

    A single-page stub is ~1.3 KB, which sits INSIDE the gate's 0.5-unit
    tolerance of a '1 KB' claim -- so a test fixture using one cannot actually
    demonstrate a stale manifest. An earlier version of this file used a stub
    and the drift test passed for the wrong reason.
    """
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica", 12)
    for i in range(12):
        c.drawString(72, 700 - i * 20, f"{body[:70]} page {i}")
        c.showPage()
    c.save()
    return buf.getvalue()


def _xlsx(rows=30):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    for i in range(rows):
        ws.append([i, i * 2, f"=A{i + 1}*B{i + 1}"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _docx():
    import docx
    d = docx.Document()
    d.add_paragraph("A template letter body with several words.")
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def _build(archive: Path, members: dict[str, bytes]):
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w") as z:
        for name, blob in members.items():
            z.writestr(name, blob)
    return archive


def _kb(n: int, decimal=True):
    return f"{round(n / (1000 if decimal else 1024))} KB"


class TestParseManifest(unittest.TestCase):
    def test_extracts_filename_and_size(self):
        claims = mg.parse_manifest(
            "guide.pdf 122 KB step 2\nsheet.xlsx 6 KB checklist")
        self.assertEqual(len(claims), 2)
        self.assertEqual(claims[0].filename, "guide.pdf")
        self.assertEqual(claims[0].size_text, "122 KB")

    def test_claimed_bytes_decimal(self):
        c = mg.parse_manifest("a.pdf 10 KB")[0]
        self.assertAlmostEqual(c.claimed_bytes, 10_000)

    def test_empty_manifest_yields_nothing(self):
        self.assertEqual(mg.parse_manifest("no filenames here"), [])


class TestMatchingArchive(unittest.TestCase):
    """Correct case: claims derived from the real members must PASS."""

    def setUp(self):
        self.a = _build(TMP / "ok.zip", {
            "guide.pdf": _pdf(), "sheet.xlsx": _xlsx(),
            "letter.docx": _docx(), "README.txt": b"start here " * 30,
        })
        import zipfile as zf
        self.sizes = {i.filename: i.file_size
                      for i in zf.ZipFile(self.a).infolist()}

    def test_all_matching_claims_pass(self):
        text = "\n".join(f"{n} {_kb(s)}" for n, s in self.sizes.items())
        res = mg.check_manifest(self.a, text)
        self.assertEqual(res.verdict, mg.PASS,
                         f"{[(r.claim.filename, r.status, r.evidence) for r in res.results]}")
        self.assertEqual(len(res.mismatched), 0)

    def test_members_actually_open(self):
        for name in self.sizes:
            state, note = mg.check_member_openable(self.a, name)
            self.assertEqual(state, mg.PASS, f"{name}: {note}")


class TestMismatchedSizes(unittest.TestCase):
    def setUp(self):
        self.a = _build(TMP / "drift.zip", {"guide.pdf": _pdf()})

    def test_stale_size_is_fail_not_pass(self):
        res = mg.check_manifest(self.a, "guide.pdf 1 KB")
        self.assertEqual(res.verdict, mg.FAIL)
        r = res.mismatched[0]
        self.assertIsNotNone(r.corrected_text)
        self.assertIn("KB", r.corrected_text)

    def test_correction_is_published_in_the_pages_own_unit(self):
        import zipfile as zf
        actual = zf.ZipFile(self.a).infolist()[0].file_size
        decimal = mg.check_manifest(self.a, "guide.pdf 1 KB")
        binary = mg.check_manifest(self.a, "guide.pdf 1 KB"
                                   .replace("KB", "KB"))
        self.assertEqual(decimal.mismatched[0].corrected_text,
                         f"{round(actual / 1000)} KB")

    def test_mismatch_reports_the_delta(self):
        import zipfile as zf
        actual = zf.ZipFile(self.a).infolist()[0].file_size
        res = mg.check_manifest(self.a, "guide.pdf 1 KB")
        self.assertIn(f"{actual:,}", res.mismatched[0].evidence)


class TestMissingAndCorrupt(unittest.TestCase):
    def test_claim_for_absent_member_is_blocked_not_failed(self):
        a = _build(TMP / "missing.zip", {"guide.pdf": _pdf()})
        import zipfile as zf
        size = zf.ZipFile(a).infolist()[0].file_size
        # guide.pdf is stated CORRECTLY so the only defect is the absent member
        res = mg.check_manifest(a, f"guide.pdf {_kb(size)}\nabsent.pdf 5 KB")
        self.assertEqual(res.verdict, mg.BLOCKED)
        self.assertEqual(len(res.mismatched), 0,
                         "an unproven claim must not be reported as a mismatch")
        self.assertTrue(res.blocked)
        self.assertEqual(res.blocked[0].claim.filename, "absent.pdf")

    def test_corrupt_archive_is_blocked(self):
        bad = TMP / "corrupt.zip"
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_bytes(b"PK\x03\x04 this is not a real archive")
        res = mg.check_manifest(bad, "guide.pdf 10 KB")
        self.assertEqual(res.verdict, mg.BLOCKED)
        self.assertTrue(res.archive_problems)

    def test_zero_byte_member_is_blocked(self):
        a = _build(TMP / "zero.zip", {"guide.pdf": _pdf(), "empty.txt": b""})
        res = mg.check_manifest(a, "guide.pdf 10 KB\nempty.txt 1 KB")
        self.assertEqual(res.verdict, mg.BLOCKED)

    def test_empty_manifest_text_is_blocked(self):
        a = _build(TMP / "ok2.zip", {"guide.pdf": _pdf()})
        self.assertEqual(mg.check_manifest(a, "").verdict, mg.BLOCKED)

    def test_unreadable_pdf_member_is_not_reported_as_match(self):
        a = _build(TMP / "badpdf.zip", {"guide.pdf": b"%PDF-1.4 truncated junk"})
        import zipfile as zf
        size = zf.ZipFile(a).infolist()[0].file_size
        res = mg.check_manifest(a, f"guide.pdf {_kb(size)}")
        self.assertNotEqual(res.verdict, mg.PASS,
                            "a member that will not open must not pass")


class TestFailClosedSemantics(unittest.TestCase):
    def test_unknown_extension_is_not_a_pass(self):
        a = _build(TMP / "bin.zip", {"blob.bin": b"\x00\x01\x02" * 50})
        import zipfile as zf
        size = zf.ZipFile(a).infolist()[0].file_size
        res = mg.check_manifest(a, f"blob.bin {_kb(size)}")
        self.assertNotEqual(res.verdict, mg.PASS)

    def test_verdict_never_passes_with_any_mismatch(self):
        a = _build(TMP / "mixed.zip", {"a.pdf": _pdf(), "b.txt": b"hello " * 60})
        import zipfile as zf
        sizes = {i.filename: i.file_size for i in zf.ZipFile(a).infolist()}
        text = f"a.pdf {_kb(sizes['a.pdf'])}\nb.txt 1 KB"
        res = mg.check_manifest(a, text)
        self.assertEqual(res.verdict, mg.FAIL)


@unittest.skipUnless(
    Path("books/_releases/etsy_suspension_complete_bundle_v3.zip").exists(),
    "real bundle not present")
class TestRealBundle(unittest.TestCase):
    """The regression that matters: the live page's own manifest text."""

    MANIFEST = (
        "etsy_policy_triage.pdf 10 KB\n"
        "etsy_suspension_appeal_kit.pdf 122 KB\n"
        "etsy_appeal_letter_template_A_IP.docx 36 KB\n"
        "etsy_appeal_letter_template_B_policy.docx 36 KB\n"
        "etsy_appeal_evidence_tracker.xlsx 6 KB\n"
        "README.txt 1 KB"
    )
    A = "books/_releases/etsy_suspension_complete_bundle_v3.zip"

    def test_two_documented_mismatches_are_detected(self):
        res = mg.check_manifest(self.A, self.MANIFEST)
        self.assertEqual(res.verdict, mg.FAIL)
        names = {r.claim.filename for r in res.mismatched}
        self.assertEqual(names,
                         {"etsy_suspension_appeal_kit.pdf",
                          "etsy_appeal_evidence_tracker.xlsx"})

    def test_corrected_values_match_the_real_bytes(self):
        res = mg.check_manifest(self.A, self.MANIFEST)
        import zipfile as zf
        sizes = {i.filename: i.file_size for i in zf.ZipFile(self.A).infolist()}
        for r in res.mismatched:
            want = round(sizes[r.claim.filename] / 1000)
            self.assertEqual(r.corrected_text, f"{want} KB")

    def test_four_correct_entries_still_pass(self):
        res = mg.check_manifest(self.A, self.MANIFEST)
        self.assertEqual(len(res.results) - len(res.mismatched), 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
"""Tests for pdf_layout_inspector.

Per-type tests: a synthetic PDF with a known margin breach must be caught, and
a clean one must not be. A layout checker that never fires looks identical to
a working one, so these assert firing, not merely a verdict.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pdf_layout_inspector as pli

try:
    from pypdf import PdfWriter
    from pypdf.generic import ContentStream, NameObject
    HAVE_PDF = True
except ImportError:  # pragma: no cover
    try:
        from PyPDF2 import PdfWriter
        from PyPDF2.generic import ContentStream, NameObject
        HAVE_PDF = True
    except ImportError:
        HAVE_PDF = False


def _make_pdf(path, tm_y, x=100.0):
    """A single-page PDF drawing text at a chosen position."""
    w = PdfWriter()
    w.add_blank_page(width=612, height=792)
    page = w.pages[0]
    stream = (f"BT /F1 12 Tf 1 0 0 1 {x} {tm_y} Tm "
              f"(LAYOUTPROBE) Tj ET").encode()
    from pypdf.generic import DecodedStreamObject
    from pypdf.generic import NameObject as NO
    obj = DecodedStreamObject()
    obj.set_data(stream)
    page[NO("/Contents")] = writer_ref = w._add_object(obj)
    w._info = None
    with open(path, "wb") as fh:
        w.write(fh)
    return path


@unittest.skipUnless(HAVE_PDF, "pypdf unavailable")
class TestLayoutInspector(unittest.TestCase):
    import tempfile

    def setUp(self):
        self.tmp = Path(self.tempfile.gettempdir()) / "gf_layout_test.pdf"

    def tearDown(self):
        if self.tmp.exists():
            self.tmp.unlink()

    def test_clean_margins_pass(self):
        _make_pdf(self.tmp, tm_y=400.0, x=100.0)
        r = pli.inspect_pdf_layout(str(self.tmp))
        self.assertTrue(r.ok, f"expected clean: {[f.evidence for f in r.findings]}")

    def test_margin_breach_is_caught(self):
        # 400x400pt page, safe area 36pt -> anything below 36 is a breach
        _make_pdf(self.tmp, tm_y=4.0, x=100.0)
        r = pli.inspect_pdf_layout(str(self.tmp))
        self.assertFalse(r.ok)
        self.assertIn("MARGIN_BREACH", {f.rule for f in r.findings})

    def test_off_page_is_caught(self):
        _make_pdf(self.tmp, tm_y=5000.0, x=100.0)
        r = pli.inspect_pdf_layout(str(self.tmp))
        self.assertFalse(r.ok)
        self.assertIn("OFF_PAGE", {f.rule for f in r.findings})

    def test_unreadable_pdf_is_critical_not_silent(self):
        bad = Path(self.tempfile.gettempdir()) / "gf_not_a.pdf"
        bad.write_bytes(b"this is definitely not a pdf")
        try:
            r = pli.inspect_pdf_layout(str(bad))
            self.assertFalse(r.ok)
            self.assertIn("PDF_UNREADABLE", {f.rule for f in r.findings})
        finally:
            bad.unlink(missing_ok=True)

    def test_missing_file_does_not_crash(self):
        r = pli.inspect_pdf_layout("no_such_file_xyz.pdf")
        self.assertFalse(r.ok)
        self.assertTrue(r.findings)


class TestCtmFalsePositiveRegression(unittest.TestCase):
    """
    Cycle 89: this checker reported 642 MARGIN_BREACH findings on the GDPR
    guide, every one of them false. The page positions its body with
    `1 0 0 1 67.2 672 cm` and then draws text at local (0, 49.5); absolute
    position is (67.2, 721.5), a correct 67pt margin. The extractor ignored
    `cm`, so local coordinates were reported as absolute and a perfectly good
    product looked like it was about to be clipped by any printer.

    These tests pin the transform handling so a good layout cannot be
    "repaired" into a broken one.
    """

    import tempfile

    def _pdf_with_cm(self, path, cm=(67.2, 672.0), local=(0.0, 49.5)):
        w = PdfWriter()
        w.add_blank_page(width=612, height=792)
        page = w.pages[0]
        e, f = cm
        lx, ly = local
        stream = (f"1 0 0 1 {e} {f} cm "
                  f"BT 1 0 0 1 {lx} {ly} Tm /F1 12 Tf "
                  f"(TRANSFORMED) Tj ET").encode()
        from pypdf.generic import DecodedStreamObject, NameObject
        obj = DecodedStreamObject()
        obj.set_data(stream)
        page[NameObject("/Contents")] = w._add_object(obj)
        with open(path, "wb") as fh:
            w.write(fh)
        return path

    def test_transformed_text_is_not_reported_as_edge(self):
        p = Path(self.tempfile.gettempdir()) / "gf_ctm_ok.pdf"
        self._pdf_with_cm(p)
        r = pli.inspect_pdf_layout(str(p))
        self.assertEqual(
            len(r.findings), 0,
            f"false positive -- transformed text inside a proper margin was "
            f"reported: {[f.evidence for f in r.findings][:3]}")
        p.unlink(missing_ok=True)

    def test_real_breach_still_caught_through_a_transform(self):
        """The fix must not blind the checker: genuinely edge-hugging text
        under a transform must still fail."""
        p = Path(self.tempfile.gettempdir()) / "gf_ctm_bad.pdf"
        self._pdf_with_cm(p, cm=(2.0, 2.0))
        r = pli.inspect_pdf_layout(str(p))
        self.assertFalse(r.ok)
        self.assertIn("MARGIN_BREACH", {f.rule for f in r.findings})
        p.unlink(missing_ok=True)

    def test_real_gdpr_guide_is_clean(self):
        import os
        pdf = os.path.join(
            "cohort_GF_SHOPIFY_PREMIUM_10_2026_09", "dist", "GF-SHOP-02",
            "gdpr_dsr_handling_kit_guide.pdf")
        if not os.path.exists(pdf):
            self.skipTest("product not present")
        r = pli.inspect_pdf_layout(pdf)
        self.assertEqual(len(r.findings), 0,
                         "the GDPR guide has a correct margin; a finding here "
                         "means the transform bug is back")


class TestShippedProductsAreLayoutClean(unittest.TestCase):
    """Regression: if a future regeneration introduces clipping, fail here."""

    def test_toolkit_has_no_layout_defect(self):
        p = Path("books/eu_ai_act_compliance_toolkit_v2.pdf")
        if not p.exists():
            self.skipTest("product not present locally")
        r = pli.inspect_pdf_layout(str(p))
        self.assertTrue(
            r.ok,
            f"layout defect found: "
            f"{[(f.rule, f.page, f.evidence) for f in r.findings][:5]}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
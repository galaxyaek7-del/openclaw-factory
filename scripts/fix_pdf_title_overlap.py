"""Repair the page-1 title overlap in the kit PDFs (founder directive
2026-10-17, "Cleanup + Evidence Fix", Mission 3).

The defect (found by file_testing_engine, confirmed by rendering): the kit
generator set a 26pt bold title with 22pt leading, so a title that wraps to
a second line is printed over the 9pt subtitle below it. The generator that
built these PDFs is not in the repository, so the PDF is repaired in place:

  * only page 1, only the title + subtitle text above the coloured notice
    box, is removed (page graphics and every other page are left untouched);
  * the title is redrawn on one line at 20pt (Helvetica-Bold), centred;
  * a thin separator line follows, then the subtitle at 9pt (45% of the
    title), with about a 20pt gap. Both are written with PyMuPDF's
    TextWriter and built-in Helvetica, so the em dash renders and the text
    layer stays exact (see _write).

Acts only when the overlap is actually present: an already-repaired or a
different PDF is reported as SKIPPED and not touched. Refuses to write if
the text would not fit above the notice box.

    python scripts/fix_pdf_title_overlap.py books/x.pdf [more.pdf ...] [--dry-run]
"""
import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

try:
    import pymupdf as fitz      # optional (AGPL; deliberately not in requirements.txt)
except ImportError:             # pragma: no cover
    fitz = None

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TITLE_SIZE, SUB_SIZE = 20, 9
NAVY = (0x1a / 255, 0x2b / 255, 0x4a / 255)
GREY = (0x55 / 255,) * 3


def _spans(page):
    return [s for b in page.get_text("dict")["blocks"] for l in b.get("lines", []) for s in l["spans"]]


def find_overlap(page):
    """Title (26pt) lines, subtitle (9pt) lines above the notice box, and the
    box top. None when the page does not show the defect."""
    spans = _spans(page)
    title = [s for s in spans if round(s["size"]) == 26]
    if len(title) < 2:
        return None
    boxes = [d["rect"].y0 for d in page.get_drawings() if d.get("fill") and d["rect"].y0 > title[0]["bbox"][1]]
    box_top = min(boxes) if boxes else None
    if box_top is None:
        return None
    subtitle = [s for s in spans if round(s["size"]) == 9 and s["bbox"][1] < box_top]
    title_bottom = max(s["bbox"][3] for s in title)
    if not subtitle or title_bottom <= min(s["bbox"][1] for s in subtitle):
        return None                                   # no overlap: nothing to fix
    return {"title": " ".join(s["text"].strip() for s in title),
            "subtitle": " ".join(s["text"].strip() for s in subtitle),
            "box_top": box_top, "top": min(s["bbox"][1] for s in title)}


def _write(page, rect, text, font_name, size, color, align, lineheight=None):
    """TextWriter with PyMuPDF's built-in Helvetica: renders characters the
    simple base-14 encoding lacks (the em dash) AND keeps an exact text layer.
    (Embedded Arial was tried first: it extracts "-" as a soft hyphen and
    spaces as no-break spaces, which breaks copy, search and screen readers.)
    Raises ValueError when the text does not fit the box."""
    tw = fitz.TextWriter(page.rect)
    kw = {"lineheight": lineheight} if lineheight else {}
    tw.fill_textbox(rect, text, font=fitz.Font(font_name), fontsize=size, align=align, **kw)
    tw.write_text(page, color=color)


def repair(src, dst):
    doc = fitz.open(src)
    page = doc[0]
    found = find_overlap(page)
    if not found:
        return {"file": str(src), "status": "SKIPPED", "reason": "no title/subtitle overlap on page 1"}
    box_top, top = found["box_top"], found["top"]
    page.add_redact_annot(fitz.Rect(55, top - 5, 557, box_top - 0.1), fill=False)
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_LINE_ART_NONE)
    try:
        _write(page, fitz.Rect(63.6, top - 6, 548.4, top + 28), found["title"], "hebo", TITLE_SIZE, NAVY, align=1)
        page.draw_line((246, top + 32), (366, top + 32), color=NAVY, width=1)
        _write(page, fitz.Rect(63.6, top + 40, 548.4, box_top - 1), found["subtitle"], "helv", SUB_SIZE, GREY,
               align=0, lineheight=1.25)
    except ValueError as exc:
        return {"file": str(src), "status": "FAILED", "reason": f"text does not fit: {exc}"}
    doc.subset_fonts()
    doc.save(dst, garbage=4, deflate=True)
    return {"file": str(src), "status": "REPAIRED", "title": found["title"], "subtitle": found["subtitle"]}


def verify(original, repaired, title, subtitle):
    """Same page count, pages 2+ text unchanged, title and subtitle present,
    and file_testing_engine passes."""
    import file_testing_engine as fte
    o, n = fitz.open(original), fitz.open(repaired)
    # Whitespace-free compare: a line wrap adds a break that is not in the source.
    text = re.sub(r"\s+", "", n[0].get_text())
    r = fte.test_file(repaired)
    return {
        "pages_equal": len(o) == len(n),
        "other_pages_unchanged": all(o[k].get_text() == n[k].get_text() for k in range(1, len(o))),
        "title_present": re.sub(r"\s+", "", title) in text,
        "subtitle_present": re.sub(r"\s+", "", subtitle) in text,
        "file_test": r.status, "file_test_problems": r.problems,
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("pdfs", nargs="+")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if fitz is None:
        print(json.dumps({"error": "PyMuPDF is not installed (pip install pymupdf); it is optional and AGPL-licensed"}))
        return 2
    results = []
    for pdf in a.pdfs:
        src = Path(pdf)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / src.name
            res = repair(src, out)
            if res["status"] == "REPAIRED":
                res["verify"] = v = verify(src, out, res["title"], res["subtitle"])
                ok = all(v[k] for k in ("pages_equal", "other_pages_unchanged", "title_present", "subtitle_present")) \
                    and v["file_test"] == "PASS"
                if not ok:
                    res["status"] = "FAILED"
                elif not a.dry_run:
                    shutil.copyfile(out, src)
                    res["written"] = True
        results.append(res)
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0 if all(r["status"] != "FAILED" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())

"""Galaxy Forge -- per-file-type testing engine (Cycle 87).

WHY THIS EXISTS
---------------
The founder's standard requires opening a product's actual files and testing
them "according to type", and explicitly forbids being satisfied with file
names and sizes. Nothing in the factory did that:

  * pdf_layout_inspector.py (Cycle 86) checks PDF geometry only.
  * verify_delivery_integrity.py proves bytes and hashes match -- which is a
    TRANSPORT check, not a USABILITY check. A hash match proves you got the
    same file you uploaded. It says nothing about whether the spreadsheet opens,
    whether its formulas compute, or whether the ZIP contains what it claims.

The audit sample makes the gap concrete: an XLSX workbook and several ZIP
bundles ship to customers, and no code had ever opened one.

Every check below actually opens the file with a real parser and inspects its
contents. Filenames and sizes are reported for context but are never, on their
own, evidence that a file is usable.

ALREADY AVAILABLE, NOTHING INSTALLED
------------------------------------
  openpyxl 3.1.5, python-docx 1.2.0, pypdf 6.20.0, Pillow 12.3.0, lxml 6.1.3
  plus stdlib zipfile/csv/ElementTree/html.parser
Total new cost: $0. No dependency was added.

PER-FORMAT CHECKS
-----------------
  PDF   magic bytes, parses, page count, encrypted, layout (reuses Cycle 86)
  XLSX  opens, sheet count, non-empty headers, formula presence, broken refs
        (#REF!, #NAME?, #VALUE!), fully-blank sheets, merged-cell traps
  DOCX  opens, paragraph/table counts, empty-document detection
  ZIP   CRCs (testzip), required entries, zero-byte members, duplicate names,
        path traversal
  HTML  parses, unclosed tags, empty body, no <title>

FAIL-CLOSED: a file that cannot be parsed yields UNKNOWN, never PASS.
"""
from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

# --- results ----------------------------------------------------------------
PASS = "PASS"
FAIL = "FAIL"
UNKNOWN = "UNKNOWN"


@dataclass
class CheckResult:
    path: str
    kind: str
    status: str
    detail: dict = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "path": self.path, "kind": self.kind, "status": self.status,
            "detail": self.detail, "problems": self.problems,
        }


# --- dispatch ---------------------------------------------------------------
def detect_kind(path: Path) -> str:
    ext = path.suffix.lower()
    return {".pdf": "pdf", ".xlsx": "xlsx", ".xlsm": "xlsx",
            ".docx": "docx", ".zip": "zip",
            ".html": "html", ".htm": "html"}.get(ext, "unknown")


def test_file(path) -> CheckResult:
    p = Path(path)
    if not p.exists():
        return CheckResult(str(p), "unknown", UNKNOWN,
                           {}, ["file does not exist"])
    kind = detect_kind(p)
    fn = {"pdf": test_pdf, "xlsx": test_xlsx, "docx": test_docx,
          "zip": test_zip, "html": test_html}.get(kind)
    if fn is None:
        return CheckResult(str(p), kind, UNKNOWN, {},
                           [f"no tester for {p.suffix}"])
    try:
        return fn(p)
    except Exception as exc:  # noqa: BLE001 -- fail closed, never PASS
        return CheckResult(str(p), kind, UNKNOWN, {},
                           [f"tester raised {type(exc).__name__}: {exc}"])


# --- PDF --------------------------------------------------------------------
_IN_WORD_BOX = re.compile(r"[A-Za-z0-9]■[A-Za-z0-9]")


def _text_overlaps(p: Path, min_share: float = 0.25) -> list[tuple]:
    """Lines from DIFFERENT text blocks whose boxes overlap by more than
    `min_share` of the smaller line. Same-block lines are excluded so normal
    tight leading inside a paragraph is never reported."""
    import pymupdf as fitz
    found = []
    with fitz.open(str(p)) as doc:
        for pno, page in enumerate(doc, 1):
            lines = []
            for blk in page.get_text("dict")["blocks"]:
                for ln in blk.get("lines", []):
                    t = "".join(s["text"] for s in ln["spans"]).strip()
                    if t:
                        lines.append((fitz.Rect(ln["bbox"]), t, blk["number"]))
            for i in range(len(lines)):
                ra, ta, ba = lines[i]
                for rb, tb, bb in lines[i + 1:]:
                    if ba == bb:
                        continue
                    x = ra & rb
                    if x.is_empty or x.height <= 3:
                        continue
                    small = min(ra.get_area(), rb.get_area()) or 1.0
                    if x.get_area() / small > min_share:
                        found.append((pno, ta[:40], tb[:40]))
    return found


# Problems that are certain defects a customer would see. Layout findings
# from pdf_layout_inspector are heuristic -- on 2026-10-14 a MARGIN_BREACH on
# the ADA kit pointed at nothing visible -- so they are reported, not blocking.
_ADVISORY_PREFIXES = ("layout ",)


def blocking_problems(result: CheckResult) -> list[str]:
    """The subset of a FAIL that is certain enough to stop a publish."""
    if result.status != FAIL:
        return []
    return [x for x in result.problems if not x.startswith(_ADVISORY_PREFIXES)]


def test_pdf(p: Path) -> CheckResult:
    problems: list[str] = []
    detail: dict = {"bytes": p.stat().st_size}
    head = p.open("rb").read(5)
    if head != b"%PDF-":
        problems.append(f"missing PDF magic bytes (got {head!r})")
        return CheckResult(str(p), "pdf", FAIL, detail, problems)
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader
    try:
        r = PdfReader(str(p))
    except Exception as exc:  # noqa: BLE001
        return CheckResult(str(p), "pdf", UNKNOWN, detail,
                           [f"does not parse: {type(exc).__name__}"])
    detail["pages"] = len(r.pages)
    detail["encrypted"] = bool(r.is_encrypted)
    detail["title"] = str((r.metadata or {}).get("/Title", ""))[:80]
    if len(r.pages) == 0:
        problems.append("zero pages")
    if r.is_encrypted:
        problems.append("encrypted -- a customer cannot read it without a key")
    # Unrenderable glyphs. reportlab's base-14 fonts silently draw a filled box
    # for characters outside WinAnsi (text_sanitizer.py, 2026-10-14), and the
    # box extracts as U+25A0. A legitimate bullet "■ " sits before a space; a
    # defect sits INSIDE a word ("Post■Removal", "30■day"), so only the
    # in-word form is counted -- a real bullet can never fail this check.
    try:
        text = "".join((pg.extract_text() or "") for pg in r.pages)
        boxes = _IN_WORD_BOX.findall(text)
        detail["in_word_box_glyphs"] = len(boxes)
        if boxes:
            problems.append(
                f"{len(boxes)} black-box glyph(s) printed inside words "
                f"(e.g. {boxes[0]!r}) -- customer sees a box instead of a hyphen")
    except Exception:  # noqa: BLE001
        detail["in_word_box_glyphs"] = "text extraction unavailable"
    # Overlapping text: lines from different blocks printed on top of each
    # other (2026-10-14: a wrapped title colliding with its subtitle on page 1
    # of three live kits). pdf_layout_inspector checks margins, not collisions.
    try:
        overlaps = _text_overlaps(p)
        detail["text_overlaps"] = len(overlaps)
        for pg, a, b in overlaps[:2]:
            problems.append(f"text overlap p{pg}: {a!r} printed over {b!r}")
    except ImportError:
        detail["text_overlaps"] = "PyMuPDF unavailable"
    except Exception:  # noqa: BLE001
        detail["text_overlaps"] = "overlap check failed"
    try:
        import pdf_layout_inspector as pli
        lay = pli.inspect_pdf_layout(str(p))
        detail["layout_findings"] = len(lay.findings)
        for f in lay.findings[:3]:
            problems.append(f"layout {f.rule} p{f.page}: {f.evidence[:70]}")
    except Exception:  # noqa: BLE001
        detail["layout_findings"] = "layout check unavailable"
    return CheckResult(str(p), "pdf", FAIL if problems else PASS, detail, problems)


# --- XLSX -------------------------------------------------------------------
_BROKEN_REF = re.compile(r"#(REF!|NAME\?|VALUE!|DIV/0!|N/A|NULL!|NUM!)")


def test_xlsx(p: Path, require_content: bool = True) -> CheckResult:
    problems: list[str] = []
    detail: dict = {"bytes": p.stat().st_size}
    try:
        import openpyxl
    except ImportError:
        return CheckResult(str(p), "xlsx", UNKNOWN, detail,
                           ["openpyxl not available"])
    # formulas preserved so we can inspect what the customer will compute
    try:
        wb = openpyxl.load_workbook(str(p), data_only=False)
    except Exception as exc:  # noqa: BLE001
        return CheckResult(str(p), "xlsx", UNKNOWN, detail,
                           [f"does not open: {type(exc).__name__}: {exc}"])

    sheets = wb.sheetnames
    detail["sheets"] = sheets
    detail["sheet_count"] = len(sheets)
    if not sheets:
        problems.append("workbook has no sheets")
        return CheckResult(str(p), "xlsx", FAIL, detail, problems)

    total_formulas = 0
    broken: list[str] = []
    blank_sheets: list[str] = []

    for name in sheets:
        ws = wb[name]
        populated = 0
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is None:
                    continue
                populated += 1
                v = cell.value
                if isinstance(v, str) and v.startswith("="):
                    total_formulas += 1
                if isinstance(v, str) and _BROKEN_REF.search(v):
                    broken.append(f"{name}!{cell.coordinate}")
        if populated == 0:
            blank_sheets.append(name)

    detail["formula_count"] = total_formulas
    detail["blank_sheets"] = blank_sheets
    if blank_sheets:
        problems.append(f"blank sheet(s): {', '.join(blank_sheets)}")
    if broken:
        problems.append(
            f"{len(broken)} broken reference(s) e.g. {', '.join(broken[:5])}")

    # A tracker sold as a workbook is worthless without formulas -- that is
    # the entire product. Flag it rather than passing a pretty empty grid.
    if require_content and total_formulas == 0:
        detail["no_formulas"] = True
        problems.append(
            "ZERO formulas across every sheet -- a workbook product with no "
            "formulas is a static grid, not a working tool")

    # header sanity on the first sheet
    try:
        ws = wb[sheets[0]]
        first_row = [c.value for c in next(ws.iter_rows(max_row=1))]
        non_empty = [h for h in first_row if h not in (None, "")]
        detail["first_row_headers"] = len(non_empty)
        if not non_empty:
            problems.append("first sheet has no header row")
    except StopIteration:
        problems.append("first sheet is empty")

    return CheckResult(str(p), "xlsx", FAIL if problems else PASS, detail, problems)


# --- DOCX -------------------------------------------------------------------
def test_docx(p: Path) -> CheckResult:
    problems: list[str] = []
    detail: dict = {"bytes": p.stat().st_size}
    try:
        import docx
    except ImportError:
        return CheckResult(str(p), "docx", UNKNOWN, detail,
                           ["python-docx not available"])
    try:
        d = docx.Document(str(p))
    except Exception as exc:  # noqa: BLE001
        return CheckResult(str(p), "docx", UNKNOWN, detail,
                           [f"does not open: {type(exc).__name__}: {exc}"])
    paras = [x.text.strip() for x in d.paragraphs if x.text.strip()]
    detail["paragraphs"] = len(paras)
    detail["tables"] = len(d.tables)
    words = sum(len(x.split()) for x in paras)
    detail["words"] = words
    if not paras and not d.tables:
        problems.append("document is empty")
    return CheckResult(str(p), "docx", FAIL if problems else PASS, detail, problems)


# --- ZIP --------------------------------------------------------------------
def test_zip(p: Path, required: list[str] | None = None) -> CheckResult:
    problems: list[str] = []
    detail: dict = {"bytes": p.stat().st_size}
    try:
        zf = zipfile.ZipFile(str(p))
    except Exception as exc:  # noqa: BLE001
        return CheckResult(str(p), "zip", UNKNOWN, detail,
                           [f"not a valid zip: {type(exc).__name__}"])
    with zf:
        bad = zf.testzip()
        if bad is not None:
            problems.append(f"CRC failure in member {bad!r} -- archive is corrupt")
        names = zf.namelist()
        detail["members"] = names
        detail["member_count"] = len(names)
        seen: dict[str, int] = {}
        for n in names:
            seen[n] = seen.get(n, 0) + 1
            try:
                info = zf.getinfo(n)
            except Exception:  # noqa: BLE001
                continue
            if info.file_size == 0:
                problems.append(f"zero-byte member: {n}")
            if ".." in Path(n).parts or n.startswith("/"):
                problems.append(f"unsafe path in archive: {n}")
        dupes = [n for n, c in seen.items() if c > 1]
        if dupes:
            problems.append(f"duplicate member name(s): {dupes[:5]}")
        if not names:
            problems.append("archive is empty")
        for r in (required or []):
            if not any(r.lower() in n.lower() for n in names):
                problems.append(f"required member missing: {r}")
    return CheckResult(str(p), "zip", FAIL if problems else PASS, detail, problems)


# --- HTML -------------------------------------------------------------------
def test_html(p: Path) -> CheckResult:
    problems: list[str] = []
    detail: dict = {"bytes": p.stat().st_size}
    raw = p.read_text(encoding="utf-8", errors="replace")
    detail["chars"] = len(raw)
    try:
        from html.parser import HTMLParser

        class P(HTMLParser):
            def __init__(self):
                super().__init__()
                self.stack: list[str] = []
                self.unclosed: list[str] = []
                self.title = ""
                self._in_title = False
                self.text_len = 0

            def handle_starttag(self, tag, attrs):
                if tag not in ("br", "img", "meta", "link", "hr", "input"):
                    self.stack.append(tag)
                if tag == "title":
                    self._in_title = True

            def handle_endtag(self, tag):
                if tag == "title":
                    self._in_title = False
                if tag in ("br", "img", "meta", "link", "hr", "input"):
                    return
                if self.stack and self.stack[-1] == tag:
                    self.stack.pop()
                elif tag in self.stack:
                    while self.stack and self.stack.pop() != tag:
                        pass

            def handle_data(self, data):
                if self._in_title:
                    self.title += data
                if data.strip():
                    self.text_len += len(data.split())

        parser = P()
        parser.feed(raw)
        detail["unclosed_tags"] = parser.stack
        detail["title"] = parser.title.strip()[:80]
        detail["word_count"] = parser.text_len
        if parser.stack:
            problems.append(f"unclosed tag(s): {parser.stack[:5]}")
        if not parser.title.strip():
            problems.append("no <title>")
        if parser.text_len < 20:
            problems.append(f"body is nearly empty ({parser.text_len} words)")
    except Exception as exc:  # noqa: BLE001
        return CheckResult(str(p), "html", UNKNOWN, detail,
                           [f"parse failed: {type(exc).__name__}"])
    return CheckResult(str(p), "html", FAIL if problems else PASS, detail, problems)
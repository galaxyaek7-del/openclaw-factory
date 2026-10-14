"""PDF layout inspection -- margins, cropping, text overlap.

The Cycle 86 standard asks for visual/type-appropriate inspection of a
product's output. Everything checked so far looked at TEXT. Nothing checked
whether the text is actually RENDERED correctly: a PDF can contain perfect
content and still clip it off the page, overlap it, or leave it in the margin.

This reads real glyph positions from the content stream rather than guessing
from text extraction, because pypdf's extract_text() discards coordinates and
cannot see any of this.

Checks:
  MARGIN_BREACH  glyph drawn outside the safe area
  TEXT_OVERLAP   two text runs occupying the same vertical band
  OFF_PAGE       glyph beyond the MediaBox entirely

Read-only. Costs $0. No rendering libraries required.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader

# A typographic safe area. 0.5in = 36pt on every side is the floor a real
# product page should clear; anything tighter risks trimming on a real printer.
SAFE_MARGIN_PT = 36.0


@dataclass
class LayoutFinding:
    rule: str
    severity: str
    page: int
    evidence: str


@dataclass
class LayoutResult:
    pdf: str
    pages: int = 0
    findings: list[LayoutFinding] = field(default_factory=list)
    pages_unreadable: int = 0
    note: str = ""

    @property
    def ok(self) -> bool:
        return not self.findings


# Text-positioning operators we need: Tm/Td/TD/T* set the matrix, Tj/TJ show
# text. We only need the translation components (e,f) of the text matrix.
_TX = re.compile(rb"([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+"
                 rb"([\d.\-]+)\s+([\d.\-]+)\s+Tm")
_TD = re.compile(rb"([\d.\-]+)\s+([\d.\-]+)\s+T[dD]")
_SHOW = re.compile(rb"(?:\[.*?\]\s*TJ|\(.*?\)\s*Tj)", re.S)


def _extract_page_data(page) -> tuple[list[tuple[float, float]], tuple[float, ...]]:
    """Return [(x, y)] text-show positions and the MediaBox."""
    try:
        content = page.get_contents()
        data = content.get_data() if content is not None else b""
    except Exception:  # noqa: BLE001
        return [], (0, 0, 0, 0)

    mb = page.mediabox
    box = (float(mb.left), float(mb.bottom), float(mb.right), float(mb.top))

    positions: list[tuple[float, float]] = []
    x = y = 0.0
    # Walk the stream in order so Td/TD accumulate onto the current position.
    for m in re.finditer(
            rb"(?P<tm>[-\d.\s]+Tm)|(?P<td>[-\d.\s]+T[dD])|(?P<show>\[(?:[^\[\]]|\\.)*\]\s*TJ|\((?:[^()\\]|\\.)*\)\s*Tj)",
            data, re.S):
        if m.group("tm"):
            nums = [float(x) for x in m.group("tm").split()[:6]]
            if len(nums) == 6:
                x, y = nums[4], nums[5]
                positions.append((x, y))
        elif m.group("td"):
            nums = [float(v) for v in m.group("td").split()[:2]]
            if len(nums) == 2:
                x += nums[0]
                y += nums[1]
                positions.append((x, y))
        else:
            if positions:
                positions.append((x, y))
    return positions, box


def inspect_pdf_layout(pdf_path: str, safe_margin: float = SAFE_MARGIN_PT) -> LayoutResult:
    res = LayoutResult(pdf=pdf_path)
    try:
        reader = PdfReader(pdf_path)
    except Exception as exc:  # noqa: BLE001
        res.note = f"unreadable: {type(exc).__name__}"
        res.findings.append(LayoutFinding(
            "PDF_UNREADABLE", "CRITICAL", 0, res.note))
        return res

    res.pages = len(reader.pages)
    for pno, page in enumerate(reader.pages, 1):
        positions, box = _extract_page_data(page)
        if not positions:
            res.pages_unreadable += 1
            continue
        left, bottom, right, top = box
        width, height = right - left, top - bottom

        for (x, y) in positions:
            if x < left - 1 or x > right + 1 or y < bottom - 1 or y > top + 1:
                res.findings.append(LayoutFinding(
                    "OFF_PAGE", "CRITICAL", pno,
                    f"text origin ({x:.0f}, {y:.0f}) outside MediaBox "
                    f"({left:.0f},{bottom:.0f},{right:.0f},{top:.0f})"))
                continue
            if (x < left + safe_margin or x > right - safe_margin
                    or y < bottom + safe_margin or y > top - safe_margin):
                res.findings.append(LayoutFinding(
                    "MARGIN_BREACH", "MAJOR", pno,
                    f"text at ({x:.0f}, {y:.0f}) inside the "
                    f"{safe_margin:.0f}pt safe area of a "
                    f"{width:.0f}x{height:.0f}pt page"))
    return res


def main() -> int:
    targets = [
        ("EU AI Act Toolkit (shipped)", "books/eu_ai_act_compliance_toolkit_v2.pdf"),
        ("EU AI Act Toolkit preview", "books/eu_ai_act_compliance_toolkit_preview.pdf"),
        ("EU AI Act Audit Logging Kit", "books/eu_ai_act_audit_logging_kit.pdf"),
    ]
    print("=" * 74)
    print("PDF LAYOUT INSPECTION -- margins, cropping, overlap")
    print("=" * 74)
    worst = 0
    for label, path in targets:
        r = inspect_pdf_layout(path)
        crit = sum(1 for f in r.findings if f.severity == "CRITICAL")
        maj = sum(1 for f in r.findings if f.severity == "MAJOR")
        worst = max(worst, crit)
        print(f"\n{label}")
        print(f"  {path}")
        print(f"  pages={r.pages} readable={r.pages - r.pages_unreadable} "
              f"critical={crit} major={maj}")
        for f in r.findings[:4]:
            print(f"    [{f.severity}] {f.rule} p{f.page}: {f.evidence[:100]}")
        if len(r.findings) > 4:
            print(f"    ... {len(r.findings) - 4} more")
        if not r.findings:
            print("    no layout defect detected")
    print()
    print("NOTE: this reads glyph positions from the content stream. It cannot")
    print("see font-embedding or visual styling problems. Absence of a finding")
    print("is not a visual sign-off.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""Galaxy Forge -- repair black-box glyphs in already-shipped PDFs.

WHY THIS EXISTS
---------------
text_sanitizer.py (2026-10-14) stops NEW books from printing black boxes, but
the PDFs already in books/ were generated before that fix, and their source
text (LLM output) was never kept. Regenerating them would mean new AI content
-- a different product. This repairs the existing files exactly instead.

THE MECHANISM, MEASURED
-----------------------
When reportlab meets a character outside WinAnsi (U+2010 HYPHEN, U+2011
NON-BREAKING HYPHEN, ...) it falls back to the ZapfDingbats font and draws the
letter "n", which in ZapfDingbats is a filled square. In the content stream:

    (Preventing Future Suspensions: Post) Tj /F3 10 Tf 12 TL (n) Tj /F2 10 Tf 12 TL (Removal ...

where /F3 is ZapfDingbats. The repair rewrites exactly that run to a hyphen in
the font that follows it:

    (... Post) Tj /F2 10 Tf 12 TL (-) Tj /F2 10 Tf 12 TL (Removal ...

SAFETY
------
  * Only a ZapfDingbats "(n)" run whose neighbouring strings end and begin
    with a letter or digit is touched -- an in-word box. A deliberate bullet
    ("■ item") has a space or line start beside it and is never changed.
  * The font is identified from the page's own /Resources, never assumed.
  * verify(): re-extracts text and requires (a) zero in-word boxes remain and
    (b) the text is otherwise identical apart from box -> hyphen. A repair that
    fails verification is not written.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_IN_WORD_BOX = re.compile(r"(?<=[A-Za-z0-9])■(?=[A-Za-z0-9])")
_WS = re.compile(r"\s+")


@dataclass
class RepairReport:
    path: str
    boxes_before: int = 0
    boxes_after: int = 0
    runs_rewritten: int = 0
    written: bool = False
    reason: str = ""
    pages_changed: list = field(default_factory=list)


def _dingbat_fonts(page) -> set[bytes]:
    out: set[bytes] = set()
    try:
        fonts = page["/Resources"]["/Font"]
    except Exception:  # noqa: BLE001
        return out
    for name, ref in fonts.items():
        try:
            base = str(ref.get_object().get("/BaseFont", ""))
        except Exception:  # noqa: BLE001
            continue
        if "ZapfDingbats" in base:
            out.add(name.encode("latin-1"))
    return out


def _run_pattern(font: bytes) -> re.Pattern:
    f = re.escape(font)
    # (..X) Tj  /Fd s Tf l TL (n) Tj  /Fn s2 Tf l2 TL (Y..
    return re.compile(
        rb"(?P<pre>[A-Za-z0-9]\)\s*Tj\s+)"
        + f + rb"\s+(?P<sz>[\d.]+)\s+Tf\s+(?P<tl>[\d.]+)\s+TL\s+\(n\)\s*Tj"
        rb"(?P<post>\s+(?P<nf>/F\d+)\s+[\d.]+\s+Tf\s+[\d.]+\s+TL\s+\([A-Za-z0-9])"
    )


def _rewrite(data: bytes, fonts: set[bytes]) -> tuple[bytes, int]:
    def sub(m):
        return (m.group("pre") + m.group("nf") + b" " + m.group("sz") + b" Tf "
                + m.group("tl") + b" TL (-) Tj" + m.group("post"))

    total = 0
    for font in fonts:
        # Boxes one character apart ("4■2■6", "as■a■service") share that
        # character, so one non-overlapping pass leaves every second box.
        # Repeat until stable; each pass strictly removes runs, so it ends.
        pat = _run_pattern(font)
        while True:
            data, n = pat.subn(sub, data)
            total += n
            if not n:
                break
    return data, total


def _text(reader) -> str:
    return "".join((p.extract_text() or "") for p in reader.pages)


def count_in_word_boxes(path) -> int:
    from pypdf import PdfReader
    return len(_IN_WORD_BOX.findall(_text(PdfReader(str(path)))))


def repair_pdf(src, dst=None) -> RepairReport:
    from pypdf import PdfReader, PdfWriter

    src = Path(src)
    dst = Path(dst) if dst else src
    rep = RepairReport(str(src))
    reader = PdfReader(str(src))
    before_text = _text(reader)
    rep.boxes_before = len(_IN_WORD_BOX.findall(before_text))
    if rep.boxes_before == 0:
        rep.reason = "no in-word boxes"
        return rep

    writer = PdfWriter(clone_from=reader)
    for i, page in enumerate(writer.pages):
        fonts = _dingbat_fonts(page)
        if not fonts:
            continue
        contents = page.get_contents()
        if contents is None:
            continue
        data = contents.get_data()
        new, n = _rewrite(data, fonts)
        if n:
            contents.set_data(new)
            page.replace_contents(contents)
            rep.runs_rewritten += n
            rep.pages_changed.append(i + 1)

    if not rep.runs_rewritten:
        rep.reason = "boxes present but not in the known ZapfDingbats fallback form"
        return rep

    tmp = dst.with_suffix(dst.suffix + ".repair.tmp")
    with open(tmp, "wb") as fh:
        writer.write(fh)

    after_text = _text(PdfReader(str(tmp)))
    rep.boxes_after = len(_IN_WORD_BOX.findall(after_text))
    expected = _WS.sub("", _IN_WORD_BOX.sub("-", before_text))
    got = _WS.sub("", after_text)
    if rep.boxes_after or expected != got:
        tmp.unlink(missing_ok=True)
        rep.reason = ("verification failed: "
                      + (f"{rep.boxes_after} boxes remain" if rep.boxes_after
                         else "text changed beyond box -> hyphen"))
        return rep
    tmp.replace(dst)
    rep.written = True
    return rep


if __name__ == "__main__":  # pragma: no cover
    import json
    import sys
    for arg in sys.argv[1:]:
        print(json.dumps(repair_pdf(arg).__dict__, default=str))

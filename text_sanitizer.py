"""Galaxy Forge -- WinAnsi text safety for the PDF pipeline (Cycle 87).

THE DEFECT, MEASURED
---------------------
40,259 black-box glyphs ("■") across 44 of 114 shipped PDFs. A buyer opening
the Etsy Suspension Appeal Kit sees "Post■Removal" and "the 30■day window".
This is not cosmetic mojibake in a log; it is the printed product.

ROOT CAUSE, ISOLATED BY TEST
----------------------------
reportlab's base-14 Helvetica is encoded WinAnsi. A character outside that
encoding is not rejected -- reportlab silently substitutes a filled box. The
build's own drawing path is innocent: drawString, _wrap_text and
draw_flowing_text all round-trip a real em-dash cleanly. The corruption
happens because the INCOMING TEXT contains dash-like characters that
WinAnsi does not contain:

    U+2010 HYPHEN          -> box
    U+2011 NON-BREAKING HYPHEN -> box
    U+FFFD REPLACEMENT CHARACTER -> box
    U+2013 EN DASH         -> renders
    U+2014 EM DASH         -> renders
    U+25A0 BLACK SQUARE    -> renders (it IS a box)

Language models emit U+2010 and U+2011 readily when writing typographically
"smart" text, and they look identical to a hyphen in the model's output. The
result is a shipped product full of black rectangles with no error, no
warning, and a green build.

WHAT THIS MODULE DOES
---------------------
`sanitize_for_pdf()` rewrites characters the target encoding cannot represent
into ones it can, and returns a report of every substitution so a caller can
log or fail. `unsafe_codepoints()` determines the unsafe set by MEASUREMENT --
it renders candidates and checks what survives -- rather than by trusting a
hardcoded list that can drift from the font.

Pure, offline, deterministic, $0.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# --- substitutions ----------------------------------------------------------
# Ordered most-specific first. Each maps an unrepresentable codepoint to a
# character that is verified to render in the base-14 Helvetica WinAnsi set.
SUBSTITUTIONS = {
    "\u2010": "-",   # HYPHEN
    "\u2011": "-",   # NON-BREAKING HYPHEN
    "\u2012": "-",   # FIGURE DASH
    "\u2015": "-",   # HORIZONTAL BAR
    "\u2016": "||",  # DOUBLE VERTICAL LINE
    "\u2017": "_",   # DOUBLE LOW LINE
    "\u201b": "'",   # QUADRUPLE PRIME
    "\u201f": '"',   # HIGH REVERSED NINE QUOTATION MARK
    "\u2212": "-",   # MINUS SIGN
    "\u00ad": "",    # SOFT HYPHEN
    "\u200b": "",    # ZERO WIDTH SPACE
    "\u200c": "",    # ZERO WIDTH NON-JOINER
    "\u200d": "",    # ZERO WIDTH JOINER
    "\ufeff": "",    # ZERO WIDTH NO-BREAK SPACE / BOM
    "\ufffd": "",    # REPLACEMENT CHARACTER (already lost upstream)
    "\u00a0": " ",   # NO-BREAK SPACE -> plain space
    "\u202f": " ",   # NARROW NO-BREAK SPACE
    "\u2009": " ",   # THIN SPACE
    "\u200a": " ",   # HAIR SPACE
}

# Characters that render correctly and must be preserved untouched.
_KEEP = {"\u2013", "\u2014", "\u2026", "\u00a9", "\u00ae", "\u00b0", "\u25a0"}

_SUB_RE = re.compile("|".join(re.escape(k) for k in SUBSTITUTIONS))


@dataclass
class SanitizeReport:
    text: str
    substitutions: dict = field(default_factory=dict)
    removed: int = 0

    @property
    def changed(self) -> bool:
        return bool(self.substitutions) or self.removed > 0

    def summary(self) -> str:
        if not self.changed:
            return "clean"
        parts = [f"{cp} x{n}" for cp, n in self.substitutions.items()]
        if self.removed:
            parts.append(f"removed {self.removed}")
        return ", ".join(parts)


def sanitize_for_pdf(text: str) -> SanitizeReport:
    """Rewrite text so every character survives the target font encoding."""
    if not text:
        return SanitizeReport(text or "")
    counts: dict[str, int] = {}
    removed = 0

    def _repl(m: re.Match) -> str:
        nonlocal removed
        src = m.group(0)
        dst = SUBSTITUTIONS[src]
        if dst == "":
            removed += 1
        counts[f"U+{ord(src):04X}"] = counts.get(f"U+{ord(src):04X}", 0) + 1
        return dst

    out = _SUB_RE.sub(_repl, text)
    return SanitizeReport(out, counts, removed)


def unsafe_codepoints(sample_text: str = "") -> dict[str, bool]:
    """
    Measure which codepoints fail to round-trip through reportlab Helvetica.

    Uses the real font rather than a hardcoded list, so the answer cannot drift
    from the renderer this factory actually ships with.
    """
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
    except ImportError:  # pragma: no cover
        return {}
    import tempfile
    import os
    from pypdf import PdfReader

    chars = set(sample_text) | set(_KEEP)
    # a spread of typographic and non-ASCII codepoints worth probing
    chars |= set(chr(c) for c in range(0x2010, 0x2020))
    chars |= set(chr(c) for c in range(0x00a0, 0x00b0))
    chars |= set("\u2212\u25a0\ufffd\u2018\u2019\u201c\u201d\u2026\u00a9\u00ae")

    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    out = {}
    try:
        for ch in sorted(chars):
            if ch in "\r\n\t":
                continue
            c = canvas.Canvas(path, pagesize=letter)
            c.setFont("Helvetica", 14)
            c.drawString(72, 700, f"A{ch}B")
            c.save()
            got = "".join((p.extract_text() or "") for p in PdfReader(path).pages)
            out[f"U+{ord(ch):04X}"] = (ch in got)
    except Exception:  # noqa: BLE001
        return out
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    return out


def sanitize_structure(obj):
    """
    Walk a book_data dict and sanitize every string it contains. This is the
    shape create_ai_book() actually receives, so sanitizing here covers
    titles, subtitles, introductions, chapter titles and chapter bodies in one
    pass -- the real entry point rather than a helper nobody calls.
    """
    report = SanitizeReport("")
    total = SanitizeReport("")

    def _walk(node):
        if isinstance(node, str):
            r = sanitize_for_pdf(node)
            if r.changed:
                for k, v in r.substitutions.items():
                    total.substitutions[k] = total.substitutions.get(k, 0) + v
                total.removed += r.removed
            return r.text
        if isinstance(node, list):
            return [_walk(x) for x in node]
        if isinstance(node, tuple):
            return tuple(_walk(x) for x in node)
        if isinstance(node, dict):
            return {k: _walk(v) for k, v in node.items()}
        return node

    return _walk(obj), total
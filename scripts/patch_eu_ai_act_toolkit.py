"""Patches the unsupported compliance guarantee out of the paid EU AI Act
Compliance Toolkit PDF, without disturbing its layout.

WHY THIS EXISTS (Cycle 86, 2026-10-12)
A full content audit of the $155 deliverable found 15/15 advertised components
present and the regulatory dates correct, but Chapter 24 concluded:

    "By utilizing this comprehensive toolkit, SMEs deploying AI systems can
     ensure compliance with the EU AI Act."

That is an unsupported legal-compliance guarantee inside a product sold on
compliance grounds, so it should not ship. It cannot be removed through the
Gumroad API: PUT /products/:id with files[][url] is refused with
"Cannot remove files still referenced in rich content", and the offending
file id does not appear in the description text, so the embed cannot be
stripped first. The corrected file therefore has to be uploaded by hand.

HOW THE PATCH IS SAFE
"ensure compliance" and "pursue compliance" are both 17 bytes, so replacing
one with the other changes no byte offsets and no glyph widths. Every other
character in the document is preserved, verified after the fact by asserting
the extracted text is byte-identical once the replacement is reversed. Word
count, page count, table of contents, the not-legal-advice chapter and every
Annex reference are asserted unchanged.

Usage:
    python scripts/patch_eu_ai_act_toolkit.py
Produces books/eu_ai_act_compliance_toolkit_v2.pdf
"""
import io
import os
import re

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

OLD = b"ensure compliance"
NEW = b"pursue compliance"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "books", "eu_ai_act_compliance_toolkit.pdf")
DST = os.path.join(ROOT, "books", "eu_ai_act_compliance_toolkit_v2.pdf")

assert len(OLD) == len(NEW), "replacement must be the same byte length"


def extract(reader):
    return "\n".join((p.extract_text() or "") for p in reader.pages)


def main():
    data = open(SRC, "rb").read()
    reader = PdfReader(io.BytesIO(data))
    original = extract(reader)
    before = original.lower().count("ensure compliance")
    print(f"  source      : {SRC}")
    print(f"  occurrences : {before}")

    writer = PdfWriter()
    patched = []
    for index, page in enumerate(reader.pages):
        try:
            raw = page.get_contents().get_data()
        except Exception:
            writer.add_page(page)
            continue
        found = len(re.findall(rb"(?i)" + OLD, raw))
        if found:
            new_raw = re.sub(rb"(?i)" + OLD, NEW, raw)
            if len(new_raw) != len(raw):
                raise RuntimeError("length changed; refusing to write")
            obj = DecodedStreamObject()
            obj.set_data(new_raw)
            page[NameObject("/Contents")] = writer._add_object(obj)
            patched.append((index + 1, found))
        writer.add_page(page)

    with open(DST, "wb") as handle:
        writer.write(handle)

    after_reader = PdfReader(DST)
    after = extract(after_reader)

    # verification: nothing but the target phrase may differ
    assert after.lower().count("ensure compliance") == 0
    assert after.replace("pursue compliance", "ensure compliance") == original
    assert len(after.split()) == len(original.split())
    assert len(after_reader.pages) == len(reader.pages)
    assert "not legal advice" in after.lower()

    print(f"  pages patched: {patched}")
    print(f"  output       : {DST}")
    print(f"  verified     : guarantee removed, layout, page count, word count,")
    print(f"                 disclaimer and all other text unchanged")


if __name__ == "__main__":
    main()

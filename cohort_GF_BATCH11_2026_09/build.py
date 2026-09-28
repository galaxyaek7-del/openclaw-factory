#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GF_BATCH11_2026_09 — renderer: guide.md -> PDF, workbook.json -> XLSX,
templates.json -> DOCX, ZIP bundle, manifest, QA. No network. Deterministic."""
import json, re, sys, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
OUT = ROOT / "dist"

PRODUCTS = [
    ("GF-B11-01", "eudr_due_diligence_starter", 6900),
    ("GF-B11-02", "empco_green_claims_kit", 6900),
    ("GF-B11-03", "restaurant_food_cost_control", 4900),
    ("GF-B11-04", "salon_commission_pay_kit", 3900),
    ("GF-B11-05", "fleet_maintenance_damage_bundle", 4900),
    ("GF-B11-06", "realestate_tc_deadline_kit", 5900),
    ("GF-B11-07", "dental_insurance_verification_kit", 5900),
    ("GF-B11-08", "homebuyer_inspection_action_kit", 2900),
    ("GF-B11-09", "cottage_food_compliance_kit", 4900),
    ("GF-B11-10", "landlord_movein_inspection_pack", 4900),
]

BANNED = ["ai-powered", "ultimate", "revolutionary", "guaranteed",
          "worth $", "best ", "best-", "ensure compliance", "guarantee approval",
          "guarantee payout", "passive income", "get rich", "no risk",
          "risk-free", "double your", "10x your"]
PLACEHOLDERS = ["TODO", "LOREM", "[INSERT]", "[YOUR ", "XXX ", "TBD", "FIXME",
                "__SA_ID_FROM_ENV__"]

REPLACEMENTS = {"\u2610": "[ ]", "\u2611": "[x]", "\u2192": "->", "\u2190": "<-",
    "\u2014": "-", "\u2013": "-", "\u2018": "'", "\u2019": "'",
    "\u201c": '"', "\u201d": '"', "\u2022": "-", "\u2713": "x", "\u2714": "x",
    "\u00a0": " ", "\u20ac": "EUR ", "\u00a3": "GBP "}

def sanitize(t: str) -> str:
    for k, v in REPLACEMENTS.items():
        t = t.replace(k, v)
    return t.encode("cp1252", errors="replace").decode("cp1252")

def build_pdf(pid, slug, guide_path, pdf_path, listing):
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_LEFT
    from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame,
                                    Paragraph, Spacer, Table, TableStyle,
                                    PageBreak)
    from reportlab.lib import colors
    raw = guide_path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    styles = getSampleStyleSheet()
    sTitle = ParagraphStyle("T", parent=styles["Title"], fontSize=26, leading=30)
    sH1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=16, leading=20,
                         spaceBefore=14, spaceAfter=8, textColor=colors.HexColor("#1a1a2e"))
    sH2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12.5, leading=16,
                         spaceBefore=10, spaceAfter=6)
    sBody = ParagraphStyle("B", parent=styles["Normal"], fontSize=10.5, leading=15,
                           spaceAfter=5, alignment=TA_LEFT)
    sBullet = ParagraphStyle("Bul", parent=sBody, leftIndent=18, bulletIndent=8,
                             spaceAfter=3)
    sMono = ParagraphStyle("M", parent=sBody, fontName="Courier", fontSize=9.5,
                           backColor=colors.HexColor("#f4f4f4"))

    def esc(t):
        return sanitize(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def inline(t):
        t = esc(t)
        t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
        t = re.sub(r"`(.+?)`", r'<font face="Courier">\1</font>', t)
        return t

    story = []
    title = listing["name"]
    story.append(Spacer(1, 1.6 * inch))
    story.append(Paragraph(esc(title), sTitle))
    story.append(Spacer(1, 0.25 * inch))
    story.append(Paragraph(esc(listing.get("outcome_statement", "")), sBody))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("Galaxy Forge Implementation Kit &nbsp;|&nbsp; Version 1.0 &nbsp;|&nbsp; September 2026", sBody))
    story.append(Paragraph("Companion files: Excel workbook, editable Word templates, README.", sBody))
    i = 0
    in_list = False
    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln.strip():
            i += 1
            continue
        if ln.startswith("```"):
            i += 1
            buf = []
            while i < len(lines) and not lines[i].rstrip().startswith("```"):
                buf.append(lines[i].rstrip()); i += 1
            i += 1
            for b in buf:
                story.append(Paragraph(esc(b) or " ", sMono))
            continue
        if ln.startswith("|") and ln.endswith("|"):
            cells = [inline(c.strip()) for c in ln.strip().strip("|").split("|")]
            if set(re.sub(r"<[^>]+>", "", c).strip() for c in cells) <= {"", "-", ":", "-"}:
                i += 1; continue
            story.append(Paragraph(" / ".join(cells), sBullet))
            i += 1; continue
        m = re.match(r"^(#{1,3})\s+(.*)", ln)
        if m:
            lvl, txt = len(m.group(1)), m.group(2).strip()
            if lvl == 1 and story and not isinstance(story[-1], PageBreak):
                pass
            story.append(Paragraph(inline(txt), sH1 if lvl <= 2 else sH2))
            i += 1; continue
        if ln.strip() in ("---", "***", "___"):
            i += 1; continue
        m = re.match(r"^\s*-\s*\[.\]\s*(.*)", ln)
        if m:
            story.append(Paragraph("[ ] " + inline(m.group(1)), sBullet, bulletText="-"))
            i += 1; continue
        m = re.match(r"^\s*[-*]\s+(.*)", ln)
        if m:
            story.append(Paragraph(inline(m.group(1)), sBullet, bulletText="-"))
            i += 1; continue
        m = re.match(r"^\s*\d+[.)]\s+(.*)", ln)
        if m:
            story.append(Paragraph(inline(m.group(1)), sBullet, bulletText=">"))
            i += 1; continue
        if ln.startswith(">"):
            story.append(Paragraph("<i>" + inline(ln.lstrip("> ")) + "</i>", sBullet))
            i += 1; continue
        story.append(Paragraph(inline(ln), sBody))
        i += 1

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(0.75 * inch, 0.55 * inch, sanitize(f"{title}  |  v1.0"))
        canvas.drawRightString(7.75 * inch, 0.55 * inch, f"Page {doc.page}")
        canvas.restoreState()

    doc = BaseDocTemplate(str(pdf_path), pagesize=LETTER,
                          leftMargin=0.85 * inch, rightMargin=0.85 * inch,
                          topMargin=0.75 * inch, bottomMargin=0.75 * inch,
                          title=sanitize(title), author="Galaxy Forge")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=footer)])
    doc.build(story)
    return doc.page

def build_xlsx(spec_path, xlsx_path):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    hdr = PatternFill("solid", fgColor="1F3864")
    hfont = Font(bold=True, color="FFFFFF")
    for sh in spec["sheets"]:
        ws = wb.create_sheet(sh["name"][:31])
        for c, col in enumerate(sh["columns"], 1):
            cell = ws.cell(row=1, column=c, value=col)
            cell.font = hfont; cell.fill = hdr
            cell.alignment = Alignment(wrap_text=True, vertical="center")
        for r, row in enumerate(sh.get("example_rows", []), 2):
            for c, val in enumerate(row, 1):
                if c <= len(sh["columns"]):
                    ws.cell(row=r, column=c, value=val)
        for f in sh.get("formulas", []):
            coord = f["cell"]
            target_ws = ws
            if "!" in coord:
                prefix, coord = coord.split("!", 1)
                prefix = prefix.strip("'")
                if prefix in wb.sheetnames:
                    target_ws = wb[prefix]
            target_ws[coord] = f["formula"]
        if sh.get("notes"):
            ws.cell(row=ws.max_row + 2, column=1, value="Notes: " + sh["notes"])
        for c in range(1, len(sh["columns"]) + 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(c)].width = 22
        ws.freeze_panes = "A2"
    wb.save(xlsx_path)

def build_docx(templates_path, out_dir):
    from docx import Document
    from docx.shared import Pt
    spec = json.loads(templates_path.read_text(encoding="utf-8"))
    made = []
    for t in spec["templates"]:
        doc = Document()
        raw_title = t.get("title") or t.get("name") or t["filename_docx"].replace(".docx", "").replace("_", " ").title()
        doc.add_heading(sanitize(raw_title), level=1)
        for sec in t["sections"]:
            doc.add_heading(sanitize(sec["heading"]), level=2)
            body = sec.get("body", [])
            if isinstance(body, dict):
                body = [body]
            for item in body:
                if isinstance(item, dict) and "fields" in item:
                    for f in item["fields"]:
                        p = doc.add_paragraph()
                        r = p.add_run(sanitize(str(f)))
                        r.font.size = Pt(11)
                        doc.add_paragraph("_" * 60)
                else:
                    p = doc.add_paragraph(sanitize(str(item)))
                    p.style.font.size = Pt(11)
        p = out_dir / t["filename_docx"]
        doc.save(p)
        made.append(p)
    return made

def build_all():
    OUT.mkdir(parents=True, exist_ok=True)
    for pid, slug, price in PRODUCTS:
        sdir = SRC / pid
        pdir = OUT / pid
        pdir.mkdir(parents=True, exist_ok=True)
        listing = json.loads((sdir / "listing.json").read_text(encoding="utf-8"))
        pages = build_pdf(pid, slug, sdir / "guide.md", pdir / f"{slug}_guide.pdf", listing)
        wspec = json.loads((sdir / "workbook.json").read_text(encoding="utf-8"))
        build_xlsx(sdir / "workbook.json", pdir / wspec["workbook_filename"])
        docxs = build_docx(sdir / "templates.json", pdir)
        readme = (f"{listing['name']}\nGalaxy Forge Implementation Kit v1.0 (September 2026)\n\n"
                  f"FILES\n- {slug}_guide.pdf : main implementation guide\n"
                  f"- {wspec['workbook_filename']} : Excel workbook "
                  f"({len(wspec['sheets'])} sheets)\n" +
                  "".join(f"- {d.name} : editable template\n" for d in docxs) +
                  f"\nHOW TO USE: start with Quick Start (section 2 of the guide), "
                  f"then work the 14-day plan in section 9.\nSUPPORT: email support "
                  f"for file/usage questions within 7 days of purchase.\n")
        (pdir / "README.txt").write_text(readme, encoding="utf-8")
        words = len((sdir / "guide.md").read_text(encoding="utf-8").split())
        zpath = ROOT / "dist" / f"{slug}_bundle.zip"
        if zpath.exists():
            zpath.unlink()
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(pdir.iterdir()):
                z.write(f, f"{slug}/{f.name}")
        manifest = {"cohort": "GF_BATCH11_2026_09", "id": pid, "slug": slug,
                    "name": listing["name"], "price_cents": price,
                    "guide_words": words, "guide_pages": pages,
                    "bundle": zpath.name,
                    "bundle_bytes": zpath.stat().st_size,
                    "files": sorted(f.name for f in pdir.iterdir())}
        (pdir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"{pid}: {words} words, {pages} pages, bundle {zpath.stat().st_size//1024} KB")

def qa_all():
    import glob
    ok = True
    for pid, slug, price in PRODUCTS:
        sdir = SRC / pid
        pdir = OUT / pid
        man = json.loads((pdir / "manifest.json").read_text(encoding="utf-8"))
        guide = (sdir / "guide.md").read_text(encoding="utf-8")
        low = guide.lower()
        for b in BANNED:
            if b in low:
                print(f"FAIL {pid}: banned phrase '{b}'"); ok = False
        for ph in PLACEHOLDERS:
            if ph in guide:
                print(f"FAIL {pid}: placeholder '{ph}'"); ok = False
        for fn in ["listing.json", "workbook.json", "templates.json", "value.md"]:
            t = (sdir / fn).read_text(encoding="utf-8")
            for b in BANNED:
                if b in t.lower():
                    print(f"FAIL {pid}/{fn}: banned '{b}'"); ok = False
        listing = json.loads((sdir / "listing.json").read_text(encoding="utf-8"))
        for key in ["name", "short_description", "long_description", "buyer_persona",
                    "problem_statement", "outcome_statement", "whats_included",
                    "who_for", "who_not_for", "how_to_use", "limitations",
                    "disclaimer", "faq", "keywords", "category", "version",
                    "changelog", "support"]:
            if key not in listing:
                print(f"FAIL {pid}: listing missing '{key}'"); ok = False
        if man["guide_words"] < 5500:
            print(f"FAIL {pid}: thin guide {man['guide_words']} words"); ok = False
        if man["guide_pages"] < 10:
            print(f"FAIL {pid}: thin PDF {man['guide_pages']} pages"); ok = False
        zp = ROOT / "dist" / man["bundle"]
        with zipfile.ZipFile(zp) as z:
            names = z.namelist()
            assert any(n.endswith("_guide.pdf") for n in names), pid
            assert any(n.endswith(".xlsx") for n in names), pid
            assert any(n.endswith(".docx") for n in names), pid
            assert any(n.endswith("README.txt") for n in names), pid
            for n in names:
                assert z.read(n), f"{pid}/{n} empty"
        print(f"QA {pid}: words={man['guide_words']} pages={man['guide_pages']} "
              f"bundle={man['bundle_bytes']//1024}KB files={len(man['files'])} OK")
    print("QA RESULT:", "PASS" if ok else "FAIL")
    return ok

if __name__ == "__main__":
    if "--qa" in sys.argv:
        sys.exit(0 if qa_all() else 1)
    build_all()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge Batch 12 — sales pages + QA + registry. Deterministic, $0.
Pages state honest DRAFT status (no Gumroad listing exists yet — no buy
buttons, no fake scarcity, no reviews).

NON-DESTRUCTIVE BY DEFAULT (2026-10-19): QA now only updates each product's
``state``/``issues`` in the registry and never regenerates a page that already
exists. The registry is merged, not rebuilt: authoritative fields added by
later cycles (price_usd, price_basis, pricing_date, gate_*, hashes, ...) are
preserved. Pass ``--rebuild-pages`` to explicitly regenerate the generic
templates (this overwrites hand-authored pages — do not use it on live copy).

Writes: data/product_batch_12.json,
data/product_batch_12_execution.jsonl (append of this run's verdicts); pages
only with --rebuild-pages.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "customer_site"
BATCH = ROOT / "books" / "batch12"
DATA = ROOT / "data"

PRODUCTS = [
 dict(id="B12-001", slug="b12-freelancer-rate-calculator", title="Freelancer Rate & Raise Calculator",
      price=14.99, files=["B12-001_freelancer_rate_raise_calculator.xlsx"],
      problem="Freelancers guess their rates and undercharge for years.",
      value="A workbook that computes your minimum rate from YOUR costs, ranks clients by revenue-per-hassle, and schedules raises on triggers — not feelings.",
      audience="Freelancers and solo consultants worldwide.", use="Fill the Inputs sheet, quote at or above the computed rate, review triggers quarterly."),
 dict(id="B12-002", slug="b12-client-handoff-pack", title="Client Project Handoff Pack",
      price=11.99, files=["B12-002_client_handoff_guide.pdf", "B12-002_client_handoff_register.xlsx"],
      problem="Project handoffs done by email threads end in disputes over what was transferred.",
      value="A 45-minute session script, copy-paste emails, and an asset register covering code, docs, accounts, money, and people — signed off line by line.",
      audience="Freelancers, agencies, and contractors handing work to clients.", use="Run the 45-min session with the register open; nothing is done until client sign-off = Y."),
 dict(id="B12-003", slug="b12-access-continuity-organizer", title="Founder Access Continuity Organizer",
      price=29, files=["B12-003_access_continuity_organizer.pdf"],
      problem="If a solo founder is unreachable, nobody can keep the business alive — and writing passwords on paper is the unsafe answer.",
      value="An inventory system (never a password store): what exists, where it lives, who may touch it, plus the three-envelope method and an annual 30-minute drill.",
      audience="Solo founders and one-person businesses.", use="Fill the inventory tables, grant password-manager emergency access today, calendar the drill."),
 dict(id="B12-004", slug="b12-meeting-cost-calculator", title="Meeting Cost & ROI Calculator",
      price=11.99, files=["B12-004_meeting_cost_roi_calculator.xlsx", "B12-004_meeting_method_guide.pdf"],
      problem="Teams lose thousands of dollars a month to recurring meetings nobody priced.",
      value="Price every recurring meeting with loaded costs, find the expensive ones with no decision attached, and run a quarterly kill review — plus a polite decline script.",
      audience="Team leads, managers, and founders with calendars full of status calls.", use="Log meetings, sort by weekly cost, kill or shorten from the top."),
 dict(id="B12-005", slug="b12-podcast-guest-kit", title="Podcast Guest Booking Kit",
      price=29, files=["B12-005_podcast_guest_scripts.pdf", "B12-005_podcast_guest_tracker.xlsx"],
      problem="Cold podcast pitches get ignored because they are generic and followed up into spam.",
      value="Sub-120-word pitch, two capped follow-ups with close-out, post-appearance assets — plus a pipeline tracker. Two follow-ups max, then close.",
      audience="Founders, freelancers, and authors seeking podcast appearances.", use="Write 3 angles first, pitch, follow up day 7 and 21, then close."),
 dict(id="B12-006", slug="b12-home-office-organizer", title="Home-Office Deduction Organizer (US)",
      price=29, files=["B12-006_home_office_method_guide.pdf", "B12-006_home_office_expense_log.xlsx"],
      problem="Home-office deductions fail on missing receipts and misunderstood exclusive-use rules.",
      value="Actual-vs-simplified method guide, exclusive-use test explained, and a receipt-disciplined expense log. Procedure information only — not tax advice.",
      audience="US remote workers and self-employed filers.", use="Measure once, pick one method for the year, log within 7 days."),
 dict(id="B12-007", slug="b12-digital-declutter-system", title="Digital Declutter & Backup: 30-Day System",
      price=19, files=["B12-007_digital_declutter_plan.pdf", "B12-007_digital_inventory.xlsx"],
      problem="Accounts, files, and subscriptions pile up for years; backups that were never restore-tested are not backups.",
      value="A 4-week plan (accounts, files, backups, subscriptions) with a 4-sheet inventory and the 3-2-1 rule plus a real restore test.",
      audience="Overwhelmed professionals and households.", use="One week per surface; every decision lands in the workbook."),
 dict(id="B12-008", slug="b12-moving-house-planner", title="Moving House 8-Week Planner",
      price=29, files=["B12-008_moving_checklist.pdf", "B12-008_moving_budget_tracker.xlsx"],
      problem="Moves bleed money through single quotes, uninsured movers, and forgotten address changes.",
      value="Week-by-week checklist from notice to keys plus a budget tracker with mover comparison and address-change register.",
      audience="Renters and homeowners planning a move.", use="Get 2+ quotes per row, work address changes in week 2."),
 dict(id="B12-009", slug="b12-pet-sitter-handover-kit", title="Pet Sitter Handover Kit",
      price=19, files=["B12-009_pet_sitter_handover_kit.pdf"],
      problem="Sitters left without vet info, meds schedules, or authorization details cannot act in an emergency.",
      value="Print-and-fill emergency contacts, pet profiles, vet authorization worksheet, and house rules. Organizer only — confirm requirements with your own clinic.",
      audience="Pet owners who travel.", use="Print, fill by hand, fridge + photo in sitter's phone, walk through once."),
 dict(id="B12-010", slug="b12-grant-pipeline-tracker", title="Nonprofit Grant Pipeline Tracker",
      price=15, files=["B12-010_grant_pipeline_tracker.xlsx", "B12-010_grant_pipeline_guide.pdf"],
      problem="Grant work is lost to applications that were never eligible and to post-award reports that live in one person's memory.",
      value="One register for every funder and program, with a twelve-question eligibility screen, per-application document readiness, computed deadline states, and a reporting calendar that steps forward in whole intervals so a post-award report is never missed. Ships with a 17-page method guide covering every field, every formula rule, a worked 90-day example and the twenty mistakes that cost applications.",
      audience="Small nonprofits, fiscal sponsors and volunteer grant writers.", use="Screen eligibility before drafting; check the Dashboard weekly and the Timeline before any report is due."),
]

PAGE_TPL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — ${price} (proposed) | Galaxy Forge</title>
<meta name="description" content="{problem} {value}">
</head>
<body style="font-family:system-ui,sans-serif;max-width:720px;margin:2rem auto;padding:0 1rem;line-height:1.6">
<p style="border:1px solid #b45309;background:#fffbeb;padding:.75rem 1rem;border-radius:6px"><strong>DRAFT — not yet listed.</strong> This product is finished and quality-checked, but it has no Gumroad listing yet, so no purchase is possible from this page. The price below is proposed, not charged.</p>
<h1>{title}</h1>
<p><strong>{problem}</strong></p>
<p>{value}</p>
<h2>What you get</h2>
<ul>
{files_li}
</ul>
<h2>How to use</h2>
<p>{use}</p>
<p><strong>Proposed price: ${price}</strong> (one-time, not yet for sale)</p>
<p><a href="mailto:galaxyaek7@gmail.com?subject=INTEREST%20{mid}%20{slug}">Notify me when it lists</a> — one email when the Gumroad listing goes live, nothing else.</p>
<p><small>New product: 0 sales recorded to date; no reviews. {audience}</small></p>
</body>
</html>
"""

BANNED_CLAIMS = ["guaranteed", "fully automated income", "get rich", "IRS-approved",
                 "lawyer-approved", "100% success", "no risk"]


def build_pages():
    for p in PRODUCTS:
        files_li = "\n".join("  <li><code>%s</code></li>" % f for f in p["files"])
        html = PAGE_TPL.format(title=p["title"], price=p["price"], problem=p["problem"],
                               value=p["value"], files_li=files_li, use=p["use"],
                               mid=p["id"], slug=p["slug"], audience="Audience: " + p["audience"])
        (SITE / (p["slug"] + ".html")).write_text(html, encoding="utf-8")
    print("pages:", len(PRODUCTS))


def qa():
    sys.path.insert(0, str(ROOT))
    import openpyxl
    import pypdf
    results = []
    for p in PRODUCTS:
        issues = []
        for f in p["files"]:
            fp = BATCH / f
            if not fp.exists() or fp.stat().st_size == 0:
                issues.append("missing/empty: " + f)
                continue
            try:
                if f.endswith(".xlsx"):
                    wb = openpyxl.load_workbook(fp, data_only=False)
                    if len(wb.sheetnames) < 2:
                        issues.append("thin workbook (<2 sheets): " + f)
                    if "README" not in wb.sheetnames:
                        issues.append("missing README sheet: " + f)
                    unfilled = [c.coordinate for ws in wb.worksheets
                                for row in ws.iter_rows() for c in row
                                if isinstance(c.value, str) and c.value.startswith("=")
                                and (c.fill is None or c.fill.fgColor.rgb in (None, "00000000"))]
                    if unfilled:
                        issues.append("formula cells without blue fill %s: %s" % (unfilled, f))
                    has_formula = any(
                        isinstance(c.value, str) and c.value.startswith("=")
                        for ws in wb.worksheets for row in ws.iter_rows() for c in row)
                    if p["id"] in ("B12-001", "B12-004", "B12-006", "B12-008") and not has_formula:
                        issues.append("calculator without formulas: " + f)
                elif f.endswith(".pdf"):
                    r = pypdf.PdfReader(str(fp))
                    if len(r.pages) == 0:
                        issues.append("empty pdf: " + f)
                    txt = "".join((pg.extract_text() or "") for pg in r.pages)
                    if len(txt.strip()) < 1500:
                        issues.append("thin content (<1500 chars): " + f)
            except Exception as e:
                issues.append("unopenable %s: %s" % (f, e))
        page = SITE / (p["slug"] + ".html")
        if not page.exists():
            issues.append("sales page missing")
        else:
            t = page.read_text(encoding="utf-8").lower()
            for b in BANNED_CLAIMS:
                if b in t:
                    issues.append("banned claim: " + b)
            for f in p["files"]:
                if f.lower() not in t:
                    issues.append("page does not list file: " + f)
        state = "READY_FOR_REVIEW" if not issues else "HOLD"
        results.append({"id": p["id"], "state": state, "issues": issues})
    return results


def merge_registry(results, now):
    """Merge QA verdicts into the existing registry without losing any
    authoritative field a later cycle added (price/basis/gate/hashes/...)."""
    path = DATA / "product_batch_12.json"
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
        old = existing.get("products", [])
    except (OSError, json.JSONDecodeError):
        old = []
    by_id = {p.get("id"): dict(p) for p in old if isinstance(p, dict)}

    for p, r in zip(PRODUCTS, results):
        rec = by_id.get(p["id"], {})
        # Template values fill gaps only; they never overwrite existing data.
        for k in ("id", "title", "price", "files", "audience", "problem"):
            rec.setdefault(k, p[k])
        rec["state"] = r["state"]
        rec["issues"] = r["issues"]
        by_id[p["id"]] = rec

    order = [p["id"] for p in PRODUCTS]
    ordered = [by_id[i] for i in order if i in by_id]
    extras = [p for p in old if p.get("id") not in order]
    return {"generated_at": now, "batch": "B12", "products": ordered + extras}


def main():
    rebuild_pages = "--rebuild-pages" in sys.argv[1:]
    if rebuild_pages:
        build_pages()
    else:
        print("pages: preserved (pass --rebuild-pages to regenerate)")
    results = qa()
    now = datetime.now(timezone.utc).isoformat()
    reg = merge_registry(results, now)
    (DATA / "product_batch_12.json").write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(DATA / "product_batch_12_execution.jsonl", "a", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps({"at": now, "id": r["id"], "transition": "QA→" + r["state"],
                                "issues": r["issues"]}, ensure_ascii=False) + "\n")
    ok = sum(1 for r in results if r["state"] == "READY_FOR_REVIEW")
    print("qa: %d/%d READY_FOR_REVIEW" % (ok, len(results)))
    for r in results:
        if r["issues"]:
            print("HOLD", r["id"], r["issues"])


if __name__ == "__main__":
    main()

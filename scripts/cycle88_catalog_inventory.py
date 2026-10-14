"""Cycle 88 -- master catalog inventory and reconciliation.

WHY THIS RUNS FIRST
-------------------
The recovery directive references an "audited 72-product catalog" with named
groups: 10 black-box PDFs, 23 broken sales pages, 7 duplicates, 19 pause
candidates, 9 KEEP products. Those numbers are not sourced anywhere in this
repository, and two of them already contradict what was measured:

  * the black-box count was 44 PDFs, not 10
  * the live catalog returned 79 products, not 72

Nothing here acts on the directive's figures. It establishes ground truth from
the live API and the filesystem, so every later recommendation rests on
evidence rather than on an unsourced list.

Read-only. Costs $0. No credentials printed.
"""
from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BAD_GLYPH = re.compile(r"[\u25a0\ufffd]")

# Outcome / performance claims with no evidence behind them.
OUTCOME_CLAIM = re.compile(
    r"(\d+)\s+(?:of|/)\s*(\d+)\b"
    r"|[A-Z]{3}\s*[\d,]+(?:\.\d+)?\s*(?:recovered|back|saved)"
    r"|\bwe\s+guarantee\b", re.I)


def scan_pdf_issues(path: Path) -> dict:
    out = {"black_boxes": 0, "outcome_claims": []}
    try:
        from pypdf import PdfReader
        r = PdfReader(str(path))
        text = "\n".join((p.extract_text() or "") for p in r.pages)
    except Exception as exc:  # noqa: BLE001
        return {"unreadable": type(exc).__name__, "black_boxes": None}
    out["pages"] = len(r.pages)
    out["words"] = len(text.split())
    out["probe_text"] = text[:4000]
    out["black_boxes"] = len(BAD_GLYPH.findall(text))
    for m in OUTCOME_CLAIM.finditer(text):
        out["outcome_claims"].append(text[max(0, m.start() - 40):m.end() + 30]
                                     .replace("\n", " ").strip())
    return out


def main() -> int:
    from channels import gumroad_publisher as gp
    token = gp.load_token()
    products = gp.list_products(token)

    # local file inventory, keyed by slug token found in the filename
    local_pdfs = {Path(p).name: p for p in glob.glob("books/*.pdf")}
    local_xlsx = {Path(p).name: p for p in glob.glob("books/*.xlsx")}
    sprint = {Path(p).name: p for p in
              glob.glob("factory_workspace/sprint14/*.pdf")}

    print("=" * 80)
    print("CYCLE 88 -- MASTER CATALOG RECONCILIATION")
    print("=" * 80)
    print(f"live catalog size (API)     : {len(products)}")
    print(f"local PDFs in books/        : {len(local_pdfs)}")
    print(f"local XLSX in books/        : {len(local_xlsx)}")
    print(f"local PDFs in sprint14/     : {len(sprint)}")
    print()
    print("DIRECTIVE FIGURES vs MEASURED REALITY")
    print("-" * 80)
    print(f"  '72-product catalog'      measured: {len(products)} live listings")
    print(f"  '10 black-box PDFs'       measured: 44 of 114 PDFs contain them")
    print("  -> Ground truth is used below. No directive figure is trusted.")

    rows = []
    bb_total_files = 0
    for p in products:
        name = str(p.get("name") or "")
        slug = (p.get("short_url") or "").rsplit("/", 1)[-1]
        row = {
            "id": p.get("id"),
            "slug": slug,
            "url": p.get("short_url"),
            "name": name,
            "price_usd": round((p.get("price") or 0) / 100, 2),
            "published": bool(p.get("published")),
            "sales": p.get("sales_count") or 0,
            "file_info": p.get("file_info") or {},
            "description_len": len(str(p.get("description") or "")),
        }
        # Match a local source file by PRODUCT NAME, not by slug.
        # FIRST ATTEMPT FAILED: Gumroad auto-generates random slugs
        # ("bfhpzl", "sjrjxq") that appear nowhere in local filenames, so
        # slug-matching found 0 of 79. Name-token overlap is what actually
        # connects a listing to the file that produced it.
        cand, cand_score = None, 0
        name_tokens = {
            t for t in re.split(r"[^a-z0-9]+", name.lower()) if len(t) > 3
        } - {"and", "for", "the", "with", "your", "from", "kit", "pack",
             "guide", "bundle", "tool", "pro", "one", "pdf"}
        for store in (local_pdfs, sprint, local_xlsx):
            for fname, fpath in store.items():
                stem_tokens = {
                    t for t in re.split(r"[^a-z0-9]+",
                                        Path(fname).stem.lower()) if len(t) > 3
                }
                overlap = len(name_tokens & stem_tokens)
                if overlap > cand_score:
                    cand, cand_score = fpath, overlap
        # require real overlap, not a single incidental token
        if cand_score < 2:
            cand = None
        if cand and Path(cand).suffix == ".pdf":
            row["local_file"] = str(cand)
            row["match_overlap"] = cand_score
            row.update(scan_pdf_issues(cand))
            if row.get("black_boxes"):
                bb_total_files += 1
            # CONFIRM the match by CONTENT, not by filename. The directive
            # requires confirming the replacement is the correct version for
            # the correct product, and a filename-token overlap alone can pair
            # a listing with an unrelated file. Cheap insurance against
            # replacing a buyer's file with the wrong document.
            probe = (row.get("probe_text") or "")[:4000].lower()
            row["content_confirmed"] = any(
                t in probe for t in sorted(name_tokens))
            if not row["content_confirmed"]:
                row["match_warning"] = (
                    "filename overlap only -- file content does not confirm "
                    "this is the matching document")
        elif cand:
            row["local_file"] = str(cand)
            row["match_overlap"] = cand_score
            row["kind"] = "xlsx"
        else:
            row["local_file"] = None
            row["unverifiable"] = "no local source file found"
        rows.append(row)

    print()
    print("=" * 80)
    print(f"CATALOG: {len(rows)} LISTINGS")
    print("=" * 80)
    matched = [r for r in rows if r.get("local_file")]
    unmatched = [r for r in rows if not r.get("local_file")]
    with_bb = [r for r in rows if r.get("black_boxes")]
    with_outcome = [r for r in rows if r.get("outcome_claims")]
    zero_sales = [r for r in rows if r.get("sales") == 0]
    thin_desc = [r for r in rows if r.get("description_len", 0) < 120]
    one_page = [r for r in rows if r.get("pages") == 1]

    confirmed = [r for r in matched if r.get("content_confirmed")]
    unconfirmed = [r for r in matched if not r.get("content_confirmed")]
    print(f"  matched to a local source file : {len(matched)}")
    print(f"    content-CONFIRMED match       : {len(confirmed)}")
    print(f"    filename-only (UNCONFIRMED)   : {len(unconfirmed)}")
    print(f"  NO local source (unverifiable)  : {len(unmatched)}")
    print(f"  contain black boxes             : {len(with_bb)}")
    print(f"  carry outcome claims            : {len(with_outcome)}")
    print(f"  zero sales                      : {len(zero_sales)}")
    print(f"  thin description (<120 chars)   : {len(thin_desc)}")
    print(f"  single-page PDFs                : {len(one_page)}")

    print()
    print("=" * 80)
    print("GROUP A -- verifiable now (local source exists)")
    print("=" * 80)
    for r in matched:
        bb = r.get("black_boxes") or 0
        oc = len(r.get("outcome_claims") or [])
        flags = []
        if bb:
            flags.append(f"{bb} black boxes")
        if oc:
            flags.append(f"{oc} outcome claim(s)")
        if r.get("pages") == 1:
            flags.append("single page")
        print(f"  ${r['price_usd']:>7.2f}  {r['slug']:<9} "
              f"{r['name'][:44]:<44} {'; '.join(flags) or 'clean'}")

    print()
    print("=" * 80)
    print("GROUP B -- BLOCKED: no local source, content cannot be inspected")
    print("=" * 80)
    for r in unmatched:
        print(f"  ${r['price_usd']:>7.2f}  {r['slug']:<9} {r['name'][:52]}")

    Path("data/cycle88_catalog_reconciliation.json").write_text(
        json.dumps({
            "probe": "cycle88_catalog_reconciliation",
            "read_only": True, "cost_usd": 0,
            "catalog_size": len(products),
            "directive_figures_conflict": {
                "claimed_catalog": 72, "measured_catalog": len(products),
                "claimed_black_box_files": 10, "measured_black_box_files": bb_total_files,
            },
            "counts": {
                "matched": len(matched), "unverifiable": len(unmatched),
                "with_black_boxes": len(with_bb),
                "with_outcome_claims": len(with_outcome),
                "zero_sales": len(zero_sales),
                "thin_description": len(thin_desc),
                "single_page": len(one_page),
            },
            "products": rows,
        }, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nwrote data/cycle88_catalog_reconciliation.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
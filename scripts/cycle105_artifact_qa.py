"""Cycle 105 -- structural artifact QA across every discovered product.

WHY THIS EXISTS
---------------
Cycle 104 QA'd the ten batch-12 products. Two whole populations were never
structurally verified at all:

  * the 22 PDFs registered in data/asset_registry.json (only GF-001 had ever
    been inspected), and
  * the secondary files of the batch-12 set (covers, PDFs alongside XLSX).

This script walks every artifact it can identify from the real registries
and answers a deliberately narrow question: *is this file structurally sound
and internally consistent?* It reports:

  PDF  : page count, extracted words, whether a text layer exists, parse errors
  XLSX : zip integrity, sheet names, live formula count, chart count

It does NOT judge content quality, market fit or price. A structural PASS is
never a commercial claim. Two structural defect classes are surfaced because
this factory has produced both before:

  * STATIC_WORKBOOK   -- an XLSX with zero live formulas (the B12-007 defect)
  * NO_TEXT_LAYER     -- a PDF that serves images only (not searchable)

Cost: $0. No network. No LLM. Read-only.

Usage:
    python scripts/cycle105_artifact_qa.py            # summary
    python scripts/cycle105_artifact_qa.py --json
    python scripts/cycle105_artifact_qa.py --write    # reports/CYCLE105/ARTIFACT_QA.{json,md}
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

FACTORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FACTORY))

SCHEMA = "galaxy_forge.artifact_qa.v1"
SKIP_DIRS = ("_cycle104_backup", "_pre_cycle88_fix", "__pycache__")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tracked(root: Path) -> set:
    try:
        proc = subprocess.run(["git", "ls-files"], cwd=str(root),
                              capture_output=True, text=True, check=False)
    except OSError:
        return set()
    if proc.returncode != 0:
        return set()
    return {ln.strip().replace("\\", "/") for ln in proc.stdout.splitlines() if ln.strip()}


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except (ValueError, OSError):
        return str(path).replace("\\", "/")


def pdf_report(path: Path) -> dict:
    from pypdf import PdfReader
    result = {"kind": "pdf", "pages": None, "words": None, "text_layer": None,
              "parse_warnings": 0}
    try:
        reader = PdfReader(str(path))
        result["pages"] = len(reader.pages)
        text = []
        for page in reader.pages:
            try:
                text.append(page.extract_text() or "")
            except Exception:  # noqa: BLE001 -- a single bad page must not abort the file
                result["parse_warnings"] += 1
        joined = "\n".join(text)
        result["words"] = len(joined.split())
        result["text_layer"] = bool(joined.strip())
    except Exception as exc:  # noqa: BLE001
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def xlsx_report(path: Path) -> dict:
    from openpyxl import load_workbook
    result = {"kind": "xlsx", "sheets": None, "sheet_names": [], "formulas": None,
              "charts": 0}
    try:
        with zipfile.ZipFile(path) as archive:
            result["zip_ok"] = archive.testzip() is None
    except (zipfile.BadZipFile, OSError) as exc:
        result["zip_ok"] = False
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result
    try:
        book = load_workbook(str(path), data_only=False, read_only=False)
        result["sheet_names"] = list(book.sheetnames)
        result["sheets"] = len(book.sheetnames)
        formulas = 0
        for sheet in book.worksheets:
            for row in sheet.iter_rows():
                for cell in row:
                    if isinstance(cell.value, str) and cell.value.startswith("="):
                        formulas += 1
        result["formulas"] = formulas
        result["charts"] = sum(len(getattr(s, "_charts", [])) for s in book.worksheets)
        book.close()
    except Exception as exc:  # noqa: BLE001
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def inspect(path: Path, tracked: set, root: Path) -> dict:
    suffix = path.suffix.lower()
    stat = path.stat()
    record = {
        "path": _rel(path, root),
        "bytes": stat.st_size,
        "sha256": _sha256(path),
        "git_tracking": "TRACKED" if _rel(path, root) in tracked else "UNTRACKED",
        "verdict": "STRUCTURALLY_OK",
        "defects": [],
    }
    if suffix == ".pdf":
        record.update(pdf_report(path))
        if record.get("error"):
            record["verdict"] = "UNREADABLE"
            record["defects"].append("PDF_UNREADABLE")
        else:
            if not record.get("pages"):
                record["verdict"] = "STRUCTURAL_FAIL"
                record["defects"].append("ZERO_PAGES")
            if not record.get("words"):
                record["verdict"] = "STRUCTURAL_FAIL"
                record["defects"].append("NO_TEXT_LAYER")
            if record.get("parse_warnings"):
                record["defects"].append("PARTIAL_PAGE_PARSE")
    elif suffix == ".xlsx":
        record.update(xlsx_report(path))
        if record.get("error") or record.get("zip_ok") is False:
            record["verdict"] = "UNREADABLE"
            record["defects"].append("XLSX_UNREADABLE")
        elif record.get("formulas") == 0 and (record.get("sheets") or 0) > 1:
            # A multi-sheet workbook with no formula at all is the
            # "calculator that does not calculate" defect class.
            record["verdict"] = "STRUCTURAL_FAIL"
            record["defects"].append("STATIC_WORKBOOK")
    else:
        record["kind"] = suffix.lstrip(".") or "unknown"
    return record


def collect_targets(root: Path) -> list:
    """Every artifact this factory can name from its own registries."""
    targets = []
    seen = set()

    def add(path: Path, origin: str, product: str):
        key = _rel(path, root)
        if key in seen or not path.exists():
            return
        seen.add(key)
        targets.append({"path": path, "origin": origin, "product": product})

    registry = root / "data" / "asset_registry.json"
    try:
        assets = json.loads(registry.read_text(encoding="utf-8-sig")).get("assets") or []
    except (OSError, json.JSONDecodeError):
        assets = []
    for asset in assets:
        file_name = (asset.get("product_genome") or {}).get("file")
        if file_name:
            add(root / file_name, "asset_registry", asset.get("asset_id"))

    batch_dir = root / "books" / "batch12"
    if batch_dir.is_dir():
        for path in sorted(batch_dir.rglob("*")):
            if path.is_file() and not any(part in SKIP_DIRS for part in path.parts):
                add(path, "books/batch12", path.stem.split("_")[0])

    return targets


def build_report(root: Path = None, now=None) -> dict:
    root = Path(root) if root else FACTORY
    now = now or datetime.now(timezone.utc)
    tracked = _tracked(root)
    results = [inspect(t["path"], tracked, root) | {"origin": t["origin"],
                                                   "product": t["product"]}
               for t in collect_targets(root)]
    by_verdict, by_defect = {}, {}
    for row in results:
        by_verdict[row["verdict"]] = by_verdict.get(row["verdict"], 0) + 1
        for defect in row["defects"]:
            by_defect[defect] = by_defect.get(defect, 0) + 1
    return {
        "schema": SCHEMA,
        "generated_at": now.isoformat(),
        "cost_usd": 0,
        "read_only": True,
        "network_calls": 0,
        "scope": ("structural soundness only -- never a content-quality, pricing "
                  "or commercial verdict"),
        "totals": {
            "artifacts": len(results),
            "by_verdict": by_verdict,
            "by_defect": by_defect,
            "untracked": sum(1 for r in results if r["git_tracking"] == "UNTRACKED"),
        },
        "results": results,
    }


def _md(report: dict) -> str:
    totals = report["totals"]
    lines = ["# Cycle 105 -- Structural Artifact QA", "",
             f"Generated: {report['generated_at']}",
             f"Artifacts inspected: {totals['artifacts']}",
             f"Cost: $0, network calls: 0", "",
             "Scope: structural soundness only. A PASS here is not a claim "
             "about content quality, price or market fit.", "",
             "## Summary", "", "| Verdict | Count |", "|---|---|"]
    for verdict, count in sorted(totals["by_verdict"].items()):
        lines.append(f"| {verdict} | {count} |")
    lines += ["", "| Defect | Count |", "|---|---|"]
    for defect, count in sorted(totals["by_defect"].items()):
        lines.append(f"| {defect} | {count} |")
    lines += ["", "## Artifacts", "",
              "| Product | Origin | Artifact | Kind | Pages/Words | Formulas | Verdict | Defects | Git |",
              "|---|---|---|---|---|---|---|---|---|"]
    for row in report["results"]:
        size = (f"{row.get('pages')}p/{row.get('words')}w"
                if row.get("kind") == "pdf" else f"{row.get('sheets')} sheets")
        lines.append("| {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            row["product"], row["origin"], row["path"], row["kind"], size,
            row.get("formulas", "-"), row["verdict"],
            ", ".join(row["defects"]) or "none", row["git_tracking"]))
    return "\n".join(lines).rstrip("\n") + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--out-dir", default="reports/CYCLE105")
    args = parser.parse_args(argv)

    report = build_report()
    if args.json:
        print(json.dumps(report, indent=1, ensure_ascii=False))
    else:
        totals = report["totals"]
        print(f"artifacts={totals['artifacts']} verdicts={totals['by_verdict']} "
              f"defects={totals['by_defect']} untracked={totals['untracked']}")
        for row in report["results"]:
            if row["defects"]:
                print(f"  {row['verdict']:<16} {row['path']} {row['defects']}")
    if args.write:
        out_dir = FACTORY / args.out_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "ARTIFACT_QA.json").write_text(
            json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        (out_dir / "ARTIFACT_QA.md").write_text(_md(report), encoding="utf-8")
        print(f"wrote {out_dir/'ARTIFACT_QA.json'} and .md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

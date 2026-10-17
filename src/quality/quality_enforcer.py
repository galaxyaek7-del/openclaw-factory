"""Galaxy Forge -- Quality Enforcer (Master Sprint, Plan A2, 2026-10-17).

Three layers, each scored 0-100 from facts the product actually carries:

  Layer 1  Core Value      (concept, pre-production)   pass >= 70
  Layer 2  Content Quality (files, post-production)    pass >= 70
  Layer 3  Market Reality  (evidence, pre-production)  pass >= 65

Verdicts
  APPROVED              every layer that was run passed
  REWRITE               a layer failed, but by at most REWRITE_MARGIN points
  NOT_READY             a layer failed by more, or a file is broken
  KILL                  Layer 1 below KILL_BELOW: no real value proposition
  BLOCKED_MISSING_DATA  a layer could not be scored because the facts it
                        needs do not exist. Kept apart from a FAIL so a
                        missing fact is never reported as a bad product,
                        and never as a good one.

Anything other than APPROVED blocks. There is no override argument.

What this module reuses rather than re-implements
  * file_testing_engine.test_file / blocking_problems: opens every file
    with a real parser (PDF, XLSX, DOCX, ZIP, HTML) and fails closed.
  * market_evidence.get_payment_evidence: real, human-recorded proof that
    someone already pays for this problem (ADR-121).

Honest limits
  * Competitor prices are used only when they carry a source URL. No such
    priced data exists in the factory today (data/competitor_database.json
    holds names from HN/GitHub, no prices), so Layer 3 usually reports
    BLOCKED_MISSING_DATA until a human records sourced prices.
  * The words-per-dollar depth rule (price x 100 words) applies to text
    formats only (PDF, DOCX, HTML, MD, TXT). A spreadsheet is judged by its
    sheets and formulas instead; counting words in a calculator is meaningless.

Every call to inspect() writes a JSON report (reports/quality/inspections/).
"""
from __future__ import annotations

import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_REPORT_DIR = ROOT / "reports" / "quality" / "inspections"

THRESHOLDS = {"core_value": 70, "content_quality": 70, "market_reality": 65}
REWRITE_MARGIN = 15
KILL_BELOW = 40

APPROVED, REWRITE, NOT_READY, KILL = "APPROVED", "REWRITE", "NOT_READY", "KILL"
BLOCKED_MISSING_DATA = "BLOCKED_MISSING_DATA"
PASS, FAIL, MISSING, SKIPPED = "PASS", "FAIL", "MISSING_DATA", "NOT_RUN"

TEXT_SUFFIXES = {".pdf", ".docx", ".html", ".htm", ".md", ".txt"}
SHEET_SUFFIXES = {".xlsx", ".xlsm"}
WORDS_PER_DOLLAR = 100

_GENERIC_AUDIENCE = re.compile(r"^\s*(everyone|anyone|all|people|users|customers|everybody)\W*$", re.I)
_PLACEHOLDER = re.compile(
    r"lorem ipsum|\bTODO\b|\bTBD\b|\[insert|\{\{|\}\}|placeholder|xxx+|<your |your name here",
    re.I)
_MOJIBAKE = re.compile("Ã.|â€|Ø§|Ù.")
_INSTRUCTIONS = re.compile(r"how to use|instructions|getting started|quick start|read ?me|step 1", re.I)


def _words(text: str) -> list[str]:
    return re.findall(r"[^\W_]+", text or "")


def _layer(status, score, checks, reason=None):
    out = {"status": status, "score": score, "checks": checks}
    if reason:
        out["reason"] = reason
    return out


# --- Layer 1: core value -----------------------------------------------------
def core_value_layer(product: dict) -> dict:
    title = (product.get("title") or product.get("name") or "").strip()
    audience = (product.get("audience") or "").strip()
    problem = (product.get("problem") or "").strip()
    outcome = (product.get("outcome") or product.get("description") or "").strip()
    price = product.get("price")

    if not audience and not problem:
        return _layer(MISSING, None, {}, "no audience and no problem recorded; value cannot be judged")

    checks = {
        "audience_specific": bool(audience) and len(_words(audience)) >= 3 and not _GENERIC_AUDIENCE.match(audience),
        "problem_stated": len(_words(problem)) >= 6,
        "outcome_stated": len(_words(outcome)) >= 6,
        "title_specific": 3 <= len(_words(title)) and len(title) <= 60,
        "priced": isinstance(price, (int, float)) and price > 0,
    }
    weights = {"audience_specific": 25, "problem_stated": 25, "outcome_stated": 25,
               "title_specific": 15, "priced": 10}
    score = sum(w for k, w in weights.items() if checks[k])
    return _layer(PASS if score >= THRESHOLDS["core_value"] else FAIL, score, checks)


# --- Layer 2: content quality ------------------------------------------------
def _extract_text(path: Path) -> str | None:
    """Text from a text-format file, or None when it cannot be read."""
    suf = path.suffix.lower()
    try:
        if suf == ".pdf":
            from pypdf import PdfReader
            return "\n".join((pg.extract_text() or "") for pg in PdfReader(str(path)).pages)
        if suf == ".docx":
            import docx
            d = docx.Document(str(path))
            parts = [p.text for p in d.paragraphs]
            for t in d.tables:
                parts += [c.text for row in t.rows for c in row.cells]
            return "\n".join(parts)
        if suf in (".html", ".htm"):
            raw = path.read_text(encoding="utf-8", errors="replace")
            return re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style).*?</\1>", " ", raw))
        if suf in (".md", ".txt"):
            return path.read_text(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 -- unreadable text is reported, never assumed fine
        return None
    return None


def _sheet_facts(path: Path) -> dict | None:
    try:
        import openpyxl
        wb = openpyxl.load_workbook(str(path), data_only=False, read_only=True)
        texts, formulas = [], 0
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                for v in row:
                    if isinstance(v, str):
                        if v.startswith("="):
                            formulas += 1
                        else:
                            texts.append(v)
        names = list(wb.sheetnames)
        wb.close()
        return {"sheets": names, "formulas": formulas, "text": "\n".join(texts)}
    except Exception:  # noqa: BLE001
        return None


def _expand(paths: list[Path], scratch: list) -> list[Path]:
    """Files to judge: plain files as-is, plus the members of any ZIP."""
    out = []
    for p in paths:
        out.append(p)
        if p.suffix.lower() == ".zip" and p.exists():
            try:
                import tempfile
                tmp = Path(tempfile.mkdtemp(prefix="gf_qe_"))
                scratch.append(tmp)
                with zipfile.ZipFile(p) as z:
                    for m in z.infolist():
                        name = Path(m.filename)
                        if m.is_dir() or ".." in name.parts or name.is_absolute():
                            continue
                        if name.suffix.lower() in TEXT_SUFFIXES | SHEET_SUFFIXES:
                            dest = tmp / name.name
                            dest.write_bytes(z.read(m))
                            out.append(dest)
            except zipfile.BadZipFile:
                pass  # file_testing_engine reports the broken archive
    return out


def content_quality_layer(product: dict, files: list) -> dict:
    if not files:
        return _layer(MISSING, None, {}, "no product files given; content cannot be judged")
    import file_testing_engine as fte

    paths = [Path(f) if Path(f).is_absolute() else ROOT / f for f in files]
    file_results, broken = [], []
    for p in paths:
        r = fte.test_file(p)
        if r.kind == "unknown" and p.suffix.lower() in (".md", ".txt") and p.exists():
            # No dedicated tester exists for plain text; it is read directly
            # below, and an unreadable one is reported there.
            file_results.append({"file": p.name, "status": "READ_AS_TEXT", "problems": []})
            continue
        problems = fte.blocking_problems(r) if r.status == fte.FAIL else (
            r.problems if r.status == fte.UNKNOWN else [])
        file_results.append({"file": str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p),
                             "status": r.status, "problems": problems})
        if r.status != fte.PASS:
            broken.append(p.name)

    scratch: list = []
    try:
        members = _expand(paths, scratch)
        words, formulas, sheets, unreadable, text = 0, 0, 0, [], []
        has_text_format = has_sheet = False
        for m in members:
            suf = m.suffix.lower()
            if suf in TEXT_SUFFIXES:
                has_text_format = True
                t = _extract_text(m)
                if t is None:
                    unreadable.append(m.name)
                else:
                    text.append(t)
                    words += len(_words(t))
            elif suf in SHEET_SUFFIXES:
                has_sheet = True
                f = _sheet_facts(m)
                if f is None:
                    unreadable.append(m.name)
                else:
                    formulas += f["formulas"]
                    sheets += len(f["sheets"])
                    text.append(f["text"] + "\n" + " ".join(f["sheets"]))
    finally:
        import shutil
        for d in scratch:
            shutil.rmtree(d, ignore_errors=True)

    joined = "\n".join(text)
    price = product.get("price") if isinstance(product.get("price"), (int, float)) else 0
    depth = {}
    if has_text_format:
        need = int(price * WORDS_PER_DOLLAR)
        depth["words"] = words
        depth["words_required"] = need
        depth["text_depth_ok"] = words >= need if need else words >= 300
    if has_sheet:
        depth["sheets"] = sheets
        depth["formulas"] = formulas
        depth["sheet_depth_ok"] = sheets >= 2 and formulas >= 5
    depth_ok = all(v for k, v in depth.items() if k.endswith("_ok")) if depth else False

    placeholders = sorted(set(m.group(0) for m in _PLACEHOLDER.finditer(joined)))[:10]
    mojibake = len(_MOJIBAKE.findall(joined))
    checks = {
        "files_open_cleanly": not broken,
        "depth_sufficient": depth_ok,
        "no_placeholders": not placeholders,
        "no_mojibake": mojibake == 0,
        "instructions_present": bool(_INSTRUCTIONS.search(joined)),
    }
    # Depth carries 40 so a thin product cannot pass on clean files alone
    # (100 - 40 = 60 < 70). Broken files block regardless of score.
    weights = {"files_open_cleanly": 30, "depth_sufficient": 40, "no_placeholders": 10,
               "no_mojibake": 10, "instructions_present": 10}
    score = sum(w for k, w in weights.items() if checks[k])
    detail = {"files": file_results, "depth": depth, "placeholders_found": placeholders,
              "mojibake_hits": mojibake, "unreadable": unreadable}
    status = PASS if score >= THRESHOLDS["content_quality"] and not broken else FAIL
    out = _layer(status, score, checks)
    out["detail"] = detail
    return out


# --- Layer 3: market reality -------------------------------------------------
def sourced_competitors(competitors) -> list[dict]:
    """Only competitors with a source URL and a numeric price count."""
    out = []
    for c in competitors or []:
        price = c.get("price_usd", c.get("price"))
        url = c.get("url") or c.get("source_url")
        if isinstance(price, (int, float)) and price > 0 and isinstance(url, str) and url.startswith("http"):
            out.append({"name": c.get("name"), "url": url, "price_usd": float(price)})
    return out


def market_reality_layer(product: dict, payment_evidence=None) -> dict:
    comps = sourced_competitors(product.get("competitors"))
    if payment_evidence is None:
        payment_evidence = []
        niche = product.get("niche")
        if niche:
            try:
                import market_evidence
                payment_evidence = market_evidence.get_payment_evidence(niche)
            except Exception:  # noqa: BLE001
                payment_evidence = []

    if not comps and not payment_evidence:
        return _layer(MISSING, None, {"sourced_competitors": 0, "payment_evidence": 0},
                      "no sourced competitor prices and no recorded proof of payment")

    price = product.get("price")
    checks = {
        "payment_evidence": len(payment_evidence) > 0,
        "three_sourced_competitors": len(comps) >= 3,
        "two_sourced_competitors": len(comps) >= 2,
        "one_sourced_competitor": len(comps) >= 1,
        "price_within_market": False,
    }
    if comps and isinstance(price, (int, float)):
        lo, hi = min(c["price_usd"] for c in comps), max(c["price_usd"] for c in comps)
        checks["price_within_market"] = price <= hi * 1.10
    # Founder directive 2026-10-17: three sourced competitors at a comparable
    # price are enough on their own (15+15+10+30 = 70 >= 65); two are not (60).
    weights = {"payment_evidence": 40, "three_sourced_competitors": 10, "two_sourced_competitors": 15,
               "one_sourced_competitor": 15, "price_within_market": 30}
    score = sum(w for k, w in weights.items() if checks[k])
    out = _layer(PASS if score >= THRESHOLDS["market_reality"] else FAIL, score, checks)
    out["detail"] = {"sourced_competitors": comps, "payment_evidence_count": len(payment_evidence)}
    return out


# --- verdict -----------------------------------------------------------------
def verdict(layers: dict) -> tuple[str, list[str]]:
    reasons = []
    run = {k: v for k, v in layers.items() if v["status"] != SKIPPED}
    cv = layers.get("core_value", {})
    if cv.get("status") == FAIL and cv["score"] < KILL_BELOW:
        return KILL, [f"core_value {cv['score']} < {KILL_BELOW}: no real value proposition"]
    missing = [k for k, v in run.items() if v["status"] == MISSING]
    if missing:
        return BLOCKED_MISSING_DATA, [f"{k}: {run[k].get('reason')}" for k in missing]
    failed = {k: v for k, v in run.items() if v["status"] == FAIL}
    if not failed:
        return APPROVED, []
    worst = NOT_READY if any(
        (THRESHOLDS[k] - v["score"]) > REWRITE_MARGIN or
        (k == "content_quality" and not v["checks"].get("files_open_cleanly", True))
        for k, v in failed.items()) else REWRITE
    reasons = [f"{k} {v['score']} < {THRESHOLDS[k]}" for k, v in failed.items()]
    return worst, reasons


def inspect(product: dict, *, files=None, stage: str = "full", payment_evidence=None,
            report_dir=None, save: bool = True) -> dict:
    """Inspect one product. stage: 'pre_production' (layers 1+3),
    'post_production' (layer 2) or 'full' (all three)."""
    if stage not in ("pre_production", "post_production", "full"):
        raise ValueError(f"unknown stage {stage!r}")
    files = files if files is not None else product.get("files")
    skipped = _layer(SKIPPED, None, {}, f"not part of stage {stage}")
    layers = {
        "core_value": core_value_layer(product) if stage != "post_production" else skipped,
        "content_quality": content_quality_layer(product, files or []) if stage != "pre_production" else skipped,
        "market_reality": market_reality_layer(product, payment_evidence) if stage != "post_production" else skipped,
    }
    v, reasons = verdict(layers)
    report = {
        "inspected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "product_id": product.get("id") or product.get("product_id"),
        "title": product.get("title") or product.get("name"),
        "stage": stage, "thresholds": THRESHOLDS,
        "verdict": v, "blocked": v != APPROVED, "reasons": reasons, "layers": layers,
    }
    if save:
        d = Path(report_dir) if report_dir else DEFAULT_REPORT_DIR
        d.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^A-Za-z0-9_-]+", "_", str(report["product_id"] or report["title"] or "product"))[:60]
        path = d / f"{slug}_{stage}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')}.json"
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        report["report_path"] = str(path)
    return report


# --- directive-facing class API (Quality Enforcement sprint, 2026-10-17) -----
_FIELD_ALIASES = {
    "problem": ("problem", "problem_statement"),
    "audience": ("audience", "target_audience"),
    "outcome": ("outcome", "measurable_value", "value"),
    "price": ("price", "price_usd"),
    "title": ("title", "name", "product_name"),
    "id": ("id", "product_id"),
    "files": ("files", "file", "deliverables"),
}
_VERDICT_LABEL = {KILL: "KILLED"}


def _normalize(product: dict) -> dict:
    """Accept either naming convention (problem / problem_statement,
    audience / target_audience, outcome / measurable_value, price /
    price_usd) so the class works against a product dict in any real shape."""
    out = dict(product or {})
    for target, keys in _FIELD_ALIASES.items():
        if out.get(target) not in (None, "", []):
            continue
        for k in keys:
            if product.get(k) not in (None, "", []):
                out[target] = product[k]
                break
    return out


class QualityEnforcer:
    """Directive-facing wrapper over inspect().

    A non-APPROVED verdict always means ``allowed_to_publish`` is False.
    There is no bypass, no override argument, and no way to skip a layer —
    same guarantee the module itself already carries. ``final_verdict`` maps
    the internal KILL to the directive's KILLED; every other verdict name is
    unchanged. Reports are NOT written by default (pass save_reports=True to
    persist one under reports/quality/inspections/).
    """

    def __init__(self, *, report_dir=None, save_reports: bool = False):
        self.report_dir = report_dir
        self.save_reports = save_reports

    def full_inspection(self, product: dict, content: str = "", *,
                        files=None, payment_evidence=None) -> dict:
        p = _normalize(product)
        fl = [str(f) for f in (files if files is not None else p.get("files") or []) if f]
        scratch: list = []
        try:
            if content:
                import tempfile
                tmp = Path(tempfile.mkdtemp(prefix="gf_qe_content_"))
                scratch.append(tmp)
                cpath = tmp / "content.md"
                cpath.write_text(content, encoding="utf-8")
                fl = fl + [str(cpath)]
            report = inspect(p, files=fl or None, stage="full",
                             payment_evidence=payment_evidence,
                             report_dir=self.report_dir, save=self.save_reports)
        finally:
            import shutil
            for d in scratch:
                shutil.rmtree(d, ignore_errors=True)
        v = report["verdict"]
        return {
            "product_id": report.get("product_id"),
            "final_verdict": _VERDICT_LABEL.get(v, v),
            "verdict": v,
            "allowed_to_publish": v == APPROVED,
            "reason": "; ".join(report.get("reasons") or []) or None,
            "layers": {k: layer["status"] for k, layer in report["layers"].items()},
            "scores": {k: layer["score"] for k, layer in report["layers"].items()},
            "detail": report["layers"],
        }


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Inspect one product (JSON) with the 3-layer quality enforcer")
    ap.add_argument("product_json", help="path to a JSON file holding one product dict")
    ap.add_argument("--stage", default="full", choices=["pre_production", "post_production", "full"])
    a = ap.parse_args()
    prod = json.loads(Path(a.product_json).read_text(encoding="utf-8"))
    r = inspect(prod, stage=a.stage)
    print(json.dumps({k: r[k] for k in ("product_id", "verdict", "reasons", "report_path")}, indent=2, ensure_ascii=False))
    sys.exit(0 if r["verdict"] == APPROVED else 1)

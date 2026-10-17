"""Product content audit (founder request 2026-10-17: "make sure the products
are not empty of content and are of quality").

For every PUBLISHED Gumroad listing (read-only GETs):
  1. what Gumroad actually delivers: files (byte sizes; the API hides names),
     page count, rich-content blocks, delivery URL;
  2. the delivered file itself: each file is read once (read-only GET of our
     own product file, size checked against Gumroad's record) into a cache
     outside the repo. With --no-download, a local copy is used instead
     (exact byte size, else the closest local build, labelled APPROXIMATE);
  3. real content measures from opening that file: pages, words, words per
     page, blank pages, repeated pages, title-term coverage, placeholders.

Verdicts (per listing):
  EMPTY       Gumroad delivers nothing (no file, no rich content, no delivery URL)
  FILLER      mostly repeated or blank pages (>= 50%)
  OFF_TOPIC   under half of the title's key terms appear in the content
  THIN        fewer than 600 words in total, or under 80 words per page
  OK          none of the above
  UNVERIFIED  no local copy of the delivered file could be found to open

Writes reports/quality/PRODUCT_CONTENT_AUDIT.json. Changes nothing on Gumroad.

    python scripts/product_content_audit.py
"""
import hashlib
import io
import json
import os
import re
import sys
import time
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "reports" / "quality" / "PRODUCT_CONTENT_AUDIT.json"
SKIP_DIRS = {"node_modules", ".git", "venv", "__pycache__", "backups", "_pre_title_fix_2026-10-17", "_pre_cycle88_fix"}
EXTS = (".pdf", ".zip", ".xlsx", ".docx", ".md", ".html", ".csv")
STOP = set("the a an and or for of to in on with your kit pack system toolkit guide checklist bundle playbook action "
           "v2 one 5 by from at as is are be its it this that".split())
PLACEHOLDER = re.compile(r"lorem ipsum|\bTODO\b|\bTBD\b|\[insert|placeholder|xxx+", re.I)


def _words(s):
    return re.findall(r"[^\W_]+", s or "")


def title_terms(title):
    return {w for w in (t.lower() for t in _words(title)) if len(w) > 2 and w not in STOP and not w.isdigit()}


def pdf_pages(data):
    from pypdf import PdfReader
    return [(pg.extract_text() or "") for pg in PdfReader(io.BytesIO(data)).pages]


def xlsx_text(data):
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=False, read_only=True)
    sheets, formulas = [], 0
    for ws in wb.worksheets:
        cells = []
        for row in ws.iter_rows(values_only=True):
            for v in row:
                if v is None:
                    continue
                if isinstance(v, str) and v.startswith("="):
                    formulas += 1
                else:
                    cells.append(str(v))
        sheets.append(" ".join(cells))
    wb.close()
    return sheets, formulas


def docx_text(data):
    import docx
    d = docx.Document(io.BytesIO(data))
    parts = [p.text for p in d.paragraphs] + [c.text for t in d.tables for r in t.rows for c in r.cells]
    return ["\n".join(parts)]


def units_of(name, data):
    """A list of (unit_label, text) for one file; ZIPs are expanded."""
    low = name.lower()
    try:
        if low.endswith(".pdf"):
            return [(f"p{i + 1}", t) for i, t in enumerate(pdf_pages(data))], {}
        if low.endswith(".xlsx"):
            sheets, f = xlsx_text(data)
            return [(f"sheet{i + 1}", t) for i, t in enumerate(sheets)], {"formulas": f}
        if low.endswith(".docx"):
            return [("doc", t) for t in docx_text(data)], {}
        if low.endswith((".md", ".txt", ".csv", ".html")):
            return [("text", data.decode("utf-8", "replace"))], {}
        if low.endswith(".zip"):
            units, extra = [], {"members": []}
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                for m in z.infolist():
                    if m.is_dir() or "__MACOSX" in m.filename:
                        continue
                    extra["members"].append(m.filename)
                    u, e = units_of(m.filename, z.read(m))
                    units += [(f"{m.filename}:{lab}", t) for lab, t in u]
                    extra["formulas"] = extra.get("formulas", 0) + e.get("formulas", 0)
            return units, extra
    except Exception as e:  # noqa: BLE001 -- unreadable is reported, never assumed fine
        return [], {"error": f"{type(e).__name__}: {e}"}
    return [], {"error": "unsupported type"}


def measure(title, units, extra):
    texts = [t for _, t in units]
    words = [len(_words(t)) for t in texts]
    total = sum(words)
    n = len(texts)
    import difflib
    norm = [re.sub(r"\s+", " ", t).strip().lower() for t in texts]
    # Near-duplicates count as repeats (seen: 9 habit-tracker pages that differ
    # only in small details). A unit repeats if it is >= 0.9 similar to an
    # earlier non-blank unit.
    repeated = 0
    for i, a in enumerate(norm):
        if len(_words(a)) < 15:
            continue
        if any(len(_words(b)) >= 15 and difflib.SequenceMatcher(None, a, b).ratio() >= 0.9 for b in norm[:i]):
            repeated += 1
    blank = sum(1 for w in words if w < 15)
    # Topic coverage over the whole file. (Excluding the cover page was tried
    # and flagged on-topic 3-page kits whose title terms sit on page 1; a
    # cover-only "match" with filler pages is caught by FILLER instead.)
    all_text = " ".join(texts).lower()
    terms = title_terms(title)
    covered = sorted(t for t in terms if t in all_text)
    return {
        "units": n, "words": total, "words_per_unit": round(total / n, 1) if n else 0,
        "blank_units": blank, "repeated_units": repeated,
        "filler_share": round((blank + repeated) / n, 2) if n else 1.0,
        "title_terms": sorted(terms), "title_terms_covered": covered,
        "title_coverage": round(len(covered) / len(terms), 2) if terms else 1.0,
        "placeholders": sorted(set(m.group(0) for m in PLACEHOLDER.finditer(all_text)))[:5],
        **{k: v for k, v in extra.items() if k in ("formulas", "members", "error")},
    }


def verdict(m, has_delivery):
    if not has_delivery:
        return "EMPTY", ["Gumroad delivers no file, no content block and no delivery link"]
    if m is None:
        return "UNVERIFIED", ["no local copy of the delivered file was found to open"]
    if m.get("error") or m["units"] == 0:
        return "UNVERIFIED", [m.get("error") or "no readable content units"]
    reasons, v = [], "OK"
    if m["filler_share"] >= 0.5:
        v = "FILLER"; reasons.append(f"{m['blank_units']} blank + {m['repeated_units']} repeated of {m['units']} pages/units")
    elif m["title_coverage"] < 0.5:
        v = "OFF_TOPIC"; reasons.append(f"only {m['title_terms_covered']} of title terms {m['title_terms']} appear")
    elif m["words"] < 600 or (m["words_per_unit"] < 80 and not m.get("formulas")):
        v = "THIN"; reasons.append(f"{m['words']} words, {m['words_per_unit']} per page/unit")
    if m["placeholders"]:
        reasons.append(f"placeholders: {m['placeholders']}")
    return v, reasons


def local_index():
    by_size, by_ext = defaultdict(list), defaultdict(list)
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.lower().endswith(EXTS):
                p = Path(root) / f
                try:
                    by_size[p.stat().st_size].append(p)
                    by_ext[p.suffix.lower()].append(p)
                except OSError:
                    pass
    return by_size, by_ext


def pdf_page_count(p):
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(p)).pages)
    except Exception:  # noqa: BLE001
        return None


def find_local(title, ftype, size, pages, by_size, by_ext):
    terms = title_terms(title)
    exact = [p for p in by_size.get(size, []) if p.suffix.lower() == f".{ftype}"]
    if exact:
        # Small files can share a byte size by coincidence (seen: two different
        # 1-page PDFs of exactly 3,061 bytes). Prefer the one named like the title;
        # if none is, the match is ambiguous and is reported as such.
        named = sorted(exact, key=lambda q: -len(terms & set(re.findall(r"[a-z0-9]+", q.stem.lower()))))
        top = named[0]
        if len(exact) == 1 or len(terms & set(re.findall(r"[a-z0-9]+", top.stem.lower()))) >= 2:
            return top, "EXACT"
        return None, "AMBIGUOUS_SIZE"
    best, best_score = None, 0
    for p in by_ext.get(f".{ftype}", []):
        stem_terms = set(re.findall(r"[a-z0-9]+", p.stem.lower()))
        overlap = len(terms & stem_terms)
        if overlap < 2:
            continue
        try:
            sz = p.stat().st_size
        except OSError:
            continue
        if abs(sz - size) / max(size, 1) > 0.10:
            continue
        if ftype == "pdf" and pages and pdf_page_count(p) != pages:
            continue
        score = overlap - abs(sz - size) / max(size, 1)
        if score > best_score:
            best, best_score = p, score
    return (best, "APPROXIMATE") if best else (None, None)


def run(detail, live, fetch=None):
    by_size, by_ext = local_index()
    pages_of = {p["id"]: (p.get("file_info") or {}).get("Length") for p in live}
    rows = []
    for o in detail:
        has_delivery = bool(o.get("files") or o.get("rich_blocks") or o.get("delivery_url"))
        title = o.get("name") or ""
        length = pages_of.get(o["id"])
        n_pages = int(re.sub(r"\D", "", length)) if length and re.search(r"\d", length) else None
        files_out, all_units, extra_all = [], [], {}
        for f in o.get("files") or []:
            data = fetch(f) if fetch else None
            if data is not None:
                local, how = None, "DELIVERED"
            else:
                local, how = find_local(title, f.get("type") or "", f.get("size") or 0, n_pages, by_size, by_ext)
            entry = {"delivered_size": f.get("size"), "type": f.get("type"),
                     "local": str(local.relative_to(ROOT)).replace("\\", "/") if local else None, "match": how}
            if data is None and local:
                data = local.read_bytes()
            if data is not None:
                entry["local_sha256"] = hashlib.sha256(data).hexdigest()[:16]
                u, e = units_of(f"x.{f.get('type') or 'bin'}", data)
                all_units += u
                for k, v in e.items():
                    extra_all[k] = extra_all.get(k, 0) + v if k == "formulas" else v
            files_out.append(entry)
        m = measure(title, all_units, extra_all) if files_out and all(x["match"] in ("DELIVERED", "EXACT", "APPROXIMATE") for x in files_out) else None
        v, reasons = verdict(m, has_delivery)
        rows.append({"listing": title, "url": o.get("url"), "price_usd": (o.get("price") or 0) / 100,
                     "gumroad_pages": length, "files": files_out, "measures": m, "verdict": v, "reasons": reasons,
                     "match_quality": (files_out[0]["match"] if files_out and len({x["match"] for x in files_out}) == 1 else
                                       ("MIXED" if files_out else None))})
    order = {"EMPTY": 0, "FILLER": 1, "OFF_TOPIC": 2, "THIN": 3, "UNVERIFIED": 4, "OK": 5}
    rows.sort(key=lambda r: (order[r["verdict"]], -r["price_usd"]))
    return {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": "Gumroad GET /v2/products and /v2/products/:id (read-only); local files opened with pypdf/openpyxl/python-docx",
            "published_listings": len(rows), "by_verdict": dict(Counter(r["verdict"] for r in rows)),
            "match_quality": dict(Counter(r["match_quality"] for r in rows)),
            "rows": rows}


def make_fetcher(cache_dir):
    """Read each delivered file once (read-only GET of our own product file)
    into a cache OUTSIDE the repository; the byte size must equal Gumroad's
    own record, or the bytes are not used."""
    import requests
    cache_dir = Path(cache_dir); cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch(f):
        url, size = f.get("url"), f.get("size")
        if not url:
            return None
        key = cache_dir / hashlib.sha256(url.encode()).hexdigest()[:24]
        if key.exists() and key.stat().st_size == size:
            return key.read_bytes()
        try:
            r = requests.get(url, timeout=120)
        except Exception:  # noqa: BLE001
            return None
        if r.status_code != 200 or len(r.content) != size:
            return None
        key.write_bytes(r.content)
        time.sleep(0.2)
        return r.content
    return fetch


def main():
    import argparse, tempfile
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-download", action="store_true", help="match local copies only (approximate)")
    ap.add_argument("--cache", default=str(Path(tempfile.gettempdir()) / "gf_delivered_cache"))
    a = ap.parse_args()
    from channels import gumroad_publisher as gp
    tok = gp.load_token()
    live = [p for p in gp.list_products(tok) if p.get("published") and not p.get("deleted")]
    detail = []
    for p in live:
        d = gp.get_product(tok, p["id"]); d = d.get("product", d)
        detail.append({"id": p["id"], "name": d.get("name"), "url": d.get("short_url"), "price": d.get("price"),
                       "files": [{"size": f.get("size"), "type": f.get("filetype") or f.get("type"), "url": f.get("url")} for f in d.get("files") or []],
                       "rich_blocks": len(d.get("rich_content") or []), "delivery_url": d.get("custom_delivery_url")})
        time.sleep(0.3)
    rep = run(detail, live, None if a.no_download else make_fetcher(a.cache))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in rep.items() if k != "rows"}, indent=2, ensure_ascii=False))
    for r in rep["rows"]:
        if r["verdict"] != "OK":
            print(f"{r['verdict']:<10} ${r['price_usd']:>6.2f}  {r['listing'][:55]:<55} {r['match_quality'] or '-':<11} {'; '.join(r['reasons'])[:120]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

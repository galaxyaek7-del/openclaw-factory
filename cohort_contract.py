#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cohort generators behind the manifest contract (backlog B9, risk R8).

The cohort ``build.py`` scripts (GF_BATCH10, GF_BATCH11, GF_PREMIUM_10,
GF_SHOPIFY_PREMIUM_10) write their own manifest shape. The factory-wide contract
(docs/factory/FACTORY_TARGET_ARCHITECTURE.md, the shape of books/batch14/*/manifest.json)
is:

    {id, slug, title, price_cents,
     files: {role: {path, bytes, sha256}},
     qa: {ok, checks: {...}}}

This module converts a cohort product into that shape and runs the adapter QA on the
files as they are on disk. It changes nothing in the cohort's own ``manifest.json``
(other code reads it). The contract goes to ``<cohort>/contracts/<id>.json``, outside
``dist/<id>`` because that folder is zipped into the customer bundle.
No network. Deterministic for identical files.
"""
import hashlib
import json
import re
import zipfile
from pathlib import Path

MIN_GUIDE_WORDS = 5500   # same thresholds as the cohort qa_all()
MIN_GUIDE_PAGES = 10


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _role(name, slug):
    if name == f"{slug}_guide.pdf":
        return "guide"
    if name.endswith(".xlsx"):
        return "workbook"
    if name == "README.txt":
        return "readme"
    if name.endswith(".docx"):
        return "template_" + re.sub(r"[^a-z0-9]+", "_", name[:-5].lower()).strip("_")
    return "other_" + re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _rel(path, root):
    return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()


def to_contract(cohort_manifest, product_dir, bundle_path, root):
    """Build the contract dict from a cohort manifest and the files on disk.

    ``product_dir`` is dist/<id>; ``bundle_path`` is dist/<slug>_bundle.zip; ``root`` is
    the repository root the paths are relative to. QA is filled in by :func:`qa`.
    """
    product_dir, bundle_path = Path(product_dir), Path(bundle_path)
    slug = cohort_manifest["slug"]
    files = {}
    for name in cohort_manifest["files"]:
        if name == "manifest.json":
            continue
        p = product_dir / name
        files[_role(name, slug)] = {"path": _rel(p, root), "bytes": p.stat().st_size,
                                    "sha256": _sha256(p)}
    files["bundle"] = {"path": _rel(bundle_path, root), "bytes": bundle_path.stat().st_size,
                       "sha256": _sha256(bundle_path)}
    contract = {"id": cohort_manifest["id"], "slug": slug, "title": cohort_manifest["name"],
                "price_cents": cohort_manifest["price_cents"],
                "cohort": cohort_manifest.get("cohort"),
                "guide_words": cohort_manifest.get("guide_words"),
                "guide_pages": cohort_manifest.get("guide_pages"),
                "files": dict(sorted(files.items()))}
    contract["qa"] = qa(contract, root)
    return contract


def qa(contract, root):
    """Adapter QA on the files as they are on disk. Returns {ok, checks}."""
    root = Path(root)
    checks, problems = {}, []

    def check(name, ok, detail=""):
        checks[name] = {"status": "PASS" if ok else "FAIL", "detail": detail}
        if not ok:
            problems.append(f"{name}: {detail}")

    files = contract.get("files", {})
    for role in ("guide", "workbook", "bundle"):
        check(f"has_{role}", role in files, "role missing" if role not in files else "")
    check("has_template", any(r.startswith("template_") for r in files), "no docx template")
    check("price_positive", isinstance(contract.get("price_cents"), int) and contract["price_cents"] > 0,
          str(contract.get("price_cents")))
    check("title_present", bool(str(contract.get("title") or "").strip()))

    for role, f in files.items():
        p = root / f["path"]
        if not p.is_file():
            check(f"file_{role}", False, f"missing {f['path']}")
            continue
        size, digest = p.stat().st_size, _sha256(p)
        ok = size > 0 and size == f["bytes"] and digest == f["sha256"]
        check(f"file_{role}", ok, "" if ok else f"size/hash differs from manifest ({f['path']})")

    words, pages = contract.get("guide_words"), contract.get("guide_pages")
    check("guide_not_thin", isinstance(words, int) and words >= MIN_GUIDE_WORDS
          and isinstance(pages, int) and pages >= MIN_GUIDE_PAGES, f"words={words} pages={pages}")

    bundle = files.get("bundle")
    if bundle and (root / bundle["path"]).is_file():
        try:
            with zipfile.ZipFile(root / bundle["path"]) as z:
                names = z.namelist()
                need = {"guide": lambda n: n.endswith("_guide.pdf"),
                        "workbook": lambda n: n.endswith(".xlsx"),
                        "template": lambda n: n.endswith(".docx"),
                        "readme": lambda n: n.endswith("README.txt")}
                missing = [k for k, fn in need.items() if not any(fn(n) for n in names)]
                empty = [n for n in names if not z.read(n)]
                check("bundle_contents", not missing and not empty,
                      f"missing={missing} empty={empty}" if missing or empty else "")
        except zipfile.BadZipFile as e:
            check("bundle_contents", False, f"bad zip: {e}")

    wb = files.get("workbook")
    if wb and (root / wb["path"]).is_file():
        try:
            import openpyxl
            book = openpyxl.load_workbook(root / wb["path"])
            check("workbook_opens", len(book.sheetnames) >= 1, f"{len(book.sheetnames)} sheets")
        except Exception as e:  # noqa: BLE001 - any failure to open is a QA failure
            check("workbook_opens", False, f"{type(e).__name__}: {e}")

    for role in [r for r in files if r.startswith("template_")]:
        p = root / files[role]["path"]
        if p.is_file():
            try:
                import docx
                docx.Document(str(p))
                check(f"{role}_opens", True)
            except Exception as e:  # noqa: BLE001
                check(f"{role}_opens", False, f"{type(e).__name__}: {e}")

    return {"ok": not problems, "checks": checks, "problems": problems}


def write_for_product(cohort_manifest, product_dir, bundle_path, root, out_dir=None):
    """Write the contract to <cohort>/contracts/<id>.json and return it (called by build.py).

    It is written outside dist/<id> on purpose: that folder is zipped into the customer
    bundle, which must stay exactly what it was before this adapter existed.
    """
    contract = to_contract(cohort_manifest, product_dir, bundle_path, root)
    out_dir = Path(out_dir) if out_dir else Path(product_dir).parent.parent / "contracts"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{contract['id']}.json"
    out.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8")
    return contract


def verify_existing(contract_path, root):
    """Re-run QA on a previously written contract (files on disk vs recorded bytes/hashes)."""
    contract = json.loads(Path(contract_path).read_text(encoding="utf-8"))
    return qa(contract, root)

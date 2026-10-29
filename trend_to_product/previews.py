"""Trend-to-Product: previews tied to the actual deliverable (2026-10-29).

A listing preview must show the product a buyer receives. Each preview is
recorded with the sha256 of the deliverable it was rendered from and of the
preview image itself, plus its kind:

  RENDER    rendered from the deliverable file (a page, a sheet, a screenshot);
  MOCKUP    an illustration (device frame, styled scene); allowed only when the
            listing labels it as an illustration, never as the finished content.

verify_preview() re-hashes both files: a preview made from an older version of
the deliverable, or a preview file changed after recording, fails. Nothing here
renders images; renderers already in the factory produce the files, this module
records and checks their provenance.
"""
import hashlib
import os

from . import records

KINDS = ("RENDER", "MOCKUP")


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def record_preview(spec_id, deliverable, preview, kind, generator, root=None, base_dir=None):
    root = root or records.ROOT
    if kind not in KINDS:
        raise records.RecordError(f"kind must be one of {KINDS}")
    if not (generator or "").strip():
        raise records.RecordError("generator (the script or tool that made the preview) is required")
    d, p = os.path.join(root, deliverable), os.path.join(root, preview)
    for path, label in ((d, "deliverable"), (p, "preview")):
        if not os.path.isfile(path):
            raise records.RecordError(f"{label} not found: {path}")
    rec = {"preview_id": records._id("PRV", spec_id, preview, _sha(p)), "spec_id": spec_id,
           "deliverable": deliverable.replace(os.sep, "/"), "deliverable_sha256": _sha(d),
           "preview": preview.replace(os.sep, "/"), "preview_sha256": _sha(p),
           "kind": kind, "generator": generator, "recorded_at": records._now()}
    if rec["preview_id"] not in records._index("previews.jsonl", "preview_id", base_dir):
        records._append("previews.jsonl", rec, base_dir)
    return rec


def verify_preview(rec, root=None):
    root = root or records.ROOT
    problems = []
    d, p = os.path.join(root, rec["deliverable"]), os.path.join(root, rec["preview"])
    if not os.path.isfile(d):
        problems.append("deliverable missing")
    elif _sha(d) != rec["deliverable_sha256"]:
        problems.append("deliverable changed since the preview was made: re-render it")
    if not os.path.isfile(p):
        problems.append("preview file missing")
    elif _sha(p) != rec["preview_sha256"]:
        problems.append("preview file changed after it was recorded")
    return {"preview_id": rec["preview_id"], "kind": rec["kind"],
            "status": "VERIFIED" if not problems else "FAILED", "problems": problems}


def check_listing_previews(preview_recs, mockups_labelled=False, root=None):
    """Problems a listing draft must clear before review. An empty list means none."""
    problems = []
    if not preview_recs:
        problems.append("no preview recorded: render at least one from the deliverable")
    if preview_recs and not any(r["kind"] == "RENDER" for r in preview_recs):
        problems.append("only mockups: at least one preview must be rendered from the deliverable")
    for r in preview_recs or []:
        v = verify_preview(r, root)
        problems += [f"{r['preview']}: {x}" for x in v["problems"]]
        if r["kind"] == "MOCKUP" and not mockups_labelled:
            problems.append(f"{r['preview']}: mockup must be labelled as an illustration in the listing")
    return problems

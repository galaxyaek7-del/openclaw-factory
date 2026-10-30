"""Prepared repair of the accessibility warnings on our own public pages.

services/accessibility_check found 0 errors and 22 warnings on customer_site/
(2026-10-29). This fixes the two mechanical kinds; the heading warnings need a
person, because the right fix depends on each page's outline:

  1. spam-trap fields (name="website", tabindex="-1") without aria-hidden:
     add aria-hidden="true", so screen readers skip them as sighted users do;
  2. fields labelled only by placeholder text: add aria-label with the same
     text, giving each field an accessible name (the visible placeholder
     still disappears on typing; a visible <label> remains the better fix).

Dry run by default; it changes public pages only with --apply, and those
changes go live only when pushed. Each file keeps its bytes and line endings
except for the inserted attributes. --check re-runs the checker on a copy of
the site with the repair applied and prints the before/after counts.

    python scripts/fix_site_accessibility_20261030.py            # list the edits
    python scripts/fix_site_accessibility_20261030.py --check    # before/after on a copy
    python scripts/fix_site_accessibility_20261030.py --apply    # write them
"""
import argparse
import html
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "customer_site"
sys.path.insert(0, str(ROOT / "services" / "accessibility_check"))

TAG = re.compile(rb"<(input|textarea|select)\b[^>]*>", re.I)
# Fields whose placeholder is an example value, named by hand (id -> name).
FIELD_NAMES = {"lookupInput": "Request ID"}


def _attr(tag, name):
    m = re.search(rb"\s" + name + rb"\s*=\s*(\"([^\"]*)\"|'([^']*)')", tag, re.I)
    if not m:
        return None
    return (m.group(2) if m.group(2) is not None else m.group(3)).decode("utf-8", "replace")


def _has(tag, name):
    return re.search(rb"\s" + name + rb"(\s*=|\s|/?>)", tag, re.I) is not None


def _labelled_ids(raw):
    return {m.group(1).decode() for m in re.finditer(rb"<label\b[^>]*\bfor\s*=\s*[\"']([^\"']+)[\"']", raw, re.I)}


def _insert(tag, attr):
    end = tag.rstrip(b">")
    if end.endswith(b"/"):
        return end[:-1].rstrip() + b" " + attr + b" />"
    return end + b" " + attr + b">"


def repair(raw):
    """(new bytes, list of edits). Fields inside a <label> element are left
    alone: they already have a name, and nesting cannot be read reliably with a
    regular expression, so such pages are only touched when the field also has
    no surrounding label in the same line."""
    labelled = _labelled_ids(raw)
    edits = []

    def fix(m):
        tag = m.group(0)
        if _has(tag, b"aria-label") or _has(tag, b"aria-labelledby") or _attr(tag, b"aria-hidden") == "true":
            return tag
        typ = (_attr(tag, b"type") or "text").lower()
        if typ in ("hidden", "submit", "button", "reset", "image"):
            return tag
        fid = _attr(tag, b"id")
        if fid and fid in labelled:
            return tag
        line_start = raw.rfind(b"\n", 0, m.start()) + 1
        line = raw[line_start:m.start()]
        if re.search(rb"<label\b", line, re.I) and not re.search(rb"</label>", line, re.I):
            return tag  # wrapped by a label opened on the same line
        if (_attr(tag, b"tabindex") or "").strip() == "-1" and (_attr(tag, b"name") or "") == "website":
            edits.append(("aria-hidden", _attr(tag, b"name")))
            return _insert(tag, b'aria-hidden="true"')
        ph = _attr(tag, b"placeholder")
        if ph and re.search(r"x{4,}|^\S+_\S+$", ph.strip()):
            # an example value ("req_xxxx"), not a description: use a name chosen by
            # a person for that field, or leave the field for manual review
            ph = FIELD_NAMES.get(fid or "")
            if not ph:
                edits.append(("manual review", fid or _attr(tag, b"name")))
                return tag
        if ph and ph.strip():
            edits.append(("aria-label", ph.strip()))
            return _insert(tag, b'aria-label="' + html.escape(html.unescape(ph.strip()), quote=True).encode("utf-8") + b'"')
        return tag

    return TAG.sub(fix, raw), edits


def run(site, apply):
    total = {}
    for p in sorted(Path(site).rglob("*.html")):
        raw = p.read_bytes()
        new, edits = repair(raw)
        if not edits:
            continue
        total[str(p.relative_to(site)).replace("\\", "/")] = edits
        if apply:
            p.write_bytes(new)
    return total


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--site", default=str(SITE))
    args = ap.parse_args(argv)
    if args.check:
        import check
        before = check.check_path(args.site)
        with tempfile.TemporaryDirectory() as d:
            copy = Path(d) / "site"
            shutil.copytree(args.site, copy)
            run(copy, apply=True)
            after = check.check_path(copy)
        for label, r in (("before", before), ("after", after)):
            print("%s: %d errors, %d warnings" % (label, r["errors"], r["warnings"]))
            for k, v in r["by_issue"].items():
                print("   %3d  %s" % (v["occurrences"], k))
        return 0
    edits = run(args.site, args.apply)
    for page, e in edits.items():
        for kind, value in e:
            print("%s %s: %s=%r" % ("fixed" if args.apply else "would fix", page, kind, value))
    print("%d edit(s) on %d page(s)%s" % (sum(len(e) for e in edits.values()), len(edits),
                                         "" if args.apply else " (dry run; --apply to write)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

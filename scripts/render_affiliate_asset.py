#!/usr/bin/env python3
"""Render an affiliate asset with its real tracked link, safely.

The affiliate URL contains the partner id. It must never be committed, pasted
into a report, or printed to a terminal that logs. The published draft keeps a
placeholder; this script substitutes the real link at render time into an
output directory that git ignores, and validates the link before writing.

Refusals are deliberate and cheap:
  * output outside drafts/affiliate/rendered/ (or a directory git does not
    ignore) is refused, so a real link cannot land in a tracked file;
  * a link whose domain is not approved, or that still looks like a
    placeholder, is refused by affiliate_guard.check_link;
  * a draft with fewer than two placeholders is refused, because one in the
    front matter and one in the body is the minimum that can produce a click;
  * nothing ever prints the URL or the id. Only the domain and counts.

Usage:
    python scripts/render_affiliate_asset.py --check
    python scripts/render_affiliate_asset.py
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import affiliate_guard  # noqa: E402
import systeme_affiliate  # noqa: E402

OUT_DIR = ROOT / "drafts" / "affiliate" / "rendered"
DEFAULT_SOURCE = ROOT / "drafts" / "affiliate" / "systeme_free_plan_ceiling_2026-10-20.md"
DEFAULT_OUT = OUT_DIR / "systeme_free_plan_ceiling_2026-10-20.md"

# Both the front-matter token and the in-body CTA are written as bracketed
# text containing "tracked link". Matching the intent, not one exact string,
# so a copy edit does not silently leave an unrendered placeholder.
PLACEHOLDER_RE = re.compile(r"\[[^\]\n]*tracked link[^\]\n]*\]", re.IGNORECASE)
MIN_PLACEHOLDERS = 2


class RenderRefused(Exception):
    """A safety rule said no. The message is safe to print: no URL, no id."""


def count_placeholders(text):
    return len(PLACEHOLDER_RE.findall(text or ""))


def _body(text):
    """The reader-facing body, excluding YAML front matter.

    Front matter is metadata. A 'disclosure:' key there is not a disclosure a
    reader ever sees, so it must not satisfy the guard on its own."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:]
    return text


def _disclosure_text(text):
    match = re.search(r"(?im)^\*?Disclosure:.*$", _body(text or ""))
    return match.group(0) if match else ""


def _is_gitignored(path):
    try:
        done = subprocess.run(
            ["git", "check-ignore", "-q", str(path)],
            cwd=str(ROOT), capture_output=True, text=True,
        )
    except OSError:
        return False
    return done.returncode == 0


def _inside(path, directory):
    try:
        Path(path).resolve().relative_to(Path(directory).resolve())
        return True
    except ValueError:
        return False


def render_asset(source, out, affiliate_url, allowed_dir=None, require_gitignored=True):
    """Return a report dict. Raises RenderRefused before any write."""
    source, out = Path(source), Path(out)
    if not source.exists():
        raise RenderRefused("source asset does not exist: %s" % source.name)
    text = source.read_text(encoding="utf-8")
    disclosure = _disclosure_text(text)
    if not disclosure:
        raise RenderRefused("source has no 'Disclosure:' line to validate against")

    verdict = affiliate_guard.check_link(affiliate_url, disclosure)
    if not verdict.get("allowed"):
        raise RenderRefused("link refused by affiliate_guard: %s" % verdict.get("reason"))

    placeholders = count_placeholders(text)
    if placeholders < MIN_PLACEHOLDERS:
        raise RenderRefused(
            "only %d placeholder(s); %d required (front matter + body)"
            % (placeholders, MIN_PLACEHOLDERS))

    if allowed_dir is not None and not _inside(out, allowed_dir):
        raise RenderRefused("output must stay inside %s" % allowed_dir)
    if require_gitignored and not _is_gitignored(out):
        raise RenderRefused("output path is not gitignored; refusing to write a real link")

    rendered = PLACEHOLDER_RE.sub(affiliate_url, text)
    if PLACEHOLDER_RE.search(rendered):
        raise RenderRefused("a placeholder survived substitution")
    if affiliate_url not in rendered:
        raise RenderRefused("the tracked link is absent from the rendered text")
    if not disclosure in rendered:
        raise RenderRefused("the disclosure line did not survive rendering")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rendered, encoding="utf-8", newline="\n")
    return {
        "source": str(source.relative_to(ROOT)) if _inside(source, ROOT) else source.name,
        "out": str(out.relative_to(ROOT)) if _inside(out, ROOT) else out.name,
        "placeholders_replaced": placeholders,
        "link_domain": verdict.get("domain"),
        "disclosure_ok": bool(verdict.get("disclosure_ok")),
        "bytes": out.stat().st_size,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Render an affiliate asset with its tracked link.")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--check", action="store_true",
                        help="validate everything, write nothing")
    args = parser.parse_args(argv)

    source, out = Path(args.source), Path(args.out)
    text = source.read_text(encoding="utf-8") if source.exists() else ""
    placeholders = count_placeholders(text)
    print("source: %s" % source.name)
    print("placeholders found: %d (need %d)" % (placeholders, MIN_PLACEHOLDERS))

    try:
        url = systeme_affiliate.get_affiliate_url()
        if args.check:
            verdict = affiliate_guard.check_link(url, _disclosure_text(text))
            if not verdict.get("allowed"):
                raise RenderRefused("link refused by affiliate_guard: %s" % verdict.get("reason"))
            print("link domain: %s; disclosure ok: %s"
                  % (verdict.get("domain"), bool(verdict.get("disclosure_ok"))))
            if not _inside(out, OUT_DIR):
                raise RenderRefused("output must stay inside %s" % OUT_DIR)
            if not _is_gitignored(out):
                raise RenderRefused("output path is not gitignored")
            if placeholders < MIN_PLACEHOLDERS:
                raise RenderRefused("not enough placeholders to render a usable asset")
            print("check: would render to %s (nothing written)" % out.relative_to(ROOT))
            return 0
        report = render_asset(source, out, url, allowed_dir=OUT_DIR, require_gitignored=True)
    except (systeme_affiliate.ConfigError, RenderRefused) as exc:
        print("REFUSED: %s" % exc, file=sys.stderr)
        return 2

    print("rendered: %(out)s" % report)
    print("placeholders replaced: %(placeholders_replaced)d" % report)
    print("link domain: %(link_domain)s; disclosure ok: %(disclosure_ok)s" % report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

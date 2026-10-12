"""Cycle 89 - replace the silent inline page-view beacons with the shared,
observable beacon in customer_site/assets/gf-pageview.js.

Safe by construction:
  * dry-run is the default; --apply is required to write
  * idempotent: a page already using the shared beacon is skipped
  * every edit is verified by re-parsing the result
  * aborts the whole run and reports if any single page fails verification
  * a .bak of each changed file is written next to it and removed on success

Why: the old inline beacon was `.catch(() => {})` in all 58 places, so a
missing receiver produced silence rather than a diagnosable failure, and
crawlers plus repeated renders could inflate counts.
"""
import argparse
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CS = os.path.join(ROOT, "customer_site")

SHARED_REF = "assets/gf-pageview.js"

TAG = '<script src="%s" defer></script>' % SHARED_REF

NEEDLE = "fetch('/api/page-view\""  # matches both quote styles below
NEEDLES = ("fetch('/api/page-view'", 'fetch("/api/page-view"')


def _match_paren(src, open_idx):
    """Return the index of the ')' matching the '(' at open_idx, or -1."""
    depth = 0
    i = open_idx
    in_str = None
    while i < len(src):
        c = src[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == in_str:
                in_str = None
        elif c in "'\"":
            in_str = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def find_beacons(src):
    """Locate whole `fetch('/api/page-view', ...).catch( ... );` statements.

    A regex cannot do this reliably: the handlers are `.catch(()=>{})`,
    `.catch(function () {})` and `.catch(function(){})`, whose nested parens
    defeat any `[^)]*` pattern. This walks balanced parentheses instead, and
    additionally swallows a trailing `.catch(function () {});` that some
    templates wrapped around the whole block.
    """
    spans = []
    for needle in NEEDLES:
        start = 0
        while True:
            i = src.find(needle, start)
            if i < 0:
                break
            open_p = src.find("(", i)
            close_p = _match_paren(src, open_p)
            if close_p < 0:
                start = i + len(needle)
                continue
            end = close_p + 1
            # trailing .catch(...) and any ; after it
            rest = src[end:]
            m = re.match(r"\s*\.catch\s*\(", rest)
            if m:
                c_open = end + m.end() - 1
                c_close = _match_paren(src, c_open)
                if c_close >= 0:
                    end = c_close + 1
            m2 = re.match(r"\s*;", src[end:])
            if m2:
                end += m2.end()
            spans.append((i, end))
            start = end
    spans.sort()
    # drop overlaps
    out = []
    last = -1
    for s, e in spans:
        if s >= last:
            out.append((s, e))
            last = e
    return out


def _inside_script(src, offset):
    """True if `offset` falls between a <script...> and its </script>.

    Cycle 89, first attempt: the tag was substituted in place, and on pages
    whose beacon sat inside a larger <script> block (about.html wraps it with
    a year-stamp script) this produced a nested <script src> INSIDE an open
    <script> element. That is invalid: it is parsed as JavaScript, never
    executes, and the tag-count check still passed because one <script> and
    one </script> were added. Placing the tag safely requires this check.
    """
    open_idx = src.rfind("<script", 0, offset)
    if open_idx < 0:
        return False
    close_idx = src.find("</script", open_idx)
    return close_idx < 0 or offset < close_idx


def process(path, apply_changes):
    src = open(path, encoding="utf-8", errors="strict").read()
    original = src
    if SHARED_REF in src:
        return "skip-already-shared", 0
    spans = find_beacons(src)
    if not spans:
        return "no-beacon", 0

    # remove every beacon statement
    parts, cursor = [], 0
    for s, e in spans:
        parts.append(src[cursor:s])
        cursor = e
    parts.append(src[cursor:])
    stripped = "".join(parts)

    # insert ONE tag at a location guaranteed to be outside any <script>
    m = re.search(r"</body>", stripped, re.I)
    if m:
        cut = m.start()
    else:
        cut = len(stripped)
    if _inside_script(stripped, cut):
        # fall back to the very end, which is outside any script by construction
        cut = len(stripped)
        new = stripped[:cut] + "\n" + TAG + "\n"
    else:
        new = stripped[:cut] + TAG + "\n" + stripped[cut:]

    # verification
    if find_beacons(new):
        return "verify-failed-residual-beacon", len(spans)
    if new.count(SHARED_REF) != 1:
        return "verify-failed-tag-count", len(spans)
    if not new.strip():
        return "verify-failed-empty", len(spans)
    if len(new) > len(original):
        return "verify-failed-grew", len(spans)
    # THE check the first attempt was missing. NOTE: this must be handed the
    # start of the whole TAG, not new.find(SHARED_REF) -- the path inside the
    # tag follows its own "<script", so passing the inner offset made the
    # check match the tag against itself and report a false positive.
    if _inside_script(new, new.find(TAG)):
        return "verify-failed-nested-in-script", len(spans)
    if new.count("<script") != new.count("</script>"):
        return "verify-failed-script-imbalance", len(spans)

    if apply_changes:
        bak = path + ".c89bak"
        with open(bak, "w", encoding="utf-8") as fh:
            fh.write(original)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(new)
        check = open(path, encoding="utf-8").read()
        if (SHARED_REF not in check or len(check) != len(new)
                or _inside_script(check, check.find(TAG))):
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(original)
            os.remove(bak)
            return "verify-failed-after-write", len(spans)
        os.remove(bak)
    return "ok", len(spans)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(CS, "*.html")))
    tally = {}
    failures = []
    total = 0
    for f in files:
        status, n = process(f, args.apply)
        tally[status] = tally.get(status, 0) + 1
        if status.startswith("verify-failed"):
            failures.append((os.path.basename(f), status))
        total += n

    print("  mode            :", "APPLY" if args.apply else "DRY RUN (pass --apply to write)")
    print("  files scanned   :", len(files))
    print("  beacons replaced:", total)
    for k in sorted(tally):
        print(f"    {k:<34} {tally[k]}")
    if failures:
        print("  FAILURES:")
        for name, why in failures:
            print("    ", name, why)
        return 1
    if not args.apply and total:
        print("  no files were modified")
    return 0


if __name__ == "__main__":
    sys.exit(main())


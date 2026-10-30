#!/usr/bin/env python3
"""Accessibility quick-check (productized automation demonstration, 2026-10-29).

A static scan of HTML files for a small set of problems that a machine can
find reliably, each mapped to the WCAG 2.2 success criterion it fails. It is a
triage list for a person to act on, not an audit and never a statement of
compliance: most of WCAG (keyboard use, focus order, meaning of alt text,
colour contrast, captions, screen-reader behaviour) needs a human and is listed
as not checked in every report. In January 2025 the US FTC ordered an
accessibility vendor to pay $1M for claiming its automated tool made sites
WCAG-compliant; this tool makes no such claim.

Checks (WCAG 2.2 success criterion):
  page language missing                     3.1.1 Language of Page
  page title missing or empty               2.4.2 Page Titled
  image without an alt attribute            1.1.1 Non-text Content
  link with no text or accessible name      2.4.4 Link Purpose (In Context) / 4.1.2
  button with no text or accessible name    4.1.2 Name, Role, Value
  form field with no label                  1.3.1 Info and Relationships / 4.1.2
  heading levels skipped (h2 -> h4)         1.3.1 (advisory: warning)
  page has no h1                            1.3.1 / 2.4.6 (advisory: warning)
  zoom disabled in the viewport tag         1.4.4 Resize Text

    python services/accessibility_check/check.py <file-or-folder> [report.json]
"""
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

NOT_CHECKED = [
    "keyboard access and visible focus (2.1.1, 2.4.7)", "colour contrast (1.4.3, 1.4.11)",
    "whether alt text describes the image (1.1.1)", "captions and audio description (1.2.x)",
    "focus order and reading order (2.4.3, 1.3.2)", "error identification in forms (3.3.1)",
    "behaviour with a screen reader", "content added by scripts after load",
]
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class _Scan(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lang = None
        self.title = None
        self.in_title = False
        self.findings = []
        self.headings = []
        self.labels_for = set()
        self.fields = []           # (line, id, has_aria_name, inside_label)
        self.stack = []            # open link/button/label: [tag, line, text, has_name]
        self.viewport = None

    def _attrs(self, attrs):
        return {k.lower(): (v or "") for k, v in attrs}

    def handle_starttag(self, tag, attrs):
        a = self._attrs(attrs)
        line = self.getpos()[0]
        named = bool(a.get("aria-label", "").strip() or a.get("aria-labelledby", "").strip() or a.get("title", "").strip())
        if tag == "html":
            self.lang = a.get("lang", "").strip()
        elif tag == "title":
            self.in_title, self.title = True, ""
        elif tag == "meta" and a.get("name", "").lower() == "viewport":
            self.viewport = (line, a.get("content", ""))
        elif tag == "img":
            if "alt" not in a and a.get("role", "") not in ("presentation", "none") and a.get("aria-hidden") != "true":
                self.findings.append((line, "image without an alt attribute", "1.1.1", "error", a.get("src", "")[:80]))
            for s in self.stack:
                if a.get("alt", "").strip():
                    s[3] = True
        elif re.fullmatch(r"h[1-6]", tag):
            self.headings.append((line, int(tag[1])))
        elif tag in ("a", "button", "label"):
            if tag == "a" and "href" not in a:
                return
            self.stack.append([tag, line, "", named, a.get("for", "")])
            if tag == "label" and a.get("for"):
                self.labels_for.add(a["for"])
        elif tag in ("input", "select", "textarea"):
            typ = a.get("type", "text").lower()
            if typ in ("hidden", "submit", "button", "reset", "image"):
                if typ in ("submit", "button", "reset") and not (a.get("value", "").strip() or named):
                    self.findings.append((line, "button with no text or accessible name", "4.1.2", "error", typ))
                return
            if a.get("aria-hidden") == "true":
                return
            inside = any(s[0] == "label" for s in self.stack)
            kind = tag + ("[%s]" % typ if tag == "input" else "")
            self.fields.append((line, a.get("id", ""), named, inside, kind,
                                a.get("tabindex", "").strip() == "-1", bool(a.get("placeholder", "").strip())))
        if tag in VOID:
            return

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                t, line, text, named, _ = self.stack.pop(i)
                if t != "label" and not text.strip() and not named:
                    what = "link" if t == "a" else "button"
                    sc = "2.4.4" if t == "a" else "4.1.2"
                    self.findings.append((line, "%s with no text or accessible name" % what, sc, "error", ""))
                for s in self.stack:
                    s[2] += text
                break

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.stack:
            self.stack[-1][2] += data


def check_html(text):
    s = _Scan()
    s.feed(text)
    s.close()
    out = [{"line": l, "issue": i, "wcag": sc, "severity": sev, "detail": d} for l, i, sc, sev, d in s.findings]
    if not s.lang:
        out.append({"line": 1, "issue": "page language missing (no lang on <html>)", "wcag": "3.1.1", "severity": "error", "detail": ""})
    if s.title is None or not s.title.strip():
        out.append({"line": 1, "issue": "page title missing or empty", "wcag": "2.4.2", "severity": "error", "detail": ""})
    for line, fid, named, inside, kind, untabbable, placeholder in s.fields:
        if named or inside or (fid and fid in s.labels_for):
            continue
        if untabbable:
            out.append({"line": line, "issue": "unlabelled field kept out of the tab order (a spam trap?) is still "
                        "announced by screen readers; add aria-hidden=\"true\"", "wcag": "1.3.1",
                        "severity": "warning", "detail": kind})
        elif placeholder:
            out.append({"line": line, "issue": "form field labelled only by placeholder text", "wcag": "1.3.1",
                        "severity": "warning", "detail": kind})
        else:
            out.append({"line": line, "issue": "form field with no label", "wcag": "1.3.1", "severity": "error", "detail": kind})
    levels = [lv for _, lv in s.headings]
    if levels and 1 not in levels:
        out.append({"line": s.headings[0][0], "issue": "page has no h1", "wcag": "1.3.1", "severity": "warning", "detail": ""})
    prev = None
    for line, lv in s.headings:
        if prev is not None and lv > prev + 1:
            out.append({"line": line, "issue": "heading level skipped (h%d after h%d)" % (lv, prev), "wcag": "1.3.1",
                        "severity": "warning", "detail": ""})
        prev = lv
    if s.viewport:
        c = s.viewport[1].replace(" ", "").lower()
        m = re.search(r"maximum-scale=([\d.]+)", c)
        if "user-scalable=no" in c or "user-scalable=0" in c or (m and float(m.group(1)) < 2):
            out.append({"line": s.viewport[0], "issue": "zoom disabled or limited in the viewport tag", "wcag": "1.4.4",
                        "severity": "error", "detail": s.viewport[1][:80]})
    return sorted(out, key=lambda f: (f["line"], f["issue"]))


def check_path(path):
    path = Path(path)
    files = sorted(path.rglob("*.html")) if path.is_dir() else [path]
    pages = []
    for f in files:
        findings = check_html(f.read_text(encoding="utf-8", errors="replace"))
        pages.append({"page": str(f.relative_to(path)).replace("\\", "/") if path.is_dir() else f.name,
                      "errors": sum(1 for x in findings if x["severity"] == "error"),
                      "warnings": sum(1 for x in findings if x["severity"] == "warning"),
                      "findings": findings})
    by_issue = {}
    for p in pages:
        for x in p["findings"]:
            k = "%s (WCAG %s)" % (x["issue"].split(" (")[0], x["wcag"])
            by_issue.setdefault(k, {"pages": 0, "occurrences": 0, "_seen": set()})
            by_issue[k]["occurrences"] += 1
            if p["page"] not in by_issue[k]["_seen"]:
                by_issue[k]["_seen"].add(p["page"])
                by_issue[k]["pages"] += 1
    for v in by_issue.values():
        v.pop("_seen")
    return {
        "pages_checked": len(pages),
        "pages_with_errors": sum(1 for p in pages if p["errors"]),
        "errors": sum(p["errors"] for p in pages), "warnings": sum(p["warnings"] for p in pages),
        "by_issue": dict(sorted(by_issue.items(), key=lambda kv: -kv[1]["occurrences"])),
        "pages": pages,
        "not_checked": NOT_CHECKED,
        "statement": "Automated triage of a few machine-checkable criteria. Not an audit, not a certification, "
                     "and not evidence of WCAG, ADA or European Accessibility Act compliance.",
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__)
        return 2
    report = check_path(argv[0])
    if len(argv) > 1:
        Path(argv[1]).write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in report if k not in ("pages",)}, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

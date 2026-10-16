"""BKL-001 helper: install the Google Search Console HTML verification file
(Phase 5, 2026-10-16).

The founder creates the property in Search Console (their own Google login;
this factory never logs in): URL-prefix property
    https://galaxyaek7-del.github.io/openclaw-factory/
and chooses "HTML file" verification. Google names the file, e.g.
google0123456789abcdef.html. Run:

    python scripts/search_console_verify.py --file google0123456789abcdef.html          # dry run
    python scripts/search_console_verify.py --file google0123456789abcdef.html --apply  # writes it

The file goes at the repository root, which GitHub Pages serves as
/openclaw-factory/. It only becomes visible to Google after the founder
approves a commit and push. Then submit sitemap.xml in Search Console.
"""
import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = re.compile(r"^google[0-9a-f]{16}\.html$")
PROPERTY_URL = "https://galaxyaek7-del.github.io/openclaw-factory/"


def _read(path, newline=None):
    with open(path, encoding="utf-8", newline=newline) as fh:
        return fh.read()


def plan(file_name, root=ROOT):
    if not NAME.match(file_name or ""):
        return {"ok": False, "error": "expected a Google file name like google0123456789abcdef.html"}
    target = os.path.join(root, file_name)
    content = f"google-site-verification: {file_name}"
    if os.path.exists(target):
        existing = _read(target).strip()
        if existing != content:
            return {"ok": False, "error": f"{file_name} exists with different content; not overwriting"}
        return {"ok": True, "action": "already_present", "target": target, "content": content}
    return {"ok": True, "action": "create", "target": target, "content": content,
            "public_url_after_push": PROPERTY_URL + file_name}


def apply(file_name, root=ROOT):
    p = plan(file_name, root)
    if p["ok"] and p["action"] == "create":
        with open(p["target"], "w", encoding="utf-8", newline="\n") as fh:
            fh.write(p["content"] + "\n")
        p["action"] = "created"
    return p


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--file", required=True)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    r = apply(a.file) if a.apply else plan(a.file)
    print(r if a.apply else dict(r, dry_run=True))
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

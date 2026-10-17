"""Master Sprint Plan E (2026-10-17): grounded tag suggestions for every
published Gumroad listing.

Rule: a tag is suggested only if it appears, as written, in that listing's
own title or description. Each tag carries its source ("title" or
"description x N"), so nothing is guessed and every suggestion can be
checked against the live page. Tags the listing already has are kept first.

Read-only. One GET (list_products). Writes data/seo/product_tags.json.
Applying tags is a live listing edit: founder approval per change.

    python scripts/generate_seo_tags.py               # live read
    python scripts/generate_seo_tags.py --from-file products.json
"""
import argparse
import html
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "seo" / "product_tags.json"
# Gumroad's own source (antiwork/gumroad app/models/tag.rb, read 2026-10-17):
# a tag is 2-20 characters, cannot start with "#" or contain a comma. No
# per-product count limit was found in tag.rb or product_tagging.rb, so the
# count limit stays UNVERIFIED; 10 is the founder's 7-10 target, not a cap.
TARGET, MAX_TAGS, MIN_LEN, MAX_LEN = 7, 10, 2, 20
OPTIMIZED = ROOT / "data" / "seo" / "optimized_tags.json"

STOP = set("""a an the and or for of to in on with your you our we us it its this that these those is are be
be by from as at into how what why when who which all any each every more most no not one two three per
vs via up out off over new get got do does did can will just than then so if but also only own
kit pack bundle system toolkit guide playbook checklist edition v1 v2 steps pages page both first
unavailable reviewed before after demo client one agent
action real minute 5-minute ready complete simple practical starter mini-guide quickstart""".split())


# Too generic to stand alone as a tag, but fine inside a phrase ("cost control").
WEAK_ALONE = {"control", "review", "management", "template", "templates", "tracker", "plan",
              "file", "files", "letter", "process", "tool", "tools", "pay", "rules", "deadline",
              "small", "sellers", "seller", "policy", "business", "materials"}


def text_of(desc):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", desc or ""))).strip()


def _words(s):
    return re.findall(r"[a-z0-9][a-z0-9'&+-]*[a-z0-9]|[a-z0-9]", s.lower())


_BREAK = re.compile(r"[.,;:!?()\[\]|/\u2013\u2014\u2022\n]+|\s-\s")


def phrases(text):
    """Phrases inside punctuation-free segments only, so a bigram is always
    two words that are really adjacent in the text."""
    out = []
    for seg in _BREAK.split(text or ""):
        out += _phrases(_words(seg))
    return out


def _phrases(words):
    """Unigrams and bigrams with no stopword at either end."""
    out = []
    for i, w in enumerate(words):
        if w not in STOP and len(w) > 2 and not w.isdigit():
            out.append(w)
        if i + 1 < len(words):
            a, b = w, words[i + 1]
            if a not in STOP and b not in STOP and len(a) > 1 and len(b) > 1 and not (a.isdigit() or b.isdigit()):
                out.append(f"{a} {b}")
    return out


def suggest(listing):
    title = listing.get("name") or ""
    desc = text_of(listing.get("description"))
    existing = [t.strip().lower() for t in (listing.get("tags") or []) if t and t.strip()]
    desc_counts = Counter(phrases(desc))

    cands = {}
    for ph in dict.fromkeys(phrases(title)):
        n = desc_counts.get(ph, 0)
        cands[ph] = (2 + (1 if " " in ph else 0) + min(n, 5), "title" + (f" + description x{n}" if n else ""))
    title_words = set(_words(title)) - STOP
    for ph, n in desc_counts.items():
        # A description-only phrase must share a word with the title, and
        # disclaimer language ("not legal advice") is never a tag.
        if "advice" in ph or not (set(ph.split()) & title_words):
            continue
        if n >= 3 and " " in ph and ph not in cands:
            cands[ph] = (n / 3, f"description x{n}")

    # Prefer a bigram over the single words it already contains.
    ranked = sorted(cands.items(), key=lambda kv: (-kv[1][0], kv[0]))
    picked = []
    have_words = {w for t in existing for w in t.split()}
    multi = [set(t.split()) for t in existing if " " in t]
    for ph, (score, src) in ranked:
        words = set(ph.split())
        if not MIN_LEN <= len(ph) <= MAX_LEN or "," in ph or ph.startswith("#") or ph in existing or ph in WEAK_ALONE:
            continue
        if words <= have_words:                      # already said by an existing tag
            continue
        if " " in ph and any(words & m and not m <= words for m in multi):
            continue                                 # straddles an existing phrase ("estate transaction")
        if any(ph in p["tag"].split() or ph == p["tag"] or words <= set(p["tag"].split()) for p in picked):
            continue
        have_words |= words if " " not in ph else set()
        picked.append({"tag": ph, "source": src})
        if len(existing) + len(picked) >= MAX_TAGS:
            break
    return {
        "product_id": listing.get("id"), "title": title, "url": listing.get("short_url"),
        "existing_tags": existing, "suggested": picked,
        "reaches_target": len(existing) + len(picked) >= TARGET,
    }


def run(listings):
    rows = [suggest(l) for l in listings if l.get("published") and not l.get("deleted")
            and "[unavailable]" not in (l.get("name") or "").lower()]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rule": ("every suggested tag appears in the listing's own title or description; a description-only phrase must "
                 "share a word with the title; disclaimer phrases are excluded; source recorded"),
        "listings": len(rows),
        "already_at_target": sum(len(r["existing_tags"]) >= TARGET for r in rows),
        "reach_target_with_suggestions": sum(r["reaches_target"] for r in rows),
        "short_of_target": [r["title"] for r in rows if not r["reaches_target"]],
        "apply": "Live listing edit. Founder approval per change; nothing was written to Gumroad.",
        "gumroad_tag_rules": {"length": "2-20 characters, no leading '#', no comma (Gumroad source, app/models/tag.rb)",
                              "count_per_product": "UNVERIFIED (no limit found in tag.rb or product_tagging.rb)"},
        "target_tags_per_listing": TARGET,
        "rows": rows,
    }


def optimized(rep):
    """The directive's per-product view: current tags plus grounded additions."""
    return {
        "generated_at": rep["generated_at"], "rule": rep["rule"], "gumroad_tag_rules": rep["gumroad_tag_rules"],
        "apply": rep["apply"],
        "products": {r["product_id"]: {
            "title": r["title"], "url": r["url"], "current_tags": r["existing_tags"],
            "optimized_tags": r["existing_tags"] + [t["tag"] for t in r["suggested"]],
            "added": r["suggested"],
            "tag_count": len(r["existing_tags"]) + len(r["suggested"]),
        } for r in rep["rows"]},
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-file")
    a = ap.parse_args(argv)
    if a.from_file:
        listings = json.loads(Path(a.from_file).read_text(encoding="utf-8"))
    else:
        sys.path.insert(0, str(ROOT))
        from channels import gumroad_publisher as gp
        listings = gp.list_products(gp.load_token())
    rep = run(listings)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    OPTIMIZED.write_text(json.dumps(optimized(rep), indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in rep.items() if k != "rows"}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

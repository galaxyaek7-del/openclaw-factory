#!/usr/bin/env python3
"""Gumroad discoverability repairs found on 2026-10-31.

Gumroad Discover finds products by category and tags. A read of the live
catalog found 7 published listings with no tags at all (B16-001..007, created
before create_product forwarded tags, bb310bb) and 67 of 112 filed under the
"Other" category, which buyers do not browse.

  tags      only for a listing with none, copied from its own manifest
  category  only for a listing in "Other", and only to a category this account
            already uses on a live listing (taxonomy ids observed, never typed),
            chosen by plain keyword rules on the title and tags; a listing no
            rule fits keeps "Other" and the report says so
  never     held listings (hold_policy.py) or listings with a broken delivery
            promise (newest delivery audit): those must not be promoted

Default is a dry run (GET only); the plan goes to
data/discoverability_20261031.json. --live writes through
gumroad_publisher.update_product, which re-reads every listing to prove the
fields persisted, under the write gate; it is a founder decision.

    python scripts/apply_discoverability_20261031.py
    python scripts/apply_discoverability_20261031.py --live
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
REPORT = ROOT / "data" / "discoverability_20261031.json"

# (category label used on this account, keywords); first match wins, most specific first.
RULES = [
    # Personal finance first: this account uses no personal-finance category, and a
    # household budget filed under business Accounting would mislead; it stays in Other.
    (None, r"\b(wedding|roommate|sinking fund|emergency fund|zero-based|debt payoff|household|personal finance)\b"),
    # Gumroad's "Security & Compliance" sits under software development/cybersecurity:
    # only data-protection and security topics belong there.
    ("Security & Compliance", r"\b(gdpr|dsar|pci|cyber|security|privacy|data protection|ai act|ai literacy)\b"),
    ("Real Estate", r"\b(rent|rental|landlord|tenant|mortgage|home buy|homebuyer|property|real estate|deposit|renovation|refinance|section 8|eviction)\b"),
    ("Accounting", r"\b(tax|invoice|bookkeeping|cash flow|cashflow|accounting|vat|reconciliation|profit|budget|break-even|breakeven|payment)\b"),
    ("Networking, Careers & Jobs", r"\b(cv|resume|job|career|interview|ats)\b"),
    ("Management & Leadership", r"\b(pto|leave|employee|staff|shift|labor|hiring|team|hr|meeting)\b"),
    ("Email", r"\b(email|newsletter)\b"),
    ("Social Media", r"\b(social media|instagram|tiktok|pinterest|linkedin)\b"),
    ("Resources", r"\b(freelance|freelancer|startup|founder|saas|pricing|small business|seller|etsy|shopify|client|consult|agency|membership|subscription|event|safe|"
                  r"compliance|regulation|cottage food|eudr|green claims|toy safety|cosmetics|weee|handbook|"
                  r"inventory|restaurant|salon|clinic|dental|returns|food truck|fleet)\b"),
]


def observed_taxonomies(live):
    """label -> taxonomy_id, from categories this account already uses."""
    out = {}
    for p in live:
        if p.get("taxonomy_id") and p.get("category_label") and p.get("category") != "other":
            out.setdefault(p["category_label"], p["taxonomy_id"])
    return out


def choose_category(name, tags, taxonomies):
    text = " ".join([name or ""] + list(tags or [])).lower()
    for label, pattern in RULES:
        if re.search(pattern, text):
            if label is None:
                return None, None  # deliberately left in Other
            if label in taxonomies:
                return label, taxonomies[label]
    return None, None


def excluded_slugs(root=ROOT):
    out = {}
    try:
        for slug in json.loads((Path(root) / "data" / "hold_products.json").read_text(encoding="utf-8"))["products"]:
            out[slug] = "on hold"
    except (OSError, ValueError, KeyError):
        pass
    try:
        from social_distribution import offers
        for slug, d in offers.delivery_issues(root).items():
            out.setdefault(slug, "delivery audit: " + ", ".join(d["issues"]))
    except Exception:  # noqa: BLE001  the hold list alone still excludes the held listings
        pass
    return out


def manifest_tags(registry, root=ROOT):
    out = {}
    for p in registry.get("products", []):
        gid, man = (p.get("external_ids") or {}).get("gumroad"), p.get("manifest")
        if gid and man and (Path(root) / man).is_file():
            tags = json.loads((Path(root) / man).read_text(encoding="utf-8")).get("tags") or []
            tags = [t.strip() for t in tags if isinstance(t, str) and t.strip()]
            if tags:
                out[gid] = tags
    return out


def plan(live, registry, root=ROOT):
    taxonomies = observed_taxonomies(live)
    excluded = excluded_slugs(root)
    tags_by_id = manifest_tags(registry, root)
    actions = []
    for p in live:
        if not p.get("published"):
            continue
        slug = (p.get("short_url") or "").rstrip("/").rsplit("/", 1)[-1]
        updates, notes = {}, []
        if slug in excluded:
            if not p.get("tags") or p.get("category") == "other":
                actions.append({"slug": slug, "product_id": p["id"], "name": p.get("name"), "skipped": excluded[slug]})
            continue
        if not p.get("tags"):
            if p["id"] in tags_by_id:
                updates["tags"] = tags_by_id[p["id"]]
            else:
                notes.append("no tags and no manifest tags to copy")
        if p.get("category") == "other":
            label, tid = choose_category(p.get("name"), updates.get("tags") or p.get("tags"), taxonomies)
            if tid:
                updates["taxonomy_id"] = tid
                notes.append(f"category Other -> {label}")
            else:
                notes.append("stays in Other: no observed category fits by the rules")
        if updates or notes:
            actions.append({"slug": slug, "product_id": p["id"], "name": p.get("name"), "updates": updates, "notes": notes})
    return {"taxonomies_observed": taxonomies, "actions": actions}


def apply(token, gp, actions):
    done = []
    for a in actions:
        if not a.get("updates"):
            done.append({**a, "result": "NOTHING_TO_WRITE" if not a.get("skipped") else "SKIPPED"})
            continue
        try:
            gp.update_product(token, a["product_id"], a["updates"])
            done.append({**a, "result": "PASS"})
        except Exception as e:  # each listing stands alone
            done.append({**a, "result": "FAILED", "reason": f"{type(e).__name__}: {str(e)[:300]}"})
    return done


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args(argv)
    from channels import gumroad_publisher as gp
    token = gp.load_token()
    live = gp.list_products(token)
    registry = json.loads((ROOT / "data" / "product_registry.json").read_text(encoding="utf-8"))
    doc = plan(live, registry)
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "mode": "LIVE" if args.live else "DRY_RUN",
              "taxonomies_observed": doc["taxonomies_observed"]}
    if args.live:
        import gumroad_auth_watch as auth
        from channels import publication_authorization as pa
        pa.assert_session_fresh(auth.poll(), max_age_seconds=3600)
        os.environ["FACTORY_LIVE_PUBLISH"] = "true"
        try:
            report["actions"] = apply(token, gp, doc["actions"])
        finally:
            os.environ["FACTORY_LIVE_PUBLISH"] = "false"
    else:
        report["actions"] = [{**a, "result": "SKIPPED" if a.get("skipped") else ("PLANNED" if a.get("updates") else "NOTHING_TO_WRITE")}
                             for a in doc["actions"]]
    REPORT.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    summary = {}
    for a in report["actions"]:
        summary[a["result"]] = summary.get(a["result"], 0) + 1
    print(json.dumps({"mode": report["mode"], "summary": summary, "report": str(REPORT.relative_to(ROOT))}))
    return 0 if all(a["result"] != "FAILED" for a in report["actions"]) else 1


if __name__ == "__main__":
    sys.exit(main())

"""One offline distribution cycle: offers -> plan -> drafts -> QA -> job ledger -> dashboard.

    python scripts/distribution_cycle.py [--n 6] [--per-arm 2] [--offline-catalog <gumroad.json>]

Reads Gumroad with a GET only (or a saved catalog). Writes:
  data/distribution_offers.json, data/social_campaign_jobs.jsonl (drafts only),
  data/distribution_dashboard.json, docs/distribution/DISTRIBUTION_DASHBOARD.md
It never approves, queues or publishes anything; those steps need a person.
Safe to re-run: the same drafts map to the same job ids.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from social_distribution import campaigns, content, dashboard, offers, platforms, prioritize, tracking  # noqa: E402


def run(n=6, per_arm=2, live=None, root=ROOT, ledger=None, write_outputs=True, include=()):
    doc = offers.build(live=live, root=root)
    jobs = campaigns.Jobs(ledger=ledger or campaigns.LEDGER)
    recent = prioritize.recent_offers(jobs.jobs())
    by_id = {o["offer_id"]: o for o in doc["offers"]}
    drafts = {}

    def usable(offer_id):  # an offer is worth a campaign only if some draft passes QA
        o = by_id[offer_id]
        camp = tracking.campaign_id(offer_id)
        drafts[offer_id] = [content.draft(o, p, campaign=camp, offers=doc["offers"]) for p in o["platforms"]]
        return any(d["qa"]["passed"] for d in drafts[offer_id])

    picked = prioritize.plan(doc["offers"], n=n, per_arm=per_arm, recent_offer_ids=recent, accept=usable)
    for oid in include or ():  # named offers join the plan with their real score, whatever it is
        if oid in by_id and oid not in {p["offer_id"] for p in picked}:
            usable(oid)
            picked.append(dict(prioritize.score(by_id[oid], recent_offer_ids=recent), included_by_name=True))
    created = []
    for s in picked:
        for d in drafts[s["offer_id"]]:
            created.append({"job": jobs.add_draft(d), "offer": d["offer_id"], "platform": d["platform"], "qa": d["qa"]["passed"]})
    dash = dashboard.build(doc, jobs.jobs(), platforms.readiness(), dashboard.real_metrics())
    if write_outputs:
        offers.write(doc)
        dashboard.write(dash)
    return {"offers": doc["summary"], "plan": picked, "drafts": created, "jobs": jobs.summary()}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--per-arm", type=int, default=2)
    ap.add_argument("--offline-catalog")
    ap.add_argument("--include", nargs="*", default=[], help="offer ids to draft in addition to the plan")
    a = ap.parse_args()
    live = json.loads(Path(a.offline_catalog).read_text(encoding="utf-8")) if a.offline_catalog else None
    r = run(a.n, a.per_arm, live=live, include=a.include)
    print(json.dumps({"offers": r["offers"], "planned": [(p["offer_id"], p["score"]) for p in r["plan"]],
                      "drafts": len(r["drafts"]), "drafts_qa_passed": sum(x["qa"] for x in r["drafts"]), "jobs": r["jobs"]},
                     indent=1))

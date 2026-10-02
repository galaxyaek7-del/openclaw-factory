"""Freelancer LOCAL simulation / dry-run (S3-DRYRUN-01).

Reads ONLY local pipeline data (data/global_pipeline.json). Makes ZERO
network calls (no socket/urllib/requests imports anywhere in this file —
verifiable by inspection). Analyzes fit from stored fields, generates a
draft proposal per active opportunity, appends to
data/dryrun_proposals.jsonl with explicit SIMULATION states.

States used: DISCOVERED -> ANALYZED -> PROPOSAL_DRAFT_READY /
SIMULATION_READY / BLOCKED_EXTERNAL_SUBMISSION. NEVER SUBMITTED/SENT/LIVE.
BLOCKED_NO_TOKEN here means exactly: real external submission unavailable
for lack of credential. Nothing leaves this machine.
"""
import datetime
import hashlib
import json

PIPELINE_PATH = "data/global_pipeline.json"
DRAFTS_PATH = "data/dryrun_proposals.jsonl"


def analyze(stored):
    """Fit analysis from stored fields only. Returns (fit, reasons)."""
    reasons = []
    score = 0
    budget = stored.get("budget") or [None, None]
    bmin, bmax = budget[0], budget[1]
    if bmax is not None and bmax >= 30 and (bmin or 0) <= 250:
        score += 1
        reasons.append("budget-overlaps-policy")
    else:
        reasons.append("budget-outside-policy")
    if stored.get("price") is not None:
        score += 1
        reasons.append("price-selected")
    if stored.get("proposal_personalized"):
        score += 1
        reasons.append("proposal-personalized")
    bids = stored.get("bids")
    if isinstance(bids, (int, float)) and bids < 100:
        score += 1
        reasons.append("competition-moderate")
    elif isinstance(bids, (int, float)):
        reasons.append("competition-high")
    fit = "FIT" if score >= 3 else "MARGINAL" if score == 2 else "WEAK"
    return fit, reasons


def draft_proposal(stored):
    base = stored.get("proposal_personalized") or {}
    if isinstance(base, dict):
        body = "; ".join(
            "%s: %s" % (k, v) for k, v in base.items() if isinstance(v, (str, int, float))
        )
    else:
        body = str(base)
    text = (
        "DRAFT (SIMULATION ONLY - NEVER SENT). Opportunity %(id)s: %(title)s. "
        "Budget %(budget)s. Factory price %(price)s. %(body)s"
        % {"id": stored.get("id"), "title": stored.get("title"),
           "budget": stored.get("budget"), "price": stored.get("price"),
           "body": body[:800]}
    )
    return text


def main():
    pipe = json.load(open(PIPELINE_PATH, encoding="utf-8"))
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        seen = {json.loads(l).get("internal_id")
                for l in open(DRAFTS_PATH, encoding="utf-8") if l.strip()}
    except OSError:
        seen = set()
    analyzed = 0
    ready = 0
    for stored in pipe.get("active", []):
        internal_id = "dry-%s" % stored.get("id")
        if internal_id in seen:
            continue
        analyzed += 1
        fit, reasons = analyze(stored)
        rec = {
            "internal_id": internal_id,
            "opportunity_id": stored.get("id"),
            "created_at": now,
            "mode": "DRY_RUN",
            "external_submission": False,
            "states": ["DISCOVERED", "ANALYZED", "PROPOSAL_DRAFT_READY",
                       "SIMULATION_READY", "BLOCKED_EXTERNAL_SUBMISSION"],
            "fit": fit,
            "fit_reasons": reasons,
            "draft_proposal": draft_proposal(stored),
            "draft_sha": hashlib.sha256(
                draft_proposal(stored).encode()).hexdigest()[:16],
        }
        with open(DRAFTS_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        ready += 1
    print(json.dumps({"analyzed_new": analyzed, "drafts_ready": ready,
                      "external_posts": 0}))
    return 0


if __name__ == "__main__":
    main()

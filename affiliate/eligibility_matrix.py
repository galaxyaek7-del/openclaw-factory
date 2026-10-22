#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — Affiliate eligibility and payout matrix (Algeria).

Answers, per program in data/commission_opportunities.jsonl, two separate
questions that must never collapse into one "VERIFIED" label:

  eligibility_state — may a publisher residing in Algeria join?
  payout_state      — is there a confirmed way to receive the money there?

Inputs are the authoritative registry and data/affiliate_algeria_evidence.json
(sourced facts with check dates). A program with no evidence entry is
ELIGIBILITY_UNKNOWN / PAYOUT_UNVERIFIED. "Global" in a registry text field is
not evidence of Algeria eligibility. Read-only. No network. No secrets.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from . import registry

FACTORY_DIR = Path(__file__).resolve().parent.parent
EVIDENCE = FACTORY_DIR / "data" / "affiliate_algeria_evidence.json"

ELIGIBILITY_STATES = ("DISCOVERED", "ELIGIBILITY_UNKNOWN", "ELIGIBLE_EVIDENCE_FOUND",
                      "INELIGIBLE", "APPLICATION_PREPARED", "APPLICATION_SUBMITTED",
                      "PENDING_APPROVAL", "APPROVED", "REJECTED", "SUSPENDED", "CLOSED")
PAYOUT_STATES = ("PAYOUT_UNVERIFIED", "PAYOUT_ROUTE_CONDITIONAL", "PAYOUT_ROUTE_BLOCKED",
                 "PAYOUT_VERIFIED")

# Rail verdicts that mean "money can plausibly arrive, with friction".
_USABLE_RAIL = {"CONDITIONAL", "LISTED"}
_BLOCKED_RAIL = {"UNAVAILABLE", "NOT_LISTED"}


def load_evidence(path=None):
    p = Path(path) if path else EVIDENCE
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"rails": {}, "programs": {}}
    return {"rails": data.get("rails", {}), "programs": data.get("programs", {})}


def eligibility_state(opp, ev):
    status = str(opp.get("verification_status", "")).upper()
    if "DISCONTINU" in status or "CLOSED" in status:
        return "CLOSED"
    if "REJECT" in status:
        return "REJECTED"
    if not ev:
        return "ELIGIBILITY_UNKNOWN"
    verdict = ev.get("publisher_eligibility_algeria")
    if verdict == "INELIGIBLE":
        return "INELIGIBLE"
    if verdict == "NO_COUNTRY_RESTRICTION_STATED" and ev.get("eligibility_basis") in ("VERIFIED", "OBSERVED"):
        return "ELIGIBLE_EVIDENCE_FOUND"
    return "ELIGIBILITY_UNKNOWN"


def payout_state(ev, rails):
    """PAYOUT_VERIFIED needs an explicit verified flag (a real received
    payout or official country confirmation). Otherwise the best documented
    route decides between CONDITIONAL, BLOCKED and UNVERIFIED."""
    if not ev:
        return "PAYOUT_UNVERIFIED", []
    if ev.get("payout_verified") is True:
        return "PAYOUT_VERIFIED", []
    verdicts = []
    for name in ev.get("payout_routes", []):
        rail = rails.get(name, {})
        verdicts.append({"rail": name, "algeria_receive": rail.get("algeria_receive", "UNKNOWN"),
                         "basis": rail.get("basis", "UNKNOWN")})
    values = {v["algeria_receive"] for v in verdicts}
    if values & _USABLE_RAIL:
        return "PAYOUT_ROUTE_CONDITIONAL", verdicts
    if verdicts and values <= _BLOCKED_RAIL:
        return "PAYOUT_ROUTE_BLOCKED", verdicts
    return "PAYOUT_UNVERIFIED", verdicts


def _next_action(elig, pay):
    if elig in ("CLOSED", "REJECTED", "INELIGIBLE"):
        return "drop: record reason, move to next candidate"
    if pay == "PAYOUT_ROUTE_BLOCKED":
        return "hold: no documented payout route usable from Algeria"
    if elig == "ELIGIBILITY_UNKNOWN":
        return "verify publisher country eligibility from the official terms"
    if pay == "PAYOUT_UNVERIFIED":
        return "verify payout rail for Algeria from official payout documentation"
    if pay == "PAYOUT_ROUTE_CONDITIONAL":
        return "founder: confirm the payout account (e.g. PayPal withdrawal path) works before promoting"
    return "eligible with verified payout: prepare first asset"


def matrix(opportunities=None, evidence=None):
    opps = opportunities if opportunities is not None else registry.load_opportunities()
    ev_all = evidence if evidence is not None else load_evidence()
    rows = []
    for opp in opps:
        oid = opp.get("opportunity_id", "UNKNOWN")
        ev = ev_all["programs"].get(oid)
        elig = eligibility_state(opp, ev)
        pay, rails = payout_state(ev, ev_all["rails"])
        rows.append({
            "opportunity_id": oid,
            "program_name": opp.get("program_name", "UNKNOWN"),
            "category": opp.get("category", "UNKNOWN"),
            "eligibility_state": elig,
            "eligibility_basis": (ev or {}).get("eligibility_basis", "UNKNOWN"),
            "payout_state": pay,
            "payout_rails": rails,
            "payout_note": (ev or {}).get("payout_note", "UNKNOWN"),
            "account_observed": (ev or {}).get("account_observed"),
            "evidence_sources": (ev or {}).get("sources", []),
            "evidence_checked": (ev or {}).get("checked", "UNKNOWN"),
            "next_action": _next_action(elig, pay),
        })
    return rows


def summary(rows=None):
    rows = rows if rows is not None else matrix()
    by_e, by_p = {}, {}
    for r in rows:
        by_e[r["eligibility_state"]] = by_e.get(r["eligibility_state"], 0) + 1
        by_p[r["payout_state"]] = by_p.get(r["payout_state"], 0) + 1
    return {"generated_at": datetime.now(timezone.utc).isoformat(),
            "programs": len(rows), "by_eligibility": by_e, "by_payout": by_p,
            "payout_verified": by_p.get("PAYOUT_VERIFIED", 0),
            "note": "eligibility and payout are independent; neither is approval or income"}

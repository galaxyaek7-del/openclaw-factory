#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — Affiliate program registry (authoritative READ model).

Directive statuses: CANDIDATE RESEARCHING QUALIFIED APPLIED APPROVED ACTIVE
HOLD REJECTED EXPIRED DISCONTINUED. Lifecycle: DISCOVERED RESEARCH QUALIFIED
APPROVAL_REQUIRED APPLY APPROVED VERIFY_LINK CREATE_CONTENT PUBLISH TRACK
MEASURE OPTIMIZE (+ REJECTED / HOLD / SCALE_CANDIDATE).

Single authoritative SOURCE remains data/commission_opportunities.jsonl
(written only by affiliate_discovery.merge_newly_verified_programs);
business_development.PLATFORM_REGISTRY and data/affiliate_links.jsonl are
cited, never duplicated. This module only READS. No network. No secrets.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

FACTORY_DIR = Path(__file__).resolve().parent.parent
OPPORTUNITIES = FACTORY_DIR / "data" / "commission_opportunities.jsonl"
PIPELINE = FACTORY_DIR / "data" / "partnership_pipeline.jsonl"
LINKS = FACTORY_DIR / "data" / "affiliate_links.jsonl"
# 2026-10-23: program approvals observed from the network (an approval email,
# the partner dashboard). Evidence, not a founder decision: nothing here
# applies to a program or changes an account.
APPROVALS = FACTORY_DIR / "data" / "affiliate_program_approvals.jsonl"
APPROVAL_STATES = ("APPLIED", "PENDING_REVIEW", "APPROVED", "REJECTED")

VALID_STATUSES = {"CANDIDATE", "RESEARCHING", "QUALIFIED", "APPLIED",
                  "APPROVED", "ACTIVE", "HOLD", "REJECTED", "EXPIRED",
                  "DISCONTINUED"}


def _read_jsonl(path):
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def load_opportunities():
    return _read_jsonl(OPPORTUNITIES)


def load_pipeline():
    return _read_jsonl(PIPELINE)


def load_links():
    return _read_jsonl(LINKS)


def _pipeline_stage_for(partner_id, pipeline_rows):
    for r in pipeline_rows:
        if r.get("partner") == partner_id or r.get("platform") == partner_id:
            return r.get("stage")
    return None


def derive_status(opp, pipeline_stage):
    """Honest status derivation. No approval record exists for any affiliate
    program today, so nothing may report APPROVED/ACTIVE from affiliate
    approval. A merchant-side ACTIVE (paddle) is not affiliate approval."""
    if not isinstance(opp, dict):
        return "CANDIDATE"
    verification = str(opp.get("verification_status", "") or opp.get("status", "")).upper()
    if "DISCONTINU" in verification or "CLOSED" in verification:
        return "DISCONTINUED"
    if pipeline_stage == "ACTIVE" and opp.get("category") != "affiliate":
        return "HOLD"  # merchant-active, affiliate angle still undiscovered
    if "REJECT" in verification:
        return "REJECTED"
    if "VERIFIED" in verification or "PARTIALLY_VERIFIED" in verification:
        evidence = opp.get("evidence_url")
        if evidence:
            return "QUALIFIED"
        return "RESEARCHING"
    if "THIRD_PARTY" in verification:
        return "RESEARCHING"
    return "CANDIDATE"


def lifecycle_stage(status):
    return {"CANDIDATE": "DISCOVERED", "RESEARCHING": "RESEARCH",
            "QUALIFIED": "QUALIFIED", "APPLIED": "APPLY",
            "APPROVED": "APPROVED", "ACTIVE": "TRACK",
            "HOLD": "HOLD", "REJECTED": "REJECTED",
            "EXPIRED": "REJECTED", "DISCONTINUED": "REJECTED"}.get(status, "DISCOVERED")


def _first_known(opp, *keys):
    for k in keys:
        v = opp.get(k)
        if v not in (None, "", [], "UNKNOWN"):
            return v
    return "UNKNOWN"


def record_approval(opportunity_id, approval_status, evidence, approvals_path=None, now=None):
    """Append one observed approval state for a program. APPROVED and
    REJECTED need evidence of at least 10 characters (e.g. "approval email
    2026-10-25 from partners@acme, ref 4411"). Returns {"ok", "entry"|"error"}."""
    if approval_status not in APPROVAL_STATES:
        return {"ok": False, "error": f"approval_status must be one of {APPROVAL_STATES}"}
    if not isinstance(opportunity_id, str) or not opportunity_id.strip():
        return {"ok": False, "error": "opportunity_id required"}
    if approval_status in ("APPROVED", "REJECTED") and len(str(evidence or "").strip()) < 10:
        return {"ok": False, "error": f"{approval_status} needs evidence (at least 10 characters)"}
    entry = {"opportunity_id": opportunity_id.strip(), "approval_status": approval_status,
             "evidence": str(evidence or "").strip() or None,
             "recorded_at": (now or datetime.now(timezone.utc)).isoformat()}
    path = Path(approvals_path) if approvals_path else APPROVALS
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return {"ok": True, "entry": entry}


def latest_approvals(approvals_path=None):
    """{opportunity_id: latest approval entry}."""
    out = {}
    for row in _read_jsonl(Path(approvals_path) if approvals_path else APPROVALS):
        if isinstance(row, dict) and row.get("opportunity_id") and row.get("approval_status") in APPROVAL_STATES:
            out[row["opportunity_id"]] = row
    return out


def program_record(opp, pipeline_rows=None, link_rows=None, approvals=None):
    """Full §3 field set; UNKNOWN where no real source exists. Never invented."""
    pipeline_rows = pipeline_rows if pipeline_rows is not None else load_pipeline()
    link_rows = link_rows if link_rows is not None else load_links()
    approvals = approvals if approvals is not None else latest_approvals()
    pid = opp.get("opportunity_id", "UNKNOWN")
    partner = opp.get("partner_id", "UNKNOWN")
    status = derive_status(opp, _pipeline_stage_for(partner, pipeline_rows))
    approval = approvals.get(pid)
    approval_status = approval["approval_status"] if approval else "NOT_APPLIED"
    # An observed network decision overrides research status: APPROVED only
    # from recorded evidence, never inferred.
    if approval_status == "APPROVED" and status not in ("DISCONTINUED", "REJECTED"):
        status = "APPROVED"
    elif approval_status == "REJECTED":
        status = "REJECTED"
    elif approval_status in ("APPLIED", "PENDING_REVIEW") and status in ("CANDIDATE", "RESEARCHING", "QUALIFIED"):
        status = "APPLIED"
    tracked = [l for l in link_rows
               if partner in str(l.get("program", "")).lower()
               or partner in str(l.get("domain", "")).lower()]
    return {
        "program_name": opp.get("program_name", "UNKNOWN"),
        "merchant": opp.get("partner_name", partner),
        "official_url": opp.get("official_url", opp.get("evidence_url", "UNKNOWN")),
        "affiliate_signup_url": opp.get("signup_url", "UNKNOWN"),
        "affiliate_status": status,
        "approval_status": approval_status,
        "approval_evidence": approval.get("evidence") if approval else None,
        "commission_model": opp.get("commission_type", "UNKNOWN"),
        "commission_rate": opp.get("commission_value", "UNKNOWN"),
        "recurring": opp.get("recurring_commission", "UNKNOWN"),
        "cookie_duration": opp.get("cookie_or_tracking_window", "UNKNOWN"),
        # 2026-10-22: the registry stores these as payout_minimum /
        # payout_methods / geography; reading only the older names made every
        # program show UNKNOWN even where the value was recorded.
        "payout_threshold": _first_known(opp, "payout_threshold", "payout_minimum"),
        "payout_method": _first_known(opp, "payout_method", "payout_methods"),
        "geographic_restrictions": _first_known(opp, "geographic_restrictions", "geography"),
        "prohibited_traffic_sources": opp.get("prohibited_traffic", "UNKNOWN"),
        "brand_restrictions": opp.get("brand_restrictions", "UNKNOWN"),
        "content_restrictions": opp.get("content_restrictions", "UNKNOWN"),
        "attribution_rules": opp.get("attribution_rules", "UNKNOWN"),
        "refund_rules": opp.get("refund_rules", "UNKNOWN"),
        "evidence_source": opp.get("source", "UNKNOWN"),
        "verification_date": opp.get("last_verified", "UNKNOWN"),
        "affiliate_link": "NOT_CONFIGURED",
        "tracking_identifier": tracked[0].get("tracking_id") if tracked else "NONE",
        "current_status": status,
        "lifecycle": lifecycle_stage(status),
        "opportunity_id": pid,
    }


def registry_summary():
    opps = load_opportunities()
    pipe = load_pipeline()
    links = load_links()
    approvals = latest_approvals()
    records = [program_record(o, pipe, links, approvals) for o in opps]
    by_status = {}
    for r in records:
        by_status[r["affiliate_status"]] = by_status.get(r["affiliate_status"], 0) + 1
    return {"total_programs": len(records), "by_status": by_status,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "authoritative_source": "data/commission_opportunities.jsonl",
            "records": records}

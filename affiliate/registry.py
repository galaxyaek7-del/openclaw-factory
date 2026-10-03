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


def program_record(opp, pipeline_rows=None, link_rows=None):
    """Full §3 field set; UNKNOWN where no real source exists. Never invented."""
    pipeline_rows = pipeline_rows if pipeline_rows is not None else load_pipeline()
    link_rows = link_rows if link_rows is not None else load_links()
    pid = opp.get("opportunity_id", "UNKNOWN")
    partner = opp.get("partner_id", "UNKNOWN")
    status = derive_status(opp, _pipeline_stage_for(partner, pipeline_rows))
    tracked = [l for l in link_rows
               if partner in str(l.get("program", "")).lower()
               or partner in str(l.get("domain", "")).lower()]
    return {
        "program_name": opp.get("program_name", "UNKNOWN"),
        "merchant": opp.get("partner_name", partner),
        "official_url": opp.get("official_url", opp.get("evidence_url", "UNKNOWN")),
        "affiliate_signup_url": opp.get("signup_url", "UNKNOWN"),
        "affiliate_status": status,
        "approval_status": "NOT_APPLIED",
        "commission_model": opp.get("commission_type", "UNKNOWN"),
        "commission_rate": opp.get("commission_value", "UNKNOWN"),
        "recurring": opp.get("recurring_commission", "UNKNOWN"),
        "cookie_duration": opp.get("cookie_or_tracking_window", "UNKNOWN"),
        "payout_threshold": opp.get("payout_threshold", "UNKNOWN"),
        "payout_method": opp.get("payout_method", "UNKNOWN"),
        "geographic_restrictions": opp.get("geographic_restrictions", "UNKNOWN"),
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
    records = [program_record(o, pipe, links) for o in opps]
    by_status = {}
    for r in records:
        by_status[r["affiliate_status"]] = by_status.get(r["affiliate_status"], 0) + 1
    return {"total_programs": len(records), "by_status": by_status,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "authoritative_source": "data/commission_opportunities.jsonl",
            "records": records}

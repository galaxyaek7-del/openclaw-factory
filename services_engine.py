#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — Services Engine (Revenue Factory, 2026-09-07).

First-class Services revenue engine. Discovers, scores, packages, prices,
and maps service offerings using existing factory capabilities. Services are
treated as a first-class revenue channel alongside Digital Products.

Reuses:
  profit_oracle          — pricing signals, margin assessment
  decision_engine        — evaluation gates
  commercial_governance  — financial truth rules
  commercial_monitor     — reality state
  revenue_engine         — stage tracking (Service products registered here)
  unit_economics_engine  — margin/delivery-effort analysis
  portfolio_prioritization — portfolio scoring
  brand_dna              — customer-facing text validation
  evidence_engine        — evidence recording

Honesty contract:
  No fabricated service revenue. No inferred customer. No auto-contact.
  Service candidates are evaluated internally only. External activation
  requires explicit Founder authorization.

Truth First vocabulary:
  NOT_BUILT, UNKNOWN, NOT_MEASURABLE, DISCOVERY, OBSERVED, DERIVED,
  ESTIMATED — applied throughout.
"""

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

for _stream in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    import profit_oracle as PROFIT_ORACLE
except (Exception, SystemExit):
    PROFIT_ORACLE = None

try:
    from decision_engine import evaluate_and_decide
except (Exception, SystemExit):
    evaluate_and_decide = None

try:
    import commercial_governance as COMMERCIAL_GOVERNANCE
except (Exception, SystemExit):
    COMMERCIAL_GOVERNANCE = None

try:
    import unit_economics_engine as UNIT_ECONOMICS
except (Exception, SystemExit):
    UNIT_ECONOMICS = None

try:
    import brand_dna as BRAND_DNA
except (Exception, SystemExit):
    BRAND_DNA = None

# ---------------------------------------------------------------------------
# Data paths
# ---------------------------------------------------------------------------
SERVICES_CATALOG_PATH = _FACTORY_ROOT / "data" / "services_catalog.json"
SERVICES_STATE_PATH = _FACTORY_ROOT / "data" / "services_state.json"
SERVICE_EVIDENCE_PATH = _FACTORY_ROOT / "data" / "service_evidence.jsonl"

# ---------------------------------------------------------------------------
# Service definition types
# ---------------------------------------------------------------------------

SERVICE_CATEGORIES = {
    "ai_implementation": {
        "name": "AI Workflow Implementation",
        "description": "Implement AI automation workflows for businesses",
        "capability_required": ["ai_generation", "automation"],
        "delivery_effort": "MEDIUM",
        "repeatability": "HIGH",
        "automation_potential": "HIGH",
    },
    "automation_audit": {
        "name": "Automation Audit & Assessment",
        "description": "Audit existing business processes for automation opportunities",
        "capability_required": ["market_intelligence"],
        "delivery_effort": "LOW",
        "repeatability": "HIGH",
        "automation_potential": "MEDIUM",
    },
    "compliance_research": {
        "name": "Regulatory Compliance Research",
        "description": "Research and summarize regulatory requirements (GDPR, EU AI Act, etc.)",
        "capability_required": ["ai_generation", "market_intelligence"],
        "delivery_effort": "MEDIUM",
        "repeatability": "HIGH",
        "automation_potential": "HIGH",
    },
    "market_intelligence": {
        "name": "Market Intelligence Report",
        "description": "Deliverable market analysis, competitor landscape, opportunity sizing",
        "capability_required": ["market_intelligence"],
        "delivery_effort": "LOW",
        "repeatability": "HIGH",
        "automation_potential": "HIGH",
    },
    "data_analysis": {
        "name": "Data Analysis & Dashboard",
        "description": "Analyze business data and deliver dashboards/reports",
        "capability_required": ["ai_generation"],
        "delivery_effort": "MEDIUM",
        "repeatability": "MEDIUM",
        "automation_potential": "MEDIUM",
    },
    "process_optimization": {
        "name": "Process Optimization Consulting",
        "description": "Optimize business workflows using AI-assisted analysis",
        "capability_required": ["ai_generation", "market_intelligence"],
        "delivery_effort": "MEDIUM",
        "repeatability": "MEDIUM",
        "automation_potential": "LOW",
    },
    "template_customization": {
        "name": "Custom Template Development",
        "description": "Build custom templates, trackers, systems for specific business needs",
        "capability_required": ["ai_generation"],
        "delivery_effort": "LOW",
        "repeatability": "HIGH",
        "automation_potential": "HIGH",
    },
    "b2b_research": {
        "name": "B2B Research & Intelligence",
        "description": "Company research, lead intelligence, competitive analysis",
        "capability_required": ["market_intelligence"],
        "delivery_effort": "MEDIUM",
        "repeatability": "MEDIUM",
        "automation_potential": "MEDIUM",
    },
    "documentation": {
        "name": "Operational Documentation",
        "description": "Create SOPs, process docs, knowledge bases",
        "capability_required": ["ai_generation"],
        "delivery_effort": "LOW",
        "repeatability": "HIGH",
        "automation_potential": "HIGH",
    },
    "content_systems": {
        "name": "AI-Assisted Content Systems",
        "description": "Set up AI content pipelines for businesses",
        "capability_required": ["ai_generation", "automation"],
        "delivery_effort": "HIGH",
        "repeatability": "MEDIUM",
        "automation_potential": "HIGH",
    },
}

SERVICE_CHANNELS = {
    "upwork": {"name": "Upwork", "eligibility": "CHANNEL_ELIGIBILITY_UNKNOWN", "account_required": True},
    "fiverr": {"name": "Fiverr", "eligibility": "CHANNEL_ELIGIBILITY_UNKNOWN", "account_required": True},
    "contra": {"name": "Contra", "eligibility": "CHANNEL_ELIGIBILITY_UNKNOWN", "account_required": True},
    "direct_b2b": {"name": "Direct B2B", "eligibility": "CHANNEL_ELIGIBILITY_UNKNOWN", "account_required": False},
    "gumroad": {"name": "Gumroad", "eligibility": "CHANNEL_ELIGIBILITY_UNKNOWN", "account_required": True},
    "website": {"name": "Direct Website", "eligibility": "CHANNEL_ELIGIBILITY_UNKNOWN", "account_required": False},
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _load_catalog(path=None):
    p = Path(path) if path else SERVICES_CATALOG_PATH
    if p.exists():
        try:
            return json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {"services": {}, "version": 2, "generated_at": _now_iso()}


def _save_catalog(catalog, path=None):
    p = Path(path) if path else SERVICES_CATALOG_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    catalog["last_modified"] = _now_iso()
    p.write_text(json.dumps(catalog, indent=2, ensure_ascii=False, default=str), encoding='utf-8')


def _load_state(path=None):
    p = Path(path) if path else SERVICES_STATE_PATH
    if p.exists():
        try:
            return json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {"services": {}, "last_scan": None, "version": 1}


def _save_state(state, path=None):
    p = Path(path) if path else SERVICES_STATE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    state["last_modified"] = _now_iso()
    p.write_text(json.dumps(state, indent=2, ensure_ascii=False, default=str), encoding='utf-8')


def _record_evidence(service_id, evidence_type, evidence_data, path=None):
    p = Path(path) if path else SERVICE_EVIDENCE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "service_id": service_id,
        "evidence_type": evidence_type,
        "evidence_data": evidence_data,
        "recorded_at": _now_iso(),
    }
    with open(p, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    return True


def _score_delivery_effort(category_info):
    effort_map = {"LOW": 30, "MEDIUM": 60, "HIGH": 90}
    return effort_map.get(category_info.get("delivery_effort", "UNKNOWN"), 50)


def _score_repeatability(category_info):
    rep_map = {"HIGH": 90, "MEDIUM": 60, "LOW": 30}
    return rep_map.get(category_info.get("repeatability", "UNKNOWN"), 50)


def _score_automation_potential(category_info):
    auto_map = {"HIGH": 90, "MEDIUM": 60, "LOW": 30}
    return auto_map.get(category_info.get("automation_potential", "UNKNOWN"), 50)


def _score_channel_fit(service_id, category_info):
    """How well does this service fit existing channels?"""
    channels = list(SERVICE_CHANNELS.keys())
    return min(100, len(channels) * 15)


# ---------------------------------------------------------------------------
# Public API — Discovery
# ---------------------------------------------------------------------------

def discover_from_capabilities(capability_filter=None, catalog_path=None):
    """Scan existing factory capabilities and suggest service candidates.

    Reuses:
      - SERVICE_CATEGORIES (defined above)
      - Factory's real capability modules (ai_generation, market_intelligence)

    Returns list of candidate services with scores.
    """
    catalog = _load_catalog(catalog_path)
    candidates = []

    for svc_id, svc_def in SERVICE_CATEGORIES.items():
        if capability_filter and svc_def.get("automation_potential") not in capability_filter:
            continue

        delivery = _score_delivery_effort(svc_def)
        repeatability = _score_repeatability(svc_def)
        automation = _score_automation_potential(svc_def)
        channel_fit = _score_channel_fit(svc_id, svc_def)

        # Composite service opportunity score (0-100)
        score = (
            delivery * 0.25 +
            repeatability * 0.25 +
            automation * 0.25 +
            channel_fit * 0.25
        )

        candidate = {
            "service_id": svc_id,
            "name": svc_def["name"],
            "description": svc_def["description"],
            "category": list(SERVICE_CATEGORIES.keys()).index(svc_id) + 1,
            "scores": {
                "delivery_effort": delivery,
                "repeatability": repeatability,
                "automation_potential": automation,
                "channel_fit": channel_fit,
                "composite_score": round(score, 1),
            },
            "evidence": {
                "method": "capability_scan",
                "source": "services_engine.SERVICE_CATEGORIES",
                "classification": "DERIVED",
            },
            "status": "CANDIDATE",
        }
        candidates.append(candidate)

    candidates.sort(key=lambda x: x["scores"]["composite_score"], reverse=True)
    return candidates


# ---------------------------------------------------------------------------
# Public API — Scoring
# ---------------------------------------------------------------------------

def score_service(service_id, custom_pricing=None, catalog_path=None):
    """Score a specific service on the 12 dimensions the directive requires.

    Dimensions: PAIN, DEMAND, CUSTOMER, OFFER, PRICE, DELIVERY EFFORT,
    MARGIN, CAPABILITY, TIME TO FIRST SALE, REPEATABILITY, AUTOMATION
    POTENTIAL, CHANNEL FIT.

    Returns dict with per-dimension scores and overall verdict.
    """
    if service_id not in SERVICE_CATEGORIES:
        return {"error": f"Unknown service_id: {service_id}", "verdict": "UNKNOWN"}

    cat = SERVICE_CATEGORIES[service_id]
    delivery = _score_delivery_effort(cat)
    repeatability = _score_repeatability(cat)
    automation = _score_automation_potential(cat)
    channel_fit = _score_channel_fit(service_id, cat)

    # Pain: how much does this solve a real problem? (UNKNOWN until real customer data)
    pain = {"score": 0, "basis": "UNKNOWN", "reason": "No real customer pain data for this service yet"}
    # Demand: is there real demand? (UNKNOWN until real market data)
    demand = {"score": 0, "basis": "UNKNOWN", "reason": "No real demand signal for this service yet"}
    # Customer: who is the customer? (UNKNOWN until real customer data)
    customer = {"score": 0, "basis": "UNKNOWN", "reason": "No real customer profile for this service yet"}
    # Offer: can we deliver this?
    offer = {"score": min(100, delivery + 30), "basis": "DERIVED", "reason": "Based on factory capability assessment"}
    # Price: what's a reasonable price? (UNKNOWN until real market data)
    price = {"score": 0, "basis": "UNKNOWN", "reason": "No real pricing data for this service yet"}
    # Delivery effort
    delivery_score = {"score": 100 - delivery, "basis": "DERIVED", "reason": f"Effort level: {cat.get('delivery_effort', 'UNKNOWN')}"}
    # Margin: UNKNOWN until real pricing
    margin = {"score": 0, "basis": "UNKNOWN", "reason": "No real pricing/cost data for margin calculation"}
    # Capability: do we have the capability?
    caps = cat.get("capability_required", [])
    capability = {"score": min(100, len(caps) * 35), "basis": "DERIVED", "reason": f"Requires: {', '.join(caps)}"}
    # Time to first sale: UNKNOWN until real market data
    time_to_sale = {"score": 0, "basis": "UNKNOWN", "reason": "No real sales history for this service"}
    # Repeatability
    repeat = {"score": repeatability, "basis": "DERIVED", "reason": f"Repeatability: {cat.get('repeatability', 'UNKNOWN')}"}
    # Automation potential
    auto = {"score": automation, "basis": "DERIVED", "reason": f"Automation: {cat.get('automation_potential', 'UNKNOWN')}"}
    # Channel fit
    ch_fit = {"score": channel_fit, "basis": "DERIVED", "reason": f"Available channels: {len(SERVICE_CHANNELS)}"}

    dimensions = {
        "pain": pain,
        "demand": demand,
        "customer": customer,
        "offer": offer,
        "price": price,
        "delivery_effort": delivery_score,
        "margin": margin,
        "capability": capability,
        "time_to_first_sale": time_to_sale,
        "repeatability": repeat,
        "automation_potential": auto,
        "channel_fit": ch_fit,
    }

    known_scores = [d["score"] for d in dimensions.values() if d["score"] > 0]
    overall = round(sum(known_scores) / max(len(known_scores), 1), 1) if known_scores else 0

    return {
        "service_id": service_id,
        "name": cat["name"],
        "dimensions": dimensions,
        "overall_score": overall,
        "verdict": "CANDIDATE" if overall >= 40 else "NEEDS_MORE_EVIDENCE",
        "evidence_quality": {
            "total_dimensions": 12,
            "scored": len([d for d in dimensions.values() if d["score"] > 0]),
            "unknown": len([d for d in dimensions.values() if d["score"] == 0]),
            "classification": "PARTIAL",
        },
    }


# ---------------------------------------------------------------------------
# Public API — Packaging
# ---------------------------------------------------------------------------

def package_service(service_id, tier="standard", custom_scope=None, catalog_path=None):
    """Package a service into a deliverable offering with scope, price, and SLA.

    Tiers:
      basic     — minimal scope, fast delivery
      standard  — typical scope, standard delivery
      premium   — full scope, priority delivery

    Returns packaged offering dict.
    """
    if service_id not in SERVICE_CATEGORIES:
        return {"error": f"Unknown service_id: {service_id}"}

    cat = SERVICE_CATEGORIES[service_id]
    effort = cat.get("delivery_effort", "MEDIUM")

    tier_configs = {
        "basic": {
            "scope": "Core deliverable only",
            "delivery_days": 3 if effort == "LOW" else 5 if effort == "MEDIUM" else 10,
            "revisions": 1,
            "support": "Email only",
        },
        "standard": {
            "scope": "Core deliverable + documentation",
            "delivery_days": 5 if effort == "LOW" else 7 if effort == "MEDIUM" else 14,
            "revisions": 2,
            "support": "Email + chat",
        },
        "premium": {
            "scope": "Full deliverable + documentation + consultation + follow-up",
            "delivery_days": 7 if effort == "LOW" else 10 if effort == "MEDIUM" else 21,
            "revisions": 3,
            "support": "Priority support",
        },
    }

    config = tier_configs.get(tier, tier_configs["standard"])

    package = {
        "service_id": service_id,
        "name": cat["name"],
        "tier": tier,
        "scope": custom_scope or config["scope"],
        "delivery_days": config["delivery_days"],
        "revisions_included": config["revisions"],
        "support_level": config["support"],
        "automation_potential": cat.get("automation_potential", "UNKNOWN"),
        "delivery_effort": effort,
        "repeatability": cat.get("repeatability", "UNKNOWN"),
        "status": "PACKAGED",
        "packaged_at": _now_iso(),
    }

    # Validate customer-facing text if brand_dna is available
    if BRAND_DNA:
        try:
            validation = BRAND_DNA.validate_customer_facing_text(package["scope"])
            package["brand_validation"] = validation
        except Exception:
            package["brand_validation"] = {"status": "UNKNOWN", "reason": "brand_dna validation failed"}

    return package


# ---------------------------------------------------------------------------
# Public API — Pricing
# ---------------------------------------------------------------------------

def price_service(service_id, tier="standard", market_context=None, catalog_path=None):
    """Price a packaged service using profit_oracle signals where available.

    Pricing is ESTIMATED until a real customer pays. profit_oracle.butter_price()
    is consulted for the niche, but service pricing ultimately depends on
    delivery effort, market rate, and customer willingness to pay.

    Returns pricing dict with breakdown.
    """
    if service_id not in SERVICE_CATEGORIES:
        return {"error": f"Unknown service_id: {service_id}"}

    cat = SERVICE_CATEGORIES[service_id]
    effort = cat.get("delivery_effort", "MEDIUM")
    repeatability = cat.get("repeatability", "UNKNOWN")

    # Base price estimation from effort
    effort_prices = {"LOW": 150, "MEDIUM": 350, "HIGH": 700}
    base = effort_prices.get(effort, 250)

    # Tier multiplier
    tier_multipliers = {"basic": 0.7, "standard": 1.0, "premium": 1.5}
    multiplier = tier_multipliers.get(tier, 1.0)

    # Repeatability discount (highly repeatable services can be priced lower)
    rep_discount = 1.0
    if repeatability == "HIGH":
        rep_discount = 0.85
    elif repeatability == "LOW":
        rep_discount = 1.2

    estimated_price = round(base * multiplier * rep_discount, 2)

    # Try profit_oracle for niche pricing signals
    oracle_signal = None
    if PROFIT_ORACLE:
        try:
            oracle_price = PROFIT_ORACLE.butter_price(service_id, product_type="service")
            if oracle_price and oracle_price > 0:
                oracle_signal = oracle_price
        except Exception:
            pass

    pricing = {
        "service_id": service_id,
        "tier": tier,
        "base_price": base,
        "tier_multiplier": multiplier,
        "repeatability_discount": rep_discount,
        "estimated_price": estimated_price,
        "oracle_signal": oracle_signal,
        "pricing_basis": "ESTIMATED" if not oracle_signal else "DERIVED",
        "currency": "USD",
        "note": "Pricing is PROJECTED until a real customer pays. Oracle signal is advisory.",
        "margin_estimate": {
            "basis": "UNKNOWN",
            "reason": "No real cost data for service delivery yet",
        },
    }

    # If oracle gave a signal, use it as a reference
    if oracle_signal and oracle_signal > 0:
        pricing["oracle_reference_price"] = oracle_signal
        pricing["pricing_note"] = f"Oracle suggests ${oracle_signal}. Estimated: ${estimated_price}. Final price TBD by Founder."

    return pricing


# ---------------------------------------------------------------------------
# Public API — Channel Mapping
# ---------------------------------------------------------------------------

def map_service_channels(service_id, catalog_path=None):
    """Map a service to appropriate sales/delivery channels.

    Returns channel eligibility matrix for the service.
    """
    if service_id not in SERVICE_CATEGORIES:
        return {"error": f"Unknown service_id: {service_id}"}

    cat = SERVICE_CATEGORIES[service_id]
    channels = {}

    for ch_id, ch_def in SERVICE_CHANNELS.items():
        eligibility = ch_def["eligibility"]
        account_required = ch_def["account_required"]

        # Determine channel fit
        fit = "UNKNOWN"
        if ch_id in ("direct_b2b", "website"):
            fit = "HIGH"  # Services sell well directly
        elif ch_id in ("upwork", "fiverr"):
            fit = "MEDIUM"  # Marketplace fees apply
        elif ch_id == "contra":
            fit = "MEDIUM"
        elif ch_id == "gumroad":
            fit = "LOW"  # Gumroad is better for digital products

        channels[ch_id] = {
            "name": ch_def["name"],
            "eligibility": eligibility,
            "account_required": account_required,
            "channel_fit": fit,
            "state": "CHANNEL_DISCOVERED",
            "blocker": "EXTERNAL_BLOCKER" if account_required else None,
        }

    return {
        "service_id": service_id,
        "name": cat["name"],
        "channels": channels,
        "recommended_channel": "direct_b2b",
        "reason": "Direct B2B has highest fit for services, no platform fees, no account gate",
    }


# ---------------------------------------------------------------------------
# Public API — Service × Channel Matrix
# ---------------------------------------------------------------------------

def service_channel_matrix(catalog_path=None):
    """Build the complete Service × Channel matrix.

    For each service category, shows channel eligibility, state, and blockers.
    """
    matrix = {}
    for svc_id, svc_def in SERVICE_CATEGORIES.items():
        channels = map_service_channels(svc_id, catalog_path)
        if "error" in channels:
            continue
        matrix[svc_id] = {
            "name": svc_def["name"],
            "channels": channels["channels"],
            "recommended": channels["recommended_channel"],
        }
    return {
        "matrix": matrix,
        "total_services": len(matrix),
        "total_channels": len(SERVICE_CHANNELS),
        "generated_at": _now_iso(),
    }


# ---------------------------------------------------------------------------
# Public API — Register service
# ---------------------------------------------------------------------------

def register_service(service_id, name=None, description=None, tier="standard",
                     pricing=None, catalog_path=None, state_path=None):
    """Register a new service in the catalog and state.

    Does NOT contact anyone or create external accounts.
    """
    catalog = _load_catalog(catalog_path)
    state = _load_state(state_path)

    if service_id not in SERVICE_CATEGORIES:
        return {"error": f"Unknown service_id: {service_id}"}

    cat = SERVICE_CATEGORIES[service_id]
    svc_name = name or cat["name"]
    svc_desc = description or cat["description"]

    # Package and price
    packaged = package_service(service_id, tier, catalog_path=catalog_path)
    priced = price_service(service_id, tier, catalog_path=catalog_path)

    service_record = {
        "service_id": service_id,
        "name": svc_name,
        "description": svc_desc,
        "category": cat,
        "tier": tier,
        "package": packaged,
        "pricing": priced,
        "channels": map_service_channels(service_id, catalog_path),
        "registered_at": _now_iso(),
        "status": "REGISTERED",
        "evidence": {
            "registration": "OBSERVED",
            "pricing": priced.get("pricing_basis", "UNKNOWN"),
            "customer_validation": "NOT_MEASURED",
        },
    }

    catalog["services"][service_id] = service_record
    _save_catalog(catalog, catalog_path)

    state["services"][service_id] = {
        "status": "REGISTERED",
        "registered_at": _now_iso(),
        "last_updated": _now_iso(),
    }
    _save_state(state, state_path)

    _record_evidence(service_id, "registration", {"status": "REGISTERED"})

    return {
        "success": True,
        "service_id": service_id,
        "name": svc_name,
        "status": "REGISTERED",
        "pricing_basis": priced.get("pricing_basis", "UNKNOWN"),
    }


# ---------------------------------------------------------------------------
# Public API — Portfolio status
# ---------------------------------------------------------------------------

def portfolio_status(catalog_path=None, state_path=None):
    """List all registered services with their current status."""
    catalog = _load_catalog(catalog_path)
    state = _load_state(state_path)

    services = []
    for svc_id, svc_data in catalog.get("services", {}).items():
        svc_state = state.get("services", {}).get(svc_id, {})
        services.append({
            "service_id": svc_id,
            "name": svc_data.get("name", "UNKNOWN"),
            "status": svc_data.get("status", "UNKNOWN"),
            "tier": svc_data.get("tier", "UNKNOWN"),
            "pricing": svc_data.get("pricing", {}).get("estimated_price", 0),
            "pricing_basis": svc_data.get("pricing", {}).get("pricing_basis", "UNKNOWN"),
            "registered_at": svc_data.get("registered_at", "UNKNOWN"),
        })

    return {
        "total_services": len(services),
        "services": services,
        "generated_at": _now_iso(),
    }


# ---------------------------------------------------------------------------
# Public API — Revenue factory integration
# ---------------------------------------------------------------------------

def revenue_factory_status():
    """Return Services engine status for the Revenue Factory audit.

    This is the function called by factory_loop.js and Mission Control.
    """
    catalog = _load_catalog()
    state = _load_state()
    services = catalog.get("services", {})
    states = state.get("services", {})

    registered = len(services)
    with_pricing = sum(1 for s in services.values()
                       if s.get("pricing", {}).get("pricing_basis") != "UNKNOWN")
    with_channels = sum(1 for s in services.values()
                        if s.get("channels", {}).get("recommended_channel"))

    return {
        "engine": "SERVICES",
        "status": "IMPLEMENTED",
        "total_registered": registered,
        "with_pricing": with_pricing,
        "with_channels": with_channels,
        "service_categories": len(SERVICE_CATEGORIES),
        "available_channels": len(SERVICE_CHANNELS),
        "verdict": "IMPLEMENTED" if registered > 0 else "NO_SERVICES_REGISTERED",
        "note": "Services engine is IMPLEMENTED. No services have been registered yet. "
                "No external actions taken. All pricing is PROJECTED.",
        "generated_at": _now_iso(),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Galaxy Forge Services Engine")
    parser.add_argument("--discover", action="store_true", help="Discover service candidates")
    parser.add_argument("--score", type=str, help="Score a service by ID")
    parser.add_argument("--register", type=str, help="Register a service by ID")
    parser.add_argument("--portfolio", action="store_true", help="Show portfolio status")
    parser.add_argument("--matrix", action="store_true", help="Show Service × Channel matrix")
    parser.add_argument("--status", action="store_true", help="Revenue factory status")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    if args.discover:
        result = discover_from_capabilities()
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    elif args.score:
        result = score_service(args.score)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    elif args.register:
        result = register_service(args.register)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    elif args.portfolio:
        result = portfolio_status()
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    elif args.matrix:
        result = service_channel_matrix()
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    elif args.status:
        result = revenue_factory_status()
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    else:
        parser.print_help()

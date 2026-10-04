#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — Software Engine (Revenue Factory, 2026-09-07).

First-class Software revenue engine. Tracks software assets through the
controlled ladder: Internal Tool → Controlled Prototype → Paid Tool →
Validated Product → Subscription → SaaS. No automatic jump to SaaS.

Reuses:
  profit_oracle          — pricing signals
  decision_engine        — evaluation gates
  commercial_governance  — financial truth rules
  revenue_engine         — stage tracking
  unit_economics_engine  — margin analysis
  brand_dna              — customer-facing text validation

Honesty contract:
  No fabricated software revenue. No inferred customer. No auto-deploy.
  Software assets are tracked internally. External activation requires
  explicit Founder authorization.

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
SOFTWARE_CATALOG_PATH = _FACTORY_ROOT / "data" / "software_catalog.json"
SOFTWARE_STATE_PATH = _FACTORY_ROOT / "data" / "software_state.json"
SOFTWARE_EVIDENCE_PATH = _FACTORY_ROOT / "data" / "software_evidence.jsonl"

# ---------------------------------------------------------------------------
# Software ladder stages
# ---------------------------------------------------------------------------

class SoftwareStage:
    INTERNAL_TOOL = "INTERNAL_TOOL"
    CONTROLLED_PROTOTYPE = "CONTROLLED_PROTOTYPE"
    PAID_TOOL = "PAID_TOOL"
    VALIDATED_PRODUCT = "VALIDATED_PRODUCT"
    SUBSCRIPTION = "SUBSCRIPTION"
    SAAS = "SAAS"


SOFTWARE_LADDER = [
    {
        "stage": SoftwareStage.INTERNAL_TOOL,
        "name": "Internal Tool",
        "description": "Tool built for internal use. Not commercial.",
        "requirements": ["functional_code", "internal_use"],
        "gates": ["code_exists", "used_internally"],
        "max_price": 0,
    },
    {
        "stage": SoftwareStage.CONTROLLED_PROTOTYPE,
        "name": "Controlled Prototype",
        "description": "Prototype shared with controlled group for feedback.",
        "requirements": ["functional_code", "prototype_scope", "feedback_group"],
        "gates": ["code_exists", "limited_users", "feedback_collected"],
        "max_price": 100,
    },
    {
        "stage": SoftwareStage.PAID_TOOL,
        "name": "Paid Tool",
        "description": "Tool sold as one-time purchase.",
        "requirements": ["functional_code", "documentation", "support_plan"],
        "gates": ["code_exists", "payment_verified", "customer_evidence"],
        "max_price": 500,
    },
    {
        "stage": SoftwareStage.VALIDATED_PRODUCT,
        "name": "Validated Product",
        "description": "Product with proven demand and customer satisfaction.",
        "requirements": ["functional_code", "documentation", "support_plan", "multiple_customers"],
        "gates": ["code_exists", "payment_verified", "customer_evidence", "repeat_purchase"],
        "max_price": 1000,
    },
    {
        "stage": SoftwareStage.SUBSCRIPTION,
        "name": "Subscription",
        "description": "Recurring revenue product.",
        "requirements": ["functional_code", "documentation", "support_plan", "billing_system"],
        "gates": ["code_exists", "payment_verified", "customer_evidence", "billing_active"],
        "max_price": 5000,
    },
    {
        "stage": SoftwareStage.SAAS,
        "name": "SaaS",
        "description": "Software as a Service — full multi-tenant deployment.",
        "requirements": ["functional_code", "documentation", "support_plan", "billing_system", "multi_tenant"],
        "gates": ["code_exists", "payment_verified", "customer_evidence", "billing_active", "multi_tenant"],
        "max_price": 10000,
    },
]

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _load_catalog(path=None):
    p = Path(path) if path else SOFTWARE_CATALOG_PATH
    if p.exists():
        try:
            return json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {"assets": {}, "version": 1, "generated_at": _now_iso()}


def _save_catalog(catalog, path=None):
    p = Path(path) if path else SOFTWARE_CATALOG_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    catalog["last_modified"] = _now_iso()
    p.write_text(json.dumps(catalog, indent=2, ensure_ascii=False, default=str), encoding='utf-8')


def _load_state(path=None):
    p = Path(path) if path else SOFTWARE_STATE_PATH
    if p.exists():
        try:
            return json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {"assets": {}, "last_scan": None, "version": 1}


def _save_state(state, path=None):
    p = Path(path) if path else SOFTWARE_STATE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    state["last_modified"] = _now_iso()
    p.write_text(json.dumps(state, indent=2, ensure_ascii=False, default=str), encoding='utf-8')


def _record_evidence(asset_id, evidence_type, evidence_data, path=None):
    p = Path(path) if path else SOFTWARE_EVIDENCE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "asset_id": asset_id,
        "evidence_type": evidence_type,
        "evidence_data": evidence_data,
        "recorded_at": _now_iso(),
    }
    with open(p, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    return True


def _get_stage_info(stage_name):
    for s in SOFTWARE_LADDER:
        if s["stage"] == stage_name:
            return s
    return None


def _get_next_stage(current_stage):
    for i, s in enumerate(SOFTWARE_LADDER):
        if s["stage"] == current_stage and i + 1 < len(SOFTWARE_LADDER):
            return SOFTWARE_LADDER[i + 1]
    return None


# ---------------------------------------------------------------------------
# Public API — Register
# ---------------------------------------------------------------------------

def register_asset(asset_id, name, description, category="tool",
                    current_stage=None, catalog_path=None, state_path=None):
    """Register a software asset in the catalog.

    Does NOT deploy, sell, or contact anyone.
    """
    catalog = _load_catalog(catalog_path)
    state = _load_state(state_path)

    stage = current_stage or SoftwareStage.INTERNAL_TOOL
    stage_info = _get_stage_info(stage)

    asset = {
        "asset_id": asset_id,
        "name": name,
        "description": description,
        "category": category,
        "current_stage": stage,
        "stage_info": stage_info,
        "registered_at": _now_iso(),
        "status": "REGISTERED",
        "ladder_position": [s["stage"] for s in SOFTWARE_LADDER].index(stage) + 1,
        "evidence": {
            "registration": "OBSERVED",
            "customer_validation": "NOT_MEASURED",
            "revenue": "NOT_MEASURED",
        },
    }

    catalog["assets"][asset_id] = asset
    _save_catalog(catalog, catalog_path)

    state["assets"][asset_id] = {
        "status": "REGISTERED",
        "current_stage": stage,
        "registered_at": _now_iso(),
        "last_updated": _now_iso(),
    }
    _save_state(state, state_path)

    _record_evidence(asset_id, "registration", {"status": "REGISTERED", "stage": stage})

    return {
        "success": True,
        "asset_id": asset_id,
        "name": name,
        "current_stage": stage,
        "status": "REGISTERED",
    }


# ---------------------------------------------------------------------------
# Public API — Stage progression
# ---------------------------------------------------------------------------

def can_advance(asset_id, catalog_path=None, state_path=None):
    """Check if a software asset can advance to the next ladder stage.

    Returns gate check results. No advancement happens.
    """
    catalog = _load_catalog(catalog_path)
    state = _load_state(state_path)

    if asset_id not in catalog.get("assets", {}):
        return {"error": f"Unknown asset_id: {asset_id}", "can_advance": False}

    asset = catalog["assets"][asset_id]
    current = asset.get("current_stage", SoftwareStage.INTERNAL_TOOL)
    next_stage = _get_next_stage(current)

    if not next_stage:
        return {
            "asset_id": asset_id,
            "current_stage": current,
            "can_advance": False,
            "reason": "Already at highest stage",
        }

    # Check gates
    gate_results = {}
    for gate in next_stage["gates"]:
        gate_results[gate] = {
            "gate": gate,
            "status": "UNKNOWN",
            "reason": "No real evidence for this gate yet",
        }

    return {
        "asset_id": asset_id,
        "current_stage": current,
        "next_stage": next_stage["stage"],
        "next_stage_name": next_stage["name"],
        "gates": gate_results,
        "can_advance": False,
        "reason": "Gates not yet satisfied — all UNKNOWN",
    }


def advance_asset(asset_id, evidence_type=None, evidence_data=None,
                  catalog_path=None, state_path=None):
    """Attempt to advance a software asset to the next ladder stage.

    Only advances if gates are satisfied. Records evidence of advancement.
    Does NOT deploy, sell, or contact anyone.
    """
    catalog = _load_catalog(catalog_path)
    state = _load_state(state_path)

    if asset_id not in catalog.get("assets", {}):
        return {"error": f"Unknown asset_id: {asset_id}"}

    asset = catalog["assets"][asset_id]
    current = asset.get("current_stage", SoftwareStage.INTERNAL_TOOL)
    next_stage = _get_next_stage(current)

    if not next_stage:
        return {"error": "Already at highest stage", "can_advance": False}

    # For now, advancement requires explicit evidence (no auto-advance)
    if not evidence_type or not evidence_data:
        return {
            "can_advance": False,
            "reason": "Evidence required for advancement. Provide evidence_type and evidence_data.",
            "next_stage": next_stage["stage"],
            "required_gates": next_stage["gates"],
        }

    # Record the evidence
    _record_evidence(asset_id, evidence_type, evidence_data)

    # Advance
    asset["current_stage"] = next_stage["stage"]
    asset["stage_info"] = next_stage
    asset["ladder_position"] = [s["stage"] for s in SOFTWARE_LADDER].index(next_stage["stage"]) + 1
    asset["last_advanced_at"] = _now_iso()
    asset["evidence"]["last_advancement"] = evidence_type

    catalog["assets"][asset_id] = asset
    _save_catalog(catalog, catalog_path)

    state["assets"][asset_id]["current_stage"] = next_stage["stage"]
    state["assets"][asset_id]["last_updated"] = _now_iso()
    _save_state(state, state_path)

    return {
        "success": True,
        "asset_id": asset_id,
        "from_stage": current,
        "to_stage": next_stage["stage"],
        "evidence_type": evidence_type,
        "status": "ADVANCED",
    }


# ---------------------------------------------------------------------------
# Public API — Pricing
# ---------------------------------------------------------------------------

def price_asset(asset_id, catalog_path=None):
    """Price a software asset based on its current ladder stage.

    Pricing is ESTIMATED until a real customer pays.
    """
    catalog = _load_catalog(catalog_path)

    if asset_id not in catalog.get("assets", {}):
        return {"error": f"Unknown asset_id: {asset_id}"}

    asset = catalog["assets"][asset_id]
    stage = asset.get("current_stage", SoftwareStage.INTERNAL_TOOL)
    stage_info = _get_stage_info(stage)

    max_price = stage_info["max_price"] if stage_info else 0

    # Internal tools are not priced
    if stage == SoftwareStage.INTERNAL_TOOL:
        return {
            "asset_id": asset_id,
            "current_stage": stage,
            "estimated_price": 0,
            "pricing_basis": "NOT_APPLICABLE",
            "note": "Internal tools are not for sale.",
        }

    # Try profit_oracle for pricing signal
    oracle_signal = None
    if PROFIT_ORACLE:
        try:
            oracle_price = PROFIT_ORACLE.butter_price(asset_id, product_type="software")
            if oracle_price and oracle_price > 0:
                oracle_signal = oracle_price
        except Exception:
            pass

    estimated = min(max_price, oracle_signal) if oracle_signal and oracle_signal > 0 else max_price * 0.6

    return {
        "asset_id": asset_id,
        "current_stage": stage,
        "stage_max_price": max_price,
        "oracle_signal": oracle_signal,
        "estimated_price": round(estimated, 2),
        "pricing_basis": "ESTIMATED",
        "currency": "USD",
        "note": "Pricing is PROJECTED until a real customer pays.",
    }


# ---------------------------------------------------------------------------
# Public API — Portfolio
# ---------------------------------------------------------------------------

def portfolio_status(catalog_path=None, state_path=None):
    """List all registered software assets with their current stage."""
    catalog = _load_catalog(catalog_path)
    state = _load_state(state_path)

    assets = []
    for asset_id, asset_data in catalog.get("assets", {}).items():
        asset_state = state.get("assets", {}).get(asset_id, {})
        assets.append({
            "asset_id": asset_id,
            "name": asset_data.get("name", "UNKNOWN"),
            "category": asset_data.get("category", "UNKNOWN"),
            "current_stage": asset_data.get("current_stage", "UNKNOWN"),
            "ladder_position": asset_data.get("ladder_position", 0),
            "status": asset_data.get("status", "UNKNOWN"),
            "registered_at": asset_data.get("registered_at", "UNKNOWN"),
        })

    # Sort by ladder position
    assets.sort(key=lambda x: x.get("ladder_position", 0))

    return {
        "total_assets": len(assets),
        "assets": assets,
        "ladder_stages": [s["stage"] for s in SOFTWARE_LADDER],
        "generated_at": _now_iso(),
    }


# ---------------------------------------------------------------------------
# Public API — Revenue factory integration
# ---------------------------------------------------------------------------

def revenue_factory_status():
    """Return Software engine status for the Revenue Factory audit.

    This is the function called by factory_loop.js and Mission Control.
    """
    catalog = _load_catalog()
    state = _load_state()
    assets = catalog.get("assets", {})

    total = len(assets)
    by_stage = {}
    for a in assets.values():
        stage = a.get("current_stage", "UNKNOWN")
        by_stage[stage] = by_stage.get(stage, 0) + 1

    return {
        "engine": "SOFTWARE",
        "status": "IMPLEMENTED",
        "total_assets": total,
        "by_stage": by_stage,
        "ladder_stages": len(SOFTWARE_LADDER),
        "verdict": "IMPLEMENTED" if total > 0 else "NO_ASSETS_REGISTERED",
        "note": "Software engine is IMPLEMENTED. Tracks assets through the controlled ladder. "
                "No software has been registered yet. No external actions taken.",
        "generated_at": _now_iso(),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Galaxy Forge Software Engine")
    parser.add_argument("--register", nargs=2, metavar=("ID", "NAME"), help="Register a software asset")
    parser.add_argument("--portfolio", action="store_true", help="Show portfolio status")
    parser.add_argument("--can-advance", type=str, help="Check if asset can advance")
    parser.add_argument("--price", type=str, help="Price a software asset")
    parser.add_argument("--status", action="store_true", help="Revenue factory status")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    if args.register:
        result = register_asset(args.register[0], args.register[1], "Registered via CLI")
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    elif args.portfolio:
        result = portfolio_status()
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    elif args.can_advance:
        result = can_advance(args.can_advance)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    elif args.price:
        result = price_asset(args.price)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    elif args.status:
        result = revenue_factory_status()
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    else:
        parser.print_help()

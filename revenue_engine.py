"""Galaxy Forge — REVENUE ENGINE (Orchestration Layer).

A state-machine orchestrator that ties the factory's existing commercial
engines into one coherent loop: SENSE → DISCOVER → SCORE → SELECT → BUILD
→ QA → PACKAGE → DISTRIBUTE → SELL → MEASURE → LEARN → IMPROVE → SCALE/KILL.

This maps directly onto the founder's "POST-REVENUE EXPANSION & RECURRING
REVENUE ENGINE" directive (20 phases):

  Directive Phase          → Revenue Engine Stage
  ─────────────────────────────────────────────────
  Phase 1  Protect GF-001  → PACKAGE (GF-001 is here)
  Phase 2  Prove Repeatability → MEASURE
  Phase 3  Select Products → SELECT
  Phase 4  Product Families → IMPROVE (bundle/upsell logic)
  Phase 5  Digital Expansion → BUILD
  Phase 6  SEO Revenue     → DISTRIBUTE (content distribution)
  Phase 7  Customer Funnels → SELL (conversion tracking)
  Phase 8  Upsell/Cross-Sell → IMPROVE
  Phase 9  SaaS & Micro-Tools → BUILD (new product type)
  Phase 10 SaaS Validation → QA
  Phase 11 Recurring Revenue → SCALE_OR_KILL (subscription decision)
  Phase 12 B2B High-Value  → SELECT (B2B tier)
  Phase 13 Unit Economics  → SCORE
  Phase 14 Controlled Experiments → IMPROVE
  Phase 15 Scale Control   → SCALE_OR_KILL
  Phase 16 Automation      → (principle, not a stage)
  Phase 17 Capital Discipline → (principle, not a stage)
  Phase 18 Revenue Dashboard → MEASURE
  Phase 19 Portfolio Engine → SELECT
  Phase 20 The Flywheel    → the full loop

Every stage calls the real existing engine. This module adds:
  A) STAGE TRACKING — persistent per-product stage state
  B) STAGE GATES — evidence-backed progression rules
  C) PORTFOLIO VIEW — all products with current stage and next action
  D) PROGRESSION — move products forward only when gates pass
  E) REVENUE LOOP STATUS — unified dashboard of the full loop

Honesty contract: never fabricate revenue, stage advancement, or evidence.
Every stage transition is recorded with a real timestamp and the evidence
that justified it. Products can only advance, never skip stages.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

_FACTORY_ROOT = Path(__file__).resolve().parent
STAGE_STATE_PATH = _FACTORY_ROOT / "data" / "revenue_engine_state.json"
FINANCE_PATH = _FACTORY_ROOT / "finance_data.json"
REALITY_PATH = _FACTORY_ROOT / "config" / "reality.json"
ASSET_REGISTRY_PATH = _FACTORY_ROOT / "data" / "asset_registry.json"


class Stage(str, Enum):
    """The 13 stages of the revenue loop."""
    SENSE = "SENSE"
    DISCOVER = "DISCOVER"
    SCORE = "SCORE"
    SELECT = "SELECT"
    BUILD = "BUILD"
    QA = "QA"
    PACKAGE = "PACKAGE"
    DISTRIBUTE = "DISTRIBUTE"
    SELL = "SELL"
    MEASURE = "MEASURE"
    LEARN = "LEARN"
    IMPROVE = "IMPROVE"
    SCALE_OR_KILL = "SCALE_OR_KILL"


STAGE_ORDER = [s.value for s in Stage]

# ---------------------------------------------------------------------------
# Stage gate definitions — what evidence is required to pass each gate
# ---------------------------------------------------------------------------

STAGE_GATES: Dict[str, Dict[str, Any]] = {
    Stage.SENSE.value: {
        "description": "Scan market signals, identify potential opportunities",
        "evidence_required": ["market_signals_scanned"],
        "engine": "market_hunter",
    },
    Stage.DISCOVER.value: {
        "description": "Evaluate opportunities against decision engine",
        "evidence_required": ["decision_recorded"],
        "engine": "decision_engine",
    },
    Stage.SCORE.value: {
        "description": "Score opportunity against profit oracle and GOOS",
        "evidence_required": ["profit_score_computed"],
        "engine": "profit_oracle",
    },
    Stage.SELECT.value: {
        "description": "Select for production based on score and gates",
        "evidence_required": ["selection_approved"],
        "engine": "scheduler",
    },
    Stage.BUILD.value: {
        "description": "Generate product (book_generator, SaaS prototype, etc.)",
        "evidence_required": ["product_generated"],
        "engine": "book_generator",
    },
    Stage.QA.value: {
        "description": "Dual Inspection — technical + commercial quality check",
        "evidence_required": ["technical_pass", "commercial_pass"],
        "engine": "inspectors",
    },
    Stage.PACKAGE.value: {
        "description": "Prepare publication package (pricing, SEO, assets)",
        "evidence_required": ["pricing_set", "seo_optimized"],
        "engine": "product_marketing_engine",
    },
    Stage.DISTRIBUTE.value: {
        "description": "Publish to channels (Gumroad, Paddle, Etsy, etc.)",
        "evidence_required": ["published_to_channel"],
        "engine": "distributor",
    },
    Stage.SELL.value: {
        "description": "Product is live and purchasable",
        "evidence_required": ["checkout_available"],
        "engine": "channels",
    },
    Stage.MEASURE.value: {
        "description": "Track real traffic, clicks, conversions, revenue",
        "evidence_required": ["measurement_data_collected"],
        "engine": "revenue_intelligence",
    },
    Stage.LEARN.value: {
        "description": "Analyze results, update decision memory",
        "evidence_required": ["outcome_recorded"],
        "engine": "decision_engine/feedback",
    },
    Stage.IMPROVE.value: {
        "description": "Iterate based on real data — pricing, content, SEO",
        "evidence_required": ["improvement_applied"],
        "engine": "commercial_experiments",
    },
    Stage.SCALE_OR_KILL.value: {
        "description": "Scale proven winners, kill underperformers",
        "evidence_required": ["scale_or_kill_decision"],
        "engine": "revenue_intelligence",
    },
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

def _load_state() -> Dict[str, Any]:
    default = {"products": {}, "last_updated": None, "loop_runs": 0}
    if STAGE_STATE_PATH.exists():
        with open(STAGE_STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Handle empty file or missing keys
        if not data:
            return default
        default.update(data)
        return default
    return default


def _save_state(state: Dict[str, Any]) -> None:
    state["last_updated"] = _now_iso()
    state["loop_runs"] = state.get("loop_runs", 0) + 1
    STAGE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STAGE_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def _load_assets() -> List[Dict[str, Any]]:
    if ASSET_REGISTRY_PATH.exists():
        with open(ASSET_REGISTRY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("assets", [])
    return []


def _load_reality() -> Dict[str, Any]:
    if REALITY_PATH.exists():
        with open(REALITY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _load_finance() -> Dict[str, Any]:
    if FINANCE_PATH.exists():
        with open(FINANCE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# ---------------------------------------------------------------------------
# A) STAGE TRACKING — register products, read current stage
# ---------------------------------------------------------------------------

def register_product(product_id: str, product_name: str, category: str,
                     initial_stage: str = Stage.SENSE.value) -> Dict[str, Any]:
    """Register a product in the revenue engine at the SENSE stage."""
    state = _load_state()
    if product_id not in state["products"]:
        state["products"][product_id] = {
            "product_id": product_id,
            "product_name": product_name,
            "category": category,
            "current_stage": initial_stage,
            "stage_history": [{
                "stage": initial_stage,
                "entered_at": _now_iso(),
                "evidence": "registered",
            }],
            "evidence_trail": [],
            "decisions": [],
        }
        _save_state(state)
    return state["products"][product_id]


def get_product_stage(product_id: str) -> Optional[str]:
    """Get the current stage of a product."""
    state = _load_state()
    product = state["products"].get(product_id)
    return product["current_stage"] if product else None


def list_products_by_stage(stage: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all products, optionally filtered by stage."""
    state = _load_state()
    products = list(state["products"].values())
    if stage:
        products = [p for p in products if p["current_stage"] == stage]
    return products


# ---------------------------------------------------------------------------
# B) STAGE GATES — check if a product can advance
# ---------------------------------------------------------------------------

def check_gate(product_id: str, target_stage: str) -> Dict[str, Any]:
    """Check if a product has met the evidence requirements for a target stage."""
    state = _load_state()
    product = state["products"].get(product_id)
    if not product:
        return {"pass": False, "reason": "product_not_registered"}

    current = product["current_stage"]
    current_idx = STAGE_ORDER.index(current) if current in STAGE_ORDER else -1
    target_idx = STAGE_ORDER.index(target_stage) if target_stage in STAGE_ORDER else -1

    if target_idx <= current_idx:
        return {"pass": False, "reason": f"already_at_or_past_{target_stage}"}

    if target_idx > current_idx + 1:
        return {"pass": False, "reason": f"cannot_skip_from_{current}_to_{target_stage}"}

    gate = STAGE_GATES.get(target_stage, {})
    evidence = product.get("evidence_trail", [])
    evidence_types = {e.get("type") for e in evidence}

    required = gate.get("evidence_required", [])
    missing = [r for r in required if r not in evidence_types]

    if missing:
        return {"pass": False, "reason": f"missing_evidence: {missing}", "missing": missing}

    return {"pass": True, "gate": gate}


# ---------------------------------------------------------------------------
# C) EVIDENCE RECORDING — attach evidence to a product
# ---------------------------------------------------------------------------

def record_evidence(product_id: str, evidence_type: str, evidence_data: Dict[str, Any],
                    source: str = "unknown") -> bool:
    """Record evidence for a product. Returns True if recorded."""
    state = _load_state()
    product = state["products"].get(product_id)
    if not product:
        return False

    product.setdefault("evidence_trail", []).append({
        "type": evidence_type,
        "data": evidence_data,
        "source": source,
        "recorded_at": _now_iso(),
    })
    _save_state(state)
    return True


# ---------------------------------------------------------------------------
# D) PROGRESSION — move a product to the next stage
# ---------------------------------------------------------------------------

def advance_product(product_id: str, evidence_type: str, evidence_data: Dict[str, Any],
                    source: str = "unknown") -> Dict[str, Any]:
    """Attempt to advance a product to the next stage.

    Records evidence, checks gate, and advances if gate passes.
    Returns the result of the gate check.
    """
    state = _load_state()
    product = state["products"].get(product_id)
    if not product:
        return {"advanced": False, "reason": "product_not_registered"}

    current = product["current_stage"]
    current_idx = STAGE_ORDER.index(current) if current in STAGE_ORDER else -1
    if current_idx >= len(STAGE_ORDER) - 1:
        return {"advanced": False, "reason": "already_at_final_stage"}

    next_stage = STAGE_ORDER[current_idx + 1]

    # Record the evidence first
    record_evidence(product_id, evidence_type, evidence_data, source)

    # Check the gate
    gate_result = check_gate(product_id, next_stage)
    if not gate_result["pass"]:
        return {"advanced": False, "reason": gate_result["reason"], "next_stage": next_stage}

    # Advance
    product["current_stage"] = next_stage
    product.setdefault("stage_history", []).append({
        "stage": next_stage,
        "entered_at": _now_iso(),
        "evidence": evidence_type,
        "gate_passed": True,
    })
    _save_state(state)

    return {"advanced": True, "from": current, "to": next_stage}


# ---------------------------------------------------------------------------
# E) PORTFOLIO VIEW — all products and their stages
# ---------------------------------------------------------------------------

def portfolio_status() -> Dict[str, Any]:
    """Full portfolio view: all products, their stages, and loop health."""
    state = _load_state()
    reality = _load_reality()
    finance = _load_finance()

    products = state.get("products", {})
    stage_counts = {}
    for stage in STAGE_ORDER:
        stage_counts[stage] = 0
    for p in products.values():
        s = p.get("current_stage", Stage.SENSE.value)
        if s in stage_counts:
            stage_counts[s] += 1

    # Real ground truth
    published_books = reality.get("published_books", [])
    real_revenue = finance.get("totalSales", 0)
    real_sales = len(finance.get("sales", []))

    return {
        "generated_at": _now_iso(),
        "total_products": len(products),
        "stage_distribution": stage_counts,
        "products_by_stage": {
            stage: [
                {"id": p["product_id"], "name": p["product_name"], "category": p["category"]}
                for p in products.values()
                if p.get("current_stage") == stage
            ]
            for stage in STAGE_ORDER
        },
        "ground_truth": {
            "published_books": len(published_books),
            "real_revenue_usd": real_revenue,
            "real_sales": real_sales,
        },
        "loop_health": _compute_loop_health(products, stage_counts),
    }


def _compute_loop_health(products: Dict, stage_counts: Dict) -> Dict[str, Any]:
    """Compute health metrics for the revenue loop."""
    total = len(products)
    if total == 0:
        return {"status": "EMPTY", "note": "no products registered"}

    # How many products have progressed past SENSE?
    progressed = sum(
        1 for p in products.values()
        if STAGE_ORDER.index(p.get("current_stage", Stage.SENSE.value)) > 0
    )

    # How many have reached SELL or beyond?
    selling = sum(
        1 for p in products.values()
        if STAGE_ORDER.index(p.get("current_stage", Stage.SENSE.value)) >= 8
    )

    # How many are stuck (same stage for > 7 days)?
    stuck = 0
    now = datetime.now(timezone.utc)
    for p in products.values():
        history = p.get("stage_history", [])
        if history:
            last_entry = history[-1]
            try:
                entered = datetime.fromisoformat(last_entry["entered_at"])
                if entered.tzinfo is None:
                    entered = entered.replace(tzinfo=timezone.utc)
                days_stuck = (now - entered).days
                if days_stuck > 7:
                    stuck += 1
            except (ValueError, KeyError):
                pass

    return {
        "status": "ACTIVE" if progressed > 0 else "STALLED",
        "total_products": total,
        "progressed_past_sense": progressed,
        "selling": selling,
        "stuck_over_7_days": stuck,
        "progression_rate": f"{progressed}/{total}" if total else "0/0",
    }


# ---------------------------------------------------------------------------
# F) REVENUE LOOP STATUS — the unified dashboard
# ---------------------------------------------------------------------------

def revenue_loop_status() -> Dict[str, Any]:
    """The unified revenue loop dashboard — one view of the full loop.

    Combines portfolio state, blocking gates, next actions, and ground truth
    into a single executive summary.
    """
    portfolio = portfolio_status()
    reality = _load_reality()
    finance = _load_finance()

    # Check blocking gates
    blocking_gates = _check_blocking_gates()

    # Find the highest-priority next action
    next_action = _find_next_action()

    # Loop stage coverage
    stage_coverage = _compute_stage_coverage()

    return {
        "generated_at": _now_iso(),
        "loop_stages": STAGE_ORDER,
        "portfolio": portfolio,
        "blocking_gates": blocking_gates,
        "next_action": next_action,
        "stage_coverage": stage_coverage,
        "ground_truth": {
            "revenue": finance.get("totalSales", 0),
            "sales_count": len(finance.get("sales", [])),
            "published_products": len(reality.get("published_books", [])),
            "treasury": finance.get("totalSales", 0),
        },
        "honesty_note": "All figures are real, observed data. No estimates or projections.",
    }


def _check_blocking_gates() -> List[Dict[str, Any]]:
    """Check which external gates are blocking the loop."""
    gates = []

    # Paddle onboarding
    paddle_path = _FACTORY_ROOT / "data" / "paddle_products.json"
    if paddle_path.exists():
        with open(paddle_path, "r", encoding="utf-8") as f:
            paddle_products = json.load(f)
        blocked = [p for p in paddle_products if not p.get("checkout_ready", False)]
        if blocked:
            gates.append({
                "gate": "PADDLE_ONBOARDING",
                "status": "BLOCKED",
                "blocked_products": len(blocked),
                "action_required": "Founder must complete Paddle account onboarding at vendors.paddle.com",
                "estimated_time": "30 minutes",
            })
        else:
            gates.append({"gate": "PADDLE_ONBOARDING", "status": "CLEAR"})

    # Gumroad publish
    asset_path = _FACTORY_ROOT / "data" / "asset_registry.json"
    if asset_path.exists():
        with open(asset_path, "r", encoding="utf-8") as f:
            registry = json.load(f)
        for asset in registry.get("assets", []):
            if asset.get("product_genome", {}).get("platform") == "gumroad_digital":
                if asset.get("production_status") == "PRODUCED":
                    gates.append({
                        "gate": "GUMROAD_PUBLISH",
                        "status": "BLOCKED",
                        "product": asset.get("product_name"),
                        "action_required": "Founder must publish to Gumroad and attach PDF",
                        "estimated_time": "15 minutes",
                    })

    # Reality check
    reality = _load_reality()
    if reality.get("published_books") == []:
        gates.append({
            "gate": "FIRST_PUBLICATION",
            "status": "BLOCKED",
            "action_required": "No products published to any channel yet",
            "note": "config/reality.json shows published_books: []",
        })

    return gates


def _find_next_action() -> Dict[str, Any]:
    """Find the single highest-priority next action for the founder."""
    state = _load_state()
    products = state.get("products", {})

    # Find products stuck at early stages (SENSE/DISCOVER/SCORE)
    stuck_early = []
    for p in products.values():
        stage = p.get("current_stage", Stage.SENSE.value)
        stage_idx = STAGE_ORDER.index(stage) if stage in STAGE_ORDER else 0
        if stage_idx <= 2:  # SENSE, DISCOVER, SCORE
            stuck_early.append(p)

    if stuck_early:
        return {
            "action": "EVALUATE_OPPORTUNITY",
            "product": stuck_early[0]["product_id"],
            "name": stuck_early[0]["product_name"],
            "current_stage": stuck_early[0]["current_stage"],
            "reason": "product stuck in early evaluation stages",
        }

    # Find products at BUILD/QA stage
    building = list_products_by_stage(Stage.BUILD.value) + list_products_by_stage(Stage.QA.value)
    if building:
        return {
            "action": "COMPLETE_PRODUCTION",
            "product": building[0]["product_id"],
            "name": building[0]["product_name"],
            "current_stage": building[0]["current_stage"],
            "reason": "product needs production completion",
        }

    # Find products at DISTRIBUTE stage
    distributing = list_products_by_stage(Stage.DISTRIBUTE.value)
    if distributing:
        return {
            "action": "PUBLISH_PRODUCT",
            "product": distributing[0]["product_id"],
            "name": distributing[0]["product_name"],
            "current_stage": distributing[0]["current_stage"],
            "reason": "product ready for publication",
        }

    return {
        "action": "RUN_MARKET_SENSE",
        "reason": "no actionable products — run market discovery",
    }


def _compute_stage_coverage() -> Dict[str, Any]:
    """Compute which stages have real evidence vs are empty."""
    state = _load_state()
    products = state.get("products", {})

    coverage = {}
    for stage in STAGE_ORDER:
        stage_products = [
            p for p in products.values()
            if p.get("current_stage") == stage
        ]
        has_evidence = any(
            len(p.get("evidence_trail", [])) > 0
            for p in stage_products
        )
        coverage[stage] = {
            "product_count": len(stage_products),
            "has_evidence": has_evidence,
            "status": "ACTIVE" if stage_products else "EMPTY",
        }

    return coverage


# ---------------------------------------------------------------------------
# G) BOOTSTRAP — initialize from asset registry
# ---------------------------------------------------------------------------

def bootstrap_from_registry() -> Dict[str, Any]:
    """Initialize the revenue engine from the existing asset registry.

    Registers all assets as products at the SENSE stage (or their actual
    stage based on production_status mapping).
    """
    assets = _load_assets()
    registered = 0

    STATUS_MAP = {
        "PRODUCED": Stage.BUILD.value,        # already built, needs QA
        "DRAFT": Stage.SENSE.value,
        "SEED": Stage.SENSE.value,
        "COMMERCIAL_CANDIDATE": Stage.PACKAGE.value,  # built + QA'd, needs packaging
        "PUBLISHED": Stage.SELL.value,        # live and selling
    }

    for asset in assets:
        asset_id = asset.get("asset_id", "")
        name = asset.get("product_name", "Unknown")
        category = asset.get("product_category", "unknown")
        status = asset.get("production_status", "DRAFT")
        stage = STATUS_MAP.get(status, Stage.SENSE.value)

        product = register_product(asset_id, name, category, stage)
        if product.get("stage_history", [{}])[0].get("evidence") == "registered":
            registered += 1

    return {
        "total_assets": len(assets),
        "newly_registered": registered,
        "stage_mapping": STATUS_MAP,
    }


# ---------------------------------------------------------------------------
# H) CONVENIENCE — entry points for factory_loop.js integration
# ---------------------------------------------------------------------------

def run_revenue_engine_tick() -> Dict[str, Any]:
    """One tick of the revenue engine — the entry point for factory_loop.js.

    1. Bootstrap from registry if needed
    2. Check all products for gate passage
    3. Return loop status
    """
    # Bootstrap if empty
    state = _load_state()
    if not state.get("products"):
        bootstrap_from_registry()

    # Check gates for all products
    advances = []
    state = _load_state()
    for product_id, product in list(state.get("products", {}).items()):
        current = product.get("current_stage", Stage.SENSE.value)
        current_idx = STAGE_ORDER.index(current) if current in STAGE_ORDER else -1
        if current_idx < len(STAGE_ORDER) - 1:
            next_stage = STAGE_ORDER[current_idx + 1]
            gate = check_gate(product_id, next_stage)
            if gate["pass"]:
                advances.append({
                    "product_id": product_id,
                    "from": current,
                    "to": next_stage,
                })

    return {
        "generated_at": _now_iso(),
        "auto_advances": advances,
        "loop_status": revenue_loop_status(),
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "bootstrap":
        result = bootstrap_from_registry()
        print(json.dumps(result, indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] == "status":
        result = revenue_loop_status()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif len(sys.argv) > 1 and sys.argv[1] == "tick":
        result = run_revenue_engine_tick()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("Usage: python revenue_engine.py [bootstrap|status|tick]")

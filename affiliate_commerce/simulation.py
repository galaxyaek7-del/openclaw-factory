#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Affiliate Commerce — Simulation Mode reference implementation
(ADR-153, 2026-07-30).

Simulates the click -> conversion -> commission funnel by drawing from
the REAL click ledger (click_tracking.py, ADR-149) and the REAL product
catalog (products.py, ADR-149) -- only the money-moving step
(conversion + commission) is simulated, using a disclosed, labeled
assumption, never a fabricated real rate. Every event is tagged
simulation:true (simulation_mode.tag_simulated) and written to its own
separate ledger, data/affiliate_simulation_events.jsonl -- never mixed
into the real data/affiliate_clicks.jsonl or any real financial ledger
(finance_data.json, config/reality.json). Production code paths
(networks.py, click_tracking.py) are untouched by this module -- this
is purely additive, exercised only to validate the pipeline end-to-end
before ADR-150's real Phase 2 gate (real Associates tag configured +
a real confirmed conversion) actually clears.
"""

import json
import random
from datetime import datetime, timezone
from pathlib import Path

from simulation_mode import is_simulation_mode, tag_simulated
from affiliate_commerce import products as products_module
from affiliate_commerce import click_tracking

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SIM_LEDGER_PATH = _FACTORY_ROOT / "data" / "affiliate_simulation_events.jsonl"

# Disclosed assumptions, never presented as confirmed real numbers: no
# real Amazon Associates account exists yet (AMAZON_ASSOCIATE_TAG
# unset), so neither figure below can be confirmed against real data.
# ASSUMED_COMMISSION_RATE: Amazon's long-published baseline "Home"
# category rate from their public rate card. ASSUMED_CONVERSION_RATE: a
# commonly cited affiliate-industry baseline (~2%), not this factory's
# own measured rate -- it has zero real conversions to measure from.
ASSUMED_COMMISSION_RATE = 0.03
ASSUMED_CONVERSION_RATE = 0.02
COMMISSION_RATE_SOURCE = "ASSUMED -- Amazon's public baseline Home-category rate; not confirmed against a real Associates account (none exists yet)"
CONVERSION_RATE_SOURCE = "ASSUMED -- a commonly cited affiliate-industry baseline; this factory has zero real conversions to measure its own rate from"


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _append(record, ledger_path):
    path = Path(ledger_path) if ledger_path else DEFAULT_SIM_LEDGER_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def simulate_conversion(product_id, source_click_timestamp=None, sim_ledger_path=None):
    """One real, honestly-labeled simulated conversion event for a real
    product. Never called from any production code path -- guarded by
    is_simulation_mode() so it cannot silently run once
    AFFILIATE_MODE=production is set."""
    if not is_simulation_mode("affiliate_commerce"):
        raise RuntimeError("simulate_conversion() must not run outside Simulation Mode")

    product = products_module.get_product(product_id)
    if not product:
        return None

    simulated_price = product["price_usd"]
    simulated_commission = round(simulated_price * ASSUMED_COMMISSION_RATE, 2)

    record = tag_simulated({
        "product_id": product_id,
        "timestamp": _now_iso(),
        "source_click_timestamp": source_click_timestamp,
        "simulated_price_usd": simulated_price,
        "simulated_commission_usd": simulated_commission,
        "commission_rate_used": ASSUMED_COMMISSION_RATE,
        "commission_rate_source": COMMISSION_RATE_SOURCE,
    })
    _append(record, sim_ledger_path)
    return record


def run_simulation_cycle(rng=None, click_ledger_path=None, sim_ledger_path=None):
    """Walks the REAL click ledger and, for each real click, simulates a
    conversion with the disclosed ASSUMED_CONVERSION_RATE probability --
    ties the simulation to real recorded activity rather than generating
    conversions independent of it. Returns the list of newly-simulated
    conversion records (empty if there are no real clicks yet, which is
    the honest, current state)."""
    if not is_simulation_mode("affiliate_commerce"):
        raise RuntimeError("run_simulation_cycle() must not run outside Simulation Mode")

    rng = rng or random.Random()
    real_clicks = click_tracking.read_clicks(ledger_path=click_ledger_path)
    generated = []
    for click in real_clicks:
        if rng.random() < ASSUMED_CONVERSION_RATE:
            record = simulate_conversion(
                click.get("product_id"),
                source_click_timestamp=click.get("timestamp"),
                sim_ledger_path=sim_ledger_path,
            )
            if record:
                generated.append(record)
    return generated


def read_simulation_events(ledger_path=None):
    path = Path(ledger_path) if ledger_path else DEFAULT_SIM_LEDGER_PATH
    if not path.exists():
        return []
    events = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def simulation_funnel_report(click_ledger_path=None, sim_ledger_path=None):
    """Real, honest simulated-funnel numbers -- every field name and the
    report itself explicitly labeled SIMULATED. Never merged with or
    presented alongside real revenue/click totals as if comparable."""
    real_clicks = click_tracking.click_summary(ledger_path=click_ledger_path)["total_real_clicks"]
    sim_events = read_simulation_events(sim_ledger_path)
    total_simulated_commission = round(sum(e.get("simulated_commission_usd", 0) for e in sim_events), 2)
    return {
        "label": "SIMULATED -- not real revenue, not counted in any real financial ledger",
        "mode": "simulation" if is_simulation_mode("affiliate_commerce") else "production",
        "real_clicks_this_pipeline_has_recorded": real_clicks,
        "simulated_conversions": len(sim_events),
        "simulated_total_commission_usd": total_simulated_commission,
        "commission_rate_used": ASSUMED_COMMISSION_RATE,
        "commission_rate_source": COMMISSION_RATE_SOURCE,
        "conversion_rate_used": ASSUMED_CONVERSION_RATE,
        "conversion_rate_source": CONVERSION_RATE_SOURCE,
    }

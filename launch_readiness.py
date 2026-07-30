#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Launch Readiness Score (ADR-153, 2026-07-30).

Per the founder's Simulation-First Company Build directive: an 8-named-
dimension scorecard (Architecture, Automation, Testing, Compliance,
Monitoring, Documentation, Integration, Operational readiness) computed
PER DIVISION -- distinct from executive_score.py's own company-wide
score. Every dimension is a real, mechanical, disclosed-heuristic check
(file/module existence, real test-function counts, real text-marker
presence in server.js/CLAUDE.md/mission_control_executive_v1.html) --
never a semantic quality judgment, never a fabricated number. A
division with no real architecture yet (SaaS, AI Services, Licensing --
none exist as real code anywhere in this factory today) reports every
dimension as honestly not_architected, never invented to look more
built-out than it is.
"""

import re
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent

NOT_ARCHITECTED = "not_architected"


def _real(value, source, **extra):
    return {"value": value, "source": source, **extra}


def _not_architected(reason):
    return {"value": NOT_ARCHITECTED, "reason": reason}


def _paths_exist(paths):
    return [str(p) for p in paths if (_FACTORY_ROOT / p).exists()]


def _count_test_functions(test_paths):
    total = 0
    found_files = []
    for rel in test_paths:
        p = _FACTORY_ROOT / rel
        if not p.exists():
            continue
        found_files.append(rel)
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        total += len(re.findall(r"^\s*def test_", text, re.MULTILINE))
    return total, found_files


def _text_contains(rel_path, pattern):
    p = _FACTORY_ROOT / rel_path
    if not p.exists():
        return False
    try:
        text = p.read_text(encoding="utf-8")
    except OSError:
        return False
    return bool(re.search(pattern, text))


# Every division below is a real, disclosed set of mechanical checks --
# no division here invents evidence for something that doesn't exist.
_DIVISIONS = {
    "affiliate_commerce": {
        "name": "Affiliate Commerce",
        "architecture_paths": ["affiliate_commerce/__init__.py", "affiliate_commerce/networks.py",
                                "affiliate_commerce/products.py", "affiliate_commerce/click_tracking.py",
                                "affiliate_commerce/simulation.py"],
        "test_paths": ["tests/test_affiliate_commerce.py"],
        "compliance_check": ("customer_site/affiliate-standing-desks.html", r"As an Amazon Associate"),
        "documentation_check": ("CLAUDE.md", r"### Affiliate Commerce"),
        "integration_check": ("mission_control_executive_v1.html", r"service:'affiliate-commerce-status'"),
        "monitoring_check": ("server.js", r"name: 'affiliate-commerce-status'"),
    },
    "digital_products": {
        "name": "Digital Products Division (KDP)",
        "architecture_paths": ["book_generator.py", "distributor.py", "inspectors.py", "production_blueprint.py"],
        "test_paths": ["tests/test_book_generator_dispatch.py", "tests/test_distributor.py",
                        "tests/test_production_factory.py", "tests/test_production_gate.py"],
        "compliance_check": ("executive_quality_gate.py", r"def check_legal_compliance_risk"),
        "documentation_check": ("CLAUDE.md", r"### Key flow: book generation"),
        "integration_check": ("mission_control_executive_v1.html", r"service:'production-status'"),
        "monitoring_check": ("server.js", r"name: 'production-status'"),
    },
    # No real code, no real product concept anywhere in this factory
    # today for any of these three -- CLAUDE.md's own six-track vision
    # doesn't name any of them (ADR-152/153). Every dimension reports
    # honestly, never invented.
    "saas": {"name": "SaaS"},
    "ai_services": {"name": "AI Services"},
    "licensing": {"name": "Licensing"},
}


def _score_division(key, cfg):
    if "architecture_paths" not in cfg:
        reason = f"{cfg['name']} has no real module, product, or architecture anywhere in this factory today -- not part of CLAUDE.md's six-track vision. Nothing to score."
        dims = {dim: _not_architected(reason) for dim in
                ("architecture", "automation", "testing", "compliance", "monitoring",
                 "documentation", "integration", "operational_readiness")}
        return {"division": cfg["name"], "dimensions": dims}

    found_arch = _paths_exist(cfg["architecture_paths"])
    architecture = (_real(f"{len(found_arch)}/{len(cfg['architecture_paths'])}", "real file existence check",
                           files=found_arch)
                    if found_arch else _not_architected("none of the expected architecture files exist"))

    from executive_score import _automation as _company_automation
    automation = dict(_company_automation())
    automation["note"] = "company-wide signal (ai_capability.registry) -- not yet a per-division automation metric"

    test_count, found_test_files = _count_test_functions(cfg["test_paths"])
    testing = (_real(test_count, "real `def test_` count in the division's own test file(s) -- count only, not a live pass/fail run",
                      files=found_test_files)
               if found_test_files else _not_architected("no real test file exists for this division"))

    comp_file, comp_pattern = cfg["compliance_check"]
    compliance = (_real(True, f"real text-marker check in {comp_file}")
                  if _text_contains(comp_file, comp_pattern)
                  else _not_architected(f"expected compliance marker not found in {comp_file}"))

    doc_file, doc_pattern = cfg["documentation_check"]
    documentation = (_real(True, f"real section-header check in {doc_file}")
                      if _text_contains(doc_file, doc_pattern)
                      else _not_architected(f"expected documentation section not found in {doc_file}"))

    int_file, int_pattern = cfg["integration_check"]
    integration = (_real(True, f"real Mission Control panel check in {int_file}")
                    if _text_contains(int_file, int_pattern)
                    else _not_architected("no real Mission Control panel found for this division"))

    mon_file, mon_pattern = cfg["monitoring_check"]
    monitoring = (_real(True, f"real SERVICE_REGISTRY health-check entry in {mon_file}")
                  if _text_contains(mon_file, mon_pattern)
                  else _not_architected("no real registered service found for this division"))

    dims = {
        "architecture": architecture, "automation": automation, "testing": testing,
        "compliance": compliance, "monitoring": monitoring, "documentation": documentation,
        "integration": integration,
    }
    real_dims = [d for d in dims.values() if d.get("value") != NOT_ARCHITECTED]
    operational_readiness = (
        _real(f"{len(real_dims)}/7 dimensions have a real signal", "composite of the 7 dimensions above")
        if len(real_dims) == 7
        else _not_architected(f"only {len(real_dims)}/7 dimensions have a real signal -- not honestly composable yet")
    )
    dims["operational_readiness"] = operational_readiness
    return {"division": cfg["name"], "dimensions": dims}


def launch_readiness_score():
    return {"divisions": {key: _score_division(key, cfg) for key, cfg in _DIVISIONS.items()}}

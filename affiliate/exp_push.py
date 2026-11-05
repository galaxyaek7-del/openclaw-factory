#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP_001 distribution push: re-confirm, rank paths, prepare the top path
to the gate line, execute only if already-authorized. Read-only except own
records. Secrets never touch disk."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
PUSH_PATH = _FACTORY_ROOT / "data" / "aff_exp_001_distribution_push.json"


def rank_paths() -> list:
    """Feasibility-ranked distribution paths (evidence, not promises)."""
    return [
        {"path": "Medium article (draft ready, UTM-tagged fetmu link)",
         "feasible": False, "blocker": "FOUNDER_GATE (f386 pending: founder publishes)",
         "value": "HIGH (relevant audience + measurable via Medium stats + sales poll)",
         "prepared": True},
        {"path": "Systeme video description link",
         "feasible": False, "blocker": "video unpublished (own publication gate)",
         "value": "HIGH (exact audience match)", "prepared": False},
        {"path": "Owned customer_site cross-link",
         "feasible": False, "blocker": "deployment UNKNOWN + site edit is external change",
         "value": "MEDIUM (unmeasured audience)", "prepared": False},
        {"path": "X organic post",
         "feasible": False, "blocker": "402 credits depleted + approval",
         "value": "MEDIUM", "prepared": False},
        {"path": "Gumroad Discover (passive)",
         "feasible": True, "blocker": "none (already live)",
         "value": "LOW (wrong product: this is the affiliate link, not the GPSR listing; "
                  "no affiliate surface exists on Gumroad)",
         "prepared": False},
    ]


def push() -> dict:
    from systeme_affiliate import validate_config
    from affiliate import links as L
    from prospecting import medium_prep as mp
    cfg = validate_config()
    offer_valid = bool(cfg["affiliate_id_present"] and cfg["affiliate_id_format_valid"]
                       and not cfg["affiliate_id_is_placeholder"])
    links = [l for l in L.list_links() if l.get("campaign") == "aff_exp_001"]
    prep = mp.audit()
    paths = rank_paths()
    executable = [p for p in paths if p["feasible"]]
    top = paths[0]
    # execute only already-authorized: none of the feasible paths distribute
    # the affiliate link (Discover serves the GPSR listing, not this link)
    executed, blocked = [], [p for p in paths if not p["feasible"]]
    result = {"ran_at": datetime.now(timezone.utc).isoformat(),
              "offer_valid": offer_valid, "link_registered": len(links) == 1,
              "medium_prep": prep["verdict"],
              "executable_paths": len(executable),
              "ACTION_EXECUTED": executed,
              "ACTION_BLOCKED": [(p["path"], p["blocker"]) for p in blocked],
              "EXACT_BLOCKER": "no permitted live publishing path: Medium gated (f386), "
                               "video unpublished, X depleted, site deploy unknown",
              "experiment": "LINK_ACTIVE_DISTRIBUTION_PENDING",
              "spend": 0}
    PUSH_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return result

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Post-window learning extractor (V70, Tier-1 safe).

Commercial learning loop (s14) WITHOUT premature conclusions: while a
protected window is open the extractor returns HELD and drafts nothing.
After the close it reads the observation file + monitoring tail + sales
poll and returns a DRAFT learning record -- it never writes to
commercial_learning.jsonl / hypothesis_register / decision_memory itself
(writing is Tier-2: needs a review pass, then a founder-visible cycle).
Read-only in all paths.
"""
import json
import os
from datetime import datetime, timezone

_FACTORY_ROOT = os.path.dirname(os.path.abspath(__file__))


def extract_post_window_learning(experiment_id="EXP-SUB-001"):
    import experiment_governor
    status = experiment_governor.protected_window_status()
    rec = status.get(experiment_id.upper(), {})
    if rec.get("state") == "PROTECTED":
        return {"state": "HELD",
                "reason": "%s window open until %s -- interim verdicts barred" % (
                    experiment_id, rec.get("window_close")),
                "draft": None}
    # Post-close path: assemble observed facts only, no conclusions invented.
    facts = {"experiment_id": experiment_id}
    try:
        obs = json.load(open(os.path.join(
            _FACTORY_ROOT, "data", "nostr_sub_observation.json"), encoding="utf-8"))
        facts["responses"] = obs.get("responses")
        facts["classification"] = obs.get("classification")
    except Exception as e:
        facts["observation_error"] = str(e)[:150]
    tail = []
    try:
        for line in open(os.path.join(_FACTORY_ROOT, "data", "monitoring_log.jsonl"),
                         encoding="utf-8"):
            try:
                o = json.loads(line)
            except ValueError:
                continue
            if o.get("experiment_id") == experiment_id:
                tail.append(o)
        facts["monitoring_rows"] = len(tail)
        facts["last_nostr_responses"] = tail[-1].get("nostr_responses") if tail else "UNKNOWN"
    except Exception as e:
        facts["monitoring_error"] = str(e)[:150]
    try:
        fin = json.load(open(os.path.join(_FACTORY_ROOT, "finance_data.json"), encoding="utf-8"))
        facts["revenue_usd"] = fin.get("totalSales", 0)
    except Exception as e:
        facts["finance_error"] = str(e)[:150]
    return {
        "state": "DRAFT",
        "reason": "window closed; facts assembled, verdict needs review cycle",
        "draft": {
            "what_happened": facts,
            "what_did_not_happen": "UNDETERMINED (review cycle fills this)",
            "hypothesis_survived": "UNDETERMINED (review cycle fills this)",
            "never_repeat": "UNDETERMINED (review cycle fills this)",
            "next_test": "UNDETERMINED (review cycle fills this)",
            "at": datetime.now(timezone.utc).isoformat(),
        },
    }

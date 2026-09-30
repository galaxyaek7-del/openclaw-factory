#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Resource governor (GF-EVOLVE-01 §17). Pure, stateless classifier.

Before any operation, the caller states what changed since the last same
operation. SKIP when: value low, operation repeated without new input,
state unchanged, or a known blocker hasn't reached recheck time. This
module never executes anything -- it only advises SKIP/PROCEED with reason.
"""
SKIP = "SKIP"
PROCEED = "PROCEED"


def govern(expected_value="unknown", repeated_without_change=False,
           state_changed=True, blocker_recheck_due=True):
    """expected_value: high|low|unknown. All others booleans."""
    if str(expected_value).lower() == "low":
        return {"decision": SKIP, "reason": "low expected value"}
    if repeated_without_change:
        return {"decision": SKIP, "reason": "repeated without new input"}
    if not state_changed:
        return {"decision": SKIP, "reason": "state unchanged since last run"}
    if not blocker_recheck_due:
        return {"decision": SKIP, "reason": "known blocker, recheck not due"}
    return {"decision": PROCEED, "reason": "value/changed/due checks pass"}

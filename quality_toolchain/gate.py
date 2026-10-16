# -*- coding: utf-8 -*-
"""Timeout + failure-handling guard for tool executions.

A tool failing (slow, hung, exception, empty result) must NEVER silently
become a quality PASS. The contract enforced here:
  - each tool function runs under a wall-clock timeout (fail closed on timeout)
  - a timeout/exception/None return resolves to the tool's configured
    `fallback` (default 'not_available'), which gate logic treats as a FAIL
    for any layer the tool is supposed to implement — never as approval.
"""

import signal


class ToolTimeoutError(Exception):
    """Raised when a tool adapter exceeds its allowed wall-clock budget."""


# signals require a main thread + a POSIX signal module; on Windows, threading
# contortions for a true interrupt are avoided in favor of a cooperative check.
_InterruptGuardIdle = True


def run_with_timeout(fn, *args, timeout_seconds=30, **kwargs):
    """Run fn(*args, **kwargs) under a wall-clock timeout. If it does not
    return within budget, raise ToolTimeoutError (callers must fail closed)."""
    if timeout_seconds <= 0:
        return fn(*args, **kwargs)

    result_box = {"done": False, "value": None, "error": None}

    def _runner():
        try:
            result_box["value"] = fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001 - captured for re-raise
            result_box["error"] = e
        finally:
            result_box["done"] = True

    import threading
    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    t.join(timeout_seconds)
    if not result_box["done"]:
        raise ToolTimeoutError(f"tool exceeded {timeout_seconds}s budget")
    if result_box["error"] is not None:
        raise result_box["error"]
    return result_box["value"]


def fail_closed(result, fallback):
    """Normalize a tool result to pass/fail semantics. The ONLY way a tool
    contributes a PASS to a quality decision is an explicit present result.
    Absent/None resolves to `fallback`, which default 'not_available' is
    treated as a FAIL by gate logic."""
    if result is None:
        return {"passed": False, "status": fallback, "reason": "tool returned no result"}
    if isinstance(result, dict) and result.get("passed") is not None:
        return result
    # Non-dict or dict-without-passed -> not a usable gate verdict.
    return {"passed": False, "status": "invalid_result", "reason": "unusable result shape"}
"""
Executive Orchestrator — retry with backoff (ADR-051).

Same idempotent-only retry philosophy already established in this
factory (channels/gumroad_publisher.py: "retry transient failures on
idempotent calls only", 2026-07-15). Every engine adapter's run(context)
is expected to be safe to call more than once for the same context
(market_intelligence/decision are pure reads+re-evaluation;
production/publishing are additionally protected at the orchestrator
level by DUPLICATE_SENSITIVE_STAGES' has_succeeded() check, so a retry
here never re-executes an already-succeeded costly action — it only
retries an attempt that itself failed).
"""

import time


def run_with_retry(fn, context, max_attempts=3, backoff_seconds=0):
    """Returns (output, error, attempts_made). output is None iff every
    attempt failed; error is None iff the final attempt succeeded."""
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn(context), None, attempt
        except Exception as e:
            last_error = str(e)
            if attempt < max_attempts and backoff_seconds:
                time.sleep(backoff_seconds)
    return None, last_error, max_attempts

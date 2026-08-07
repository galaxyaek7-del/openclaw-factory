"""Galaxy Forge -- Anti-Bias Protection (new, ADR-206, Phase 16, 2026-08-08).

Answers Section 20 of the founder's "Adaptive Growth & Resource
Allocation Engine" directive: a real, callable, reusable check that
flags weak evidence before any recommendation built on it is trusted.

Checked first: this factory already has extensive per-module honest-
gap disclosure (truth_first.py's 9-term vocabulary, ADR-160) but no
single, named function that checks a *recommendation* for the specific
bias patterns this directive names. This is the genuinely new,
narrow piece -- a real, mechanical, disclosed-heuristic check (never a
semantic/AI judgment), reused by every Phase 16 report rather than
each one inventing its own ad-hoc caveat.
"""

from datetime import datetime, timezone

# Real, disclosed minimum sample size before a performance claim is
# trusted -- matches commercial_experiments.py's own real
# MIN_SAMPLE_SIZE_FOR_DECISION precedent (ADR-202), reused as the same
# company-wide threshold rather than inventing a second number.
_MIN_SAMPLE_SIZE = 30


def check_small_sample(n, context=""):
    """SMALL-SAMPLE + OVERFITTING: a real, mechanical minimum-n gate."""
    if n is None:
        return {"bias": "small_sample", "flagged": True, "reason": f"No real sample count available{' for ' + context if context else ''} -- cannot assess."}
    if n < _MIN_SAMPLE_SIZE:
        return {"bias": "small_sample", "flagged": True, "reason": f"n={n} is below the real, disclosed minimum ({_MIN_SAMPLE_SIZE}) for a trustworthy conclusion{' about ' + context if context else ''}."}
    return {"bias": "small_sample", "flagged": False, "reason": f"n={n} meets the real minimum sample size."}


def check_single_data_point(events, context=""):
    """SURVIVORSHIP + FALSE CAUSALITY: one anomalous result must never
    be read as a trend."""
    count = len(events) if events is not None else 0
    if count <= 1:
        return {"bias": "survivorship_or_false_causality", "flagged": True, "reason": f"Only {count} real data point(s) exist{' for ' + context if context else ''} -- a single result is an anecdote, not a trend. Never scale or conclude from one anomalous result."}
    return {"bias": "survivorship_or_false_causality", "flagged": False, "reason": f"{count} real data points exist -- more than a single anecdote."}


def check_vanity_metric(metric_name, is_revenue_linked):
    """VANITY METRICS + REVENUE ILLUSION: traffic/signups/engagement
    numbers are never a substitute for verified net revenue."""
    if not is_revenue_linked:
        return {"bias": "vanity_metric", "flagged": True, "reason": f"'{metric_name}' is not directly tied to verified net revenue -- real, but must never be reported as a commercial success signal on its own."}
    return {"bias": "vanity_metric", "flagged": False, "reason": f"'{metric_name}' is directly revenue-linked."}


def check_platform_concentration(platform_count, total_platforms_implemented):
    """PLATFORM BIAS: a conclusion drawn from one platform's data isn't
    evidence about the company's real multi-platform performance."""
    if total_platforms_implemented and platform_count < total_platforms_implemented:
        return {"bias": "platform_bias", "flagged": True, "reason": f"Real data exists for only {platform_count}/{total_platforms_implemented} implemented platforms -- a conclusion here reflects that one platform, not the company's real cross-platform performance."}
    return {"bias": "platform_bias", "flagged": False, "reason": "Real data spans every implemented platform."}


def check_model_bias(single_ai_provider, real_providers_available):
    """MODEL BIAS: a scoring/recommendation result produced by one AI
    provider is not independently corroborated."""
    if single_ai_provider and real_providers_available <= 1:
        return {"bias": "model_bias", "flagged": True, "reason": "Every real AI-generated score/recommendation in this factory comes from one provider (Groq) -- ai_capability/registry.py's own real DISCOVERY status for every other provider confirms no independent corroboration exists."}
    return {"bias": "model_bias", "flagged": False, "reason": "Real, independent multi-provider corroboration exists."}


def check_recency_bias(data_span_days, min_days=30):
    """RECENCY BIAS: a conclusion from a short, recent window may not
    generalize."""
    if data_span_days is None:
        return {"bias": "recency_bias", "flagged": True, "reason": "No real timestamped data span is available to assess -- cannot rule out recency bias."}
    if data_span_days < min_days:
        return {"bias": "recency_bias", "flagged": True, "reason": f"Real data spans only {data_span_days} real day(s), below the {min_days}-day minimum this factory uses elsewhere (commercial_readiness.py's own trend gate) for a trustworthy trend."}
    return {"bias": "recency_bias", "flagged": False, "reason": f"Real data spans {data_span_days} days, meeting the minimum window."}


def check_confirmation_bias(evidence_sources_count, min_sources=2):
    """CONFIRMATION BIAS: a claim resting on a single evidence source is
    weaker than one independently corroborated."""
    if evidence_sources_count < min_sources:
        return {"bias": "confirmation_bias", "flagged": True, "reason": f"Only {evidence_sources_count} real evidence source(s) cited -- below the {min_sources}-source minimum for independent corroboration."}
    return {"bias": "confirmation_bias", "flagged": False, "reason": f"{evidence_sources_count} independent real evidence sources cited."}


def assess_recommendation(n=None, events=None, metric_name=None, is_revenue_linked=True,
                           platform_count=None, total_platforms_implemented=None,
                           single_ai_provider=True, real_providers_available=1,
                           data_span_days=None, evidence_sources_count=1, context=""):
    """The one real aggregator -- runs every named check that has enough
    real input to run, skips (never fabricates an answer for) any check
    missing its real input. Returns the full list of checks plus a real,
    mechanical `weak_evidence` flag (true if ANY check flagged)."""
    now = datetime.now(timezone.utc)
    checks = []

    if n is not None:
        checks.append(check_small_sample(n, context))
    if events is not None:
        checks.append(check_single_data_point(events, context))
    if metric_name is not None:
        checks.append(check_vanity_metric(metric_name, is_revenue_linked))
    if platform_count is not None and total_platforms_implemented is not None:
        checks.append(check_platform_concentration(platform_count, total_platforms_implemented))
    if single_ai_provider is not None:
        checks.append(check_model_bias(single_ai_provider, real_providers_available))
    if data_span_days is not None:
        checks.append(check_recency_bias(data_span_days))
    if evidence_sources_count is not None:
        checks.append(check_confirmation_bias(evidence_sources_count))

    flagged = [c for c in checks if c["flagged"]]
    return {
        "generated_at": now.isoformat(),
        "context": context,
        "checks_run": checks,
        "weak_evidence": len(flagged) > 0,
        "flagged_biases": [c["bias"] for c in flagged],
        "note": f"{len(flagged)}/{len(checks)} real checks flagged weak evidence. Say so explicitly wherever this recommendation is used -- never silently proceed as if evidence were strong." if flagged else f"All {len(checks)} real checks passed -- no weak-evidence signal detected this call.",
    }

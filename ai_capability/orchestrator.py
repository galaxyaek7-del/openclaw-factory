"""
AI Multi-Model Orchestrator — OpenClaw Strategic Principle (2026-07-23):
"OpenClaw is not loyal to models. OpenClaw is loyal to results."

The real, working dispatcher this directive's "every production workflow
must support multi-model orchestration" asks for: automatically selects
the best real, measured-data-backed provider for a task (reusing
ai_capability.evaluator.recommend_for_task() directly — never a second,
competing selection algorithm), then dispatches to that provider's real
call implementation.

Honest architecture, not a fabricated one: this factory has exactly ONE
real, working provider integration today — Groq, via
book_generator.groq_chat(). Every other named provider (Claude, GPT,
Gemini, MiniMax, DeepSeek, Qwen, Kimi, open-source) is a real, tracked
candidate in ai_capability.registry.PROVIDER_CATALOG with honest
DISCOVERY-level metrics — and has NO real call implementation registered
in _REAL_PROVIDER_CALLERS below. evaluator.recommend_for_task() only
ever recommends a provider with real measured usage data, so it can
never actually select an unimplemented one today; generate() still
raises a clear, honest NotImplementedError rather than silently
substituting Groq and pretending multi-model orchestration happened, in
case a future evaluator change ever could.

"The company never depends on one vendor... if a better model appears
tomorrow, OpenClaw adopts it": adding a real second provider is a real,
three-step, non-breaking change — (1) a real credential in .env, (2) a
real call-implementation function here, (3) one new dict entry in
_REAL_PROVIDER_CALLERS. No call site that already routes through
generate() needs to change at all; the provider selection becomes
genuinely comparative the moment real usage data exists for more than
one provider (the exact mechanism ai_capability/evaluator.py's own
docstring already describes).

Proven end-to-end on one real, already-isolated production call site
(market_intelligence_engine.py's reformulate_pain_query(), 2026-07-23)
rather than the highest-risk core content-generation call sites, which
stay on their existing, already-proven direct groq_chat() calls for now.
"""

from ai_capability import evaluator


def _call_groq(system_prompt, user_prompt, **kwargs):
    from book_generator import groq_chat
    return groq_chat(system_prompt, user_prompt, **kwargs)


# The one real, registered provider implementation today.
_REAL_PROVIDER_CALLERS = {
    "groq": _call_groq,
}


def select_provider(task_type, cost_log_path=None):
    """Real, evidence-based provider selection — reuses
    evaluator.recommend_for_task() directly, never a second ranking
    algorithm. Falls back to 'groq' (this factory's one real,
    always-available provider) only when recommend_for_task() found no
    measured provider for this exact task_type at all — an honest
    default grounded in real current capability, not a guess."""
    recommendation = evaluator.recommend_for_task(task_type, cost_log_path=cost_log_path)
    provider = recommendation.get("recommendation") or "groq"
    return provider, recommendation


def generate(task_type, system_prompt, user_prompt, cost_log_path=None, **kwargs):
    """The real multi-model orchestration entrypoint. Picks a provider
    automatically (select_provider(), above), then dispatches to that
    provider's real implementation. Raises a clear, honest
    NotImplementedError for any selected provider with no real
    integration registered — never silently substitutes a different
    provider, never fabricates a response.

    Returns {"content": <the real generated text>, "provider": <the real
    provider that answered>, "selection": <the real selection
    reasoning>} — callers that only need the text read result["content"],
    same as book_generator.groq_chat()'s own plain-string return, just
    with the real routing decision now visible alongside it."""
    provider, recommendation = select_provider(task_type, cost_log_path=cost_log_path)
    caller = _REAL_PROVIDER_CALLERS.get(provider)
    if caller is None:
        raise NotImplementedError(
            f"لا تكامل حقيقي مُسجَّل بعد للمزوّد المختار '{provider}' — "
            f"أضِف بيانات اعتماد حقيقية ودالة استدعاء حقيقية في ai_capability/orchestrator.py أولاً"
        )
    content = caller(system_prompt, user_prompt, **kwargs)
    return {"content": content, "provider": provider, "selection": recommendation}

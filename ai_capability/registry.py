"""
AI Capability Registry -- Autonomous Digital Company v1, Track B2 (2026-07-19).

Same REAL/ESTIMATED/DISCOVERY discipline as config/capability_registry.json
(ADR-040), applied to AI *providers* instead of business capabilities.
Every metric below is either REAL (computed from this factory's own real,
logged usage) or DISCOVERY (not measurable yet -- no credential exists, or
a credential exists but the provider has never actually been called) --
never a fabricated ESTIMATED number standing in for a benchmark this
factory never ran.

Groq is the one provider ever actually called (data/ai_cost_log.jsonl,
ADR-041, extended 2026-07-19 with real per-call latency_ms) -- every metric
on it is computed live from that log, REAL where the underlying field
exists, DISCOVERY where it doesn't yet (e.g. log lines written before
latency_ms was tracked). Every other provider (Claude, GPT, Gemini, Grok,
DeepSeek, Qwen, Mistral, local models) is a real, named candidate with
DISCOVERY-level metrics only: the entry exists so a department can request
it (record_capability_request()), but no quality/speed/cost/availability/
context_size/reasoning_suitability/multimodal_support number is invented
until a real credential exists and is actually called.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
AI_COST_LOG_PATH = _FACTORY_ROOT / "data" / "ai_cost_log.jsonl"
REQUESTS_LOG_PATH = _FACTORY_ROOT / "data" / "ai_capability_requests.jsonl"

METRIC_NAMES = [
    "quality", "speed", "cost", "availability",
    "context_size", "reasoning_suitability", "multimodal_support",
]

# Real, named candidates the founder asked to be tracked. `task_types` are
# candidate categories only -- what a department might request this
# provider FOR -- never a measured suitability ranking.
PROVIDER_CATALOG = [
    {"provider": "groq", "display_name": "Groq (Llama 3.1 8B Instant)", "credential_env_var": "GROQ_KEY",
     "task_types": ["content_generation", "book_structure", "seo_copy", "marketing_copy", "support_copy"]},
    {"provider": "anthropic", "display_name": "Claude (Anthropic)", "credential_env_var": "ANTHROPIC_API_KEY",
     "task_types": ["reasoning", "long_context_analysis", "code_generation"]},
    {"provider": "openai", "display_name": "GPT (OpenAI)", "credential_env_var": "OPENAI_API_KEY",
     "task_types": ["general_purpose", "multimodal", "code_generation"]},
    {"provider": "google", "display_name": "Gemini (Google)", "credential_env_var": "GEMINI_API_KEY",
     "task_types": ["multimodal", "long_context_analysis"]},
    {"provider": "xai", "display_name": "Grok (xAI)", "credential_env_var": "XAI_API_KEY",
     "task_types": ["general_purpose", "reasoning"]},
    {"provider": "deepseek", "display_name": "DeepSeek", "credential_env_var": "DEEPSEEK_API_KEY",
     "task_types": ["reasoning", "code_generation"]},
    {"provider": "alibaba_qwen", "display_name": "Qwen (Alibaba)", "credential_env_var": "QWEN_API_KEY",
     "task_types": ["general_purpose", "multilingual"]},
    {"provider": "mistral", "display_name": "Mistral", "credential_env_var": "MISTRAL_API_KEY",
     "task_types": ["general_purpose", "code_generation"]},
    {"provider": "local", "display_name": "Local models (e.g. Ollama)", "credential_env_var": None,
     "task_types": ["offline_fallback", "no_api_cost"]},
]


def _read_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _groq_real_stats(entries):
    """Real, computed-from-logged-usage stats for Groq. Fields are honestly
    None when the underlying data isn't there yet (e.g. no latency_ms on
    log lines written before 2026-07-19)."""
    if not entries:
        return {"calls": 0, "avg_latency_ms": None, "avg_cost_usd_per_call": None, "total_cost_usd": None}

    costs = [e["cost_usd"] for e in entries if e.get("cost_usd") is not None]
    latencies = [e["latency_ms"] for e in entries if e.get("latency_ms") is not None]

    return {
        "calls": len(entries),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
        "avg_cost_usd_per_call": round(sum(costs) / len(costs), 6) if costs else None,
        "total_cost_usd": round(sum(costs), 6) if costs else None,
    }


def _metric(level, value=None, note=None):
    """One METRIC_NAMES entry, following config/capability_registry.json's
    REAL/ESTIMATED/DISCOVERY schema (ADR-040)."""
    m = {"level": level, "value": value}
    if note:
        m["note"] = note
    return m


def _groq_entry(catalog_entry, cost_log_entries):
    stats = _groq_real_stats(cost_log_entries)
    configured = bool(os.environ.get(catalog_entry["credential_env_var"]))

    speed = (_metric("REAL", stats["avg_latency_ms"], f"متوسط زمن استجابة حقيقي عبر {stats['calls']} استدعاء حقيقي مسجَّل.")
             if stats["avg_latency_ms"] is not None
             else _metric("DISCOVERY", note="لا يوجد استدعاءات تحمل latency_ms بعد (أُضيفت في 2026-07-19 -- الأسطر الأقدم لا تحمل هذا الحقل)."))
    cost = (_metric("REAL", stats["avg_cost_usd_per_call"], f"متوسط تكلفة حقيقي لكل استدعاء عبر {stats['calls']} استدعاء مسجَّل.")
            if stats["avg_cost_usd_per_call"] is not None
            else _metric("DISCOVERY", note="لا توجد بيانات تكلفة مسجَّلة بعد."))

    metrics = {
        "quality": _metric("DISCOVERY", note="لا يوجد ربط بين نتائج Dual Inspection والموديل الذي أنتج المحتوى بعد."),
        "speed": speed,
        "cost": cost,
        "availability": _metric("DISCOVERY", note="لا يوجد تتبّع لمعدّل الفشل/الجاهزية بعد -- تُسجَّل الاستدعاءات الناجحة فقط."),
        "context_size": _metric("DISCOVERY", note="مواصفة معلنة من المزوّد، لم تُتحقَّق مباشرة عبر استدعاء حقيقي -- لا تُسجَّل هنا لتفادي ذكر رقم لا يمكن لهذا المصنع تأكيده بنفسه."),
        "reasoning_suitability": _metric("DISCOVERY", note="لم يُجرَ أي اختبار مقارنة حقيقي للاستدلال بعد."),
        "multimodal_support": _metric("DISCOVERY", note="غير مُتحقَّق عبر استدعاء حقيقي -- هذا المصنع أرسل نصوصاً فقط حتى الآن."),
    }
    return {
        "provider": catalog_entry["provider"],
        "display_name": catalog_entry["display_name"],
        "configured": configured,
        "credential_env_var": catalog_entry["credential_env_var"],
        "task_types": catalog_entry["task_types"],
        "real_stats": stats,
        "metrics": metrics,
    }


def _candidate_entry(catalog_entry):
    credential_env_var = catalog_entry["credential_env_var"]
    configured = bool(credential_env_var and os.environ.get(credential_env_var))
    reason = ("لا يوجد بيانات اعتماد في .env" if not configured
               else "توجد بيانات اعتماد لكن لم يُستدعَ هذا المزوّد مطلقاً بعد")
    metrics = {name: _metric("DISCOVERY", note=f"لم يُقَس بعد -- {reason}.") for name in METRIC_NAMES}
    return {
        "provider": catalog_entry["provider"],
        "display_name": catalog_entry["display_name"],
        "configured": configured,
        "credential_env_var": credential_env_var,
        "task_types": catalog_entry["task_types"],
        "real_stats": None,
        "metrics": metrics,
    }


def list_providers(cost_log_path=None):
    """Every real, named provider candidate -- Groq (real, measured stats
    wherever the underlying log has the field) plus every other founder-
    requested provider (DISCOVERY-level metrics, never fabricated)."""
    entries = _read_jsonl(cost_log_path or AI_COST_LOG_PATH)
    out = []
    for c in PROVIDER_CATALOG:
        out.append(_groq_entry(c, entries) if c["provider"] == "groq" else _candidate_entry(c))
    return out


def render_markdown(providers):
    """EOS Phase 1 (2026-07-19): a compact markdown summary of
    list_providers()'s output, for the combined executive report --
    same 'real report + render_markdown()' shape every other report
    module in this factory already follows (validation_layer,
    executive_intelligence, strategic_intelligence)."""
    lines = ["| Provider | Configured | Calls | Avg Latency (ms) | Avg Cost/Call | Metrics Level |",
             "|---|---|---|---|---|---|"]
    for p in providers:
        stats = p.get("real_stats") or {}
        levels = sorted({m["level"] for m in p["metrics"].values()})
        lines.append(
            f"| {p['display_name']} | {'✅' if p['configured'] else '❌'} | "
            f"{stats.get('calls', '—')} | {stats.get('avg_latency_ms', '—')} | "
            f"{stats.get('avg_cost_usd_per_call', '—')} | {', '.join(levels)} |"
        )
    return "\n".join(lines) + "\n"


def record_capability_request(department, task_type, requested_provider, reason, path=None):
    """Append-only log of a department's real request for a different/
    better AI model (Autonomous Digital Company v1 §8) -- same discipline
    as decision_engine/store.py: one JSON object per line, never rewritten.
    A logged request, not an autonomous model switch -- too risky with zero
    comparative data across providers today (see evaluator.recommend_for_task())."""
    path = Path(path or REQUESTS_LOG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "department": department,
        "task_type": task_type,
        "requested_provider": requested_provider,
        "reason": reason,
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def read_capability_requests(path=None):
    return _read_jsonl(path or REQUESTS_LOG_PATH)

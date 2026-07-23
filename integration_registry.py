"""
Integration Registry (EOS Phase 2, 2026-07-19) — real, adapter-based
extension points for every vendor the founder named, generalizing
ai_capability/registry.py's catalog+report pattern (confirmed the best
fit over channels/registry.py's live-arm-only registry and
tool_intelligence/proposals.py's recommendation-log shape): a named-but-
uncredentialed vendor stays honestly unconfigured with zero fabricated
capability data, same discipline as 8/9 AI providers in ai_capability
today.

Explicit anti-duplication rule: a vendor already covered by an existing
registry is REFERENCED from it here, never re-derived independently --
  - AI providers -> ai_capability/registry.py's own PROVIDER_CATALOG
    (Claude, GPT, Gemini, DeepSeek, Groq, Qwen, Mistral, Kimi, Doubao,
    MiniMax). Perplexity is the one still new-to-any-registry provider
    (not yet in ai_capability's catalog), so it keeps its own real entry
    in NEW_VENDOR_CATALOG below. MiniMax moved OUT of NEW_VENDOR_CATALOG
    (2026-07-23, OpenClaw Strategic Principle) the moment it was added to
    ai_capability's own PROVIDER_CATALOG — the exact real duplicate this
    module's own anti-duplication rule exists to prevent, caught by
    tests/test_integration_registry.py's own duplicate-name test before
    it could ship.
  - Commerce channels with a real, live BaseArm -> channels/registry.py
    ::all_arms() (Paddle, Gumroad, Payhip, Etsy).

Everything else the founder named (n8n, GitHub, Google Workspace,
Notion, Linear, Slack, Discord, Telegram, Cloudflare, Docker, Supabase,
PostgreSQL, SQLite, vector databases, Shopify, KDP) is a real, named
catalog entry with `configured` computed from a real environment-
variable presence check only -- never a live "test connection" call (a
new live dependency this factory doesn't need yet, and "design
extension points... without forcing implementation" is the founder's
own framing). Tools with no credential concept at all (Docker, SQLite,
a local vector store) report `configured: None` -- honestly "not
applicable" rather than guessing. n8n and Telegram are honestly
`configured: True` -- both are real, live parts of this factory today
(this exact session deployed an n8n workflow change and sends real
Telegram messages).
"""

import os

NEW_VENDOR_CATALOG = [
    {"name": "n8n", "category": "automation", "credential_env_var": "N8N_TELEGRAM_WEBHOOK_URL"},
    {"name": "GitHub", "category": "developer_tools", "credential_env_var": "GITHUB_TOKEN"},
    {"name": "Google Workspace", "category": "productivity", "credential_env_var": "GOOGLE_WORKSPACE_CREDENTIALS"},
    {"name": "Notion", "category": "knowledge", "credential_env_var": "NOTION_API_KEY"},
    {"name": "Linear", "category": "project_management", "credential_env_var": "LINEAR_API_KEY"},
    {"name": "Slack", "category": "communication", "credential_env_var": "SLACK_BOT_TOKEN"},
    {"name": "Discord", "category": "communication", "credential_env_var": "DISCORD_BOT_TOKEN"},
    {"name": "Telegram", "category": "communication", "credential_env_var": "TELEGRAM_BOT_TOKEN"},
    {"name": "Cloudflare", "category": "infrastructure", "credential_env_var": "CLOUDFLARE_API_TOKEN"},
    {"name": "Docker", "category": "infrastructure", "credential_env_var": None},
    {"name": "Supabase", "category": "data", "credential_env_var": "SUPABASE_URL"},
    {"name": "PostgreSQL", "category": "data", "credential_env_var": "DATABASE_URL"},
    {"name": "SQLite", "category": "data", "credential_env_var": None},
    {"name": "Vector database", "category": "data", "credential_env_var": None},
    {"name": "Shopify", "category": "commerce", "credential_env_var": "SHOPIFY_ACCESS_TOKEN"},
    {"name": "KDP", "category": "commerce", "credential_env_var": None},
    {"name": "Perplexity", "category": "ai_provider", "credential_env_var": "PERPLEXITY_API_KEY"},
]


def _ai_provider_entries():
    from ai_capability import registry as ai_registry
    return [
        {
            "name": p["display_name"], "category": "ai_provider",
            "configured": p["configured"], "source": "ai_capability.registry",
        }
        for p in ai_registry.list_providers()
    ]


def _commerce_channel_entries():
    try:
        import distributor  # noqa: F401 -- self-registers every real, live arm
        from channels import registry as channel_registry
        return [
            {
                "name": arm.name, "category": "commerce_channel",
                "configured": arm.status().value == "ready", "source": "channels.registry",
            }
            for arm in channel_registry.all_arms()
        ]
    except Exception:
        return []


def _new_vendor_entries(catalog=None):
    entries = []
    for v in (catalog or NEW_VENDOR_CATALOG):
        env_var = v["credential_env_var"]
        configured = bool(os.environ.get(env_var)) if env_var else None
        entries.append({
            "name": v["name"], "category": v["category"],
            "configured": configured, "source": "integration_registry (new)",
        })
    return entries


def list_integrations():
    """Every real, named integration extension point across this
    factory -- AI providers and commerce channels referenced from their
    own real registries, every other founder-named vendor as an honest,
    env-var-based catalog entry. Never a live test-connection call."""
    return _ai_provider_entries() + _commerce_channel_entries() + _new_vendor_entries()

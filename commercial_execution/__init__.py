"""OpenClaw Factory — Commercial Execution Layer (Universal Production
Engine Roadmap Step 4, 2026-07-19): the unified Publish Pipeline that
turns a generated, QA'd product into a real (or dry-run) marketplace
listing, with one explicit, auditable record per publish.

Deliberately does NOT rebuild anything distributor.py/channels/ledger.py/
factory_state.py already do for real (fan-out publishing, the audit
ledger, the retry queue) — it wraps and unifies them, and adds the one
genuinely new integration: publishing now respects a product family's
manifest-declared supported_marketplaces (Product Definition Registry,
Step 3) instead of blindly fanning out to every registered arm.
"""

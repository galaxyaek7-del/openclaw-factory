"""OpenClaw Factory — Unified Recovery System (2026-07-18).

Ties together the pieces the approved architecture calls one system: safe
startup detection (startup_check.py), the offline retry queue
(retry_queue.py), and the backup snapshot helper (snapshot.py) — all
built on top of data/factory_state.json (factory_state.py/lib/
factory_state.js), the Phase A "what's happening right now" view.
"""

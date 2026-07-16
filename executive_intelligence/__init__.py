"""
OpenClaw Factory — Executive Intelligence Layer (ADR-052).

A read-only reporting layer on top of the already-built infrastructure
(orchestrator/, decision_engine/, market_intelligence_core/, channels/).
Adds zero new engines and zero new automation surfaces — every function
here only reads real, already-persisted data and computes a real,
traceable metric from it, or reports honestly that no real data exists
yet (never a fabricated KPI).

report.generate_report() is the single entrypoint most callers need —
see that module for the CEO-readable Markdown rendering designed to be
read in under 60 seconds.
"""

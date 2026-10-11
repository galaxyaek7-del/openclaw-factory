"""Cycle 77 section 2: mirrors scripts/run_python_group.py's network
block for ad-hoc `pytest` runs (the real CI entrypoint is unittest-based
and does not load this file at all -- see that script for the
authoritative enforcement point). Session-scoped and autouse so every
test, in every file, is covered with no per-file opt-in needed.
"""
import network_guard


def pytest_configure(config):
    network_guard.block()

"""Cycle 77 section 2 -- global network block for the Python test suite.

Wired into scripts/run_python_group.py (the real CI entrypoint for every
Python test group) and tests/conftest.py (for ad-hoc `pytest` runs, same
effect). Monkeypatches socket.socket.connect/connect_ex -- the one real
chokepoint every Python HTTP client (urllib, requests, http.client)
ultimately calls -- to raise instead of opening a real socket, for any
non-loopback destination.

Loopback connections (127.0.0.1 / ::1 / localhost) are NOT blocked: this
factory's test suite legitimately boots real local servers and talks to
them in-process -- that is not "the network" and blocking it would break
already-correct, already-offline tests for no real safety gain.

One documented, deliberate exception exists today:
tests/test_pioneer.py::TestRealHackerNewsIntegration makes one real,
free, keyless HN Firebase call by design (its own docstring: "a genuine
connectivity proof"). It opts out per-test via the allow_network()
context manager below, not via a global environment flag -- the
exception is visible at the call site, not hidden in CI config.
"""
import socket

_REAL_CONNECT = socket.socket.connect
_REAL_CONNECT_EX = socket.socket.connect_ex

_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost", "0.0.0.0", "::"}


def _is_blocked_destination(address):
    """Only a real (host, port)-style address can be a real network call --
    a bare string/path address is a unix socket, never "the network"."""
    if not (isinstance(address, tuple) and address):
        return False
    return address[0] not in _LOOPBACK_HOSTS


def _blocked_connect(self, address, *a, **kw):
    if _is_blocked_destination(address):
        raise RuntimeError(
            "Real network access blocked during tests (attempted connect to %r). "
            "If this test deliberately needs real network, wrap it in "
            "tests.network_guard.allow_network()." % (address,)
        )
    return _REAL_CONNECT(self, address, *a, **kw)


def _blocked_connect_ex(self, address, *a, **kw):
    if _is_blocked_destination(address):
        raise RuntimeError(
            "Real network access blocked during tests (attempted connect_ex to %r). "
            "If this test deliberately needs real network, wrap it in "
            "tests.network_guard.allow_network()." % (address,)
        )
    return _REAL_CONNECT_EX(self, address, *a, **kw)


def block():
    socket.socket.connect = _blocked_connect
    socket.socket.connect_ex = _blocked_connect_ex


def unblock():
    socket.socket.connect = _REAL_CONNECT
    socket.socket.connect_ex = _REAL_CONNECT_EX


class allow_network:
    """Context manager / decorator: temporarily restores real network
    access for a deliberately-real test. Always re-blocks on exit, even
    on exception, so one real-network test can never leave the guard
    disabled for every test that runs after it."""

    def __enter__(self):
        unblock()
        return self

    def __exit__(self, exc_type, exc, tb):
        block()
        return False

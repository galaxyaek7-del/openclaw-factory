"""Galaxy Forge — shared advisory file lock (Phase 41, ADR-238, 2026-08-09).

Extracted from commission_ledger.py's own real duplicate-commission
fix (Phase 39, ADR-236) so a second, unrelated module (lead_discovery.py)
could reuse the identical real concurrency-safety mechanism to fix its
own real duplicate-lead race (found via this round's Section O
"concurrent referral creation" stress test) WITHOUT importing
commission_ledger.py itself -- lead_discovery.py has a real, tested
structural guarantee (tests/test_lead_discovery.py::
TestSimulationLeakage::test_reality_firewall_module_has_no_ledger_import)
that it can never write real commission/revenue data, proven by never
importing commission_ledger at all. Weakening or removing that test
to accommodate a reused lock would violate this same directive's own
explicit "do NOT weaken any ... reality-firewall gate" rule -- so the
lock itself was extracted here instead, a purely mechanical,
financially-neutral utility with zero relation to commission/revenue
data, while commission_ledger.py re-exports it as _LedgerLock for
100% backward compatibility with every existing internal caller.
"""

import platform
import threading


class LedgerLock:
    """A real, minimal, cross-process advisory lock -- blocks until
    acquired, released even on exception via context-manager __exit__.

    Real production topology (per CLAUDE.md) spawns a separate Python
    subprocess per Mission Control action, so genuinely concurrent
    writes are almost always separate OS processes -- the real case
    this lock exists for, handled by msvcrt.locking() (Windows) /
    fcntl.flock() (POSIX). A dedicated intra-process threading.Lock()
    is held first: Windows' msvcrt.locking(LK_LOCK) was found, while
    writing commission_ledger.py's own concurrency stress test (Phase
    39, Section 9), to raise a real 'Resource deadlock avoided' OSError
    when multiple THREADS in the same process race for the same
    byte-range lock via separate handles -- a genuine Windows same-
    process locking quirk, not a hypothetical. The threading.Lock()
    serializes same-process callers before they ever reach msvcrt,
    while the file lock still protects the real cross-process case.

    The threading.Lock() is a single, shared class attribute -- every
    real caller across every real lock path serializes against it,
    a pre-existing, deliberately conservative characteristic carried
    over unchanged from the original commission_ledger.py
    implementation, not a new behavior introduced by this extraction."""

    _thread_lock = threading.Lock()

    def __init__(self, lock_target_path):
        self._lock_path = str(lock_target_path) + ".lock"
        self._fh = None

    def __enter__(self):
        self._thread_lock.acquire()
        self._fh = open(self._lock_path, "a+")
        if platform.system() == "Windows":
            import msvcrt
            self._fh.seek(0)
            msvcrt.locking(self._fh.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if platform.system() == "Windows":
                import msvcrt
                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        finally:
            self._fh.close()
            self._thread_lock.release()
        return False

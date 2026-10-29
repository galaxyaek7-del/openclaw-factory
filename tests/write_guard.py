"""Backlog B5 (2026-10-29) -- keep the Python test suite from writing the factory's
live files.

Observed: a full-suite run on 2026-10-29 appended test-fixture rows ("error": "e",
"source": "src", ...) to live ledgers -- evidence_ledger, design_*, distribution
events, recovery actions (backlog B27). Many modules default their paths to the
repository (inspectors.QUARANTINE_FILE, profit_oracle.GOLDEN_MD_FILE,
book_generator's generation log, ...) and a test that forgets one override writes
the real file.

What this does: while tests run, every write to a path inside the repository is
redirected to a per-process overlay directory (copy-on-write: appending to a live
ledger first copies it, then appends to the copy). Later reads, stats, renames and
deletes of that path inside the same process see the overlay, so a test still
observes what it wrote. Nothing inside the repository is created, changed or
deleted. Paths outside the repository (temp dirs) are untouched.

Same wiring as network_guard: scripts/run_python_group.py (the CI entrypoint) and
tests/conftest.py (ad-hoc pytest) call install(). redirected() lists the live
paths a run tried to write, which is the per-run evidence of which modules still
default to live files.

Not covered, and stated rather than hidden:
  * subprocesses a test starts (python scripts, node) write directly;
  * os.listdir and os.scandir (and so glob and Path.iterdir) merge the live
    directory with the overlay; os.walk's top-down recursion uses the same
    calls. Lower-level directory APIs (nt.listdir via file descriptors) do not;
  * C extensions that open files themselves (e.g. sqlite3) bypass it.
"""
import atexit
import builtins
import io
import os
import shutil
import tempfile
import threading

REPO_ROOT = os.path.normcase(os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_SKIP_PARTS = ("__pycache__", ".pytest_cache", ".git")

_real = {
    "open": builtins.open, "io_open": io.open, "os_open": os.open, "stat": os.stat,
    "replace": os.replace, "rename": os.rename, "remove": os.remove, "unlink": os.unlink,
    "mkdir": os.mkdir, "makedirs": os.makedirs, "exists": os.path.exists,
    "isfile": os.path.isfile, "isdir": os.path.isdir, "lexists": os.path.lexists,
    "rmdir": os.rmdir, "listdir": os.listdir, "scandir": os.scandir,
}
_lock = threading.RLock()
_state = {"installed": False, "overlay": None, "redirected": set(), "deleted": set(), "dirs": set()}

_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC


def _abs(path):
    if isinstance(path, int):
        return None
    try:
        p = os.fspath(path)
    except TypeError:
        return None
    if isinstance(p, bytes):
        p = os.fsdecode(p)
    return os.path.normcase(os.path.abspath(p))


def _is_live(ap):
    if ap is None or _state["overlay"] is None:
        return False
    if ap == REPO_ROOT or not ap.startswith(REPO_ROOT + os.sep):
        return False
    if ap.startswith(os.path.normcase(_state["overlay"])):
        return False
    rel = ap[len(REPO_ROOT) + 1:]
    return not any(part in _SKIP_PARTS for part in rel.split(os.sep))


def _overlay_path(ap):
    return os.path.join(_state["overlay"], ap[len(REPO_ROOT) + 1:])


def _has_overlay(ap):
    try:
        _real["stat"](_overlay_path(ap))
        return True
    except OSError:
        return False


def _prepare_write(ap, copy_existing):
    """Overlay path for a write to live path `ap` (copy-on-write when needed)."""
    ov = _overlay_path(ap)
    with _lock:
        _state["redirected"].add(ap[len(REPO_ROOT) + 1:])
        _real["makedirs"](os.path.dirname(ov), exist_ok=True)
        if copy_existing and ap not in _state["deleted"] and not _has_overlay(ap):
            try:
                if _real["isfile"](ap):
                    shutil.copyfile(ap, ov)
            except OSError:
                pass
        _state["deleted"].discard(ap)
    return ov


def _read_target(ap):
    """Path to read for live path `ap`: overlay copy, or the live file, or None if deleted."""
    if ap in _state["deleted"]:
        return None
    return _overlay_path(ap) if _has_overlay(ap) else ap


def _guarded_open(file, mode="r", *args, **kwargs):
    ap = _abs(file)
    if _is_live(ap):
        writes = any(c in mode for c in "wax+")
        if writes:
            ov = _prepare_write(ap, copy_existing=("a" in mode or "+" in mode))
            return _real["open"](ov, mode, *args, **kwargs)
        target = _read_target(ap)
        if target is None:
            raise FileNotFoundError(2, "No such file or directory (deleted in test overlay)", str(file))
        return _real["open"](target, mode, *args, **kwargs)
    return _real["open"](file, mode, *args, **kwargs)


def _guarded_os_open(path, flags, mode=0o777, *args, **kwargs):
    ap = _abs(path)
    if _is_live(ap):
        if flags & _WRITE_FLAGS:
            ov = _prepare_write(ap, copy_existing=not (flags & os.O_TRUNC))
            return _real["os_open"](ov, flags, mode, *args, **kwargs)
        target = _read_target(ap)
        if target is None:
            raise FileNotFoundError(2, "No such file or directory (deleted in test overlay)", str(path))
        return _real["os_open"](target, flags, mode, *args, **kwargs)
    return _real["os_open"](path, flags, mode, *args, **kwargs)


def _guarded_stat(path, *args, **kwargs):
    ap = _abs(path)
    if _is_live(ap):
        if ap in _state["deleted"]:
            raise FileNotFoundError(2, "No such file or directory (deleted in test overlay)", str(path))
        ov = _overlay_path(ap)
        if _has_overlay(ap):
            return _real["stat"](ov, *args, **kwargs)
    return _real["stat"](path, *args, **kwargs)


def _exists_like(name):
    real = _real[name]

    def check(path):
        ap = _abs(path)
        if _is_live(ap):
            if ap in _state["deleted"]:
                return False
            if _has_overlay(ap):
                return real(_overlay_path(ap))
        return real(path)
    return check


def _src_for_move(src):
    ap = _abs(src)
    if _is_live(ap):
        if _has_overlay(ap):
            return _overlay_path(ap), ap
        return None, ap          # a live source: copy it, never move the live file
    return src, None


def _guarded_move(kind):
    real = _real[kind]

    def move(src, dst, *args, **kwargs):
        dap = _abs(dst)
        s, s_live = _src_for_move(src)
        if not _is_live(dap) and s_live is None:
            return real(src, dst, *args, **kwargs)
        if _is_live(dap):
            target = _prepare_write(dap, copy_existing=False)
        else:
            target = dst
        if s is None:            # live source, copy instead of moving it
            shutil.copyfile(s_live, target)
        else:
            if kind == "rename" and os.name == "nt":
                _real["replace"](s, target)
            else:
                real(s, target, *args, **kwargs)
        if s_live is not None:
            with _lock:
                _state["deleted"].add(s_live)
                _state["redirected"].add(s_live[len(REPO_ROOT) + 1:])
    return move


def _guarded_remove(kind):
    real = _real[kind]

    def remove(path, *args, **kwargs):
        ap = _abs(path)
        if _is_live(ap):
            if ap in _state["deleted"]:
                raise FileNotFoundError(2, "No such file or directory (deleted in test overlay)", str(path))
            existed = _has_overlay(ap) or _real["exists"](ap)
            if not existed:
                raise FileNotFoundError(2, "No such file or directory", str(path))
            if _has_overlay(ap):
                real(_overlay_path(ap))
            with _lock:
                _state["deleted"].add(ap)
                _state["redirected"].add(ap[len(REPO_ROOT) + 1:])
            return None
        return real(path, *args, **kwargs)
    return remove


def _guarded_mkdir(path, *args, **kwargs):
    ap = _abs(path)
    if _is_live(ap) and not _real["exists"](ap):
        ov = _overlay_path(ap)
        if _real["exists"](ov):
            raise FileExistsError(17, "File exists", str(path))
        _real["makedirs"](os.path.dirname(ov), exist_ok=True)
        _state["dirs"].add(ap)
        return _real["mkdir"](ov, *args, **kwargs)
    return _real["mkdir"](path, *args, **kwargs)


def _guarded_makedirs(name, mode=0o777, exist_ok=False):
    ap = _abs(name)
    if _is_live(ap) and not _real["exists"](ap):
        _state["dirs"].add(ap)
        return _real["makedirs"](_overlay_path(ap), mode, exist_ok=exist_ok)
    return _real["makedirs"](name, mode, exist_ok=exist_ok)


def _dir_sources(path):
    """(live dir or None, overlay dir or None, deleted names) for a live path."""
    ap = _abs(path)
    if not _is_live(ap):
        return None
    live = ap if (ap not in _state["deleted"] and _real["isdir"](ap)) else None
    ov = _overlay_path(ap)
    ov = ov if _real["isdir"](ov) else None
    prefix = ap + os.sep
    deleted = {d[len(prefix):] for d in _state["deleted"] if d.startswith(prefix) and os.sep not in d[len(prefix):]}
    return live, ov, deleted


def _guarded_listdir(path="."):
    if isinstance(path, int) or isinstance(path, bytes):
        return _real["listdir"](path)
    src = _dir_sources(path)
    if src is None:
        return _real["listdir"](path)
    live, ov, deleted = src
    if live is None and ov is None:
        raise FileNotFoundError(2, "No such file or directory", str(path))
    names = set(_real["listdir"](live)) if live else set()
    if ov:
        names |= set(_real["listdir"](ov))
    return sorted(n for n in names if os.path.normcase(n) not in deleted)


class _Entry:
    """A DirEntry whose .path is under the directory the caller asked for, even
    when the file lives in the overlay (callers do Path.relative_to on it)."""

    def __init__(self, entry, requested):
        self._e = entry
        self.name = entry.name
        self.path = os.path.join(requested, entry.name)

    def is_file(self, *, follow_symlinks=True):
        return self._e.is_file(follow_symlinks=follow_symlinks)

    def is_dir(self, *, follow_symlinks=True):
        return self._e.is_dir(follow_symlinks=follow_symlinks)

    def is_symlink(self):
        return self._e.is_symlink()

    def stat(self, *, follow_symlinks=True):
        return self._e.stat(follow_symlinks=follow_symlinks)

    def inode(self):
        return self._e.inode()

    def is_junction(self):
        return getattr(self._e, "is_junction", lambda: False)()

    def __fspath__(self):
        return self.path

    def __repr__(self):
        return f"<DirEntry {self.name!r}>"


class _MergedScandir:
    """os.scandir over the live directory plus the overlay (overlay wins on a name)."""

    def __init__(self, live, ov, deleted, requested):
        entries = {}
        for d in (live, ov):
            if d:
                with _real["scandir"](d) as it:
                    for e in it:
                        if os.path.normcase(e.name) not in deleted:
                            entries[e.name] = _Entry(e, requested)
        self._it = iter(sorted(entries.values(), key=lambda e: e.name))

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._it)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def close(self):
        pass


def _guarded_scandir(path="."):
    if isinstance(path, int) or isinstance(path, bytes):
        return _real["scandir"](path)
    src = _dir_sources(path)
    if src is None:
        return _real["scandir"](path)
    live, ov, deleted = src
    if live is None and ov is None:
        raise FileNotFoundError(2, "No such file or directory", str(path))
    if ov is None and not deleted:
        return _real["scandir"](live)
    return _MergedScandir(live, ov, deleted, os.fspath(path))


def _guarded_rmdir(path, *args, **kwargs):
    ap = _abs(path)
    if _is_live(ap):
        ov = _overlay_path(ap)
        if _real["exists"](ov) and not _real["exists"](ap):
            return _real["rmdir"](ov, *args, **kwargs)
        return None              # never remove a live directory
    return _real["rmdir"](path, *args, **kwargs)


def install():
    """Idempotent. Returns the overlay directory."""
    with _lock:
        if _state["installed"]:
            return _state["overlay"]
        _state["overlay"] = os.path.realpath(tempfile.mkdtemp(prefix="gf_write_guard_"))
        builtins.open = _guarded_open
        io.open = _guarded_open
        os.open = _guarded_os_open
        os.stat = _guarded_stat
        os.replace = _guarded_move("replace")
        os.rename = _guarded_move("rename")
        os.remove = _guarded_remove("remove")
        os.unlink = _guarded_remove("unlink")
        os.mkdir = _guarded_mkdir
        os.makedirs = _guarded_makedirs
        os.rmdir = _guarded_rmdir
        os.listdir = _guarded_listdir
        os.scandir = _guarded_scandir
        os.path.exists = _exists_like("exists")
        os.path.isfile = _exists_like("isfile")
        os.path.isdir = _exists_like("isdir")
        os.path.lexists = _exists_like("lexists")
        _state["installed"] = True
        atexit.register(_report)
        return _state["overlay"]


def uninstall():
    with _lock:
        if not _state["installed"]:
            return
        builtins.open = _real["open"]
        io.open = _real["io_open"]
        os.open = _real["os_open"]
        os.stat = _real["stat"]
        os.replace = _real["replace"]
        os.rename = _real["rename"]
        os.remove = _real["remove"]
        os.unlink = _real["unlink"]
        os.mkdir = _real["mkdir"]
        os.makedirs = _real["makedirs"]
        os.rmdir = _real["rmdir"]
        os.listdir = _real["listdir"]
        os.scandir = _real["scandir"]
        os.path.exists = _real["exists"]
        os.path.isfile = _real["isfile"]
        os.path.isdir = _real["isdir"]
        os.path.lexists = _real["lexists"]
        _state["installed"] = False


def redirected():
    return sorted(_state["redirected"])


def _report():
    """At exit: list the live paths this process tried to write (stderr + a file
    named by GF_WRITE_GUARD_REPORT, if set). Then drop the overlay."""
    paths = redirected()
    out = os.environ.get("GF_WRITE_GUARD_REPORT")
    if out and paths:
        try:
            with _real["open"](out, "a", encoding="utf-8") as f:
                for p in paths:
                    f.write(p.replace(os.sep, "/") + "\n")
        except OSError:
            pass
    if paths:
        import sys
        sys.stderr.write(f"write_guard: {len(paths)} live path(s) redirected to the test overlay\n")
    shutil.rmtree(_state["overlay"] or "", ignore_errors=True)

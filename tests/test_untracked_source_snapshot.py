import subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import untracked_source_snapshot as u


def _repo(tmp_path):
    def g(*a):
        return subprocess.run(["git", *a], cwd=str(tmp_path), capture_output=True, text=True)
    g("init", "-q"); g("config", "user.email", "t@t"); g("config", "user.name", "t")
    (tmp_path / "tracked.txt").write_text("x"); g("add", "."); g("commit", "-q", "-m", "init")
    return g


def test_snapshot_saves_untracked_source_on_a_branch_and_leaves_main_alone(tmp_path):
    g = _repo(tmp_path)
    (tmp_path / "scripts").mkdir(); (tmp_path / "scripts" / "tool.py").write_text("print(1)")
    (tmp_path / "data").mkdir(); (tmp_path / "data" / "x.py").write_text("skipped dir")
    head = g("rev-parse", "HEAD").stdout
    r = u.snapshot(tmp_path, "local/test")
    assert r["action"] == "snapshot"
    assert g("show", "local/test:scripts/tool.py").stdout == "print(1)"
    assert g("cat-file", "-e", "local/test:data/x.py").returncode != 0
    assert g("rev-parse", "HEAD").stdout == head and (tmp_path / "scripts" / "tool.py").exists()
    assert u.snapshot(tmp_path, "local/test")["action"] == "none"  # unchanged tree -> no new commit
    (tmp_path / "scripts" / "tool.py").write_text("print(2)")
    assert u.snapshot(tmp_path, "local/test")["action"] == "snapshot"
    assert g("show", "local/test:scripts/tool.py").stdout == "print(2)"


def test_secret_blocks_the_snapshot(tmp_path):
    _repo(tmp_path)
    (tmp_path / "leak.py").write_text("K = 'gsk_" + "a" * 30 + "'")
    r = u.snapshot(tmp_path, "local/test")
    assert r["action"] == "blocked" and "leak.py" in r["detail"]

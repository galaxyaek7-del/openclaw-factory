"""Tree-mode publishing of the site publisher: site files go out, unrelated local commits never do (real git repos)."""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import auto_publish_site as aps  # noqa: E402


def g(cwd, *args):
    p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0, p.stderr
    return p.stdout


@pytest.fixture()
def repos(tmp_path, monkeypatch):
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    local = tmp_path / "local"
    subprocess.run(["git", "clone", "-q", str(origin), str(local)], check=True, capture_output=True)
    for k, v in (("user.name", "t"), ("user.email", "t@t"), ("commit.gpgsign", "false")):
        g(local, "config", k, v)
    g(local, "checkout", "-q", "-b", "main")
    (local / "customer_site").mkdir()
    (local / "customer_site" / "a.html").write_text("<p>a v1</p>")
    (local / "sitemap.xml").write_text("<urlset></urlset>")
    g(local, "add", "-A"); g(local, "commit", "-q", "-m", "init"); g(local, "push", "-q", "origin", "main")
    monkeypatch.setattr(aps, "ROOT", local)
    monkeypatch.setattr(aps, "STATE", tmp_path / "state.json")
    monkeypatch.setattr(aps, "run_gate", lambda d: (True, "gate stub passed"))
    return origin, local


def commit(local, files, msg):
    for path, text in files.items():
        p = local / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    g(local, "add", "-A"); g(local, "commit", "-q", "-m", msg)


def origin_files(origin):
    return set(g(origin, "ls-tree", "-r", "--name-only", "main").split())


def test_site_files_are_published_and_code_commits_stay_local(repos):
    origin, local = repos
    commit(local, {"customer_site/a.html": "<p>a v2</p>", "customer_site/b.html": "<p>new</p>"}, "site pages")
    commit(local, {"scripts/tool.py": "print(1)"}, "code, must stay local")
    r = aps.run()
    assert r["action"] == "pushed" and "tree mode" in r["detail"], r
    files = origin_files(origin)
    assert "customer_site/b.html" in files and "scripts/tool.py" not in files
    assert g(origin, "show", "main:customer_site/a.html") == "<p>a v2</p>"
    assert aps.run()["action"] == "none"  # nothing left to publish, no repeated push


def test_a_product_file_in_the_site_is_held(repos):
    origin, local = repos
    commit(local, {"customer_site/downloads/kit.pdf": "x"}, "pdf in site")
    commit(local, {"scripts/tool.py": "print(1)"}, "code")
    r = aps.run()
    assert r["action"] == "none" and "product-like" in r["detail"]
    assert "customer_site/downloads/kit.pdf" not in origin_files(origin)


def test_a_file_origin_changed_too_is_never_overwritten(repos, tmp_path):
    origin, local = repos
    other = tmp_path / "other"
    subprocess.run(["git", "clone", "-q", str(origin), str(other)], check=True, capture_output=True)
    for k, v in (("user.name", "t"), ("user.email", "t@t")):
        g(other, "config", k, v)
    commit(other, {"customer_site/a.html": "<p>a from elsewhere</p>"}, "remote edit"); g(other, "push", "-q", "origin", "main")
    commit(local, {"customer_site/a.html": "<p>a local edit</p>"}, "local site edit")
    commit(local, {"scripts/tool.py": "print(1)"}, "code")
    r = aps.run()
    assert r["action"] in ("blocked", "none")
    assert g(origin, "show", "main:customer_site/a.html") == "<p>a from elsewhere</p>"


def test_a_failing_gate_pushes_nothing(repos, monkeypatch):
    origin, local = repos
    monkeypatch.setattr(aps, "run_gate", lambda d: (False, "secret scan failed"))
    commit(local, {"customer_site/b.html": "<p>new</p>"}, "site")
    commit(local, {"scripts/tool.py": "print(1)"}, "code")
    r = aps.run()
    assert r["action"] == "blocked" and "customer_site/b.html" not in origin_files(origin)


def test_a_file_we_published_earlier_in_tree_mode_can_be_updated_again(repos):
    """Tree mode leaves origin-only commits, so the merge base is old: a second edit of a file we ourselves published must go out,
    not be blocked as a foreign change (it stalled automatic publishing three times on 2026-11-06)."""
    origin, local = repos
    commit(local, {"customer_site/a.html": "<p>a v2</p>"}, "site v2")
    commit(local, {"scripts/tool.py": "print(1)"}, "code, stays local")
    assert aps.run()["action"] == "pushed"
    commit(local, {"customer_site/a.html": "<p>a v3</p>"}, "site v3")
    commit(local, {"scripts/tool2.py": "print(2)"}, "more code")
    r = aps.run()
    assert r["action"] == "pushed", r
    assert g(origin, "show", "main:customer_site/a.html") == "<p>a v3</p>"

"""tests/write_guard.py (backlog B5): writes inside the repository go to an overlay.

Each case runs in a fresh Python process against a fake repository in a temp
directory, so it neither depends on nor disturbs the guard the suite itself runs
under.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent

PRELUDE = textwrap.dedent("""
    import json, os, sys, pathlib, tempfile
    sys.path.insert(0, {tests!r})
    import write_guard as wg
    wg.REPO_ROOT = os.path.normcase(os.path.realpath({repo!r}))
    wg.install()
    R = {repo!r}
    out = {{}}
""")


def run_case(repo, body):
    code = PRELUDE.format(tests=str(TESTS), repo=repo) + textwrap.dedent(body) + \
        "\nprint(json.dumps(out))\n"
    env = dict(os.environ)
    env.pop("GF_WRITE_GUARD_REPORT", None)
    # Isolate from the guard this test suite itself runs under.
    for k in ("GF_WRITE_GUARD_OVERLAY", "GF_WRITE_GUARD_ROOT"):
        env.pop(k, None)
    site = str(TESTS / "_guard_site")
    env["PYTHONPATH"] = os.pathsep.join(p for p in env.get("PYTHONPATH", "").split(os.pathsep) if p and p != site)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=60)
    if r.returncode != 0:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout.strip().splitlines()[-1]), r.stderr


class WriteGuard(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.repo, "data"))
        self.ledger = os.path.join(self.repo, "data", "ledger.jsonl")
        with open(self.ledger, "w", encoding="utf-8") as f:
            f.write('{"row": "live"}\n')

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def live(self):
        with open(self.ledger, encoding="utf-8") as f:
            return f.read()

    def test_append_is_copy_on_write_and_visible_to_the_test(self):
        out, err = run_case(self.repo, """
            p = os.path.join(R, "data", "ledger.jsonl")
            with open(p, "a", encoding="utf-8") as f:
                f.write('{"row": "test"}\\n')
            out["seen"] = open(p, encoding="utf-8").read()
            out["redirected"] = wg.redirected()
        """)
        self.assertEqual('{"row": "live"}\n{"row": "test"}\n', out["seen"])
        self.assertEqual('{"row": "live"}\n', self.live())
        self.assertEqual(1, len(out["redirected"]))
        self.assertIn("redirected to the test overlay", err)

    def test_new_file_exists_only_for_the_test(self):
        out, _ = run_case(self.repo, """
            p = pathlib.Path(R) / "data" / "new.json"
            p.write_text("{}", encoding="utf-8")
            out["exists"] = [p.exists(), os.path.exists(p), os.path.isfile(p)]
            out["size"] = os.stat(p).st_size
        """)
        self.assertEqual([True, True, True], out["exists"])
        self.assertEqual(2, out["size"])
        self.assertFalse(os.path.exists(os.path.join(self.repo, "data", "new.json")))

    def test_atomic_replace_pattern(self):
        out, _ = run_case(self.repo, """
            p = os.path.join(R, "data", "state.json")
            tmp = p + ".tmp"
            with open(tmp, "w") as f:
                f.write('{"v": 2}')
            os.replace(tmp, p)
            out["v"] = json.load(open(p))["v"]
            out["tmp_left"] = os.path.exists(tmp)
        """)
        self.assertEqual(2, out["v"])
        self.assertFalse(out["tmp_left"])
        self.assertEqual(["ledger.jsonl"], os.listdir(os.path.join(self.repo, "data")))

    def test_mkstemp_in_repo_then_replace(self):
        out, _ = run_case(self.repo, """
            d = os.path.join(R, "data")
            fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
            os.write(fd, b"x"); os.close(fd)
            os.replace(tmp, os.path.join(d, "ledger.jsonl"))
            out["seen"] = open(os.path.join(d, "ledger.jsonl")).read()
        """)
        self.assertEqual("x", out["seen"])
        self.assertEqual('{"row": "live"}\n', self.live())
        self.assertEqual(["ledger.jsonl"], os.listdir(os.path.join(self.repo, "data")))

    def test_delete_is_virtual(self):
        out, _ = run_case(self.repo, """
            p = os.path.join(R, "data", "ledger.jsonl")
            os.remove(p)
            out["exists"] = os.path.exists(p)
            try:
                open(p).read(); out["read"] = "ok"
            except FileNotFoundError:
                out["read"] = "missing"
            with open(p, "w") as f:
                f.write("again")
            out["after"] = open(p).read()
        """)
        self.assertEqual([False, "missing", "again"], [out["exists"], out["read"], out["after"]])
        self.assertEqual('{"row": "live"}\n', self.live())

    def test_rename_of_live_file_copies(self):
        out, _ = run_case(self.repo, """
            p = os.path.join(R, "data", "ledger.jsonl")
            q = os.path.join(R, "data", "moved.jsonl")
            os.rename(p, q)
            out["moved"] = open(q).read()
            out["src_exists"] = os.path.exists(p)
        """)
        self.assertEqual('{"row": "live"}\n', out["moved"])
        self.assertFalse(out["src_exists"])
        self.assertEqual('{"row": "live"}\n', self.live())
        self.assertFalse(os.path.exists(os.path.join(self.repo, "data", "moved.jsonl")))

    def test_new_directories_stay_virtual(self):
        out, _ = run_case(self.repo, """
            d = os.path.join(R, "reports", "x")
            os.makedirs(d, exist_ok=True)
            open(os.path.join(d, "r.md"), "w").write("hi")
            out["isdir"] = os.path.isdir(d)
            out["read"] = open(os.path.join(d, "r.md")).read()
        """)
        self.assertEqual([True, "hi"], [out["isdir"], out["read"]])
        self.assertFalse(os.path.exists(os.path.join(self.repo, "reports")))

    def test_listing_merges_live_and_overlay(self):
        # Regression, 2026-10-29: a module made niche_reports/ (overlay only) and
        # then listed it; listdir/scandir raised FileNotFoundError.
        out, _ = run_case(self.repo, """
            import glob
            d = os.path.join(R, "niche_reports")
            os.makedirs(d, exist_ok=True)
            open(os.path.join(d, "a.md"), "w").write("x")
            out["listdir"] = os.listdir(d)
            with os.scandir(d) as it:
                out["scandir"] = sorted(e.name for e in it)
            out["glob"] = [os.path.basename(p) for p in glob.glob(os.path.join(d, "*.md"))]
            out["iterdir"] = [p.name for p in pathlib.Path(d).iterdir()]
            out["relative"] = [str(p.relative_to(pathlib.Path(R))) for p in pathlib.Path(d).iterdir()]
            with os.scandir(d) as it:
                out["entry_parent"] = [os.path.dirname(e.path) == d for e in it]
            data = os.path.join(R, "data")
            open(os.path.join(data, "new.jsonl"), "w").write("{}")
            os.remove(os.path.join(data, "ledger.jsonl"))
            out["data"] = os.listdir(data)
            try:
                os.listdir(os.path.join(R, "missing"))
                out["missing"] = "listed"
            except FileNotFoundError:
                out["missing"] = "raised"
        """)
        for k in ("listdir", "scandir", "glob", "iterdir"):
            self.assertEqual(["a.md"], out[k], k)
        self.assertEqual([os.path.join("niche_reports", "a.md")], out["relative"])
        self.assertEqual([True], out["entry_parent"])
        self.assertEqual(["new.jsonl"], out["data"])
        self.assertEqual("raised", out["missing"])
        self.assertFalse(os.path.exists(os.path.join(self.repo, "niche_reports")))
        self.assertEqual(["ledger.jsonl"], os.listdir(os.path.join(self.repo, "data")))

    def test_python_subprocess_shares_the_overlay(self):
        # 2026-10-29: tests that start python subprocesses still wrote live files
        # (generation log, QUARANTINE.md). Children now inherit the guard.
        out, _ = run_case(self.repo, """
            import subprocess
            p = os.path.join(R, "data", "ledger.jsonl")
            child = "open(r'%s', 'a', encoding='utf-8').write('child-row')" % p
            subprocess.run([sys.executable, "-c", child], check=True)
            out["seen"] = open(p, encoding="utf-8").read()
        """)
        self.assertIn("child-row", out["seen"])
        self.assertNotIn("child-row", self.live())

    def test_paths_outside_repo_are_untouched(self):
        outside = tempfile.mkdtemp()
        try:
            out, _ = run_case(self.repo, f"""
                p = os.path.join({outside!r}, "f.txt")
                open(p, "w").write("real")
                out["r"] = wg.redirected()
            """)
            self.assertEqual([], out["r"])
            self.assertEqual("real", open(os.path.join(outside, "f.txt")).read())
        finally:
            shutil.rmtree(outside, ignore_errors=True)

    def test_reads_of_untouched_live_files_still_work(self):
        out, _ = run_case(self.repo, """
            out["live"] = open(os.path.join(R, "data", "ledger.jsonl")).read()
            out["r"] = wg.redirected()
        """)
        self.assertEqual('{"row": "live"}\n', out["live"])
        self.assertEqual([], out["r"])

    def test_rmtree_of_a_temp_dir_works_with_cwd_in_the_repo(self):
        # On Linux shutil.rmtree deletes by name relative to an open directory
        # (unlink(name, dir_fd=fd)). With the working directory at the repo
        # root, those bare names must not be mistaken for live repo paths:
        # CI failed with "Directory not empty" on every temp-dir cleanup.
        outside = tempfile.mkdtemp()
        os.makedirs(os.path.join(outside, "sub"))
        for name in ("ledger.jsonl", os.path.join("sub", "x.json")):
            with open(os.path.join(outside, name), "w") as f:
                f.write("tmp")
        out, _ = run_case(self.repo, f"""
            import shutil
            os.chdir(R)
            shutil.rmtree({outside!r})
            out["gone"] = not os.path.exists({outside!r})
            out["r"] = wg.redirected()
        """)
        shutil.rmtree(outside, ignore_errors=True)
        self.assertTrue(out["gone"])
        self.assertEqual([], out["r"])
        self.assertEqual('{"row": "live"}\n', self.live())

    def test_new_dir_is_listable_with_posix_style_path_checks(self):
        # On POSIX os.path.isdir/exists are genericpath functions that call
        # os.stat at call time, i.e. the guarded stat. The guard must not use
        # them as its "real" checks: it then believed a directory that exists
        # only in the overlay was live, and os.listdir raised FileNotFoundError
        # (CI, Linux: niche_reports, book_generator.py / profit_oracle.py).
        code = textwrap.dedent(f"""
            import genericpath, json, os, sys
            for name in ("isdir", "isfile", "exists"):
                setattr(os.path, name, getattr(genericpath, name))
            sys.path.insert(0, {str(TESTS)!r})
            import write_guard as wg
            wg.REPO_ROOT = os.path.normcase(os.path.realpath({self.repo!r}))
            wg.install()
            d = os.path.join({self.repo!r}, "niche_reports")
            os.makedirs(d, exist_ok=True)
            open(os.path.join(d, "r.json"), "w").write("{{}}")
            out = {{"isdir": os.path.isdir(d), "list": os.listdir(d),
                    "live_exists": os.path.exists(d) and True}}
            print(json.dumps(out))
        """)
        env = dict(os.environ)
        for k in ("GF_WRITE_GUARD_OVERLAY", "GF_WRITE_GUARD_ROOT", "GF_WRITE_GUARD_REPORT"):
            env.pop(k, None)
        site = str(TESTS / "_guard_site")
        env["PYTHONPATH"] = os.pathsep.join(p for p in env.get("PYTHONPATH", "").split(os.pathsep) if p and p != site)
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertTrue(out["isdir"])
        self.assertEqual(out["list"], ["r.json"])
        self.assertFalse(os.path.exists(os.path.join(self.repo, "niche_reports")))

    def test_rmtree_of_a_live_dir_stays_virtual(self):
        out, _ = run_case(self.repo, """
            import shutil
            shutil.rmtree(os.path.join(R, "data"), ignore_errors=True)
            out["visible"] = os.path.exists(os.path.join(R, "data", "ledger.jsonl"))
        """)
        self.assertFalse(out["visible"])
        self.assertEqual('{"row": "live"}\n', self.live())


if __name__ == "__main__":
    unittest.main()

"""scripts/tool_pages_daily.py: once-a-day gate around the tool-page generator.
The real generator, state file and site are never touched: temp state and an
injected runner only."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import tool_pages_daily as tpd  # noqa: E402


class DailyGate(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.state = Path(self.dir.name) / "state.json"

    def tearDown(self):
        self.dir.cleanup()

    def test_new_pages_report_updated_and_set_the_gate(self):
        out = tpd.run_once(today="2026-10-29", state_path=self.state,
                           runner=lambda: {"pages": 30, "sitemap_added": 3, "skipped_unpublished": []})
        self.assertEqual(out["action"], "updated")
        self.assertIn("3 new in sitemap", out["detail"])
        again = tpd.run_once(today="2026-10-29", state_path=self.state, runner=lambda: self.fail("ran twice"))
        self.assertEqual(again["action"], "none")

    def test_nothing_new_is_none(self):
        out = tpd.run_once(today="2026-10-30", state_path=self.state,
                           runner=lambda: {"pages": 30, "sitemap_added": 0, "skipped_unpublished": ["B16-008"]})
        self.assertEqual(out["action"], "none")
        self.assertIn("1 unpublished skipped", out["detail"])

    def test_missing_generator_is_reported_not_failed(self):
        out = tpd.run_once(today="2026-10-29", state_path=self.state, generator=Path(self.dir.name) / "absent.py")
        self.assertEqual(out["action"], "none")
        self.assertIn("generator not present", out["detail"])
        self.assertFalse(self.state.exists())

    def test_generator_error_is_reported_and_retried_next_tick(self):
        def boom():
            raise RuntimeError("bad page")
        out = tpd.run_once(today="2026-10-29", state_path=self.state, runner=boom)
        self.assertEqual(out["action"], "failed")
        self.assertFalse(self.state.exists())

    def test_without_once_flag_it_does_nothing(self):
        self.assertEqual(tpd.main([]), 2)


if __name__ == "__main__":
    unittest.main()


def _repo(tmp_path):
    import subprocess
    r = tmp_path / "r"
    r.mkdir()
    for a in (["init", "-q", "-b", "main"], ["config", "user.name", "t"], ["config", "user.email", "t@t"], ["config", "commit.gpgsign", "false"]):
        subprocess.run(["git", *a], cwd=r, check=True, capture_output=True)
    (r / "customer_site").mkdir()
    (r / "customer_site" / "tools.html").write_text("<ul></ul>")
    (r / "customer_site" / "about.html").write_text("about v1")
    (r / "sitemap.xml").write_text("<urlset>\n<url><loc>x/index.html</loc></url>\n</urlset>\n")
    subprocess.run(["git", "add", "-A"], cwd=r, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=r, check=True, capture_output=True)
    return r


def _changed(r):
    import subprocess
    return subprocess.run(["git", "show", "--name-only", "--format=", "HEAD"], cwd=r, capture_output=True, text=True).stdout.split()


def test_generated_tool_pages_are_committed_and_unrelated_changes_are_not(tmp_path):
    import importlib.util
    import sys
    spec = importlib.util.spec_from_file_location("tpd", str(Path(__file__).resolve().parent.parent / "scripts" / "tool_pages_daily.py"))
    tpd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tpd)
    r = _repo(tmp_path)
    (r / "customer_site" / "tool-new.html").write_text("new page")
    (r / "customer_site" / "tools.html").write_text("<ul><li>new</li></ul>")
    (r / "customer_site" / "about.html").write_text("about v2 (someone else's edit)")
    (r / "sitemap.xml").write_text("<urlset>\n<url><loc>x/index.html</loc></url>\n  <url><loc>x/tool-new.html</loc></url>\n</urlset>\n")
    out = tpd.commit_generated(r)
    assert out["committed"] == 3
    assert sorted(_changed(r)) == ["customer_site/tool-new.html", "customer_site/tools.html", "sitemap.xml"]
    import subprocess
    assert "about.html" in subprocess.run(["git", "status", "--porcelain"], cwd=r, capture_output=True, text=True).stdout  # left alone


def test_a_sitemap_with_unrelated_or_removed_lines_is_not_committed(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("tpd2", str(Path(__file__).resolve().parent.parent / "scripts" / "tool_pages_daily.py"))
    tpd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tpd)
    r = _repo(tmp_path)
    (r / "sitemap.xml").write_text("<urlset>\n<url><loc>x/other-page.html</loc></url>\n</urlset>\n")  # removes a line, adds a non-tool one
    out = tpd.commit_generated(r)
    assert out["committed"] == 0

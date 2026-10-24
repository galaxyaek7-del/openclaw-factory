"""Tests for the read-only MCP pilot (mcp_pilot/gf_readonly_server.py).

They pin the boundaries the pilot was approved under: exactly three read-only
tools, no write path, no secret or fingerprint in any output, no path escape
from kids_studio/renders, no import shadowing, UTF-8 Arabic over stdio
regardless of the console code page, and a byte-exact settings rollback.
No test touches the network: the CI detector is replaced with a fake.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "mcp_pilot" / "gf_readonly_server.py"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


S = _load("gf_readonly_server_under_test", SERVER)
_TMP_LOG = Path(tempfile.mkdtemp()) / "calls.jsonl"
S.LOG = _TMP_LOG                       # keep test calls out of the real audit log
_TEST_ENV = dict(os.environ, GF_MCP_CALL_LOG=str(_TMP_LOG))


def _rpc(lines, cwd=ROOT, env=None):
    """Run the real server as a subprocess, the way an MCP client does."""
    env = dict(env or os.environ, GF_MCP_CALL_LOG=str(_TMP_LOG))
    data =b"".join(json.dumps(m, ensure_ascii=False).encode("utf-8") + b"\n" for m in lines)
    p = subprocess.run([sys.executable, "-E", "-P", str(SERVER)], input=data, capture_output=True,
                       cwd=cwd, env=env, timeout=120)
    return [json.loads(x) for x in p.stdout.decode("utf-8").splitlines() if x.strip()], p


ALL_TOOLS = ["ci_status", "write_gate_status", "verify_render",
             "factory_products", "distribution_status", "pinterest_queue_status", "video_studio_status"]
FILE_TOOLS = ALL_TOOLS[3:]          # 2026-10-24: fixed-file readers, no arguments

INIT = {"jsonrpc": "2.0", "id": 0, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}}


class TestProtocol(unittest.TestCase):
    def test_handshake_and_tool_list(self):
        out, _ = _rpc([INIT, {"jsonrpc": "2.0", "method": "notifications/initialized"},
                       {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}])
        self.assertEqual([r["id"] for r in out], [0, 1])            # no reply to the notification
        self.assertEqual(out[0]["result"]["protocolVersion"], "2025-06-18")
        self.assertIn("tools", out[0]["result"]["capabilities"])
        names = [t["name"] for t in out[1]["result"]["tools"]]
        self.assertEqual(names, ALL_TOOLS)
        for t in out[1]["result"]["tools"]:
            self.assertTrue(t["annotations"]["readOnlyHint"])
            self.assertFalse(t["annotations"]["destructiveHint"])
            self.assertFalse(t["inputSchema"]["additionalProperties"])

    def test_unknown_protocol_version_gets_a_supported_one(self):
        r = S.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "1999-01-01"}})
        self.assertIn(r["result"]["protocolVersion"], S.SUPPORTED_PROTOCOLS)

    def test_errors_are_jsonrpc_errors(self):
        out, _ = _rpc([{"jsonrpc": "2.0", "id": 5, "method": "resources/write"}])
        self.assertEqual(out[0]["error"]["code"], -32601)
        p = subprocess.run([sys.executable, "-E", "-P", str(SERVER)], input=b"{not json\n",
                           capture_output=True, timeout=60, env=_TEST_ENV)
        self.assertEqual(json.loads(p.stdout)["error"]["code"], -32700)


class TestReadOnlySurface(unittest.TestCase):
    def test_exactly_the_listed_tools_and_no_generic_capability(self):
        # The tool set is pinned by name: adding one means adding it here, on purpose.
        self.assertEqual(list(S.TOOLS), ALL_TOOLS)
        src = SERVER.read_text(encoding="utf-8")
        for bad in ("shell=True", "eval(", "exec(", "os.system", "urlopen", "requests",
                    ".write_text(", "unlink(", "rmtree", "record_state(", "check_write_authorization(",
                    "credential_fingerprint(", "load_token", "consume_scope("):
            code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith(("#", "*", "never", "This")))
            self.assertNotIn(bad, code.split('"""', 2)[-1], bad)

    def test_ci_status_never_records_state(self):
        fake = mock.Mock()
        fake.detect.return_value = ("PASS", "ok", {"evidence": {"runs": [], "jobs": [], "commit_sha": "a" * 40}, "detail": {}})
        with mock.patch.dict(S._MODULES, {"gf_ci_health_detector": fake}):
            S.tool_ci_status({"commit_sha": "a" * 40})
        fake.record_state.assert_not_called()

    def test_ci_status_reports_blocked_when_github_unreadable(self):
        fake = mock.Mock()
        fake.detect.return_value = ("UNKNOWN", "evidence could not be read: URLError",
                                    {"evidence": {"evidence_error": "URLError", "runs": [], "jobs": []}, "detail": {}})
        with mock.patch.dict(S._MODULES, {"gf_ci_health_detector": fake}):
            r = S.tool_ci_status({"commit_sha": "abcdef1"})
        self.assertEqual(r["status"], "BLOCKED")
        self.assertEqual(r["detector_verdict"], "UNKNOWN")      # never upgraded

    def test_ci_status_rejects_bad_input(self):
        for bad in ({"commit_sha": "HEAD; rm -rf /"}, {"commit_sha": "ABCDEF1"}, {"ref": "--upload-pack=x"}):
            with self.assertRaises(S.ToolError):
                S.tool_ci_status(bad)


class TestNoSecretsLeave(unittest.TestCase):
    def test_write_gate_status_never_returns_fingerprint_and_never_reads_env(self):
        fp = "0123456789abcdef"
        state = {"status": "VERIFIED", "reason": "x", "fingerprint_prefix": fp, "at": "2026-10-15T00:00:00+00:00"}
        with tempfile.TemporaryDirectory() as d:
            sp = Path(d) / "state.json"
            sp.write_text(json.dumps(state), encoding="utf-8")
            opened = []
            real_open = open

            def spy(f, *a, **k):
                opened.append(str(f))
                return real_open(f, *a, **k)

            with mock.patch.object(S, "AUTH_STATE", sp), mock.patch("builtins.open", spy), \
                    mock.patch.dict(os.environ, {"FACTORY_LIVE_PUBLISH": "true"}):
                r = S.call_tool("write_gate_status", {})
        text = r["content"][0]["text"]
        self.assertNotIn(fp, text)
        self.assertNotIn("fingerprint_prefix", text)
        self.assertFalse(any(o.endswith(".env") for o in opened), opened)
        body = json.loads(text)
        self.assertNotEqual(body["observable_decision"], "ALLOW")
        self.assertEqual(set(body["auth_state"]), {"status", "recorded_at", "age_seconds", "stale"})

    def test_sanitizer(self):
        sha = "125653195d338499f0b31cec2772f71099476e2e"
        dirty = (f"commit {sha} digest {'ab' * 32} fp 0123456789abcdef "
                 "url https://x/?access_token=SECRETVALUE123 tok ghp_" + "A" * 36 +
                 " bot 1234567890:" + "B" * 35 + " نونو")
        clean = S.sanitize_text(dirty)
        self.assertIn(sha, clean)
        self.assertIn("نونو", clean)
        for leaked in ("ab" * 32, "0123456789abcdef", "SECRETVALUE123", "ghp_", "B" * 35):
            self.assertNotIn(leaked, clean)


class TestPathBoundary(unittest.TestCase):
    def test_escapes_and_wrong_types_are_refused(self):
        for p in ("kids_studio/renders/../../.env", "../.env", ".env", "C:/Windows/win.ini",
                  "kids_studio/renders/ep01_animatic.ar.srt", "kids_studio/renders/missing.mp4",
                  "kids_studio/renders/x.mp4\x00.txt", "", "a" * 300):
            with self.subTest(p=p), self.assertRaises(S.ToolError):
                S._render_path(p)
        with self.assertRaises(S.ToolError):
            S.tool_verify_render({"path": "kids_studio/renders/ep01_animatic.mp4", "out": "x"})

    def test_symlink_out_of_the_root_is_refused(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / "evil.mp4"
            target.write_bytes(b"\x00" * 16)
            link = S.RENDERS / "zz_symlink_probe.mp4"
            try:
                os.symlink(target, link)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation not permitted on this machine")
            try:
                with self.assertRaises(S.ToolError):
                    S._render_path("kids_studio/renders/zz_symlink_probe.mp4")
            finally:
                link.unlink()

    @unittest.skipUnless(sys.platform == "win32", "directory junctions are Windows-only")
    def test_junction_out_of_the_root_is_refused(self):
        import _winapi
        with tempfile.TemporaryDirectory() as outside:
            (Path(outside) / "evil.mp4").write_bytes(b"\x00" * 16)
            junction = S.RENDERS / "zz_junction_probe"
            _winapi.CreateJunction(outside, str(junction))
            try:
                self.assertTrue((junction / "evil.mp4").exists())       # the escape route is real
                with self.assertRaises(S.ToolError):
                    S._render_path("kids_studio/renders/zz_junction_probe/evil.mp4")
            finally:
                os.rmdir(junction)                                      # removes the link, not the target

    def test_verify_render_writes_nothing(self):
        vv = mock.Mock()
        vv.analyze.return_value = {"verdict": "PASS", "file": "x", "checks": {}}
        target = S.RENDERS / "ep01_sc01_poc.mp4"
        if not target.exists():
            self.skipTest("render not present")
        before = sorted((p.name, p.stat().st_mtime_ns) for p in S.RENDERS.iterdir() if p.is_file())
        with mock.patch.dict(S._MODULES, {"gf_verify_video": vv}):
            r = S.tool_verify_render({"path": "kids_studio/renders/ep01_sc01_poc.mp4"})
        after = sorted((p.name, p.stat().st_mtime_ns) for p in S.RENDERS.iterdir() if p.is_file())
        self.assertEqual(before, after)
        self.assertEqual(r["status"], "PASS")
        self.assertEqual(r["file"], "kids_studio/renders/ep01_sc01_poc.mp4")


class TestEnvironmentRobustness(unittest.TestCase):
    def test_stdlib_shadowing_modules_in_cwd_are_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ("select", "json", "subprocess"):
                (Path(d) / f"{name}.py").write_text("raise SystemExit('SHADOWED')\n", encoding="utf-8")
            out, p = _rpc([INIT, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}], cwd=d)
        self.assertNotIn(b"SHADOWED", p.stdout + p.stderr)
        self.assertEqual(len(out[1]["result"]["tools"]), len(ALL_TOOLS))

    def test_request_arriving_during_a_verification_is_not_swallowed(self):
        # Regression (2026-10-15): FFmpeg inherited the server's stdin and read
        # the next JSON-RPC line, so a ci_status call sent while verify_render
        # was running never reached the server and the client hung. Earlier
        # tests sent every line up front, where Python had already buffered them.
        if not (S.RENDERS / "ep01_sc01_poc.mp4").exists():
            self.skipTest("render not present")
        import threading
        p = subprocess.Popen([sys.executable, "-E", "-P", str(SERVER)], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=_TEST_ENV)
        got = []
        reader = threading.Thread(target=lambda: got.extend(json.loads(l) for l in p.stdout), daemon=True)
        reader.start()

        def send(m):
            p.stdin.write(json.dumps(m).encode("utf-8") + b"\n")
            p.stdin.flush()
        try:
            send(INIT)
            send({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                  "params": {"name": "verify_render", "arguments": {"path": "kids_studio/renders/ep01_sc01_poc.mp4"}}})
            import time
            time.sleep(0.4)                       # FFmpeg is now running
            send({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                  "params": {"name": "write_gate_status", "arguments": {}}})
            deadline = time.time() + 90
            while time.time() < deadline and len(got) < 3:
                time.sleep(0.2)
        finally:
            p.stdin.close()
            p.wait(timeout=30)
        self.assertEqual(sorted(r["id"] for r in got), [0, 2, 3])

    def test_arabic_round_trips_under_a_non_utf8_code_page(self):
        env = dict(os.environ, PYTHONIOENCODING="cp850", PYTHONUTF8="0")
        name = "أداة_نونو"
        out, _ = _rpc([INIT, {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                              "params": {"name": name, "arguments": {}}}], env=env)
        self.assertTrue(out[1]["result"]["isError"])
        self.assertIn(name, out[1]["result"]["content"][0]["text"])


class TestSettingsRollback(unittest.TestCase):
    def test_apply_then_rollback_is_byte_exact_and_keeps_allow_rules(self):
        R = _load("settings_rules_under_test", ROOT / "mcp_pilot" / "settings_rules.py")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "settings.local.json"
            original = '{\n  "permissions": {\n    "allow": [\n      "Bash(ls)",\n      "Read(*)"\n    ]\n  }\n}\n'
            p.write_text(original, encoding="utf-8", newline="")
            R.apply(p)
            data = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(data["permissions"]["allow"], ["Bash(ls)", "Read(*)"])
            self.assertEqual(data["permissions"]["deny"], R.RULES)
            R.rollback(p)
            self.assertEqual(p.read_text(encoding="utf-8"), original)

    def test_deny_list_covers_no_read_tools(self):
        R = _load("settings_rules_under_test2", ROOT / "mcp_pilot" / "settings_rules.py")
        for r in R.RULES:
            tool = r.split("__")[-1].lower()
            for read_word in ("read", "get", "list", "search", "fetch", "query"):
                self.assertFalse(tool.startswith(read_word), r)


class TestFactoryStateTools(unittest.TestCase):
    """The 2026-10-24 file readers: fixed files only, no arguments, nothing written."""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)
        w = lambda name, obj: (self.d / name).write_text(json.dumps(obj), encoding="utf-8")  # noqa: E731
        w("reg.json", {"generated_at": "2026-10-24T00:00:00+00:00", "drift": {"live_missing_from_catalog": ["a", "b"]},
                       "products": [{"primary_state": "PUBLIC_LISTING_VERIFIED", "sales_count": 0},
                                    {"primary_state": "UPLOAD_COMPLETED", "sales_count": 0}]})
        w("dash.json", {"generated_at": "2026-10-24T00:00:00+00:00",
                        "operational": {"platforms": {"x": {"name": "X", "state": "BLOCKED_SPEND", "publish_mode": "MANUAL_HANDOFF",
                                                            "why": "paid", "missing_credentials": ["X_SECRET_NAME"]}},
                                        "awaiting_approval": ["SJ-1", "SJ-2"], "jobs_by_state": {"QA_PASSED": 2}},
                        "commercial": {"metrics": "NO REAL METRICS RECORDED", "verified_revenue_cents": 0}})
        w("queue.json", {"generated_at": "2026-10-24T00:00:00+00:00", "board": None, "board_lookup": "no board",
                         "summary": {"BLOCKED_NO_BOARD": 1},
                         "items": [{"offer_id": "B14-001", "status": "BLOCKED_NO_BOARD", "when_local": "2026-10-27T10:00:00",
                                    "call": {"reviewers": "founder@example.com", "info": "{}"}}]})
        w("brand.json", {"label": "galaxyaek7", "connected_networks": {"pinterest": "p", "tiktok": "t"}, "post_creation": "BLOCKED_NEEDS_BOARD"})
        self.patches = [mock.patch.object(S, "PRODUCT_REGISTRY", self.d / "reg.json"),
                        mock.patch.object(S, "DIST_DASHBOARD", self.d / "dash.json"),
                        mock.patch.object(S, "PINTEREST_QUEUE", self.d / "queue.json"),
                        mock.patch.object(S, "METRICOOL_BRAND", self.d / "brand.json"),
                        mock.patch.object(S, "METRICOOL_ATTEMPTS", self.d / "attempts.jsonl"),
                        mock.patch.object(S, "VIDEO_PROJECTS", self.d / "projects"),
                        mock.patch.object(S, "VIDEO_OUTPUT", self.d / "output")]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)
        (self.d / "projects").mkdir()

    def call(self, name, args=None):
        r = S.call_tool(name, args or {})
        return r, (json.loads(r["content"][0]["text"]) if not r["isError"] else r["content"][0]["text"])

    def test_values_come_from_the_files(self):
        _, p = self.call("factory_products")
        self.assertEqual((p["products"], p["sales_total"], p["drift_counts"]), (2, 0, {"live_missing_from_catalog": 2}))
        _, d = self.call("distribution_status")
        self.assertEqual((d["awaiting_approval"], d["platforms"]["x"]["state"]), (2, "BLOCKED_SPEND"))
        self.assertNotIn("missing_credentials", d["platforms"]["x"])          # credential names are not repeated
        _, q = self.call("pinterest_queue_status")
        self.assertEqual((q["board_found"], q["summary"], q["submissions"]), (False, {"BLOCKED_NO_BOARD": 1}, {"attempts": 0, "created": 0}))
        self.assertNotIn("founder@example.com", json.dumps(q))                  # the post bodies stay in the file
        _, v = self.call("video_studio_status")
        self.assertEqual(v["videos"], [])

    def test_arguments_refused_and_missing_files_reported(self):
        for name in FILE_TOOLS:
            r, text = self.call(name, {"path": "../../.env"})
            self.assertTrue(r["isError"], name)
            self.assertIn("takes no arguments", text)
        (self.d / "reg.json").unlink()
        r, text = self.call("factory_products")
        self.assertTrue(r["isError"])
        self.assertIn("not been generated yet", text)

    def test_reads_no_env_and_writes_nothing(self):
        opened, real_open = [], open

        def spy(f, *a, **k):
            opened.append((str(f), a[0] if a else k.get("mode", "r")))
            return real_open(f, *a, **k)

        before = sorted(p.name for p in self.d.iterdir())
        with mock.patch("builtins.open", spy):
            for name in FILE_TOOLS:
                self.call(name)
        self.assertFalse(any(f.endswith(".env") for f, _ in opened), opened)
        writes = [f for f, m in opened if any(c in str(m) for c in "wax+") and not f.endswith(".jsonl")]
        self.assertEqual(writes, [])                                         # only the call log is appended
        self.assertEqual(sorted(p.name for p in self.d.iterdir()), before)


if __name__ == "__main__":
    unittest.main()

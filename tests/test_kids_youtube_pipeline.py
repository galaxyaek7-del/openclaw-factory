"""Children's YouTube pipeline: preflight gates, founder approval bound to the
file, write gate, upload calls (fake HTTP), ledger and dedup. Temp files only;
no network, no real credentials, the real ledgers are never touched."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "kids_studio" / "publishing"))
import preflight  # noqa: E402
import youtube_publisher as yp  # noqa: E402
import kids_youtube_publish_daily as daily  # noqa: E402
import approve_kids_episode as approve  # noqa: E402

NOW = datetime(2026, 10, 30, 12, tzinfo=timezone.utc)
CREDS = {"YOUTUBE_CLIENT_ID": "id", "YOUTUBE_CLIENT_SECRET": "secret", "YOUTUBE_REFRESH_TOKEN": "refresh"}
SRT = "1\n00:00:00,000 --> 00:00:02,000\nمرحبا\n\n2\n00:00:03,000 --> 00:00:05,000\nهيا\n"


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.root = Path(self.dir.name)
        (self.root / "r").mkdir()
        video = self.root / "r" / "ep.mp4"
        video.write_bytes(b"\x00" * 200_000)
        (self.root / "r" / "ep.ar.srt").write_text(SRT, encoding="utf-8")
        (self.root / "r" / "ep.verify.json").write_text(json.dumps(
            {"bytes": 200_000, "container_duration_s": 10.0, "checks": {"a": True, "b": True}}), encoding="utf-8")
        (self.root / "ledger.json").write_text(json.dumps({"assets": [
            {"id": "char", "usable": True}, {"id": "voice-arabic", "usable": False}]}), encoding="utf-8")
        self.ep = {"episode": "ep99", "video": "r/ep.mp4", "verify": "r/ep.verify.json", "subtitles": "r/ep.ar.srt",
                   "rights_ledger": "ledger.json", "not_in_this_cut": {"voice-arabic": "no voice"},
                   "title": "حلقة", "description": "قصة قصيرة", "tags": ["أطفال"]}
        self.defaults = {"made_for_kids": True, "category_id": "1"}
        self.registry = self.root / "episodes.json"
        self.registry.write_text(json.dumps({"channel_defaults": self.defaults, "episodes": [self.ep]}), encoding="utf-8")
        self.approvals = self.root / "approvals.json"
        self.uploads = self.root / "uploads.jsonl"
        self.paths = {"registry": self.registry, "approvals": self.approvals, "ledger": self.uploads, "root": self.root,
                      "status": self.root / "status.json"}

    def tearDown(self):
        self.dir.cleanup()

    def approve(self, **over):
        kw = dict(episode="ep99", privacy="unlisted", child_safety=True, arabic=True, days=14,
                  approvals_path=self.approvals, registry=self.registry, root=self.root, now=NOW)
        kw.update(over)
        return approve.approve(**kw)

    def checks(self, env=CREDS, now=NOW):
        res, digest = preflight.check(self.ep, self.defaults, root=self.root, approvals_path=self.approvals,
                                      ledger=self.uploads, env=env, now=now)
        return {k: v["status"] for k, v in res.items()}, digest


class Preflight(Base):
    def test_everything_but_approval_passes_on_a_good_episode(self):
        c, _ = self.checks()
        self.assertEqual([k for k, v in c.items() if v != "PASS"], ["approval"])

    def test_approval_is_bound_to_the_exact_file(self):
        self.approve()
        self.assertEqual(self.checks()[0]["approval"], "PASS")
        (self.root / "r" / "ep.mp4").write_bytes(b"\x01" * 200_000)       # rebuilt video
        self.assertEqual(self.checks()[0]["approval"], "FAIL")

    def test_approval_needs_both_reviews_and_expires(self):
        with self.assertRaises(ValueError):
            self.approve(arabic=False)
        with self.assertRaises(ValueError):
            self.approve(privacy="everyone")
        self.approve(days=1)
        self.assertEqual(self.checks(now=NOW + timedelta(days=2))[0]["approval"], "FAIL")

    def test_each_gate_fails_on_its_own_defect(self):
        self.approve()
        bad_verify = {"bytes": 200_000, "container_duration_s": 10.0, "checks": {"a": True, "b": False}}
        (self.root / "r" / "ep.verify.json").write_text(json.dumps(bad_verify), encoding="utf-8")
        self.assertEqual(self.checks()[0]["verify"], "FAIL")
        self.ep["not_in_this_cut"] = {}
        self.assertEqual(self.checks()[0]["rights"], "FAIL")
        self.ep["description"] = "visit https://example.com"
        self.assertEqual(self.checks()[0]["metadata"], "FAIL")
        self.assertEqual(self.checks(env={})[0]["credentials"], "FAIL")
        (self.root / "r" / "ep.ar.srt").write_text("1\n00:00:05,000 --> 00:00:04,000\nx\n", encoding="utf-8")
        self.assertEqual(self.checks()[0]["subtitles"], "FAIL")


class FakeYouTube:
    def __init__(self, upload_status=200):
        self.calls = []
        self.upload_status = upload_status

    def __call__(self, method, url, *, headers=None, data=None, timeout=600):
        self.calls.append((method, url.split("?")[0], headers or {}, data))
        if url == yp.TOKEN_URL:
            return 200, {}, json.dumps({"access_token": "tok"}).encode()
        if url == yp.UPLOAD_URL:
            return 200, {"Location": "https://upload.example/session"}, b"{}"
        if url == "https://upload.example/session":
            return self.upload_status, {}, json.dumps({"id": "VID123", "status": {"privacyStatus": "unlisted",
                                                                                  "madeForKids": True}}).encode()
        if url == yp.CAPTION_URL:
            return 200, {}, b"{}"
        return 404, {}, b""


class Upload(Base):
    def run_once(self, fake, **env):
        with mock.patch.dict(os.environ, env, clear=False):
            return daily.once(creds=CREDS, now=NOW, http=fake, **self.paths)

    def test_nothing_happens_without_approval(self):
        fake = FakeYouTube()
        out = self.run_once(fake, GF_ALLOW_KIDS_VIDEO_UPLOAD="true")
        self.assertEqual(out["action"], "none")
        self.assertEqual(fake.calls, [])
        st = json.loads((self.root / "status.json").read_text(encoding="utf-8"))
        self.assertEqual(st["episodes"], [{"episode": "ep99", "passed": False, "failing": ["approval"]}])
        self.assertNotIn("secret", json.dumps(st))

    def test_ready_but_gate_closed_makes_no_call(self):
        self.approve()
        fake = FakeYouTube()
        with mock.patch.dict(os.environ, {"GF_ALLOW_KIDS_VIDEO_UPLOAD": "", "FACTORY_LIVE_PUBLISH": "false"}):
            out = daily.once(creds=CREDS, now=NOW, http=fake, **self.paths)
        self.assertEqual(out["action"], "blocked")
        self.assertEqual(fake.calls, [])

    def test_upload_made_for_kids_with_captions_then_never_again(self):
        self.approve()
        fake = FakeYouTube()
        out = self.run_once(fake, GF_ALLOW_KIDS_VIDEO_UPLOAD="true")
        self.assertEqual(out["action"], "uploaded", out)
        self.assertIn("https://youtu.be/VID123", out["detail"])
        meta = json.loads(fake.calls[1][3].decode("utf-8"))
        self.assertIs(meta["status"]["selfDeclaredMadeForKids"], True)
        self.assertEqual(meta["status"]["privacyStatus"], "unlisted")
        self.assertEqual([c[0] for c in fake.calls], ["POST", "POST", "PUT", "POST"])   # token, session, file, captions
        self.assertNotIn("refresh", out["detail"])
        rec = json.loads(self.uploads.read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual((rec["status"], rec["video_id"], rec["captions"]), ("UPLOADED", "VID123", "UPLOADED"))
        again = FakeYouTube()
        self.assertEqual(self.run_once(again, GF_ALLOW_KIDS_VIDEO_UPLOAD="true")["action"], "none")
        self.assertEqual(again.calls, [])

    def test_a_failed_upload_is_recorded_and_retried_next_time(self):
        self.approve()
        out = self.run_once(FakeYouTube(upload_status=500), GF_ALLOW_KIDS_VIDEO_UPLOAD="true")
        self.assertEqual(out["action"], "failed")
        self.assertEqual(json.loads(self.uploads.read_text(encoding="utf-8").splitlines()[-1])["status"], "FAILED")
        self.assertEqual(self.run_once(FakeYouTube(), GF_ALLOW_KIDS_VIDEO_UPLOAD="true")["action"], "uploaded")

    def test_the_publisher_refuses_before_any_request_when_the_gate_is_closed(self):
        fake = FakeYouTube()
        from channels.write_gate import WriteNotAuthorized
        with mock.patch.dict(os.environ, {"GF_ALLOW_KIDS_VIDEO_UPLOAD": "", "FACTORY_LIVE_PUBLISH": "false"}):
            with self.assertRaises(WriteNotAuthorized):
                yp.upload(self.ep, self.defaults, "private", self.root / "r/ep.mp4", None, CREDS, http=fake)
        self.assertEqual(fake.calls, [])


class Privacy(unittest.TestCase):
    def test_approvals_and_upload_log_are_git_ignored(self):
        import subprocess
        for f in ("data/kids_upload_approvals.json", "data/youtube_uploads.jsonl"):
            self.assertEqual(subprocess.run(["git", "check-ignore", "-q", "--no-index", f], cwd=ROOT).returncode, 0, f)


if __name__ == "__main__":
    unittest.main()

"""video_studio: renderer layout/timing, media verifier (catches real defects),
and the fail-closed YouTube state machine (14 offline cases, fake transport,
no network). Speech is stubbed so this runs on CI (Linux, no Windows voices)."""
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    import imageio_ffmpeg  # noqa: F401
    from video_studio import narrated, verify_media
    HAVE_FFMPEG = True
except Exception:  # noqa: BLE001
    HAVE_FFMPEG = False

from video_studio import youtube_upload as yt  # noqa: E402

PILOTS = ROOT / "video_studio" / "projects"


def fake_tts(text, out_wav, voice=None, rate=0):
    """A tone whose length depends on the text, standing in for speech."""
    dur = 0.4 + 0.02 * len(text)
    n = int(22050 * dur)
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(22050)
        w.writeframes(b"".join(struct.pack("<h", int(6000 * math.sin(i * 0.06))) for i in range(n)))
    return n / 22050


def tiny_manifest(fmt="vertical"):
    return {"id": f"t_{fmt}", "format": fmt, "palette": {"bg1": "#000022", "bg2": "#002244", "accent": "#FFCC00", "text": "#FFFFFF"},
            "scenes": [{"heading": "One", "visual": {"type": "stat", "value": "6%", "label": "a label"}, "lines": ["First line.", "Second one here."]},
                       {"heading": "Two", "visual": {"type": "steps", "progressive": True, "items": ["a", "b"]}, "lines": ["Third."]}]}


@unittest.skipUnless(HAVE_FFMPEG, "imageio-ffmpeg not installed")
class TestRenderer(unittest.TestCase):
    def test_pilot_frames_fit_and_stay_still_within_a_scene(self):
        for f in sorted(x for x in PILOTS.glob("pilot_*.json") if not x.name.endswith(".rights.json")):
            m = json.loads(f.read_text(encoding="utf-8"))
            with tempfile.TemporaryDirectory() as td:
                for si, sc in enumerate(m["scenes"]):
                    tops = set()
                    for li in range(len(sc["lines"])):
                        meta = narrated.draw_frame(m, si, li, Path(td) / "x.png")
                        self.assertLess(meta["content_bottom"], meta["subtitle_box"][0], f"{f.name} scene {si} line {li}")
                        self.assertGreater(meta["content_top"], 100)
                        tops.add(meta["content_top"])
                    self.assertEqual(len(tops), 1, f"{f.name} scene {si}: content moves between cuts")

    def test_pilot_b_facts_are_internally_consistent(self):
        m = json.loads((PILOTS / "pilot_b_cap_rate_explainer.json").read_text(encoding="utf-8"))
        f = m["facts"]
        self.assertEqual(f["monthly_rent"] * 12, f["gross_annual_rent"])
        self.assertEqual(round(f["gross_annual_rent"] * f["vacancy_rate"]), f["vacancy_loss"])
        self.assertEqual(f["gross_annual_rent"] - f["vacancy_loss"] - f["operating_expenses"], f["noi"])
        self.assertAlmostEqual(f["noi"] / f["price"], f["cap_rate"])

    def test_build_is_timed_by_the_audio_and_passes_verification(self):
        with tempfile.TemporaryDirectory() as td:
            mp = Path(td) / "m.json"
            mp.write_text(json.dumps(tiny_manifest("landscape")), encoding="utf-8")
            rec = narrated.build(mp, out_root=Path(td) / "out", synthesize=fake_tts)
            self.assertEqual(rec["sentences"], 3)
            for a, b in zip(rec["cues"], rec["cues"][1:]):
                self.assertLessEqual(a["end"], b["start"])
            expected = sum(round((fake_tts(c["text"], Path(td) / "t.wav") + narrated.PAUSE_S) * 30) / 30 for c in rec["cues"])
            self.assertAlmostEqual(rec["duration_s"], expected, places=2)
            r = verify_media.verify(rec["video"], "landscape", Path(td) / "out" / rec["id"] / f"{rec['id']}.build.json")
            self.assertTrue(r["passed"], r["failures"])
            self.assertEqual(r["probe"]["audio"]["sample_rate"], 48000)
            self.assertTrue(r["probe"]["subtitle"])


class TestTrimSilence(unittest.TestCase):
    def test_padding_is_cut_and_speech_kept(self):
        from video_studio import tts
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "a.wav"
            rate, tone = 22050, [int(8000 * math.sin(i * 0.05)) for i in range(22050)]   # 1.0 s of "speech"
            pcm = [0] * int(0.1 * rate) + tone + [0] * int(0.75 * rate)                 # padding as measured
            with wave.open(str(p), "wb") as w:
                w.setnchannels(1), w.setsampwidth(2), w.setframerate(rate)
                w.writeframes(struct.pack(f"<{len(pcm)}h", *pcm))
            dur = tts.trim_silence(p)
            self.assertAlmostEqual(dur, 1.0 + 2 * 0.04, delta=0.03)
            self.assertAlmostEqual(tts.wav_duration(p), dur, places=3)


@unittest.skipUnless(HAVE_FFMPEG, "imageio-ffmpeg not installed")
class TestVerifierCatchesDefects(unittest.TestCase):
    """A verifier that always passes proves nothing: feed it broken files."""

    def _make(self, td, name, vf, af, subs=True, size="1920x1080", dur=4):
        out = Path(td) / name
        args = [narrated.ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"{vf}{':' if '=' in vf else '='}s={size}:d={dur}:r=30",
                "-f", "lavfi", "-i", af]
        if subs:
            srt = Path(td) / "s.srt"
            srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nhi\n", encoding="utf-8")
            args += ["-i", str(srt), "-map", "0:v", "-map", "1:a", "-map", "2:s", "-c:s", "mov_text"]
        args += ["-t", str(dur), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(out)]
        subprocess.run(args, check=True, stdin=subprocess.DEVNULL)
        return out

    def test_good_file_passes(self):
        with tempfile.TemporaryDirectory() as td:
            f = self._make(td, "ok.mp4", "testsrc2", "sine=f=440:d=4")
            self.assertEqual(verify_media.verify(f, "landscape")["failures"], [])

    def test_black_video_is_caught(self):
        with tempfile.TemporaryDirectory() as td:
            f = self._make(td, "black.mp4", "color=c=black", "sine=f=440:d=4")
            self.assertTrue(any("black" in x for x in verify_media.verify(f, "landscape")["failures"]))

    def test_silent_audio_is_caught(self):
        with tempfile.TemporaryDirectory() as td:
            f = self._make(td, "silent.mp4", "testsrc2", "anullsrc=r=48000:cl=mono")
            fails = verify_media.verify(f, "landscape")["failures"]
            self.assertTrue(any("silence" in x or "quiet" in x for x in fails), fails)

    def test_missing_subtitles_and_wrong_resolution_are_caught(self):
        with tempfile.TemporaryDirectory() as td:
            f = self._make(td, "nosub.mp4", "testsrc2", "sine=f=440:d=4", subs=False)
            fails = verify_media.verify(f, "vertical")["failures"]
            self.assertIn("no subtitle stream", fails)
            self.assertTrue(any("resolution" in x for x in fails))

    def test_truncated_file_is_caught(self):
        with tempfile.TemporaryDirectory() as td:
            f = self._make(td, "ok.mp4", "testsrc2", "sine=f=440:d=4")
            data = f.read_bytes()
            bad = Path(td) / "cut.mp4"
            bad.write_bytes(data[: len(data) // 2])
            self.assertFalse(verify_media.verify(bad, "landscape")["passed"])


class FakeYouTube:
    """Scripted stand-in for the platform. Records every call; touches no network."""

    def __init__(self, upload_error=None, processing="processed", privacy_after_publish="public"):
        self.calls, self.upload_error, self.processing = [], upload_error, processing
        self.privacy_after_publish, self.privacy = privacy_after_publish, {}

    def upload(self, path, meta):
        self.calls.append(("upload", path))
        if self.upload_error:
            err, self.upload_error = self.upload_error, None
            raise err
        vid = f"FAKE{len(self.calls):04d}"
        self.privacy[vid] = meta["privacy"]
        return {"video_id": vid, "privacy": meta["privacy"]}

    def get_status(self, vid):
        self.calls.append(("get_status", vid))
        return {"upload_status": self.processing, "privacy": self.privacy.get(vid), "rejection_reason": "duplicate"}

    def set_privacy(self, vid, privacy):
        self.calls.append(("set_privacy", vid, privacy))
        self.privacy[vid] = self.privacy_after_publish


GOOD_META = {"title": "Cap rate in 90 seconds", "description": "Educational. Not financial advice.", "tags": ["cap rate"],
             "category_id": "27", "made_for_kids": False, "contains_synthetic_media": True, "privacy": "private"}


class TestYouTubeStateMachine(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.td, ignore_errors=True)
        self.video = Path(self.td) / "v.mp4"
        self.video.write_bytes(b"not really a video but stable bytes" * 100)
        env = {"FACTORY_WRITE_SCOPE_DIR": str(Path(self.td) / "scopes"), "FACTORY_LIVE_PUBLISH": "false"}
        p = mock.patch.dict(os.environ, env)
        p.start()
        self.addCleanup(p.stop)
        self.fake = FakeYouTube()
        self.jobs = yt.Jobs(ledger=Path(self.td) / "jobs.jsonl", transport=self.fake)

    def ready(self, meta=GOOD_META, rights="CLEARED"):
        j = self.jobs.register(self.video, dict(meta), {"status": rights})
        self.jobs.record_qa(j, {"passed": True, "score": 80, "video_sha256": yt.sha256_file(self.video)})
        return j

    def scope(self, j):
        from channels import write_scope
        sha = self.jobs.job(j)["video_sha256"]
        return write_scope.issue_scope(product_id="yt:" + sha, slug="test", payload={"file_path": str(self.video)},
                                       operation="upload_file").scope_id

    def live(self):
        return mock.patch.dict(os.environ, {"FACTORY_LIVE_PUBLISH": "true"})

    def uploaded(self):
        j = self.ready()
        self.jobs.request_upload(j)
        with self.live():
            self.jobs.upload(j, self.scope(j))
        return j

    # 1
    def test_01_factory_switch_off_refuses_before_any_call(self):
        from channels.write_gate import WriteNotAuthorized
        j = self.ready()
        self.jobs.request_upload(j)
        with self.assertRaises(WriteNotAuthorized):
            self.jobs.upload(j, self.scope(j))
        self.assertEqual(self.fake.calls, [])

    # 2
    def test_02_no_upload_authorization_refused(self):
        j = self.ready()
        self.jobs.request_upload(j)
        with self.live(), self.assertRaises(yt.Refused):
            self.jobs.upload(j, "made-up-scope")
        self.assertEqual(self.fake.calls, [])

    # 3
    def test_03_authorization_for_other_bytes_refused(self):
        from channels import write_scope
        j = self.ready()
        self.jobs.request_upload(j)
        other = write_scope.issue_scope(product_id="yt:" + "0" * 64, slug="x", payload={"file_path": str(self.video)},
                                        operation="upload_file").scope_id
        with self.live(), self.assertRaises(yt.Refused):
            self.jobs.upload(j, other)
        self.assertEqual(self.fake.calls, [])

    # 4
    def test_04_failed_or_mismatched_qa_cannot_reach_upload(self):
        j = self.jobs.register(self.video, dict(GOOD_META), {"status": "CLEARED"})
        self.jobs.record_qa(j, {"passed": True, "score": 90, "video_sha256": "f" * 64})
        self.assertEqual(self.jobs.job(j)["state"], "QA_FAILED")
        with self.assertRaises(yt.Refused):
            self.jobs.request_upload(j)

    # 5
    def test_05_uncleared_rights_block(self):
        j = self.ready(rights="UNRESOLVED")
        with self.assertRaises(yt.Refused):
            self.jobs.request_upload(j)
        self.assertEqual(self.jobs.job(j)["state"], "BLOCKED")

    # 6
    def test_06_invalid_metadata_blocks(self):
        bad = dict(GOOD_META, title="x" * 101, description="<script>", made_for_kids=None)
        j = self.ready(meta=bad)
        with self.assertRaises(yt.Refused) as c:
            self.jobs.request_upload(j)
        for part in ("title longer", "< or >", "made_for_kids"):
            self.assertIn(part, str(c.exception))

    # 7
    def test_07_public_upload_refused(self):
        j = self.ready(meta=dict(GOOD_META, privacy="public"))
        with self.assertRaises(yt.Refused):
            self.jobs.request_upload(j)

    # 8
    def test_08_happy_path_uploads_private_once(self):
        j = self.uploaded()
        rec = self.jobs.job(j)
        self.assertEqual(rec["state"], "UPLOADED_PRIVATE_OR_UNLISTED")
        self.assertEqual(rec["platform_privacy"], "private")
        self.assertEqual([c[0] for c in self.fake.calls], ["upload"])

    # 9
    def test_09_same_bytes_never_uploaded_twice(self):
        j = self.uploaded()
        self.assertEqual(self.jobs.register(self.video, dict(GOOD_META), {"status": "CLEARED"}), j)
        with self.live():
            r = self.jobs.upload(j, "anything")
        self.assertTrue(r["duplicate"])
        self.assertEqual([c[0] for c in self.fake.calls], ["upload"])

    # 10
    def test_10_network_failure_recorded_and_retry_needs_new_authorization(self):
        self.fake.upload_error = ConnectionError("reset by peer")
        j = self.ready()
        self.jobs.request_upload(j)
        s1 = self.scope(j)
        with self.live(), self.assertRaises(ConnectionError):
            self.jobs.upload(j, s1)
        self.assertEqual(self.jobs.job(j)["state"], "UPLOAD_FAILED")
        self.jobs.request_upload(j)
        with self.live(), self.assertRaises(yt.Refused):
            self.jobs.upload(j, s1)          # single use: the first scope is spent
        with self.live():
            self.jobs.upload(j, self.scope(j))
        self.assertEqual(self.jobs.job(j)["state"], "UPLOADED_PRIVATE_OR_UNLISTED")

    # 11
    def test_11_crash_mid_upload_is_never_reuploaded_automatically(self):
        j = self.ready()
        self.jobs.request_upload(j)
        self.jobs._append(j, "UPLOAD_IN_PROGRESS", transport_call="upload")   # process died here
        with self.live(), self.assertRaises(yt.Refused):
            self.jobs.upload(j, self.scope(j))
        self.assertEqual(self.jobs.job(j)["state"], "NEEDS_RECONCILIATION")
        self.assertEqual(self.fake.calls, [])

    # 12
    def test_12_rejected_processing_stops_publication(self):
        self.fake.processing = "rejected"
        j = self.uploaded()
        self.jobs.check_processing(j)
        self.assertEqual(self.jobs.job(j)["state"], "PROCESSING_FAILED")
        with self.assertRaises(yt.Refused):
            self.jobs.approve_publication(j, approver="founder", evidence="approval message 2026-10-23",
                                          youtube_video_id=self.jobs.job(j)["youtube_video_id"])

    # 13
    def test_13_publication_needs_approval_and_a_public_read_back(self):
        j = self.uploaded()
        self.jobs.check_processing(j)
        vid = self.jobs.job(j)["youtube_video_id"]
        with self.assertRaises(yt.Refused):
            self.jobs.publish(j)                                              # not approved
        with self.assertRaises(yt.Refused):
            self.jobs.approve_publication(j, approver="founder", evidence="ok", youtube_video_id=vid)
        with self.assertRaises(yt.Refused):
            self.jobs.approve_publication(j, approver="founder", evidence="approval message 2026-10-23",
                                          youtube_video_id="OTHER")
        self.jobs.approve_publication(j, approver="founder", evidence="approval message 2026-10-23", youtube_video_id=vid)
        from channels.write_gate import WriteNotAuthorized
        with self.assertRaises(WriteNotAuthorized):
            self.jobs.publish(j)                                              # factory switch still off
        with self.live():
            self.jobs.publish(j)
        self.assertEqual(self.jobs.job(j)["state"], "PUBLISHED_VERIFIED")

    # 14
    def test_14_read_back_mismatch_is_not_counted_as_published(self):
        self.fake.privacy_after_publish = "private"
        j = self.uploaded()
        self.jobs.check_processing(j)
        vid = self.jobs.job(j)["youtube_video_id"]
        self.jobs.approve_publication(j, approver="founder", evidence="approval message 2026-10-23", youtube_video_id=vid)
        with self.live():
            self.jobs.publish(j)
        rec = self.jobs.job(j)
        self.assertEqual(rec["state"], "PUBLICATION_AUTHORIZED")
        self.assertIn("not counted as published", rec["error"])

    def test_secrets_never_reach_the_ledger(self):
        self.fake.upload_error = RuntimeError("401 for Bearer ya29.a0AfH6SMBxxxxxxxxxxxxxxxxxxxxx refresh_token=1//0gabcdefghijklmnopqrstuv")
        j = self.ready()
        self.jobs.request_upload(j)
        with self.live(), self.assertRaises(RuntimeError):
            self.jobs.upload(j, self.scope(j))
        text = Path(self.jobs.ledger).read_text(encoding="utf-8")
        self.assertNotIn("ya29.", text)
        self.assertNotIn("1//0g", text)
        self.assertIn("[REDACTED]", text)

    def test_default_transport_makes_no_call(self):
        jobs = yt.Jobs(ledger=Path(self.td) / "j2.jsonl")
        j = jobs.register(self.video, dict(GOOD_META), {"status": "CLEARED"})
        jobs.record_qa(j, {"passed": True, "score": 80, "video_sha256": yt.sha256_file(self.video)})
        jobs.request_upload(j)
        sha = jobs.job(j)["video_sha256"]
        from channels import write_scope
        s = write_scope.issue_scope(product_id="yt:" + sha, slug="t", payload={"file_path": str(self.video)}, operation="upload_file")
        with self.live(), self.assertRaises(yt.TransportNotConfigured):
            jobs.upload(j, s.scope_id)
        self.assertEqual(jobs.job(j)["state"], "UPLOAD_FAILED")

    def test_module_contains_no_network_client(self):
        src = (ROOT / "video_studio" / "youtube_upload.py").read_text(encoding="utf-8")
        for needle in ("requests", "urllib", "http.client", "googleapiclient", "googleapis.com"):
            self.assertNotIn(needle, src)


if __name__ == "__main__":
    unittest.main()

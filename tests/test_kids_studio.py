"""Tests for the Kids Studio proof-of-concept tools.

They pin the properties the studio's rules depend on: deterministic output,
no network access, a footstep schedule tied to the walk cycle (so audio
sync is checkable), and the storyboard's safety staging (Nunu stops on the
grass and never moves faster than a walk).
"""
import importlib.util
import re
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "kids_studio" / "tools"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


R = _load("render_poc")


class TestNoNetwork(unittest.TestCase):
    def test_tools_import_no_network_modules(self):
        for f in ("render_poc.py", "verify_video.py"):
            src = (TOOLS / f).read_text(encoding="utf-8")
            for bad in ("import socket", "import urllib", "import requests", "http://", "https://"):
                self.assertNotIn(bad, src, f"{f} contains {bad!r}")


class TestDeterminism(unittest.TestCase):
    def test_same_frame_twice_is_identical(self):
        a = R.render(5.0, 64, 36)
        b = R.render(5.0, 64, 36)
        self.assertTrue(np.array_equal(a, b))

    def test_audio_is_deterministic_and_within_peak(self):
        x1, x2 = R.synth_audio(2.0), R.synth_audio(2.0)
        self.assertTrue(np.array_equal(x1, x2))
        self.assertLessEqual(float(np.max(np.abs(x1))), 0.5 + 1e-9)   # about -6 dBFS


class TestWalkAndFootsteps(unittest.TestCase):
    def test_footsteps_fall_inside_the_walk_and_are_evenly_spaced(self):
        ft = R.footstep_times()
        self.assertGreater(len(ft), 10)
        self.assertTrue(all(R.WALK_START < t < R.WALK_END for t in ft))
        gaps = np.diff(ft)
        self.assertTrue(np.allclose(gaps, 0.5 / R.STEP_HZ, atol=1e-3))

    def test_footsteps_coincide_with_a_foot_reaching_the_ground(self):
        # a footfall is where one diagonal pair's lift returns to zero
        for t in R.footstep_times():
            ph = R.nunu_state(t)["phase"]
            self.assertAlmostEqual(abs(np.sin(ph)), 0.0, places=6)

    def test_nunu_stops_on_the_grass_before_the_bridge(self):
        bridge_near_end = -1.6
        self.assertLess(R.nunu_state(12.0)["x"], bridge_near_end)
        # nose included: head reaches about +0.56 beyond the body centre
        self.assertLess(R.nunu_state(12.0)["x"] + 0.56, -1.0)   # stream bank at x = -1.0

    def test_nunu_never_moves_faster_than_a_walk(self):
        xs = [R.nunu_state(t / 24)["x"] for t in range(int(R.DURATION * 24))]
        speed = np.max(np.abs(np.diff(xs))) * 24       # scene units per second
        self.assertLess(speed, 1.0)


class TestVerifierIsHonest(unittest.TestCase):
    def test_verifier_fails_unless_every_check_passes(self):
        src = (TOOLS / "verify_video.py").read_text(encoding="utf-8")
        self.assertRegex(src, r'"PASS" if all\(v is not False for v in C\.values\(\)\) else "FAIL"')



EP = _load("ep01_shots")
B = _load("build_episode")


class TestEpisodeShotList(unittest.TestCase):
    def test_matches_the_storyboard(self):
        sb = (ROOT / "kids_studio/episodes/ep01_nunu_little_bridge/storyboard.md").read_text(encoding="utf-8")
        board = [(m[0], int(m[1])) for m in re.findall(r"^\| (\d{2}) \| \d \| (\d+) s \|", sb, re.M)]
        self.assertEqual([(s["id"], s["dur"]) for s in EP.SHOTS], board)
        self.assertEqual(EP.timeline()[1], 158)

    def test_every_subtitle_line_is_in_the_script(self):
        script = (ROOT / "kids_studio/episodes/ep01_nunu_little_bridge/script_ar.md").read_text(encoding="utf-8")
        lines = [line for s in EP.SHOTS for _, _, line in s["subs"]]
        self.assertEqual(len(lines), 16)
        for line in lines:
            self.assertIn(line.rstrip("."), script, line)

    def test_subtitles_do_not_overlap_and_fit_their_shot(self):
        for s in EP.SHOTS:
            last = -1
            for a, b, _ in s["subs"]:
                self.assertTrue(0 <= a < b <= s["dur"], (s["id"], a, b))
                self.assertGreaterEqual(a, last)
                last = b

    def test_srt_keeps_only_lines_inside_the_cut(self):
        body, n = B.srt(EP, 24.0)
        self.assertEqual(n, 1)      # only shot 02's greeting falls inside the first 24 s
        self.assertIn("صَبَاحُ الخَيْرِ", body)


class TestEpisodeSafetyStaging(unittest.TestCase):
    def _nunu_feet(self, sid, t):
        s = next(x for x in EP.SHOTS if x["id"] == sid)
        objs = s["actors"](t)
        feet = [o for o in objs if o["k"] == "e" and np.allclose(o["r"], (0.05, 0.14, 0.05))]
        return min(o["c"][1] for o in feet) - 0.14

    def test_nunu_never_leaves_the_ground_or_the_deck(self):
        for s in EP.SHOTS:
            for k in range(0, int(s["dur"] * 12)):
                low = self._nunu_feet(s["id"], k / 12) if any(
                    np.allclose(o["r"], (0.05, 0.14, 0.05)) for o in s["actors"](k / 12) if o["k"] == "e") else None
                if low is not None:
                    # standing on grass (0) or the bridge deck (0.12); a raised paw adds at most 0.08,
                    # a hop in the closing shot at most 0.08 -- never a jump over the gap
                    self.assertLess(low, 0.12 + 0.081, (s["id"], k))

    def test_plank_is_tied_before_nunu_crosses(self):
        s12 = next(x for x in EP.SHOTS if x["id"] == "12")
        objs = s12["actors"](8.0)
        plank = [o for o in objs if o["k"] == "o" and np.allclose(o["h"], (0.15, 0.025, 0.42))][0]
        self.assertTrue(np.allclose(plank["R"], np.eye(3)))       # no tilt
        self.assertTrue(any(o["col"] == EP.ROPE for o in objs))   # ropes present


class TestCullingIsExact(unittest.TestCase):
    def test_culled_render_equals_unculled(self):
        s = next(x for x in EP.SHOTS if x["id"] == "10")
        objs = s["actors"](6.0)
        cam, look, fov = s["camera"](6.0)
        culled = R.render_scene(objs, cam, look, fov, 6.0, 96, 54)
        saved = R._screen_candidates, R._shadow_candidates
        try:
            R._screen_candidates = lambda objs, *a: [None] * len(objs)
            R._shadow_candidates = lambda objs, *a: [None] * len(objs)
            full = R.render_scene(objs, cam, look, fov, 6.0, 96, 54)
        finally:
            R._screen_candidates, R._shadow_candidates = saved
        self.assertTrue(np.array_equal(culled, full))



EP2 = _load("ep02_shots")


class TestEpisode2ShotList(unittest.TestCase):
    """Episode 2 (130 s, 14 shots) - the delivered subtitle animatic."""

    SB = ROOT / "kids_studio/episodes/ep02_lulus_lost_ball/storyboard.md"
    SCRIPT = ROOT / "kids_studio/episodes/ep02_lulus_lost_ball/script_ar.md"

    def test_matches_the_storyboard(self):
        sb = self.SB.read_text(encoding="utf-8")
        board = [(m[0], int(m[1])) for m in
                 re.findall(r"^\| (\d{2}) \| \d+ \| (\d+) s \|", sb, re.M)]
        self.assertEqual([(s["id"], s["dur"]) for s in EP2.SHOTS], board)
        self.assertEqual(len(board), 14)
        self.assertEqual(EP2.timeline()[1], 130)

    def test_every_cue_matches_the_script_table(self):
        script = self.SCRIPT.read_text(encoding="utf-8")
        rows = re.findall(
            r"^\| (\d+) \| (\d{2}) \| ([\d.]+)[-\u2013]([\d.]+) \| (.+?) \| (.+?) \|[ \t\r]*$",
            script, re.M)
        self.assertEqual(len(rows), 16)
        got = []
        for t0, s in EP2.timeline()[0]:
            for a, b, line in s["subs"]:
                got.append((s["id"], round(t0 + a, 1), round(t0 + b, 1), line))
        self.assertEqual(len(got), 16)
        self.assertEqual(EP2.SUBTITLE_CUES_TOTAL, 16)
        for (_n, sid, a, b, text, _gloss), (gsid, ga, gb, gline) in zip(rows, got):
            self.assertEqual(sid, gsid)
            self.assertEqual((float(a), float(b)), (ga, gb))
            self.assertEqual(text.strip(), gline)

    def test_subtitles_do_not_overlap_and_fit_their_shot(self):
        for s in EP2.SHOTS:
            last = -1
            for a, b, _ in s["subs"]:
                self.assertTrue(0 <= a < b <= s["dur"], (s["id"], a, b))
                self.assertGreaterEqual(a, last)
                last = b

    def test_srt_keeps_only_lines_inside_the_cut(self):
        body, n = B.srt(EP2, 12.0)
        self.assertEqual(n, 1)          # only shot 01's line starts inside 12 s
        _body, full = B.srt(EP2, 130.0)
        self.assertEqual(full, 16)


class TestEpisode2VisualInvariants(unittest.TestCase):
    """Regressions for three defects found by visual QA of the first cut:
    the ball was orange under a 'red ball' line, the garden backdrop was
    placed behind the cameras, and the ladybug had zero-depth spots."""

    def test_ball_is_red_and_red_dominant(self):
        r, g, b = EP2.BALL_RED
        self.assertGreater(r, 2 * g)
        self.assertGreater(r, 2 * b)
        objs = next(s for s in EP2.SHOTS if s["id"] == "01")["actors"](0.0)
        balls = [o for o in objs if o["k"] == "e" and np.allclose(o["r"], (0.1, 0.1, 0.1))]
        self.assertTrue(balls)
        self.assertTrue(all(tuple(o["col"]) == EP2.BALL_RED for o in balls))

    def test_backdrop_sits_behind_every_camera(self):
        for s in EP2.SHOTS:
            cam, look, _fov = s["camera"](0.0)
            self.assertGreater(cam[2], 0.0, s["id"])
            self.assertLess(look[2], cam[2], s["id"])
        hedges = [o for o in EP2.garden_scene()
                  if o["k"] == "e" and np.allclose(o["r"], (3.0, 1.1, 0.9))]
        self.assertEqual(len(hedges), 6)
        self.assertTrue(all(o["c"][2] < 0.0 for o in hedges))

    def test_no_zero_sized_primitive_in_any_shot(self):
        for s in EP2.SHOTS:
            for k in range(0, int(s["dur"] * 2) + 1):
                for o in s["actors"](k / 2):
                    if o["k"] == "e":
                        self.assertTrue(all(abs(float(v)) > 0 for v in o["r"]),
                                        (s["id"], k / 2, o["c"], o["r"]))

    def test_frame_at_is_deterministic(self):
        a = EP2.frame_at(46.0, 64, 36)
        b = EP2.frame_at(46.0, 64, 36)
        self.assertTrue(np.array_equal(a, b))


class TestSyncMeasurement(unittest.TestCase):
    """Regression for the rounded-hop drift found on the 158 s episode."""
    V = _load("verify_video")

    def _thumps(self, times, dur, sr=44100, lag=0.0):
        rng = np.random.default_rng(1)
        x = 0.02 * rng.standard_normal(int(dur * sr))
        seg = np.arange(int(0.07 * sr)) / sr
        thump = 0.5 * np.sin(2 * np.pi * 140 * seg) * np.exp(-seg * 60)
        for t in times:
            i = int((t + lag) * sr)
            x[i:i + len(seg)] += thump
        return x.astype(np.float32)

    def test_late_footsteps_in_a_long_track_are_measured_exactly(self):
        times = [5.0, 80.0, 150.0, 157.0]
        offs, missed = self.V.footstep_offsets(self._thumps(times, 158.0), 44100, times)
        self.assertEqual(missed, [])
        self.assertLess(max(abs(o) for o in offs), 0.006)

    def test_a_real_lag_is_reported_not_hidden(self):
        times = [10.0, 120.0]
        offs, _ = self.V.footstep_offsets(self._thumps(times, 130.0, lag=0.03), 44100, times)
        for o in offs:
            self.assertAlmostEqual(o, 0.03, delta=0.006)

    def test_missing_footstep_is_missed_not_measured_from_noise(self):
        offs, missed = self.V.footstep_offsets(self._thumps([10.0], 30.0), 44100, [10.0, 20.0])
        self.assertEqual(missed, [20.0])


if __name__ == "__main__":
    unittest.main()

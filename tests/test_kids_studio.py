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


if __name__ == "__main__":
    unittest.main()

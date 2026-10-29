"""kids_studio/tools/check_subtitles.py catches each timing and readability
fault, and the two verified episodes pass. Synthetic cues only, except the
check of the committed episode subtitle files."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "kids_studio" / "tools"))
import check_subtitles as cs  # noqa: E402


def srt(*cues):
    return "\n\n".join("%d\n%s --> %s\n%s" % (i, a, b, t) for i, (a, b, t) in enumerate(cues, start=1)) + "\n"


class Subtitles(unittest.TestCase):
    def issues(self, text, duration=None):
        return [i["issue"] for i in cs.check(text, duration)["issues"]]

    def test_clean_cues_pass(self):
        out = cs.check(srt(("00:00:00,000", "00:00:02,000", "مَرْحَبًا"), ("00:00:03,000", "00:00:05,000", "هَيَّا")), 10)
        self.assertTrue(out["passed"])
        self.assertEqual(out["issues"], [])

    def test_overlap_and_reversed_cues_fail(self):
        text = srt(("00:00:00,000", "00:00:03,000", "a"), ("00:00:02,000", "00:00:04,000", "b"),
                   ("00:00:06,000", "00:00:05,000", "c"))
        got = self.issues(text)
        self.assertIn("overlaps the previous cue", got)
        self.assertIn("ends at or before it starts", got)

    def test_a_cue_after_the_episode_ends_fails(self):
        self.assertTrue(any("ends after the episode" in i for i in
                            self.issues(srt(("00:00:08,000", "00:00:12,000", "x")), 10)))

    def test_fast_or_short_cues_warn(self):
        text = srt(("00:00:00,000", "00:00:00,500", "قصير"),
                   ("00:00:01,000", "00:00:02,000", "هذه جملة طويلة جدا لطفل صغير يقرؤها"))
        out = cs.check(text, 10)
        self.assertTrue(out["passed"])
        self.assertEqual(out["warnings"], 2)

    def test_diacritics_do_not_count_toward_reading_speed(self):
        plain = cs.check(srt(("00:00:00,000", "00:00:01,000", "الكرة")), 5)
        vowelled = cs.check(srt(("00:00:00,000", "00:00:01,000", "الْكُرَةُ")), 5)
        self.assertEqual(plain["warnings"], vowelled["warnings"])

    def test_numbering_gap_fails(self):
        text = "1\n00:00:00,000 --> 00:00:01,000\na\n\n3\n00:00:02,000 --> 00:00:03,000\nb\n"
        self.assertTrue(any("cue number 3" in i for i in self.issues(text)))

    def test_the_two_verified_episodes_pass(self):
        for srt_name, verify in (("ep01_animatic.ar.srt", "ep01_animatic"), ("ep02_lulus_lost_ball.ar.srt", "ep02_lulus_lost_ball")):
            p = ROOT / "kids_studio" / "renders" / srt_name
            v = ROOT / "kids_studio" / "renders" / (verify + ".verify.json")
            if not p.exists() or not v.exists():
                self.skipTest("render files not present")
            duration = json.loads(v.read_text(encoding="utf-8"))["container_duration_s"]
            self.assertTrue(cs.check(p.read_text(encoding="utf-8-sig"), duration)["passed"], srt_name)


if __name__ == "__main__":
    unittest.main()

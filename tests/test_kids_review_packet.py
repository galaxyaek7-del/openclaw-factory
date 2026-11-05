import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import kids_review_packet as kp  # noqa: E402


def test_cues_parse_time_and_text():
    srt = "1\n00:00:00,000 --> 00:00:05,000\nمرحبا\n\n2\n00:00:12,000 --> 00:00:14,000\nسطر أول\nسطر ثان\n"
    assert kp.cues(srt) == [("00:00:00", "مرحبا"), ("00:00:12", "سطر أول سطر ثان")]


def test_sheet_never_approves_and_binds_to_the_file(tmp_path):
    (tmp_path / "v.mp4").write_bytes(b"abc")
    (tmp_path / "s.srt").write_text("1\n00:00:01,000 --> 00:00:02,000\nجملة\n", encoding="utf-8")
    ep = {"episode": "e1", "video": "v.mp4", "verify": "none.json", "subtitles": "s.srt", "title": "T", "description": "D", "tags": ["a"]}
    text = kp.sheet(ep, root=tmp_path)
    assert kp.sha256(tmp_path / "v.mp4") in text and "جملة" in text
    assert "--child-safety-reviewed --arabic-reviewed" in text and "لا يكتبه الوكيل" in text
    assert not (tmp_path / "data").exists()  # nothing written but the returned text

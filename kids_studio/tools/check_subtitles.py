#!/usr/bin/env python3
"""Subtitle timing and readability check for Kids Studio episodes (2026-10-29).

verify_video.py confirms an Arabic subtitle track exists with the expected
number of cues. This checks what it does not: cue numbering and order, end
after start, no overlaps, every cue inside the episode, a minimum time on
screen, and a reading speed suited to young viewers.

The readability limits are a disclosed guideline for ages 4-8 (adjustable
below), not an established standard: diacritics are excluded from the count,
since fully vowelled text has many more characters for the same words.

    python kids_studio/tools/check_subtitles.py kids_studio/renders/ep02_lulus_lost_ball.ar.srt 130.0
"""
import json
import re
import sys

MIN_SECONDS = 1.0           # shortest time a cue should stay on screen
MAX_CHARS_PER_SECOND = 12   # base letters per second (diacritics excluded)
DIACRITICS = re.compile(r"[ً-ْٰ]")
TIME = re.compile(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})")


def _seconds(t):
    m = TIME.fullmatch(t.strip())
    if not m:
        raise ValueError("bad timestamp %r" % t)
    h, mi, s, ms = map(int, m.groups())
    return h * 3600 + mi * 60 + s + ms / 1000.0


def parse(text):
    cues = []
    for block in re.split(r"\r?\n\s*\r?\n", text.strip()):
        lines = [l for l in block.splitlines() if l.strip()]
        if len(lines) < 2:
            continue
        idx = lines[0].strip()
        start, _, end = lines[1].partition("-->")
        cues.append({"index": idx, "start": start.strip(), "end": end.strip(), "text": " ".join(lines[2:]).strip()})
    return cues


def check(text, duration_s=None):
    issues = []
    cues = parse(text)
    if not cues:
        return {"cues": 0, "issues": [{"severity": "error", "cue": None, "issue": "no cues"}], "passed": False}
    prev_end = None
    for n, c in enumerate(cues, start=1):
        where = c["index"]
        if c["index"] != str(n):
            issues.append({"severity": "error", "cue": where, "issue": "cue number %s where %d expected" % (c["index"], n)})
        try:
            s, e = _seconds(c["start"]), _seconds(c["end"])
        except ValueError as exc:
            issues.append({"severity": "error", "cue": where, "issue": str(exc)})
            continue
        if e <= s:
            issues.append({"severity": "error", "cue": where, "issue": "ends at or before it starts"})
        if prev_end is not None and s < prev_end:
            issues.append({"severity": "error", "cue": where, "issue": "overlaps the previous cue"})
        if duration_s is not None and e > duration_s + 0.05:
            issues.append({"severity": "error", "cue": where, "issue": "ends after the episode (%.2f s > %.2f s)" % (e, duration_s)})
        if not c["text"]:
            issues.append({"severity": "error", "cue": where, "issue": "empty text"})
        length = e - s
        if 0 < length < MIN_SECONDS:
            issues.append({"severity": "warning", "cue": where, "issue": "on screen %.2f s (< %.1f s)" % (length, MIN_SECONDS)})
        letters = len(re.sub(r"\s", "", DIACRITICS.sub("", c["text"])))
        if length > 0 and letters / length > MAX_CHARS_PER_SECOND:
            issues.append({"severity": "warning", "cue": where,
                           "issue": "%.1f letters per second (> %d)" % (letters / length, MAX_CHARS_PER_SECOND)})
        prev_end = e
    return {"cues": len(cues), "issues": issues, "passed": not any(i["severity"] == "error" for i in issues),
            "warnings": sum(1 for i in issues if i["severity"] == "warning"),
            "limits": {"min_seconds": MIN_SECONDS, "max_letters_per_second": MAX_CHARS_PER_SECOND}}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__)
        return 2
    text = open(argv[0], encoding="utf-8-sig").read()
    out = check(text, float(argv[1]) if len(argv) > 1 else None)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if out["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())

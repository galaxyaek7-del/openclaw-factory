"""Technical verification of a rendered video using only the bundled FFmpeg.

    python -m video_studio.verify_media <video.mp4> [--expect vertical|landscape] [--build <build.json>]

There is no ffprobe in the bundle, so stream facts are read from FFmpeg's own
banner, and content checks run real filters over a full decode:
  * decode errors       (-v error over the whole file)
  * black stretches     (blackdetect)
  * frozen stretches    (freezedetect, longer than the longest planned still)
  * silence             (silencedetect) and loudness (volumedetect)
  * subtitle stream     present, and cue timing inside the video duration
Returns a report dict with "passed" and a list of "failures"; nothing here
changes the file.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from video_studio.narrated import FORMATS, ffmpeg_exe

MAX_SILENCE_S = 1.5          # a pause longer than this inside narration is a defect
MIN_MEAN_DB, MAX_PEAK_DB = -35.0, -0.1
MAX_CUE_OFFSET_S = 0.30      # subtitle end vs measured end of speech


def _run(args, timeout=600):
    p = subprocess.run([ffmpeg_exe(), "-hide_banner", *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout, stdin=subprocess.DEVNULL)
    return p.returncode, p.stderr


def probe(path):
    _, err = _run(["-i", str(path)])
    info = {"video": None, "audio": None, "subtitle": False, "duration_s": None}
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    if m:
        info["duration_s"] = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])
    for line in err.splitlines():
        if "Stream #" not in line:
            continue
        if "Video:" in line:
            r = re.search(r"(\d{3,5})x(\d{3,5})", line)
            fps = re.search(r"([\d.]+) fps", line)
            info["video"] = {"codec": line.split("Video:")[1].split()[0].strip(","), "width": int(r[1]), "height": int(r[2]),
                             "fps": float(fps[1]) if fps else None, "yuv420p": "yuv420p" in line}
        elif "Audio:" in line:
            hz = re.search(r"(\d+) Hz", line)
            info["audio"] = {"codec": line.split("Audio:")[1].split()[0].strip(","), "sample_rate": int(hz[1]) if hz else None}
        elif "Subtitle:" in line:
            info["subtitle"] = True
    return info


def analyse(path, freeze_s):
    rc, err = _run(["-v", "info", "-i", str(path),
                    "-vf", f"blackdetect=d=0.5:pix_th=0.05,freezedetect=n=0.001:d={freeze_s:.2f}",
                    "-af", f"silencedetect=n=-50dB:d={MAX_SILENCE_S},volumedetect", "-f", "null", "-"], timeout=1200)
    blacks = [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", err)]
    freezes = [float(x) for x in re.findall(r"freeze_duration: ([\d.]+)", err)]
    silences = [float(x) for x in re.findall(r"silence_duration: ([\d.]+)", err)]
    mean = re.search(r"mean_volume: (-?[\d.]+) dB", err)
    peak = re.search(r"max_volume: (-?[\d.]+) dB", err)
    rc2, err2 = _run(["-v", "error", "-i", str(path), "-f", "null", "-"], timeout=1200)
    return {"black_segments": blacks, "freeze_durations": freezes, "silence_durations": silences,
            "mean_volume_db": float(mean[1]) if mean else None, "max_volume_db": float(peak[1]) if peak else None,
            "decode_errors": [l for l in err2.splitlines() if l.strip()][:20], "decode_rc": rc2}


def verify(path, expect=None, build=None):
    path = Path(path)
    failures, info = [], probe(path)
    rec = json.loads(Path(build).read_text(encoding="utf-8")) if build else None
    if not info["video"]:
        failures.append("no video stream")
    if not info["audio"]:
        failures.append("no audio stream")
    if not info["subtitle"]:
        failures.append("no subtitle stream")
    if expect and info["video"]:
        w, h = FORMATS[expect]
        if (info["video"]["width"], info["video"]["height"]) != (w, h):
            failures.append(f"resolution {info['video']['width']}x{info['video']['height']} != {w}x{h}")
    if info["video"] and not info["video"]["yuv420p"]:
        failures.append("pixel format is not yuv420p (poor player compatibility)")
    # longest planned still = longest sentence clip; a freeze beyond it is a defect
    longest = max((c["end"] - c["start"] for c in rec["cues"]), default=10.0) + 1.0 if rec else 15.0
    a = analyse(path, longest)
    if a["decode_errors"] or a["decode_rc"]:
        failures.append(f"decode errors: {a['decode_errors'][:3]}")
    long_black = [s for s in a["black_segments"] if s[1] - s[0] > 0.6]
    if long_black:
        failures.append(f"black stretches: {long_black}")
    if a["freeze_durations"]:
        failures.append(f"frozen stretches longer than {longest:.1f}s: {a['freeze_durations']}")
    if a["silence_durations"]:
        failures.append(f"silences longer than {MAX_SILENCE_S}s: {a['silence_durations']}")
    if a["mean_volume_db"] is None or a["mean_volume_db"] < MIN_MEAN_DB:
        failures.append(f"narration too quiet: mean {a['mean_volume_db']} dB")
    if a["max_volume_db"] is not None and a["max_volume_db"] > MAX_PEAK_DB:
        failures.append(f"clipping risk: peak {a['max_volume_db']} dB")
    if rec:
        if abs((info["duration_s"] or 0) - rec["duration_s"]) > 0.25:
            failures.append(f"duration {info['duration_s']} differs from build {rec['duration_s']}")
        bad = [c for c in rec["cues"] if c["end"] > rec["duration_s"] + 0.01 or c["start"] >= c["end"]]
        if bad:
            failures.append(f"subtitle cues outside the video: {bad[:2]}")
        overlap = [i for i in range(1, len(rec["cues"])) if rec["cues"][i]["start"] < rec["cues"][i - 1]["end"]]
        if overlap:
            failures.append(f"overlapping subtitle cues at {overlap}")
        # subtitle sync, measured: each cue should end where the speech actually stops
        _, err = _run(["-i", str(path), "-vn", "-af", "silencedetect=n=-45dB:d=0.2", "-f", "null", "-"])
        starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
        if starts and rec["cues"]:
            offs = [min(abs(c["end"] - s) for s in starts) for c in rec["cues"]]
            a["subtitle_end_offset_ms"] = {"max": round(max(offs) * 1000), "mean": round(sum(offs) / len(offs) * 1000)}
            if max(offs) > MAX_CUE_OFFSET_S:
                failures.append(f"subtitle cues end up to {max(offs) * 1000:.0f} ms away from the speech")
        hits = [f for f in rec["frames"] if f["content_bottom"] > f["subtitle_box"][0]]
        if hits:
            failures.append(f"{len(hits)} frame(s) where content runs into the subtitle box")
        if rec.get("video_sha256"):
            import hashlib
            if hashlib.sha256(path.read_bytes()).hexdigest() != rec["video_sha256"]:
                failures.append("file hash differs from the build record")
    return {"file": str(path), "probe": info, "analysis": a, "failures": failures, "passed": not failures}


if __name__ == "__main__":
    args = sys.argv[1:]
    expect = args[args.index("--expect") + 1] if "--expect" in args else None
    build = args[args.index("--build") + 1] if "--build" in args else None
    r = verify(args[0], expect, build)
    print(json.dumps(r, indent=1))
    sys.exit(0 if r["passed"] else 1)

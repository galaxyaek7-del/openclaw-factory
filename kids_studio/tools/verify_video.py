"""Decode a Kids Studio render and check it, rather than trusting metadata.

Checks: container/stream info, full decode with zero errors, every frame
decoded and none black, blank or frozen beyond intended holds, audio peak and
loudness, audio/video duration match, and footstep sync against the
build's own footfall schedule (<build>.build.json), within one frame.

    python kids_studio/tools/verify_video.py kids_studio/renders/ep01_sc01_poc.mp4
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np


def run(cmd, binary=False, timeout=None):
    # stdin=DEVNULL: FFmpeg reads stdin for keystrokes. Inherited, it swallowed
    # the next JSON-RPC request when this ran inside the MCP pilot (2026-10-15).
    p = subprocess.run(cmd, capture_output=True, timeout=timeout, stdin=subprocess.DEVNULL)
    return p.returncode, p.stdout if binary else p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def footstep_offsets(x, sr, expected, window=0.06, band=(100, 200), min_snr=4.0):
    """Measured onset minus expected time for each footstep (seconds).

    Footsteps are 140 Hz thumps: isolate the band, build a block envelope, and
    find the first crossing of half the local peak near each expected time.
    Block times use the EXACT block length (hop / sr). The first version used
    a rounded 5 ms and drifted 2.3 ms per second -- 0.34 s by the end of a
    158 s episode -- so late footsteps fell outside the window and noise was
    measured instead (fixed 2026-10-15). A footstep whose peak is not clearly
    above the local background is reported as missed, never measured from noise.
    """
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / sr)
    X[(f < band[0]) | (f > band[1])] = 0
    b = np.abs(np.fft.irfft(X, len(x)))
    hop = int(0.005 * sr)
    step = hop / sr                                   # exact block duration
    nblk = len(b) // hop
    env = b[: nblk * hop].reshape(nblk, hop).max(axis=1)
    offsets, missed = [], []
    for t in expected:
        i0 = max(int(np.floor((t - window) / step)), 0)
        i1 = min(int(np.ceil((t + window) / step)) + 1, nblk)
        seg = env[i0:i1]
        bg = env[max(i0 - int(0.3 / step), 0):i0]
        if len(seg) == 0 or len(bg) == 0 or seg.max() < min_snr * np.median(bg):
            missed.append(t)
            continue
        on = int(np.argmax(seg >= 0.5 * seg.max()))
        offsets.append((i0 + on) * step - t)
    return offsets, missed


def analyze(path, timeout=None):
    """Decode and check `path`; return the report. Writes nothing.

    Kept separate from main() so a read-only caller (the MCP pilot) can verify
    a render without overwriting its .verify.json. `timeout` bounds every
    FFmpeg call, in seconds.
    """
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    path = Path(path)
    rep = {"file": str(path), "bytes": path.stat().st_size, "checks": {}}
    C = rep["checks"]

    _, _, info = run([ff, "-hide_banner", "-i", str(path)], timeout=timeout)
    dur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", info)
    v = re.search(r"Video: (\w+).*?, (\d+)x(\d+).*?, ([\d.]+) fps", info)
    a = re.search(r"Audio: (\w+).*?, (\d+) Hz", info)
    rep["container_duration_s"] = int(dur[1]) * 3600 + int(dur[2]) * 60 + float(dur[3]) if dur else None
    rep["video"] = {"codec": v[1], "width": int(v[2]), "height": int(v[3]), "fps": float(v[4])} if v else None
    rep["audio"] = {"codec": a[1], "sample_rate": int(a[2])} if a else None
    C["has_video_and_audio"] = bool(v and a)

    code, _, err = run([ff, "-v", "error", "-i", str(path), "-f", "null", "-"], timeout=timeout)
    C["full_decode_without_errors"] = code == 0 and not err.strip()
    rep["decode_errors"] = err.strip()[:500]

    w, h = 160, 90
    _, raw, _ = run([ff, "-v", "error", "-i", str(path), "-vf", f"scale={w}:{h}", "-f", "rawvideo",
                     "-pix_fmt", "gray", "-"], binary=True, timeout=timeout)
    frames = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)
    rep["decoded_frames"] = int(len(frames))
    means = frames.mean(axis=(1, 2))
    stds = frames.std(axis=(1, 2))
    C["no_black_or_blank_frames"] = bool((means > 8).all() and (stds > 4).all())
    diffs = np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2))
    still = diffs < 0.02
    longest, run_ = 0, 0
    for s in still:
        run_ = run_ + 1 if s else 0
        longest = max(longest, run_)
    rep["longest_identical_run_frames"] = int(longest)
    rep["frames_with_motion"] = int((~still).sum())
    fps = rep["video"]["fps"] if rep["video"] else 24
    C["no_frozen_stretch_over_2s"] = longest < 2 * fps

    sr = 44100
    _, pcm, _ = run([ff, "-v", "error", "-i", str(path), "-f", "s16le", "-ac", "1", "-ar", str(sr), "-"], binary=True, timeout=timeout)
    x = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
    rep["audio_duration_s"] = round(len(x) / sr, 3)
    rep["video_duration_s"] = round(len(frames) / fps, 3)
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    rms = float(np.sqrt(np.mean(x ** 2))) if len(x) else 0.0
    rep["audio_peak_dbfs"] = round(20 * np.log10(max(peak, 1e-9)), 1)
    rep["audio_rms_dbfs"] = round(20 * np.log10(max(rms, 1e-9)), 1)
    C["audio_peak_below_minus_1_dbfs"] = rep["audio_peak_dbfs"] < -1.0
    C["audio_not_silent"] = rep["audio_rms_dbfs"] > -45
    C["audio_video_duration_match_within_50ms"] = abs(rep["audio_duration_s"] - rep["video_duration_s"]) <= 0.05

    build = path.with_name(path.stem + ".build.json")
    if build.exists() and len(x):
        expected = json.loads(build.read_text(encoding="utf-8")).get("footstep_times_s", [])
        offsets, missed = footstep_offsets(x, sr, expected)
        rep["footsteps_expected"] = len(expected)
        rep["footsteps_measured"] = len(offsets)
        rep["footsteps_not_detected"] = missed
        rep["sync_offset_ms"] = {"median": round(float(np.median(offsets)) * 1000, 1) if offsets else None,
                                 "max_abs": round(float(np.max(np.abs(offsets))) * 1000, 1) if offsets else None}
        C["footstep_sync_within_one_frame"] = (bool(offsets) and not missed
                                               and float(np.max(np.abs(offsets))) <= 1 / fps)
    else:
        C["footstep_sync_within_one_frame"] = None

    # subtitle track, when the build declares one
    if build.exists():
        want = json.loads(build.read_text(encoding="utf-8")).get("subtitle_cues")
        if want is not None:
            has = bool(re.search(r"Subtitle: mov_text", info))
            lang = bool(re.search(r"\(ara\).*Subtitle|Subtitle.*\(ara\)", info)) or bool(re.search(r"Stream #0:\d+\(ara\): Subtitle", info))
            _, srt_txt, _ = run([ff, "-v", "error", "-i", str(path), "-map", "0:s:0", "-f", "srt", "-"], timeout=timeout)
            cues = len(re.findall(r"^\d+\s*$", srt_txt, re.M)) if has else 0
            arabic = bool(re.search(r"[؀-ۿ]", srt_txt))
            first = re.search(r"-->[^\n]*\r?\n(.+)", srt_txt)
            rep["subtitles"] = {"stream": has, "language_ara": lang, "cues": cues, "expected": want,
                                "arabic_text": arabic, "first_cue_text": first[1].strip()[:120] if first else None}
            C["arabic_subtitle_track_complete"] = has and lang and arabic and cues == want

    for k, v in C.items():          # numpy bools are not JSON-serialisable
        C[k] = None if v is None else bool(v)
    rep["verdict"] = "PASS" if all(v is not False for v in C.values()) else "FAIL"
    return rep


def main(path):
    path = Path(path)
    rep = analyze(path)
    out = path.with_name(path.stem + ".verify.json")
    out.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(json.dumps(rep, indent=1))
    return 0 if rep["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))

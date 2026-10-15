"""Build the Episode 1 ANIMATIC: all 14 storyboard shots, cut, scored, subtitled.

ANIMATIC means a timing and staging preview in the primitive 3D style, with
no voices: the Arabic dialogue appears as a soft subtitle track taken from
script_ar.md. It is not the finished episode.

Steps: render every frame in parallel -> synthesise the soundtrack (original
music, brook, footsteps tied to the walk cycles, plank creaks) -> write an
Arabic SRT -> mux H.264 + AAC + mov_text subtitles with FFmpeg -> write a
build report that verify_video.py checks against.

No network calls, no external assets.

    python kids_studio/tools/build_episode.py [--fps 12 --workers 4]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import time
import wave
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image

TOOLS = Path(__file__).resolve().parent
OUT = TOOLS.parent / "renders"
NAME = "ep01_animatic"
SR = 44100
_EP = None


def _load_ep():
    spec = importlib.util.spec_from_file_location("ep01_shots", TOOLS / "ep01_shots.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _init_worker():
    global _EP
    _EP = _load_ep()


def _render_one(job):
    f, fps, W, H, fdir = job
    img = _EP.frame_at(f / fps, W, H)
    Image.fromarray(img).save(Path(fdir) / f"{f:05d}.png")
    return f


def _tone(seg, f, decay):
    return np.exp(-seg * decay) * (np.sin(2 * np.pi * f * seg) + 0.25 * np.sin(4 * np.pi * f * seg))


def soundtrack(ep, total):
    rng = np.random.default_rng(15)
    n = int(SR * total)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    brook = np.convolve(noise, np.ones(60) / 60, mode="same") * 0.9
    brook *= 0.6 + 0.4 * np.sin(2 * np.pi * 0.23 * t)
    # original melody: the PoC's pentatonic phrase, varied each 12 s block
    phrase = [(0.5, 72), (1.25, 76), (2.0, 79), (2.75, 76), (3.5, 74), (4.25, 72),
              (5.0, 69), (5.75, 72), (6.5, 74), (7.25, 76), (8.0, 79), (9.0, 81),
              (9.75, 79), (10.5, 76), (11.0, 72)]
    shift = [0, 0, -3, 2, 0, -5, 0, 2, 0, 0, -3, 0, 0, 0]
    mel = np.zeros(n)
    for b in range(int(np.ceil(total / 12))):
        for st, midi in phrase:
            start = b * 12 + st
            if start >= total - 0.5:
                continue
            f = 440 * 2 ** ((midi + shift[b % len(shift)] - 69) / 12)
            i0 = int(start * SR)
            seg = np.arange(min(int(0.9 * SR), n - i0)) / SR
            env = np.minimum(seg / 0.02, 1.0)
            mel[i0:i0 + len(seg)] += env * _tone(seg, f, 3.2)
    steps, creak = np.zeros(n), np.zeros(n)
    step_times, creak_times = [], []
    for t0, s in ep.timeline()[0]:
        step_times += [round(t0 + x, 4) for x in s["steps"]]
        creak_times += [t0 + x for x in s["creaks"]]
    for ft in step_times:
        i0 = int(ft * SR)
        seg = np.arange(int(0.07 * SR)) / SR
        thump = np.sin(2 * np.pi * 140 * seg) * np.exp(-seg * 60)
        steps[i0:i0 + len(seg)] += thump[: max(0, min(len(seg), n - i0))]
    for ct in creak_times:          # soft wooden creak: a short downward glide, never loud
        i0 = int(ct * SR)
        seg = np.arange(int(0.45 * SR)) / SR
        f = 620 - 140 * seg / seg[-1]
        c = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-seg * 7) * (0.5 + 0.5 * np.sin(2 * np.pi * 23 * seg))
        creak[i0:i0 + len(seg)] += c[: max(0, min(len(seg), n - i0))]
    mix = 0.10 * brook + 0.16 * mel + 0.55 * steps + 0.12 * creak
    fade = np.minimum(np.minimum(t / 0.5, 1.0), np.minimum((total - t) / 1.5, 1.0))
    mix *= fade
    mix *= 0.5 / max(1e-9, np.max(np.abs(mix)))
    return mix, step_times, creak_times


def srt(ep, total):
    def ts(x):
        ms = int(round(x * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    cues = []
    for t0, s in ep.timeline()[0]:
        for a, b, line in s["subs"]:
            if t0 + a < total - 0.2:          # only lines inside the rendered cut
                cues.append((t0 + a, min(t0 + b, total - 0.05), line))
    body = "".join(f"{i}\n{ts(a)} --> {ts(b)}\n{line}\n\n" for i, (a, b, line) in enumerate(cues, 1))
    return body, len(cues)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fps", type=int, default=12)
    ap.add_argument("--width", type=int, default=640)
    ap.add_argument("--height", type=int, default=360)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seconds", type=float, default=0, help="only the first N seconds (test)")
    args = ap.parse_args()
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    ep = _load_ep()
    _, total = ep.timeline()
    if args.seconds:
        total = min(total, args.seconds)
    nframes = int(round(total * args.fps))
    OUT.mkdir(parents=True, exist_ok=True)
    fdir = OUT / f"{NAME}_frames"
    if fdir.exists():
        shutil.rmtree(fdir)
    fdir.mkdir()
    t0 = time.time()
    jobs = [(f, args.fps, args.width, args.height, str(fdir)) for f in range(nframes)]
    with Pool(args.workers, initializer=_init_worker) as pool:
        for k, _ in enumerate(pool.imap_unordered(_render_one, jobs, chunksize=4), 1):
            if k % 120 == 0:
                print(f"frames {k}/{nframes}  {time.time() - t0:.0f}s", flush=True)
    render_s = time.time() - t0
    mix, step_times, creak_times = soundtrack(ep, nframes / args.fps)
    wav = OUT / f"{NAME}.wav"
    pcm = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    body, ncues = srt(ep, nframes / args.fps)
    srt_path = OUT / f"{NAME}.ar.srt"
    srt_path.write_text(body, encoding="utf-8")
    mp4 = OUT / f"{NAME}.mp4"
    t1 = time.time()
    subprocess.run([ff, "-y", "-loglevel", "error", "-framerate", str(args.fps), "-i", str(fdir / "%05d.png"),
                    "-i", str(wav), "-i", str(srt_path),
                    "-map", "0:v", "-map", "1:a", "-map", "2:s",
                    "-vf", "scale=1280:720:flags=lanczos,format=yuv420p",
                    "-c:v", "libx264", "-crf", "20", "-preset", "medium",
                    "-c:a", "aac", "-b:a", "160k", "-c:s", "mov_text",
                    "-metadata:s:s:0", "language=ara", "-metadata", "title=ANIMATIC - Nunu and the Little Bridge (no voices)",
                    # explicit duration: -shortest mis-cuts when a subtitle stream is mapped
                    "-t", f"{nframes / args.fps:.3f}", "-movflags", "+faststart", str(mp4)], check=True)
    meta = {"name": NAME, "label": "ANIMATIC: primitive 3D, no voices, Arabic soft subtitles",
            "shots": [{"id": s["id"], "start_s": round(a, 2), "dur_s": s["dur"]} for a, s in ep.timeline()[0]],
            "frames": nframes, "fps": args.fps, "render_resolution": [args.width, args.height],
            "output_resolution": [1280, 720], "workers": args.workers,
            "render_seconds": round(render_s, 1), "encode_seconds": round(time.time() - t1, 1),
            "footstep_times_s": step_times, "creak_times_s": [round(x, 3) for x in creak_times],
            "subtitle_cues": ncues, "network_calls": 0, "external_assets": 0}
    (OUT / f"{NAME}.build.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: meta[k] for k in ("frames", "fps", "render_seconds", "encode_seconds", "subtitle_cues")}, indent=1))


if __name__ == "__main__":
    sys.exit(main())

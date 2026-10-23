"""Render a narrated explainer video from a project manifest (JSON).

    python -m video_studio.narrated video_studio/projects/<id>.json

Pipeline, all local: every sentence is spoken separately (video_studio.tts)
so its real duration is known; a still frame is drawn per sentence (Pillow)
with the scene heading, the scene's visual and the sentence as a burned-in
subtitle; each frame becomes a clip of exactly that duration with a slow zoom;
clips are concatenated; the audio is concatenated with the same timings; an
SRT track built from the same timings is muxed as a soft subtitle. Output and
a build record (inputs hash, durations, tools) go to video_studio/output/<id>/
(git-ignored). Re-running with the same manifest reproduces the same video.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
FORMATS = {"vertical": (1080, 1920), "landscape": (1920, 1080)}
FPS = 30
PAUSE_S = 0.35
FONT_DIR = Path("C:/Windows/Fonts")


def ffmpeg_exe():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def _font(name, size):
    for f in (name, "segoeui.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(str(FONT_DIR / f), size)
        except OSError:
            continue
    return ImageFont.load_default(size)  # no Windows fonts (e.g. Linux CI): Pillow's scalable default


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _wrap(draw, text, font, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= width:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_frame(m, scene_i, sentence_i, path):
    W, H = FORMATS[m["format"]]
    vertical = m["format"] == "vertical"
    pal = m["palette"]
    bg1, bg2, accent, fg = (_hex(pal[k]) for k in ("bg1", "bg2", "accent", "text"))
    img = Image.new("RGB", (W, H), bg1)
    d = ImageDraw.Draw(img)
    for y in range(H):  # vertical gradient
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(bg1[k] + (bg2[k] - bg1[k]) * t) for k in range(3)))
    scene = m["scenes"][scene_i]
    pad = int(W * 0.07)
    s = W / 1080 if vertical else H / 1080
    # brand bar and progress
    d.rectangle([0, 0, W, int(10 * s)], fill=accent)
    d.text((pad, int(40 * s)), m.get("brand", "Galaxy Forge"), font=_font("segoeuib.ttf", int(34 * s)), fill=fg)
    n = len(m["scenes"])
    d.text((W - pad, int(40 * s)), f"{scene_i + 1}/{n}", font=_font("segoeui.ttf", int(34 * s)), fill=fg, anchor="ra")
    header_bottom = int(110 * s)
    # subtitle box (burned in), placed first so the content can be fitted above it
    sub = scene["lines"][sentence_i]
    sfont = _font("segoeuib.ttf", int((54 if vertical else 48) * s))
    lines = _wrap(d, sub, sfont, W - 2 * pad - int(40 * s))
    lh = int(sfont.size * 1.3)
    box_h = lh * len(lines) + int(50 * s)
    top = H - box_h - int((300 if vertical else 70) * s)
    d.rounded_rectangle([pad - int(20 * s), top, W - pad + int(20 * s), top + box_h], radius=int(24 * s), fill=(0, 0, 0))
    ty = top + int(25 * s)
    for line in lines:
        d.text((W // 2, ty), line, font=sfont, fill=(255, 255, 255), anchor="ma")
        ty += lh
    # heading + visual are drawn on their own layer, then centred in the free band
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    hfont = _font("segoeuib.ttf", int((92 if vertical else 88) * s))
    y = 0
    for line in _wrap(ld, scene["heading"], hfont, W - 2 * pad):
        ld.text((pad, y), line, font=hfont, fill=fg)
        y += int(hfont.size * 1.18)
    y += int(55 * s)
    v = scene.get("visual") or {}
    vt = v.get("type")
    if vt == "stat":
        sf = _font("segoeuib.ttf", int((260 if vertical else 230) * s))
        ld.text((pad, y), v["value"], font=sf, fill=accent)
        y += int(sf.size * 1.15)
        lf = _font("segoeui.ttf", int((52 if vertical else 54) * s))
        for line in _wrap(ld, v.get("label", ""), lf, W - 2 * pad):
            ld.text((pad, y), line, font=lf, fill=fg)
            y += int(lf.size * 1.3)
    elif vt in ("bullets", "steps"):
        bf = _font("segoeui.ttf", int((60 if vertical else 58) * s))
        active = min(sentence_i, len(v["items"]) - 1) if v.get("progressive") else None
        for k, item in enumerate(v["items"]):
            on = active is None or k <= active
            color = fg if on else tuple(int(c * 0.55 + b * 0.45) for c, b in zip(fg, bg1))
            mark = f"{k + 1}." if vt == "steps" else "\u2022"
            ld.text((pad, y), mark, font=bf, fill=accent if on else color)
            for line in _wrap(ld, item, bf, W - 2 * pad - int(80 * s)):
                ld.text((pad + int(80 * s), y), line, font=bf, fill=color)
                y += int(bf.size * 1.25)
            y += int(28 * s)
    elif vt == "formula":
        ff = _font("consolab.ttf", int((66 if vertical else 78) * s))
        y += int(14 * s)
        for line in v["lines"]:
            box = ld.textbbox((pad, y), line, font=ff)
            ld.rounded_rectangle([pad - 20, y - 14, box[2] + 20, box[3] + 14], radius=int(14 * s), outline=accent, width=4)
            ld.text((pad, y), line, font=ff, fill=fg)
            y += int(ff.size * 1.9)
    bbox = layer.getbbox() or (0, 0, W, 0)
    # the band uses the scene's tallest subtitle so content stays still across the scene's cuts
    max_lines = max(len(_wrap(d, x, sfont, W - 2 * pad - int(40 * s))) for x in scene["lines"])
    scene_top = H - (lh * max_lines + int(50 * s)) - int((300 if vertical else 70) * s)
    band_top, band_bottom = header_bottom + int(40 * s), scene_top - int(40 * s)
    content_h = bbox[3] - bbox[1]
    # centred in the free band, never above it; if it is too tall it overflows and is reported
    dy = band_top - bbox[1] + max(0, (band_bottom - band_top - content_h) // 2)
    img.paste(layer, (0, dy), layer)
    img.save(path)
    return {"subtitle_lines": len(lines), "subtitle_box": [top, top + box_h],
            "content_top": bbox[1] + dy, "content_bottom": bbox[3] + dy}


def _srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def manifest_hash(m):
    return hashlib.sha256(json.dumps(m, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def build(manifest_path, out_root=OUT, synthesize=None):
    from video_studio import tts
    synthesize = synthesize or tts.synthesize
    m = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if m.get("format") not in FORMATS:
        raise ValueError(f"format must be one of {sorted(FORMATS)}")
    out = Path(out_root) / m["id"]
    work = out / "work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    ff = ffmpeg_exe()
    W, H = FORMATS[m["format"]]
    t, cues, clips, wavs, frames_meta = 0.0, [], [], [], []
    k = 0
    for si, scene in enumerate(m["scenes"]):
        for li, sentence in enumerate(scene["lines"]):
            wav = work / f"s{k:03d}.wav"
            dur = synthesize(sentence, wav, voice=m.get("voice", tts.DEFAULT_VOICE), rate=m.get("rate", 0))
            seg = dur + PAUSE_S
            png = work / f"s{k:03d}.png"
            frames_meta.append(draw_frame(m, si, li, png))
            nframes = max(1, round(seg * FPS))
            clip = work / f"s{k:03d}.mp4"
            fade = []
            if li == 0:
                fade.append("fade=t=in:st=0:d=0.25")
            if li == len(scene["lines"]) - 1:
                fade.append(f"fade=t=out:st={max(0.0, nframes / FPS - 0.25):.3f}:d=0.25")
            vf = (f"scale={W * 2}:{H * 2},zoompan=z='min(1+0.00025*on,1.04)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                  f":d={nframes}:s={W}x{H}:fps={FPS}" + ("," + ",".join(fade) if fade else "") + ",format=yuv420p")
            subprocess.run([ff, "-y", "-loglevel", "error", "-loop", "1", "-i", str(png), "-vf", vf, "-frames:v", str(nframes),
                            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", str(FPS), str(clip)],
                           check=True, stdin=subprocess.DEVNULL)
            seg_exact = nframes / FPS
            cues.append((t, t + dur, sentence))
            wavs.append((wav, seg_exact))
            clips.append(clip)
            t += seg_exact
            k += 1
    # audio: each sentence padded with silence to its clip's exact length
    full = work / "narration.wav"
    with wave.open(str(wavs[0][0]), "rb") as w0:
        params = w0.getparams()
    with wave.open(str(full), "wb") as out_w:
        out_w.setparams(params)
        for wav, seg in wavs:
            with wave.open(str(wav), "rb") as w:
                data = w.readframes(w.getnframes())
            out_w.writeframes(data)
            pad_frames = int(round(seg * params.framerate)) - len(data) // (params.sampwidth * params.nchannels)
            out_w.writeframes(b"\x00" * max(0, pad_frames) * params.sampwidth * params.nchannels)
    srt = out / f"{m['id']}.srt"
    srt.write_text("\n".join(f"{i + 1}\n{_srt_time(a)} --> {_srt_time(b)}\n{txt}\n" for i, (a, b, txt) in enumerate(cues)), encoding="utf-8")
    lst = work / "clips.txt"
    lst.write_text("".join(f"file '{c.as_posix()}'\n" for c in clips), encoding="utf-8")
    video = out / f"{m['id']}.mp4"
    subprocess.run([ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(full), "-i", str(srt),
                    "-map", "0:v", "-map", "1:a", "-map", "2:s", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
                    "-c:s", "mov_text", "-metadata:s:s:0", f"language={m.get('subtitle_language', 'eng')}",
                    "-movflags", "+faststart", str(video)], check=True, stdin=subprocess.DEVNULL)
    record = {"id": m["id"], "manifest": str(manifest_path), "manifest_sha256": manifest_hash(m), "format": m["format"],
              "resolution": [W, H], "fps": FPS, "sentences": k, "scenes": len(m["scenes"]), "duration_s": round(t, 3),
              "voice": m.get("voice", tts.DEFAULT_VOICE), "ffmpeg": Path(ff).name, "fonts": ["segoeui.ttf", "segoeuib.ttf", "consolab.ttf"],
              "cues": [{"start": round(a, 3), "end": round(b, 3), "text": x} for a, b, x in cues], "frames": frames_meta,
              "video": str(video), "video_sha256": hashlib.sha256(video.read_bytes()).hexdigest()}
    (out / f"{m['id']}.build.json").write_text(json.dumps(record, indent=1, ensure_ascii=False), encoding="utf-8")
    shutil.rmtree(work)
    return record


if __name__ == "__main__":
    r = build(sys.argv[1])
    print(json.dumps({k: r[k] for k in ("id", "format", "resolution", "duration_s", "sentences", "video")}, indent=1))

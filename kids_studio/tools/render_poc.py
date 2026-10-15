"""Kids Studio, Ep01 Shot 01 proof of concept: a procedural 3D test render.

WHAT THIS IS
    A real 3D render (ray-cast geometry, lighting, cast shadows), built only
    from primitives (ellipsoids and boxes) and rendered on the CPU with numpy.
    It is a TECHNICAL TEST SHOT for Shot 01 of the storyboard, not a finished
    film and not production character models.

WHY NO BLENDER
    Blender was not installed on this machine (audit 2026-10-15) and
    installing software needs founder approval. This script needs only
    Python, numpy, Pillow and the FFmpeg binary bundled with imageio-ffmpeg.

GUARANTEES
    * No network calls, no external assets: every shape, colour, note and
      sound is defined in this file (see rights_ledger.json).
    * Deterministic: the same code produces the same frames (seeded RNG).
    * Footstep sounds are scheduled from the same walk-cycle function that
      moves the legs, so audio/video sync can be checked mechanically.

USAGE
    python kids_studio/tools/render_poc.py [--width 640 --height 360 --fps 24]
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import time
import wave
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "renders"
SHOT = "ep01_sc01_poc"
DURATION = 12.0

# --- palette (series bible) -------------------------------------------------
ORANGE = (232, 118, 42)
CREAM = (246, 232, 206)
DARK = (52, 34, 28)
LULU = (237, 235, 230)
PINK = (238, 170, 180)
SCARF = (70, 130, 200)
MIMO_SPINE = (122, 75, 42)
MIMO_FACE = (226, 196, 150)
GRASS = (112, 178, 88)
GRASS_FAR = (138, 192, 120)
WATER = (96, 170, 214)
BED = (150, 128, 96)
WOOD = (168, 116, 70)
WOOD_DARK = (128, 84, 50)
TRUNK = (120, 86, 60)
LEAF = (84, 150, 80)
HILL = (124, 176, 120)


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


# --- animation --------------------------------------------------------------
WALK_START, WALK_END = 0.6, 7.6         # seconds
X_START, X_END = -4.6, -2.2             # stops on the grass, in front of the bridge
STEP_HZ = 1.6                           # leg cycles per second


def smoothstep(a, b, t):
    u = min(max((t - a) / (b - a), 0.0), 1.0)
    return u * u * (3 - 2 * u)


def nunu_state(t):
    """Single source of truth for Nunu's motion; audio uses it too."""
    u = smoothstep(WALK_START, WALK_END, t)
    x = X_START + (X_END - X_START) * u
    walking = WALK_START + 0.3 < t < WALK_END - 0.3
    phase = 2 * math.pi * STEP_HZ * (t - WALK_START)
    amp = 1.0 if walking else 0.0
    return {"x": x, "phase": phase, "amp": amp, "walking": walking}


def footstep_times():
    """Footfall = each leg pair's lift returning to zero (phase = k*pi)."""
    times, k = [], 1
    while True:
        t = WALK_START + k * 0.5 / STEP_HZ
        if t >= WALK_END - 0.3:
            break
        if t > WALK_START + 0.3:
            times.append(round(t, 4))
        k += 1
    return times


# --- scene ------------------------------------------------------------------
def ell(c, r, col, R=None, cast=True):
    return {"k": "e", "c": np.array(c, float), "r": np.array(r, float),
            "R": np.eye(3) if R is None else R, "col": col, "cast": cast}


def box(lo, hi, col, cast=True, tex=None):
    return {"k": "b", "lo": np.array(lo, float), "hi": np.array(hi, float),
            "col": col, "cast": cast, "tex": tex}


def static_scene():
    s = []
    s.append(box((-30, -2, -40), (-1.0, 0.0, 12), GRASS, cast=False))     # near bank
    s.append(box((1.0, -2, -40), (30, 0.0, 12), GRASS, cast=False))       # far bank
    s.append(box((-1.0, -2, -40), (1.0, -0.32, 12), BED, cast=False))     # stream bed
    s.append(box((-1.0, -2, -40), (1.0, -0.14, 12), WATER, cast=False, tex="water"))
    # bridge deck with plank texture, posts and rails
    s.append(box((-1.6, 0.04, -0.45), (1.6, 0.12, 0.45), WOOD, tex="planks"))
    for x in (-1.5, 0.0, 1.5):
        for z in (-0.47, 0.47):
            s.append(box((x - 0.04, 0.12, z - 0.04), (x + 0.04, 0.58, z + 0.04), WOOD_DARK))
    for z in (-0.47, 0.47):
        s.append(box((-1.55, 0.50, z - 0.03), (1.55, 0.56, z + 0.03), WOOD_DARK))
    # olive tree (left, behind) and distant hills
    s.append(box((-4.2, 0.0, -2.9), (-3.95, 1.5, -2.65), TRUNK))
    s += [ell((-4.1, 1.85, -2.8), (0.9, 0.6, 0.8), LEAF),
          ell((-3.5, 1.65, -2.5), (0.55, 0.42, 0.5), LEAF),
          ell((-4.6, 1.6, -2.6), (0.5, 0.4, 0.5), LEAF)]
    s += [ell((-9, -1.5, -22), (11, 5.2, 4), HILL, cast=False),
          ell((7, -2.2, -26), (13, 5.8, 4), HILL, cast=False),
          ell((0, -3.0, -34), (20, 6.5, 4), GRASS_FAR, cast=False)]
    return s


def nunu(t):
    st = nunu_state(t)
    x, ph, a = st["x"], st["phase"], st["amp"]
    bob = 0.025 * a * abs(math.sin(ph))
    y = 0.36 + bob
    parts = [ell((x, y, 0), (0.32, 0.21, 0.2), ORANGE),
             ell((x + 0.17, y - 0.04, 0), (0.13, 0.13, 0.15), CREAM),
             ell((x + 0.30, y + 0.30, 0), (0.18, 0.17, 0.17), ORANGE),
             ell((x + 0.45, y + 0.26, 0), (0.11, 0.06, 0.07), CREAM),
             ell((x + 0.555, y + 0.27, 0), (0.025, 0.025, 0.025), DARK, cast=False)]
    for zs in (1, -1):
        parts.append(ell((x + 0.26, y + 0.50, 0.09 * zs), (0.05, 0.12, 0.035), ORANGE, R=rot_x(0.25 * zs)))
        parts.append(ell((x + 0.43, y + 0.35, 0.075 * zs), (0.022, 0.026, 0.022), DARK, cast=False))
    # legs: diagonal pairs lift in alternation
    for dx, dz, off in ((0.17, 0.10, 0), (-0.17, -0.10, 0), (0.17, -0.10, math.pi), (-0.17, 0.10, math.pi)):
        lift = 0.06 * a * max(0.0, math.sin(ph + off))
        swing = 0.05 * a * math.cos(ph + off)
        parts.append(ell((x + dx + swing, 0.14 + lift, dz), (0.05, 0.14, 0.05), ORANGE))
    # tail sways sideways; a happy double sway after stopping
    sway = 0.35 * math.sin(2 * math.pi * 0.8 * t) if t > WALK_END else 0.18 * math.sin(ph)
    R = rot_y(sway) @ rot_z(0.35)
    tail_c = np.array([x - 0.44, y + 0.10, 0]) + rot_y(sway) @ np.array([-0.05, 0, 0])
    parts.append(ell(tail_c, (0.26, 0.09, 0.09), ORANGE, R=R))
    tip = tail_c + R @ np.array([-0.24, 0, 0])
    parts.append(ell(tip, (0.07, 0.07, 0.07), CREAM))
    return parts


def lulu(t):
    x, z = 2.3, 0.25
    wig = 0.12 * math.sin(2 * math.pi * 1.6 * t) if 7.4 < t < 9.4 else 0.0
    p = [ell((x, 0.30, z), (0.2, 0.26, 0.2), LULU),
         ell((x - 0.04, 0.66, z), (0.16, 0.15, 0.15), LULU),
         ell((x - 0.04, 0.48, z), (0.17, 0.05, 0.17), SCARF),
         ell((x - 0.18, 0.66, z + 0.06), (0.02, 0.025, 0.02), DARK, cast=False),
         ell((x - 0.18, 0.66, z - 0.06), (0.02, 0.025, 0.02), DARK, cast=False),
         ell((x - 0.19, 0.61, z), (0.02, 0.016, 0.02), PINK, cast=False)]
    for zs in (1, -1):
        R = rot_x(0.12 * zs + wig * zs)
        p.append(ell(np.array([x - 0.02, 0.98, z + 0.06 * zs]), (0.045, 0.22, 0.03), LULU, R=R))
        p.append(ell(np.array([x - 0.035, 0.98, z + 0.06 * zs]), (0.02, 0.16, 0.015), PINK, R=R, cast=False))
    return p


def mimo(t):
    x, z = 2.9, -0.15
    hop = 0.08 * max(0.0, math.sin(2 * math.pi * 1.2 * (t - 9.6))) if 9.6 < t < 11.3 else 0.0
    return [ell((x, 0.2 + hop, z), (0.22, 0.18, 0.2), MIMO_SPINE),
            ell((x - 0.17, 0.2 + hop, z), (0.1, 0.1, 0.11), MIMO_FACE),
            ell((x - 0.27, 0.19 + hop, z), (0.025, 0.025, 0.025), DARK, cast=False),
            ell((x - 0.22, 0.25 + hop, z + 0.05), (0.018, 0.02, 0.018), DARK, cast=False),
            ell((x - 0.22, 0.25 + hop, z - 0.05), (0.018, 0.02, 0.018), DARK, cast=False)]


# --- ray casting -------------------------------------------------------------
def hit_ellipsoid(o, d, ob):
    Rt = ob["R"].T
    lo = ((o - ob["c"]) @ Rt.T) / ob["r"]
    ld = (d @ Rt.T) / ob["r"]
    a = np.einsum("ij,ij->i", ld, ld)
    b = 2 * np.einsum("ij,ij->i", lo, ld)
    c = np.einsum("ij,ij->i", lo, lo) - 1
    disc = b * b - 4 * a * c
    t = np.full(len(d), np.inf)
    m = disc > 0
    sq = np.sqrt(np.where(m, disc, 0))
    t0 = (-b - sq) / (2 * a)
    t1 = (-b + sq) / (2 * a)
    tt = np.where(t0 > 1e-4, t0, np.where(t1 > 1e-4, t1, np.inf))
    t[m] = tt[m]
    return t


def normal_ellipsoid(p, ob):
    Rt = ob["R"].T
    local = ((p - ob["c"]) @ Rt.T) / ob["r"]
    n = (local / ob["r"]) @ ob["R"].T
    return n / np.linalg.norm(n, axis=1, keepdims=True)


def hit_box(o, d, ob):
    with np.errstate(divide="ignore", invalid="ignore"):
        inv = 1.0 / d
        t1 = (ob["lo"] - o) * inv
        t2 = (ob["hi"] - o) * inv
    tmin = np.nanmax(np.minimum(t1, t2), axis=1)
    tmax = np.nanmin(np.maximum(t1, t2), axis=1)
    ok = (tmax >= np.maximum(tmin, 1e-4))
    return np.where(ok, np.where(tmin > 1e-4, tmin, tmax), np.inf)


def normal_box(p, ob):
    c = (ob["lo"] + ob["hi"]) / 2
    h = (ob["hi"] - ob["lo"]) / 2
    q = (p - c) / h
    ax = np.argmax(np.abs(q), axis=1)
    n = np.zeros_like(p)
    n[np.arange(len(p)), ax] = np.sign(q[np.arange(len(p)), ax])
    return n


def obox(c, half, col, R=None, cast=True, tex=None):
    """Oriented box: centre, half-extents, rotation. Used for tilting props."""
    return {"k": "o", "c": np.array(c, float), "h": np.array(half, float),
            "R": np.eye(3) if R is None else R, "col": col, "cast": cast, "tex": tex}


def _to_local(o, d, ob):
    Rt = ob["R"].T
    return (o - ob["c"]) @ Rt.T, d @ Rt.T


def hit_obox(o, d, ob):
    lo, ld = _to_local(o, d, ob)
    return hit_box(lo, ld, {"lo": -ob["h"], "hi": ob["h"]})


def normal_obox(p, ob):
    lp, _ = _to_local(p, np.zeros_like(p), ob)
    n = normal_box(lp, {"lo": -ob["h"], "hi": ob["h"]})
    return n @ ob["R"].T


def _hit(o, d, ob):
    k = ob["k"]
    return hit_ellipsoid(o, d, ob) if k == "e" else hit_obox(o, d, ob) if k == "o" else hit_box(o, d, ob)


def _normal(p, ob):
    k = ob["k"]
    return normal_ellipsoid(p, ob) if k == "e" else normal_obox(p, ob) if k == "o" else normal_box(p, ob)


def _bsphere(ob):
    """Centre and radius of a sphere that encloses the object (for culling)."""
    if ob["k"] == "e":
        return ob["c"], float(ob["r"].max())
    if ob["k"] == "o":
        return ob["c"], float(np.linalg.norm(ob["h"]))
    return (ob["lo"] + ob["hi"]) / 2, float(np.linalg.norm(ob["hi"] - ob["lo"]) / 2)


def cast(o, d, objs, sel=None):
    """Nearest hit per ray. `sel[i]`, when given, lists the only rays that can
    possibly reach object i (conservative culling); None means test all."""
    best = np.full(len(d), np.inf)
    idx = np.full(len(d), -1)
    for i, ob in enumerate(objs):
        ix = None if sel is None else sel[i]
        if ix is None:
            t = _hit(o, d, ob)
            m = t < best
            best[m] = t[m]
            idx[m] = i
        elif len(ix):
            t = _hit(o[ix], d[ix], ob)
            m = t < best[ix]
            best[ix[m]] = t[m]
            idx[ix[m]] = i
    return best, idx


def _screen_candidates(objs, cam, right, up, fwd, tx, ty, W, H):
    """Pixels whose primary ray could hit each object: the projected bounding
    box of the 8 corners of a cube enclosing the object's bounding sphere.
    Exact-conservative: a ray outside this box cannot hit the object."""
    out = []
    signs = np.array([[sx, sy, sz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)], float)
    for ob in objs:
        c, rad = _bsphere(ob)
        corners = c + signs * rad - cam
        z = corners @ fwd
        if (z <= 1e-3).any():
            out.append(None)
            continue
        sx = (corners @ right) / z / tx
        sy = (corners @ up) / z / ty
        c0 = int(max(0, np.floor((sx.min() + 1) / 2 * W - 1)))
        c1 = int(min(W - 1, np.ceil((sx.max() + 1) / 2 * W + 1)))
        r0 = int(max(0, np.floor((1 - sy.max()) / 2 * H - 1)))
        r1 = int(min(H - 1, np.ceil((1 - sy.min()) / 2 * H + 1)))
        if c0 > c1 or r0 > r1:
            out.append(np.zeros(0, int))
            continue
        rows, cols = np.arange(r0, r1 + 1), np.arange(c0, c1 + 1)
        out.append((rows[:, None] * W + cols[None, :]).ravel())
    return out


def _shadow_candidates(objs, sp, L):
    """Shadow rays all share direction L: keep only rays passing within the
    object's bounding sphere (distance from centre to the ray line)."""
    out = []
    for ob in objs:
        c, rad = _bsphere(ob)
        rel = c - sp
        proj = rel @ L
        perp2 = np.einsum("ij,ij->i", rel, rel) - proj * proj
        out.append(np.nonzero((perp2 <= rad * rad * 1.0001) & (proj >= -rad))[0])
    return out


LIGHT = np.array([-0.45, 1.0, 0.55])
LIGHT /= np.linalg.norm(LIGHT)


POC_CAMERA = ((0.4, 2.0, 6.6), (-0.4, 0.35, 0.0), 46)


def render(t, W, H):
    """The verified Shot 01 proof of concept (unchanged camera and scene)."""
    objs = static_scene() + nunu(t) + lulu(t) + mimo(t)
    return render_scene(objs, *POC_CAMERA, t, W, H)


def render_scene(objs, cam, look, fov_deg, t, W, H):
    """Generic renderer: any object list, any camera."""
    cam = np.array(cam, float)
    look = np.array(look, float)
    fwd = look - cam
    fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, [0, 1, 0])
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    fov = math.radians(fov_deg)
    ys, xs = np.mgrid[0:H, 0:W]
    px = (2 * (xs + 0.5) / W - 1) * math.tan(fov / 2) * W / H
    py = (1 - 2 * (ys + 0.5) / H) * math.tan(fov / 2)
    d = px.reshape(-1, 1) * right + py.reshape(-1, 1) * up + fwd
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    o = np.broadcast_to(cam, d.shape)

    tx, ty = math.tan(fov / 2) * W / H, math.tan(fov / 2)
    tbest, idx = cast(o, d, objs, _screen_candidates(objs, cam, right, up, fwd, tx, ty, W, H))
    sky_v = np.clip(d[:, 1] * 2.2 + 0.25, 0, 1)[:, None]
    img = (1 - sky_v) * np.array([206, 232, 248]) + sky_v * np.array([120, 178, 236])
    hit = np.isfinite(tbest)
    p = o[hit] + d[hit] * tbest[hit, None]
    n = np.zeros_like(p)
    col = np.zeros_like(p)
    ids = idx[hit]
    for i, ob in enumerate(objs):
        m = ids == i
        if not m.any():
            continue
        n[m] = _normal(p[m], ob)
        c = np.array(ob["col"], float)
        if ob.get("tex") == "planks":
            stripe = (np.floor((p[m, 0] + 1.6) / 0.32) % 2)[:, None]
            col[m] = c * (0.92 + 0.08 * stripe)
        elif ob.get("tex") == "water":
            ripple = 0.5 + 0.5 * np.sin(p[m, 2] * 6 + p[m, 0] * 2 + t * 2.2)
            col[m] = c * (0.95 + 0.07 * ripple[:, None])
        else:
            col[m] = c
    ndl = np.clip(n @ LIGHT, 0, 1)
    # cast shadows from casters onto everything
    casters = [ob for ob in objs if ob["cast"]]
    sp = p + n * 2e-3
    st, _ = cast(sp, np.broadcast_to(LIGHT, sp.shape), casters, _shadow_candidates(casters, sp, LIGHT))
    lit = np.where(np.isfinite(st), 0.0, 1.0)
    band = np.where(ndl > 0.55, 1.0, np.where(ndl > 0.2, 0.72, 0.5))   # toon bands
    shade = 0.42 + 0.58 * band * lit
    shaded = col * shade[:, None]
    fog = np.clip((tbest[hit] - 9) / 30, 0, 0.55)[:, None]
    shaded = shaded * (1 - fog) + np.array([206, 232, 248]) * fog
    img[hit] = shaded
    img = img.reshape(H, W, 3)
    # outlines where the visible object changes (stylized look)
    idmap = np.where(hit, idx, -2).reshape(H, W)
    edge = np.zeros((H, W), bool)
    for dy, dx in ((0, 1), (1, 0)):
        edge |= idmap != np.roll(np.roll(idmap, dy, 0), dx, 1)
    # no outlines on terrain: ground boxes and the large distant hills
    big = {i for i, ob in enumerate(objs)
           if not ob["cast"] and (ob["k"] == "b" or (ob["k"] == "e" and ob["r"].max() > 3))}
    on_char = np.isin(idmap, [i for i in range(len(objs)) if i not in big])
    img[edge & on_char] *= 0.55
    return np.clip(img, 0, 255).astype(np.uint8)


# --- audio (original, procedural) ---------------------------------------------
SR = 44100


def synth_audio(duration):
    rng = np.random.default_rng(15)
    n = int(SR * duration)
    t = np.arange(n) / SR
    # stream ambience: smoothed noise with slow swell
    noise = rng.standard_normal(n)
    k = 60
    brook = np.convolve(noise, np.ones(k) / k, mode="same") * 0.9
    brook *= 0.6 + 0.4 * np.sin(2 * np.pi * 0.23 * t)
    # gentle pentatonic melody (C major pentatonic), original sequence
    notes = [(0.5, 72), (1.25, 76), (2.0, 79), (2.75, 76), (3.5, 74), (4.25, 72),
             (5.0, 69), (5.75, 72), (6.5, 74), (7.25, 76), (8.0, 79), (9.0, 81),
             (9.75, 79), (10.5, 76), (11.0, 72)]
    mel = np.zeros(n)
    for start, midi in notes:
        f = 440 * 2 ** ((midi - 69) / 12)
        i0, length = int(start * SR), int(0.9 * SR)
        seg = np.arange(min(length, n - i0)) / SR
        env = np.minimum(seg / 0.02, 1.0) * np.exp(-seg * 3.2)
        mel[i0:i0 + len(seg)] += env * (np.sin(2 * np.pi * f * seg) + 0.25 * np.sin(4 * np.pi * f * seg))
    # soft footsteps at the exact walk-cycle footfalls
    steps = np.zeros(n)
    for ft in footstep_times():
        i0 = int(ft * SR)
        seg = np.arange(int(0.07 * SR)) / SR
        thump = np.sin(2 * np.pi * 140 * seg) * np.exp(-seg * 60)
        steps[i0:i0 + len(seg)] += thump[: max(0, min(len(seg), n - i0))]
    mix = 0.10 * brook + 0.16 * mel + 0.55 * steps
    fade = np.minimum(np.minimum(t / 0.4, 1.0), np.minimum((duration - t) / 0.8, 1.0))
    mix *= fade
    mix *= 0.5 / max(1e-9, np.max(np.abs(mix)))        # peak about -6 dBFS
    return mix


def write_wav(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# --- main ---------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=int, default=640)
    ap.add_argument("--height", type=int, default=360)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--frames", type=int, default=0, help="render only N frames (test)")
    args = ap.parse_args()

    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    OUT.mkdir(parents=True, exist_ok=True)
    fdir = OUT / f"{SHOT}_frames"
    if fdir.exists():
        shutil.rmtree(fdir)
    fdir.mkdir()
    total = args.frames or int(DURATION * args.fps)
    t0 = time.time()
    for f in range(total):
        img = render(f / args.fps, args.width, args.height)
        Image.fromarray(img).save(fdir / f"{f:04d}.png")
        if f % 24 == 0:
            print(f"frame {f}/{total}  {time.time() - t0:.1f}s", flush=True)
    render_s = time.time() - t0
    wav = OUT / f"{SHOT}.wav"
    write_wav(wav, synth_audio(total / args.fps))
    mp4 = OUT / f"{SHOT}.mp4"
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-framerate", str(args.fps),
           "-i", str(fdir / "%04d.png"), "-i", str(wav),
           "-vf", "scale=1280:720:flags=lanczos,format=yuv420p",
           "-c:v", "libx264", "-crf", "18", "-preset", "medium",
           "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(mp4)]
    t1 = time.time()
    subprocess.run(cmd, check=True)
    meta = {"shot": SHOT, "frames": total, "fps": args.fps,
            "render_resolution": [args.width, args.height], "output_resolution": [1280, 720],
            "render_seconds": round(render_s, 1), "encode_seconds": round(time.time() - t1, 1),
            "footstep_times_s": footstep_times(), "ffmpeg": ffmpeg.split("\\")[-1],
            "network_calls": 0, "external_assets": 0}
    (OUT / f"{SHOT}.build.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(json.dumps(meta, indent=1))


if __name__ == "__main__":
    sys.exit(main())

"""Episode 1 shot list for the ANIMATIC: every storyboard shot as data.

Each shot returns, for a shot-local time t, the scene objects and the camera.
Characters are posed parametrically and built from the same primitives as
the verified proof of concept (render_poc.py). Subtitle lines are the
script's own Arabic lines (script_ar.md). No voices: this is a timing and
staging preview, labelled ANIMATIC everywhere it appears.
"""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np

_spec = importlib.util.spec_from_file_location("render_poc", Path(__file__).with_name("render_poc.py"))
E = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E)
ell, obox, rot_y, rot_z, rot_x = E.ell, E.obox, E.rot_y, E.rot_z, E.rot_x

OWL_BROWN = (150, 110, 78)
OWL_FACE = (236, 218, 190)
BEAK = (232, 170, 60)
ROPE = (214, 190, 140)
BASKET = (170, 120, 70)
SPINE = (96, 58, 32)


# --- placement ---------------------------------------------------------------
def place(parts, origin, yaw):
    """Characters are modelled facing +x at the origin; turn and move them."""
    Ry = rot_y(yaw)
    o = np.array(origin, float)
    out = []
    for p in parts:
        q = dict(p)
        q["c"] = o + Ry @ p["c"]
        q["R"] = Ry @ p["R"]
        out.append(q)
    return out


def walk(t, t0, t1, a, b, hz=1.6):
    """Position and gait for a walk from a to b between t0 and t1 (never a run)."""
    u = E.smoothstep(t0, t1, t)
    x = a + (b - a) * u
    walking = t0 + 0.3 < t < t1 - 0.3
    return x, 2 * math.pi * hz * (t - t0), (1.0 if walking else 0.0)


def footfalls(t0, t1, hz=1.6):
    out, k = [], 1
    while True:
        tt = t0 + k * 0.5 / hz
        if tt >= t1 - 0.3:
            return out
        if tt > t0 + 0.3:
            out.append(tt)
        k += 1


# --- characters ----------------------------------------------------------------
def nunu(phase=0.0, amp=0.0, sway=0.0, head_tilt=0.0, paw=0.0, basket=False):
    bob = 0.025 * amp * abs(math.sin(phase))
    y = 0.36 + bob
    H = rot_z(head_tilt)
    head = np.array([0.30, y + 0.30, 0])
    parts = [ell((0, y, 0), (0.32, 0.21, 0.2), E.ORANGE),
             ell((0.17, y - 0.04, 0), (0.13, 0.13, 0.15), E.CREAM),
             ell(head, (0.18, 0.17, 0.17), E.ORANGE),
             ell(head + H @ np.array([0.15, -0.04, 0]), (0.11, 0.06, 0.07), E.CREAM, R=H),
             ell(head + H @ np.array([0.255, -0.03, 0]), (0.025, 0.025, 0.025), E.DARK, cast=False)]
    for zs in (1, -1):
        parts.append(ell(head + H @ np.array([-0.04, 0.20, 0.09 * zs]), (0.05, 0.12, 0.035), E.ORANGE, R=H @ rot_x(0.25 * zs)))
        parts.append(ell(head + H @ np.array([0.13, 0.05, 0.075 * zs]), (0.022, 0.026, 0.022), E.DARK, cast=False))
    legs = ((0.17, 0.10, 0), (-0.17, -0.10, 0), (0.17, -0.10, math.pi), (-0.17, 0.10, math.pi))
    for i, (dx, dz, off) in enumerate(legs):
        lift = 0.06 * amp * max(0.0, math.sin(phase + off)) + (0.08 * paw if i == 0 else 0.0)
        swing = 0.05 * amp * math.cos(phase + off) + (0.06 * paw if i == 0 else 0.0)
        parts.append(ell((dx + swing, 0.14 + lift, dz), (0.05, 0.14, 0.05), E.ORANGE))
    R = rot_y(sway) @ rot_z(0.35)
    tail_c = np.array([-0.44, y + 0.10, 0]) + rot_y(sway) @ np.array([-0.05, 0, 0])
    parts.append(ell(tail_c, (0.26, 0.09, 0.09), E.ORANGE, R=R))
    parts.append(ell(tail_c + R @ np.array([-0.24, 0, 0]), (0.07, 0.07, 0.07), E.CREAM))
    if basket:
        parts.append(ell((0.08, 0.22, 0.26), (0.11, 0.08, 0.09), BASKET))
        parts.append(ell((0.08, 0.30, 0.26), (0.08, 0.03, 0.06), ROPE, cast=False))
    return parts


def lulu(ear=0.12, hop=0.0):
    p = [ell((0, 0.30 + hop, 0), (0.2, 0.26, 0.2), E.LULU),
         ell((0.04, 0.66 + hop, 0), (0.16, 0.15, 0.15), E.LULU),
         ell((0.04, 0.48 + hop, 0), (0.17, 0.05, 0.17), E.SCARF),
         ell((0.18, 0.66 + hop, 0.06), (0.02, 0.025, 0.02), E.DARK, cast=False),
         ell((0.18, 0.66 + hop, -0.06), (0.02, 0.025, 0.02), E.DARK, cast=False),
         ell((0.19, 0.61 + hop, 0), (0.02, 0.016, 0.02), E.PINK, cast=False)]
    for zs in (1, -1):
        R = rot_x(ear * zs)
        p.append(ell((0.02, 0.98 + hop, 0.06 * zs), (0.045, 0.22, 0.03), E.LULU, R=R))
        p.append(ell((0.035, 0.98 + hop, 0.06 * zs), (0.02, 0.16, 0.015), E.PINK, R=R, cast=False))
    return p


def mimo(hop=0.0, curl=0.0):
    y = 0.2 + hop
    p = [ell((0, y, 0), (0.22, 0.18 - 0.03 * curl, 0.2), E.MIMO_SPINE),
         ell((0.17, y, 0), (0.1, 0.1, 0.11), E.MIMO_FACE),
         ell((0.27, y - 0.01, 0), (0.025, 0.025, 0.025), E.DARK, cast=False),
         ell((0.22, y + 0.05, 0.05), (0.018, 0.02, 0.018), E.DARK, cast=False),
         ell((0.22, y + 0.05, -0.05), (0.018, 0.02, 0.018), E.DARK, cast=False)]
    # spines: so Mimo reads as a hedgehog (QA defect C2 in the PoC)
    for ia, a in enumerate(np.linspace(0.35, 2.75, 7)):
        for zs in (-0.11, 0.0, 0.11):
            d = np.array([-math.cos(a) * 0.9, math.sin(a), 0.0])
            d /= np.linalg.norm(d)
            c = np.array([-0.02, y, zs]) + d * np.array([0.2, 0.17, 0.2])
            ang = math.atan2(d[1], d[0]) - math.pi / 2
            p.append(ell(c, (0.025, 0.09, 0.025), SPINE, R=rot_z(ang), cast=False))
    return p


def owl(nod=0.0, wing=0.0):
    H = rot_z(-0.15 * nod)
    p = [ell((0, 0.32, 0), (0.2, 0.3, 0.2), OWL_BROWN),
         ell((0.05, 0.62, 0), (0.18, 0.17, 0.18), OWL_BROWN),
         ell((0.12, 0.62, 0) + H @ np.array([0.06, 0, 0]), (0.07, 0.13, 0.15), OWL_FACE, R=H)]
    for zs in (1, -1):
        p.append(ell(np.array([0.2, 0.66, 0.06 * zs]) + H @ np.array([0, 0, 0]), (0.03, 0.04, 0.035), E.CREAM, cast=False))
        p.append(ell((0.225, 0.66, 0.06 * zs), (0.018, 0.022, 0.018), E.DARK, cast=False))
        p.append(ell((0.02, 0.78, 0.09 * zs), (0.03, 0.07, 0.03), OWL_BROWN, R=rot_x(0.35 * zs)))
        p.append(ell((-0.02, 0.33, 0.17 * zs), (0.13, 0.22, 0.05), OWL_BROWN, R=rot_x(wing * zs)))
    p.append(ell((0.22, 0.6, 0), (0.035, 0.03, 0.025), BEAK, cast=False))
    return p


# --- set pieces ----------------------------------------------------------------
TREE_X, TREE_Z = -4.1, -2.8
# low branch, below the canopy (canopy underside is about y = 1.30 at the perch)
OWL_PERCH = (TREE_X + 0.75, 0.45, TREE_Z + 0.55)


def loose_plank(tilt):
    return [obox((0.0, 0.135, 0.0), (0.15, 0.025, 0.42), (190, 136, 86), R=rot_z(tilt))]


def ropes():
    out = []
    for z in (-0.32, 0.32):
        for x in (-0.13, 0.13):
            out.append(ell((x, 0.13, z), (0.03, 0.045, 0.04), ROPE, cast=False))
    return out


def branch():
    return [obox((TREE_X + 0.55, 0.40, TREE_Z + 0.35), (0.5, 0.05, 0.06), E.TRUNK, R=rot_y(-0.6))]


def plank_tilt(t, start, stop):
    """Gentle wobble while the plank is loose; zero once tied."""
    if t < start or t > stop:
        return 0.0
    return 0.08 * math.sin(2 * math.pi * 1.1 * (t - start)) * min(1.0, (t - start) / 0.4)


# --- shots ---------------------------------------------------------------------
# Each shot: id, duration, camera(t) -> (cam, look, fov), actors(t) -> objects,
# footfalls (shot-local seconds), subtitles [(start, end, line)] in Arabic.
def _shot(sid, dur, camera, actors, steps=(), subs=(), creaks=()):
    return {"id": sid, "dur": dur, "camera": camera, "actors": actors,
            "steps": list(steps), "subs": list(subs), "creaks": list(creaks)}


def _base(t, tilt=0.0, tied=False, owl_obj=None):
    objs = E.static_scene() + loose_plank(0.0 if tied else tilt) + branch()
    if tied:
        objs += ropes()
    if owl_obj:
        objs += owl_obj
    return objs


def _lulu_mimo(t, ear=0.12, lulu_hop=0.0, mimo_hop=0.0):
    return place(lulu(ear=ear, hop=lulu_hop), (2.3, 0, 0.25), math.pi) + \
           place(mimo(hop=mimo_hop), (2.9, 0, -0.15), math.pi)


def shot01():
    def actors(t):
        x, ph, a = walk(t, 0.6, 7.6, -4.6, -2.2)
        sway = 0.35 * math.sin(2 * math.pi * 0.8 * t) if t > 7.6 else 0.18 * math.sin(ph)
        wig = 0.12 + (0.12 * math.sin(2 * math.pi * 1.6 * t) if 7.4 < t < 9.4 else 0.0)
        hop = 0.08 * max(0.0, math.sin(2 * math.pi * 1.2 * (t - 9.6))) if 9.6 < t < 11.3 else 0.0
        owl_obj = place(owl(), OWL_PERCH, 0.4)
        return _base(t, owl_obj=owl_obj) + place(nunu(ph, a, sway), (x, 0, 0), 0) + _lulu_mimo(t, ear=wig, mimo_hop=hop)
    return _shot("01", 12, lambda t: E.POC_CAMERA, actors, steps=footfalls(0.6, 7.6))


def shot02():
    cam = ((-1.2, 0.95, 2.4), (-2.2, 0.55, 0.0), 40)
    def actors(t):
        return _base(t) + place(nunu(sway=0.25 * math.sin(2 * math.pi * 0.7 * t), head_tilt=0.08 * math.sin(2 * math.pi * 0.5 * t)), (-2.2, 0, 0), -0.6)
    return _shot("02", 6, lambda t: cam, actors,
                 subs=[(0.8, 5.6, "صَبَاحُ الخَيْرِ يَا وَادِي الزَّهْر! لُولُو وَمِيمُو يَنْتَظِرَانِنِي!")])


def shot03():
    cam = ((-0.7, 0.9, 2.3), (-1.0, 0.25, 0.0), 44)
    def actors(t):
        paw = min(1.0, max(0.0, (t - 0.8) / 0.8)) * (1.0 if t < 4.5 else max(0.0, 1 - (t - 4.5) / 0.8))
        return _base(t, tilt=plank_tilt(t, 2.0, 6.0)) + place(nunu(paw=paw), (-1.75, 0, 0), 0)
    return _shot("03", 6, lambda t: cam, actors, creaks=[2.0, 3.8])


def shot04():
    cam = ((-1.8, 0.9, 2.6), (-2.2, 0.5, 0.0), 40)
    def actors(t):
        x, ph, a = walk(t, 3.6, 6.0, -1.75, -2.4, hz=1.2)
        return _base(t, tilt=plank_tilt(t, 0.0, 3.0)) + place(nunu(ph, a, head_tilt=-0.1), (x, 0, 0), 0)
    return _shot("04", 8, lambda t: cam, actors, steps=footfalls(3.6, 6.0, 1.2),
                 subs=[(0.6, 3.2, "أُوه! هَذَا اللَّوْحُ يَهْتَزّ!")])


def shot05():
    cam = ((-2.0, 0.85, 1.9), (-2.4, 0.55, 0.0), 38)
    def actors(t):
        tilt = 0.15 * math.sin(math.pi * min(1.0, t / 3.0)) if t < 6 else 0.0
        return _base(t) + place(nunu(head_tilt=tilt, sway=0.1 * math.sin(2 * math.pi * 0.5 * t)), (-2.4, 0, 0), 0)
    return _shot("05", 10, lambda t: cam, actors,
                 subs=[(0.8, 4.6, "أَسْتَطِيعُ أَنْ أَقْفِزَ بِسُرْعَة..."),
                       (5.0, 9.4, "لَحْظَة! سَأُفَكِّرُ أَوَّلًا.")])


def shot06():
    cam = ((0.2, 1.6, 5.2), (0.0, 0.45, 0.0), 44)
    def actors(t):
        ear = 0.12 if t < 4 else (-0.35 if t < 8 else 0.1)
        return _base(t, tilt=plank_tilt(t, 0.0, 12.0)) + place(nunu(), (-2.4, 0, 0), 0) + _lulu_mimo(t, ear=ear)
    return _shot("06", 12, lambda t: cam, actors,
                 subs=[(0.5, 3.0, "نُونُو! مَا الأَمْر؟"),
                       (3.4, 6.6, "فِي الجِسْرِ لَوْحٌ مُخَلْخَل!"),
                       (7.0, 11.5, "لَا تَقْفِزْ يَا نُونُو! هَيَّا نَسْأَل!")])


def shot07():
    cam = ((1.55, 0.6, -0.95), (2.9, 0.25, -0.1), 40)
    def actors(t):
        turn = math.pi + (-0.5 * min(1.0, max(0.0, (t - 1.0) / 1.5)))
        breath = 0.015 * (1 + math.sin(2 * math.pi * 0.8 * t))
        return _base(t) + place(lulu(ear=0.12 + 0.06 * math.sin(2 * math.pi * 0.5 * t)), (2.3, 0, 0.25), math.pi) + place(mimo(hop=breath, curl=0.4 if t < 2 else 0.0), (2.9, 0, -0.15), turn)
    return _shot("07", 8, lambda t: cam, actors,
                 subs=[(1.2, 7.4, "جَدَّةُ بُومَة... بَيْتُهَا قَرِيبٌ مِنْكَ، عِنْدَ شَجَرَةِ الزَّيْتُون.")])


def shot08():
    def cam(t):
        u = t / 10.0
        return ((-2.2 - 0.9 * u, 1.3, 3.2), (-2.8 - 0.9 * u, 0.6, -1.0), 44)
    def actors(t):
        x, ph, a = walk(t, 0.5, 8.5, -2.4, -3.3)
        z = -1.4 * E.smoothstep(0.5, 8.5, t)
        owl_obj = place(owl(), OWL_PERCH, 0.4)
        return _base(t, owl_obj=owl_obj) + place(nunu(ph, a, 0.18 * math.sin(ph)), (x, 0, z), -0.95)
    return _shot("08", 10, cam, actors, steps=footfalls(0.5, 8.5))


def shot09():
    cam = ((-0.9, 1.5, -0.2), (-3.3, 1.0, -1.9), 46)
    def actors(t):
        nod = math.sin(2 * math.pi * 0.6 * t) if 5.0 < t < 11.0 else 0.25 * math.sin(2 * math.pi * 0.3 * t)
        owl_obj = place(owl(nod=nod), OWL_PERCH, -1.57)
        return _base(t, owl_obj=owl_obj) + place(nunu(head_tilt=0.22, sway=0.25 * math.sin(2 * math.pi * 0.6 * t)), (-3.3, 0, -1.4), 1.57)
    return _shot("09", 14, lambda t: cam, actors,
                 subs=[(0.6, 4.4, "جَدَّتِي بُومَة! فِي الجِسْرِ لَوْحٌ يَهْتَزّ."),
                       (4.8, 13.4, "أَحْسَنْتَ يَا نُونُو، لِأَنَّكَ لَمْ تَقْفِزْ وَجِئْتَ تُخْبِرُنِي. هَيَّا نُصْلِحُهُ مَعًا.")])


def shot10():
    cam = ((0.3, 1.5, 3.4), (0.0, 0.3, 0.0), 40)
    def actors(t):
        tied = t > 13.0
        wing = 0.5 * abs(math.sin(2 * math.pi * 1.5 * t)) if 3.0 < t < 13.0 else 0.0
        owl_obj = place(owl(wing=wing), (0.0, 0.12, -0.75), -math.pi / 2)
        return _base(t, tilt=plank_tilt(t, 0.0, 3.0), tied=tied, owl_obj=owl_obj) + \
            place(nunu(basket=True), (-1.25, 0, 0.0), 0) + _lulu_mimo(t)
    return _shot("10", 20, lambda t: cam, actors,
                 subs=[(4.0, 9.0, "الحَبْلُ هُنَا... وَهُنَا."),
                       (13.6, 19.0, "الآنَ صَارَ الجِسْرُ قَوِيًّا.")])


def shot11():
    cam = ((1.55, 0.6, -0.95), (2.9, 0.25, -0.1), 40)
    def actors(t):
        hop = 0.1 * max(0.0, math.sin(2 * math.pi * 1.2 * t)) if 0.8 < t < 4.0 else 0.015 * (1 + math.sin(2 * math.pi * 0.8 * t))
        return _base(t, tied=True) + place(lulu(), (2.3, 0, 0.25), math.pi) + place(mimo(hop=hop), (2.9, 0, -0.15), math.pi - 0.5)
    return _shot("11", 6, lambda t: cam, actors, subs=[(1.0, 5.0, "قَوِيٌّ جِدًّا!")])


def shot12():
    cam = ((0.0, 0.9, 3.0), (0.0, 0.35, 0.0), 46)
    def actors(t):
        x, ph, a = walk(t, 1.0, 14.0, -2.2, 1.9, hz=1.2)
        on_deck = -1.6 < x < 1.6
        y = 0.12 if on_deck else 0.0
        ear = 0.12 + (0.15 * math.sin(2 * math.pi * 1.6 * t) if t > 12 else 0.0)
        return _base(t, tied=True) + place(nunu(ph, a, 0.15 * math.sin(ph)), (x, y, -0.12), 0) + _lulu_mimo(t, ear=ear)
    return _shot("12", 16, lambda t: cam, actors, steps=footfalls(1.0, 14.0, 1.2),
                 subs=[(13.0, 15.6, "أَحْسَنْتَ يَا نُونُو!")])


def shot13():
    cam = ((2.3, 1.15, 3.4), (2.35, 0.45, 0.05), 44)
    def actors(t):
        hop = 0.08 * max(0.0, math.sin(2 * math.pi * 1.2 * (t - 7.0))) if 7.0 < t < 9.5 else 0.0
        return _base(t, tied=True) + place(nunu(sway=0.3 * math.sin(2 * math.pi * 0.8 * t)), (1.9, 0, 0.0), -0.4) + \
            place(lulu(hop=hop), (2.6, 0, 0.55), math.pi + 0.3) + place(mimo(hop=hop), (2.9, 0, -0.4), math.pi + 0.4)
    return _shot("13", 10, lambda t: cam, actors,
                 subs=[(0.5, 6.4, "عِنْدَمَا نَرَى شَيْئًا مَكْسُورًا... نُخْبِرُ الكِبَار!"),
                       (6.8, 9.6, "هَيَّا نَلْعَب!")])


def shot14():
    def cam(t):
        u = E.smoothstep(0, 20, t)
        return ((1.4, 1.4 + 1.6 * u, 3.4 + 5.0 * u), (2.0, 0.4, 0.0), 46)
    def actors(t):
        hop = lambda ph: 0.08 * max(0.0, math.sin(2 * math.pi * 1.0 * t + ph))
        return _base(t, tied=True) + place(nunu(sway=0.3 * math.sin(2 * math.pi * 0.8 * t)), (1.8 + 0.3 * math.sin(0.4 * t), hop(0.0), 0.3), math.pi / 2) + \
            place(lulu(hop=hop(2.0)), (2.6, 0, 0.6), math.pi) + place(mimo(hop=hop(4.0)), (2.4, 0, -0.3), math.pi)
    return _shot("14", 20, cam, actors)


SHOTS = [shot01(), shot02(), shot03(), shot04(), shot05(), shot06(), shot07(),
         shot08(), shot09(), shot10(), shot11(), shot12(), shot13(), shot14()]


def timeline():
    """Absolute start time of every shot in the cut."""
    out, t0 = [], 0.0
    for s in SHOTS:
        out.append((t0, s))
        t0 += s["dur"]
    return out, t0


def frame_at(t_abs, W, H):
    for t0, s in timeline()[0]:
        if t0 <= t_abs < t0 + s["dur"]:
            tl = t_abs - t0
            cam, look, fov = s["camera"](tl)
            return E.render_scene(s["actors"](tl), cam, look, fov, tl, W, H)
    raise ValueError(t_abs)

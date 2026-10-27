# Storyboard: Episode 2 — «لولى والكرة الضائعة» / "Lulu's Lost Ball"

Status: DRAFT v0.1 — **not approved** (native Arabic review and child-safety sign-off outstanding).
Camera language for ages 4–8: long, steady shots; no whip pans; no fast cuts (no shot under 3 s); eye-level camera.

Frame: 16:9. Camera heights: "eye" = character eye level, about 0.6 m in scene units.

**Delivered cut (2026-10-27):** 14 shots, 130.0 s, 1560 frames at 12 fps, 1280×720.
`kids_studio/renders/ep02_lulus_lost_ball.mp4`, `verify_video.py` PASS (9/9).
This table is the board as rendered, not the earlier 12-shot / ~180 s plan.

| Shot | In (s) | Dur | Camera | Action | Cue(s) | PoC? |
|---|---|---|---|---|---|---|
| 01 | 0 | 12 s | wide, static, slight high angle; garden centre-frame, fov 40 | Garden at morning. Lulu plays at centre with the red ball; she hops and her ears sway; the ball rocks gently beside her | 1 | **YES — rendered and verified** |
| 02 | 12 | 6 s | tracks right with the ball, fov 42 | The ball rolls away to the right; Lulu turns her head to follow it | 2–3 | no |
| 03 | 18 | 8 s | tracks Lulu left, then right, fov 40 | Lulu walks left, searching, then turns and walks back to the right | 4 | no |
| 04 | 26 | 8 s | static medium, low, looking under the bush, fov 40 | Lulu walks to the bush and leans in to look underneath it | 5 | no |
| 05 | 34 | 8 s | static close on the bush top, fov 38 | A ladybug walks along the top of the bush; Lulu looks up at it and asks | 6–7 | no |
| 06 | 42 | 8 s | tracks Lulu toward the ball, fov 40 | Lulu walks to the ball lying under a leaf and finds it | 8 | no |
| 07 | 50 | 8 s | static close on Lulu, fov 38 | Lulu lifts the ball and holds it up | 9 | no |
| 08 | 58 | 8 s | tracks Lulu carrying the ball, fov 40 | Lulu carries the ball to a clear spot and sets it down | 10 | no |
| 09 | 66 | 12 s | static medium, fov 40 | Lulu plays beside the ball, hopping gently | 11 | no |
| 10 | 78 | 6 s | tracks the rolling ball, fov 42 | The ball rolls again and settles; Lulu's ears lift | 12 | no |
| 11 | 84 | 8 s | tracks Lulu to the ball, fov 40 | Lulu walks to the ball and picks it up a second time | 13 | no |
| 12 | 92 | 12 s | static close, fov 38 | Lulu holds the ball close; it stays with her | 14 | no |
| 13 | 104 | 12 s | slow lateral drift, fov 40 | Lulu sits with the ball; the ladybug rests nearby | 15 | no |
| 14 | 116 | 14 s | slow pull-out wide, fov 42 | Closing: Lulu, the ball and the ladybug in the garden | 16 | no |

Total: 130.0 s. No shot shorter than 6 s.

**Technical note (disclosed):** `frame_at()` adds a slow ±0.15-unit camera drift to
every shot. This exists because a static camera plus a still character produced
3.75 s of pixel-identical frames, which `verify_video.py` rejects
(`no_frozen_stretch_over_2s`). It is a stabiliser, not animation direction, and it
is applied identically to every shot.

**Revision (2026-10-27, after visual QA of the first PASS render):** three real
defects were found and fixed, then the episode was re-rendered and re-verified.
The ball was orange while the script's line says "the RED ball" - it is now red
(`BALL_RED`). The hedge line, tree and pond were placed at +z, behind the
cameras, which look toward -z, so the garden read as an empty field - they are
now behind the action, with three distant bushes added for depth. The ladybug's
four shell spots were zero-depth ellipsoids (a divide-by-zero in the renderer,
and invisible inside the shell); they now sit on the shell surface. No timing,
subtitle or footstep data changed.

## Shot 01 detail (proof of concept)

- **Set:** garden with grass, a hedge line, a tree, three foreground bushes, three distant bushes, flowers and a pond, all behind or beside the action; 3D primitive style matching Episode 1
- **Lulu:** centre, red ball beside her; ear sway and a gentle hop
- **Camera:** locked framing (matching Episode 1's shot 01 style); the stabiliser drift below is the only camera movement
- **No dialogue audio:** subtitles only (see `script_ar.md`)

## Not in this cut

- No narration and no character voices.
- No burned-in Arabic text (no open-licensed Arabic font on this machine).
- No basket prop: the "safe place" is a cleared spot, as rendered.

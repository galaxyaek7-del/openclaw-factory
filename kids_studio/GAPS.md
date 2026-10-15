# Kids Studio: pipeline gap audit (2026-10-15)

Measured from the files, not assumed (see the audit command in the session log).

## Buildable now, locally, at $0
| # | Gap | Evidence | Plan |
|---|---|---|---|
| 1 | 13 of 14 shots never rendered | manifest: 1 VERIFIED, 13 BOARDED | data-driven shot list for the whole episode |
| 2 | Camera fixed in code; no per-shot camera | `render(t, W, H)` hard-codes the camera | camera per shot |
| 3 | Grandma Owl not modelled | no `owl` builder | primitive model, same style as the others |
| 4 | Story props missing: wobbly plank, rope, basket | none in the renderer | oriented boxes (tilt) and rope wraps |
| 5 | Mimo unreadable as a hedgehog | open QA defect C2 | add spines |
| 6 | No subtitle track for the Arabic dialogue | none | SRT + soft subtitle track (needs no font) |
| 7 | No episode assembly (shots, edit, audio, mux) | no build_episode.py | one build script: render, mix, mux, verify |
| 8 | Rendering is single-process | 3.3 s/frame, ~6 h ESTIMATED per episode | parallel frame rendering across CPU cores |
| 9 | Verification covers one shot only | verify_video.py ran on shot 01 | run it on the whole episode |

## Blocked: needs a founder decision (not built, not faked)
| Gap | Why it is blocked |
|---|---|
| Arabic voices | no cleared voice on the machine; actors with a release, or a licensed synthetic voice |
| Burned-in Arabic text / title card | no open-licensed Arabic font; download needs approval (the soft subtitle track works without one) |
| Production character models | Blender install needs approval; the primitive style continues meanwhile |
| Native Arabic review (QA D1, D2) | needs a human reviewer |
| Upload | founder approval only |

## What "done" means for this round
A complete **animatic** of Episode 1: every storyboard shot rendered in the primitive 3D style, cut together with music, sound and Arabic soft subtitles, and decoded and verified end to end. It is labelled ANIMATIC: it is a timing and staging preview with no voices, not the finished episode.

## Status after this round
| # | Gap | Status |
|---|---|---|
| 1 | 13 of 14 shots never rendered | **CLOSED**: all 14 rendered in the animatic |
| 2 | No per-shot camera | **CLOSED**: `render_scene()` takes any camera; every shot has its own |
| 3 | Grandma Owl not modelled | **CLOSED** |
| 4 | Props missing | **CLOSED**: tilting plank (oriented box), rope wraps, basket, low branch |
| 5 | Mimo unreadable | **CLOSED**: spines added |
| 6 | No subtitle track | **CLOSED**: 16 Arabic cues, soft track tagged `ara`, verified in the MP4 |
| 7 | No episode assembly | **CLOSED**: `build_episode.py` |
| 8 | Single-process rendering | **CLOSED**: 4 workers + exact culling (pixel-identical, 4.2x faster per frame) |
| 9 | Verification for one shot only | **CLOSED**, and the verifier's own sync drift was found and fixed |

Still blocked (founder decisions): voices, an open Arabic font for burned-in text, Blender for production models, a native Arabic reviewer, and any upload.

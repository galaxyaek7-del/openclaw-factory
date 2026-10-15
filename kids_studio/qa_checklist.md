# QA checklist: Kids Studio

Every item gets PASS, FAIL, N/A (with reason) or PENDING, plus who checked it and when. An episode ships only when every item is PASS or a justified N/A, **and** the founder approves.

## A. Child safety (ages 4-8)
| # | Check | Ep01 shot 01 (PoC), checked 2026-10-15 |
|---|---|---|
| A1 | No frightening imagery, sounds, chases or peril | PASS: calm walk, soft melody and brook; no peril (reviewed on the MP4 contact sheet) |
| A2 | No behaviour a child could copy unsafely (jumping over water, climbing, touching broken things, playing near deep water) | PASS: Nunu walks (max speed pinned by test) and stops on the grass before the bridge; the stream is shallow |
| A3 | Risky situations resolved by stopping and telling a grown-up | N/A for shot 01 (setup only); applies to the full episode script |
| A4 | No mockery, exclusion, insults or violence between characters | PASS: no interaction beyond waiting and greeting |
| A5 | No brands, ads, purchase prompts or links aimed at children | PASS: none in frame or audio |
| A6 | No flashing or strobing (fewer than 3 flashes per second) | PASS: max frame-to-frame mean-luminance change 0.03/255 |

## B. Story coherence
| # | Check | |
|---|---|---|
| B1 | A child can retell the story in one sentence | applies to the full episode |
| B2 | Each scene has one clear action | PASS: Nunu walks to the bridge and stops |
| B3 | The lesson is shown in action, not only said | episode-level: Nunu steps back and asks for help |

## C. Visual consistency
| # | Check | |
|---|---|---|
| C1 | Character colours match the bible's hex values | PASS: palette constants in render_poc.py are the bible's values |
| C2 | Characters stay on-model across frames (no popping or distortion) | PASS for consistency; **open quality defect:** Mimo reads as a brown ball (no spines) |
| C3 | No shot under 3 s; steady camera | PASS: one 12 s shot, fixed camera |

## D. Arabic language
| # | Check | |
|---|---|---|
| D1 | Native-speaker review of wording and vowelling | **PENDING: needs a human reviewer** |
| D2 | Read-aloud test: lines are easy to say and understand | PENDING: needs a human |
| D3 | Pronunciation checked in the recorded audio | N/A: no voice recorded yet |

## E. Audio
| # | Check | |
|---|---|---|
| E1 | Peak below -1 dBFS; nothing sudden or loud | PASS: peak -6.0 dBFS, RMS -25.6 dBFS |
| E2 | Dialogue intelligible over music (when there is dialogue) | N/A: no dialogue in the PoC |
| E3 | Sound synced to picture | PASS: 21/21 footsteps, median 7.5 ms, max 15 ms (limit 42 ms) |

## F. Technical playback
| # | Check | |
|---|---|---|
| F1 | Decodes fully with no errors | PASS: 288/288 frames, 0 decode errors |
| F2 | Expected dimensions, frame rate and duration | PASS: 1280x720 H.264, 24 fps, 12.0 s (rendered at 640x360, upscaled) |
| F3 | No black, blank or frozen stretches | PASS: motion in 287/287 frame steps |
| F4 | Audio and video durations match | PASS: 12.005 s audio, 12.0 s video |

## G. Rights
| # | Check | |
|---|---|---|
| G1 | Every asset in `rights_ledger.json` with `usable: true` | PASS: every asset used in the PoC is original and owned |
| G2 | No voice, music or font with unknown rights | PASS: no voice or font used; music is original |

## Episode 1 animatic (2026-10-15)
Technical (verify_video.py): PASS. 1896/1896 frames, 0 decode errors, 1280x720, 12 fps, 158.0 s; audio peak -6.0 dBFS; 80/80 footsteps synced (max 4.0 ms); Arabic subtitle track 16/16 cues.
Child safety: PASS on staging. Nunu never jumps (tested on every frame of every shot), steps back from the wobbly plank, asks the grown-up; the plank is tied before anyone crosses (tested); no flashing (max 1 luminance jump per second, at cuts).
Open: D1/D2 native Arabic review (human), voices, visual defects listed in production_log.json.

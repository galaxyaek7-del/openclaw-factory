# Galaxy Forge Kids Studio

Original Arabic 3D animated shorts for children aged 4-8.
Status: **proof of concept**. No episode is finished, approved, or published.

## Rules this studio runs on

1. **Nothing is called finished until it exists and was checked.** A render counts only after `tools/verify_video.py` has decoded it and recorded the result.
2. **Original or properly licensed assets only.** Every model, texture, font, voice, sound and piece of music has a row in `rights_ledger.json` before it is used. Unknown rights means not usable.
3. **No cloned or imitated real voices.** Voices come from consenting human voice actors under a written release, or from a synthetic voice whose licence explicitly allows this use.
4. **$0 new spend.** No paid software, APIs, credits or subscriptions.
5. **No upload without founder approval.** `publishing/` holds drafts only.
6. **Child safety outranks schedule.** An episode that fails `qa_checklist.md` does not ship, however late.

## Layout

```
kids_studio/
  README.md                  this file
  bible/series_bible.md      world, tone, characters, Arabic style
  episodes/ep01_nunu_little_bridge/
    script_ar.md             Arabic pilot script
    storyboard.md            shot-by-shot board with timings
  production_manifest.json   every scene: status, method, assets, approvals
  rights_ledger.json         every asset: source, licence, evidence
  qa_checklist.md            child safety, story, visuals, audio, playback
  production_log.json        measured time, render time, defects
  tools/render_poc.py        reproducible proof-of-concept build (no network)
  tools/verify_video.py      decodes a render and checks it
  publishing/youtube_metadata_draft.md   draft only, not uploaded
  renders/                   build output (not committed)
```

## Production workflow

| Stage | Output | Automated? | Human gate |
|---|---|---|---|
| 1. Story | premise, beats | drafting can be assisted | **yes**: age fit, safety, cultural review |
| 2. Script (Arabic) | `script_ar.md` | drafting can be assisted | **yes**: native Arabic review, read-aloud test |
| 3. Storyboard | `storyboard.md` | yes | yes |
| 4. Assets | models, textures | procedural where possible | rights entry required |
| 5. Layout and animation | scene files | partly (blocking, camera) | yes |
| 6. Voice | recorded lines | **no**: human actors under release | yes |
| 7. Music and sound | stems | original procedural, or licensed | rights entry required |
| 8. Render | frames | yes (`render_poc.py`) | no |
| 9. Edit and mix | master file | yes (FFmpeg) | yes |
| 10. QA | checklist results | technical checks automated | **yes**: full watch-through |
| 11. Publish | YouTube upload | **never automatic** | **founder approval** |

## Reproducing the proof of concept

```
python kids_studio/tools/render_poc.py      # renders frames, synthesises audio, encodes MP4
python kids_studio/tools/verify_video.py kids_studio/renders/ep01_sc01_poc.mp4
```

Needs only Python, numpy, Pillow and the FFmpeg binary bundled with the `imageio-ffmpeg` package. Makes no network calls.

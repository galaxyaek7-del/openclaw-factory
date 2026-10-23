# Video factory: architecture map

## Components

```
video_studio/projects/<id>.json          manifest: format, palette, voice, scenes[heading, visual, lines]
video_studio/projects/<id>.rights.json   rights manifest (status gates upload)
        |
        v
video_studio/tts.py        System.Speech -> wav per sentence -> trim_silence() -> real duration
video_studio/narrated.py   Pillow frame per sentence (heading + visual centred, burned-in subtitle)
                           -> ffmpeg clip of exactly that duration (slow zoom, fades)
                           -> concat + narration (48 kHz AAC) + soft SRT (mov_text)
                           -> output/<id>/<id>.mp4, .srt, .build.json (hashes, cues, frame layout)
        |
        v
video_studio/verify_media.py   streams, resolution, pixel format, decode errors, black, freeze,
                               silence, loudness, clipping, cue range/overlap, measured subtitle sync,
                               layout overlap, file hash vs build record
        |
        v
video_studio/youtube_upload.py  Jobs ledger (append-only JSONL, default data/video_publish_jobs.jsonl)
   LOCAL_READY -> QA_PASSED -> AWAITING_AUTHORIZATION -> UPLOAD_IN_PROGRESS
   -> UPLOADED_PRIVATE_OR_UNLISTED -> PROCESSING_VERIFIED -> PUBLICATION_AUTHORIZED -> PUBLISHED_VERIFIED
   failures: QA_FAILED, BLOCKED, UPLOAD_FAILED, NEEDS_RECONCILIATION, PROCESSING_FAILED
   gates: channels.write_gate (FACTORY_LIVE_PUBLISH), channels.write_scope upload_file scope bound to
          "yt:<sha256>", recorded human approval for publication, public read-back required
   transport: NoTransport (refuses) by default; the real YouTube Data API client is NOT BUILT
```

`kids_studio/` stays separate: it is a 3D animation pipeline with its own verifier. The two share only FFmpeg.

## Production lifecycle

| Stage | Owner | Exists | Output |
|---|---|---|---|
| Topic selection | human / product registry | partial: pilots chosen to match live products B14-001, B14-002 | manifest |
| Script + fact check | human or Claude | yes (manifest + `facts` block, test-checked for pilot B) | manifest |
| Rights review | human | manifest only; licences unresolved | `.rights.json` |
| Narration | `tts.py` | yes (English only) | wav |
| Visuals + assembly | `narrated.py` | yes (text-and-shape explainer, not animation) | mp4, srt |
| Technical QA | `verify_media.py` | yes | report |
| Editorial QA | human (rubric) | rubric defined; human listen pending | score |
| Upload (private) | `youtube_upload.py` | state machine yes, transport NOT BUILT | job state |
| Processing check | same | simulated only | job state |
| Publication | human approval + same | simulated only | job state |
| Analytics | none | NOT BUILT | none |

## Resumable loop design (not activated)

A loop step would be idempotent by construction and safe to kill at any point:

1. For each manifest in `projects/` with no `build.json` whose `manifest_sha256` matches, render (a re-render of the same manifest is skipped).
2. Verify; write the report next to the build record.
3. Register the job (job id = video sha, so the same bytes are one job); record QA.
4. `request_upload` (stops at BLOCKED until rights are CLEARED).
5. Stop. Upload, publication approval and publish are never called by the loop: they need a single-use scope and a person.

A crash mid-render leaves only `output/<id>/work/`, which the next run deletes. A crash mid-upload leaves `UPLOAD_IN_PROGRESS`, which is turned into `NEEDS_RECONCILIATION` and never retried automatically. It is not wired into `factory_loop.js`: with rights unresolved and no transport, it would only produce blocked jobs.

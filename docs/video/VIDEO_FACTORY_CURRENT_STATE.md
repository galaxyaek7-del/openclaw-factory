# Video factory: current state (verified 2026-10-23)

## Before this mandate

| Item | Finding | Evidence |
|---|---|---|
| `kids_studio/` | A real local pipeline for one children's 3D animatic (episode 1, Arabic subtitles). `ep01_animatic.mp4` is 158 s; its own verifier passes (1,896 frames, footstep sync max 4 ms, 16 subtitle cues). Style is primitive 3D; the contact sheet shows a character cut off by the frame edge. Renders are git-ignored. | `kids_studio/README.md`, `GAPS.md`, `tools/verify_video.py` |
| YouTube | No API client, no OAuth, no upload code anywhere in the repository. `revenue_os.py` labels `youtube_shorts` as `HUMAN_GATE` ("requires OAuth + human account"). | repository-wide search |
| Short-video scripts | `affiliate_launch_batch.py` produces `short_video_script` text only; nothing renders it. | source |
| Tools on the machine | FFmpeg 7.1 via `imageio_ffmpeg` (no ffmpeg on PATH, no ffprobe); Pillow 12.3; numpy; Windows System.Speech voices Zira (en-US) and Hortense/Julie/Paul (fr-FR); no Arabic voice; speech recognition installed for French only. | `video_studio.tts.installed_voices()`, PowerShell |
| Channel, account, revenue | No YouTube channel connection exists in code or config. Views, subscribers, watch time, monetization: UNKNOWN (no data source). | `.env` keys, search |

## After this mandate

- `video_studio/`: a general, manifest-driven narrated-video renderer (vertical and landscape), local speech with silence trimming, a technical media verifier that catches black/frozen/silent/truncated/unsynced output, and a fail-closed YouTube upload/publication state machine with no real transport.
- Two pilot videos rendered and verified locally (see the pilot manifest). Both are blocked from upload because their rights are UNRESOLVED.
- 26 tests, all passing locally.

## Truth line

Videos produced: 2 local pilots (internal review). Uploaded: 0. Published: 0. Channel connected: NO. Views/revenue: UNKNOWN / ZERO VERIFIED.

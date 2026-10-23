# Video factory: next actions

## Founder (authority required)

1. Watch and listen to both pilots (`video_studio/output/*/`) and decide whether this explainer style is worth pursuing.
2. Decide the voice: your own recorded narration (free, clearly licensed, also solves Arabic) or a voice service with an explicit commercial licence (possible cost; not authorized here).
3. If YouTube is wanted: create or choose the channel and a Google Cloud OAuth client (YouTube Data API v3). Do not paste secrets into chat; put them in `.env`.
4. Authorize each publication explicitly (video and visibility); uploads will always be private first.

## Engineering (safe, next)

1. Replace Windows fonts with OFL fonts committed with their licences (clears V2).
2. Add a "record your own narration" input: the renderer takes a wav per sentence instead of speech synthesis.
3. Add real product screenshots as a visual type, so each video shows the actual spreadsheet (reduces V5).
4. Build the real YouTube transport behind the existing gates only after step 3 above, with a resumable upload and quota handling, tested against the same 14 cases.
5. Thumbnails and an end card; then the loop step described in the architecture map.
6. Optional: a free local English speech recogniser to measure narration intelligibility.

## Truth

Videos uploaded: 0. Published: 0. Channel connected: no. Views, subscribers, watch time, revenue: UNKNOWN / ZERO VERIFIED.

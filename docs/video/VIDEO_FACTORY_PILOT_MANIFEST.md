# Video factory: pilot manifest

Both pilots are internal-review renders. Neither is authorized for upload or publication.

| Field | Pilot A | Pilot B |
|---|---|---|
| Project file | `video_studio/projects/pilot_a_cashflow_short.json` | `video_studio/projects/pilot_b_cap_rate_explainer.json` |
| Title | Profit is not cash: the 13-week cash flow check | Cap rate in 90 seconds, with a worked example |
| Format | vertical 1080x1920, 30 fps (Shorts-style) | landscape 1920x1080, 30 fps (explainer) |
| Audience | small business owners, freelancers | first-time rental investors |
| Supports live product | B14-001 13-Week Cash Flow Forecast | B14-002 Rental Property Deal Analyzer |
| Scenes / sentences | 4 / 11 | 4 / 11 |
| Final duration | 42.17 s (v1 was 50.5 s) | 54.27 s (v1 was 62.63 s) |
| Video | H.264 yuv420p, AAC 48 kHz, mov_text subtitles | same |
| File size | 7,053 KB | 8,269 KB |
| Manifest sha256 (first 16) | 6d4d1300f125777a | 6a1f7e59ef1b65e3 |
| Video sha256 (first 16) | ab079cd53c87ae3c | 323cd0ce1edd71a2 |
| Loudness | mean -20.0 dB, peak -2.1 dB | mean -19.9 dB, peak -2.2 dB |
| Subtitle sync (measured) | max 50 ms, mean 44 ms | max 49 ms, mean 45 ms |
| Technical verification | PASS | PASS |
| Rights | UNRESOLVED (`pilot_a_cashflow_short.rights.json`) | UNRESOLVED |
| Publishing state (dry run) | BLOCKED: rights not cleared | BLOCKED: rights not cleared |
| Output location | `video_studio/output/pilot_a_cashflow_short/` (git-ignored) | `video_studio/output/pilot_b_cap_rate_explainer/` |

Rebuild: `python -m video_studio.narrated video_studio/projects/<id>.json`, verify: `python -m video_studio.verify_media <mp4> --expect <format> --build <build.json>`. A rebuild on another day may differ in bytes (encoder timestamps); the manifest hash identifies the inputs.

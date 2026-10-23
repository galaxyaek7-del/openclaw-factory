# Video factory: production test plan

| Layer | Test | How | Pass rule |
|---|---|---|---|
| Content | Pilot B arithmetic | `test_pilot_b_facts_are_internally_consistent` | 24,000 - 1,200 - 7,800 = 15,000; 15,000/250,000 = 6% |
| Layout | Every pilot frame | `test_pilot_frames_fit_and_stay_still_within_a_scene` | content above subtitle box; no movement between cuts in a scene |
| Timing | Build with stubbed speech | `test_build_is_timed_by_the_audio_and_passes_verification` | duration equals sum of frame-rounded sentence lengths; cues ordered |
| Speech | Silence trimming | `TestTrimSilence` | 0.1 s / 0.75 s padding removed, speech kept |
| Verifier (positive) | Clean synthetic file | `test_good_file_passes` | no failures |
| Verifier (negative) | black, silent, truncated, no subtitles, wrong size | `TestVerifierCatchesDefects` | each defect reported |
| Real output | Both pilots | `python -m video_studio.verify_media ... --build` | passed, sync <= 300 ms |
| Visual | Contact sheet at each cue midpoint | scratch script, reviewed by eye | no clipping, overlap or jumps |
| Publishing | 14 cases + secrets + default transport + no network client | `TestYouTubeStateMachine` | see simulation results |
| Isolation | Production ledger untouched | dry run with temp ledger; `data/video_publish_jobs.jsonl` absent before and after | absent |

Human checks not automated: listening to the narration, judging pacing and usefulness, final editorial approval.

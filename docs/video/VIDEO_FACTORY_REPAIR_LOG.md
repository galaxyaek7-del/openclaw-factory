# Video factory: repair log

| # | Defect | Found by | Fix | Proof |
|---|---|---|---|---|
| R1 | Vertical frames top-heavy: content in the top third, empty middle | contact sheet of pilot A v1 | heading + visual drawn on a layer and centred between header and subtitles | frame preview; layout test |
| R2 | Formula boxes touching the heading | contact sheet | larger gap after heading and before formulas | frame preview |
| R3 | Text too small for phones; landscape half empty | contact sheets A v1, B v1/v2 | larger fonts per format | frame previews |
| R4 | Content jumped between cuts of the same scene (subtitle height varied) | preview comparison | free band computed from the scene's tallest subtitle | `test_pilot_frames_fit_and_stay_still_within_a_scene` |
| R5 | Hook label "$0 in the bank" read as a universal fact | review | "can be the bank balance, even in a profitable month" | manifest |
| R6 | Subtitles stayed about 750 ms after speech; 1.1 s gaps between sentences | sync measurement (silencedetect vs cue ends) | `tts.trim_silence()` removes the engine's padding before timing | sync 753 ms -> 50 ms; verifier now fails above 300 ms (shown failing on the old renders) |
| R7 | Audio at 22.05 kHz | probe | output resampled to 48 kHz | probe shows 48000 |
| R8 | Font fallback would crash where Windows fonts are absent (`.size` on default font) | portability review | `ImageFont.load_default(size)` | drawn with fonts path removed |
| R9 | Upload path wrote two events on a privacy mismatch; a dead QA condition in `request_upload` | code review before tests | one event with an error field; condition removed | state-machine tests |
| R10 | Test helper built an invalid lavfi filter for `color=c=black` | first test run | option separator chosen per filter | 26/26 |

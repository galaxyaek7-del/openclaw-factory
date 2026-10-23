# Video factory: capability matrix

States: OBSERVED (measured on real output), BUILT-TESTED, PARTIAL, NOT BUILT, BLOCKED, UNKNOWN.

| Capability | State | Evidence / limit |
|---|---|---|
| Script from manifest | BUILT-TESTED | JSON manifests; pilot B facts checked by a test |
| English narration (local, free) | OBSERVED | Zira voice; intelligibility NOT MEASURED automatically (no English recogniser) |
| Arabic narration | NOT BUILT | no Arabic voice installed |
| French narration | PARTIAL | voices installed, not used in a pilot |
| Exact sentence timing | OBSERVED | subtitle end vs measured speech end: max 50 ms (pilot A), 49 ms (pilot B) |
| Vertical 1080x1920 | OBSERVED | pilot A, 42.2 s |
| Landscape 1920x1080 | OBSERVED | pilot B, 54.3 s |
| Burned-in + soft subtitles | OBSERVED | mov_text stream + drawn subtitle box |
| Motion | PARTIAL | slow zoom, fades, progressive list highlighting; no animation, no footage |
| Cinematic / character animation | PARTIAL (kids_studio only) | primitive 3D animatic; not general |
| Background music | NOT BUILT | none licensed |
| Thumbnails | NOT BUILT | |
| Technical QA | BUILT-TESTED | verifier catches black, silent, truncated, missing subtitles, wrong size, unsynced cues |
| Editorial QA | PARTIAL | rubric + frame contact sheets; human listen pending |
| Rights tracking | BUILT-TESTED | rights manifest; UNRESOLVED blocks upload |
| Upload state machine | BUILT-TESTED | 14 offline cases, fake transport |
| Real YouTube connection | NOT BUILT | needs a Google Cloud OAuth client created by the founder |
| Channel analytics | NOT BUILT | |
| Monetization | UNKNOWN | no channel; YPP eligibility needs subscribers and watch hours |
| Scheduling in factory loop | NOT BUILT (designed) | see architecture map |
| Cost | OBSERVED $0 | all local; render time about 1 to 2 minutes per pilot |

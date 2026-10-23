# Video factory documents (2026-10-23)

Mandate: GF-VIDEO-FACTORY-VALIDATION-v1.0. Everything here was produced and tested locally; no video was uploaded, published or sent anywhere.

| Document | Purpose |
|---|---|
| [VIDEO_FACTORY_CURRENT_STATE.md](VIDEO_FACTORY_CURRENT_STATE.md) | What exists today, verified |
| [VIDEO_FACTORY_ARCHITECTURE_MAP.md](VIDEO_FACTORY_ARCHITECTURE_MAP.md) | Components, lifecycle, resumable loop design |
| [VIDEO_FACTORY_CAPABILITY_MATRIX.md](VIDEO_FACTORY_CAPABILITY_MATRIX.md) | Capability by capability, with evidence |
| [VIDEO_FACTORY_GAP_AND_RISK_REGISTER.md](VIDEO_FACTORY_GAP_AND_RISK_REGISTER.md) | Gaps V1-V12 and risks |
| [VIDEO_FACTORY_PRODUCTION_TEST_PLAN.md](VIDEO_FACTORY_PRODUCTION_TEST_PLAN.md) | What is tested and how |
| [VIDEO_FACTORY_PILOT_MANIFEST.md](VIDEO_FACTORY_PILOT_MANIFEST.md) | The two pilots, inputs and outputs |
| [VIDEO_FACTORY_QUALITY_EVALUATION.md](VIDEO_FACTORY_QUALITY_EVALUATION.md) | 0-100 rubric and scores |
| [VIDEO_FACTORY_YOUTUBE_SIMULATION_RESULTS.md](VIDEO_FACTORY_YOUTUBE_SIMULATION_RESULTS.md) | 14 offline publishing cases |
| [VIDEO_FACTORY_REPAIR_LOG.md](VIDEO_FACTORY_REPAIR_LOG.md) | Defects found and fixed |
| [VIDEO_FACTORY_REGRESSION_TEST_REPORT.md](VIDEO_FACTORY_REGRESSION_TEST_REPORT.md) | Test runs |
| [VIDEO_FACTORY_RIGHTS_AND_POLICY_CHECKLIST.md](VIDEO_FACTORY_RIGHTS_AND_POLICY_CHECKLIST.md) | Rights, disclosures, platform policy |
| [VIDEO_FACTORY_NEXT_ACTIONS.md](VIDEO_FACTORY_NEXT_ACTIONS.md) | Founder and engineering next steps |

Code: `video_studio/` (renderer, speech, verifier, YouTube state machine), tests in `tests/test_video_studio.py`. Rendered media lives in `video_studio/output/` and is never committed.

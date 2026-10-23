# Video factory: YouTube publishing simulation (offline)

All cases run against `FakeYouTube` (records calls, no network) with a temporary ledger and a temporary write-scope folder. `FACTORY_LIVE_PUBLISH` is false unless a case switches it on inside the test. Source: `tests/test_video_studio.py::TestYouTubeStateMachine`.

| # | Case | Expected | Result |
|---|---|---|---|
| 1 | Factory switch off | `WriteNotAuthorized`, zero transport calls | PASS |
| 2 | No upload authorization | refused, zero calls | PASS |
| 3 | Authorization for other bytes | refused, zero calls | PASS |
| 4 | QA report for different bytes | QA_FAILED, cannot request upload | PASS |
| 5 | Rights UNRESOLVED | BLOCKED | PASS |
| 6 | Invalid metadata (title > 100, `<`, missing made_for_kids) | BLOCKED, all three reasons named | PASS |
| 7 | Upload requested as public | refused | PASS |
| 8 | Happy path | UPLOADED_PRIVATE_OR_UNLISTED, privacy private, one call | PASS |
| 9 | Same bytes again | same job id, no second upload | PASS |
| 10 | Network failure | UPLOAD_FAILED; spent scope refused; new scope succeeds | PASS |
| 11 | Crash during upload | NEEDS_RECONCILIATION, never re-uploaded automatically | PASS |
| 12 | Platform rejects processing | PROCESSING_FAILED; publication approval refused | PASS |
| 13 | Publication | refused without approval, with weak evidence, for another video id, with switch off; PUBLISHED_VERIFIED only after approval + switch + public read-back | PASS |
| 14 | Read-back still private | stays PUBLICATION_AUTHORIZED with error, not counted | PASS |
| + | Token in an error message | ledger shows `[REDACTED]`, no token text | PASS |
| + | Default transport | `TransportNotConfigured`, UPLOAD_FAILED, no call | PASS |
| + | Module source | contains no HTTP client or Google endpoint | PASS |

## Real pilots, dry run

Both real pilot files were registered with a temporary ledger and a fake transport: QA recorded, then `request_upload` refused both with "rights not cleared (status 'UNRESOLVED')". Transport calls: none. `data/video_publish_jobs.jsonl` did not exist before or after.

No real upload, API call or channel connection happened. Real-platform behaviour (quota, processing time, actual rejection reasons) is UNKNOWN until a real transport exists.

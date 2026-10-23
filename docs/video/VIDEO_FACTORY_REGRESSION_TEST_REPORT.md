# Video factory: regression test report (2026-10-23, Windows, Python 3.14)

| Suite | Runner | Result |
|---|---|---|
| `tests/test_video_studio.py` (26 tests) | `scripts/run_python_group.py --pattern test_video_studio.py` with `CI=true` | 26 passed |
| same, with `imageio_ffmpeg` made unavailable (as on CI) | unittest | 18 passed, 8 skipped, 0 failed |
| `test_platform_write_gate.py` | CI runner | OK |
| `test_write_gate.py` | CI runner | OK |
| `test_write_scope.py` | CI runner | OK |
| `test_staged_scope_guard.py` | CI runner | OK |
| `test_description_scoped.py` | CI runner | OK |
| `test_publish_queue_write_gate.py` | CI runner | OK |

Shared security modules (`channels/write_gate.py`, `channels/write_scope.py`) were used, not changed.

## Failures met along the way (all fixed, see repair log)

1. Test helper: invalid lavfi option for `color=c=black` (R10).
2. After adding `*.rights.json`, the layout test's glob picked them up as manifests (`KeyError: 'scenes'`); the glob now excludes them.

## Verifier proven against real defects

The sync check was run on the pre-repair renders and failed both ("subtitle cues end up to 753 ms away from the speech"); after the repair both pass at 50 ms and 49 ms. The black, silent, truncated, missing-subtitle and wrong-resolution files are generated synthetically in the tests and each is reported.

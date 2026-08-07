// ADR-200 (2026-08-07): tests for runRecordDailyCommercialReadinessSnapshot(),
// the factory_loop.js side of wiring commercial_readiness.py's new
// record_commercial_readiness_snapshot() into the same daily
// (once-per-calendar-day) cadence growth_stages.py already has -- exact
// same shape as tests/test_factory_loop_daily_growth_stage_snapshot.js.
//
// maybeRecordDailyCommercialReadinessSnapshot() itself is NOT called
// here: it unconditionally writes into the real
// data/commercial_readiness_snapshots.jsonl and
// data/.commercial_readiness_snapshot_daily_marker -- calling it from an
// automated test would pollute real, live files. The real end-to-end
// success path was verified manually instead (two live calls via
// `python3 mission_control_api.py record_daily_commercial_readiness_snapshot`,
// each appending a real snapshot); the Python side has its own isolated
// unit tests in tests/test_commercial_readiness.py::TestCommercialReadinessSnapshotRecorder.
//
//   node tests/test_factory_loop_daily_commercial_readiness_snapshot.js

const assert = require('assert');
const fl = require('../factory_loop.js');

let passed = 0;
async function test(name, fn) {
  try {
    await fn();
    console.log(`ok - ${name}`);
    passed++;
  } catch (err) {
    console.error(`FAIL - ${name}`);
    console.error(err);
    process.exitCode = 1;
  }
}

async function main() {
  await test('runRecordDailyCommercialReadinessSnapshot: nonexistent interpreter -> ok:false with a spawn-error detail', async () => {
    const result = await fl.runRecordDailyCommercialReadinessSnapshot({ pythonPath: 'this-binary-does-not-exist-anywhere' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('runRecordDailyCommercialReadinessSnapshot: interpreter that cannot run mission_control_api.py -> ok:false with a parse-failure detail', async () => {
    const result = await fl.runRecordDailyCommercialReadinessSnapshot({ pythonPath: 'node' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  console.log(`\n${passed} passed`);
}

main();

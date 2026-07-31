// Enterprise Strategic Planning System (ADR-159, 2026-07-31): tests for
// runRecordDailyGrowthStageSnapshot(), the factory_loop.js side of
// wiring growth_stages.py's new record_growth_stage_snapshot() into the
// same daily (once-per-calendar-day) cadence every other report already
// has -- exact same shape as tests/test_factory_loop_daily_ai_doctor_report.js.
//
// maybeRecordDailyGrowthStageSnapshot() itself is NOT called here: it
// unconditionally writes into the real data/growth_stage_snapshots.jsonl
// and data/.growth_stage_snapshot_daily_marker -- calling it from an
// automated test would pollute real, live files. The real end-to-end
// success path was verified manually instead (two live calls: the first
// recorded a real snapshot, the second correctly no-op'd same-day); the
// Python side has its own isolated unit tests in
// tests/test_strategic_planning.py::TestGrowthStageSnapshotRecorder.
//
//   node tests/test_factory_loop_daily_growth_stage_snapshot.js

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
  await test('runRecordDailyGrowthStageSnapshot: nonexistent interpreter -> ok:false with a spawn-error detail', async () => {
    const result = await fl.runRecordDailyGrowthStageSnapshot({ pythonPath: 'this-binary-does-not-exist-anywhere' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('runRecordDailyGrowthStageSnapshot: interpreter that cannot run mission_control_api.py -> ok:false with a parse-failure detail', async () => {
    const result = await fl.runRecordDailyGrowthStageSnapshot({ pythonPath: 'node' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  console.log(`\n${passed} passed`);
}

main();

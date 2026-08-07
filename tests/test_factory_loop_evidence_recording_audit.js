// Enterprise Evidence Engine daily recording pass (2026-08-07): tests
// for runDailyEvidenceRecordingAudit(), the factory_loop.js side of
// dispatching mission_control_api.py's run_daily_evidence_recording_audit
// -- the one real caller of reality_audit.audit_all_endpoints(record_evidence=True).
// Exact same shape as tests/test_factory_loop_daily_growth_stage_snapshot.js.
//
// maybeRunDailyEvidenceRecordingAudit() itself is NOT called here: a real
// run spawns a multi-minute live audit and writes into the real
// data/evidence_ledger.jsonl and data/.evidence_recording_audit_daily_marker
// -- calling it from an automated test would incur real cost and pollute
// real, live files. The real end-to-end path was verified manually.
//
//   node tests/test_factory_loop_evidence_recording_audit.js

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
  await test('runDailyEvidenceRecordingAudit: nonexistent interpreter -> ok:false with a spawn-error detail', async () => {
    const result = await fl.runDailyEvidenceRecordingAudit({ pythonPath: 'this-binary-does-not-exist-anywhere' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('runDailyEvidenceRecordingAudit: interpreter that cannot run mission_control_api.py -> ok:false with a parse-failure detail', async () => {
    const result = await fl.runDailyEvidenceRecordingAudit({ pythonPath: 'node' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  console.log(`\n${passed} passed`);
}

main();

// V5.6 Sec 18: tests for runDailyRealityIntegrityCheck(), the
// factory_loop.js side of dispatching mission_control_api.py's
// run_daily_reality_integrity_check -- the one daily writer of
// data/reality_integrity_verdict.json. Exact same shape as
// tests/test_factory_loop_evidence_recording_audit.js.
//
// maybeRunDailyRealityIntegrityCheck() itself is NOT called here: a real
// run takes ~70s and writes the real verdict file + daily marker --
// calling it from an automated test would incur real cost and pollute
// real, live files. The real end-to-end path was verified manually
// (PASS 10/10, verdict file written).
//
//   node tests/test_factory_loop_reality_integrity_check.js

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
  await test('runDailyRealityIntegrityCheck: nonexistent interpreter -> ok:false with a spawn-error detail', async () => {
    const result = await fl.runDailyRealityIntegrityCheck({ pythonPath: 'this-binary-does-not-exist-anywhere' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('runDailyRealityIntegrityCheck: interpreter that cannot run mission_control_api.py -> ok:false with a parse-failure detail', async () => {
    const result = await fl.runDailyRealityIntegrityCheck({ pythonPath: 'node' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('runDailyRealityIntegrityCheck is exported alongside the maybe gate', async () => {
    assert.strictEqual(typeof fl.runDailyRealityIntegrityCheck, 'function');
    assert.strictEqual(typeof fl.maybeRunDailyRealityIntegrityCheck, 'function');
  });

  console.log(`\n${passed} passed`);
}

main();

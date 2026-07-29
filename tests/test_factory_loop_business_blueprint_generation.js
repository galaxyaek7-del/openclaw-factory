// Final Executive Directive (2026-07-29): tests for
// runGeneratePendingBusinessBlueprints(), the factory_loop.js side of
// wiring mission_control_api.py's generate_pending_business_blueprints
// CLI endpoint into the same daily (once-per-calendar-day) cadence
// evolution_report/ai_doctor_report/department_health_report already
// have -- exact same shape as
// tests/test_factory_loop_daily_evolution_queue_intake.js.
//
// maybeGenerateBusinessBlueprintsForNewAcceptedDecisions() itself is NOT
// called here: it appends to the real data/generated_business_blueprints
// .jsonl + writes the real daily marker file, and each real blueprint
// costs ~16s of real compute -- calling it from an automated test would
// both pollute real, live state and be slow. The real end-to-end success
// path was verified manually instead: generate_pending_business_
// blueprints() was called directly (with a temp generated_path to avoid
// touching the real ledger) against this factory's 3 real ACCEPTED
// decisions, confirmed idempotent across 2 calls (first call generated 2
// of 3, correctly reporting remaining_pending: 1; second call generated
// the last 1, correctly reporting remaining_pending: 0) -- see also the
// function's own unit tests in tests/test_autonomous_business_builder.py.
//
//   node tests/test_factory_loop_business_blueprint_generation.js

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
  await test('runGeneratePendingBusinessBlueprints: nonexistent interpreter -> ok:false with a spawn-error detail', async () => {
    const result = await fl.runGeneratePendingBusinessBlueprints({ pythonPath: 'this-binary-does-not-exist-anywhere' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('runGeneratePendingBusinessBlueprints: interpreter that cannot run mission_control_api.py -> ok:false with a parse-failure detail', async () => {
    const result = await fl.runGeneratePendingBusinessBlueprints({ pythonPath: 'node' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  console.log(`\n${passed} passed`);
}

main();

// Autonomous Company Evolution Engine, Round 4 (2026-07-29): tests for
// runEvolutionQueueDailyCycle(), the factory_loop.js side of wiring
// mission_control_api.py's evolution_queue_daily_cycle CLI endpoint into
// the same daily (once-per-calendar-day) cadence evolution_report/
// ai_doctor_report/department_health_report already have -- exact same
// shape as tests/test_factory_loop_daily_department_health_report.js.
//
// maybeGenerateDailyEvolutionQueueIntake() itself is NOT called here: it
// unconditionally mutates the real data/evolution_queue_state.json and
// writes the real daily marker file -- calling it from an automated test
// would pollute real, live state. The real end-to-end success path was
// verified manually instead: `python mission_control_api.py
// evolution_queue_daily_cycle` was run directly and its result confirmed
// real; the Python side of the underlying state machine has its own
// isolated unit tests in tests/test_evolution_queue.py.
//
//   node tests/test_factory_loop_daily_evolution_queue_intake.js

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
  await test('runEvolutionQueueDailyCycle: nonexistent interpreter -> ok:false with a spawn-error detail', async () => {
    const result = await fl.runEvolutionQueueDailyCycle({ pythonPath: 'this-binary-does-not-exist-anywhere' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('runEvolutionQueueDailyCycle: interpreter that cannot run mission_control_api.py -> ok:false with a parse-failure detail', async () => {
    const result = await fl.runEvolutionQueueDailyCycle({ pythonPath: 'node' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  console.log(`\n${passed} passed`);
}

main();

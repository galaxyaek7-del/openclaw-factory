// Revenue Mode directive (2026-07-31): tests for runPaymentStatusCheckTick(),
// the factory_loop.js side of wiring mission_control_api.py's
// check_customer_payments CLI endpoint into every tick (not daily-gated,
// same reasoning as resilience_monitor above it -- see
// test_factory_loop_resilience_monitor_tick.js for the precedent).
//
// The real success path is NOT called here: check_payment_status() (which
// check_all_awaiting_payments() calls per AWAITING_PAYMENT record) mutates
// real state (data/customer_pipeline_state.json) and fires a real founder
// Telegram notification on a real confirmed payment -- calling it from an
// automated test would risk polluting real customer-pipeline state. The
// real end-to-end success path was verified manually instead: `python
// mission_control_api.py check_customer_payments` was run directly and its
// result confirmed real (0 real AWAITING_PAYMENT records exist today, so
// it returned checked_count: 0 -- an honest, real, empty result, not a
// stub). customer_pipeline.py's own logic has its own isolated unit tests.
//
//   node tests/test_factory_loop_payment_status_check_tick.js

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
  await test('runPaymentStatusCheckTick: nonexistent interpreter -> action:failed with a spawn-error detail', async () => {
    const result = await fl.runPaymentStatusCheckTick({ pythonPath: 'this-binary-does-not-exist-anywhere' });
    assert.strictEqual(result.action, 'failed');
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('runPaymentStatusCheckTick: interpreter that cannot run mission_control_api.py -> action:failed with a parse-failure detail', async () => {
    const result = await fl.runPaymentStatusCheckTick({ pythonPath: 'node' });
    assert.strictEqual(result.action, 'failed');
    assert.ok(result.detail && result.detail.length > 0);
  });

  console.log(`\n${passed} passed`);
}

main();

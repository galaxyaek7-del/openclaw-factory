// Pricing Review Trigger (ADR-182, 2026-08-07): tests for
// runEuAiActPricingReview(), the factory_loop.js side of dispatching
// mission_control_api.py's eu_ai_act_pricing_review. Exact same shape
// as tests/test_factory_loop_evidence_recording_audit.js.
//
// maybeCheckEuAiActPricingReview() itself is NOT called here: a real
// run writes into the real data/.eu_ai_act_pricing_review_daily_marker
// -- calling it from an automated test would pollute real, live state.
// The real end-to-end path was verified manually (python
// mission_control_api.py eu_ai_act_pricing_review).
//
//   node tests/test_factory_loop_pricing_review.js

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
  await test('runEuAiActPricingReview: nonexistent interpreter -> ok:false with a spawn-error detail', async () => {
    const result = await fl.runEuAiActPricingReview({ pythonPath: 'this-binary-does-not-exist-anywhere' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('runEuAiActPricingReview: interpreter that cannot run mission_control_api.py -> ok:false with a parse-failure detail', async () => {
    const result = await fl.runEuAiActPricingReview({ pythonPath: 'node' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  console.log(`\n${passed} passed`);
}

main();

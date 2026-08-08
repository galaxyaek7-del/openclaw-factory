// Golden Hunter — Daily Commission Opportunity Scan (Phase 38b, "Chief
// Commercial Engineer" directive, ADR-234, 2026-08-08): tests for
// runCommissionOpportunityScan(), the factory_loop.js side of wiring
// commission_engine.py::rank_commission_shortlist() into the same daily
// (once-per-calendar-day) cadence every other report already has -- exact
// same shape as tests/test_factory_loop_daily_growth_stage_snapshot.js.
//
// maybeRunDailyCommissionOpportunityScan() itself is NOT called here: it
// unconditionally writes into the real data/.commission_opportunity_scan_
// daily_marker -- calling it from an automated test would touch a real
// file. The real end-to-end success path was verified manually instead
// (a live `python mission_control_api.py commission_opportunity_scan` call
// returned the real 5-opportunity shortlist). The Python side has its own
// isolated unit tests in tests/test_commission_engine.py::
// TestRankCommissionShortlist.
//
//   node tests/test_factory_loop_commission_opportunity_scan.js

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
  await test('runCommissionOpportunityScan: nonexistent interpreter -> ok:false with a spawn-error detail', async () => {
    const result = await fl.runCommissionOpportunityScan({ pythonPath: 'this-binary-does-not-exist-anywhere' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('runCommissionOpportunityScan: interpreter that cannot run mission_control_api.py -> ok:false with a parse-failure detail', async () => {
    const result = await fl.runCommissionOpportunityScan({ pythonPath: 'node' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  console.log(`\n${passed} passed`);
}

main();

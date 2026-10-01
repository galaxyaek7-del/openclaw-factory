// S3 factory need (2026-10-01): tests for runFreelancerStateMonitor() /
// maybeMonitorFreelancerStates(), the factory_loop.js side of wiring
// freelancer_monitor.py --once into every tick. Silent unless the
// monitor reports structured state changes.
//
// No network mocking here: the script reads the REAL pipeline file and
// hits the REAL public API (read-only). The failure-path tests use a bad
// interpreter (no network, no state touched). The live silent-path test
// only asserts the wrapper surfaces whatever structured result the real
// script returns -- it never triggers a commercial action.
//
//   node tests/test_factory_loop_freelancer_state_monitor.js

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
  await test('runFreelancerStateMonitor: nonexistent interpreter -> ok:false with detail', async () => {
    const result = await fl.runFreelancerStateMonitor({ pythonPath: 'this-binary-does-not-exist-anywhere' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('runFreelancerStateMonitor: bad interpreter -> ok:false with parse-failure detail', async () => {
    const result = await fl.runFreelancerStateMonitor({ pythonPath: 'node' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('maybeMonitorFreelancerStates: surfaces structured result, silent or changed, never throws', async () => {
    const result = await fl.maybeMonitorFreelancerStates();
    assert.ok(['none', 'changed', 'failed'].includes(result.action));
    assert.ok(result.detail && result.detail.length > 0);
  });

  console.log(`\n${passed} passed`);
}

main();

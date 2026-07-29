// Continuous Trust & Resilience Monitoring (2026-07-29): tests for
// runResilienceMonitorTick(), the factory_loop.js side of wiring
// mission_control_api.py's resilience_monitor_tick CLI endpoint into
// every tick (not daily-gated, unlike the report engines above it).
//
// The real success path is NOT called here: it unconditionally reads/
// mutates real state (data/incidents.jsonl) via resilience_monitor.py's
// real record_incidents_for_findings() -- calling it from an automated
// test would pollute real, live state. The real end-to-end success path
// was verified manually instead: `python mission_control_api.py
// resilience_monitor_tick` was run directly and its result confirmed
// real; resilience_monitor.py's own logic has its own isolated unit
// tests in tests/test_resilience_monitor.py.
//
//   node tests/test_factory_loop_resilience_monitor_tick.js

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
  await test('runResilienceMonitorTick: nonexistent interpreter -> action:failed with a spawn-error detail', async () => {
    const result = await fl.runResilienceMonitorTick({ pythonPath: 'this-binary-does-not-exist-anywhere' });
    assert.strictEqual(result.action, 'failed');
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('runResilienceMonitorTick: interpreter that cannot run mission_control_api.py -> action:failed with a parse-failure detail', async () => {
    const result = await fl.runResilienceMonitorTick({ pythonPath: 'node' });
    assert.strictEqual(result.action, 'failed');
    assert.ok(result.detail && result.detail.length > 0);
  });

  console.log(`\n${passed} passed`);
}

main();

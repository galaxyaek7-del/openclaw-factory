// S3 arm audit: tests for runArmStatusWatch() / maybeWatchArmStatus().
// Same discipline as the grant-resume/monitor tests: failure paths use a
// bad interpreter (no network, no state); the live path only asserts the
// wrapper surfaces a structured silent-or-changed result.
//
//   node tests/test_factory_loop_arm_status_watch.js

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
  await test('runArmStatusWatch: nonexistent interpreter -> ok:false with detail', async () => {
    const result = await fl.runArmStatusWatch({ pythonPath: 'this-binary-does-not-exist-anywhere' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('runArmStatusWatch: bad interpreter -> ok:false with parse-failure detail', async () => {
    const result = await fl.runArmStatusWatch({ pythonPath: 'node' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('maybeWatchArmStatus: surfaces structured result, never throws', async () => {
    const result = await fl.maybeWatchArmStatus();
    assert.ok(['none', 'changed', 'failed'].includes(result.action));
    assert.ok(result.detail && result.detail.length > 0);
  });

  console.log(`\n${passed} passed`);
}

main();

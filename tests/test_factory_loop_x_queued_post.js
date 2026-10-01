// S3 fruitful cycle (2026-10-01): tests for runQueuedXPost() /
// maybeSendQueuedXPost(). The real send path is NOT exercised: with a
// queued post and a clear gate it would publish a REAL tweet. CI asserts
// failure paths + the protection-hold/silent surfacing only.
//
//   node tests/test_factory_loop_x_queued_post.js

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
  await test('runQueuedXPost: nonexistent interpreter -> ok:false with detail', async () => {
    const result = await fl.runQueuedXPost({ pythonPath: 'this-binary-does-not-exist-anywhere' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('runQueuedXPost: bad interpreter -> ok:false with parse-failure detail', async () => {
    const result = await fl.runQueuedXPost({ pythonPath: 'node' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('maybeSendQueuedXPost: surfaces structured result, never throws', async () => {
    const result = await fl.maybeSendQueuedXPost();
    assert.ok(['none', 'sent', 'failed'].includes(result.action));
    assert.ok(result.detail && result.detail.length > 0);
  });

  console.log(`\n${passed} passed`);
}

main();

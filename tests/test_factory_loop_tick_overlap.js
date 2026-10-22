// Regression test for the zero-assumption audit's Medium-High finding:
// factory_loop.js's setInterval(safeTick, INTERVAL_MS) had no guard
// against a tick still running when the next one fires. If a tick ever
// takes close to or longer than the 10-minute interval (plausible once
// real, non-dry-run production/distribution calls start firing), two
// concurrent runTick() calls could each independently evaluate the same
// opportunities — duplicate production, duplicate Groq spend.
//
// Uses an injected slow tickFn (never the real runTick, which would make
// real Groq/network calls) to prove the overlap guard without touching
// anything real.
//
//   node --test tests/test_factory_loop_tick_overlap.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

// safeTick() logs skipped/failed ticks. Point that log at a temp file BEFORE
// factory_loop.js is loaded, so this test never writes "simulated tick
// failure" into the real factory_loop.log (it did, 2026-10-18).
const TMP_LOG = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'gf_loop_log_')), 'factory_loop.log');
process.env.FACTORY_LOOP_LOG_PATH = TMP_LOG;
const { safeTick } = require('../factory_loop.js');

function slowTick(callLog, delayMs = 100) {
  return async () => {
    callLog.push('start');
    await new Promise(r => setTimeout(r, delayMs));
    callLog.push('end');
  };
}

test('safeTick: a second call while the first is still running is skipped, not run concurrently', async () => {
  const callLog = [];
  const tick = slowTick(callLog, 150);

  const first = safeTick(tick);
  // Give the first call a moment to actually start before firing the second.
  await new Promise(r => setTimeout(r, 20));
  const second = safeTick(tick);

  await Promise.all([first, second]);

  // Exactly one real start/end pair — the second call must have been
  // skipped entirely, not queued or run concurrently.
  assert.deepEqual(callLog, ['start', 'end']);
});

test('safeTick: after a tick completes, the next call runs normally (guard resets)', async () => {
  const callLog = [];
  const tick = slowTick(callLog, 20);

  await safeTick(tick);
  await safeTick(tick);

  assert.deepEqual(callLog, ['start', 'end', 'start', 'end']);
});

test('safeTick: the guard resets even if the tick function throws', async () => {
  const callLog = [];
  const throwingTick = async () => {
    callLog.push('start');
    throw new Error('simulated tick failure');
  };
  const okTick = slowTick(callLog, 10);

  await safeTick(throwingTick); // safeTick itself must swallow this, never throw
  await safeTick(okTick);

  assert.deepEqual(callLog, ['start', 'start', 'end']);
});

test('safeTick: test-generated log entries go to the temp log, never the real one', async () => {
  const realLog = path.join(__dirname, '..', 'factory_loop.log');
  const realBefore = fs.existsSync(realLog) ? fs.readFileSync(realLog, 'utf8') : '';
  await safeTick(async () => { throw new Error('simulated tick failure (isolation check)'); });
  const realAfter = fs.existsSync(realLog) ? fs.readFileSync(realLog, 'utf8') : '';
  assert.ok(!realAfter.slice(realBefore.length).includes('isolation check'),
    'the real factory_loop.log must not receive test entries');
  assert.ok(fs.readFileSync(TMP_LOG, 'utf8').includes('isolation check'));
});

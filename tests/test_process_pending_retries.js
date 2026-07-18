// Tests for factory_loop.js's processPendingRetries() (Unified Recovery
// System §3, 2026-07-18). Monkey-patches lib/factory_state.js's exported
// functions directly (factory_loop.js requires the same cached module
// instance, so this affects its calls too) and lib/n8n_notify.js's
// notifyN8nProductionEvent — never touches the real data/factory_state.json
// or makes a real network call.
//
//   node --test tests/test_process_pending_retries.js

const test = require('node:test');
const assert = require('node:assert/strict');

const factoryState = require('../lib/factory_state.js');
const n8nNotify = require('../lib/n8n_notify.js');
const { processPendingRetries } = require('../factory_loop.js');

function withPatched(obj, patches, fn) {
  const originals = {};
  for (const key of Object.keys(patches)) {
    originals[key] = obj[key];
    obj[key] = patches[key];
  }
  return Promise.resolve(fn()).finally(() => {
    for (const key of Object.keys(originals)) obj[key] = originals[key];
  });
}

test('a telegram_notify entry with stored context is genuinely replayed', async () => {
  const retryEntry = {
    task: 'telegram_notify:factory_recovered', attempt: 1,
    context: { payload: { event: 'factory_recovered' }, webhookUrl: 'http://x', envVarName: 'N8N_TELEGRAM_WEBHOOK_URL' },
  };
  let clearedTask = null;
  let notifyCalledWith = null;

  await withPatched(factoryState, {
    dueRetries: () => [retryEntry],
    loadState: () => ({ pending_retries: [] }),
    clearRetry: (task) => { clearedTask = task; },
  }, () => withPatched(n8nNotify, {
    notifyN8nProductionEvent: async (payload, opts) => {
      notifyCalledWith = { payload, opts };
      return { attempted: true, success: true };
    },
  }, async () => {
    const result = await processPendingRetries();
    assert.equal(result.replayed, 1);
    assert.equal(clearedTask, 'telegram_notify:factory_recovered');
    assert.deepEqual(notifyCalledWith.payload, { event: 'factory_recovered' });
    assert.equal(notifyCalledWith.opts.attempt, 2, 'attempt must increment so backoff escalates');
  }));
});

test('a telegram_notify entry with no stored context is counted but never replayed', async () => {
  const retryEntry = { task: 'telegram_notify:recovery_completed', attempt: 1, context: null };
  let notifyCalled = false;

  await withPatched(factoryState, {
    dueRetries: () => [retryEntry],
    loadState: () => ({ pending_retries: [retryEntry] }),
    clearRetry: () => {},
  }, () => withPatched(n8nNotify, {
    notifyN8nProductionEvent: async () => { notifyCalled = true; return { success: true }; },
  }, async () => {
    const result = await processPendingRetries();
    assert.equal(notifyCalled, false);
    assert.equal(result.replayed, 0);
    assert.equal(result.still_pending, 1);
  }));
});

test('arm_publish/groq_generation entries are counted, never replayed in this pass', async () => {
  const entries = [
    { task: 'arm_publish:paddle:PROD-1', attempt: 1, context: null },
    { task: 'groq_generation', attempt: 1, context: null },
  ];
  let notifyCalled = false;

  await withPatched(factoryState, {
    dueRetries: () => entries,
    loadState: () => ({ pending_retries: entries }),
    clearRetry: () => {},
  }, () => withPatched(n8nNotify, {
    notifyN8nProductionEvent: async () => { notifyCalled = true; return { success: true }; },
  }, async () => {
    const result = await processPendingRetries();
    assert.equal(notifyCalled, false);
    assert.equal(result.replayed, 0);
    assert.equal(result.still_pending, 2);
  }));
});

test('an empty queue processes cleanly with zero replays', async () => {
  await withPatched(factoryState, {
    dueRetries: () => [],
    loadState: () => ({ pending_retries: [] }),
  }, async () => {
    const result = await processPendingRetries();
    assert.equal(result.processed, 0);
    assert.equal(result.replayed, 0);
  });
});

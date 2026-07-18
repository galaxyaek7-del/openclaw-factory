// Tests for lib/factory_state.js (Operational Resilience Architecture,
// Phase A, 2026-07-18): the Factory State Manager's JS side. Mirrors
// tests/test_factory_state.py's coverage. Never touches the real
// data/factory_state.json -- every test passes an explicit temp path.
//
//   node --test tests/test_factory_state.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const factoryState = require('../lib/factory_state.js');

function tempPath() {
  return path.join(os.tmpdir(), `factory_state_test_${Date.now()}_${Math.random().toString(36).slice(2)}.json`);
}

function cleanup(p) {
  if (fs.existsSync(p)) fs.unlinkSync(p);
  const dir = path.dirname(p);
  const base = path.basename(p);
  for (const entry of fs.readdirSync(dir)) {
    if (entry.startsWith(`${base}.tmp-`)) fs.unlinkSync(path.join(dir, entry));
  }
}

test('missing file reads as the safe default', () => {
  const p = tempPath();
  try {
    const state = factoryState.loadState(p);
    assert.equal(state.current_task, null);
    assert.deepEqual(state.pending_retries, []);
  } finally {
    cleanup(p);
  }
});

test('corrupt file reads as the safe default, never throws', () => {
  const p = tempPath();
  try {
    fs.writeFileSync(p, '{not valid json');
    const state = factoryState.loadState(p);
    assert.equal(state.current_task, null);
  } finally {
    cleanup(p);
  }
});

test('non-object JSON reads as the safe default', () => {
  const p = tempPath();
  try {
    fs.writeFileSync(p, JSON.stringify([1, 2, 3]));
    const state = factoryState.loadState(p);
    assert.deepEqual(state, factoryState.defaultState());
  } finally {
    cleanup(p);
  }
});

test('saveState is atomic - no leftover tmp file after a real save', () => {
  const p = tempPath();
  try {
    factoryState.saveState(factoryState.defaultState(), p);
    assert.equal(fs.existsSync(p), true);
    const dir = path.dirname(p);
    const leftover = fs.readdirSync(dir).filter(e => e.startsWith(`${path.basename(p)}.tmp-`));
    assert.deepEqual(leftover, []);
  } finally {
    cleanup(p);
  }
});

test('save then load round-trips', () => {
  const p = tempPath();
  try {
    const state = factoryState.defaultState();
    state.active_workflow = 'test_workflow';
    factoryState.saveState(state, p);
    const loaded = factoryState.loadState(p);
    assert.equal(loaded.active_workflow, 'test_workflow');
  } finally {
    cleanup(p);
  }
});

test('setCurrentTask marks in-flight, clearCurrentTask resolves it', () => {
  const p = tempPath();
  try {
    factoryState.setCurrentTask('golden_hunter_tick', 'sales_poll', null, p);
    let state = factoryState.loadState(p);
    assert.equal(state.current_task.name, 'golden_hunter_tick');
    assert.equal(state.current_task.step, 'sales_poll');
    assert.equal(state.active_workflow, 'golden_hunter_tick');

    factoryState.clearCurrentTask(p);
    state = factoryState.loadState(p);
    assert.equal(state.current_task, null);
  } finally {
    cleanup(p);
  }
});

test('a never-cleared task stays in-flight - this is the crash evidence', () => {
  const p = tempPath();
  try {
    factoryState.setCurrentTask('golden_hunter_tick', 'hunt', 'key1', p);
    const state = factoryState.loadState(p);
    assert.notEqual(state.current_task, null);
    assert.equal(state.current_task.idempotency_key, 'key1');
  } finally {
    cleanup(p);
  }
});

test('recordCheckpoint stores the last real success', () => {
  const p = tempPath();
  try {
    factoryState.recordCheckpoint('learning', 'key2', p);
    const state = factoryState.loadState(p);
    assert.equal(state.last_successful_checkpoint.stage, 'learning');
    assert.equal(state.last_successful_checkpoint.idempotency_key, 'key2');
  } finally {
    cleanup(p);
  }
});

test('enqueueRetry and dueRetries round-trip a queued failure', () => {
  const p = tempPath();
  try {
    factoryState.enqueueRetry('telegram_notify', new Error('ECONNREFUSED'), p);
    const due = factoryState.dueRetries(p);
    assert.equal(due.length, 1);
    assert.equal(due[0].task, 'telegram_notify');
    assert.match(due[0].last_error, /ECONNREFUSED/);
  } finally {
    cleanup(p);
  }
});

test('clearRetry removes only the matching task', () => {
  const p = tempPath();
  try {
    factoryState.enqueueRetry('telegram_notify', 'err1', p);
    factoryState.enqueueRetry('paddle_publish', 'err2', p);
    factoryState.clearRetry('telegram_notify', p);
    const due = factoryState.dueRetries(p);
    assert.deepEqual(due.map(r => r.task), ['paddle_publish']);
  } finally {
    cleanup(p);
  }
});

test('mutators never throw even when the underlying write genuinely fails', () => {
  // Pointing statePath at a real, existing directory (not a file) makes
  // the rename step fail (EISDIR/EPERM on every platform) - proves the
  // "never break the caller" contract holds even when the write
  // structurally cannot succeed, not just when the target is missing.
  const badPath = os.tmpdir();
  assert.doesNotThrow(() => factoryState.setCurrentTask('x', 'y', null, badPath));
  assert.doesNotThrow(() => factoryState.clearCurrentTask(badPath));
  assert.doesNotThrow(() => factoryState.recordCheckpoint('x', 'y', badPath));
  assert.doesNotThrow(() => factoryState.enqueueRetry('x', 'err', badPath));
  assert.doesNotThrow(() => factoryState.clearRetry('x', badPath));
});

// Unified Recovery System §3: attempt=1 is due immediately (the factory's
// own ~10min tick cadence already exceeds any sub-minute backoff);
// attempt 2+ escalates 60s, 120s, 240s..., capped at 1h.

test('backoffSeconds schedule', () => {
  assert.equal(factoryState.backoffSeconds(1), 0);
  assert.equal(factoryState.backoffSeconds(2), 60);
  assert.equal(factoryState.backoffSeconds(3), 120);
  assert.equal(factoryState.backoffSeconds(4), 240);
});

test('backoffSeconds caps at one hour', () => {
  assert.equal(factoryState.backoffSeconds(20), 3600);
});

test('first attempt is immediately due', () => {
  const p = tempPath();
  try {
    factoryState.enqueueRetry('groq_generation', 'timeout', p, 1);
    const due = factoryState.dueRetries(p);
    assert.equal(due.length, 1);
  } finally {
    cleanup(p);
  }
});

test('second attempt is not due within the backoff window', () => {
  const p = tempPath();
  try {
    factoryState.enqueueRetry('groq_generation', 'timeout', p, 2);
    const due = factoryState.dueRetries(p);
    assert.deepEqual(due, []);
  } finally {
    cleanup(p);
  }
});

test('entry missing next_retry_at is treated as immediately due', () => {
  const p = tempPath();
  try {
    const state = factoryState.loadState(p);
    state.pending_retries.push({ task: 'legacy_task', last_error: 'x' });
    factoryState.saveState(state, p);
    const due = factoryState.dueRetries(p);
    assert.equal(due.length, 1);
  } finally {
    cleanup(p);
  }
});

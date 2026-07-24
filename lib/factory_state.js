// Galaxy Forge — Factory State Manager, JS side (Operational
// Resilience Architecture, Phase A, 2026-07-18).
//
// Mirrors factory_state.py exactly — both languages read/write the SAME
// data/factory_state.json, same atomic tmp-file-then-rename write
// server.js's saveFin()/channels/ledger.py's reconcile_ledger_to_finance()
// already use (the proven cross-language-shared-file precedent from
// ADR-077's finance_data.json). A corrupt/missing file never throws —
// every read falls back to the safe default.
//
// Phase A scope only: plumbing. Nothing here yet acts on recovery_info/
// pending_retries (Phase B/C) — wiring this in changes no existing
// behavior, it only adds a new, accurate, disk-persisted view.

const fs = require('fs');
const path = require('path');

const DEFAULT_STATE_PATH = path.join(__dirname, '..', 'data', 'factory_state.json');

function defaultState() {
  return {
    current_task: null,
    active_workflow: null,
    queue: null,
    last_successful_checkpoint: null,
    recovery_info: { interrupted: false, detected_at: null, evidence: null, reason: null },
    pending_retries: [],
    updated_at: null,
  };
}

function loadState(statePath = DEFAULT_STATE_PATH) {
  if (!fs.existsSync(statePath)) return defaultState();
  let raw;
  try {
    raw = fs.readFileSync(statePath, 'utf8');
  } catch {
    return defaultState();
  }
  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return defaultState();
  }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return defaultState();

  const state = defaultState();
  for (const key of Object.keys(state)) {
    if (key in parsed) state[key] = parsed[key];
  }
  return state;
}

function saveState(state, statePath = DEFAULT_STATE_PATH) {
  fs.mkdirSync(path.dirname(statePath), { recursive: true });
  state.updated_at = new Date().toISOString();
  const tmpPath = `${statePath}.tmp-${process.pid}`;
  fs.writeFileSync(tmpPath, JSON.stringify(state, null, 2));
  fs.renameSync(tmpPath, statePath);
  return state;
}

// Every mutator below must never throw back into its caller — this is
// new instrumentation layered onto already-working code (factory_loop.js's
// tick, orchestrator stages); a disk error writing factory_state.json
// must never break the real work it's merely observing. Same discipline
// as appendLoopLog()'s own try/catch.

function setCurrentTask(name, step = null, idempotencyKey = null, statePath = DEFAULT_STATE_PATH) {
  try {
    const state = loadState(statePath);
    state.current_task = { name, step, idempotency_key: idempotencyKey, started_at: new Date().toISOString() };
    state.active_workflow = name;
    return saveState(state, statePath);
  } catch (err) {
    console.error('[factory_state] setCurrentTask failed:', err.message);
    return null;
  }
}

function clearCurrentTask(statePath = DEFAULT_STATE_PATH) {
  try {
    const state = loadState(statePath);
    state.current_task = null;
    return saveState(state, statePath);
  } catch (err) {
    console.error('[factory_state] clearCurrentTask failed:', err.message);
    return null;
  }
}

function recordCheckpoint(stage, idempotencyKey, statePath = DEFAULT_STATE_PATH) {
  try {
    const state = loadState(statePath);
    state.last_successful_checkpoint = { stage, idempotency_key: idempotencyKey, at: new Date().toISOString() };
    return saveState(state, statePath);
  } catch (err) {
    console.error('[factory_state] recordCheckpoint failed:', err.message);
    return null;
  }
}

const MAX_BACKOFF_SECONDS = 3600; // 1 hour ceiling

// 0s, 60s, 120s, 240s, ... capped at 1h (Unified Recovery System §3).
// attempt is 1-indexed. The first failure (attempt=1) is due immediately
// -- the factory's own tick cadence (~10 minutes) is already a longer
// wait than any sub-minute backoff would add, so escalating backoff only
// matters from the second consecutive failure onward.
function backoffSeconds(attempt) {
  if (attempt <= 1) return 0;
  return Math.min(60 * (2 ** (attempt - 2)), MAX_BACKOFF_SECONDS);
}

// context (Unified Recovery System §3, 2026-07-18): an optional, small,
// JSON-serializable snapshot of what's needed to actually replay this
// specific action (e.g. { payload, webhookUrl, envVarName } for a
// Telegram notify) -- without it, process_pending_retries() can only
// count/report the entry, never replay it. Omitted (every caller before
// this existed) reproduces the exact prior shape.
function enqueueRetry(task, error, statePath = DEFAULT_STATE_PATH, attempt = 1, context = null) {
  try {
    const state = loadState(statePath);
    const now = Date.now();
    state.pending_retries.push({
      task, last_error: error && error.message ? error.message : String(error), attempt, context,
      queued_at: new Date(now).toISOString(),
      next_retry_at: new Date(now + backoffSeconds(attempt) * 1000).toISOString(),
    });
    return saveState(state, statePath);
  } catch (err) {
    console.error('[factory_state] enqueueRetry failed:', err.message);
    return null;
  }
}

function dueRetries(statePath = DEFAULT_STATE_PATH) {
  const now = Date.now();
  return loadState(statePath).pending_retries.filter((r) => {
    if (!r.next_retry_at) return true;
    const t = Date.parse(r.next_retry_at);
    return Number.isNaN(t) || t <= now;
  });
}

function clearRetry(task, statePath = DEFAULT_STATE_PATH) {
  try {
    const state = loadState(statePath);
    state.pending_retries = state.pending_retries.filter(r => r.task !== task);
    return saveState(state, statePath);
  } catch (err) {
    console.error('[factory_state] clearRetry failed:', err.message);
    return null;
  }
}

module.exports = {
  DEFAULT_STATE_PATH, defaultState, loadState, saveState,
  setCurrentTask, clearCurrentTask, recordCheckpoint,
  enqueueRetry, dueRetries, clearRetry, backoffSeconds,
};

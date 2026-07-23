// Tests for scripts/supervisor.js (Enterprise Upgrade Roadmap Phase 1.1,
// 2026-07-23). Spawns the real supervisor as a subprocess against real
// fixture scripts (tests/fixtures/) rather than mocking child_process —
// this is exactly the integration behavior (does a crashed child
// actually get restarted, does a crash loop actually get capped) that
// matters, and mocking spawn() would only prove the mock behaves as
// mocked.
//
// Signal-forwarding (SIGINT/SIGTERM -> clean child shutdown, no orphan)
// is deliberately NOT covered by an automated OS-signal test here —
// Windows' signal emulation for child Node processes is fragile enough
// that an automated test would be testing Node's platform shims more
// than this module's own logic. It was verified live instead: see
// ENTERPRISE_UPGRADE_ROADMAP.md's execution log for the real manual
// verification (start supervisor, confirm server.js comes up, send a
// real shutdown, confirm clean exit and no orphan process).
//
//   node --test tests/test_supervisor.js

const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('path');
const fs = require('fs');
const os = require('os');
const { spawn } = require('child_process');

const REPO_ROOT = path.join(__dirname, '..');
const SUPERVISOR_SCRIPT = path.join(REPO_ROOT, 'scripts', 'supervisor.js');

function runSupervisor(env, timeoutMs = 15000) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [SUPERVISOR_SCRIPT], {
      cwd: REPO_ROOT,
      env: { ...process.env, ...env },
    });
    let stdout = '';
    child.stdout.on('data', (d) => { stdout += d; });
    child.stderr.on('data', (d) => { stdout += d; });
    const timer = setTimeout(() => {
      child.kill('SIGKILL');
      reject(new Error(`supervisor did not exit within ${timeoutMs}ms\n${stdout}`));
    }, timeoutMs);
    child.on('exit', (code) => {
      clearTimeout(timer);
      resolve({ code, stdout });
    });
  });
}

function tempFilePath(name) {
  return path.join(os.tmpdir(), `supervisor_test_${name}_${Date.now()}_${Math.random().toString(36).slice(2)}`);
}

test('restarts a crashing child until it succeeds, then exits cleanly', async () => {
  const counterFile = tempFilePath('counter');
  try {
    const result = await runSupervisor({
      SUPERVISOR_TARGET: path.join(__dirname, 'fixtures', 'crash_n_times.js'),
      CRASH_COUNTER_FILE: counterFile,
      CRASH_N: '2',
      SUPERVISOR_BACKOFF_MS: '50',
      SUPERVISOR_MAX_RESTARTS: '5',
      SUPERVISOR_WINDOW_MS: '10000',
    });
    assert.equal(result.code, 0, result.stdout);
    const finalCount = parseInt(fs.readFileSync(counterFile, 'utf8'), 10);
    assert.equal(finalCount, 3, 'child should have run 3 times: 2 crashes + 1 real success');
    assert.match(result.stdout, /"event":"crash"/);
    assert.match(result.stdout, /"event":"restarting"/);
    assert.match(result.stdout, /"event":"clean_exit"/);
  } finally {
    fs.rmSync(counterFile, { force: true });
  }
});

test('gives up and exits non-zero after exceeding the crash-loop guard', async () => {
  const result = await runSupervisor({
    SUPERVISOR_TARGET: path.join(__dirname, 'fixtures', 'always_crash.js'),
    SUPERVISOR_BACKOFF_MS: '20',
    SUPERVISOR_MAX_RESTARTS: '3',
    SUPERVISOR_WINDOW_MS: '10000',
  });
  assert.equal(result.code, 1, result.stdout);
  assert.match(result.stdout, /"event":"giving_up"/);
  const crashCount = (result.stdout.match(/"event":"crash"/g) || []).length;
  assert.equal(crashCount, 3, 'must stop restarting at exactly SUPERVISOR_MAX_RESTARTS, not before or after');
});

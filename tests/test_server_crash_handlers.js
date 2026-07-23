// Tests for server.js's uncaughtException/unhandledRejection handlers
// (Enterprise Upgrade Roadmap Phase 1.1, 2026-07-23). Spawns the real
// server.js with a test-only fault-injection env var
// (__OPENCLAW_TEST_FORCE_CRASH__) rather than reimplementing the
// handler logic in a test file — this proves the real production code
// actually logs and exits non-zero on a real crash, not a copy of it.
//
// server_crashes.log has no path override (unlike this factory's
// data/*.jsonl convention) — deliberately: it's the same gitignored,
// accumulates-over-real-operational-history convention already used by
// factory_loop.log/scout_runs.log/finance_errors.log at the repo root,
// so a few real test-crash entries landing in it is consistent with how
// every other .log file here already behaves, not a new pollution risk.
//
//   node --test tests/test_server_crash_handlers.js

const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');

const REPO_ROOT = path.join(__dirname, '..');
const SERVER_SCRIPT = path.join(REPO_ROOT, 'server.js');
const CRASH_LOG_PATH = path.join(REPO_ROOT, 'server_crashes.log');

function runServerAndForceCrash(kind, timeoutMs = 10000) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [SERVER_SCRIPT], {
      cwd: REPO_ROOT,
      env: {
        ...process.env,
        __OPENCLAW_TEST_FORCE_CRASH__: kind,
        MISSION_CONTROL_PASSWORD: 'crash-handler-test-password',
        PORT: '0', // unused in the uncaughtException case (crashes before listen); harmless otherwise
      },
    });
    let stdout = '';
    child.stdout.on('data', (d) => { stdout += d; });
    child.stderr.on('data', (d) => { stdout += d; });
    const timer = setTimeout(() => {
      child.kill('SIGKILL');
      reject(new Error(`server.js did not exit within ${timeoutMs}ms for kind=${kind}\n${stdout}`));
    }, timeoutMs);
    child.on('exit', (code) => {
      clearTimeout(timer);
      resolve({ code, stdout });
    });
  });
}

function lastLogLine() {
  const lines = fs.readFileSync(CRASH_LOG_PATH, 'utf8').trim().split('\n');
  return JSON.parse(lines[lines.length - 1]);
}

test('a real uncaughtException is logged to server_crashes.log and exits non-zero', async () => {
  const before = fs.existsSync(CRASH_LOG_PATH) ? fs.statSync(CRASH_LOG_PATH).size : 0;
  const result = await runServerAndForceCrash('uncaughtException');
  assert.equal(result.code, 1, result.stdout);
  assert.match(result.stdout, /uncaughtException/);
  const after = fs.statSync(CRASH_LOG_PATH).size;
  assert.ok(after > before, 'server_crashes.log must have grown by a real appended entry');
  const entry = lastLogLine();
  assert.equal(entry.kind, 'uncaughtException');
  assert.match(entry.message, /deliberate test crash/);
  assert.ok(entry.stack, 'a real stack trace must be recorded, not just a message');
});

test('a real unhandledRejection is logged to server_crashes.log and exits non-zero', async () => {
  const before = fs.existsSync(CRASH_LOG_PATH) ? fs.statSync(CRASH_LOG_PATH).size : 0;
  const result = await runServerAndForceCrash('unhandledRejection');
  assert.equal(result.code, 1, result.stdout);
  assert.match(result.stdout, /unhandledRejection/);
  const after = fs.statSync(CRASH_LOG_PATH).size;
  assert.ok(after > before, 'server_crashes.log must have grown by a real appended entry');
  const entry = lastLogLine();
  assert.equal(entry.kind, 'unhandledRejection');
  assert.match(entry.message, /deliberate test crash/);
});

// child_process.kill('SIGTERM'/'SIGINT') on Windows unconditionally
// hard-terminates the target (proven live while writing this test —
// exit code comes back null, the handler never runs) rather than
// delivering a graceful signal process.on() can intercept. That's a
// real, documented Node-on-Windows platform limitation in how the OS
// delivers the signal, not something this codebase's handler logic
// controls — real interactive Ctrl+C in an attached console (the actual
// day-to-day shutdown path) reaches process.on('SIGINT') correctly, the
// same as any standard Node CLI tool on Windows, but isn't reproducible
// from a non-interactive automated test. What this test verifies
// instead, for real: that handleShutdownSignal() in server.js behaves
// correctly once Node actually emits the SIGINT/SIGTERM event, via the
// same test-only hook pattern already used above for the crash handlers
// (__OPENCLAW_TEST_EMIT_SHUTDOWN_SIGNAL__ triggers a real
// process.emit(), not a reimplementation of the handler).
for (const signal of ['SIGINT', 'SIGTERM']) {
  test(`a real ${signal} event exits 0 cleanly, never touching server_crashes.log`, async () => {
    const before = fs.existsSync(CRASH_LOG_PATH) ? fs.statSync(CRASH_LOG_PATH).size : 0;
    const result = await new Promise((resolve, reject) => {
      const child = spawn(process.execPath, [SERVER_SCRIPT], {
        cwd: REPO_ROOT,
        env: {
          ...process.env,
          __OPENCLAW_TEST_EMIT_SHUTDOWN_SIGNAL__: signal,
          MISSION_CONTROL_PASSWORD: 'crash-handler-test-password',
          PORT: '3987',
        },
      });
      let stdout = '';
      child.stdout.on('data', (d) => { stdout += d; });
      child.stderr.on('data', (d) => { stdout += d; });
      const timer = setTimeout(() => {
        child.kill('SIGKILL');
        reject(new Error(`server.js did not exit cleanly within timeout\n${stdout}`));
      }, 10000);
      child.on('exit', (code) => {
        clearTimeout(timer);
        resolve({ code, stdout });
      });
    });
    assert.equal(result.code, 0, result.stdout);
    assert.match(result.stdout, new RegExp(`${signal} received`));
    const after = fs.existsSync(CRASH_LOG_PATH) ? fs.statSync(CRASH_LOG_PATH).size : 0;
    assert.equal(after, before, 'a clean, intentional shutdown must never write to the crash log');
  });
}

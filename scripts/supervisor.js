// Process supervisor (Enterprise Upgrade Roadmap Phase 1.1, 2026-07-23).
//
// Real finding this closes: server.js has only ever been run manually
// (`node server.js`) with nothing to restart it after a crash — a
// single unhandled exception (now logged and exited cleanly by
// server.js's own new handlers) previously meant total, silent outage
// until a human happened to notice and restart it by hand.
//
// This is a self-contained, in-repo wrapper — not a new system-level
// dependency (no pm2, no Windows Service/NSSM install). It is opt-in:
// start the factory with `node scripts/supervisor.js` instead of
// `node server.js` directly. CLAUDE.md's "Running the project" section
// documents both; nothing about the existing manual-start workflow is
// removed or silently changed.
//
// Crash-loop guard: a real repeated-crash scenario (e.g. a bad config
// change) must not spin CPU/restart forever — after too many restarts
// within a short window, the supervisor gives up, alerts, and exits
// non-zero rather than looping indefinitely.
//
// Orphan-process discipline (DISASTER_RECOVERY_PLAN.md's own real
// finding: `taskkill /F` without `/T` does not kill child processes on
// Windows): SIGINT/SIGTERM received by the supervisor is forwarded to
// the child, and the supervisor waits for the child's own 'exit' event
// before exiting itself, so the supervisor process itself is never
// orphaned from its child's lifecycle.
//
// Real, tested Windows caveat (found writing this module's own test
// suite): child_process.kill() on Windows unconditionally hard-
// terminates the target rather than delivering a signal the child's own
// process.on('SIGINT'/'SIGTERM') handler can gracefully react to — so
// forwardSignal() below reliably stops the child (Node still emits a
// real 'exit' event for it), but on Windows specifically it is a hard
// stop, not the child's own graceful-shutdown path. Real interactive
// Ctrl+C on this supervisor's own console (not a programmatic kill())
// reaches both processes' process.on('SIGINT') correctly via Windows'
// normal console-event delivery, since the child is spawned attached
// (not `detached: true`) — that remains the graceful path in practice.
// On Linux/macOS, forwardSignal() below delivers a real POSIX signal
// either way, so the child's own graceful handler runs regardless of
// how the shutdown was triggered.
//
//   node scripts/supervisor.js
//   SUPERVISOR_TARGET=path/to/other_script.js node scripts/supervisor.js  (testing only)

const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');

const REPO_ROOT = path.join(__dirname, '..');
const SUPERVISOR_LOG_PATH = path.join(REPO_ROOT, 'supervisor.log');

const TARGET_SCRIPT = process.env.SUPERVISOR_TARGET || path.join(REPO_ROOT, 'server.js');
const MAX_RESTARTS = parseInt(process.env.SUPERVISOR_MAX_RESTARTS || '5', 10);
const WINDOW_MS = parseInt(process.env.SUPERVISOR_WINDOW_MS || String(60 * 1000), 10);
const BACKOFF_MS = parseInt(process.env.SUPERVISOR_BACKOFF_MS || '2000', 10);

function log(entry) {
  const line = JSON.stringify({ at: new Date().toISOString(), ...entry });
  console.log(`[supervisor] ${line}`);
  try {
    fs.appendFileSync(SUPERVISOR_LOG_PATH, line + '\n');
  } catch { /* a failing supervisor-log write must never block supervision itself */ }
}

let child = null;
let stopping = false;
const restartTimestamps = [];

function alertGivingUp(reason) {
  try {
    const telegramDirect = require(path.join(REPO_ROOT, 'lib', 'telegram_direct'));
    telegramDirect
      .sendTelegramMessage(telegramDirect.buildCriticalErrorMessage([
        `supervisor: توقف عن إعادة تشغيل ${path.basename(TARGET_SCRIPT)} — ${reason}`,
      ]))
      .catch(() => {});
  } catch { /* best-effort only — a failed alert must never block the real shutdown */ }
}

function withinCrashLoopLimit() {
  const now = Date.now();
  while (restartTimestamps.length && now - restartTimestamps[0] > WINDOW_MS) {
    restartTimestamps.shift();
  }
  return restartTimestamps.length < MAX_RESTARTS;
}

function spawnChild() {
  log({ event: 'spawn', target: TARGET_SCRIPT });
  child = spawn(process.execPath, [TARGET_SCRIPT], {
    cwd: REPO_ROOT,
    stdio: 'inherit',
    env: process.env,
  });

  child.on('exit', (code, signal) => {
    if (stopping) {
      log({ event: 'child_exited_during_shutdown', code, signal });
      process.exit(0);
      return;
    }

    if (code === 0) {
      log({ event: 'clean_exit', code });
      process.exit(0);
      return;
    }

    log({ event: 'crash', code, signal });
    restartTimestamps.push(Date.now());
    if (!withinCrashLoopLimit()) {
      const reason = `${restartTimestamps.length} restarts within ${WINDOW_MS}ms — crash-loop guard tripped`;
      log({ event: 'giving_up', reason });
      alertGivingUp(reason);
      process.exit(1);
      return;
    }

    log({ event: 'restarting', after_ms: BACKOFF_MS });
    setTimeout(spawnChild, BACKOFF_MS);
  });
}

function forwardSignal(signal) {
  if (stopping) return;
  stopping = true;
  log({ event: 'shutdown_signal_received', signal });
  if (child && !child.killed) {
    child.kill(signal);
  } else {
    process.exit(0);
  }
}

process.on('SIGINT', () => forwardSignal('SIGINT'));
process.on('SIGTERM', () => forwardSignal('SIGTERM'));

if (require.main === module) {
  spawnChild();
}

module.exports = { spawnChild, withinCrashLoopLimit, restartTimestamps, MAX_RESTARTS, WINDOW_MS };

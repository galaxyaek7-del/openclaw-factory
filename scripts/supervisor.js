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
const SUPERVISOR_LOG_PATH = process.env.SUPERVISOR_LOG_PATH || path.join(REPO_ROOT, 'supervisor.log');

const TARGET_SCRIPT = process.env.SUPERVISOR_TARGET || path.join(REPO_ROOT, 'server.js');
const MAX_RESTARTS = parseInt(process.env.SUPERVISOR_MAX_RESTARTS || '5', 10);
const WINDOW_MS = parseInt(process.env.SUPERVISOR_WINDOW_MS || String(60 * 1000), 10);
const COOLDOWN_MS = parseInt(process.env.SUPERVISOR_COOLDOWN_MS === undefined ? String(5 * 60 * 1000) : process.env.SUPERVISOR_COOLDOWN_MS, 10);
// Hang watchdog: a child that is alive but silent (its heartbeat file not touched for STALE_MS) is killed so it restarts.
const HEARTBEAT_FILE = process.env.SUPERVISOR_HEARTBEAT_FILE || '';
const STALE_MS = parseInt(process.env.SUPERVISOR_STALE_MS || String(45 * 60 * 1000), 10);
const BACKOFF_MS = parseInt(process.env.SUPERVISOR_BACKOFF_MS || '2000', 10);
// Log rotation: an unbounded supervisor.log on a long-running process is the
// same real defect rotateLoopLog() fixed for factory_loop.log (2026-11-18).
const SUPERVISOR_LOG_MAX_BYTES = parseInt(process.env.SUPERVISOR_LOG_MAX_BYTES || String(8 * 1024 * 1024), 10);
const SUPERVISOR_LOG_KEEP = parseInt(process.env.SUPERVISOR_LOG_KEEP || '3', 10);
// Kill switch (TASKS.md item 5): a STOP file in the repo root stops supervision.
const STOP_FILE = process.env.SUPERVISOR_STOP_FILE || path.join(REPO_ROOT, 'STOP');

function rotateLog(file, { maxBytes = SUPERVISOR_LOG_MAX_BYTES, keep = SUPERVISOR_LOG_KEEP } = {}) {
  try {
    if (fs.statSync(file).size < maxBytes) return false;
  } catch { return false; }
  try {
    if (keep <= 0) {
      fs.writeFileSync(file, '');
      return true;
    }
    for (let i = keep; i >= 1; i -= 1) {
      const from = i === 1 ? file : `${file}.${i - 1}`;
      const to = `${file}.${i}`;
      try { fs.renameSync(from, to); } catch { /* an absent older generation is fine */ }
    }
    return true;
  } catch { return false; }
}

function log(entry) {
  const line = JSON.stringify({ at: new Date().toISOString(), ...entry });
  console.log(`[supervisor] ${line}`);
  try {
    rotateLog(SUPERVISOR_LOG_PATH);
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

// Enterprise Upgrade Roadmap Phase 1.2 (2026-07-23): the real gap found
// in this same commit's own research -- a single real crash that DID
// get successfully restarted was previously completely silent, only
// alertGivingUp() (above) ever notified anyone, and only once the
// crash-loop guard had already been fully exhausted. MTTD for a real,
// isolated crash was therefore unbounded (a human had to notice by
// hand). Every real crash now alerts immediately, in real time --
// bounded naturally by the same crash-loop guard that already caps
// restartTimestamps within WINDOW_MS, so this can never spam beyond
// MAX_RESTARTS real alerts per real crash-loop episode.
function alertCrashRestart(code, signal, restartCount) {
  try {
    const telegramDirect = require(path.join(REPO_ROOT, 'lib', 'telegram_direct'));
    telegramDirect
      .sendTelegramMessage(
        `⚠️ ${path.basename(TARGET_SCRIPT)} تعطّل (code=${code}, signal=${signal || 'none'}) — إعادة تشغيل تلقائية رقم ${restartCount}`,
      )
      .catch(() => {});
  } catch { /* best-effort only — a failed alert must never block the real restart */ }
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

    if (code === 0 && !(COOLDOWN_MS && process.env.SUPERVISOR_RESTART_ON_CLEAN_EXIT === 'true')) {
      log({ event: 'clean_exit', code });
      process.exit(0);
      return;
    }

    log({ event: 'crash', code, signal });
    restartTimestamps.push(Date.now());
    alertCrashRestart(code, signal, restartTimestamps.length);
    if (!withinCrashLoopLimit()) {
      const reason = `${restartTimestamps.length} restarts within ${WINDOW_MS}ms — crash-loop guard tripped`;
      log({ event: 'giving_up', reason });
      alertGivingUp(reason);
      if (!COOLDOWN_MS) { process.exit(1); return; }
      // 2026-11-07 (founder: the factory must never stop): a crash loop pauses, it does not end supervision.
      restartTimestamps.length = 0;
      log({ event: 'cooldown', after_ms: COOLDOWN_MS });
      setTimeout(spawnChild, COOLDOWN_MS);
      return;
    }

    log({ event: 'restarting', after_ms: BACKOFF_MS });
    setTimeout(spawnChild, BACKOFF_MS);
  });
}

function heartbeatAgeMs(file, now = Date.now()) {
  try { return now - fs.statSync(file).mtimeMs; } catch { return 0; } // a missing file is not proof of a hang
}

function startHangWatchdog() {
  if (!HEARTBEAT_FILE) return null;
  const t = setInterval(() => {
    if (stopping || !child || child.killed) return;
    const age = heartbeatAgeMs(HEARTBEAT_FILE);
    if (age > STALE_MS) {
      log({ event: 'hung_child_killed', heartbeat: path.basename(HEARTBEAT_FILE), age_ms: Math.round(age) });
      try { child.kill('SIGKILL'); } catch { /* the exit handler restarts it */ }
      try { fs.utimesSync(HEARTBEAT_FILE, new Date(), new Date()); } catch { /* best effort: avoids an immediate re-kill of the new child */ }
    }
  }, Math.min(60 * 1000, Math.max(1000, Math.floor(STALE_MS / 4))));
  t.unref();
  return t;
}

function stopFilePresent(file = STOP_FILE) {
  try { return fs.existsSync(file); } catch { return false; }
}

function startStopWatch() {
  const t = setInterval(() => {
    if (stopping) return;
    if (stopFilePresent()) {
      log({ event: 'stop_file_detected', file: STOP_FILE });
      forwardSignal('SIGTERM');
    }
  }, 5000);
  t.unref();
  return t;
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

if (require.main === module) {
  // Signal handlers only attach in the supervisor's own process — never as a
  // side effect of another module requiring this file (same real bug fixed in
  // factory_loop.js on 2026-07-23).
  process.on('SIGINT', () => forwardSignal('SIGINT'));
  process.on('SIGTERM', () => forwardSignal('SIGTERM'));
  spawnChild();
  startHangWatchdog();
  startStopWatch();
}

module.exports = { heartbeatAgeMs, startHangWatchdog, startStopWatch, stopFilePresent, rotateLog, spawnChild, withinCrashLoopLimit, restartTimestamps, MAX_RESTARTS, WINDOW_MS, alertCrashRestart, alertGivingUp };

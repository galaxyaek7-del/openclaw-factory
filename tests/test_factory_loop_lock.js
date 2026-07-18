// Regression test for the Phase 10 red-team audit's MEDIUM finding:
// factory_loop.js's acquireLock() used to do existsSync -> read ->
// isPidAlive -> writeFileSync as four separate calls, not one atomic
// operation, so two instances starting in the same narrow window could
// both see "no live lock" and both write. Fixed with an atomic
// exclusive-create ({ flag: 'wx' }).
//
// Uses an isolated temp lock file (never the real .factory_loop.lock a
// real, currently-running factory_loop.js instance owns) and an injected
// exit function (never the real process.exit) so this test cannot
// disturb the real factory or kill the test runner.
//
//   node --test tests/test_factory_loop_lock.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawn } = require('child_process');
const { acquireLock, releaseLock } = require('../factory_loop.js');

function tempLockPath() {
  return path.join(os.tmpdir(), `test_factory_loop_lock_${process.pid}_${Date.now()}_${Math.random().toString(36).slice(2)}.lock`);
}

test('acquireLock: creates the lock file atomically when none exists', () => {
  const lockFile = tempLockPath();
  try {
    let exited = false;
    const wasStaleLockReclaimed = acquireLock(lockFile, () => { exited = true; });
    assert.equal(exited, false);
    assert.ok(fs.existsSync(lockFile));
    assert.equal(fs.readFileSync(lockFile, 'utf8'), String(process.pid));
    // Unified Recovery System §2 (2026-07-18): a clean create is not a
    // stale-lock reclaim -- the startup safety check must see false here.
    assert.equal(wasStaleLockReclaimed, false);
  } finally {
    releaseLock(lockFile);
  }
});

test('acquireLock: a second call while the same (alive) pid holds it triggers the "another instance" exit path, without overwriting the lock', () => {
  const lockFile = tempLockPath();
  try {
    let exitedFirst = false;
    acquireLock(lockFile, () => { exitedFirst = true; });
    assert.equal(exitedFirst, false);

    let exitedSecond = false;
    let exitCode = null;
    acquireLock(lockFile, (code) => { exitedSecond = true; exitCode = code; });
    assert.equal(exitedSecond, true, 'second call must take the "another live instance" exit path');
    assert.equal(exitCode, 0);
    // The lock file must still contain the original holder's pid — a
    // blocked second caller must never clobber it.
    assert.equal(fs.readFileSync(lockFile, 'utf8'), String(process.pid));
  } finally {
    releaseLock(lockFile);
  }
});

test('acquireLock: reclaims a stale lock left by a pid that is no longer alive', () => {
  const lockFile = tempLockPath();
  try {
    // A pid essentially guaranteed not to be a real running process.
    fs.writeFileSync(lockFile, '999999999');
    let exited = false;
    const wasStaleLockReclaimed = acquireLock(lockFile, () => { exited = true; });
    assert.equal(exited, false, 'a stale lock must be reclaimed, not treated as live');
    assert.equal(fs.readFileSync(lockFile, 'utf8'), String(process.pid));
    // Unified Recovery System §2: this IS the real "previous instance
    // died uncleanly" signal the startup safety check acts on.
    assert.equal(wasStaleLockReclaimed, true);
  } finally {
    releaseLock(lockFile);
  }
});

test('acquireLock: the underlying fs.writeFileSync(..., {flag:"wx"}) primitive this fix relies on really is exclusive', () => {
  const lockFile = tempLockPath();
  try {
    fs.writeFileSync(lockFile, 'a', { flag: 'wx' });
    assert.throws(() => fs.writeFileSync(lockFile, 'b', { flag: 'wx' }), /EEXIST/);
  } finally {
    fs.unlinkSync(lockFile);
  }
});

function runHelper(lockFile, holdMs) {
  return new Promise((resolve, reject) => {
    const helperScript = path.join(__dirname, 'helpers', 'acquire_lock_once.js');
    const child = spawn(process.execPath, [helperScript, lockFile, String(holdMs)]);
    let stdout = '';
    child.stdout.on('data', d => { stdout += d; });
    child.on('error', reject);
    child.on('close', () => {
      // acquireLock() itself may console.log a diagnostic line (e.g. "another
      // factory_loop running...") before the helper's own JSON result line —
      // that diagnostic is expected, real output, not a bug; take the last
      // non-empty line, which is always the helper's own JSON.
      const lines = stdout.trim().split('\n').filter(Boolean);
      try {
        resolve(JSON.parse(lines[lines.length - 1]));
      } catch (err) {
        reject(new Error(`helper produced non-JSON output: ${stdout}`));
      }
    });
  });
}

test('two real, concurrently-running processes racing to reclaim the SAME stale lock: exactly one wins', async () => {
  // Zero-assumption audit follow-up — Medium finding: only the common
  // "no lock file yet" path was atomic before; the stale-lock-reclaim path
  // (both processes see a dead pid and would both plainly overwrite) was
  // still racy. Pre-seed a stale lock (a pid essentially guaranteed not to
  // be a real running process), then race two real processes against it.
  const lockFile = tempLockPath();
  fs.writeFileSync(lockFile, '999999999');
  try {
    const [a, b] = await Promise.all([
      runHelper(lockFile, 800),
      runHelper(lockFile, 800),
    ]);
    const results = [a, b];
    const winners = results.filter(r => r.acquired);
    const losers = results.filter(r => !r.acquired);
    assert.equal(winners.length, 1, `exactly one real process must win the stale-lock reclaim, got: ${JSON.stringify(results)}`);
    assert.equal(losers.length, 1, 'exactly one real process must be blocked');
    assert.equal(losers[0].exitedViaGuard, true);

    const finalHolder = fs.readFileSync(lockFile, 'utf8').trim();
    assert.equal(finalHolder, String(winners[0].pid), "the reclaimed lock file must hold the real winner's own pid, never a stale or corrupted value");
  } finally {
    fs.rmSync(lockFile, { force: true });
  }
});

test('two real, concurrently-running processes: exactly one wins the lock, the other exits 0 without corrupting it', async () => {
  const lockFile = tempLockPath();
  try {
    // Launch both nearly simultaneously (not sequential spawnSync, which
    // would let the first process fully exit before the second even
    // starts — defeating the point of a concurrency test). The winner
    // holds the lock for 800ms so the loser reliably sees a live pid.
    const [a, b] = await Promise.all([
      runHelper(lockFile, 800),
      runHelper(lockFile, 800),
    ]);

    const results = [a, b];
    const winners = results.filter(r => r.acquired);
    const losers = results.filter(r => !r.acquired);
    assert.equal(winners.length, 1, `exactly one real process must win the lock, got: ${JSON.stringify(results)}`);
    assert.equal(losers.length, 1, 'exactly one real process must be blocked');
    assert.equal(losers[0].exitedViaGuard, true);

    const finalHolder = fs.readFileSync(lockFile, 'utf8').trim();
    assert.equal(finalHolder, String(winners[0].pid), "the lock file must hold the real winner's own pid");
  } finally {
    fs.rmSync(lockFile, { force: true });
  }
});

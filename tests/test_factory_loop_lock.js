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

/**
 * Spawn a helper and resolve as soon as it REPORTS, not when it exits.
 *
 * Real fix (2026-10-05): the previous version resolved on 'close', which meant
 * the parent could not learn who had won until every process had exited. That
 * forced the tests to express "keep the winner alive" as a fixed holdMs, and a
 * fixed hold is a scheduling assumption, not a correctness property -- when the
 * loser was scheduled after the hold expired, the winner's pid was genuinely
 * dead, the loser legitimately reclaimed the lock, and both reported acquired.
 *
 * A helper now reports its outcome immediately and, if it won, stays alive
 * until a release file appears. Reading the report as it arrives lets the
 * parent hold the winner for exactly as long as the assertions need.
 */
function spawnHelper(lockFile, holdMs, goFile, releaseFile) {
  const helperScript = path.join(__dirname, 'helpers', 'acquire_lock_once.js');
  const args = [helperScript, lockFile, String(holdMs)];
  if (goFile) args.push(goFile);
  if (releaseFile) args.push(releaseFile);

  const child = spawn(process.execPath, args);
  let stdout = '';
  let settled = false;

  const result = new Promise((resolve, reject) => {
    // Attach the helper's FULL stdout to every report. acquireLock() logs real
    // decision-path diagnostics ("another factory_loop running (PID N)") and a
    // concurrency assertion that fails without them tells us nothing about WHY
    // it failed -- which is exactly how this bug stayed misdiagnosed.
    const settle = (parsed) => {
      if (settled) return;
      settled = true;
      parsed.raw = stdout;
      resolve(parsed);
    };
    const tryParse = () => {
      if (settled) return;
      const lines = stdout.trim().split('\n').filter(Boolean);
      if (!lines.length) return;
      try {
        settle(JSON.parse(lines[lines.length - 1]));
      } catch (err) {
        // Not the helper's JSON line yet; keep buffering.
      }
    };

    child.stdout.on('data', (d) => { stdout += d; tryParse(); });
    child.on('error', reject);
    child.on('close', () => {
      if (settled) return;
      // acquireLock() itself may console.log a diagnostic line (e.g. "another
      // factory_loop running...") before the helper's own JSON result line -
      // that diagnostic is expected, real output, not a bug; take the last
      // non-empty line, which is always the helper's own JSON.
      const lines = stdout.trim().split('\n').filter(Boolean);
      try {
        settle(JSON.parse(lines[lines.length - 1]));
      } catch (err) {
        reject(new Error('helper produced non-JSON output: ' + stdout));
      }
    });
  });

  return { child, result };
}

function waitForExit(child) {
  return new Promise((resolve) => {
    if (child.exitCode !== null) return resolve();
    child.on('close', () => resolve());
  });
}

/**
 * Start two real helper processes behind a shared start barrier, collect both
 * reports, then release the winner and reap both.
 *
 * The winner is provably alive and holding for the whole time the caller
 * inspects the results, so "exactly one wins" is a property of the lock code
 * rather than of how fast the scheduler ran the losers.
 */
async function raceTwo(lockFile, holdMs) {
  const goFile = lockFile + '.go';
  const releaseFile = lockFile + '.release';
  fs.rmSync(goFile, { force: true });
  fs.rmSync(releaseFile, { force: true });

  const a = spawnHelper(lockFile, holdMs, goFile, releaseFile);
  const b = spawnHelper(lockFile, holdMs, goFile, releaseFile);
  fs.writeFileSync(goFile, 'go');            // release the barrier
  const reports = await Promise.all([a.result, b.result]);

  fs.writeFileSync(releaseFile, 'release');  // let the winner exit
  await Promise.all([waitForExit(a.child), waitForExit(b.child)]);

  fs.rmSync(goFile, { force: true });
  fs.rmSync(releaseFile, { force: true });
  return reports;
}

test('a lock file with NO readable pid is never stolen -- unreadable is not dead', () => {
  // THE DETERMINISTIC TEST FOR THIS FIX. Rewritten 2026-10-05.
  //
  // This started as a test of the reclaim's content-verification, which was the
  // previous fix. It then became VACUOUS once the empty-lock guard below was
  // added in front of the reclaim, because a non-numeric pid is now rejected
  // before the reclaim is ever reached -- so it passed just as well against the
  // old broken code. Caught by re-running scripts/mutation_check.py rather than
  // by inspection, which is the only reason it was noticed.
  //
  // The property being pinned is the one the Linux CI actually failed on:
  //
  //   the lock file must hold the real winner's own pid   ->   '' !== '3890'
  //
  // The lock is created by an exclusive create that writes the pid afterwards,
  // so between creation and write the file EXISTS but is EMPTY. A racing
  // reader did parseInt('') -> NaN, and `Number.isFinite(NaN) && ...` evaluated
  // false, which the old code read as "no live owner" -- i.e. dead. It renamed
  // the brand-new lock aside and restored it EMPTY, overwriting the real
  // winner's pid while the winner still believed it held the lock.
  //
  // "I could not read a pid" is not the claim "the owner is dead". Only the
  // second justifies stealing.
  const lockFile = tempLockPath();
  fs.writeFileSync(lockFile, '');

  let exitCode = null;
  try {
    const reclaimed = acquireLock(lockFile, (code) => { exitCode = code; });

    assert.equal(reclaimed, false,
      'a lock with no readable pid must never be treated as abandoned and claimed');
    assert.equal(exitCode, 0,
      "main() ignores acquireLock's return value, so standing down requires exitFn");

    assert.equal(fs.readFileSync(lockFile, 'utf8'), '',
      "an unreadable lock must be left exactly as found, not renamed away or rewritten");
  } finally {
    fs.rmSync(lockFile, { force: true });
  }
});

test('two real, concurrently-running processes racing to reclaim the SAME stale lock: exactly one wins', async () => {
  // Zero-assumption audit follow-up — Medium finding: only the common
  // "no lock file yet" path was atomic before; the stale-lock-reclaim path
  // (both processes see a dead pid and would both plainly overwrite) was
  // still racy. Pre-seed a stale lock (a pid essentially guaranteed not to
  // be a real running process), then race two real processes against it.
  const lockFile = tempLockPath();
  fs.writeFileSync(lockFile, '999999999');
  // Start barrier (2026-10-05): both helpers wait for this file before
  // attempting, so neither can begin before the other exists. Previously the
  // "race" relied on both spawns landing inside a 800ms window; on a loaded CI
  // runner the second spawn can land later than that, the first has already
  // released, and BOTH legitimately acquire -- failing a test that then proved
  // nothing about the lock at all. This was the cause of the only JS failure
  // on CI, which passed locally every time.
  try {
    const results = await raceTwo(lockFile, 800);
    const winners = results.filter(r => r.acquired);
    const losers = results.filter(r => !r.acquired);
    assert.equal(winners.length, 1, `exactly one real process must win the stale-lock reclaim, got: ${JSON.stringify(results)}\n${results.map(r => r.raw).join('\n----\n')}`);
    assert.equal(losers.length, 1, 'exactly one real process must be blocked');
    assert.equal(losers[0].exitedViaGuard, true);

    const finalHolder = fs.readFileSync(lockFile, 'utf8').trim();
    assert.equal(finalHolder, String(winners[0].pid), "the reclaimed lock file must hold the real winner's own pid, never a stale or corrupted value");
  } finally {
    fs.rmSync(lockFile, { force: true });
  }
});

test('EIGHT real processes reclaiming the SAME stale lock: still exactly one wins', async () => {
  // Added 2026-10-05, and this is the test that actually pins the reclaim race.
  //
  // The two-process tests above cannot detect the bug on their own, and that
  // was proven rather than assumed: reverting factory_loop.js to the old
  // unlink-then-exclusive-create reclaim left all of them passing (12/12),
  // because the winner is held alive and the loser simply reads a LIVE pid and
  // stands down. Honest coverage would have quietly been reduced.
  //
  // The old bug needs the loser's steal to land on a lock that has ALREADY
  // changed hands. With two processes that interleaving is a narrow window and
  // rarely occurs; with eight processes all released from one barrier onto the
  // same dead-pid lock, several read the stale pid before anyone re-creates,
  // and one of them necessarily tries to unlink a freshly written lock. Under
  // the old code two or more then acquire; under the fixed code the steal is
  // verified against the stale pid it expected, so exactly one wins.
  //
  // Nothing is disabled or relaxed here -- the invariant asserted is strictly
  // the same one, over more real processes.
  const lockFile = tempLockPath();
  const PARTICIPANTS = 8;
  fs.writeFileSync(lockFile, '999999999');   // a genuinely dead pid
  const goFile = `${lockFile}.go`;
  const releaseFile = `${lockFile}.release`;
  fs.rmSync(goFile, { force: true });
  fs.rmSync(releaseFile, { force: true });

  const helpers = [];
  for (let i = 0; i < PARTICIPANTS; i += 1) {
    helpers.push(spawnHelper(lockFile, 5000, goFile, releaseFile));
  }
  fs.writeFileSync(goFile, 'go');
  const results = await Promise.all(helpers.map(h => h.result));

  fs.writeFileSync(releaseFile, 'release');
  await Promise.all(helpers.map(h => waitForExit(h.child)));
  fs.rmSync(goFile, { force: true });
  fs.rmSync(releaseFile, { force: true });

  const winners = results.filter(r => r.acquired);
  assert.equal(winners.length, 1,
    `exactly one of ${PARTICIPANTS} real processes must win the stale-lock reclaim, got: ${JSON.stringify(results)}\n${results.map(r => r.raw).join('\n----\n')}`);
  for (const loser of results.filter(r => !r.acquired)) {
    assert.equal(loser.exitedViaGuard, true, 'every blocked process must have exited via the guard');
  }

  try {
    const finalHolder = fs.readFileSync(lockFile, 'utf8').trim();
    assert.equal(finalHolder, String(winners[0].pid),
      'the lock must hold the single real winner\'s own pid');
  } finally {
    fs.rmSync(lockFile, { force: true });
  }
});

test('two real, concurrently-running processes: exactly one wins the lock, the other exits 0 without corrupting it', async () => {
  const lockFile = tempLockPath();
  try {
    // Two real processes, started behind a shared barrier, with the winner held
    // alive until both reports are in. This is what makes "exactly one wins" a
    // property of acquireLock rather than of scheduler timing -- see raceTwo().
    const results = await raceTwo(lockFile, 800);
    const winners = results.filter(r => r.acquired);
    const losers = results.filter(r => !r.acquired);
    assert.equal(winners.length, 1, `exactly one real process must win the lock, got: ${JSON.stringify(results)}\n${results.map(r => r.raw).join('\n----\n')}`);
    assert.equal(losers.length, 1, 'exactly one real process must be blocked');
    assert.equal(losers[0].exitedViaGuard, true);

    const finalHolder = fs.readFileSync(lockFile, 'utf8').trim();
    assert.equal(finalHolder, String(winners[0].pid), "the lock file must hold the real winner's own pid");
  } finally {
    fs.rmSync(lockFile, { force: true });
  }
});

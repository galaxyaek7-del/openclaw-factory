// Helper process for tests/test_factory_loop_lock.js's real two-process
// tests. Not a test itself — invoked as:
//   node tests/helpers/acquire_lock_once.js <lockFile> <holdMs> [goFile] [releaseFile]
//
// Prints one JSON line describing what happened the moment the outcome is
// known, and — if it won the lock — then stays alive until <releaseFile>
// appears (or <holdMs> elapses as a backstop).
//
// Why releaseFile (2026-10-05): both real-process tests previously relied on a
// fixed holdMs to keep the winner alive "long enough" for the loser to attempt.
// That is a scheduling assumption, not a correctness property. When the loser
// was scheduled after the winner's hold expired, the winner had already
// exited, so `isPidAliveWithIdentity` correctly reported a DEAD pid and the
// loser legitimately reclaimed the lock — both reported acquired, and the test
// failed having proved nothing. Reproduced locally ~1 run in 12.
//
// With a release file the winner provably stays alive for the whole test, so
// the loser's attempt ALWAYS lands on a live owner. The invariant under test —
// while a live process holds the lock, no second process can acquire it —
// becomes deterministic instead of a race against the scheduler.

const fs = require('fs');

const { acquireLock } = require('../../factory_loop.js');

const lockFile = process.argv[2];
const holdMs = parseInt(process.argv[3], 10) || 0;
const goFile = process.argv[4] || null;
const releaseFile = process.argv[5] || null;

let exitedViaGuard = false;

function spin(ms) {
  const end = Date.now() + ms;
  while (Date.now() < end) { /* bounded wait */ }
}

function waitFor(what, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (!fs.existsSync(what)) {
    if (Date.now() > deadline) return false;
    spin(5);
  }
  return true;
}

// Start barrier: neither process may begin before the other is ready.
if (goFile) {
  if (!waitFor(goFile, 10000)) {
    console.error('helper: timed out waiting for the start barrier ' + goFile);
    process.exit(3);
  }
}

acquireLock(lockFile, () => {
  exitedViaGuard = true;
});

// Report the outcome immediately: the parent must not have to wait for exit to
// learn who won, because the winner deliberately stays alive.
console.log(JSON.stringify({
  pid: process.pid,
  acquired: !exitedViaGuard,
  exitedViaGuard,
}));

if (exitedViaGuard) {
  process.exit(0);
}

if (releaseFile) {
  waitFor(releaseFile, Math.max(holdMs, 30000));
} else if (holdMs > 0) {
  spin(holdMs);
}
process.exit(0);
// Helper process for tests/test_factory_loop_lock.js's real two-process
// race test. Not a test itself — invoked as:
//   node tests/helpers/acquire_lock_once.js <lockFilePath> <holdMs> [goFilePath]
//
// Prints one JSON line describing what happened, then (if it won the
// lock) stays alive for <holdMs> ms so a concurrently-spawned second
// process sees a genuinely live pid, not an already-exited one.
//
// goFilePath (optional, added 2026-10-05): a start barrier. The helper waits
// for this file to appear before attempting the lock. Without it the "race"
// was not guaranteed to be one -- if the runner was slow enough that process
// B spawned only after process A had finished its hold and released the lock,
// B legitimately acquired it too and the test failed having proved nothing.
// Both helpers now wait for the same go file, so neither can start before the
// other is ready.

const fs = require('fs');

const { acquireLock } = require('../../factory_loop.js');

const lockFile = process.argv[2];
const holdMs = parseInt(process.argv[3], 10) || 0;
const goFile = process.argv[4] || null;
let exitedViaGuard = false;

function waitForGo() {
  if (!goFile) return;
  const deadline = Date.now() + 10000;
  while (!fs.existsSync(goFile)) {
    if (Date.now() > deadline) {
      console.error('helper: timed out waiting for the start barrier ' + goFile);
      process.exit(3);
    }
    // Atomics.wait is not available on the main thread, so this is a short
    // sleep loop. It is bounded and only ever runs before the real work.
    const end = Date.now() + 5;
    while (Date.now() < end) { /* spin briefly */ }
  }
}

waitForGo();

acquireLock(lockFile, () => {
  exitedViaGuard = true;
});

console.log(JSON.stringify({
  pid: process.pid,
  acquired: !exitedViaGuard,
  exitedViaGuard,
}));

if (!exitedViaGuard && holdMs > 0) {
  setTimeout(() => process.exit(0), holdMs);
} else {
  process.exit(0);
}

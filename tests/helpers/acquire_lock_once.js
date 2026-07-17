// Helper process for tests/test_factory_loop_lock.js's real two-process
// race test. Not a test itself — invoked as:
//   node tests/helpers/acquire_lock_once.js <lockFilePath> <holdMs>
// Prints one JSON line describing what happened, then (if it won the
// lock) stays alive for <holdMs> ms so a concurrently-spawned second
// process sees a genuinely live pid, not an already-exited one.

const { acquireLock } = require('../../factory_loop.js');

const lockFile = process.argv[2];
const holdMs = parseInt(process.argv[3], 10) || 0;
let exitedViaGuard = false;

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

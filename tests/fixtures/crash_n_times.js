// Test fixture for tests/test_supervisor.js — crashes for the first
// CRASH_N invocations (tracked via a real counter file, since each
// restart is a fresh process with no shared memory), then exits 0.
const fs = require('fs');

const counterFile = process.env.CRASH_COUNTER_FILE;
const crashN = parseInt(process.env.CRASH_N || '0', 10);

let count = 0;
try { count = parseInt(fs.readFileSync(counterFile, 'utf8'), 10) || 0; } catch { /* first run */ }
count += 1;
fs.writeFileSync(counterFile, String(count));

if (count <= crashN) {
  process.exit(1);
}
process.exit(0);

// Regression test for the V5.5 PID-recycling finding (2026-09-29):
// factory_loop.js's startup guard used kill(pid, 0), which only proves a PID
// EXISTS — not that it is still factory_loop.js. After the 2026-09-26
// unclean death the OS recycled the stale lock's PID to a browser process,
// and every restart exited with "another factory_loop running" for 3 days
// while continuous operations were silently down.
//
// isPidAliveWithIdentity() verifies the process image on win32 (tasklist,
// argv array — no shell) and keeps fail-closed behavior on any check error.
// acquireLock() accepts an injectable execFn (same convention as its
// lockFile/exitFn params) so every path below is proven without touching
// real processes — except the live two, which are clearly marked.
//
//   node --test tests/test_factory_loop_lock_identity.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { acquireLock, isPidAliveWithIdentity } = require('../factory_loop.js');

const DEAD_PID = 2 ** 22; // far beyond any real PID — kill(pid, 0) throws
const LIVE_PID = process.pid; // this test process itself — kill(pid, 0) succeeds

function lockWith(pid) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'floop-lock-'));
  const file = path.join(dir, '.factory_loop.lock');
  fs.writeFileSync(file, String(pid));
  return file;
}

function noExit() {
  throw new Error('exitFn must not fire on the reclaim path');
}

const nodeCsv = (pid) => `"node.exe","${pid}","Console","1","10,000 K"`;
const otherCsv = (pid) => `"msedge.exe","${pid}","Console","1","200,000 K"`;

test('dead PID is reclaimed (unchanged legacy behavior)', () => {
  const file = lockWith(DEAD_PID);
  const reclaimed = acquireLock(file, noExit, () => { throw new Error('checker must not run for a dead PID'); });
  assert.equal(reclaimed, true);
  assert.equal(fs.readFileSync(file, 'utf8').trim(), String(process.pid));
});

test('live PID owned by a NON-node process is reclaimed (the PID-recycling bug)', () => {
  const file = lockWith(LIVE_PID);
  const fakeTasklist = () => otherCsv(LIVE_PID);
  const reclaimed = acquireLock(file, noExit, fakeTasklist);
  assert.equal(reclaimed, true);
  assert.equal(fs.readFileSync(file, 'utf8').trim(), String(process.pid));
});

test('live PID owned by node.exe blocks startup (no double-run)', () => {
  const file = lockWith(LIVE_PID);
  let exited = null;
  const fakeTasklist = () => nodeCsv(LIVE_PID);
  const reclaimed = acquireLock(file, (code) => { exited = code; }, fakeTasklist);
  assert.equal(reclaimed, false);
  assert.equal(exited, 0);
  assert.equal(fs.readFileSync(file, 'utf8').trim(), String(LIVE_PID)); // lock untouched
});

test('checker failure fails closed (blocks startup, never double-runs)', () => {
  const file = lockWith(LIVE_PID);
  let exited = null;
  const brokenTasklist = () => { throw new Error('tasklist unavailable'); };
  const reclaimed = acquireLock(file, (code) => { exited = code; }, brokenTasklist);
  assert.equal(reclaimed, false);
  assert.equal(exited, 0);
});

test('checker reporting "no tasks match" reclaims (PID died in the race window)', () => {
  // Real tasklist prints exactly this when no process matches the PID
  // filter — combined with the kill(pid, 0) success a moment earlier, the
  // owner died between the two checks. Reclaiming is correct here.
  const file = lockWith(LIVE_PID);
  const reclaimed = acquireLock(file, noExit, () => 'INFO: No tasks are running matching the specified criteria.');
  assert.equal(reclaimed, true);
  assert.equal(fs.readFileSync(file, 'utf8').trim(), String(process.pid));
});

test('empty checker output fails closed (blocks startup, never double-runs)', () => {
  const file = lockWith(LIVE_PID);
  let exited = null;
  const reclaimed = acquireLock(file, (code) => { exited = code; }, () => '');
  assert.equal(reclaimed, false);
  assert.equal(exited, 0);
});

test('isPidAliveWithIdentity: live self-PID resolves against the REAL tasklist on win32', { skip: process.platform !== 'win32' }, () => {
  assert.equal(isPidAliveWithIdentity(process.pid), true);
  assert.equal(isPidAliveWithIdentity(DEAD_PID), false);
});

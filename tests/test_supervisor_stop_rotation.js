// scripts/supervisor.js log rotation + kill-switch helpers (TASKS.md items 2, 5,
// 2026-11-18). Real finding: supervisor.log only ever appended, and a STOP file
// stopped the loop but nothing guaranteed the supervisor noticed. Pure helper
// coverage here; the spawn/restart integration stays in test_supervisor.js.
//
//   node --test tests/test_supervisor_stop_rotation.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const sup = require('../scripts/supervisor.js');

function tmp(name) {
  return path.join(os.tmpdir(), `test_sup_${name}_${process.pid}_${Date.now()}_${Math.random().toString(36).slice(2)}`);
}

function cleanup(base, keep) {
  for (let i = 0; i <= keep + 1; i += 1) {
    try { fs.unlinkSync(i === 0 ? base : `${base}.${i}`); } catch { /* absent is fine */ }
  }
}

test('stopFilePresent reflects a real STOP file', () => {
  const stop = tmp('stop');
  try {
    assert.equal(sup.stopFilePresent(stop), false);
    fs.writeFileSync(stop, '');
    assert.equal(sup.stopFilePresent(stop), true);
  } finally {
    cleanup(stop, 0);
  }
});

test('below the cap: no rotation', () => {
  const log = tmp('small');
  try {
    fs.writeFileSync(log, 'a\nb\n');
    assert.equal(sup.rotateLog(log, { maxBytes: 100, keep: 2 }), false);
    assert.equal(fs.readFileSync(log, 'utf8'), 'a\nb\n');
    assert.equal(fs.existsSync(`${log}.1`), false);
  } finally { cleanup(log, 2); }
});

test('at/over the cap: current becomes .1 and generations shift', () => {
  const log = tmp('rotate');
  try {
    fs.writeFileSync(`${log}.1`, 'older\n');
    fs.writeFileSync(log, 'x'.repeat(50));
    assert.equal(sup.rotateLog(log, { maxBytes: 10, keep: 3 }), true);
    assert.equal(fs.existsSync(log), false);
    assert.equal(fs.readFileSync(`${log}.1`, 'utf8'), 'x'.repeat(50));
    assert.equal(fs.readFileSync(`${log}.2`, 'utf8'), 'older\n');
  } finally { cleanup(log, 3); }
});

test('keeping is bounded: the oldest generation is dropped', () => {
  const log = tmp('bound');
  try {
    fs.writeFileSync(`${log}.1`, 'g1\n');
    fs.writeFileSync(`${log}.2`, 'g2\n');
    fs.writeFileSync(log, 'current\n');
    assert.equal(sup.rotateLog(log, { maxBytes: 1, keep: 2 }), true);
    assert.equal(fs.readFileSync(`${log}.1`, 'utf8'), 'current\n');
    assert.equal(fs.readFileSync(`${log}.2`, 'utf8'), 'g1\n');
    assert.equal(fs.existsSync(`${log}.3`), false);
  } finally { cleanup(log, 2); }
});

test('a missing log is not an error', () => {
  const log = tmp('missing');
  try {
    assert.equal(sup.rotateLog(log, { maxBytes: 1, keep: 2 }), false);
  } finally { cleanup(log, 2); }
});

// Tests for lib/health_trend.js (Global Trust & Resilience Layer,
// Round 1, 2026-07-29). Never touches the real data/health_snapshots.jsonl
// — every test passes an explicit temp path.
//
//   node --test tests/test_health_trend.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const {
  recordHealthSnapshot, readHealthSnapshots, detectHealthDegradation,
} = require('../lib/health_trend.js');

function tempPath() {
  return path.join(os.tmpdir(), `health_snapshots_${process.pid}_${Date.now()}_${Math.random().toString(36).slice(2)}.jsonl`);
}

test('recordHealthSnapshot rejects an unrecognized status, never writes garbage', () => {
  const p = tempPath();
  const result = recordHealthSnapshot('not_a_real_status', p);
  assert.equal(result.recorded, false);
  assert.equal(fs.existsSync(p), false);
});

test('recordHealthSnapshot appends a real, timestamped entry', () => {
  const p = tempPath();
  try {
    const result = recordHealthSnapshot('healthy', p, new Date('2026-07-29T00:00:00Z'));
    assert.equal(result.recorded, true);
    const entries = readHealthSnapshots(p);
    assert.equal(entries.length, 1);
    assert.equal(entries[0].status, 'healthy');
  } finally {
    if (fs.existsSync(p)) fs.unlinkSync(p);
  }
});

test('readHealthSnapshots on a missing file is honestly empty, never throws', () => {
  const entries = readHealthSnapshots(tempPath());
  assert.deepEqual(entries, []);
});

test('readHealthSnapshots skips a corrupt line rather than throwing', () => {
  const p = tempPath();
  try {
    fs.writeFileSync(p, '{"at":"x","status":"healthy"}\nnot valid json\n{"at":"y","status":"degraded"}\n');
    const entries = readHealthSnapshots(p);
    assert.equal(entries.length, 2);
  } finally {
    if (fs.existsSync(p)) fs.unlinkSync(p);
  }
});

test('detectHealthDegradation with fewer than windowSize readings is honestly not degrading', () => {
  const p = tempPath();
  try {
    recordHealthSnapshot('critical', p);
    const result = detectHealthDegradation(p, 3);
    assert.equal(result.degrading, false);
    assert.match(result.reason, /أقل من/);
  } finally {
    if (fs.existsSync(p)) fs.unlinkSync(p);
  }
});

test('detectHealthDegradation flags a real strictly-worsening trend', () => {
  const p = tempPath();
  try {
    recordHealthSnapshot('healthy', p);
    recordHealthSnapshot('degraded', p);
    recordHealthSnapshot('critical', p);
    const result = detectHealthDegradation(p, 3);
    assert.equal(result.degrading, true);
    assert.match(result.reason, /تزداد سوءاً/);
  } finally {
    if (fs.existsSync(p)) fs.unlinkSync(p);
  }
});

test('detectHealthDegradation flags a real sustained-unhealthy trend even without worsening', () => {
  const p = tempPath();
  try {
    recordHealthSnapshot('degraded', p);
    recordHealthSnapshot('critical', p);
    recordHealthSnapshot('degraded', p);
    const result = detectHealthDegradation(p, 3);
    assert.equal(result.degrading, true);
    assert.match(result.reason, /غير سليمة/);
  } finally {
    if (fs.existsSync(p)) fs.unlinkSync(p);
  }
});

test('detectHealthDegradation is honestly not degrading for a healthy, stable history', () => {
  const p = tempPath();
  try {
    recordHealthSnapshot('healthy', p);
    recordHealthSnapshot('healthy', p);
    recordHealthSnapshot('healthy', p);
    const result = detectHealthDegradation(p, 3);
    assert.equal(result.degrading, false);
  } finally {
    if (fs.existsSync(p)) fs.unlinkSync(p);
  }
});

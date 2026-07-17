// Regression test for the standing-charter continuous-improvement
// follow-up: scripts/ops_maintenance.js used to rotate only
// logs/service_layer.log. factory_loop.log and inspections.log are real,
// unbounded, growing root-level logs it never covered (zero-assumption
// audit, Section C). Generalized rotateLogIfNeeded() into a single
// parameterized function every log shares, called for all three via
// rotateAllKnownLogs(). Uses temp files, never the real logs.
//
//   node --test tests/test_ops_maintenance.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { rotateLogIfNeeded } = require('../scripts/ops_maintenance.js');

function tempLogPath() {
  return path.join(os.tmpdir(), `test_ops_maintenance_${process.pid}_${Date.now()}_${Math.random().toString(36).slice(2)}.log`);
}

test('rotateLogIfNeeded: missing file -> no-op, never throws', () => {
  const p = tempLogPath();
  const result = rotateLogIfNeeded(p, 'test', 1024, false);
  assert.equal(result.rotated, false);
  assert.equal(result.reason, 'missing');
});

test('rotateLogIfNeeded: below threshold -> no-op, dry run never touches the file', () => {
  const p = tempLogPath();
  fs.writeFileSync(p, 'small content');
  try {
    const result = rotateLogIfNeeded(p, 'test', 1024 * 1024, false);
    assert.equal(result.rotated, false);
    assert.equal(result.reason, 'below_threshold');
    assert.ok(fs.existsSync(p), 'file must be untouched below threshold');
  } finally {
    fs.rmSync(p, { force: true });
  }
});

test('rotateLogIfNeeded: over threshold, dry run -> reports but does not actually rotate', () => {
  const p = tempLogPath();
  fs.writeFileSync(p, 'x'.repeat(2000));
  try {
    const result = rotateLogIfNeeded(p, 'test', 1000, false); // apply=false (default)
    assert.equal(result.rotated, false, 'dry run must never actually rotate');
    assert.equal(result.reason, 'over_threshold');
    assert.ok(fs.existsSync(p), 'dry run must leave the original file exactly as it was');
    assert.equal(fs.statSync(p).size, 2000);
  } finally {
    fs.rmSync(p, { force: true });
  }
});

test('rotateLogIfNeeded: over threshold, --apply -> real rotation, original file truncated', () => {
  const p = tempLogPath();
  fs.writeFileSync(p, 'x'.repeat(2000));
  let archivePath;
  try {
    const result = rotateLogIfNeeded(p, 'test-rotate', 1000, true);
    assert.equal(result.rotated, true);
    archivePath = result.archivePath;
    assert.ok(fs.existsSync(archivePath), 'a real archive file must be created');
    assert.equal(fs.statSync(archivePath).size, 2000, 'the archive must contain the real, full original content');
    assert.ok(fs.existsSync(p), 'the original log path must still exist, now empty');
    assert.equal(fs.statSync(p).size, 0, 'the original log must be truncated to empty after rotation, not deleted');
  } finally {
    fs.rmSync(p, { force: true });
    if (archivePath) fs.rmSync(archivePath, { force: true });
  }
});

// Tests for lib/recovery_log.js (Phase 10D — Disaster Recovery &
// Business Continuity). Same convention as tests/test_metrics.js.
//
//   node --test tests/test_recovery_log.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const { recordRecoveryAction, readRecoveryActions } = require('../lib/recovery_log.js');

function tmpLogPath() {
  return path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'recovery-log-test-')), 'recovery_actions.jsonl');
}

// Isolates department_events writes from the real data/department_events.jsonl
function tmpDeptEventsPath() {
  return path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'recovery-log-test-dep-')), 'department_events.jsonl');
}

test('recordRecoveryAction: writes a real record with all 5 required fields', () => {
  const logPath = tmpLogPath();
  const record = recordRecoveryAction({
    operator: 'test-operator',
    reason: 'simulated crash recovery test',
    affectedSystems: ['server.js', 'mission_control'],
    result: 'success',
    logPath,
    departmentEventsPath: tmpDeptEventsPath(),
  });
  assert.ok(record.timestamp);
  assert.equal(record.operator, 'test-operator');
  assert.equal(record.reason, 'simulated crash recovery test');
  assert.deepEqual(record.affected_systems, ['server.js', 'mission_control']);
  assert.equal(record.result, 'success');

  const written = readRecoveryActions(logPath);
  assert.equal(written.length, 1);
  assert.deepEqual(written[0], record);
});

test('recordRecoveryAction: appends, never overwrites prior entries', () => {
  const logPath = tmpLogPath();
  const departmentEventsPath = tmpDeptEventsPath();
  recordRecoveryAction({ operator: 'a', reason: 'r1', affectedSystems: ['x'], result: 'ok', logPath, departmentEventsPath });
  recordRecoveryAction({ operator: 'b', reason: 'r2', affectedSystems: ['y'], result: 'ok', logPath, departmentEventsPath });
  const all = readRecoveryActions(logPath);
  assert.equal(all.length, 2);
  assert.equal(all[0].reason, 'r1');
  assert.equal(all[1].reason, 'r2');
});

test('recordRecoveryAction: requires every field, never silently logs an incomplete record', () => {
  const logPath = tmpLogPath();
  assert.throws(() => recordRecoveryAction({ reason: 'r', affectedSystems: ['x'], result: 'ok', logPath }), /operator/);
  assert.throws(() => recordRecoveryAction({ operator: 'a', affectedSystems: ['x'], result: 'ok', logPath }), /reason/);
  assert.throws(() => recordRecoveryAction({ operator: 'a', reason: 'r', result: 'ok', logPath }), /affectedSystems/);
  assert.throws(() => recordRecoveryAction({ operator: 'a', reason: 'r', affectedSystems: ['x'], logPath }), /result/);
  assert.throws(() => recordRecoveryAction({ operator: 'a', reason: 'r', affectedSystems: [], result: 'ok', logPath }), /affectedSystems/);
});

test('recordRecoveryAction: department_events write is isolated to the given departmentEventsPath, never the real default log', () => {
  const logPath = tmpLogPath();
  const departmentEventsPath = tmpDeptEventsPath();
  const { readEvents, DEFAULT_LOG_PATH } = require('../lib/department_events.js');
  const before = fs.existsSync(DEFAULT_LOG_PATH) ? fs.readFileSync(DEFAULT_LOG_PATH, 'utf8') : null;
  recordRecoveryAction({ operator: 'iso-test', reason: 'r', affectedSystems: ['x'], result: 'ok', logPath, departmentEventsPath });
  const after = fs.existsSync(DEFAULT_LOG_PATH) ? fs.readFileSync(DEFAULT_LOG_PATH, 'utf8') : null;
  assert.equal(after, before, 'the real department_events.jsonl must be untouched when departmentEventsPath is given');
  const events = readEvents(departmentEventsPath);
  assert.equal(events.length, 1);
  assert.equal(events[0].department, 'recovery');
});

test('readRecoveryActions: missing file -> empty array, never throws', () => {
  const missingPath = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'recovery-log-test-')), 'does-not-exist.jsonl');
  assert.deepEqual(readRecoveryActions(missingPath), []);
});

test('readRecoveryActions: skips a corrupt line rather than throwing', () => {
  const logPath = tmpLogPath();
  fs.writeFileSync(logPath, '{"timestamp":"t","operator":"a","reason":"r","affected_systems":["x"],"result":"ok"}\nnot valid json\n');
  const records = readRecoveryActions(logPath);
  assert.equal(records.length, 1);
  assert.equal(records[0].operator, 'a');
});

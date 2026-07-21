// Tests for lib/department_events.js (EOS Phase 2, Round 2, 2026-07-19):
// the JS-side shared JSONL correlation-index envelope. Same convention
// as tests/test_recovery_log.js/test_n8n_notify.js.
//
//   node --test tests/test_department_events.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const { emit, readEvents, VALID_DEPARTMENTS } = require('../lib/department_events.js');

function tmpLogPath() {
  return path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'dept-events-test-')), 'department_events.jsonl');
}

test('emit: unknown department throws', () => {
  const logPath = tmpLogPath();
  assert.throws(() => emit({ department: 'not_a_real_department', event_type: 'x' }, logPath));
});

test('emit: real department writes a real envelope', () => {
  const logPath = tmpLogPath();
  const record = emit({ department: 'golden_hunter', event_type: 'opportunity.attempted', ref_id: 'niche-x', source_log: 'data/golden_hunter_events.jsonl', summary: 'test' }, logPath);
  assert.equal(record.department, 'golden_hunter');
  assert.ok(record.event_id);
  assert.ok(record.emitted_at);
  const entries = readEvents(logPath);
  assert.equal(entries.length, 1);
  assert.equal(entries[0].ref_id, 'niche-x');
});

test('emit: never duplicates business data, envelope-only', () => {
  const logPath = tmpLogPath();
  const record = emit({ department: 'ai_capability_manager', event_type: 'capability.request_logged', ref_id: 'req-1' }, logPath);
  assert.deepEqual(
    Object.keys(record).sort(),
    ['department', 'emitted_at', 'event_id', 'event_type', 'ref_id', 'source_log', 'summary'].sort(),
  );
});

test('emit: append-only, never overwrites', () => {
  const logPath = tmpLogPath();
  emit({ department: 'recovery', event_type: 'recovery.action_taken' }, logPath);
  emit({ department: 'recovery', event_type: 'recovery.action_taken' }, logPath);
  const entries = readEvents(logPath);
  assert.equal(entries.length, 2);
});

test('VALID_DEPARTMENTS: includes all 12 named departments', () => {
  assert.equal(VALID_DEPARTMENTS.length, 12);
  for (const d of ['researchers', 'customer_intelligence', 'golden_hunter', 'pioneer']) {
    assert.ok(VALID_DEPARTMENTS.includes(d));
  }
});

test('readEvents: missing file reads as empty, never throws', () => {
  const entries = readEvents('/no/such/department_events.jsonl');
  assert.deepEqual(entries, []);
});

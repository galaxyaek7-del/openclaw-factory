// lib/connection_status.js -- Mission Control view of real execution evidence.
//   node --test tests/test_connection_status.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { buildConnectionStatus } = require('../lib/connection_status');

const dir = () => fs.mkdtempSync(path.join(os.tmpdir(), 'gf_cs_'));

test('missing sources are UNKNOWN with a reason, never zero or OK', () => {
  const s = buildConnectionStatus({ dataDir: dir() });
  assert.equal(s.verifier.status, 'UNKNOWN');
  assert.equal(s.agents.status, 'UNKNOWN');
  assert.equal(s.tasks.status, 'UNKNOWN');
  for (const part of [s.verifier, s.agents, s.tasks]) assert.ok(part.reason);
});

test('real records are summarized: per-agent calls and per-task status', () => {
  const d = dir();
  fs.writeFileSync(path.join(d, 'connection_status.json'), JSON.stringify({ checked_at: '2026-10-23T07:00:00Z',
    counts: { VERIFIED: 2, FAILED: 1 }, rows: [{ name: 'a', status: 'VERIFIED' }, { name: 'paddle', status: 'FAILED' },
      { name: 'agent:x', status: 'VERIFIED_EXECUTABLE_NOT_CONNECTED' }] }));
  fs.writeFileSync(path.join(d, 'agent_executions.jsonl'), [
    { agent: 'scout', outcome: 'ok', source: 'probe', started_at: '2026-10-23T07:50:00Z' },
    { agent: 'scout', outcome: 'timeout', source: 'agent_chain', started_at: '2026-10-23T08:00:00Z', error: 'timed out' },
  ].map((x) => JSON.stringify(x)).join('\n') + '\n');
  fs.writeFileSync(path.join(d, 'agent_tasks.jsonl'), [
    { task_id: 'T', step: 'scout_brief', status: 'done', at: '2026-10-23T08:00:00Z' },
    { task_id: 'T', step: 'distribute', status: 'blocked', at: '2026-10-23T08:00:01Z' },
  ].map((x) => JSON.stringify(x)).join('\n') + '\n');
  const s = buildConnectionStatus({ dataDir: d, now: Date.parse('2026-10-23T09:00:00Z') });
  assert.equal(s.verifier.age_hours, 2);
  assert.deepEqual(s.verifier.not_verified.map((r) => r.name), ['paddle']);
  assert.equal(s.agents.scout.calls, 2);
  assert.equal(s.agents.scout.failures, 1);
  assert.equal(s.agents.scout.last.outcome, 'timeout');
  assert.equal(s.tasks.T.status, 'blocked');
});

test('a verifier result older than 24 h is flagged stale', () => {
  const d = dir();
  fs.writeFileSync(path.join(d, 'connection_status.json'), JSON.stringify({ checked_at: '2026-10-20T00:00:00Z', counts: {}, rows: [] }));
  assert.equal(buildConnectionStatus({ dataDir: d, now: Date.parse('2026-10-23T00:00:00Z') }).verifier.stale, true);
});

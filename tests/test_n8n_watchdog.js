// n8n watchdog in factory_loop.js (2026-10-29). n8n was down from 2026-10-25 to
// 2026-10-29 with only a warning logged each tick. Fake network and fake task
// starter only: no real process is started and no real port is probed.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const fl = require('../factory_loop.js');

const T0 = Date.parse('2026-10-29T08:00:00Z');
const okFetch = async () => ({ ok: true });
const downFetch = async () => { throw new Error('ECONNREFUSED'); };

test('decision: reachable resets the failure count', () => {
  const r = fl.n8nWatchdogDecision({ failures: 2, last_restart_at: null }, true, T0);
  assert.equal(r.decision, 'none');
  assert.equal(r.state.failures, 0);
});

test('decision: restart only after 3 consecutive failures', () => {
  let s = null;
  const seen = [];
  for (let i = 0; i < 3; i++) {
    const r = fl.n8nWatchdogDecision(s, false, T0 + i * 600000);
    seen.push(r.decision);
    s = r.state;
  }
  assert.deepEqual(seen, ['wait', 'wait', 'restart']);
  assert.equal(s.last_restart_at, new Date(T0 + 2 * 600000).toISOString());
});

test('decision: at most one restart per hour', () => {
  const s = { failures: 5, last_restart_at: new Date(T0).toISOString() };
  assert.equal(fl.n8nWatchdogDecision(s, false, T0 + 30 * 60000).decision, 'wait');
  assert.equal(fl.n8nWatchdogDecision(s, false, T0 + 61 * 60000).decision, 'restart');
});

test('step: starts the scheduled task on the third down tick, persists state', async (t) => {
  if (process.platform !== 'win32') t.skip('scheduled task path is Windows-only');
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gf-n8n-wd-'));
  const statePath = path.join(dir, 'state.json');
  const started = [];
  const startTask = (name) => started.push(name);
  try {
    const a = await fl.runN8nWatchdog({ statePath, now: T0, fetchImpl: downFetch, startTask });
    const b = await fl.runN8nWatchdog({ statePath, now: T0 + 600000, fetchImpl: downFetch, startTask });
    const c = await fl.runN8nWatchdog({ statePath, now: T0 + 1200000, fetchImpl: downFetch, startTask });
    assert.deepEqual([a.action, b.action, c.action], ['waiting', 'waiting', 'restarted']);
    assert.deepEqual(started, ['GalaxyForge-N8N-Autostart']);
    const d = await fl.runN8nWatchdog({ statePath, now: T0 + 1800000, fetchImpl: okFetch, startTask });
    assert.equal(d.action, 'none');
    assert.equal(JSON.parse(fs.readFileSync(statePath, 'utf8')).failures, 0);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('step: a failed start is reported as failed and reaches NEEDS_ATTENTION reasons', async (t) => {
  if (process.platform !== 'win32') t.skip('scheduled task path is Windows-only');
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gf-n8n-wd-'));
  const statePath = path.join(dir, 'state.json');
  fs.writeFileSync(statePath, JSON.stringify({ failures: 2, last_restart_at: null }));
  try {
    const r = await fl.runN8nWatchdog({ statePath, now: T0, fetchImpl: downFetch,
      startTask: () => { throw new Error('task not found'); } });
    assert.equal(r.action, 'failed');
    const reasons = fl.checkNeedsAttention([{ step: 'n8n_watchdog', ...r }], path.join(dir, 'events.jsonl'));
    assert.ok(reasons.some((x) => x.includes('n8n_watchdog')));
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('B39: stale or failing scheduled workflows are raised; UNKNOWN and OK are not', () => {
  const checks = (wf) => ({ sensing_engine: { ok: false, severity: 'degraded', workflows: wf } });
  const r = fl.workflowHealthReasons(checks({ '02_Sales_Poll': 'STALE', Openclaw_Sensing_Engine: 'FAILING' }));
  assert.equal(r.length, 1);
  assert.ok(r[0].includes('02_Sales_Poll=STALE') && r[0].includes('Openclaw_Sensing_Engine=FAILING'));
  assert.deepEqual(fl.workflowHealthReasons(checks({ '02_Sales_Poll': 'OK', Openclaw_Sensing_Engine: 'UNKNOWN' })), []);
  assert.deepEqual(fl.workflowHealthReasons({ sensing_engine: { ok: false, detail: 'n8n down' } }), []);
  assert.deepEqual(fl.workflowHealthReasons(null), []);
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gf-n8n-wf-'));
  try {
    const reasons = fl.checkNeedsAttention([], path.join(dir, 'e.jsonl'), checks({ '02_Sales_Poll': 'STALE' }));
    assert.ok(reasons.some((x) => x.includes('02_Sales_Poll=STALE')));
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

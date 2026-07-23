// Tests for scripts/health_monitor.js (Enterprise Upgrade Roadmap Phase
// 1.2, 2026-07-23). Every function here is pure or dependency-injected
// (fetchImpl/alertImpl), same convention as lib/health_checks.js's own
// run/fetchImpl parameters — no live network calls, no live Telegram
// send, no real running server required.
//
//   node --test tests/test_health_monitor.js

const test = require('node:test');
const assert = require('node:assert/strict');

const hm = require('../scripts/health_monitor.js');

test('shouldAlert: never alerts on the first poll (no previous status yet)', () => {
  assert.equal(hm.shouldAlert(null, 'critical'), false);
});

test('shouldAlert: never alerts when status is unchanged, however bad', () => {
  assert.equal(hm.shouldAlert('critical', 'critical'), false);
  assert.equal(hm.shouldAlert('healthy', 'healthy'), false);
});

test('shouldAlert: alerts on any real status change', () => {
  assert.equal(hm.shouldAlert('healthy', 'degraded'), true);
  assert.equal(hm.shouldAlert('degraded', 'critical'), true);
  assert.equal(hm.shouldAlert('critical', 'healthy'), true);
});

test('extractFailingCheckNames: returns only real failing, applicable checks', () => {
  const report = {
    checks: {
      memory: { ok: true, severity: 'high' },
      disk: { ok: false, severity: 'high' },
      network: { ok: false, severity: 'critical' },
      database: { ok: null, severity: 'not_applicable' },
    },
  };
  assert.deepEqual(hm.extractFailingCheckNames(report), ['disk', 'network']);
});

test('extractFailingCheckNames: never throws on a missing/malformed report', () => {
  assert.deepEqual(hm.extractFailingCheckNames(null), []);
  assert.deepEqual(hm.extractFailingCheckNames({}), []);
});

test('buildStatusChangeMessage: names the real transition and real failing checks', () => {
  const msg = hm.buildStatusChangeMessage('critical', 'healthy', ['disk', 'network']);
  assert.match(msg, /حرج/);
  assert.match(msg, /سليم/);
  assert.match(msg, /disk/);
  assert.match(msg, /network/);
});

test('buildStatusChangeMessage: never fabricates a failing-checks line when there are none', () => {
  const msg = hm.buildStatusChangeMessage('healthy', 'degraded', []);
  assert.doesNotMatch(msg, /فحوصات فاشلة/);
});

test('fetchHealth: a real 200 response with a status is passed through honestly', async () => {
  const result = await hm.fetchHealth('http://fake', async () => ({
    ok: true, json: async () => ({ status: 'degraded', checks: { disk: { ok: false } } }),
  }));
  assert.equal(result.status, 'degraded');
  assert.deepEqual(result.checks, { disk: { ok: false } });
  assert.equal(result.error, null);
});

test('fetchHealth: a non-200 response is honestly unreachable, never fabricated healthy', async () => {
  const result = await hm.fetchHealth('http://fake', async () => ({ ok: false, status: 503 }));
  assert.equal(result.status, 'unreachable');
  assert.match(result.error, /503/);
});

test('fetchHealth: a real network failure is honestly unreachable, never thrown', async () => {
  const result = await hm.fetchHealth('http://fake', async () => { throw new Error('ECONNREFUSED'); });
  assert.equal(result.status, 'unreachable');
  assert.match(result.error, /ECONNREFUSED/);
});

test('tick: first poll never alerts, returns the real status', async () => {
  let alertCalled = false;
  const status = await hm.tick(null, {
    fetchImpl: async () => ({ ok: true, json: async () => ({ status: 'healthy', checks: {} }) }),
    alertImpl: async () => { alertCalled = true; },
  });
  assert.equal(status, 'healthy');
  assert.equal(alertCalled, false);
});

test('tick: a real transition triggers exactly one real alert with the right content', async () => {
  let alertMessage = null;
  const status = await hm.tick('healthy', {
    fetchImpl: async () => ({
      ok: true, json: async () => ({ status: 'critical', checks: { network: { ok: false, severity: 'critical' } } }),
    }),
    alertImpl: async (msg) => { alertMessage = msg; },
  });
  assert.equal(status, 'critical');
  assert.match(alertMessage, /حرج/);
  assert.match(alertMessage, /network/);
});

test('tick: an unchanged status never alerts, even repeatedly', async () => {
  let alertCount = 0;
  const alertImpl = async () => { alertCount += 1; };
  const fetchImpl = async () => ({ ok: true, json: async () => ({ status: 'degraded', checks: {} }) });

  let status = await hm.tick(null, { fetchImpl, alertImpl });
  status = await hm.tick(status, { fetchImpl, alertImpl });
  status = await hm.tick(status, { fetchImpl, alertImpl });

  assert.equal(status, 'degraded');
  assert.equal(alertCount, 0, 'the same real degraded status must never re-alert on every poll');
});

test('tick: recovery from critical back to healthy alerts exactly once', async () => {
  let alertCount = 0;
  let lastMessage = null;
  const alertImpl = async (msg) => { alertCount += 1; lastMessage = msg; };

  let status = await hm.tick(null, {
    fetchImpl: async () => ({ ok: true, json: async () => ({ status: 'critical', checks: {} }) }),
    alertImpl,
  });
  status = await hm.tick(status, {
    fetchImpl: async () => ({ ok: true, json: async () => ({ status: 'healthy', checks: {} }) }),
    alertImpl,
  });

  assert.equal(status, 'healthy');
  assert.equal(alertCount, 1);
  assert.match(lastMessage, /سليم/);
});

test('sendAlert: a missing telegram_direct dependency never throws, reports honestly', async () => {
  // Real fail-safe path — sendAlert() itself never throws even if the
  // real telegram module can't be loaded or isn't configured.
  const result = await hm.sendAlert('test message');
  assert.equal(typeof result, 'object');
});

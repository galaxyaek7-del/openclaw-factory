// API contract tests (Phase 10C — Operations Automation & CI/CD).
// Unlike every other test in this repo, this one boots a real server.js
// subprocess — safe here because CI always runs against a fresh
// checkout with no already-running production instance to interfere
// with (the same reason this suite never does this against the real
// local factory: there, a second instance would collide with the one
// already running). Verifies the *shape* of the Unified Service Layer's
// contract (envelope, service registry completeness, action registry
// completeness) — not the business logic inside each service, which is
// already covered by its own tests.
//
//   node --test tests/test_api_contract.js
//
// Requires no real secrets: MISSION_CONTROL_PASSWORD is set to a
// throwaway value for the test process only; GROQ_KEY/N8N_*/GUMROAD_*
// are all optional at server startup (confirmed: server.js never fails
// to boot without them, it only degrades those specific features).

const test = require('node:test');
const assert = require('node:assert/strict');
const { spawn } = require('child_process');
const path = require('path');

const PORT = 3199; // distinct from the interactive-session convention (3099), to avoid any collision if both ever run at once
const BASE_URL = `http://localhost:${PORT}`;
const TEST_PASSWORD = 'contract-test-password';
const REPO_ROOT = path.join(__dirname, '..');

let serverProcess;
let cookie;

async function waitForServer(timeoutMs = 15000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(`${BASE_URL}/api/dashboard`);
      if (res.status) return;
    } catch {
      // not up yet
    }
    await new Promise(r => setTimeout(r, 200));
  }
  throw new Error('server did not become ready in time');
}

test.before(async () => {
  serverProcess = spawn(process.execPath, ['server.js'], {
    cwd: REPO_ROOT,
    env: { ...process.env, PORT: String(PORT), MISSION_CONTROL_PASSWORD: TEST_PASSWORD },
  });
  await waitForServer();

  const loginRes = await fetch(`${BASE_URL}/api/mission-control/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password: TEST_PASSWORD }),
  });
  const setCookie = loginRes.headers.get('set-cookie');
  assert.ok(setCookie, 'login must set a session cookie');
  cookie = setCookie.split(';')[0];
});

test.after(() => {
  if (serverProcess) serverProcess.kill();
});

test('GET /api/v1/docs lists every registered service with both a data and health endpoint', async () => {
  const res = await fetch(`${BASE_URL}/api/v1/docs`, { headers: { Cookie: cookie } });
  assert.equal(res.status, 200);
  const body = await res.json();
  assert.equal(body.success, true);
  assert.ok(Array.isArray(body.services));
  assert.ok(body.services.length >= 11, `expected at least 11 services, got ${body.services.length}`);
  for (const svc of body.services) {
    assert.equal(svc.data_endpoint, `/api/v1/${svc.name}`);
    assert.equal(svc.health_endpoint, `/api/v1/${svc.name}/health`);
    assert.ok(svc.description && svc.description.length > 0);
  }
});

test('every documented service responds 200 with the standard success envelope', async () => {
  const docsRes = await fetch(`${BASE_URL}/api/v1/docs`, { headers: { Cookie: cookie } });
  const { services } = await docsRes.json();
  for (const svc of services) {
    const res = await fetch(`${BASE_URL}${svc.data_endpoint}`, { headers: { Cookie: cookie } });
    assert.equal(res.status, 200, `${svc.name} data endpoint should return 200`);
    const body = await res.json();
    assert.equal(body.success, true, `${svc.name} should report success:true`);
    assert.equal(body.service, svc.name);
    assert.equal(body.version, 'v1');
    assert.ok('data' in body, `${svc.name} response must have a data field`);
  }
});

test('every documented service health endpoint responds with a real status', async () => {
  const docsRes = await fetch(`${BASE_URL}/api/v1/docs`, { headers: { Cookie: cookie } });
  const { services } = await docsRes.json();
  for (const svc of services) {
    const res = await fetch(`${BASE_URL}${svc.health_endpoint}`, { headers: { Cookie: cookie } });
    assert.equal(res.status, 200, `${svc.name} health endpoint should return 200`);
    const body = await res.json();
    assert.equal(body.success, true);
    assert.ok(['ok', 'error'].includes(body.status), `${svc.name} health status must be ok/error, got ${body.status}`);
  }
});

test('GET /api/v1/health aggregates all documented services', async () => {
  const docsRes = await fetch(`${BASE_URL}/api/v1/docs`, { headers: { Cookie: cookie } });
  const { services } = await docsRes.json();
  const res = await fetch(`${BASE_URL}/api/v1/health`, { headers: { Cookie: cookie } });
  assert.equal(res.status, 200);
  const body = await res.json();
  assert.equal(body.total_count, services.length);
  assert.ok(['healthy', 'degraded', 'unhealthy'].includes(body.overall));
});

test('GET /api/v1/metrics returns valid Prometheus exposition format', async () => {
  const res = await fetch(`${BASE_URL}/api/v1/metrics`, { headers: { Cookie: cookie } });
  assert.equal(res.status, 200);
  assert.match(res.headers.get('content-type'), /text\/plain/);
  const text = await res.text();
  assert.match(text, /^# HELP openclaw_uptime_seconds/m);
  assert.match(text, /^# TYPE openclaw_uptime_seconds gauge/m);
});

test('GET /api/v1/actions lists every registered action with a name, description, and kind', async () => {
  const res = await fetch(`${BASE_URL}/api/v1/actions`, { headers: { Cookie: cookie } });
  assert.equal(res.status, 200);
  const body = await res.json();
  assert.ok(Array.isArray(body.actions));
  assert.ok(body.actions.length >= 8, `expected at least 8 actions, got ${body.actions.length}`);
  for (const action of body.actions) {
    assert.ok(action.name);
    assert.ok(['sync', 'async'].includes(action.kind));
    assert.equal(typeof action.reversible, 'boolean');
  }
});

test('POST /api/v1/actions/:name requires confirmed:true (contract, not just one action)', async () => {
  const res = await fetch(`${BASE_URL}/api/v1/actions/refresh-data`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Cookie: cookie },
    body: JSON.stringify({}),
  });
  assert.equal(res.status, 400);
  const body = await res.json();
  assert.equal(body.success, false);
  assert.equal(body.error.code, 'confirmation_required');
});

test('unauthenticated requests to /api/v1/* are rejected as JSON, not redirected', async () => {
  const res = await fetch(`${BASE_URL}/api/v1/company-health`, { redirect: 'manual' });
  assert.equal(res.status, 401);
  const body = await res.json();
  assert.equal(body.success, false);
});

test('unknown /api/v1/* path returns a 404 JSON envelope, not the SPA fallback', async () => {
  const res = await fetch(`${BASE_URL}/api/v1/not-a-real-service`, { headers: { Cookie: cookie } });
  assert.equal(res.status, 404);
  const contentType = res.headers.get('content-type');
  assert.match(contentType, /application\/json/);
});

test('GET /api/dashboard (pre-existing, unauthenticated) still responds 200', async () => {
  const res = await fetch(`${BASE_URL}/api/dashboard`);
  assert.equal(res.status, 200);
  const body = await res.json();
  assert.equal(body.success, true);
});

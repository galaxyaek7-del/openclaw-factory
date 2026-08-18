// Security P1 bundle (2026-08-18), server-side fixes 3-5:
//   3) per-IP rate limit on the 5 production routes that spawn real
//      subprocesses / spend real Groq budget (/generate-book,
//      /api/distribute, /webhooks/paddle, /api/agent/:name,
//      /api/scout/run);
//   4) security response headers (nosniff, frame options, referrer
//      policy, HSTS, CSP) on every response;
//   5) append-only auth audit ledger (at/event/ip only -- never
//      passwords or tokens) on login success/failure and logout.
// Spawns its OWN dedicated server.js subprocess (port 3197, distinct
// from test_login_security.js's 3198 and test_api_contract.js's 3199)
// with a tiny PRODUCTION_RATE_LIMIT_MAX and a temp AUTH_AUDIT_FILE so
// the real in-memory limiter state and the real audit writes can be
// exercised without touching production data.
//
//   node --test tests/test_security_p1.js

const test = require('node:test');
const assert = require('node:assert/strict');
const { spawn } = require('child_process');
const path = require('path');
const os = require('os');
const fs = require('fs');

const PORT = 3197; // distinct from test_login_security.js's 3198 and test_api_contract.js's 3199
const BASE_URL = `http://localhost:${PORT}`;
const TEST_PASSWORD = 'security-p1-test-password';
const TEST_TOKEN = 'security-p1-internal-token';
const AUTH_AUDIT_FILE = path.join(os.tmpdir(), `security_p1_auth_audit_${process.pid}.jsonl`);
const REPO_ROOT = path.join(__dirname, '..');

let serverProcess;

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

function distribute() {
  // Cheap path: no `record` -> real 400, but the limiter runs first.
  return fetch(`${BASE_URL}/api/distribute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Internal-Token': TEST_TOKEN },
    body: JSON.stringify({}),
  });
}

function readAuditLines() {
  if (!fs.existsSync(AUTH_AUDIT_FILE)) return [];
  return fs.readFileSync(AUTH_AUDIT_FILE, 'utf8').split('\n').filter(Boolean).map(JSON.parse);
}

test.before(async () => {
  serverProcess = spawn(process.execPath, ['server.js'], {
    cwd: REPO_ROOT,
    env: {
      ...process.env,
      PORT: String(PORT),
      MISSION_CONTROL_PASSWORD: TEST_PASSWORD,
      INTERNAL_SERVICE_TOKEN: TEST_TOKEN,
      // Real, explicit overrides of the same real env vars a founder could
      // set -- PRODUCTION_RATE_LIMIT_MAX=3 so the limiter is trippable in
      // a test, AUTH_AUDIT_FILE at a temp path so the real writes land in
      // a disposable file instead of data/auth_audit.jsonl.
      PRODUCTION_RATE_LIMIT_MAX: '3',
      AUTH_AUDIT_FILE,
    },
  });
  await waitForServer();
});

test.after(() => {
  if (serverProcess) serverProcess.kill();
  try { fs.unlinkSync(AUTH_AUDIT_FILE); } catch (_) {}
});

test('every response carries the security headers (fix 4)', async () => {
  const res = await fetch(`${BASE_URL}/api/dashboard`);
  assert.equal(res.status, 200);
  assert.equal(res.headers.get('x-content-type-options'), 'nosniff');
  assert.equal(res.headers.get('x-frame-options'), 'SAMEORIGIN');
  assert.equal(res.headers.get('referrer-policy'), 'no-referrer');
  assert.ok(res.headers.get('strict-transport-security'), 'HSTS header must be present');
  const csp = res.headers.get('content-security-policy');
  assert.ok(csp, 'CSP header must be present');
  assert.match(csp, /default-src 'self'/);
  assert.match(csp, /frame-ancestors 'none'/);
  assert.match(csp, /object-src 'none'/);
  assert.match(csp, /script-src 'self' 'unsafe-inline'/);
});

test('the production routes pass normally below the rate limit (fix 3, normal path)', async () => {
  for (let i = 0; i < 3; i++) {
    const res = await distribute();
    assert.equal(res.status, 400, `attempt ${i + 1} should be the route's own 400 (missing record), not 429 yet`);
  }
});

test('the next production request is rate-limited (429) once the window budget is exhausted (fix 3)', async () => {
  const res = await distribute();
  assert.equal(res.status, 429, 'the 4th request in the window must be rate-limited');
  const body = await res.json();
  assert.match(body.error, /Too many production requests/);
});

test('rate limiting one production route does not bleed into unrelated routes', async () => {
  const dashboard = await fetch(`${BASE_URL}/api/dashboard`);
  assert.equal(dashboard.status, 200, 'GET /api/dashboard must be unaffected by the /api/distribute limiter');
  const login = await fetch(`${BASE_URL}/api/mission-control/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password: TEST_PASSWORD }),
  });
  assert.equal(login.status, 200, 'a real login must not be blocked by the production-route limiter');
});

test('auth events are appended to the audit ledger, never containing secrets (fix 5)', async () => {
  await fetch(`${BASE_URL}/api/mission-control/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password: 'definitely-wrong-password' }),
  });
  await fetch(`${BASE_URL}/api/mission-control/logout`, { method: 'POST' });

  const lines = readAuditLines();
  const events = lines.map(l => l.event);
  assert.ok(events.includes('login_success'), `expected a login_success record, got ${events}`);
  assert.ok(events.includes('login_failure'), `expected a login_failure record, got ${events}`);
  assert.ok(events.includes('logout'), `expected a logout record, got ${events}`);

  const raw = fs.readFileSync(AUTH_AUDIT_FILE, 'utf8');
  assert.ok(!raw.includes(TEST_PASSWORD), 'the audit ledger must never contain the password');
  assert.ok(!raw.includes('mc|'), 'the audit ledger must never contain a session token payload');
  assert.ok(!raw.includes('security-p1-internal-token'), 'the audit ledger must never contain the internal token');

  for (const line of lines) {
    assert.deepEqual(Object.keys(line).sort(), ['at', 'event', 'ip'], 'each record must carry exactly at/event/ip');
    assert.equal(typeof line.ip, 'string', 'ip must be a real string');
  }
});
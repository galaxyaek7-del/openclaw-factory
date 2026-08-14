// Tests for the Internal Market Validation System (Founder Directive,
// 2026-08-14): public validation page + public submit, auth-gated
// internal dashboard, and the no-PII protection rule. Boots the real
// server.js (same pattern as tests/test_customer_front_door.js), with
// VALIDATION_RESPONSES_PATH pointed at a temp ledger so these tests
// never write into the real data/validation_responses.jsonl file.
//
//   node --test tests/test_market_validation.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawn } = require('child_process');

const PORT = 3299; // distinct from test_customer_front_door.js's 3298 and test_api_contract.js's 3199
const BASE_URL = `http://localhost:${PORT}`;
const TEST_PASSWORD = 'validation-test-password';
const REPO_ROOT = path.join(__dirname, '..');
const TEMP_LEDGER = path.join(os.tmpdir(), `val_ledger_${process.pid}.jsonl`);

let serverProcess;

async function waitForServer(timeoutMs = 15000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(`${BASE_URL}/api/dashboard`);
      if (res.status) return;
    } catch { /* not up yet */ }
    await new Promise((r) => setTimeout(r, 200));
  }
  throw new Error('server did not become ready in time');
}

function login() {
  return fetch(`${BASE_URL}/api/mission-control/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password: TEST_PASSWORD }),
  });
}

const VALID_PAYLOAD = {
  q1_frequency: 'weekly',
  q2_intent: 'maybe',
  q3_pain: 'I lose hours verifying whether my citations are still good law.',
  source: 'linkedin',
  professional_role: 'Solo attorney',
  practice_area: 'Family law',
  contact: 'real.prospect@example.com',
};

test.before(async () => {
  if (fs.existsSync(TEMP_LEDGER)) fs.unlinkSync(TEMP_LEDGER);
  serverProcess = spawn(process.execPath, ['server.js'], {
    cwd: REPO_ROOT,
    env: { ...process.env, PORT: String(PORT), MISSION_CONTROL_PASSWORD: TEST_PASSWORD, VALIDATION_RESPONSES_PATH: TEMP_LEDGER },
  });
  await waitForServer();
});

test.after(() => {
  if (serverProcess) serverProcess.kill();
  if (fs.existsSync(TEMP_LEDGER)) fs.unlinkSync(TEMP_LEDGER);
});

test('public validation page is reachable unauthenticated and is a real responsive HTML page', async () => {
  const res = await fetch(`${BASE_URL}/market-validation.html`);
  assert.equal(res.status, 200);
  const body = await res.text();
  assert.match(body, /Professional Legal Research — Help Us Validate This/, 'must carry the exact founder headline');
  assert.match(body, /\$194/, 'must state the $194 future price');
  assert.match(body, /NOT a launched product/, 'must declare validation-status, not a live product');
  assert.match(body, /name="viewport" content="width=device-width/, 'must be mobile responsive');
  assert.match(body, /@media/, 'must have a real responsive breakpoint');
});

test('internal dashboard PAGE is protected: unauthenticated -> redirected to login', async () => {
  // requireMissionControlAuth sends non-API HTML GETs to the login page
  // (302), not a 401 JSON — the established pattern every other protected
  // Mission Control page follows. The point is the page content must never
  // be served unauthenticated.
  const res = await fetch(`${BASE_URL}/validation-dashboard.html`, { redirect: 'manual' });
  assert.equal(res.status, 302);
  assert.ok(res.headers.get('location').includes('mission_control_login.html'), 'must redirect to the real login page');
});

test('internal dashboard API is protected: unauthenticated -> 401', async () => {
  const res = await fetch(`${BASE_URL}/api/validation/dashboard`);
  assert.equal(res.status, 401);
});

test('public submit records exactly one real response', async () => {
  const res = await fetch(`${BASE_URL}/api/validation/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(VALID_PAYLOAD),
  });
  assert.equal(res.status, 200);
  const body = await res.json();
  assert.equal(body.success, true);
  assert.equal(body.recorded, true);
  const lines = fs.readFileSync(TEMP_LEDGER, 'utf8').split('\n').filter(Boolean);
  assert.equal(lines.length, 1);
});

test('public submit rejects a bad source at the boundary', async () => {
  const res = await fetch(`${BASE_URL}/api/validation/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...VALID_PAYLOAD, source: 'tiktok' }),
  });
  assert.equal(res.status, 400);
  const body = await res.json();
  assert.equal(body.success, false);
});

test('public submit rejects invalid q2 at the boundary', async () => {
  const res = await fetch(`${BASE_URL}/api/validation/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...VALID_PAYLOAD, q2_intent: 'definitely' }),
  });
  assert.equal(res.status, 400);
  const body = await res.json();
  assert.equal(body.success, false);
});

test('public submit rejects a duplicate (no phantom second response)', async () => {
  const res = await fetch(`${BASE_URL}/api/validation/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(VALID_PAYLOAD),
  });
  assert.equal(res.status, 400);
  const body = await res.json();
  assert.equal(body.success, false);
  const lines = fs.readFileSync(TEMP_LEDGER, 'utf8').split('\n').filter(Boolean);
  assert.equal(lines.length, 1);
});

test('dashboard API is reachable with a real login and exposes only aggregates', async () => {
  const loginRes = await login();
  assert.equal(loginRes.status, 200);
  const cookie = loginRes.headers.get('set-cookie').split(';')[0];

  const res = await fetch(`${BASE_URL}/api/validation/dashboard`, { headers: { Cookie: cookie } });
  assert.equal(res.status, 200);
  const body = await res.json();
  const s = body.summary;
  assert.equal(s.total_responses, 1);
  assert.equal(s.qualified_responses, 1);
  assert.equal(s.q2_maybe, 1);
  assert.equal(s.source_breakdown.linkedin, 1);
  assert.ok(Array.isArray(s.top_pain_themes));
  const dumped = JSON.stringify(body);
  assert.ok(!dumped.includes('real.prospect@example.com'), 'aggregate must never expose a contact email');
  assert.ok(!dumped.includes('I lose hours'), 'aggregate must never expose verbatim q3 text');
});

test('dashboard page is reachable with a real login', async () => {
  const loginRes = await login();
  assert.equal(loginRes.status, 200);
  const cookie = loginRes.headers.get('set-cookie').split(';')[0];
  const res = await fetch(`${BASE_URL}/validation-dashboard.html`, { headers: { Cookie: cookie } });
  assert.equal(res.status, 200);
  const body = await res.text();
  assert.match(body, /<title>Market Validation Dashboard/, 'must be the internal dashboard page');
});

// Tests for Security Mission Tracker finding 2.3 (2026-07-23): the
// Mission Control login password comparison and its new rate limiter.
// Spawns its OWN dedicated server.js subprocess (a different port from
// tests/test_api_contract.js's shared instance) specifically so the
// real, in-memory loginFailureTimestamps state this fix adds can be
// deliberately exhausted by these tests without bleeding into any other
// test file's shared server process.
//
//   node --test tests/test_login_security.js

const test = require('node:test');
const assert = require('node:assert/strict');
const { spawn } = require('child_process');
const path = require('path');

const PORT = 3198; // distinct from test_api_contract.js's 3199 and the interactive-session convention (3099)
const BASE_URL = `http://localhost:${PORT}`;
const TEST_PASSWORD = 'login-security-test-password';
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

function login(password) {
  return fetch(`${BASE_URL}/api/mission-control/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  });
}

test.before(async () => {
  serverProcess = spawn(process.execPath, ['server.js'], {
    cwd: REPO_ROOT,
    env: {
      ...process.env, PORT: String(PORT), MISSION_CONTROL_PASSWORD: TEST_PASSWORD,
      // Keep the real 15-minute default window out of this fast test
      // suite's way -- these are real, explicit overrides of the same
      // real env vars a founder could set, not a different code path.
      MISSION_CONTROL_LOGIN_MAX_ATTEMPTS: '3', MISSION_CONTROL_LOGIN_WINDOW_MS: '2000',
    },
  });
  await waitForServer();
});

test.after(() => {
  if (serverProcess) serverProcess.kill();
});

test('a correct password still logs in successfully (no regression from the timing-safe rewrite)', async () => {
  const res = await login(TEST_PASSWORD);
  assert.equal(res.status, 200);
  assert.ok(res.headers.get('set-cookie'), 'a real session cookie must be set on success');
});

test('a wrong password of a DIFFERENT length than the real one is still correctly rejected', async () => {
  // Real regression risk specific to this fix: timingSafeEqualStrings()
  // requires equal-length buffers and returns false early otherwise --
  // must never throw or silently misbehave for the (very real) common
  // case of a wrong-length guess.
  const res = await login('x');
  assert.equal(res.status, 401);
  // Every test in this file shares one real, live server process (and
  // therefore its real in-memory failure counter) -- reset it here so
  // this test's one deliberate failure never leaks into the next test's
  // own exact-count expectations.
  await login(TEST_PASSWORD);
});

test('after MAX_ATTEMPTS real failures, the next attempt is rate-limited (429), even with the correct password', async () => {
  for (let i = 0; i < 3; i++) {
    const res = await login('definitely wrong');
    assert.equal(res.status, 401, `attempt ${i + 1} should still be a normal 401, not yet rate-limited`);
  }
  const limited = await login(TEST_PASSWORD);
  assert.equal(limited.status, 429, 'the real correct password must still be rejected once the real attempt budget is exhausted');
  const body = await limited.json();
  assert.match(body.error, /محاولات كثيرة/);
});

test('the rate limit window genuinely expires and real access is restored', async () => {
  for (let i = 0; i < 3; i++) {
    await login('wrong again');
  }
  const limited = await login(TEST_PASSWORD);
  assert.equal(limited.status, 429);

  // MISSION_CONTROL_LOGIN_WINDOW_MS=2000 for this test process.
  await new Promise(r => setTimeout(r, 2200));

  const restored = await login(TEST_PASSWORD);
  assert.equal(restored.status, 200, 'a real, sufficiently old failure window must genuinely clear, not stay locked forever');
});

test('a real successful login resets the failure counter (does not carry over to the next real lockout window)', async () => {
  await login('wrong once');
  await login('wrong twice');
  const success = await login(TEST_PASSWORD);
  assert.equal(success.status, 200);

  // 2 prior failures should have been cleared by the success above --
  // a fresh set of failures must need the full MAX_ATTEMPTS again, not
  // immediately trip the limiter from residual count.
  await login('wrong yet again');
  const stillNormal = await login('wrong yet again 2');
  assert.equal(stillNormal.status, 401, 'must still be a normal 401, not prematurely rate-limited from a cleared counter');
});

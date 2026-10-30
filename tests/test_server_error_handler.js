// server.js last error handler (2026-10-30): a malformed JSON body used to
// come back as an HTML page with the full stack trace and local file paths.
// Spawns its own server on a test port; the requests below write nothing
// (the body is rejected before any route runs).
'use strict';
const test = require('node:test');
const assert = require('node:assert');
const path = require('path');
const { spawn } = require('child_process');

const REPO_ROOT = path.join(__dirname, '..');
const PORT = 3233; // distinct from the other server-spawning suites (3197-3299)
const BASE_URL = `http://localhost:${PORT}`;
let serverProcess;

async function waitForServer(timeoutMs = 20000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(`${BASE_URL}/site/`);
      if (res.status) return;
    } catch { /* not up yet */ }
    await new Promise((r) => setTimeout(r, 200));
  }
  throw new Error('server did not become ready in time');
}

test.before(async () => {
  serverProcess = spawn(process.execPath, ['server.js'], {
    cwd: REPO_ROOT,
    env: { ...process.env, PORT: String(PORT), MISSION_CONTROL_PASSWORD: 'error-handler-test-password' },
  });
  await waitForServer();
});

test.after(() => {
  if (serverProcess) serverProcess.kill();
});

test('malformed JSON gets a 400 JSON answer with no stack trace or file path', async () => {
  const res = await fetch(`${BASE_URL}/api/customer/interest`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{x',
  });
  assert.equal(res.status, 400);
  assert.match(res.headers.get('content-type') || '', /application\/json/);
  const text = await res.text();
  assert.deepEqual(JSON.parse(text), { success: false, error: 'request body is not valid JSON' });
  assert.doesNotMatch(text, /node_modules|SyntaxError|at JSON\.parse|openclaw/i);
});

test('a normal route still works after the handler', async () => {
  const res = await fetch(`${BASE_URL}/health`);
  assert.ok([200, 503].includes(res.status), `unexpected ${res.status}`);
});

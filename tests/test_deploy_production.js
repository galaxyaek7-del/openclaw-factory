// Regression test for the Phase 10 red-team audit's HIGH finding:
// scripts/deploy_production.js used to declare a --confirm deploy
// successful (and log a success recovery-action entry) immediately after
// spawn(), with no check that the new server process actually came up.
// Fixed: waitForHealthy() polls the real health endpoint before the
// script decides success/failure. This test exercises that function
// directly, in isolation, against a real throwaway HTTP server.
//
//   node --test tests/test_deploy_production.js

const test = require('node:test');
const assert = require('node:assert/strict');
const http = require('http');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { waitForHealthy, checkServerSyntax } = require('../scripts/deploy_production.js');

test('waitForHealthy: resolves true quickly once the real endpoint returns 200', async () => {
  const server = http.createServer((req, res) => {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end('{"success":true}');
  });
  await new Promise(resolve => server.listen(0, resolve));
  const port = server.address().port;
  try {
    const healthy = await waitForHealthy(port, 5000, 50);
    assert.equal(healthy, true);
  } finally {
    server.close();
  }
});

test('waitForHealthy: resolves false when nothing is listening on the port', async () => {
  // A port nothing is bound to (high, unlikely-to-collide port).
  const healthy = await waitForHealthy(58234, 500, 100);
  assert.equal(healthy, false);
});

test('waitForHealthy: resolves false when the server responds with a non-200 status', async () => {
  const server = http.createServer((req, res) => {
    res.writeHead(500, { 'Content-Type': 'application/json' });
    res.end('{"success":false}');
  });
  await new Promise(resolve => server.listen(0, resolve));
  const port = server.address().port;
  try {
    const healthy = await waitForHealthy(port, 500, 100);
    assert.equal(healthy, false);
  } finally {
    server.close();
  }
});

// Operational-excellence follow-up: deploy_production.js used to kill the
// existing live server BEFORE checking anything about the new code at
// all -- a bad commit that doesn't even parse (a real, common failure
// mode) would previously have been discovered only after the old process
// was already dead. checkServerSyntax() is the cheap pre-flight gate that
// now runs before that kill step. Uses a real scratch repo directory
// (never the real server.js), with both a valid and a genuinely broken
// file, so this proves the check actually distinguishes them.
test('checkServerSyntax: a real, valid JS file passes', () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'test_deploy_syntax_'));
  try {
    fs.writeFileSync(path.join(tmpDir, 'server.js'), 'const x = 1 + 1;\nconsole.log(x);\n');
    const result = checkServerSyntax(tmpDir);
    assert.equal(result.ok, true);
    assert.equal(result.error, undefined);
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
});

test('checkServerSyntax: a real, genuinely broken JS file fails, with a real error message', () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'test_deploy_syntax_'));
  try {
    fs.writeFileSync(path.join(tmpDir, 'server.js'), 'const x = 1 +\n'); // deliberately incomplete
    const result = checkServerSyntax(tmpDir);
    assert.equal(result.ok, false);
    assert.ok(result.error && result.error.length > 0, 'a real syntax error message must be captured');
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
});

test('checkServerSyntax: the real, current server.js passes (sanity check against the actual live file)', () => {
  const repoRoot = path.join(__dirname, '..');
  const result = checkServerSyntax(repoRoot);
  assert.equal(result.ok, true, `the real server.js must currently pass its own pre-flight check: ${result.error}`);
});

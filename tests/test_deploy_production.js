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
const { waitForHealthy } = require('../scripts/deploy_production.js');

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

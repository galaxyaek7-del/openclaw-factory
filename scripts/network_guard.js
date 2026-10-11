#!/usr/bin/env node
/**
 * Cycle 77 section 2 — global network block for the JS test suite.
 *
 * Preloaded via `node --require ./scripts/network_guard.js --test ...`
 * (scripts/run_js_group.js, the real CI entrypoint for every JS test
 * group). Monkeypatches net.Socket.prototype.connect — the one real
 * chokepoint every Node HTTP/HTTPS client (fetch, http.request,
 * https.request) ultimately calls — to throw instead of opening a real
 * socket, unless the current process explicitly opted out via
 * ALLOW_REAL_NETWORK_TESTS=1 (set only by a deliberately-real test file,
 * never globally in CI).
 *
 * Loopback connections (127.0.0.1 / ::1 / localhost) are NOT blocked:
 * this factory's own test suite legitimately boots real local HTTP
 * servers (server.js on an ephemeral port) and talks to them in-process
 * — that is not "the network", it never leaves the machine, and
 * blocking it would break dozens of already-correct, already-offline
 * tests for no real safety gain.
 */
'use strict';

const net = require('net');

if (process.env.ALLOW_REAL_NETWORK_TESTS === '1') {
  module.exports = { active: false };
  return;
}

const LOOPBACK_HOSTS = new Set(['127.0.0.1', '::1', 'localhost', '0.0.0.0', '::']);

function isLoopback(host) {
  if (host === undefined || host === null) return true; // no host = connecting to a path/fd, not a remote network call
  return LOOPBACK_HOSTS.has(String(host));
}

function extractHost(args) {
  // net.Socket#connect has several real call shapes:
  //   connect(path)                      -- unix socket, not network
  //   connect(port, host, cb)
  //   connect(options, cb)
  const first = args[0];
  if (first && typeof first === 'object') {
    return first.host || first.hostname || first.path;
  }
  if (typeof first === 'number' && typeof args[1] === 'string') {
    return args[1];
  }
  return undefined;
}

const originalConnect = net.Socket.prototype.connect;

net.Socket.prototype.connect = function guardedConnect(...args) {
  const host = extractHost(args);
  if (!isLoopback(host)) {
    const err = new Error(
      `Real network access blocked during tests (attempted connect to "${host}"). ` +
      'If this test deliberately needs real network, set ALLOW_REAL_NETWORK_TESTS=1 ' +
      'for that specific run (scripts/network_guard.js).'
    );
    err.code = 'EFACTORYNETWORKBLOCKED';
    throw err;
  }
  return originalConnect.apply(this, args);
};

module.exports = { active: true };

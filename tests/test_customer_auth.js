// Tests for lib/customer_auth.js — customer account password hashing and
// session signing. Uses Node's built-in test runner (node:test). Every
// test uses a temp path for the session secret, never the real
// data/.customer_session_secret.
//
//   node --test tests/test_customer_auth.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const auth = require('../lib/customer_auth.js');

const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'customer_auth_'));

test('hashPassword/verifyPassword: correct password verifies', () => {
  const stored = auth.hashPassword('correct horse battery staple');
  assert.ok(stored.startsWith('scrypt$'));
  assert.equal(auth.verifyPassword('correct horse battery staple', stored), true);
});

test('hashPassword/verifyPassword: wrong password fails', () => {
  const stored = auth.hashPassword('correct horse battery staple');
  assert.equal(auth.verifyPassword('wrong password', stored), false);
});

test('hashPassword: two hashes of the same password differ (random salt)', () => {
  const a = auth.hashPassword('same input');
  const b = auth.hashPassword('same input');
  assert.notEqual(a, b);
  assert.equal(auth.verifyPassword('same input', a), true);
  assert.equal(auth.verifyPassword('same input', b), true);
});

test('verifyPassword: malformed/missing stored hash never throws, returns false', () => {
  assert.equal(auth.verifyPassword('x', null), false);
  assert.equal(auth.verifyPassword('x', ''), false);
  assert.equal(auth.verifyPassword('x', 'not-a-real-hash'), false);
  assert.equal(auth.verifyPassword('x', 'scrypt$onlyonepart'), false);
  assert.equal(auth.verifyPassword('x', 'md5$deadbeef$deadbeef'), false);
});

test('generateAccountId: unique, prefixed', () => {
  const a = auth.generateAccountId();
  const b = auth.generateAccountId();
  assert.match(a, /^acct_[0-9a-f]{16}$/);
  assert.notEqual(a, b);
});

test('signCustomerSession/verifyCustomerSession: round-trips the account id', () => {
  const secret = 'test-secret';
  const token = auth.signCustomerSession(secret, 'acct_abc123');
  assert.equal(auth.verifyCustomerSession(secret, token), 'acct_abc123');
});

test('verifyCustomerSession: rejects a tampered token', () => {
  const secret = 'test-secret';
  const token = auth.signCustomerSession(secret, 'acct_abc123');
  const tampered = token.replace('acct_abc123', 'acct_evilevil');
  assert.equal(auth.verifyCustomerSession(secret, tampered), null);
});

test('verifyCustomerSession: rejects a token signed with a different secret', () => {
  const token = auth.signCustomerSession('secret-one', 'acct_abc123');
  assert.equal(auth.verifyCustomerSession('secret-two', token), null);
});

test('verifyCustomerSession: rejects malformed/missing tokens, never throws', () => {
  const secret = 'test-secret';
  assert.equal(auth.verifyCustomerSession(secret, null), null);
  assert.equal(auth.verifyCustomerSession(secret, ''), null);
  assert.equal(auth.verifyCustomerSession(secret, 'no-dot-here'), null);
  assert.equal(auth.verifyCustomerSession(secret, 'payload.not-hex-mac'), null);
});

test('verifyCustomerSession: a Mission Control mc_session-shaped token never verifies here', () => {
  // Different payload shape ("mc|<ts>" vs "cust|<id>|<ts>") and a
  // deliberately separate secret space -- a founder session must never
  // double as a customer session.
  const crypto = require('crypto');
  const secret = 'test-secret';
  const payload = `mc|${Date.now()}`;
  const mac = crypto.createHmac('sha256', secret).update(payload).digest('hex');
  const mcShapedToken = `${payload}.${mac}`;
  assert.equal(auth.verifyCustomerSession(secret, mcShapedToken), null);
});

test('loadOrCreateSessionSecret: creates once, persists, returns the same value on reload', () => {
  const secretPath = path.join(tmpDir, '.session_secret');
  assert.equal(fs.existsSync(secretPath), false);
  const first = auth.loadOrCreateSessionSecret(secretPath);
  assert.ok(first.length > 0);
  assert.equal(fs.existsSync(secretPath), true);
  const second = auth.loadOrCreateSessionSecret(secretPath);
  assert.equal(first, second);
});

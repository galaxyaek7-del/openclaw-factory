// Galaxy Forge — Customer account authentication primitives (Customer
// Platform Round 1, 2026-07-29).
//
// Reuses the exact pattern server.js already established for the founder's
// own Mission Control session (crypto.createHmac signed token + a
// crypto.timingSafeEqual verify, deliberately no express-session/
// jsonwebtoken/bcrypt npm dependency) rather than inventing a second style.
// Password hashing uses Node's built-in crypto.scrypt — the one piece
// mc_session never needed (it's a single shared password, not per-account
// credentials) — so this is still zero new npm dependencies.
//
// Deliberately a SEPARATE secret/signing scheme from MISSION_CONTROL_
// SESSION_SECRET: a customer session token must never be usable to forge a
// founder Mission Control session, or vice versa.
//
// Pure functions only (no fs/Express here) so this is unit-testable in
// isolation, same discipline as lib/dashboard_data.js and
// lib/next_sale_id.js. The one piece of file I/O this system needs
// (persisting the session secret across restarts) lives in
// loadOrCreateSessionSecret(), kept separate and given an explicit path so
// tests never touch the real data/ directory.

const crypto = require('crypto');
const fs = require('fs');

const SCRYPT_KEYLEN = 64;
const SALT_BYTES = 16;

function timingSafeEqualStrings(a, b) {
  const bufA = Buffer.from(String(a));
  const bufB = Buffer.from(String(b));
  if (bufA.length !== bufB.length) return false;
  return crypto.timingSafeEqual(bufA, bufB);
}

// "scrypt$<saltHex>$<hashHex>" — self-describing so a future algorithm
// change doesn't break verification of already-stored hashes.
function hashPassword(password) {
  const salt = crypto.randomBytes(SALT_BYTES);
  const hash = crypto.scryptSync(String(password), salt, SCRYPT_KEYLEN);
  return `scrypt$${salt.toString('hex')}$${hash.toString('hex')}`;
}

function verifyPassword(password, stored) {
  if (!stored || typeof stored !== 'string') return false;
  const parts = stored.split('$');
  if (parts.length !== 3 || parts[0] !== 'scrypt') return false;
  const [, saltHex, hashHex] = parts;
  let salt, expected;
  try {
    salt = Buffer.from(saltHex, 'hex');
    expected = Buffer.from(hashHex, 'hex');
  } catch {
    return false;
  }
  const actual = crypto.scryptSync(String(password), salt, expected.length || SCRYPT_KEYLEN);
  if (actual.length !== expected.length) return false;
  return crypto.timingSafeEqual(actual, expected);
}

function generateAccountId() {
  return 'acct_' + crypto.randomBytes(8).toString('hex');
}

// Payload carries the account_id (unlike mc_session's identity-free
// "mc|<timestamp>" — Mission Control has exactly one implicit user;
// customer accounts are genuinely multi-tenant).
function signCustomerSession(secret, accountId) {
  const payload = `cust|${accountId}|${Date.now()}`;
  const mac = crypto.createHmac('sha256', secret).update(payload).digest('hex');
  return `${payload}.${mac}`;
}

// Returns the verified account_id, or null if the token is missing,
// malformed, or its signature doesn't match.
function verifyCustomerSession(secret, token) {
  if (!token || !token.includes('.')) return null;
  const dot = token.lastIndexOf('.');
  const payload = token.slice(0, dot);
  const mac = token.slice(dot + 1);
  const expected = crypto.createHmac('sha256', secret).update(payload).digest('hex');
  let macBuf, expectedBuf;
  try {
    macBuf = Buffer.from(mac, 'hex');
    expectedBuf = Buffer.from(expected, 'hex');
  } catch {
    return null;
  }
  if (macBuf.length !== expectedBuf.length || !crypto.timingSafeEqual(macBuf, expectedBuf)) {
    return null;
  }
  const parts = payload.split('|');
  if (parts.length !== 3 || parts[0] !== 'cust') return null;
  return parts[1];
}

// Real customers must not be silently logged out by a routine server
// restart the way the founder's own mc_session deliberately is (that
// in-memory-only secret is an accepted single-operator convenience
// tradeoff — see server.js's comment on MISSION_CONTROL_SESSION_SECRET).
// Generates the secret once and persists it locally; every subsequent
// call reads the same value back.
function loadOrCreateSessionSecret(secretPath) {
  try {
    const existing = fs.readFileSync(secretPath, 'utf8').trim();
    if (existing) return existing;
  } catch {
    // File doesn't exist yet (or unreadable) — fall through and create it.
  }
  const secret = crypto.randomBytes(32).toString('hex');
  fs.writeFileSync(secretPath, secret, { encoding: 'utf8', mode: 0o600 });
  return secret;
}

module.exports = {
  timingSafeEqualStrings,
  hashPassword,
  verifyPassword,
  generateAccountId,
  signCustomerSession,
  verifyCustomerSession,
  loadOrCreateSessionSecret,
};

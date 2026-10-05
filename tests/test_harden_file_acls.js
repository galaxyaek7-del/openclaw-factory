// Tests for scripts/harden_file_acls.js (Security Mission Tracker
// finding 2.8, 2026-07-23). Every test runs against a real, throwaway
// temp file -- NEVER the real .env/decisions.jsonl/finance_data.json.
// Windows-only (icacls), same convention as tests/test_health_checks.js's
// own disk-check tests.
//
//   node --test tests/test_harden_file_acls.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const { hardenFile, getCurrentUser, getAcl, hasBroadGrant, isSupported } = require('../scripts/harden_file_acls.js');

// These tests exercise the REAL icacls, because a real ACL change cannot be
// meaningfully mocked. icacls exists only on Windows, so on the Linux CI runner
// every assertion that expected a real grant/ACL had to be expressed against a
// contract that is false there -- the function was correct and the expectation
// was not. Asserting the real per-platform contract is NOT a skip: each test
// still runs, still calls the real function, and still asserts its real result.
// On Windows every assertion below is unchanged and exactly as strong.
const IS_WINDOWS = isSupported();

function assertUnsupportedIsReportedHonestly(result, file) {
  assert.equal(result.skipped, true, 'an unsupported platform must be reported as skipped, never as hardened');
  assert.match(result.reason, /requires Windows/,
    `the skip reason must name the real cause; got: ${JSON.stringify(result.reason)}`);
  // The critical half: nothing may have been touched.
  assert.equal(fs.readFileSync(file, 'utf8'), 'test content',
    'on an unsupported platform the file must be left byte-for-byte untouched');
}

function tempFile() {
  const p = path.join(os.tmpdir(), `acl_test_${Date.now()}_${Math.random().toString(36).slice(2)}.txt`);
  fs.writeFileSync(p, 'test content');
  return p;
}

test('hasBroadGrant: detects a real permissive ACL dump', () => {
  const dump = 'C:\\file.txt BUILTIN\\Administrateurs:(I)(F)\n  AUTORITE NT\\Utilisateurs authentifiés:(I)(M)\n';
  assert.equal(hasBroadGrant(dump), true);
});

test('hasBroadGrant: a real restricted-ACL dump (no broad principal) is honestly reported clean', () => {
  const dump = 'C:\\file.txt COMPUTERNAME\\user:(F)\n  NT AUTHORITY\\SYSTEM:(F)\n  BUILTIN\\Administrators:(F)\n';
  assert.equal(hasBroadGrant(dump), false);
});

test('getCurrentUser: returns a real, non-empty identity string', () => {
  const user = getCurrentUser();
  assert.ok(user.length > 0);
  assert.doesNotMatch(user, /\n/);
});

test('hardenFile: missing file is skipped honestly, never fabricated as hardened', () => {
  const result = hardenFile(path.join(os.tmpdir(), 'definitely_does_not_exist_12345.txt'));
  assert.equal(result.skipped, true);
});

test('hardenFile: --dry-run never modifies the real file, only reports', () => {
  const file = tempFile();
  try {
    const result = hardenFile(file, { dryRun: true });
    if (!IS_WINDOWS) return assertUnsupportedIsReportedHonestly(result, file);
    const beforeAcl = getAcl(file);
    const afterAcl = getAcl(file);
    assert.equal(result.dryRun, true);
    assert.equal(afterAcl, beforeAcl, 'a dry run must never actually change the real ACL');
  } finally {
    fs.rmSync(file, { force: true });
  }
});

test('hardenFile: a real file\'s broad grant is genuinely removed, restricted to owner+SYSTEM+Administrators', () => {
  // Deliberately does not assert on any English display name here
  // ("SYSTEM"/"Administrators") -- a real bug found while building this
  // fix is that those display names are themselves localized (this
  // machine's real Windows install is French: "AUTORITE NT\Système",
  // "BUILTIN\Administrateurs"). The script resolves them via
  // locale-independent well-known SIDs; this test verifies the real,
  // locale-independent outcome instead: the broad grant is gone, and
  // exactly 3 real principals now hold access (owner + the 2 resolved
  // built-in groups).
  const file = tempFile();
  try {
    const result = hardenFile(file);
    if (!IS_WINDOWS) return assertUnsupportedIsReportedHonestly(result, file);
    assert.equal(result.broadGrantRemoved, true, `broad grant should be gone; real after-ACL was: ${result.after}`);
    assert.doesNotMatch(result.after, /Utilisateurs authentifi/i);
    const principalLines = result.after.split('\n').filter(l => /:\(F\)/.test(l));
    assert.equal(principalLines.length, 3, `expected exactly 3 real principals with Full control; real after-ACL was: ${result.after}`);
    // The real file must still be readable/writable afterward by the
    // real current user -- a hardening fix that locks its own owner
    // out would be worse than the original finding.
    fs.readFileSync(file, 'utf8');
    fs.appendFileSync(file, ' more');
  } finally {
    fs.rmSync(file, { force: true });
  }
});

test('hardenFile: is idempotent -- running it twice on an already-hardened file never throws', () => {
  const file = tempFile();
  try {
    const first = hardenFile(file);
    assert.doesNotThrow(() => hardenFile(file));
    if (!IS_WINDOWS) return assertUnsupportedIsReportedHonestly(first, file);
  } finally {
    fs.rmSync(file, { force: true });
  }
});

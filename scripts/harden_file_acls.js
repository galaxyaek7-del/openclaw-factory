// File ACL Hardening (Security Mission Tracker finding 2.8, 2026-07-23).
//
// Real finding: .env/data/decisions.jsonl/finance_data.json carry
// permissive, inherited default Windows ACLs -- readable by the built-in
// Users group, writable by Authenticated Users. Low real risk today
// (single enabled Google/Windows account on this machine, per CLAUDE.md's
// own Identity Architecture note) but no owner-only restriction exists.
//
// Real fix: disables inheritance (`icacls /inheritance:r`) and grants
// Full control to ONLY the real current user + SYSTEM + the built-in
// Administrators group -- removes the broad Users/Authenticated Users
// grants entirely. Windows-only (`icacls`), matching this factory's
// existing Windows-only precedent for OS-level checks
// (lib/health_checks.js's checkDiskSpace()).
//
// Deliberately opt-in and explicit -- nothing in this factory runs this
// automatically. A real filesystem-permission change on files the live
// server depends on every request is exactly the kind of action that
// should never happen silently; a human runs this by hand, reviews the
// real before/after ACL dump it prints, and can re-run --dry-run first.
//
//   node scripts/harden_file_acls.js --dry-run
//   node scripts/harden_file_acls.js
//   node scripts/harden_file_acls.js --files .env,data/decisions.jsonl

const { execFileSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

const REPO_ROOT = path.join(__dirname, '..');
const DEFAULT_TARGETS = ['.env', path.join('data', 'decisions.jsonl'), 'finance_data.json'];

// Real bug found while building this fix: shelling out to `whoami`
// resolves to a DIFFERENT binary depending on which shell launched this
// script -- the real Windows whoami.exe returns "COMPUTERNAME\username"
// (the form icacls needs), but Git Bash/MSYS2's own whoami on PATH
// returns a bare "username" with no domain/computer prefix, which
// icacls then fails to reliably resolve as a security principal (a real
// EPERM-on-delete was observed from a file "hardened" this way, even
// though read/write still worked -- the grant silently only partially
// applied). Fixed by reading the real Windows environment variables
// directly instead of shelling out at all -- USERDOMAIN/COMPUTERNAME
// and USERNAME are real OS-level env vars, inherited identically no
// matter which shell spawned this process.
function getCurrentUser() {
  const domain = process.env.USERDOMAIN || process.env.COMPUTERNAME;
  const username = process.env.USERNAME || os.userInfo().username;
  return domain ? `${domain}\\${username}` : username;
}

function getAcl(filePath) {
  return execFileSync('icacls', [filePath]).toString();
}

// Pure enough to unit-test without touching a real file: given a real
// icacls dump (before or after), reports whether the broad, real-world-
// confirmed-permissive principals (Users, Authenticated Users) still
// hold any grant.
function hasBroadGrant(aclDump) {
  return /\\Users:|Authenticated Users:|Utilisateurs authentifi.s:|BUILTIN\\Utilisateurs:/i.test(aclDump);
}

// Real bug found while building this fix: hardcoding the English
// display names "SYSTEM"/"Administrators" fails on a non-English
// Windows install with "Le mappage entre les noms de compte et les ID
// de sécurité n'a pas été effectué" (this machine is French-localized;
// its real built-in-group display name is "Administrateurs", confirmed
// directly in a real `icacls` dump before this fix). Well-known SIDs
// are locale-independent identifiers for these exact built-in
// principals -- `*S-1-5-18` is always SYSTEM and `*S-1-5-32-544` is
// always the local Administrators group, on every language edition of
// Windows. icacls's own `*SID` syntax resolves them without ever
// needing a localized name at all.
const SYSTEM_SID = '*S-1-5-18';
const ADMINISTRATORS_SID = '*S-1-5-32-544';

function hardenFile(filePath, { dryRun = false, user = null } = {}) {
  if (!fs.existsSync(filePath)) {
    return { file: filePath, skipped: true, reason: 'file does not exist' };
  }
  const before = getAcl(filePath);
  if (dryRun) {
    return { file: filePath, dryRun: true, before, wouldRestrict: hasBroadGrant(before) };
  }

  const currentUser = user || getCurrentUser();
  execFileSync('icacls', [filePath, '/inheritance:r']);
  execFileSync('icacls', [
    filePath,
    '/grant:r', `${currentUser}:F`,
    '/grant:r', `${SYSTEM_SID}:F`,
    '/grant:r', `${ADMINISTRATORS_SID}:F`,
  ]);
  const after = getAcl(filePath);

  return { file: filePath, before, after, broadGrantRemoved: !hasBroadGrant(after) };
}

function main() {
  const args = process.argv.slice(2);
  const dryRun = args.includes('--dry-run');
  const filesIdx = args.indexOf('--files');
  const targets = (filesIdx >= 0 && args[filesIdx + 1] ? args[filesIdx + 1].split(',') : DEFAULT_TARGETS)
    .map(f => (path.isAbsolute(f) ? f : path.join(REPO_ROOT, f)));

  const results = targets.map(f => hardenFile(f, { dryRun }));
  console.log(JSON.stringify(results, null, 2));
}

if (require.main === module) {
  main();
}

module.exports = { hardenFile, getCurrentUser, getAcl, hasBroadGrant, DEFAULT_TARGETS };

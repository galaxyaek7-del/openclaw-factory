// Regression test for the Phase 10 red-team audit's MEDIUM finding:
// scripts/restore_file_from_git.js --apply used to overwrite the target
// file with zero backup of its pre-restore state. Fixed: it now backs up
// the existing file to <path>.pre-restore-backup before overwriting.
//
// Runs the real CLI via subprocess against real, low-risk, git-tracked
// files, restoring them to their own current HEAD. Ground truth for
// "what should the restored content be" is always `git show` itself
// (never a raw disk read), since this checkout has core.autocrlf
// converting LF<->CRLF on checkout — comparing against git's own output
// sidesteps that entirely instead of asserting a byte-for-byte disk
// no-op that this platform's git config doesn't actually guarantee.
// Every real file this test touches is restored via `git checkout --`
// in a finally block, every time, regardless of pass/fail.
//
//   node --test tests/test_restore_file_from_git.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const REPO_ROOT = path.join(__dirname, '..');

function gitShow(ref, target) {
  return execSync(`git show ${ref}:${target}`, { cwd: REPO_ROOT, encoding: 'utf8' });
}

test('restore --apply backs up the pre-restore file before overwriting it', () => {
  const target = 'CLAUDE.md';
  const fullPath = path.join(REPO_ROOT, target);
  const backupPath = `${fullPath}.pre-restore-backup`;
  fs.rmSync(backupPath, { force: true });

  const beforeOnDisk = fs.readFileSync(fullPath, 'utf8');
  const expectedFromGit = gitShow('HEAD', target);

  try {
    const out = execSync(
      `node scripts/restore_file_from_git.js ${target} HEAD --apply --reason "regression test (no-op restore to HEAD)"`,
      { cwd: REPO_ROOT, encoding: 'utf8' }
    );

    assert.match(out, /Pre-restore backup saved to/);
    assert.ok(fs.existsSync(backupPath), 'a pre-restore backup file must exist after --apply');

    const backupContent = fs.readFileSync(backupPath, 'utf8');
    assert.equal(backupContent, beforeOnDisk, 'the backup must be byte-identical to the file as it was immediately before the restore');

    const restoredContent = fs.readFileSync(fullPath, 'utf8');
    assert.equal(restoredContent, expectedFromGit, 'the restored content must match what git show itself returns for that ref');
  } finally {
    fs.rmSync(backupPath, { force: true });
    // Real, always-run cleanup: whatever the restore/backup logic did to
    // CLAUDE.md's on-disk line endings, put the working tree back exactly
    // as git itself considers correct for this checkout.
    execSync('git checkout -- CLAUDE.md', { cwd: REPO_ROOT });
  }
});

test('restore --apply on a target with no existing local file skips the backup step cleanly', () => {
  // requirements.txt: small, tracked, inert. Moved aside (never deleted
  // via git) so the real file is trivially restorable by renaming back,
  // independent of the script under test.
  const target = 'requirements.txt';
  const fullPath = path.join(REPO_ROOT, target);
  const asideCopy = `${fullPath}.test-aside-copy`;
  const backupPath = `${fullPath}.pre-restore-backup`;
  fs.rmSync(asideCopy, { force: true });
  fs.rmSync(backupPath, { force: true });

  const expectedFromGit = gitShow('HEAD', target);
  fs.renameSync(fullPath, asideCopy);
  assert.ok(!fs.existsSync(fullPath), 'precondition: no local file at the target path');

  try {
    const out = execSync(
      `node scripts/restore_file_from_git.js ${target} HEAD --apply --reason "regression test (no prior local file)"`,
      { cwd: REPO_ROOT, encoding: 'utf8' }
    );
    assert.doesNotMatch(out, /Pre-restore backup saved to/, 'no backup should be created when there was nothing to back up');
    assert.ok(!fs.existsSync(backupPath), 'no backup file should exist when the target had no prior local file');
    assert.ok(fs.existsSync(fullPath), 'the file must have been recreated from git');

    const recreated = fs.readFileSync(fullPath, 'utf8');
    assert.equal(recreated, expectedFromGit, 'the recreated file must match what git show itself returns for that ref');
  } finally {
    // Restore the real file exactly, by renaming the untouched original
    // copy back — never relying on the script under test to undo itself.
    fs.rmSync(fullPath, { force: true });
    fs.renameSync(asideCopy, fullPath);
    fs.rmSync(backupPath, { force: true });
  }
});

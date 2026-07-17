// Restore a single file from git history (Phase 10D — Disaster Recovery
// & Business Continuity). Read-only by default — extracts the file's
// content at a given ref into a safe review location, never overwrites
// the real working file unless --apply is passed. Records a real
// recovery action (timestamp/operator/reason/affected systems/result)
// whenever a real restore actually happens.
//
// Covers "Configuration," "Database (if applicable — this factory's
// real equivalent is its git-tracked data/*.jsonl files)," and
// "Documentation" rollback, all via the same one real mechanism: git
// itself already is this factory's version control for every backed-up
// category (see DISASTER_RECOVERY_PLAN.md). Logs/*.log are NOT
// recoverable this way — they are gitignored by design (see the plan).
//
//   node scripts/restore_file_from_git.js <path> <ref>
//     -> writes the ref's version to <path>.restored-from-git for review
//   node scripts/restore_file_from_git.js <path> <ref> --apply --reason "..."
//     -> actually overwrites <path> with the ref's version, records a recovery action

const { execSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { recordRecoveryAction } = require('../lib/recovery_log.js');

const REPO_ROOT = path.join(__dirname, '..');
const [, , targetPath, ref] = process.argv;
const apply = process.argv.includes('--apply');
const reasonIdx = process.argv.indexOf('--reason');
const reason = reasonIdx !== -1 ? process.argv[reasonIdx + 1] : 'manual file restore (no --reason given)';

if (!targetPath || !ref) {
  console.error('usage: node scripts/restore_file_from_git.js <path> <ref> [--apply] [--reason "..."]');
  process.exit(1);
}

try {
  const content = execSync(`git show ${ref}:${targetPath}`, { cwd: REPO_ROOT, encoding: 'utf8' });

  if (!apply) {
    const reviewPath = path.join(REPO_ROOT, `${targetPath}.restored-from-git`);
    fs.mkdirSync(path.dirname(reviewPath), { recursive: true });
    fs.writeFileSync(reviewPath, content);
    console.log(`Extracted ${targetPath}@${ref} to ${reviewPath} for review (real file untouched).`);
    console.log('Re-run with --apply --reason "..." to actually restore it.');
  } else {
    const fullTargetPath = path.join(REPO_ROOT, targetPath);
    // Red-team audit (Phase 10 follow-up) — MEDIUM finding, fixed: this
    // used to overwrite the target with zero backup of its pre-restore
    // state. If the wrong <ref> was given, any uncommitted local drift in
    // that file (plausible for the JSONL files factory_loop.js writes to
    // continuously) was permanently destroyed with no undo. Now backs up
    // the current file first, whenever one exists to back up.
    let backupPath = null;
    if (fs.existsSync(fullTargetPath)) {
      backupPath = `${fullTargetPath}.pre-restore-backup`;
      fs.copyFileSync(fullTargetPath, backupPath);
    }
    fs.writeFileSync(fullTargetPath, content);
    console.log(`Restored ${targetPath} to its state at ${ref}.`);
    if (backupPath) {
      console.log(`Pre-restore backup saved to ${backupPath}`);
    }
    recordRecoveryAction({
      operator: os.userInfo().username,
      reason,
      affectedSystems: [targetPath],
      result: backupPath
        ? `success — restored to ${ref}, pre-restore state backed up to ${path.basename(backupPath)}`
        : `success — restored to ${ref} (no prior file existed to back up)`,
    });
  }
} catch (err) {
  console.error(`Restore failed: ${err.message}`);
  if (apply) {
    recordRecoveryAction({
      operator: os.userInfo().username,
      reason,
      affectedSystems: [targetPath],
      result: `failed — ${err.message}`,
    });
  }
  process.exit(1);
}

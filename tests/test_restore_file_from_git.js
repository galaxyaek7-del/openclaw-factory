// Regression test for the Phase 10 red-team audit's MEDIUM finding:
// scripts/restore_file_from_git.js --apply used to overwrite the target
// file with zero backup of its pre-restore state. Fixed: it now backs up
// the existing file to <path>.pre-restore-backup before overwriting.
//
// 2026-10-29 (backlog B36): this test used to restore CLAUDE.md and
// requirements.txt in the REAL working tree and then `git checkout -- CLAUDE.md`
// -- any uncommitted edit to CLAUDE.md was lost on every run -- and each run
// appended two "regression test" rows to the live data/recovery_actions.jsonl
// (120 found). It now runs the real CLI against a throwaway git repository
// (GF_RESTORE_REPO_ROOT) with the audit records sent to temp files
// (GF_RECOVERY_LOG_PATH, GF_DEPARTMENT_EVENTS_PATH), and also checks that
// record.
//
//   node --test tests/test_restore_file_from_git.js
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execSync, execFileSync } = require('child_process');

const SCRIPT = path.join(__dirname, '..', 'scripts', 'restore_file_from_git.js');

function sandbox() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gf-restore-'));
  const git = (args) => execFileSync('git', args, { cwd: dir, encoding: 'utf8' });
  git(['init', '-q']);
  git(['config', 'user.email', 'test@example.invalid']);
  git(['config', 'user.name', 'restore-test']);
  git(['config', 'core.autocrlf', 'false']);
  fs.writeFileSync(path.join(dir, 'notes.md'), 'committed version\n');
  fs.writeFileSync(path.join(dir, 'req.txt'), 'pinned==1.0\n');
  git(['add', 'notes.md', 'req.txt']);
  git(['commit', '-q', '-m', 'fixture']);
  const env = { ...process.env, GF_RESTORE_REPO_ROOT: dir,
    GF_RECOVERY_LOG_PATH: path.join(dir, 'recovery.jsonl'),
    GF_DEPARTMENT_EVENTS_PATH: path.join(dir, 'department_events.jsonl') };
  const run = (args) => execSync(`node "${SCRIPT}" ${args}`, { cwd: dir, encoding: 'utf8', env });
  const log = () => fs.readFileSync(env.GF_RECOVERY_LOG_PATH, 'utf8').trim().split('\n').map(JSON.parse);
  return { dir, run, log, cleanup: () => fs.rmSync(dir, { recursive: true, force: true }) };
}

test('restore --apply backs up the pre-restore file before overwriting it', () => {
  const s = sandbox();
  try {
    const target = path.join(s.dir, 'notes.md');
    fs.writeFileSync(target, 'local edit not yet committed\n');
    const out = s.run('notes.md HEAD --apply --reason "regression test (restore over a local edit)"');
    assert.match(out, /Pre-restore backup saved to/);
    assert.equal(fs.readFileSync(`${target}.pre-restore-backup`, 'utf8'), 'local edit not yet committed\n');
    assert.equal(fs.readFileSync(target, 'utf8'), 'committed version\n');
    const [rec] = s.log();
    assert.equal(rec.reason, 'regression test (restore over a local edit)');
    assert.deepEqual(rec.affected_systems, ['notes.md']);
    assert.match(rec.result, /^success/);
  } finally {
    s.cleanup();
  }
});

test('restore --apply on a target with no existing local file skips the backup step cleanly', () => {
  const s = sandbox();
  try {
    const target = path.join(s.dir, 'req.txt');
    fs.rmSync(target);
    const out = s.run('req.txt HEAD --apply --reason "regression test (no prior local file)"');
    assert.doesNotMatch(out, /Pre-restore backup saved to/);
    assert.ok(!fs.existsSync(`${target}.pre-restore-backup`));
    assert.equal(fs.readFileSync(target, 'utf8'), 'pinned==1.0\n');
    assert.match(s.log()[0].result, /no prior file existed/);
  } finally {
    s.cleanup();
  }
});

test('without --apply the real file is untouched and nothing is logged', () => {
  const s = sandbox();
  try {
    fs.writeFileSync(path.join(s.dir, 'notes.md'), 'local edit\n');
    s.run('notes.md HEAD');
    assert.equal(fs.readFileSync(path.join(s.dir, 'notes.md'), 'utf8'), 'local edit\n');
    assert.equal(fs.readFileSync(path.join(s.dir, 'notes.md.restored-from-git'), 'utf8'), 'committed version\n');
    assert.ok(!fs.existsSync(path.join(s.dir, 'recovery.jsonl')));
  } finally {
    s.cleanup();
  }
});

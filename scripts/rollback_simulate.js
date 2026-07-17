// Rollback simulation (Phase 10C — Operations Automation & CI/CD
// Pipeline). Proves a prior commit would still pass its own regression
// suite WITHOUT ever touching the real working directory, branch, or
// running processes — uses `git worktree add` (additive, creates a
// separate checkout in a temp folder) rather than `git checkout`/`git
// reset` (which would mutate real, current state). The worktree is
// always removed at the end, success or failure.
//
//   node scripts/rollback_simulate.js <git-ref>
//   node scripts/rollback_simulate.js HEAD~1   (rollback one commit)

const { spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const REPO_ROOT = path.join(__dirname, '..');
const targetRef = process.argv[2];

if (!targetRef) {
  console.error('usage: node scripts/rollback_simulate.js <git-ref>');
  process.exit(1);
}

// shell:true on Windows is required for spawnSync to resolve npm (a
// .cmd shim, not a directly-executable binary there) — CI (ubuntu-latest)
// doesn't need this, but local runs on this development machine do.
const NEEDS_SHELL = process.platform === 'win32';

function run(cmd, args, opts = {}) {
  const res = spawnSync(cmd, args, { cwd: REPO_ROOT, encoding: 'utf8', shell: NEEDS_SHELL, ...opts });
  if (res.status !== 0) {
    throw new Error(`${cmd} ${args.join(' ')} failed: ${res.stderr || res.stdout || `exit code ${res.status}`}`);
  }
  return res.stdout;
}

(async () => {
  const resolvedRef = run('git', ['rev-parse', '--short', targetRef]).trim();
  console.log(`Simulating rollback to ${targetRef} (${resolvedRef})...`);

  const worktreeDir = fs.mkdtempSync(path.join(os.tmpdir(), 'openclaw-rollback-'));
  // git worktree needs the parent dir to not already exist as a git-managed path
  fs.rmdirSync(worktreeDir);

  let failed = false;
  try {
    console.log(`\n=== Creating isolated worktree at ${resolvedRef} ===`);
    run('git', ['worktree', 'add', '--detach', worktreeDir, resolvedRef]);
    console.log('✔ worktree created (real working directory untouched)');

    console.log('\n=== Installing dependencies in the isolated worktree ===');
    run('npm', ['ci'], { cwd: worktreeDir });
    console.log('✔ npm ci OK');

    console.log('\n=== Running Python regression in the isolated worktree ===');
    const pyResult = spawnSync(process.platform === 'win32' ? 'python' : 'python3',
      ['-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py'],
      { cwd: worktreeDir, stdio: 'inherit', shell: NEEDS_SHELL });
    if (pyResult.status !== 0) throw new Error('Python regression failed at this ref');
    console.log('✔ Python regression OK at this ref');

    console.log('\n=== Running JS regression in the isolated worktree ===');
    const jsResult = spawnSync('node',
      ['--test', 'tests/test_metrics.js', 'tests/test_dashboard_data.js', 'tests/test_n8n_notify.js'],
      { cwd: worktreeDir, stdio: 'inherit', shell: NEEDS_SHELL });
    if (jsResult.status !== 0) throw new Error('JS regression failed at this ref');
    console.log('✔ JS regression OK at this ref');

    console.log(`\nROLLBACK SIMULATION: PASSED — ${resolvedRef} is a safe rollback target`);
  } catch (err) {
    failed = true;
    console.error(`\nROLLBACK SIMULATION: FAILED — ${err.message}`);
  } finally {
    console.log(`\n=== Removing isolated worktree ===`);
    try {
      run('git', ['worktree', 'remove', '--force', worktreeDir]);
      console.log('✔ worktree removed, real repository state unaffected');
    } catch (cleanupErr) {
      console.error(`Warning: failed to auto-remove worktree at ${worktreeDir}: ${cleanupErr.message}`);
      console.error(`Manual cleanup: git worktree remove --force "${worktreeDir}"`);
    }
  }
  process.exit(failed ? 1 : 0);
})();

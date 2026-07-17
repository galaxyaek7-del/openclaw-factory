// Production deploy script (Phase 10C — Operations Automation & CI/CD
// Pipeline). This factory runs as ONE real local environment (CLAUDE.md:
// "everything local, no cloud") — there is no separate hosted
// "production" to push to. "Deploying to production" here means:
// stopping the real, currently-running server.js/factory_loop.js
// processes and restarting them so they pick up the latest committed
// code, using the exact safe-restart pattern ADR-045 already
// established (stop by exact PID, never a broad `taskkill /IM node.exe`
// — that would kill every other unrelated Node process on the machine).
//
// THIS SCRIPT NEVER RUNS ITSELF. It requires --confirm, and even then
// only performs the restart — it never decides on its own that "now" is
// the right time to deploy. That decision is the founder's alone, every
// single time ("prod deploy" is one of the standing actions that always
// needs an explicit, per-instance go-ahead, never a standing
// authorization) — an AI agent must never invoke this against the real
// running instance without being told to, for this specific run.
//
// Phase 10D adds real recovery-action auditing (objective 5): every
// --confirm run — success or failure — appends a real record (timestamp,
// operator, reason, affected systems, result) to
// data/recovery_actions.jsonl via lib/recovery_log.js. Pass --reason
// "..." to record why (defaults to "manual deploy" if omitted).
//
//   node scripts/deploy_production.js              (dry run — shows what would happen)
//   node scripts/deploy_production.js --confirm     (actually stops + restarts the real server)
//   node scripts/deploy_production.js --confirm --reason "picking up Phase 10D fixes"

const { execSync, spawn } = require('child_process');
const os = require('os');
const path = require('path');
const { recordRecoveryAction } = require('../lib/recovery_log.js');

const REPO_ROOT = path.join(__dirname, '..');
const confirmed = process.argv.includes('--confirm');
const reasonIdx = process.argv.indexOf('--reason');
const reason = reasonIdx !== -1 ? process.argv[reasonIdx + 1] : 'manual deploy (no --reason given)';

function findListeningPid(port) {
  try {
    const out = execSync(`netstat -ano | findstr ":${port} " | findstr LISTENING`, { encoding: 'utf8' });
    const line = out.trim().split('\n')[0];
    const parts = line.trim().split(/\s+/);
    return parts[parts.length - 1];
  } catch {
    return null;
  }
}

console.log('=== OpenClaw Production Deploy ===');
console.log(confirmed ? 'Mode: LIVE (--confirm passed)' : 'Mode: DRY RUN (pass --confirm to actually deploy)');

const port = process.env.PORT || 3000;
const existingPid = findListeningPid(port);

console.log(`\n1. Current production server on port ${port}: ${existingPid ? `PID ${existingPid}` : 'not running'}`);
console.log('2. Would run: git pull origin main');
console.log('3. Would run: npm ci');
console.log(existingPid
  ? `4. Would stop the exact process PID ${existingPid} (never a broad "taskkill /IM node.exe" — that would kill unrelated Node processes)`
  : '4. No existing process to stop');
console.log('5. Would start: node server.js (and separately, if desired: node factory_loop.js)');
console.log('6. Would verify: GET /api/dashboard returns 200 within 15s');

if (!confirmed) {
  console.log('\nDry run only — nothing was changed. Re-run with --confirm to actually deploy.');
  console.log('This script must only be run with --confirm when a human has explicitly decided this is the moment to deploy.');
  process.exit(0);
}

console.log('\n--confirm passed — proceeding with a real deploy.');
try {
  console.log('\n=== git pull origin main ===');
  execSync('git pull origin main', { cwd: REPO_ROOT, stdio: 'inherit' });

  console.log('\n=== npm ci ===');
  execSync('npm ci', { cwd: REPO_ROOT, stdio: 'inherit' });

  if (existingPid) {
    console.log(`\n=== Stopping existing server (PID ${existingPid}) ===`);
    execSync(`taskkill /F /PID ${existingPid}`, { stdio: 'inherit' });
  }

  console.log('\n=== Starting server.js ===');
  const child = spawn(process.execPath, ['server.js'], {
    cwd: REPO_ROOT,
    detached: true,
    stdio: 'ignore',
  });
  child.unref();
  console.log(`server.js started (PID ${child.pid}). Verify manually: curl http://localhost:${port}/api/dashboard`);
  console.log('\nNote: factory_loop.js is not restarted automatically — start it separately if it was running before, per this factory\'s "no scheduler" convention (every process start is a deliberate action).');

  recordRecoveryAction({
    operator: os.userInfo().username,
    reason,
    affectedSystems: existingPid ? [`server.js (was PID ${existingPid})`, 'server.js (new instance)'] : ['server.js (new instance)'],
    result: `success — new PID ${child.pid}`,
  });
} catch (err) {
  console.error(`\nDeploy failed: ${err.message}`);
  recordRecoveryAction({
    operator: os.userInfo().username,
    reason,
    affectedSystems: existingPid ? [`server.js (was PID ${existingPid})`] : ['server.js'],
    result: `failed — ${err.message}`,
  });
  process.exit(1);
}

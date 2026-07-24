// Daily operational checks (Phase 10C — Operations Automation & CI/CD
// Pipeline). Read-only — never mutates anything. Checks the REAL,
// already-running factory where that's safe to do (only unauthenticated,
// GET-only endpoints: /api/dashboard), plus local file-based checks that
// need no network access at all. Never wired to run on a schedule by
// this session (this factory's "no scheduler" principle, CLAUDE.md) —
// a standalone tool for a human (or the founder's own OS task
// scheduler, their choice) to run when they want a snapshot.
//
//   node scripts/ops_daily_checks.js [base_url]
//   (default base_url: http://localhost:3000 — the real running server)

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const REPO_ROOT = path.join(__dirname, '..');
const baseUrl = process.argv[2] || 'http://localhost:3000';
const results = [];

function report(name, status, detail) {
  results.push({ name, status, detail });
  const icon = { ok: '✔', warn: '⚠', error: '✘' }[status];
  console.log(`${icon} ${name}: ${detail}`);
}

async function checkServerAvailability() {
  try {
    const res = await fetch(`${baseUrl}/api/dashboard`, { signal: AbortSignal.timeout(5000) });
    const contentType = res.headers.get('content-type') || '';
    if (contentType.includes('text/html')) {
      // A real, previously-undetected failure mode: the request reached
      // a live process, but got the SPA fallback (index.html) instead of
      // real JSON — the strongest sign the running process is serving
      // stale code from before this route (or its current routing) was
      // ever loaded, not that the server is actually down.
      return report('Server availability', 'error', `reachable but returned HTML, not JSON — the running process is very likely serving STALE code (see DEPLOYMENT_PIPELINE.md's production deploy procedure)`);
    }
    if (!res.ok) return report('Server availability', 'error', `HTTP ${res.status}`);
    const body = await res.json();
    const status = body.health?.status || 'unknown';
    report('Server availability', status === 'critical' ? 'warn' : 'ok', `reachable, real health status: ${status}`);
  } catch (err) {
    report('Server availability', 'error', `unreachable: ${err.message}`);
  }
}

function checkBackgroundAutomation() {
  const logPath = path.join(REPO_ROOT, 'factory_loop.log');
  if (!fs.existsSync(logPath)) return report('Background automation (factory_loop.js)', 'warn', 'factory_loop.log does not exist — never run, or run from elsewhere');
  const lines = fs.readFileSync(logPath, 'utf8').trim().split('\n').filter(Boolean);
  if (!lines.length) return report('Background automation (factory_loop.js)', 'warn', 'log file is empty');
  try {
    const last = JSON.parse(lines[lines.length - 1]);
    const ageMs = Date.now() - Date.parse(last.timestamp);
    const ageMin = Math.round(ageMs / 60000);
    // Real tick cadence observed all session: ~10 minutes. 30 min is a
    // generous real threshold before flagging as stale, not an arbitrary guess.
    report('Background automation (factory_loop.js)', ageMin > 30 ? 'warn' : 'ok', `last tick ${ageMin} minute(s) ago`);
  } catch {
    report('Background automation (factory_loop.js)', 'error', 'last log line is not valid JSON');
  }
}

function checkDecisionHistory() {
  const p = path.join(REPO_ROOT, 'data', 'decisions.jsonl');
  if (!fs.existsSync(p)) return report('Decision history integrity', 'warn', 'data/decisions.jsonl does not exist yet');
  const lines = fs.readFileSync(p, 'utf8').split('\n').filter(Boolean);
  let corrupt = 0;
  for (const line of lines) {
    try { JSON.parse(line); } catch { corrupt++; }
  }
  report('Decision history integrity', corrupt > 0 ? 'error' : 'ok', `${lines.length} real record(s), ${corrupt} corrupt line(s)`);
}

function checkKnowledgeSync() {
  const brainDir = path.join(REPO_ROOT, 'OpenClaw_Brain');
  const indexFile = path.join(brainDir, 'MASTER_INDEX.md');
  if (!fs.existsSync(brainDir)) return report('Knowledge Base sync', 'error', 'OpenClaw_Brain/ does not exist');
  if (!fs.existsSync(indexFile)) return report('Knowledge Base sync', 'warn', 'MASTER_INDEX.md missing');
  const folderCount = fs.readdirSync(brainDir, { withFileTypes: true }).filter(e => e.isDirectory()).length;
  report('Knowledge Base sync', 'ok', `${folderCount} real section folders present`);
}

function checkBackupVerification() {
  try {
    const status = execSync('git status --porcelain', { cwd: REPO_ROOT, encoding: 'utf8' });
    const uncommittedCount = status.trim().split('\n').filter(Boolean).length;
    execSync('git fetch origin main --quiet', { cwd: REPO_ROOT });
    const ahead = execSync('git rev-list --count origin/main..HEAD', { cwd: REPO_ROOT, encoding: 'utf8' }).trim();
    const behind = execSync('git rev-list --count HEAD..origin/main', { cwd: REPO_ROOT, encoding: 'utf8' }).trim();
    if (uncommittedCount > 0) {
      report('Backup verification (git remote)', 'warn', `${uncommittedCount} uncommitted change(s) not yet backed up to any remote`);
    } else if (ahead !== '0') {
      report('Backup verification (git remote)', 'warn', `${ahead} local commit(s) not yet pushed to origin/main`);
    } else {
      report('Backup verification (git remote)', 'ok', `clean, fully in sync with origin/main${behind !== '0' ? ` (origin is ${behind} ahead — pull recommended)` : ''}`);
    }
  } catch (err) {
    report('Backup verification (git remote)', 'warn', `could not check remote sync: ${err.message}`);
  }
}

function checkStorageUsage() {
  const dirs = ['books', 'data', 'OpenClaw_Brain', 'logs', 'reports'];
  for (const dir of dirs) {
    const full = path.join(REPO_ROOT, dir);
    if (!fs.existsSync(full)) continue;
    let totalBytes = 0;
    const walk = (d) => {
      for (const entry of fs.readdirSync(d, { withFileTypes: true })) {
        const p = path.join(d, entry.name);
        if (entry.isDirectory()) walk(p);
        else totalBytes += fs.statSync(p).size;
      }
    };
    walk(full);
    report(`Storage usage: ${dir}/`, 'ok', `${(totalBytes / 1024 / 1024).toFixed(2)} MB`);
  }
}

(async () => {
  console.log(`=== Galaxy Forge Daily Operational Checks (${new Date().toISOString()}) ===\n`);
  await checkServerAvailability();
  checkBackgroundAutomation();
  checkDecisionHistory();
  checkKnowledgeSync();
  checkBackupVerification();
  checkStorageUsage();

  const errors = results.filter(r => r.status === 'error');
  const warnings = results.filter(r => r.status === 'warn');
  console.log(`\n=== Summary: ${results.length} checks, ${errors.length} error(s), ${warnings.length} warning(s) ===`);
  process.exit(errors.length ? 1 : 0);
})();

// Galaxy Forge — Safe Startup Detection, JS wrapper (Unified Recovery
// System §2, 2026-07-18). Thin shell around recovery/startup_check.py's
// real implementation (stdin/stdout-JSON, same convention as
// mission_control_api.py) — one real decision point, callable from
// factory_loop.js's main() (right after acquireLock()) or standalone.
//
//   echo '{"was_stale_lock": true}' | node scripts/factory_startup_check.js

const { execFileSync } = require('child_process');
const path = require('path');

const REPO_ROOT = path.join(__dirname, '..');

function detectPython() {
  const candidates = ['python3', 'python', 'py'];
  for (const cmd of candidates) {
    try {
      execFileSync(cmd, ['--version'], { stdio: 'ignore' });
      return cmd;
    } catch { /* try next candidate */ }
  }
  return 'python';
}

// Synchronous by design: this runs once, at startup, before the tick
// loop begins — blocking here is correct, there is nothing useful to do
// concurrently with "is it safe to resume yet."
function checkStartupSafety(wasStaleLock) {
  try {
    const pythonPath = detectPython();
    const output = execFileSync(
      pythonPath, ['-m', 'recovery.startup_check'],
      { cwd: REPO_ROOT, input: JSON.stringify({ was_stale_lock: !!wasStaleLock }), encoding: 'utf-8', timeout: 15000 },
    );
    return JSON.parse(output);
  } catch (err) {
    // Fail closed, never crash the caller: an unreadable/unparseable
    // result must be treated as "cannot confirm this is safe," never as
    // "must be fine."
    return { success: false, classification: 'NEEDS_CONFIRMATION', reason: `startup check itself failed: ${err.message}`, current_task: null };
  }
}

module.exports = { checkStartupSafety };

if (require.main === module) {
  const wasStaleLock = process.argv.includes('--stale-lock');
  console.log(JSON.stringify(checkStartupSafety(wasStaleLock)));
}

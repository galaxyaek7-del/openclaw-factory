// Log rotation + cleanup jobs (Phase 10C — Operations Automation &
// CI/CD Pipeline). Defaults to a dry run (report only) — nothing is
// deleted or rotated unless --apply is passed, matching this session's
// standing rule for any destructive action. Standalone, never scheduled
// by this session (this factory's "no scheduler" principle) — a human
// (or the founder's own OS task scheduler, their choice) runs it.
//
//   node scripts/ops_maintenance.js              (dry run — report only)
//   node scripts/ops_maintenance.js --apply      (actually rotate/clean)

const fs = require('fs');
const path = require('path');

const REPO_ROOT = path.join(__dirname, '..');
const apply = process.argv.includes('--apply');

const LOG_ROTATE_THRESHOLD_BYTES = 10 * 1024 * 1024; // 10MB — generous; logs/service_layer.log is 0.05MB today (see ops_daily_checks.js), far below this
const REPORTS_RETENTION_COUNT = 10; // keep the 10 most recent reports/*.md; this session's own reports/ dir is far below this today

console.log(`=== OpenClaw Maintenance (${apply ? 'APPLYING CHANGES' : 'DRY RUN — pass --apply to actually act'}) ===\n`);

function rotateLogIfNeeded() {
  const logPath = path.join(REPO_ROOT, 'logs', 'service_layer.log');
  if (!fs.existsSync(logPath)) return console.log('✔ logs/service_layer.log does not exist yet — nothing to rotate');
  const sizeBytes = fs.statSync(logPath).size;
  if (sizeBytes < LOG_ROTATE_THRESHOLD_BYTES) {
    return console.log(`✔ logs/service_layer.log is ${(sizeBytes / 1024).toFixed(1)}KB — below the ${LOG_ROTATE_THRESHOLD_BYTES / 1024 / 1024}MB rotation threshold, no action needed`);
  }
  const archiveName = `service_layer.${new Date().toISOString().replace(/[:.]/g, '-')}.log`;
  const archivePath = path.join(REPO_ROOT, 'logs', archiveName);
  console.log(`${apply ? 'Rotating' : 'Would rotate'} logs/service_layer.log (${(sizeBytes / 1024 / 1024).toFixed(2)}MB) -> logs/${archiveName}`);
  if (apply) {
    fs.renameSync(logPath, archivePath);
    fs.writeFileSync(logPath, '');
    console.log('✔ rotated');
  }
}

function cleanupOldReports() {
  const reportsDir = path.join(REPO_ROOT, 'reports');
  if (!fs.existsSync(reportsDir)) return console.log('✔ reports/ does not exist — nothing to clean up');
  const files = fs.readdirSync(reportsDir)
    .filter(f => f.endsWith('.md'))
    .map(f => ({ name: f, mtime: fs.statSync(path.join(reportsDir, f)).mtimeMs }))
    .sort((a, b) => b.mtime - a.mtime);
  const toRemove = files.slice(REPORTS_RETENTION_COUNT);
  if (!toRemove.length) {
    return console.log(`✔ reports/ has ${files.length} file(s), within the ${REPORTS_RETENTION_COUNT}-file retention window — no cleanup needed`);
  }
  console.log(`${apply ? 'Removing' : 'Would remove'} ${toRemove.length} report(s) beyond the ${REPORTS_RETENTION_COUNT}-file retention window:`);
  for (const f of toRemove) {
    console.log(`  - ${f.name}`);
    if (apply) fs.unlinkSync(path.join(reportsDir, f.name));
  }
}

rotateLogIfNeeded();
console.log('');
cleanupOldReports();

if (!apply) {
  console.log('\nDry run only — nothing was changed. Re-run with --apply to actually perform the actions above.');
}

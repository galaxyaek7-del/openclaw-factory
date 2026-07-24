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

const LOG_ROTATE_THRESHOLD_BYTES = 10 * 1024 * 1024; // 10MB — generous; every log rotated here is far below this today
const REPORTS_RETENTION_COUNT = 10; // keep the 10 most recent reports/*.md; this session's own reports/ dir is far below this today

// Standing-charter continuous-improvement follow-up (verified via the
// zero-assumption production audit, Section C): this used to rotate only
// logs/service_layer.log. factory_loop.log and inspections.log are real,
// unbounded, growing root-level logs (measured: 535KB/386KB after ~56h of
// continuous operation, ~230KB/day for factory_loop.log alone) that this
// script never covered — a real long-horizon risk for a system meant to
// run "for years with minimal human intervention." Generalized to a
// single parameterized function so every log this factory writes shares
// one rotation implementation, not a second copy per log file.
function rotateLogIfNeeded(logPath, archivePrefix, thresholdBytes = LOG_ROTATE_THRESHOLD_BYTES, apply = false) {
  const relPath = path.relative(REPO_ROOT, logPath);
  if (!fs.existsSync(logPath)) {
    console.log(`✔ ${relPath} does not exist yet — nothing to rotate`);
    return { rotated: false, reason: 'missing' };
  }
  const sizeBytes = fs.statSync(logPath).size;
  if (sizeBytes < thresholdBytes) {
    console.log(`✔ ${relPath} is ${(sizeBytes / 1024).toFixed(1)}KB — below the ${thresholdBytes / 1024 / 1024}MB rotation threshold, no action needed`);
    return { rotated: false, reason: 'below_threshold', sizeBytes };
  }
  const archiveName = `${archivePrefix}.${new Date().toISOString().replace(/[:.]/g, '-')}.log`;
  const archivePath = path.join(path.dirname(logPath), archiveName);
  console.log(`${apply ? 'Rotating' : 'Would rotate'} ${relPath} (${(sizeBytes / 1024 / 1024).toFixed(2)}MB) -> ${path.relative(REPO_ROOT, archivePath)}`);
  if (apply) {
    fs.renameSync(logPath, archivePath);
    fs.writeFileSync(logPath, '');
    console.log('✔ rotated');
  }
  return { rotated: apply, reason: 'over_threshold', sizeBytes, archivePath };
}

function rotateAllKnownLogs(apply = false) {
  return [
    rotateLogIfNeeded(path.join(REPO_ROOT, 'logs', 'service_layer.log'), 'service_layer', LOG_ROTATE_THRESHOLD_BYTES, apply),
    rotateLogIfNeeded(path.join(REPO_ROOT, 'factory_loop.log'), 'factory_loop', LOG_ROTATE_THRESHOLD_BYTES, apply),
    rotateLogIfNeeded(path.join(REPO_ROOT, 'inspections.log'), 'inspections', LOG_ROTATE_THRESHOLD_BYTES, apply),
  ];
}

function cleanupOldReports(apply = false) {
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

module.exports = { rotateLogIfNeeded, rotateAllKnownLogs, cleanupOldReports };

if (require.main === module) {
  const apply = process.argv.includes('--apply');
  console.log(`=== Galaxy Forge Maintenance (${apply ? 'APPLYING CHANGES' : 'DRY RUN — pass --apply to actually act'}) ===\n`);
  rotateAllKnownLogs(apply);
  console.log('');
  cleanupOldReports(apply);
  if (!apply) {
    console.log('\nDry run only — nothing was changed. Re-run with --apply to actually perform the actions above.');
  }
}

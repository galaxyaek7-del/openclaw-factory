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

// REAL INCIDENT, 2026-10-28: this function used to delete every reports/*.md
// beyond the newest 10 — and on a real `--apply` run it removed 591 files, 112
// of them tracked (recovered from git) and ~479 untracked (permanently lost,
// including hand-written deliverables like CYCLE116_BASELINE.md and
// REALITY_LEDGER_2026-07-31.md that were never committed). reports/ is not a
// disposable cache: it holds generated digests *and* authored evidence. Only
// names this factory's own scheduled reports actually generate may ever be
// removed; anything else is never touched, whatever its age.
const GENERATED_REPORT_PATTERNS = [
  /^EXECUTIVE_BRIEF_\d{4}-\d{2}-\d{2}\.md$/,
  /^EVOLUTION_\d{4}-\d{2}-\d{2}\.md$/,
  /^AI_DOCTOR_\d{4}-\d{2}-\d{2}\.md$/,
  /^DEPARTMENT_HEALTH_\d{4}-\d{2}-\d{2}\.md$/,
  /^WEEK_\d{4}-\d{2}-\d{2}\.md$/,
  /^GALAXY_EVOLUTION_\d{4}-\d{2}\.md$/,
  /^ARCHITECTURE_REVIEW_\d{4}-Q[1-4]\.md$/,
  /^ANNUAL_STRATEGIC_REVIEW_\d{4}\.md$/,
  /^executive_report_\d{8}T\d{6}Z\.md$/,
];

function isGeneratedReport(name) {
  return GENERATED_REPORT_PATTERNS.some(re => re.test(name));
}

function cleanupOldReports(apply = false, reportsDir = path.join(REPO_ROOT, 'reports'), retention = REPORTS_RETENTION_COUNT) {
  if (!fs.existsSync(reportsDir)) return console.log('✔ reports/ does not exist — nothing to clean up');
  const all = fs.readdirSync(reportsDir).filter(f => f.endsWith('.md'));
  const files = all
    .filter(isGeneratedReport)
    .map(f => ({ name: f, mtime: fs.statSync(path.join(reportsDir, f)).mtimeMs }))
    .sort((a, b) => b.mtime - a.mtime);
  const toRemove = files.slice(retention);
  const protectedCount = all.length - files.length;
  if (!toRemove.length) {
    return console.log(`✔ reports/ has ${files.length} generated report(s) within the ${REPORTS_RETENTION_COUNT}-file window (${protectedCount} non-generated file(s) never touched) — no cleanup needed`);
  }
  console.log(`${apply ? 'Removing' : 'Would remove'} ${toRemove.length} generated report(s) beyond the ${REPORTS_RETENTION_COUNT}-file window (${protectedCount} non-generated file(s) never touched):`);
  for (const f of toRemove) {
    console.log(`  - ${f.name}`);
    if (apply) fs.unlinkSync(path.join(reportsDir, f.name));
  }
}

module.exports = { rotateLogIfNeeded, rotateAllKnownLogs, cleanupOldReports, isGeneratedReport };

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

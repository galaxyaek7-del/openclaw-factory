// Health Monitor (Enterprise Upgrade Roadmap Phase 1.2, 2026-07-23).
//
// Real finding this closes: lib/health_checks.js's buildHealthReport()
// (finding 4.7, commit f050414) is computed correctly, but only ever
// on-demand -- nothing proactively alerts when a real check goes
// degraded/critical. Combined with scripts/supervisor.js's own real gap
// (closed in this same commit -- see its own comment): a single real
// crash-then-successful-restart was previously silent, only "giving up"
// ever alerted. Together, MTTD (mean time to detect) was genuinely
// unbounded -- a human had to manually notice and hit /health by hand.
//
// Opt-in, exactly like supervisor.js: start with
// `node scripts/health_monitor.js` alongside (not instead of) the real
// server/supervisor process. No scheduler exists in this factory
// (CLAUDE.md) -- this is a real, explicitly-started, long-running
// foreground process, the same honest pattern supervisor.js already
// established, never a hidden background cron job.
//
// Polls the real, already-live GET /health endpoint (server.js's own
// computeHealthStatus()) on a real interval -- the exact same endpoint a
// human would otherwise have to check by hand. Alerts via Telegram
// (lib/telegram_direct.js, ADR-085) ONLY on a real status transition
// (healthy -> degraded/critical/unreachable, or back to healthy) --
// never repeatedly for an unchanged status, the same "no alert spam"
// discipline this session's Live Competitive Intelligence work already
// established for market alerts (ADR-095) and decision reopens
// (ADR-096).
//
//   node scripts/health_monitor.js
//   HEALTH_MONITOR_URL=http://127.0.0.1:3000/health node scripts/health_monitor.js
//   HEALTH_MONITOR_INTERVAL_MS=300000 node scripts/health_monitor.js

const path = require('path');
const fs = require('fs');

const REPO_ROOT = path.join(__dirname, '..');
const LOG_PATH = path.join(REPO_ROOT, 'health_monitor.log');

const HEALTH_URL = process.env.HEALTH_MONITOR_URL || `http://127.0.0.1:${process.env.PORT || 3000}/health`;
const INTERVAL_MS = parseInt(process.env.HEALTH_MONITOR_INTERVAL_MS || String(5 * 60 * 1000), 10);

const STATUS_LABELS = { healthy: 'سليم', warning: 'تحذير', degraded: 'متدهور', critical: 'حرج', unreachable: 'غير قابل للوصول' };
const STATUS_ICONS = { healthy: '✅', warning: '⚠️', degraded: '⚠️', critical: '🚨', unreachable: '📡' };

function log(entry) {
  const line = JSON.stringify({ at: new Date().toISOString(), ...entry });
  console.log(`[health-monitor] ${line}`);
  try {
    fs.appendFileSync(LOG_PATH, line + '\n');
  } catch { /* a failing monitor-log write must never block monitoring itself */ }
}

// Real, deterministic rule: alert whenever the status actually changed
// since the last real poll -- never on an unchanged status, however bad
// (that would be spam, and would tell a human nothing new).
// previousStatus === null means "first poll, nothing to compare against
// yet" -- never alerts on startup alone.
function shouldAlert(previousStatus, currentStatus) {
  return previousStatus !== null && previousStatus !== currentStatus;
}

// Real names only, from the real checks buildHealthReport()/
// computeHealthStatus() already computed -- never a guessed or invented
// reason. not_applicable checks (database/queue/worker_pool -- this
// factory genuinely has none) are correctly excluded, matching the same
// "!null is true" trap lib/health_checks.js's own aggregation already
// guards against.
function extractFailingCheckNames(report) {
  if (!report || !report.checks) return [];
  return Object.entries(report.checks)
    .filter(([, c]) => c && c.severity !== 'not_applicable' && c.ok === false)
    .map(([name]) => name);
}

function buildStatusChangeMessage(currentStatus, previousStatus, failingChecks) {
  const icon = STATUS_ICONS[currentStatus] || '⚠️';
  const lines = [
    `${icon} تغيّر حالة صحة المصنع: ${STATUS_LABELS[currentStatus] || currentStatus}`,
    '',
    `من: ${STATUS_LABELS[previousStatus] || previousStatus || 'غير معروفة'}`,
  ];
  if (failingChecks.length) {
    lines.push('', `فحوصات فاشلة: ${failingChecks.join('، ')}`);
  }
  return lines.join('\n');
}

// A network failure reaching /health at all is itself real, meaningful
// signal (the server is down, or unreachable) -- reported as its own
// honest 'unreachable' status, never silently swallowed as if nothing
// happened.
async function fetchHealth(url = HEALTH_URL, fetchImpl = fetch) {
  try {
    const res = await fetchImpl(url, { signal: AbortSignal.timeout(10000) });
    if (!res.ok) return { status: 'unreachable', checks: {}, error: `HTTP ${res.status}` };
    const body = await res.json();
    return { status: body.status || 'unreachable', checks: body.checks || {}, error: null };
  } catch (err) {
    return { status: 'unreachable', checks: {}, error: err.message };
  }
}

function sendAlert(message) {
  try {
    const telegramDirect = require(path.join(REPO_ROOT, 'lib', 'telegram_direct'));
    return telegramDirect.sendTelegramMessage(message).catch(() => {});
  } catch {
    return Promise.resolve({ sent: false, error: 'telegram_direct module unavailable' });
  }
}

// Data-freshness watchdog (CTO+COO audit closure 2026-08-15, Phase 11):
// the HTTP /health endpoint tells us the server is up, but a factory_loop
// that silently stopped producing fresh artifacts would pass every HTTP
// check while the factory went dormant -- a real, previously-undetected
// MTTD gap (RED_TEAM_REPORT.md). These are the real files factory_loop's
// tick/scheduler writes, each with a max-acceptable staleness:
//   * tick-adjacent files update every ~10min tick
//   * health_snapshots update every tick (per tick() in factory_loop.js)
//   * daily reports have a 26h grace so one missed midnight tick (e.g. a
//     laptop asleep overnight) is reported honestly, not as an alarm.
const FRESHNESS_FILES = [
  { file: 'data/factory_state.json', maxAgeMs: 25 * 60 * 1000 },
  { file: 'data/golden_hunter_events.jsonl', maxAgeMs: 25 * 60 * 1000 },
  { file: 'data/health_snapshots.jsonl', maxAgeMs: 25 * 60 * 1000 },
  { file: 'data/orchestrator_timeline.jsonl', maxAgeMs: 2 * 60 * 60 * 1000 },
  { file: 'data/decisions.jsonl', maxAgeMs: 26 * 60 * 60 * 1000 },
];

function checkFreshness(now = Date.now(), files = FRESHNESS_FILES) {
  return files.map(({ file, maxAgeMs }) => {
    const fullPath = path.join(REPO_ROOT, file);
    let ageMs = null;
    let exists = false;
    try {
      if (fs.existsSync(fullPath)) {
        exists = true;
        const mtime = fs.statSync(fullPath).mtimeMs;
        ageMs = now - mtime;
      }
    } catch { /* stat failure treated as stale-below */ }
    return {
      file,
      exists,
      age_ms: ageMs,
      stale: !exists || (ageMs !== null && ageMs > maxAgeMs),
      max_age_ms: maxAgeMs,
    };
  });
}

function buildStalenessMessage(staleFiles) {
  const lines = [
    '⚠️ بيانات المصنع غير محدَّثة:',
    '',
    ...staleFiles.map((s) => {
      const ageH = s.age_ms === null ? 'غير موجود' : `${Math.round(s.age_ms / 60000)}m`;
      return `• ${s.file} — ${s.exists ? `آخر تحديث منذ ${ageH}` : 'الملف غير موجود'}`;
    }),
  ];
  return lines.join('\n');
}

// previousStatus is passed in and the new status returned (not hidden
// module state) -- keeps this pure and directly testable, the same
// dependency-injection shape lib/health_checks.js's own run/fetchImpl
// parameters already established.
async function tick(previousStatus, { url = HEALTH_URL, fetchImpl = fetch, alertImpl = sendAlert } = {}) {
  const report = await fetchHealth(url, fetchImpl);
  log({ event: 'poll', status: report.status, error: report.error });

  if (shouldAlert(previousStatus, report.status)) {
    const failing = extractFailingCheckNames(report);
    const message = buildStatusChangeMessage(report.status, previousStatus, failing);
    log({ event: 'status_changed', from: previousStatus, to: report.status });
    await alertImpl(message);
  }

  return report.status;
}

// Extends the per-tick check with data-freshness (CTO+COO audit closure
// 2026-08-15): the HTTP endpoint only proves the server is up; a
// factory_loop that silently stopped writing fresh artifacts would pass
// every HTTP check while the factory went dormant -- the real MTTD gap
// RED_TEAM_REPORT.md flagged. Alerts only on a staleness *transition*
// (fresh -> stale, or back), never on an unchanged state -- the same no-
// spam discipline as the HTTP status alerts.
async function tickWithFreshness(previousState, { url = HEALTH_URL, fetchImpl = fetch, alertImpl = sendAlert, now = Date.now(), files = FRESHNESS_FILES } = {}) {
  const status = await tick(previousState.status, { url, fetchImpl, alertImpl });
  const freshness = checkFreshness(now, files);
  const staleFiles = freshness.filter((f) => f.stale);
  const staleNow = staleFiles.length > 0;
  // previousState.stale === null means "first poll, nothing to compare yet" --
  // never alert on startup, exactly like shouldAlert()'s first-poll rule.
  const wasStale = previousState.stale === null ? null : Boolean(previousState.stale);

  if (wasStale !== null && wasStale !== staleNow) {
    const message = staleNow
      ? buildStalenessMessage(staleFiles)
      : '✅ بيانات المصنع عادت للتحديث';
    log({ event: 'freshness_changed', stale: staleNow, files: staleFiles.length });
    await alertImpl(message);
  }

  return { status, stale: staleNow, files: freshness };
}

function start() {
  let lastState = { status: null, stale: null };
  log({ event: 'started', url: HEALTH_URL, interval_ms: INTERVAL_MS });
  const poll = async () => {
    lastState = await tickWithFreshness(lastState);
  };
  poll();
  return setInterval(poll, INTERVAL_MS);
}

if (require.main === module) {
  start();
}

module.exports = {
  shouldAlert, extractFailingCheckNames, buildStatusChangeMessage, fetchHealth, sendAlert,
  checkFreshness, buildStalenessMessage, tick, tickWithFreshness, start,
  HEALTH_URL, INTERVAL_MS, FRESHNESS_FILES,
};

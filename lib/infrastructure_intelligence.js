// Galaxy Forge — Infrastructure Intelligence (Autonomous Digital
// Company v1, Track B1, 2026-07-19).
//
// Real signals only: CPU/memory/disk via Node's built-in `os`/`fs`
// modules (zero new dependency), and a real cost-rate trend computed by
// bucketing the already-real data/ai_cost_log.jsonl (written by
// book_generator.py's _log_ai_cost()) by day, comparing this week's real
// spend against the real trailing average. Groq exposes no queryable
// quota API, so no "quota remaining" field is invented here. Automatic
// recovery is already real (factory_state.py, recovery/) — surfaced by
// the existing recovery-status service, not duplicated here.
//
// Pure file/os reads only, no Express/child_process dependency — same
// "unit-testable without a live server" discipline as lib/dashboard_data.js.

const os = require('os');
const fs = require('fs');
const path = require('path');
const { readJsonlEntries } = require('./jsonl');

const FACTORY_DIR = path.join(__dirname, '..');
const AI_COST_LOG = path.join(FACTORY_DIR, 'data', 'ai_cost_log.jsonl');

const DAY_MS = 24 * 60 * 60 * 1000;

function getSystemResources(factoryDir = FACTORY_DIR) {
  const cpus = os.cpus();
  const totalMem = os.totalmem();
  const freeMem = os.freemem();

  let disk;
  try {
    const stats = fs.statfsSync(factoryDir);
    const totalBytes = stats.blocks * stats.bsize;
    const freeBytes = stats.bfree * stats.bsize;
    disk = {
      total_bytes: totalBytes,
      free_bytes: freeBytes,
      used_pct: totalBytes ? Number((((totalBytes - freeBytes) / totalBytes) * 100).toFixed(1)) : null,
    };
  } catch (err) {
    disk = { error: err.message };
  }

  return {
    cpu: {
      count: cpus.length,
      model: cpus.length ? cpus[0].model : 'unknown',
      // [0,0,0] on Windows -- Node has no per-OS load average API there;
      // reported honestly as-is rather than faked.
      load_avg_1_5_15min: os.loadavg(),
    },
    memory: {
      total_bytes: totalMem,
      free_bytes: freeMem,
      used_pct: totalMem ? Number((((totalMem - freeMem) / totalMem) * 100).toFixed(1)) : null,
    },
    disk,
  };
}

// Buckets real AI cost log entries by calendar day (UTC date of each
// entry's own timestamp), then compares the most recent 7-day window
// against the trailing average of all earlier complete days -- the same
// "real statistical comparison over already-real data" shape as
// factory_loop.js's revenueSince(), just for cost instead of revenue.
function getCostTrend(now = new Date(), logPath = AI_COST_LOG) {
  const entries = readJsonlEntries(logPath);
  if (!entries.length) {
    return {
      total_calls: 0,
      total_cost_usd: 0,
      recent_7d_cost_usd: 0,
      recent_7d_calls: 0,
      trailing_daily_avg_usd: null,
      outlier: false,
      note: 'لا يوجد سجل تكاليف بعد (data/ai_cost_log.jsonl فارغ أو غير موجود) — لا Groq calls مسجَّلة.',
    };
  }

  const nowMs = now.getTime();
  const sinceRecentMs = nowMs - 7 * DAY_MS;

  let totalCost = 0;
  let recentCost = 0;
  let recentCalls = 0;
  const byDay = new Map();

  for (const e of entries) {
    const cost = Number(e.cost_usd) || 0;
    totalCost += cost;
    const t = Date.parse(e.timestamp);
    if (!Number.isFinite(t)) continue;
    if (t >= sinceRecentMs) {
      recentCost += cost;
      recentCalls++;
    }
    const dayKey = new Date(t).toISOString().slice(0, 10);
    byDay.set(dayKey, (byDay.get(dayKey) || 0) + cost);
  }

  const days = [...byDay.keys()].sort();
  const trailingDays = days.filter(d => new Date(`${d}T00:00:00Z`).getTime() < sinceRecentMs);
  const trailingAvg = trailingDays.length
    ? trailingDays.reduce((sum, d) => sum + byDay.get(d), 0) / trailingDays.length
    : null;

  const recentDailyAvg = recentCost / 7;
  // Flag an outlier only when there's a real trailing baseline to compare
  // against (never fabricate a threshold with zero history) and the
  // recent daily average is genuinely more than double it.
  const outlier = trailingAvg !== null && trailingAvg > 0 && recentDailyAvg > trailingAvg * 2;

  return {
    total_calls: entries.length,
    total_cost_usd: Number(totalCost.toFixed(6)),
    recent_7d_cost_usd: Number(recentCost.toFixed(6)),
    recent_7d_calls: recentCalls,
    trailing_daily_avg_usd: trailingAvg !== null ? Number(trailingAvg.toFixed(6)) : null,
    outlier,
    note: trailingAvg === null ? 'لا يوجد تاريخ كافٍ بعد (أقل من أسبوع من البيانات) لحساب متوسط اتجاه موثوق.' : null,
  };
}

function getInfrastructureStatus(now = new Date()) {
  return {
    system: getSystemResources(),
    ai_cost_trend: getCostTrend(now),
  };
}

module.exports = { getSystemResources, getCostTrend, getInfrastructureStatus };

// EOS Phase 1 (2026-07-19): a direct CLI entry point so
// mission_control_api.py's combined executive report can reuse this real
// function via a subprocess call (`node lib/infrastructure_intelligence.js`)
// instead of reimplementing CPU/memory/disk/cost-trend logic in Python a
// second time -- the same "reuse over reimplementation" choice this
// factory always makes across its Python<->JS boundary, just in the other
// direction (every other cross-language call in this repo has JS spawning
// Python; this is the first Python-spawns-JS one, for the same reason).
if (require.main === module) {
  process.stdout.write(JSON.stringify(getInfrastructureStatus()));
}

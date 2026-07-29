// Galaxy Forge — Health Trend Tracking (Global Trust & Resilience Layer,
// Round 1, 2026-07-29): closes the one real gap found in this session's
// own research — lib/health_checks.js's buildHealthReport() (and every
// other health surface: ai_doctor.py, department_health.py) is real but
// purely point-in-time. Nothing anywhere stores health history or
// detects a real trend across readings.
//
// Every real GET /health status factory_loop.js's own tick already
// fetches (diagnose()) gets appended here as one more real, honest data
// point — same append-only JSONL convention as every other ledger in
// this repo (channels/ledger.py's data/sales_ledger.jsonl,
// data/decisions.jsonl). detectHealthDegradation() is a real, disclosed
// mechanical heuristic over real recorded history — never a fabricated
// ML-style prediction. This is NOT a substitute for the real-time
// checks themselves; it is the trend layer they never had.
const fs = require('fs');
const path = require('path');

const DEFAULT_SNAPSHOTS_PATH = path.join(__dirname, '..', 'data', 'health_snapshots.jsonl');
const SEVERITY_RANK = { healthy: 0, degraded: 1, critical: 2 };

function recordHealthSnapshot(status, snapshotsPath = DEFAULT_SNAPSHOTS_PATH, now = new Date()) {
  if (!(status in SEVERITY_RANK)) {
    return { recorded: false, reason: `unrecognized status: ${status}` };
  }
  const entry = { at: now.toISOString(), status };
  fs.mkdirSync(path.dirname(snapshotsPath), { recursive: true });
  fs.appendFileSync(snapshotsPath, JSON.stringify(entry) + '\n');
  return { recorded: true, entry };
}

function readHealthSnapshots(snapshotsPath = DEFAULT_SNAPSHOTS_PATH, limit = 50) {
  if (!fs.existsSync(snapshotsPath)) return [];
  const lines = fs.readFileSync(snapshotsPath, 'utf8').split('\n').filter(Boolean);
  const entries = [];
  for (const line of lines) {
    try {
      entries.push(JSON.parse(line));
    } catch (_) {
      // A corrupt line is skipped, never crashes the read — same
      // discipline as every other JSONL reader in this repo.
    }
  }
  return entries.slice(-limit);
}

// Two real, narrow signals, never blended into one fabricated score:
//  - strictlyWorsening: each of the last `windowSize` real readings is
//    worse than the one before it.
//  - sustainedUnhealthy: every one of the last `windowSize` real readings
//    is not "healthy" (a persistent problem, not necessarily worsening).
// `degrading` is true if either real signal fires.
function detectHealthDegradation(snapshotsPath = DEFAULT_SNAPSHOTS_PATH, windowSize = 3) {
  const recent = readHealthSnapshots(snapshotsPath, windowSize);
  if (recent.length < windowSize) {
    return {
      degrading: false,
      reason: `أقل من ${windowSize} قراءات صحة حقيقية مسجَّلة بعد لحساب اتجاه موثوق`,
      window: recent,
    };
  }

  const statuses = recent.map((e) => e.status);
  const ranks = statuses.map((s) => SEVERITY_RANK[s]);
  if (ranks.some((r) => r === undefined)) {
    return { degrading: false, reason: 'قراءة واحدة أو أكثر في النافذة الأخيرة غير صالحة', window: recent };
  }

  let strictlyWorsening = true;
  for (let i = 1; i < ranks.length; i++) {
    if (ranks[i] <= ranks[i - 1]) { strictlyWorsening = false; break; }
  }
  const sustainedUnhealthy = ranks.every((r) => r > 0);

  let reason;
  if (strictlyWorsening) {
    reason = `${windowSize} قراءات صحة حقيقية متتالية تزداد سوءاً: ${statuses.join(' -> ')}`;
  } else if (sustainedUnhealthy) {
    reason = `${windowSize} قراءات صحة حقيقية متتالية غير سليمة (لم تعد healthy): ${statuses.join(' -> ')}`;
  } else {
    reason = 'لا اتجاه تدهور حقيقي في آخر القراءات';
  }

  return { degrading: strictlyWorsening || sustainedUnhealthy, reason, window: recent };
}

module.exports = {
  recordHealthSnapshot, readHealthSnapshots, detectHealthDegradation,
  SEVERITY_RANK, DEFAULT_SNAPSHOTS_PATH,
};

// OpenClaw Factory — Executive Dashboard data aggregator.
//
// Per ADR-034's explicit-override update (2026-07-15): built by REUSING
// real, already-existing signals — golden_opportunities.json, finance_data.json,
// market_hunter_runs.log, pending_review/, tier1_intake/, NEEDS_ATTENTION.md,
// NEEDS_REVIEW.md — never inventing new metrics with no data behind them.
// Every function here degrades independently (missing file -> honest zero/
// note, never a thrown error) — same discipline as server.js's own
// readTopOpportunities()/readNextDollarActions().
//
// Pure file reads only, no Express/child_process dependency, so this module
// is unit-testable in isolation (see tests/test_dashboard_data.js) without
// needing a live server or a spawned Python process.

const fs = require('fs');
const path = require('path');

const FACTORY_DIR = path.join(__dirname, '..');

function readJsonSafe(filePath) {
  try {
    if (!fs.existsSync(filePath)) return null;
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch (_) {
    return null;
  }
}

function readOracleSummary(jsonPath = path.join(FACTORY_DIR, 'golden_opportunities.json')) {
  const data = readJsonSafe(jsonPath);
  if (!data) {
    return { golden_count: 0, total_scored: 0, top: [], note: 'لم يُشغَّل profit_oracle.py بعد' };
  }
  const results = Array.isArray(data.results) ? data.results : [];
  const golden = results.filter(r => r && r.verdict === 'GOLDEN');
  return {
    generated_at: data.generated_at || null,
    golden_count: golden.length,
    total_scored: results.length,
    top: golden.slice(0, 5),
  };
}

function readHunterSummary(logPath = path.join(FACTORY_DIR, 'market_hunter_runs.log')) {
  try {
    if (!fs.existsSync(logPath)) {
      return { ran: false, note: 'لم يُشغَّل market_hunter.py بعد' };
    }
    const lines = fs.readFileSync(logPath, 'utf8').split('\n').filter(Boolean);
    if (!lines.length) return { ran: false, note: 'السجل فارغ' };
    const last = JSON.parse(lines[lines.length - 1]);
    return {
      ran: true,
      timestamp: last.timestamp,
      scanned_count: last.scanned_count,
      skipped_count: last.skipped_count,
      golden_count: last.golden_count,
    };
  } catch (err) {
    return { ran: false, note: `تعذّرت قراءة السجل: ${err.message}` };
  }
}

function readFinanceSummary(financeFile = path.join(FACTORY_DIR, 'finance_data.json')) {
  const data = readJsonSafe(financeFile);
  if (!data) {
    return { total_sales: 0, total_revenue: 0, by_platform: {}, note: 'لا مبيعات مسجَّلة بعد' };
  }
  const sales = Array.isArray(data.sales) ? data.sales : [];
  return {
    total_sales: sales.length,
    total_revenue: Number(data.totalSales || 0),
    by_platform: {
      KDP: Number(data.totalKDP || 0),
      Etsy: Number(data.totalEtsy || 0),
      Gumroad: Number(data.totalGumroad || 0),
    },
    last_updated: data.lastUpdated || null,
  };
}

function countJsonFiles(dir) {
  try {
    if (!fs.existsSync(dir)) return 0;
    return fs.readdirSync(dir).filter(f => f.toLowerCase().endsWith('.json')).length;
  } catch (_) {
    return 0;
  }
}

function readPendingReviewSummary(baseDir = path.join(FACTORY_DIR, 'pending_review')) {
  return {
    queue: countJsonFiles(path.join(baseDir, 'queue')),
    approved: countJsonFiles(path.join(baseDir, 'approved')),
    completed: countJsonFiles(path.join(baseDir, 'completed')),
    rejected: countJsonFiles(path.join(baseDir, 'rejected')),
  };
}

// STRUCTURAL_DIAGNOSIS.md / ADR-035 / ADR-036: real research batches toward
// the Tier-1 Golden Hunter trigger (ADR-034 §3.2) — honestly reports what
// exists (candidates gathered, none yet accepted) rather than a fabricated
// "Tier 1 pipeline: active" status.
function readTier1IntakeSummary(candidatesDir = path.join(FACTORY_DIR, 'tier1_intake', 'candidates')) {
  try {
    if (!fs.existsSync(candidatesDir)) {
      return { candidates_researched: 0, accepted: 0, note: 'tier1_intake/ غير موجود بعد' };
    }
    const files = fs.readdirSync(candidatesDir).filter(f => f.toLowerCase().endsWith('.json'));
    const candidates = files.map(f => readJsonSafe(path.join(candidatesDir, f))).filter(Boolean);
    const acceptedCount = candidates.filter(c => {
      const post = c.opportunity_score_tier1_POST_FIX || c.opportunity_score_tier1_post_fix;
      return post && post.accepted === true;
    }).length;
    return {
      candidates_researched: candidates.length,
      accepted: acceptedCount,
      note: acceptedCount === 0
        ? 'لا مرشَّح Tier 1 حقيقي مقبول بعد — راجع ADR-035/ADR-036 (البوابة أُصلِحت، لكن التسجيل نفسه لا يزال أعمى أمام إشارة B2B حقيقية)'
        : undefined,
    };
  } catch (err) {
    return { candidates_researched: 0, accepted: 0, note: `error: ${err.message}` };
  }
}

// ADR-043: reads the last real analysis from
// data/market_intelligence_analyses.jsonl (market_intelligence_engine.py's
// append-only history) — never recomputes, just surfaces the latest real
// AI CEO decision + evidence the tool already produced.
function readLatestMarketIntelligence(logPath = path.join(FACTORY_DIR, 'data', 'market_intelligence_analyses.jsonl')) {
  if (!fs.existsSync(logPath)) {
    return { available: false, note: 'لم يُشغَّل market_intelligence_engine.py بعد' };
  }
  try {
    const lines = fs.readFileSync(logPath, 'utf8').split('\n').filter(Boolean);
    if (!lines.length) return { available: false, note: 'السجل فارغ' };
    const last = JSON.parse(lines[lines.length - 1]);
    return { available: true, ...last };
  } catch (err) {
    return { available: false, note: `تعذّرت القراءة: ${err.message}` };
  }
}

// ADR-040: reads config/capability_registry.json — every metric the
// factory has considered building, classified as REAL/ESTIMATED/DISCOVERY.
// Summarizes counts for the Capability Maturity view; never invents a
// capability not already in the registry file.
function readCapabilityMaturity(registryPath = path.join(FACTORY_DIR, 'config', 'capability_registry.json')) {
  const data = readJsonSafe(registryPath);
  if (!data || !Array.isArray(data.capabilities)) {
    return { real: 0, estimated: 0, discovery: 0, total: 0, capabilities: [], note: 'capability_registry.json غير موجود بعد' };
  }
  const caps = data.capabilities;
  const byLevel = (level) => caps.filter(c => c.level === level);
  return {
    real: byLevel('REAL').length,
    estimated: byLevel('ESTIMATED').length,
    discovery: byLevel('DISCOVERY').length,
    total: caps.length,
    last_updated: data.last_updated || null,
    capabilities: caps,
  };
}

// Phase 11 (Business Activation): Mission Control was asked to display
// "products created" and "production throughput" — neither existed as a
// real metric anywhere (audited directly, not assumed). Both are derived
// here from books/_generation_log.jsonl, which book_generator.py's
// _log_generation() already appends to unconditionally on every real
// generation attempt, success or failure — reused, not reinvented.
// `passed_quality_review` is deliberately NOT called "published" — that
// word is reserved for health.reality's channel-distribution truth
// (currently 0); this field means "Dual Inspection let it through",
// a distinct, earlier stage.
function readProductionInventorySummary(logPath = path.join(FACTORY_DIR, 'books', '_generation_log.jsonl')) {
  const entries = readJsonlTail(logPath, Infinity);
  if (!entries.length) {
    return {
      total_attempts: 0, created: 0, failed: 0, passed_quality_review: 0,
      last_7_days: 0, last_updated: null,
      note: fs.existsSync(logPath) ? 'السجل فارغ' : 'لم يُولَّد أي منتج بعد',
    };
  }
  const sevenDaysAgoMs = Date.now() - 7 * 24 * 60 * 60 * 1000;
  let created = 0, failed = 0, passedQuality = 0, last7 = 0;
  let lastUpdated = null;
  for (const e of entries) {
    if (e.success) created++; else failed++;
    if (e.published === true) passedQuality++;
    if (e.timestamp) {
      const t = Date.parse(e.timestamp);
      if (Number.isFinite(t)) {
        if (t >= sevenDaysAgoMs) last7++;
        if (!lastUpdated || t > Date.parse(lastUpdated)) lastUpdated = e.timestamp;
      }
    }
  }
  return {
    total_attempts: entries.length,
    created,
    failed,
    passed_quality_review: passedQuality,
    last_7_days: last7,
    last_updated: lastUpdated,
  };
}

// Standing charter follow-up — verified live: decisions.jsonl is a real,
// growing, append-only file (10.8MB / 1,344 lines today) and this function
// re-reads and re-parses the ENTIRE thing on every single call. Measured
// directly: 282ms alone, the dominant cost in computeDashboard()'s total
// ~350ms — a real, self-inflicted regression from this same Phase 11
// addition, only visible once GET /api/dashboard's OTHER costs
// (runReality()'s Python spawn, self_awareness.js's redundant self-fetch)
// were fixed and this one became the new bottleneck. Cached by file mtime,
// not a TTL: correct by construction (invalidates the instant the file
// actually changes, e.g. a new decision appended by a real tick) rather
// than serving anything stale within an arbitrary window, and costs
// nothing extra when the file hasn't changed (a stat call, not a re-read).
// Keyed by logPath so this stays safe for tests that pass their own temp
// file paths — never collides with the real default path's cache entry.
const _decisionQueueCache = new Map(); // logPath -> { mtimeMs, result }

function readDecisionQueueSummary(logPath = path.join(FACTORY_DIR, 'data', 'decisions.jsonl')) {
  let mtimeMs = null;
  try {
    mtimeMs = fs.statSync(logPath).mtimeMs;
  } catch (_) {
    mtimeMs = null; // file doesn't exist — fall through to the real read below, which handles that honestly
  }
  const cached = _decisionQueueCache.get(logPath);
  if (mtimeMs !== null && cached && cached.mtimeMs === mtimeMs) {
    return cached.result;
  }

  const result = _readDecisionQueueSummaryUncached(logPath);
  if (mtimeMs !== null) {
    _decisionQueueCache.set(logPath, { mtimeMs, result });
  } else {
    _decisionQueueCache.delete(logPath);
  }
  return result;
}

// Phase 11: "opportunities waiting" — read directly from
// data/decisions.jsonl (decision_engine's own real, append-only record),
// same reuse pattern as readLatestMarketIntelligence() above. DEFERRED is
// the real "waiting for a future decision cycle" bucket; ACCEPTED is the
// (today, honestly, usually zero) "ready to produce" bucket — reported
// separately so neither number gets silently conflated with the other.
function _readDecisionQueueSummaryUncached(logPath) {
  const entries = readJsonlTail(logPath, Infinity);
  if (!entries.length) {
    return {
      accepted: 0, deferred: 0, rejected: 0, other: 0, total: 0,
      note: fs.existsSync(logPath) ? 'السجل فارغ' : 'لم يُشغَّل decision_engine بعد',
    };
  }
  const counts = { accepted: 0, deferred: 0, rejected: 0, other: 0 };
  for (const e of entries) {
    const status = String(e.status || '').toUpperCase();
    if (status === 'ACCEPTED' || status === 'BUILD') counts.accepted++;
    else if (status === 'DEFERRED' || status === 'WAIT' || status === 'IMPROVE') counts.deferred++;
    else if (status === 'REJECTED' || status === 'PIVOT') counts.rejected++;
    else counts.other++;
  }
  return { ...counts, total: entries.length };
}

// Phase 11: "failed jobs" — server.js's own ACTION_JOBS map tracks async
// action failures but is in-memory only (lost on every restart, not a
// persisted history — confirmed by reading server.js directly). This
// reuses factory_loop.log instead: every real tick already records each
// step's outcome, including a real, persisted `action: "failed"` marker
// (checked live: 9 real failures across 392 historical ticks) — no new
// logging mechanism invented.
function readFailedJobsSummary(logPath = path.join(FACTORY_DIR, 'factory_loop.log'), limit = 500) {
  const ticks = readJsonlTail(logPath, limit);
  if (!ticks.length) {
    return { failed_count: 0, recent: [], note: fs.existsSync(logPath) ? 'السجل فارغ' : 'factory_loop.js لم يُشغَّل بعد' };
  }
  const failures = [];
  for (const tick of ticks) {
    const ts = tick.timestamp || (tick.diagnosis && tick.diagnosis.timestamp);
    for (const a of (tick.actions || [])) {
      if (a.action === 'failed') failures.push({ timestamp: ts, step: a.step, detail: a.detail });
    }
  }
  return {
    failed_count: failures.length,
    recent: failures.slice(-5).reverse(),
  };
}

function readAttentionFlag(filePath = path.join(FACTORY_DIR, 'NEEDS_ATTENTION.md')) {
  if (!fs.existsSync(filePath)) return { active: false };
  try {
    return { active: true, content: fs.readFileSync(filePath, 'utf8') };
  } catch (_) {
    return { active: true };
  }
}

function readReviewFlag(filePath = path.join(FACTORY_DIR, 'NEEDS_REVIEW.md')) {
  if (!fs.existsSync(filePath)) return { active: false };
  try {
    return { active: true, content: fs.readFileSync(filePath, 'utf8') };
  } catch (_) {
    return { active: true };
  }
}

function readJsonlTail(filePath, limit) {
  if (!fs.existsSync(filePath)) return [];
  try {
    const lines = fs.readFileSync(filePath, 'utf8').split('\n').filter(Boolean);
    return lines.slice(-limit).map(line => {
      try { return JSON.parse(line); } catch (_) { return null; }
    }).filter(Boolean);
  } catch (_) {
    return [];
  }
}

// Real activity timeline — merges factory_loop.js's own tick log,
// inspectors.py's Dual Inspection log, and the Golden Hunter Bridge's event
// log into one honest, timestamp-sorted feed. No event is invented: every
// row here is a line that already existed in one of these three files
// before this function ever read them.
function readActivityTimeline({ limit = 20, factoryLoopLog = path.join(FACTORY_DIR, 'factory_loop.log'),
  inspectionsLog = path.join(FACTORY_DIR, 'inspections.log'),
  goldenHunterEvents = path.join(FACTORY_DIR, 'data', 'golden_hunter_events.jsonl') } = {}) {
  const events = [];

  for (const tick of readJsonlTail(factoryLoopLog, 30)) {
    const ts = tick.timestamp || (tick.diagnosis && tick.diagnosis.timestamp);
    const realActions = (tick.actions || []).filter(a => a.action && a.action !== 'none');
    events.push({
      timestamp: ts,
      source: 'factory_loop',
      summary: realActions.length
        ? realActions.map(a => `${a.step}: ${a.action}`).join('، ')
        : 'تِكّة روتينية — لا فعل جديد',
    });
  }

  for (const insp of readJsonlTail(inspectionsLog, 30)) {
    events.push({
      timestamp: insp.timestamp,
      source: 'inspection',
      summary: `${insp.title || insp.niche || '—'}: ${insp.passed ? 'مقبول' : 'مرفوض'} (profit_score ${insp.commercial ? insp.commercial.profit_score : '—'})`,
    });
  }

  for (const ev of readJsonlTail(goldenHunterEvents, 30)) {
    if (ev.action === 'skipped' && (ev.reason === 'already_attempted')) continue; // pure noise, not a real event
    events.push({
      timestamp: ev.timestamp,
      source: 'golden_hunter',
      summary: ev.detail || `${ev.action}${ev.niche ? ': ' + ev.niche : ''}`,
    });
  }

  return events
    .filter(e => e.timestamp)
    .sort((a, b) => Date.parse(b.timestamp) - Date.parse(a.timestamp))
    .slice(0, limit);
}

// Transparent risk derivation from signals already computed elsewhere — no
// new data source, just a single honest label summarizing what health/
// needs_attention already say. "reuse before creating" (2026-07-15
// directive): this is exactly why health/needsAttention are parameters,
// not recomputed here.
function deriveRiskLevel(health, needsAttention) {
  const status = health && health.status;
  if (status === 'critical') return { level: 'critical', reason: 'health.status = critical' };
  if (needsAttention && needsAttention.active) return { level: 'high', reason: 'NEEDS_ATTENTION.md active' };
  if (status === 'degraded') return { level: 'medium', reason: 'health.status = degraded' };
  if (status === 'healthy') return { level: 'low', reason: 'health.status = healthy' };
  return { level: 'unknown', reason: 'health status unavailable' };
}

// Composes every real signal above into one view. `health`, `awareness`,
// and `priorities` are passed in (computed by server.js's own
// computeHealthStatus()/self_awareness.assessSelfAwareness()/
// readNextDollarActions() — all already exist and are reused, not
// reimplemented, per "reuse before creating") so this module stays free of
// server.js's Express/child_process dependencies and fully unit-testable.
function computeDashboard({ health = null, awareness = null, priorities = null } = {}) {
  const needsAttention = readAttentionFlag();
  return {
    generated_at: new Date().toISOString(),
    health,
    risk: deriveRiskLevel(health, needsAttention),
    current_priorities: priorities,
    self_awareness: awareness ? {
      verdict: awareness.verdict,
      growth: awareness.growth,
      weakest_cell: awareness.diagnosis ? awareness.diagnosis.weakest_cell : null,
    } : null,
    finance: readFinanceSummary(),
    oracle: readOracleSummary(),
    hunter: readHunterSummary(),
    tier1_discovery: readTier1IntakeSummary(),
    pending_review: readPendingReviewSummary(),
    needs_attention: needsAttention,
    needs_review: readReviewFlag(),
    activity: readActivityTimeline({}),
    capability_maturity: readCapabilityMaturity(),
    latest_market_intelligence: readLatestMarketIntelligence(),
    production_inventory: readProductionInventorySummary(),
    decision_queue: readDecisionQueueSummary(),
    failed_jobs: readFailedJobsSummary(),
  };
}

module.exports = {
  computeDashboard,
  readOracleSummary,
  readHunterSummary,
  readFinanceSummary,
  readPendingReviewSummary,
  readTier1IntakeSummary,
  readAttentionFlag,
  readReviewFlag,
  readActivityTimeline,
  deriveRiskLevel,
  readCapabilityMaturity,
  readLatestMarketIntelligence,
  readProductionInventorySummary,
  readDecisionQueueSummary,
  readFailedJobsSummary,
};

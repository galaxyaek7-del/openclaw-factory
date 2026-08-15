#!/usr/bin/env node
/**
 * Galaxy Forge — Self-Healing Loop (Task [8])
 *
 * Runs as its OWN process, separate from server.js, so a bug here can never
 * crash the dashboard (Constitution §7: Self-Healing / never terminate the
 * whole factory). It talks to the dashboard only over HTTP (/health,
 * /generate-book) and reads factory files directly on disk.
 *
 * Usage:
 *   node factory_loop.js                     # runs forever, one tick every 10 minutes
 *   node factory_loop.js --once              # runs a single tick and exits (testing)
 *   node factory_loop.js --weekly-report      # force-generate this week's report now
 *   node factory_loop.js --weekly-report --force  # ...and overwrite if already generated today
 *
 * Every Sunday (any tick that lands on a Sunday), if this week's report
 * doesn't exist yet, a weekly report is generated to:
 *   reports/WEEK_YYYY-MM-DD.md   (dated archive)
 *   FACTORY_WEEKLY_REPORT.md     (always-current copy of the latest report)
 * and a summary row is appended to FACTORY_STATUS.md.
 */

const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawn, execSync, execFileSync } = require('child_process');
const selfAwareness = require('./self_awareness');
const n8nNotify = require('./lib/n8n_notify');
const telegramDirect = require('./lib/telegram_direct');
const departmentEvents = require('./lib/department_events');
const {
  notifyN8nProductionEvent, buildGoldenHunterNotifyPayload,
  buildFactoryStoppedUnexpectedlyPayload, buildFactoryRecoveredPayload,
  buildRetryQueueStatusPayload,
  buildPendingReviewNeededPayload, buildNewSaleDetectedPayload,
} = n8nNotify;
const factoryState = require('./lib/factory_state');
const healthTrend = require('./lib/health_trend');
const { checkStartupSafety } = require('./scripts/factory_startup_check');

const FACTORY_DIR = __dirname;
const DASHBOARD_URL = process.env.DASHBOARD_URL || 'http://localhost:3000';
// Enterprise Security & Cyber Defense Mission, Phase 2, finding 2.1
// (2026-07-23): server.js's /api/distribute, /api/sales/poll, and
// /generate-book now require either a real Mission Control session (this
// process has none) or this shared secret, read from the same .env file
// server.js itself reads — same trust model as MISSION_CONTROL_PASSWORD,
// a single shared credential for a single-operator factory's own
// internal automation, not a fake per-service identity system.
const INTERNAL_SERVICE_TOKEN = process.env.INTERNAL_SERVICE_TOKEN;
function internalAuthHeaders() {
  return INTERNAL_SERVICE_TOKEN ? { 'X-Internal-Token': INTERNAL_SERVICE_TOKEN } : {};
}
// ADR-065 Step 3(a): separate from server.js's N8N_PRODUCTION_WEBHOOK_URL
// (a different, already-documented payload contract) — unset by default,
// same fail-safe-if-unconfigured discipline as that one. Points at the
// prepared n8n_workflows/04_Telegram_Notify.prepared.json workflow once the
// founder imports/activates it (n8n_workflows/README.md has the exact
// manual steps — a Telegram bot token is an external credential this
// factory cannot create for itself).
const N8N_TELEGRAM_WEBHOOK_URL = process.env.N8N_TELEGRAM_WEBHOOK_URL || null;
const INTERVAL_MS = 10 * 60 * 1000; // 10 minutes

const LOOP_LOG = path.join(FACTORY_DIR, 'factory_loop.log');
const SCOUT_LOG = path.join(FACTORY_DIR, 'scout_runs.log');
const FINANCE_FILE = path.join(FACTORY_DIR, 'finance_data.json');
const BOOKS_DIR = path.join(FACTORY_DIR, 'books');
const GENERATION_LOG_FILE = path.join(BOOKS_DIR, '_generation_log.jsonl');
const GOLDEN_JSON_FILE = path.join(FACTORY_DIR, 'golden_opportunities.json');
const GOLDEN_HUNTER_EVENTS_FILE = path.join(FACTORY_DIR, 'data', 'golden_hunter_events.jsonl');
const GOLDEN_FRESHNESS_MS = 24 * 60 * 60 * 1000; // ADR-009: >24h old = stale, skip without failing
const NEEDS_ATTENTION_FILE = path.join(FACTORY_DIR, 'NEEDS_ATTENTION.md');
const ATTENTION_STREAK_THRESHOLD = 3; // consecutive occurrences before flagging

// Real live publishing from the automatic loop requires BOTH this env var
// AND a platform secret (e.g. GUMROAD_ACCESS_TOKEN) — channels/gumroad_arm.py
// enforces the token check independently, so setting this alone can never
// push anything live. Absent (the default): every automatic distribution
// attempt stays dry_run, no exceptions (OCTOPUS_ARCHITECTURE.md §10.4/ADR-6).
const LIVE_PUBLISH_ENABLED = process.env.FACTORY_LIVE_PUBLISH === 'true';

// Real automatic production from a Golden Hunter discovery requires this
// separate, explicit flag — unset (the default) means the bridge always
// picks the top opportunity and RECORDS what it would produce, but never
// spends a real Groq call. ADR-009: not set anywhere in this repo/.env.
const AUTO_PRODUCE_ENABLED = process.env.FACTORY_AUTO_PRODUCE === 'true';
const REPORTS_DIR = path.join(FACTORY_DIR, 'reports');
const WEEKLY_REPORT_STABLE = path.join(FACTORY_DIR, 'FACTORY_WEEKLY_REPORT.md');
const OPPORTUNITIES_FILE = path.join(FACTORY_DIR, 'OPPORTUNITIES.md');
const FACTORY_STATUS_FILE = path.join(FACTORY_DIR, 'FACTORY_STATUS.md');
const MARKET_HUNTER_LOG = path.join(FACTORY_DIR, 'market_hunter_runs.log');
const REJECTED_NICHES_FILE = path.join(FACTORY_DIR, 'REJECTED_NICHES.md');
const WEEK_MS = 7 * 24 * 60 * 60 * 1000;
const REJECTION_COOLDOWN_MS = WEEK_MS;

// ── PID LOCKFILE GUARD ──
// Two factory_loop.js instances were found running concurrently (audit
// task), ticking in near-lockstep and double-writing every log/state file
// and racing on triggerGenerateBook(). This guard refuses a second startup
// while a live instance already holds the lock. Acquired only from main()
// — i.e. only when this file is executed directly (`node factory_loop.js`)
// — never as a side effect of `require('./factory_loop')`, so importing
// this module's exported functions for reuse/testing stays side-effect-free.
const LOCK_FILE = path.join(FACTORY_DIR, '.factory_loop.lock');

function isPidAlive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch (err) {
    return false;
  }
}

// lockFile/exitFn are parameterized (defaulting to the real values) purely
// so tests can exercise this against an isolated temp file and a fake exit
// function — never the real, currently-running factory's own lock file.
//
// Return value (Unified Recovery System §2, 2026-07-18): true iff a stale
// lock (dead PID) was reclaimed — the real, concrete "did the previous
// instance die uncleanly" signal the new startup safety check needs.
// false for a clean create or a blocked-exit path. Purely additive — no
// existing caller reads this return value, so this changes no behavior.
function acquireLock(lockFile = LOCK_FILE, exitFn = process.exit) {
  // Red-team audit (Phase 10 follow-up) — MEDIUM finding, fixed: the old
  // version did existsSync -> read -> isPidAlive -> writeFileSync as four
  // separate calls, not one atomic operation, so two instances starting in
  // the same narrow window could both see "no live lock" and both write —
  // exactly the failure this guard exists to prevent (see comment above).
  // { flag: 'wx' } makes the common case (no lock file yet) a single
  // atomic exclusive-create: the OS itself guarantees only one process can
  // win it, no check-then-act gap.
  try {
    fs.writeFileSync(lockFile, String(process.pid), { flag: 'wx' });
    return false;
  } catch (err) {
    if (err.code !== 'EEXIST') {
      console.error('[factory_loop] lockfile check failed, continuing without guard:', err.message);
      return false;
    }
  }
  // A lock file already exists — check whether its owner is still alive.
  try {
    const existingPid = parseInt(fs.readFileSync(lockFile, 'utf8').trim(), 10);
    if (Number.isFinite(existingPid) && isPidAlive(existingPid)) {
      console.log(`[factory_loop] another factory_loop running (PID ${existingPid}), exiting`);
      exitFn(0);
      return false;
    }
    // Zero-assumption audit follow-up — Medium finding, fixed: this used to
    // reclaim a stale lock with a plain writeFileSync, three separate calls
    // (read -> isPidAlive -> write) after the common-path fix above only
    // closed the "no lock file yet" race, not this one. Two processes
    // starting right after a crash (stale lock still present) could both
    // pass the dead-PID check above and both believe they'd reclaimed it.
    // Fixed with unlink-then-exclusive-create: the OS guarantees only one
    // caller can ever successfully unlink the SAME directory entry — a
    // second caller's unlink throws ENOENT, which is treated as "someone
    // else already reclaimed it," not a collision to paper over.
    try {
      fs.unlinkSync(lockFile);
    } catch (unlinkErr) {
      if (unlinkErr.code === 'ENOENT') {
        console.log('[factory_loop] another factory_loop already reclaimed the stale lock, exiting');
        exitFn(0);
        return false;
      }
      throw unlinkErr;
    }
    fs.writeFileSync(lockFile, String(process.pid), { flag: 'wx' });
    return true;
  } catch (err) {
    // Disk full, permissions, etc. — never let the lockfile itself block
    // startup; worst case this run just isn't guarded against a duplicate.
    console.error('[factory_loop] lockfile check failed, continuing without guard:', err.message);
    return false;
  }
}

function releaseLock(lockFile = LOCK_FILE) {
  try {
    fs.unlinkSync(lockFile);
  } catch (err) {
    // Nothing safe left to do on cleanup — file may already be gone, or may
    // belong to a newer process that reclaimed a stale lock after us.
  }
}

function appendLoopLog(entry) {
  try {
    fs.appendFileSync(LOOP_LOG, JSON.stringify({ timestamp: new Date().toISOString(), ...entry }) + '\n');
  } catch (err) {
    // If we can't even log, there's nothing safe left to do but say so on
    // stderr — this must never throw back into the caller.
    console.error('[factory_loop] failed to write factory_loop.log:', err.message);
  }
}

// ── CIRCUIT BREAKER (Anti-Fragility / Digital Sanitation) ──
// Root cause of the retry-storm this fixes: book_generator.py's
// generate_book() can return success:true (the PDF really was written) while
// still setting published:false (CONSTITUTION.md §17, Dual Inspection,
// blocked it). server.js's /generate-book handler used to drop `published`/
// `inspection` from its response entirely, so this loop had no way to tell
// a quarantined book from a real success — it just saw success:true and,
// finding no matching file on disk next tick (title/theme drift, re-runs,
// etc.), tried the exact same rejected niche again. Every 10 minutes.
// Every failure now becomes durable knowledge in REJECTED_NICHES.md instead.
function summarizeInspectionFailure(inspection) {
  if (!inspection) return 'سبب غير معروف (لا بيانات فحص مُرفَقة)';
  const failures = [
    ...((inspection.technical && inspection.technical.failures) || []),
    ...((inspection.commercial && inspection.commercial.failures) || []),
  ];
  return failures.length ? failures.join('؛ ') : 'رُفض دون سبب مُفصَّل';
}

function recordRejectedNiche(niche, title, reason) {
  const now = new Date();
  const entry = [
    `## 🚫 ${now.toISOString()}`,
    `**النيتش:** ${niche || ''}`,
    `**العنوان:** ${title || ''}`,
    `**السبب:** ${reason}`,
    '',
  ].join('\n') + '\n';
  try {
    if (!fs.existsSync(REJECTED_NICHES_FILE)) {
      fs.writeFileSync(REJECTED_NICHES_FILE,
        '# 🚫 Rejected Niches — ذاكرة قاطع الدائرة (Circuit Breaker)\n\n' +
        'نيتشات فشلت في اجتياز الفحص المزدوج (Dual Inspection, CONSTITUTION.md §17) — ' +
        'تُحفَظ هنا كي لا يُعاد توليدها ويُهدَر استدعاء Groq عليها قبل انتهاء فترة التهدئة ' +
        '(7 أيام). Anti-Fragility: كل فشل هنا معرفة دائمة، لا مجرد خطأ منسي.\n\n');
    }
    fs.appendFileSync(REJECTED_NICHES_FILE, entry);
  } catch (err) {
    console.error('[factory_loop] failed to write REJECTED_NICHES.md:', err.message);
  }
}

function readRejectedNiches() {
  if (!fs.existsSync(REJECTED_NICHES_FILE)) return [];
  const text = fs.readFileSync(REJECTED_NICHES_FILE, 'utf8');
  const blocks = text.split(/^## /m).slice(1); // drop the file header before the first entry
  const entries = [];
  for (const block of blocks) {
    const tsMatch = block.match(/^🚫\s*(\S+)/);
    const nicheMatch = block.match(/\*\*النيتش:\*\*\s*(.+)/);
    const reasonMatch = block.match(/\*\*السبب:\*\*\s*(.+)/);
    if (tsMatch && nicheMatch) {
      entries.push({
        timestamp: tsMatch[1],
        niche: nicheMatch[1].trim(),
        reason: reasonMatch ? reasonMatch[1].trim() : '',
      });
    }
  }
  return entries;
}

// Returns null if the niche is clear to try, or {reason, rejectedAt,
// retryAfter} if a cooldown from a past rejection is still active. The
// cooldown window is recomputed from `now` each call (not stored per-entry)
// so a single constant (REJECTION_COOLDOWN_MS) stays the one source of truth.
function isNicheRejected(niche, now = new Date()) {
  if (!niche) return null;
  const nicheLower = niche.trim().toLowerCase();
  const cutoffMs = now.getTime() - REJECTION_COOLDOWN_MS;
  const matches = readRejectedNiches().filter(e => e.niche.trim().toLowerCase() === nicheLower);
  if (!matches.length) return null;
  const latest = matches.reduce((a, b) => (Date.parse(a.timestamp) > Date.parse(b.timestamp) ? a : b));
  const rejectedMs = Date.parse(latest.timestamp);
  if (!Number.isFinite(rejectedMs) || rejectedMs < cutoffMs) return null; // cooldown expired
  return {
    reason: latest.reason,
    rejectedAt: latest.timestamp,
    retryAfter: new Date(rejectedMs + REJECTION_COOLDOWN_MS).toISOString(),
  };
}

// A real AbortController-based timeout — unlike a bare Promise.race, this
// actually cancels the underlying HTTP request instead of just abandoning it
// to keep running in the background after we stop waiting for it.
async function fetchWithTimeout(url, options, ms, label) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  try {
    return await fetch(url, { ...(options || {}), signal: controller.signal });
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error(`${label} timed out after ${ms}ms`);
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

// ── DIAGNOSE ──
async function diagnose() {
  try {
    const res = await fetchWithTimeout(`${DASHBOARD_URL}/health`, {}, 5000, 'health');
    const health = await res.json();
    return { reachable: true, health };
  } catch (err) {
    return { reachable: false, error: err.message };
  }
}

function readScoutLog() {
  if (!fs.existsSync(SCOUT_LOG)) return [];
  const lines = fs.readFileSync(SCOUT_LOG, 'utf8').split('\n').filter(Boolean);
  const entries = [];
  for (const line of lines) {
    try { entries.push(JSON.parse(line)); } catch (_) { /* skip a malformed line, don't fail the read */ }
  }
  return entries;
}

function countBooks() {
  if (!fs.existsSync(BOOKS_DIR)) return 0;
  return fs.readdirSync(BOOKS_DIR).filter(f => f.toLowerCase().endsWith('.pdf')).length;
}

// The last line of books/_generation_log.jsonl is the exact record
// book_generator.py's generate_book() wrote for the request that just
// completed (schemas/product.py's Product.from_jsonl_record() bridges
// this same record into a Product) — _log_generation() is called
// synchronously right before generate_book() returns, so by the time
// /generate-book's HTTP response reaches us, the record is already on disk.
function readLastGenerationRecord(logPath = GENERATION_LOG_FILE) {
  if (!fs.existsSync(logPath)) return null;
  const lines = fs.readFileSync(logPath, 'utf8').split('\n').filter(Boolean);
  if (!lines.length) return null;
  try {
    return JSON.parse(lines[lines.length - 1]);
  } catch (_) {
    return null;
  }
}

function formatDistributionAction(distribution) {
  return { action: distribution.ok ? 'distributed' : 'failed', detail: distribution.detail };
}

// Calls the distribution backbone (distributor.py, via server.js's
// POST /api/distribute) for one already-generated, already-inspected
// record. dry_run stays true unless a human has explicitly set
// FACTORY_LIVE_PUBLISH=true — and even then, channels/gumroad_arm.py
// independently refuses to push live without GUMROAD_ACCESS_TOKEN. Every
// attempt (dry-run or live, success or failure) is recorded to
// data/sales_ledger.jsonl by distributor.py itself, regardless of the
// outcome here.
async function triggerDistribute(record) {
  try {
    const res = await fetchWithTimeout(`${DASHBOARD_URL}/api/distribute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...internalAuthHeaders() },
      body: JSON.stringify({ record, dry_run: !LIVE_PUBLISH_ENABLED }),
    }, 140000, 'api-distribute');
    const data = await res.json();

    if (!data.success) {
      return { ok: false, dry_run: null, detail: `فشل التوزيع: ${data.error}`, outcomes: null };
    }

    const outcomes = data.outcomes || [];
    const summary = outcomes.length
      ? outcomes.map(o => {
          if (!o.attempted) return `${o.arm}: تخطّي (${o.skip_reason})`;
          const r = o.result;
          return `${o.arm}: ${r.ok ? 'نجاح' : 'فشل'}${r.dry_run ? ' [dry-run]' : ' [حي]'}${r.error ? ' — ' + r.error : ''}`;
        }).join('؛ ')
      : 'لا أذرع مسجَّلة';

    return { ok: true, dry_run: data.dry_run, detail: summary, outcomes };
  } catch (err) {
    return { ok: false, dry_run: null, detail: `فشل الاتصال بـ /api/distribute: ${err.message}`, outcomes: null };
  }
}

// ── SALES POLL (ADR-016) ──
// Calls POST /api/sales/poll (scripts/poll_sales.py) every tick so a real
// Gumroad sale is recorded to data/sales_ledger.jsonl without a human ever
// running --sales by hand. Fails safe exactly like triggerDistribute: no
// GUMROAD_ACCESS_TOKEN means channels/gumroad_arm.py's get_sales() reports
// a skip_reason, never a crash, and this function turns that into a normal
// "none" tick action, not a "failed" one.
async function pollSales(reachable) {
  if (!reachable) {
    return { action: 'skipped', detail: 'السيرفر غير متاح — تخطي استطلاع المبيعات هذه الدورة' };
  }
  try {
    const res = await fetchWithTimeout(`${DASHBOARD_URL}/api/sales/poll`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...internalAuthHeaders() },
      body: JSON.stringify({}),
    }, 30000, 'api-sales-poll');
    const data = await res.json();

    if (!data.success) {
      return { action: 'failed', detail: `فشل استطلاع المبيعات: ${data.error}` };
    }

    const outcomes = data.outcomes || [];
    const summary = outcomes.length
      ? outcomes.map(o => {
          if (o.skip_reason) return `${o.arm}: تخطّي (${o.skip_reason})`;
          if (o.error) return `${o.arm}: خطأ (${o.error})`;
          return `${o.arm}: ${o.new_sales} مبيعة جديدة`;
        }).join('؛ ')
      : 'لا أذرع مسجَّلة';

    const totalNewSales = data.total_new_sales || 0;
    if (totalNewSales > 0) {
      // Fire-and-forget, same discipline as every other n8n notify call —
      // a Telegram hiccup must never affect the real, already-recorded sale.
      notifyFactoryRecoveryEvent(buildNewSaleDetectedPayload(outcomes, totalNewSales)).catch(() => {});
    }

    return {
      action: totalNewSales > 0 ? 'found_sales' : 'none',
      detail: `استطلاع المبيعات: ${summary}`,
    };
  } catch (err) {
    return { action: 'failed', detail: `فشل الاتصال بـ /api/sales/poll: ${err.message}` };
  }
}

async function triggerGenerateBook(brief) {
  try {
    const res = await fetchWithTimeout(`${DASHBOARD_URL}/generate-book`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...internalAuthHeaders() },
      body: JSON.stringify({
        title: brief.title,
        topic: brief.topic,
        chapters: brief.chapters,
        audience: brief.audience,
        price: brief.price,
        // ADR-071: forwards product_type:"techdoc" through to server.js's
        // /generate-book when briefFromGoldenOpportunity() built a ladder-
        // tagged brief — undefined for every other brief (JSON.stringify
        // drops it), so this is a no-op for every existing caller.
        ...(brief.product_type ? { product_type: brief.product_type } : {}),
      }),
    }, 150000, 'generate-book');
    const data = await res.json();

    // success:true + published:false means Dual Inspection quarantined it
    // (CONSTITUTION.md §17) — a real, distinct outcome from a plain failure.
    // NOTE: the actual REJECTED_NICHES.md write now happens inside
    // book_generator.py's generate_book() itself (CONSTITUTION.md §19/§20
    // fix — every caller of /generate-book, including Scout, shares that
    // one recording point now). Recording it AGAIN here would double-write
    // the same rejection every time hunt() calls this endpoint — this stays
    // read-only: just recognizing the outcome to report it correctly.
    if (data.success && data.published === false) {
      const reason = summarizeInspectionFailure(data.inspection);
      return { ok: false, rejected: true, detail: `تم التوليد لكن رُفض النشر (Dual Inspection): ${reason}` };
    }

    if (!data.success) {
      return { ok: false, detail: `فشل التوليد: ${data.error}` };
    }

    // data.success && data.published === true from here on: BOTH inspectors
    // passed (CONSTITUTION.md §17 — Technical/QA + Commercial Auditor). No
    // human step from here — hand the fresh record straight to the
    // distributor automatically (Publishing Council, OCTOPUS_ARCHITECTURE.md).
    const result = { ok: true, detail: `تم توليد الكتاب: ${data.filename} (${data.pages} صفحة)` };
    const record = readLastGenerationRecord();
    if (!record || record.file !== data.filename) {
      result.distribution = {
        ok: false, dry_run: null, outcomes: null,
        detail: 'تعذّر مطابقة سجل التوليد الأخير في books/_generation_log.jsonl — تخطّي التوزيع الآلي هذه المرة',
      };
    } else {
      result.distribution = await triggerDistribute(record);
    }
    return result;
  } catch (err) {
    return { ok: false, detail: `فشل الاتصال بـ /generate-book: ${err.message}` };
  }
}

// ── GOLDEN HUNTER BRIDGE (ADR-009) ──
// Connects market_hunter.py/profit_oracle.py's daily output
// (golden_opportunities.json) to actual production — the gap identified in
// AUTOMATION_GAPS_REPORT.md §1: discovery ran automatically but nothing
// ever consumed it. This bridge is read-only toward Golden Hunter itself —
// it never imports or calls market_hunter.py/profit_oracle.py, only reads
// their already-written output file.

function appendGoldenHunterEvent(fields, logPath = GOLDEN_HUNTER_EVENTS_FILE, departmentEventsLogPath = departmentEvents.DEFAULT_LOG_PATH) {
  try {
    fs.mkdirSync(path.dirname(logPath), { recursive: true });
    const record = { timestamp: new Date().toISOString(), ...fields };
    fs.appendFileSync(logPath, JSON.stringify(record) + '\n');
    // EOS Phase 2, Round 2 (2026-07-19): also emits a real correlation-
    // index entry -- envelope only (no business data duplicated), same
    // call site as the real write above, never a re-derivation scan.
    // Best-effort: a department_events write failure must never affect
    // the real golden_hunter_events.jsonl record just written.
    try {
      departmentEvents.emit({
        department: 'golden_hunter', event_type: `golden_hunter.${fields.action || 'event'}`,
        ref_id: fields.niche || null, source_log: 'data/golden_hunter_events.jsonl',
        summary: fields.detail || fields.action || '',
      }, departmentEventsLogPath);
    } catch (_) { /* best effort, never blocks the real event log */ }
    return record;
  } catch (err) {
    // Logging failure must never break the tick itself.
    console.error('[factory_loop] failed to write golden_hunter_events.jsonl:', err.message);
    return { ...fields, _logFailed: true };
  }
}

function readGoldenHunterEvents(logPath = GOLDEN_HUNTER_EVENTS_FILE) {
  if (!fs.existsSync(logPath)) return [];
  const lines = fs.readFileSync(logPath, 'utf8').split('\n').filter(Boolean);
  const events = [];
  for (const line of lines) {
    try { events.push(JSON.parse(line)); } catch (_) { /* skip a malformed line */ }
  }
  return events;
}

function normalizeNiche(niche) {
  return String(niche || '').trim().toLowerCase();
}

// Only a real (dry_run:false) prior attempt blocks retrying the same niche
// — a dry-run "would have produced X" entry is informational only and must
// never permanently block the real attempt once FACTORY_AUTO_PRODUCE is
// eventually enabled.
function goldenNicheAlreadyAttempted(niche, logPath = GOLDEN_HUNTER_EVENTS_FILE) {
  const target = normalizeNiche(niche);
  if (!target) return false;
  return readGoldenHunterEvents(logPath).some(
    e => e.action === 'attempted' && e.dry_run === false && normalizeNiche(e.niche) === target
  );
}

function readGoldenOpportunities(jsonPath = GOLDEN_JSON_FILE) {
  if (!fs.existsSync(jsonPath)) return null;
  try {
    return JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
  } catch (_) {
    return null;
  }
}

// Highest profit_score among non-SKIP verdicts only — a niche profit_oracle
// itself flagged SKIP (<60) is never auto-produced, matching the same
// quality bar a human reviewing GOLDEN_OPPORTUNITIES.md would apply.
function pickTopGoldenOpportunity(data) {
  const results = Array.isArray(data && data.results) ? data.results : [];
  const eligible = results.filter(r => r && r.verdict && r.verdict !== 'SKIP' && typeof r.profit_score === 'number');
  if (!eligible.length) return null;

  // ADR-070: ladder-accepted opportunities (profit_oracle.
  // ladder_opportunity_score(), the Strategic Production Priority Ladder
  // gate, ADR-066) always outrank plain profit_score-ranked ones — the
  // whole point of the ladder pivot is that a lower-profit_score AI SaaS/
  // B2B opportunity should still win over a higher-profit_score KDP one
  // (real, confirmed case: an AI SaaS niche scored profit_score 69 under
  // the old scorer, an old KDP printable scored 71 — without this, the
  // KDP one would still win). Entries without ladder info (every pre-
  // ladder golden_opportunities.json, and every existing test's synthetic
  // fixture) fall through to the exact prior behavior, unchanged.
  const ladderAccepted = eligible.filter(r => r.ladder_accepted === true);
  if (ladderAccepted.length) {
    return ladderAccepted.reduce((best, r) => (r.ladder_score > best.ladder_score ? r : best));
  }
  return eligible.reduce((best, r) => (r.profit_score > best.profit_score ? r : best));
}

const MIN_BUTTER_PRICE = 30; // CONSTITUTION.md §16 — last-resort fallback only, mirrors profit_oracle.py's own MIN_BUTTER_PRICE

// ADR-010: calls the REAL, existing profit_oracle.butter_price(niche) —
// the single constitutional source of truth for CONSTITUTION.md §16's $30
// floor — via a purely additive `--butter-price` CLI flag on
// profit_oracle.py. golden_opportunities.json's recommended_price
// (score_opportunity()'s _score_margin() keyword-tier estimate) is NOT
// butter-compliant and can land below $30 (observed for real: $19 for
// "مخطط شهري قابل للطباعة العودة للمدارس", 2026-07-11) — so it is never
// used directly as a production price.
function getButterPrice(niche, { timeoutMs = 15000, scriptPath = path.join(FACTORY_DIR, 'profit_oracle.py'), pythonPath } = {}) {
  return new Promise((resolve) => {
    let python;
    try {
      python = spawn(pythonPath || detectPythonForHunter(), [scriptPath, '--butter-price'], { cwd: FACTORY_DIR });
    } catch (err) {
      resolve({ ok: false, error: `تعذّر تشغيل profit_oracle.py: ${err.message}` });
      return;
    }

    let output = '', errOut = '', settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };
    const timer = setTimeout(() => {
      try { python.kill(); } catch (_) { /* best effort */ }
      finish({ ok: false, error: 'انتهت مهلة profit_oracle.py --butter-price (15 ثانية)' });
    }, timeoutMs);

    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', (err) => finish({ ok: false, error: err.message }));
    python.on('close', () => {
      try {
        const result = JSON.parse(output.trim());
        if (result.success && Number.isFinite(result.butter_price)) {
          finish({ ok: true, price: result.butter_price });
        } else {
          finish({ ok: false, error: result.error || `ناتج غير متوقع: ${output}${errOut}` });
        }
      } catch (e) {
        finish({ ok: false, error: `Parse error: ${output}${errOut}` });
      }
    });

    try {
      python.stdin.write(JSON.stringify({ niche }));
      python.stdin.end();
    } catch (err) {
      finish({ ok: false, error: err.message });
    }
  });
}

// ADR-026 (ELITE_ASSET_DOCTRINE.md §4): same spawn pattern as
// getButterPrice() above, calling profit_oracle.py's new
// --opportunity-score flag. Golden Hunter's market_hunter.py searches for
// KDP-book-shaped signals only (ELITE_ASSET_DOCTRINE.md §5's honest
// finding — not redirected to Tier 1/2 yet), so every opportunity from
// this bridge is scored as "tier4" here, never guessed at a higher tier.
function getOpportunityScore(niche, { timeoutMs = 15000, scriptPath = path.join(FACTORY_DIR, 'profit_oracle.py'), pythonPath, tier = 'tier4' } = {}) {
  return new Promise((resolve) => {
    let python;
    try {
      python = spawn(pythonPath || detectPythonForHunter(), [scriptPath, '--opportunity-score'], { cwd: FACTORY_DIR });
    } catch (err) {
      resolve({ ok: false, error: `تعذّر تشغيل profit_oracle.py: ${err.message}` });
      return;
    }

    let output = '', errOut = '', settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };
    const timer = setTimeout(() => {
      try { python.kill(); } catch (_) { /* best effort */ }
      finish({ ok: false, error: 'انتهت مهلة profit_oracle.py --opportunity-score (15 ثانية)' });
    }, timeoutMs);

    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', (err) => finish({ ok: false, error: err.message }));
    python.on('close', () => {
      try {
        const result = JSON.parse(output.trim());
        if (result.success && Number.isFinite(result.opportunity_score)) {
          finish({ ok: true, score: result.opportunity_score, accepted: result.accepted, reason: result.reason, components: result.components });
        } else {
          finish({ ok: false, error: result.error || `ناتج غير متوقع: ${output}${errOut}` });
        }
      } catch (e) {
        finish({ ok: false, error: `Parse error: ${output}${errOut}` });
      }
    });

    try {
      python.stdin.write(JSON.stringify({ niche, tier }));
      python.stdin.end();
    } catch (err) {
      finish({ ok: false, error: err.message });
    }
  });
}

// ADR-070 (mission follow-up, 2026-07-17): same spawn pattern as
// getOpportunityScore() above, calling profit_oracle.py's --ladder-score
// flag (profit_oracle.ladder_opportunity_score(), ADR-066) instead of
// --opportunity-score. Returns the exact same {ok, score, accepted,
// reason, components} shape so every downstream caller in huntGolden()
// (skip-detail logging, notifyGoldenHunterAccepted()) works identically
// regardless of which gate produced the result.
function getLadderOpportunityScore(niche, ladder, { timeoutMs = 15000, scriptPath = path.join(FACTORY_DIR, 'profit_oracle.py'), pythonPath, evidencePath, externalSignal, competitorDbFile } = {}) {
  return new Promise((resolve) => {
    let python;
    try {
      python = spawn(pythonPath || detectPythonForHunter(), [scriptPath, '--ladder-score'], { cwd: FACTORY_DIR });
    } catch (err) {
      resolve({ ok: false, error: `تعذّر تشغيل profit_oracle.py: ${err.message}` });
      return;
    }

    let output = '', errOut = '', settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };
    const timer = setTimeout(() => {
      try { python.kill(); } catch (_) { /* best effort */ }
      finish({ ok: false, error: 'انتهت مهلة profit_oracle.py --ladder-score (15 ثانية)' });
    }, timeoutMs);

    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', (err) => finish({ ok: false, error: err.message }));
    python.on('close', () => {
      try {
        const result = JSON.parse(output.trim());
        if (result.success && Number.isFinite(result.ladder_score)) {
          // ADR-073: price threaded through too — a Telegram notification's
          // "key numbers" (mission follow-up, 2026-07-18) means both the
          // score and the real ladder-band price, not score alone.
          finish({ ok: true, score: result.ladder_score, price: result.price, accepted: result.accepted, reason: result.reason, components: result.components });
        } else {
          finish({ ok: false, error: result.error || `ناتج غير متوقع: ${output}${errOut}` });
        }
      } catch (e) {
        finish({ ok: false, error: `Parse error: ${output}${errOut}` });
      }
    });

    try {
      // evidencePath (Proof of Payment doctrine, ADR-121) / externalSignal
      // (Strategic Doctrine v2, ADR-122, real customer-pain evidence a
      // caller already computed via analyze_customer_pain() elsewhere) /
      // competitorDbFile (GALAXY FORGE PRODUCT STRATEGY, ADR-126): test
      // isolation / explicit real evidence passthrough only -- a real
      // automatic-tick caller never sets any of these, so profit_oracle.py
      // falls back to its real defaults (real ledger, no pain evidence,
      // real shared competitor database) exactly as before these
      // parameters existed.
      python.stdin.write(JSON.stringify({ niche, ladder, evidence_path: evidencePath, external_signal: externalSignal, competitor_db_file: competitorDbFile }));
      python.stdin.end();
    } catch (err) {
      finish({ ok: false, error: err.message });
    }
  });
}

// Autonomous Digital Company v1 follow-up (2026-07-19): "data flows, not
// isolated modules" — executive_intelligence's real per-engine success-
// rate detection (ADR-052) now actually gates a real business decision
// (whether to dispatch a new production run this cycle) via profit_oracle.
// py's new --production-health-gate flag, instead of only ever appearing
// in a standalone daily report. Same spawn pattern as getLadderOpportunity
// Score() above; needs no stdin (checks real, factory-wide history, not a
// per-niche input). Fails OPEN on a spawn/parse error, same discipline as
// every other gate in this file — never block production because this
// NEWER check itself failed to run.
function checkProductionEngineHealth({ timeoutMs = 15000, scriptPath = path.join(FACTORY_DIR, 'profit_oracle.py'), pythonPath } = {}) {
  return new Promise((resolve) => {
    let python;
    try {
      python = spawn(pythonPath || detectPythonForHunter(), [scriptPath, '--production-health-gate'], { cwd: FACTORY_DIR });
    } catch (err) {
      resolve({ ok: true, reason: `تعذّر تشغيل بوابة صحة الإنتاج (فشل فتح فشل) — لا حظر: ${err.message}` });
      return;
    }

    let output = '', errOut = '', settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };
    const timer = setTimeout(() => {
      try { python.kill(); } catch (_) { /* best effort */ }
      finish({ ok: true, reason: 'انتهت مهلة بوابة صحة الإنتاج (15 ثانية) — لا حظر (فشل فتح)' });
    }, timeoutMs);

    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', (err) => finish({ ok: true, reason: `خطأ بوابة صحة الإنتاج — لا حظر (فشل فتح): ${err.message}` }));
    python.on('close', () => {
      try {
        const result = JSON.parse(output.trim());
        if (result.success) {
          finish({ ok: result.ok, reason: result.reason, engine_health: result.engine_health });
        } else {
          finish({ ok: true, reason: `بوابة صحة الإنتاج أبلغت عن فشل — لا حظر (فشل فتح): ${result.error || output}${errOut}` });
        }
      } catch (e) {
        finish({ ok: true, reason: `فشل تحليل ناتج بوابة صحة الإنتاج — لا حظر (فشل فتح): ${e.message}` });
      }
    });
  });
}

// ADR-065 Step 3(a): fire-and-forget real notification the moment a real
// opportunity clears profit_oracle's acceptance gate — reuses
// lib/n8n_notify.js's generic sender (same one server.js's production
// pipeline already uses), never a second HTTP implementation. Deliberately
// never awaited by its caller (huntGolden()) and never throws: a
// notification is observability, not part of the production decision
// itself — it must never be able to delay or fail a real tick.
async function notifyGoldenHunterAccepted(niche, opportunityScore) {
  try {
    const payload = buildGoldenHunterNotifyPayload(niche, opportunityScore);
    return await notifyN8nProductionEvent(payload, {
      webhookUrl: N8N_TELEGRAM_WEBHOOK_URL,
      envVarName: 'N8N_TELEGRAM_WEBHOOK_URL',
      log: (entry) => appendGoldenHunterEvent({ action: 'n8n_notify', niche, ...entry }),
    });
  } catch (err) {
    return { attempted: false, error: err.message };
  }
}

// Unified Recovery System §4 (2026-07-18): the same fire-and-forget,
// never-throws pattern as notifyGoldenHunterAccepted() above, reused for
// the factory's own stopped/recovered events rather than a second
// notify implementation.
async function notifyFactoryRecoveryEvent(payload) {
  try {
    return await notifyN8nProductionEvent(payload, {
      webhookUrl: N8N_TELEGRAM_WEBHOOK_URL,
      envVarName: 'N8N_TELEGRAM_WEBHOOK_URL',
      log: (entry) => appendLoopLog({ diagnosis: { status: 'recovery_notify' }, actions: [{ step: 'recovery_notify', ...entry }] }),
    });
  } catch (err) {
    return { attempted: false, error: err.message };
  }
}

// Builds a /generate-book-compatible brief straight from a scored
// opportunity — bypasses Scout's free-association Groq prompt entirely,
// since the niche is already real, tested data from profit_oracle.py, not
// something to re-invent. The price is NOT taken from opportunity.
// recommended_price directly (see getButterPrice() above) — it always goes
// through butter_price(), with a fail-safe floor-clamp if that call itself
// fails for any reason (never silently use an unchecked, possibly
// sub-floor, raw price).
async function briefFromGoldenOpportunity(opportunity, butterOpts = {}) {
  // ADR-071 (mission follow-up, 2026-07-18): a ladder-tagged opportunity
  // (Strategic Production Priority Ladder, MASTER_CHARTER.md §2) already
  // carries its own real, ladder-band price — ladder_price, computed by
  // profit_oracle.ladder_opportunity_score() via butter_price()'s elite/
  // premium bands (ADR-066). Using getButterPrice()'s default "book" band
  // below would silently reprice a $388 AI SaaS opportunity down into
  // KDP's $30-100 book band. Routes to book_generator.
  // generate_product_package() (product_type: "techdoc") via server.js's
  // /generate-book instead of the AI-generated-book path — early return,
  // the rest of this function (getButterPrice()-based book pricing) is
  // completely unchanged for every non-ladder opportunity.
  if (opportunity.ladder && Number.isFinite(opportunity.ladder_price)) {
    return {
      title: opportunity.niche,
      topic: opportunity.niche,
      audience: 'القارئ العام',
      price: opportunity.ladder_price,
      product_type: 'techdoc',
      _raw_recommended_price: opportunity.ladder_price,
      _price_source: 'ladder_price',
      _butter_price_error: null,
    };
  }

  const rawMatch = /([0-9]+(\.[0-9]+)?)/.exec(opportunity.recommended_price || '');
  const rawPrice = rawMatch ? parseFloat(rawMatch[1]) : null;

  const butter = await getButterPrice(opportunity.niche, butterOpts);
  let price, priceSource;
  if (butter.ok) {
    price = butter.price;
    priceSource = 'butter_price';
  } else {
    price = Math.max(rawPrice !== null ? rawPrice : MIN_BUTTER_PRICE, MIN_BUTTER_PRICE);
    priceSource = 'fallback_floor_clamped';
  }

  return {
    title: opportunity.niche,
    topic: opportunity.niche,
    audience: 'القارئ العام',
    price,
    chapters: 8,
    _raw_recommended_price: rawPrice,
    _price_source: priceSource,
    _butter_price_error: butter.ok ? null : butter.error,
  };
}

// Pure decision logic (data + "now" in, a verdict out) — separated from
// huntGolden() specifically so it's unit-testable with fabricated data,
// without ever reading/writing the real golden_opportunities.json.
function evaluateGoldenOpportunities(data, nowMs = Date.now()) {
  if (!data) {
    return { ok: false, reason: 'missing_or_unreadable', detail: 'golden_opportunities.json غير موجود أو غير قابل للقراءة — تخطٍّ بلا فشل' };
  }

  const generatedAtMs = Date.parse(data.generated_at);
  if (!Number.isFinite(generatedAtMs)) {
    return { ok: false, reason: 'invalid_timestamp', detail: 'generated_at غير صالح في golden_opportunities.json' };
  }

  const ageMs = nowMs - generatedAtMs;
  if (ageMs > GOLDEN_FRESHNESS_MS) {
    const ageHours = Math.round(ageMs / (60 * 60 * 1000));
    return { ok: false, reason: 'stale', age_hours: ageHours, detail: `golden_opportunities.json قديم (${ageHours} ساعة، الحد 24) — تخطٍّ بلا فشل` };
  }

  const top = pickTopGoldenOpportunity(data);
  if (!top) {
    return { ok: false, reason: 'no_eligible_opportunity', detail: 'لا فرصة بحكم GOOD/GOLDEN في golden_opportunities.json حالياً' };
  }

  return { ok: true, top };
}

async function huntGolden(reachable) {
  if (!reachable) {
    return { action: 'skipped', ...appendGoldenHunterEvent({ action: 'skipped', reason: 'dashboard_unreachable', detail: 'السيرفر غير متاح — تخطّي جسر Golden Hunter هذه الدورة' }) };
  }

  const data = readGoldenOpportunities();
  const evaluation = evaluateGoldenOpportunities(data);
  if (!evaluation.ok) {
    const rec = appendGoldenHunterEvent({ action: 'skipped', reason: evaluation.reason, age_hours: evaluation.age_hours, detail: evaluation.detail });
    return { action: 'skipped', detail: rec.detail };
  }
  const top = evaluation.top;

  if (goldenNicheAlreadyAttempted(top.niche)) {
    const rec = appendGoldenHunterEvent({ action: 'skipped', reason: 'already_attempted', niche: top.niche, detail: `النيتش "${top.niche}" جُرِّب فعلياً سابقاً عبر جسر Golden Hunter — لا تكرار` });
    return { action: 'none', detail: rec.detail };
  }

  const rejection = isNicheRejected(top.niche);
  if (rejection) {
    const rec = appendGoldenHunterEvent({ action: 'skipped', reason: 'circuit_breaker', niche: top.niche, detail: `تخطّي نيتش مرفوض سابقاً (${top.niche}) — قاطع الدائرة نشط حتى ${rejection.retryAfter}: ${rejection.reason}` });
    return { action: 'skipped', detail: rec.detail };
  }

  // ADR-026: Opportunity Score gate — "fewer, better assets" means a
  // stricter bar than the old profit_score>=60 check alone. A scoring
  // failure (spawn error, timeout, bad output) fails OPEN here on
  // purpose, not closed: this is a NEW, additive gate layered on top of
  // profit_score/butter_price's existing checks (still enforced later by
  // book_generator.py's Dual Inspection regardless) — never block
  // production because a second, newer scoring call happened to fail.
  //
  // ADR-070 (mission follow-up, 2026-07-17): when the picked opportunity
  // carries a ladder tag (pickTopGoldenOpportunity() now prefers these,
  // market_hunter.py's retooled Strategic Production Priority Ladder
  // candidates, ADR-068), gate via the ladder-aware score instead — the
  // exact wiring ADR-069 disclosed as the remaining gap after Step 5's
  // proof. Every entry with no ladder tag (every pre-ladder golden
  // opportunity) keeps using the original opportunity_score() gate,
  // byte-for-byte unchanged.
  const opportunityScore = top.ladder
    ? await getLadderOpportunityScore(top.niche, top.ladder)
    : await getOpportunityScore(top.niche, { tier: 'tier4' });
  if (opportunityScore.ok && !opportunityScore.accepted) {
    const rec = appendGoldenHunterEvent({
      action: 'skipped', reason: 'opportunity_score_below_floor', niche: top.niche,
      opportunity_score: opportunityScore.score, detail: `تخطّي "${top.niche}" — Opportunity Score ${opportunityScore.score}/100 (${opportunityScore.reason})`,
    });
    return { action: 'skipped', detail: rec.detail };
  }

  if (opportunityScore.ok && opportunityScore.accepted) {
    notifyGoldenHunterAccepted(top.niche, opportunityScore).catch(() => {});
  }

  const brief = await briefFromGoldenOpportunity(top);

  if (!AUTO_PRODUCE_ENABLED) {
    // dry_run: record exactly what WOULD have been produced — zero Groq
    // calls, zero side effects beyond this one log line.
    const rec = appendGoldenHunterEvent({
      action: 'attempted', dry_run: true, niche: top.niche, profit_score: top.profit_score,
      verdict: top.verdict, brief,
      detail: `[dry-run] كان سيُنتَج: "${top.niche}" (score ${top.profit_score}, ${top.verdict}) — FACTORY_AUTO_PRODUCE غير مفعَّل`,
    });
    return { action: 'skipped', detail: rec.detail };
  }

  // Strategic Phase (2026-07-19): a ladder-tagged opportunity routes
  // through the modern pipeline (Product Definition Registry +
  // Commercial Execution Layer) instead of the legacy book_generator.py-
  // only path — market_hunter.py's own daily run already recorded a real
  // ACCEPTED decision for this exact niche (decision_path=
  // "ladder_fast_gate"); runLadderOpportunityPipeline() reuses it
  // (existing_decision=) rather than re-evaluating, so this can never
  // record a second decision/production_id for the same real opportunity.
  // A non-ladder opportunity (every pre-ladder golden candidate) keeps
  // using triggerGenerateBook(), byte-for-byte unchanged.
  if (top.ladder) {
    // Autonomous Digital Company v1 follow-up (2026-07-19): real production-
    // engine health gate — see checkProductionEngineHealth()'s own comment.
    const healthGate = await checkProductionEngineHealth();
    if (!healthGate.ok) {
      const rec = appendGoldenHunterEvent({
        action: 'skipped', reason: 'production_engine_unhealthy', niche: top.niche,
        detail: `تخطّي الإنتاج — ${healthGate.reason}`,
      });
      return { action: 'skipped', detail: rec.detail };
    }

    const result = await runLadderOpportunityPipeline(top.niche, top.ladder);
    const rec = appendGoldenHunterEvent({
      action: 'attempted', dry_run: false, niche: top.niche, profit_score: top.profit_score,
      verdict: top.verdict, brief, ladder: top.ladder, pipeline: 'orchestrator',
      ok: result.ok, detail: result.detail, production_id: result.production_id,
    });
    return {
      action: result.ok ? 'produced' : 'failed',
      detail: `[Golden Hunter → المحرك الحديث] ${rec.detail}`,
    };
  }

  const result = await triggerGenerateBook(brief);
  const rec = appendGoldenHunterEvent({
    action: 'attempted', dry_run: false, niche: top.niche, profit_score: top.profit_score,
    verdict: top.verdict, brief,
    ok: result.ok, rejected: !!result.rejected, detail: result.detail,
    distribution: result.distribution
      ? { ok: result.distribution.ok, dry_run: result.distribution.dry_run, detail: result.distribution.detail }
      : null,
  });
  return {
    action: result.ok ? 'produced' : (result.rejected ? 'rejected' : 'failed'),
    detail: `[Golden Hunter → إنتاج] ${rec.detail}`,
    distribution: result.distribution,
  };
}

// ── MINIMAL ATTENTION ALERTING ──
// AUTOMATION_GAPS_REPORT.md §3 flagged zero notification channel (inspectors.py
// itself: "no live notification channel wired"). NEEDS_ATTENTION.md is the
// simplest possible fix: no email/Slack, just a file at the repo root that
// this same function creates AND removes — its entire lifecycle is
// self-owned, the same pattern as .factory_loop.lock. It exists only while a
// real problem condition holds; a human doesn't have to remember to check
// logs every day during the FACTORY_AUTO_PRODUCE dry-run review window
// (AUTO_PRODUCE_ACTIVATION_CHECKLIST.md) — but is still expected to
// investigate via data/golden_hunter_events.jsonl / factory_loop.log, this
// file only says "look", never why in full detail.
//
// Three trigger conditions, all confirmed with real data before wiring in:
//   1. This tick's actions include action:"failed" for golden_hunter_bridge
//      or distribute — an immediate, single-tick signal.
//   2. The last ATTENTION_STREAK_THRESHOLD raw events in
//      golden_hunter_events.jsonl are ALL skipped for reason
//      stale/missing_or_unreadable — Golden Hunter itself looks stuck.
//   3. The last ATTENTION_STREAK_THRESHOLD "attempted" events all used
//      _price_source "fallback_floor_clamped" — profit_oracle.py
//      --butter-price (ADR-010) is failing repeatedly, not just once.
//   4. The same top niche (STRUCTURAL_DIAGNOSIS.md disease #1): each
//      dry-run "attempted" entry is individually honest, but
//      golden_opportunities.json's top pick can go unchanged for days while
//      huntGolden() keeps logging a "fresh" attempt every tick — which
//      *reads* like ongoing search activity when it is really the same
//      static candidate being re-scored. See checkGoldenStagnation() below.
const GOLDEN_STAGNATION_MS = 24 * 60 * 60 * 1000; // same top niche re-attempted, unchanged, for this long

// Walks the "attempted" events backwards from the most recent one and finds
// how long the exact same (niche, profit_score) pick has been repeating.
// Returns a human reason string once that streak exceeds GOLDEN_STAGNATION_MS,
// or null if the pick is new/changing/there isn't enough history yet.
function checkGoldenStagnation(logPath = GOLDEN_HUNTER_EVENTS_FILE, nowMs = Date.now()) {
  const attempted = readGoldenHunterEvents(logPath).filter(e => e.action === 'attempted' && e.niche);
  if (!attempted.length) return null;

  const last = attempted[attempted.length - 1];
  const lastNiche = normalizeNiche(last.niche);

  let streakStart = last;
  for (let i = attempted.length - 1; i >= 0; i--) {
    const e = attempted[i];
    if (normalizeNiche(e.niche) !== lastNiche || e.profit_score !== last.profit_score) break;
    streakStart = e;
  }

  const startMs = Date.parse(streakStart.timestamp);
  if (!Number.isFinite(startMs)) return null;
  const spanMs = nowMs - startMs;
  if (spanMs < GOLDEN_STAGNATION_MS) return null;

  const spanHours = Math.round(spanMs / (60 * 60 * 1000));
  return (
    `النيتش "${last.niche}" (profit_score ${last.profit_score}) هو نفسه أعلى فرصة في golden_opportunities.json ` +
    `منذ ${spanHours} ساعة بلا تغيير — الجسر يعمل ويسجّل بصدق كل تِكّة، لكن لا مرشّح جديد يُكتشَف؛ ` +
    'المصدر الحالي (market_hunter.py SEED_CATEGORIES الثابتة) لا يولِّد جديداً — راجع ADR-028 (مصدر مرشّحين حقيقي لم يُبنَ بعد).'
  );
}

// ADR-044: the one real integration point between market_intelligence_engine.py
// (run manually/deliberately — network calls stay out of this live loop,
// same boundary ADR-041/042/043 already established) and the actual
// automation loop. Pure file read — no new network call, no new
// subprocess. Surfaces the CURRENT state (an actionable AI CEO decision
// still sitting unaddressed), not a one-time notification — same
// semantics as every other NEEDS_ATTENTION.md reason: it stays flagged
// as long as it's still true, clears when it's not.
const MARKET_INTELLIGENCE_ANALYSES_FILE = path.join(FACTORY_DIR, 'data', 'market_intelligence_analyses.jsonl');
const AI_CEO_ACTIONABLE_DECISIONS = ['BUILD', 'PIVOT'];

function checkPendingAiCeoDecision(logPath = MARKET_INTELLIGENCE_ANALYSES_FILE) {
  if (!fs.existsSync(logPath)) return null;
  let lines;
  try {
    lines = fs.readFileSync(logPath, 'utf8').split('\n').filter(Boolean);
  } catch (_) {
    return null;
  }
  if (!lines.length) return null;

  let last;
  try {
    last = JSON.parse(lines[lines.length - 1]);
  } catch (_) {
    return null;
  }

  const decision = last && last.ai_ceo && last.ai_ceo.decision;
  if (!AI_CEO_ACTIONABLE_DECISIONS.includes(decision)) return null;

  const evidence = (last.ai_ceo.evidence || []).join('؛ ');
  return (
    `محرك الاستخبارات السوقية أصدر قراراً فعلياً غير مُعالَج بعد: "${decision}" لنيتش "${last.niche}" ` +
    `— ${evidence}. راجعه عبر: python market_intelligence_engine.py --analyze "${last.niche}"`
  );
}

function checkNeedsAttention(tickActions, logPath = GOLDEN_HUNTER_EVENTS_FILE) {
  const reasons = [];

  for (const a of tickActions || []) {
    if ((a.step === 'golden_hunter_bridge' || a.step === 'distribute') && a.action === 'failed') {
      reasons.push(`فشل حقيقي في خطوة "${a.step}" هذه الدورة: ${a.detail}`);
    }
  }

  const events = readGoldenHunterEvents(logPath);

  const recentRaw = events.slice(-ATTENTION_STREAK_THRESHOLD);
  if (
    recentRaw.length === ATTENTION_STREAK_THRESHOLD &&
    recentRaw.every(e => e.action === 'skipped' && (e.reason === 'stale' || e.reason === 'missing_or_unreadable'))
  ) {
    reasons.push(
      `آخر ${ATTENTION_STREAK_THRESHOLD} محاولات لجسر Golden Hunter كانت كلها "${recentRaw[recentRaw.length - 1].reason}" — ` +
      'يبدو Golden Hunter نفسه متوقفاً، أو golden_opportunities.json لا يتحدَّث.'
    );
  }

  const recentAttempted = events.filter(e => e.action === 'attempted').slice(-ATTENTION_STREAK_THRESHOLD);
  if (
    recentAttempted.length === ATTENTION_STREAK_THRESHOLD &&
    recentAttempted.every(e => e.brief && e.brief._price_source === 'fallback_floor_clamped')
  ) {
    reasons.push(
      `آخر ${ATTENTION_STREAK_THRESHOLD} محاولات تسعير استخدمت السقوط الآمن (fallback_floor_clamped) بدل ` +
      'butter_price() الحقيقية — استدعاء profit_oracle.py --butter-price يفشل بانتظام، لا مرة واحدة عابرة.'
    );
  }

  const stagnation = checkGoldenStagnation(logPath);
  if (stagnation) reasons.push(stagnation);

  const pendingAiCeo = checkPendingAiCeoDecision();
  if (pendingAiCeo) reasons.push(pendingAiCeo);

  return reasons;
}

// Prove-the-Company follow-up (Master Roadmap "Important" item M4): before
// this, NEEDS_ATTENTION.md/NEEDS_REVIEW.md were written correctly but
// nothing pushed them to a human — a real, verified gap between "the
// system correctly detects a problem" and "a human finds out" without
// remembering to check a file. Zero new dependencies, zero cloud service
// (CLAUDE.md's own architecture): a real Windows toast notification via
// PowerShell's System.Windows.Forms.NotifyIcon, already present on this
// machine. Fails completely silently on any error (missing PowerShell,
// no desktop session, non-Windows) — a notification must never be able
// to break a tick, exactly like every other best-effort side effect in
// this file. A hard 5s timeout guarantees this can never hang the loop.
// Security Mission Tracker finding 2.9 (2026-07-23), real fix: the
// previous implementation only escaped single quotes for the INNER
// PowerShell single-quoted string, then concatenated the whole script
// into an OUTER double-quoted `-Command "..."` shell argument -- a real
// double-quote character in title/message (both carry externally-
// influenced text, e.g. this same file's own Scout/Hacker-News-sourced
// niche titles) would terminate that outer double-quoted argument
// early, letting the remainder be parsed as additional PowerShell/shell
// tokens.
//
// Fixed by removing string interpolation of untrusted data from the
// script text entirely: the PowerShell script is now a fixed, static
// file written to a real temp path (never containing title/message),
// with a `param([string]$title, [string]$message)` block. Real,
// unescaped title/message are passed as separate, literal `-File`
// script arguments via execFileSync -- PowerShell's own documented
// contract for `-File` is that everything after the script path is the
// script's own literal parameters, never re-parsed as PowerShell/shell
// syntax (unlike `-Command`/`-EncodedCommand`'s trailing arguments,
// which real testing while building this fix found PowerShell.exe
// itself sometimes still misinterprets around embedded quotes). Proven
// directly: a title/message containing `"`, `` ` ``, `$(...)`, `;`, and
// `|` together reaches the script as inert literal text with zero
// execution -- see tests/test_factory_loop_notification.js.
function sendDesktopNotification(title, message) {
  let scriptPath;
  try {
    scriptPath = path.join(os.tmpdir(), `galaxy_forge_notify_${process.pid}_${Date.now()}.ps1`);
    fs.writeFileSync(scriptPath, [
      'param([string]$title, [string]$message)',
      'Add-Type -AssemblyName System.Windows.Forms',
      '$n = New-Object System.Windows.Forms.NotifyIcon',
      '$n.Icon = [System.Drawing.SystemIcons]::Warning; $n.Visible = $true',
      '$n.ShowBalloonTip(10000, $title, $message, [System.Windows.Forms.ToolTipIcon]::Warning)',
      'Start-Sleep -Seconds 1; $n.Dispose()',
      '',
    ].join('\n'), 'utf8');
    execFileSync('powershell.exe', [
      '-NoProfile', '-NonInteractive', '-File', scriptPath, title, message,
    ], { timeout: 5000, stdio: 'ignore' });
    return true;
  } catch (_) {
    return false; // never let a notification failure affect the real tick
  } finally {
    if (scriptPath) {
      try { fs.unlinkSync(scriptPath); } catch (_) { /* best-effort cleanup only */ }
    }
  }
}

function writeNeedsAttention(reasons, filePath = NEEDS_ATTENTION_FILE) {
  const content = [
    '# ⚠️ NEEDS_ATTENTION.md — يحتاج مراجعة بشرية',
    '',
    `آخر تحديث: ${new Date().toISOString()}`,
    '',
    'هذا الملف يُكتَب ويُحذَف تلقائياً بواسطة factory_loop.js فقط — وجوده يعني أن أحد الشروط التالية تحقّق الآن:',
    '',
    ...reasons.map(r => `- ${r}`),
    '',
    'راجع `data/golden_hunter_events.jsonl` و`factory_loop.log` للتفاصيل الكاملة. سيُحذَف هذا الملف تلقائياً بمجرد أن تعود الدورات القادمة لحالتها الطبيعية — لا حاجة لحذفه يدوياً.',
    '',
  ].join('\n');
  try {
    fs.writeFileSync(filePath, content, 'utf8');
  } catch (err) {
    console.error('[factory_loop] failed to write NEEDS_ATTENTION.md:', err.message);
  }
}

function clearNeedsAttention(filePath = NEEDS_ATTENTION_FILE) {
  try {
    if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
  } catch (err) {
    console.error('[factory_loop] failed to clear NEEDS_ATTENTION.md:', err.message);
  }
}

// ── PENDING REVIEW NOTIFICATION (Human-in-the-Loop, HIGH_VALUE_EXECUTION_PLAN.md) ──
// Same self-owned create/delete lifecycle as NEEDS_ATTENTION.md above —
// NEEDS_REVIEW.md exists only while pending_review/queue/ actually has
// drafts waiting, so the president doesn't have to remember to check an
// empty folder. This step only counts files; it never reads/writes/moves
// any draft itself (that stays a manual+Claude review action, then
// scripts/process_approved_drafts.py — see pending_review/README.md).
const PENDING_REVIEW_QUEUE_DIR = path.join(FACTORY_DIR, 'pending_review', 'queue');
const NEEDS_REVIEW_FILE = path.join(FACTORY_DIR, 'NEEDS_REVIEW.md');

function countPendingReviewDrafts(queueDir = PENDING_REVIEW_QUEUE_DIR) {
  if (!fs.existsSync(queueDir)) return 0;
  try {
    return fs.readdirSync(queueDir).filter(f => f.toLowerCase().endsWith('.json')).length;
  } catch (err) {
    return 0;
  }
}

function writeNeedsReview(count, filePath = NEEDS_REVIEW_FILE) {
  const content = [
    '# 📝 NEEDS_REVIEW.md — مسودات بانتظار المراجعة',
    '',
    `آخر تحديث: ${new Date().toISOString()}`,
    '',
    `يوجد ${count} مسودة في \`pending_review/queue/\` بانتظار مراجعة بشرية-Claude (نموذج المراجعة المعلَّقة، HIGH_VALUE_EXECUTION_PLAN.md).`,
    '',
    'الخطوة التالية: افتح Claude Code وقل "راجع المسودات المعلقة" — راجع `pending_review/README.md` لخطوات المراجعة الكاملة.',
    '',
    'هذا الملف يُكتَب ويُحذَف تلقائياً بواسطة factory_loop.js فقط — سيُحذَف تلقائياً بمجرد أن يُفرَّغ `queue/` (بعد نقل كل مسودة إلى `approved/`).',
    '',
  ].join('\n');
  try {
    fs.writeFileSync(filePath, content, 'utf8');
  } catch (err) {
    console.error('[factory_loop] failed to write NEEDS_REVIEW.md:', err.message);
  }
}

function clearNeedsReview(filePath = NEEDS_REVIEW_FILE) {
  try {
    if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
  } catch (err) {
    console.error('[factory_loop] failed to clear NEEDS_REVIEW.md:', err.message);
  }
}

function checkPendingReview(queueDir = PENDING_REVIEW_QUEUE_DIR, notifyFilePath = NEEDS_REVIEW_FILE) {
  const count = countPendingReviewDrafts(queueDir);
  if (count > 0) {
    writeNeedsReview(count, notifyFilePath);
  } else {
    clearNeedsReview(notifyFilePath);
  }
  return { action: count > 0 ? 'needs_review' : 'none', detail: count > 0 ? `${count} مسودة بانتظار المراجعة` : '\`pending_review/queue/\` فارغ' };
}

// ── HEAL ──

// NOTE on this check: the task asked to "rebuild finance.json from
// scout_runs.log". scout_runs.log records Scout niche-picks and book
// generations — it holds no sales/revenue data at all, so there is nothing
// in it to reconstruct financial totals from. The honest, safe repair
// (mirroring server.js's own loadFin() self-heal from the Finance fix task)
// is: quarantine the corrupt file and reset to clean empty finance data —
// exactly what already happens automatically on the next /finance request.
// This just does it proactively instead of waiting for that request.
function healFinance(health) {
  const financeOk = health && health.checks && health.checks.finance && health.checks.finance.ok;
  if (financeOk !== false) {
    return { action: 'none', detail: 'finance_data.json سليم' };
  }
  try {
    if (fs.existsSync(FINANCE_FILE)) {
      fs.copyFileSync(FINANCE_FILE, `${FINANCE_FILE}.loop-corrupt-${Date.now()}.bak`);
    }
    const clean = { sales: [], totalKDP: 0, totalEtsy: 0, totalGumroad: 0, totalSales: 0, lastUpdated: new Date().toISOString() };
    fs.writeFileSync(FINANCE_FILE, JSON.stringify(clean, null, 2));
    return {
      action: 'healed',
      detail: 'finance_data.json كان فاسداً — عُزل واستُبدل ببيانات فارغة نظيفة (وليس من scout_runs.log، فهو لا يحوي بيانات مالية — انظر التعليق أعلى الدالة)',
    };
  } catch (err) {
    return { action: 'failed', detail: `تعذّر إصلاح finance_data.json: ${err.message}` };
  }
}

async function healEmptyBooks(reachable) {
  if (countBooks() > 0) return { action: 'none', detail: 'books/ غير فارغ' };
  if (!reachable) return { action: 'skipped', detail: 'books/ فارغ لكن السيرفر غير متاح الآن لإعادة التوليد' };

  const entries = readScoutLog();
  const lastSuccess = [...entries].reverse().find(e => e.context === 'success' && e.brief);
  if (!lastSuccess) {
    return { action: 'skipped', detail: 'books/ فارغ ولا يوجد نيتش Scout سابق في scout_runs.log لإعادة توليده' };
  }
  const result = await triggerGenerateBook(lastSuccess.brief);
  return {
    action: result.ok ? 'healed' : 'failed',
    detail: `books/ كان فارغاً — أُعيد توليد آخر نيتش Scout (${lastSuccess.brief.title}): ${result.detail}`,
    distribution: result.distribution,
  };
}

function healN8n(health) {
  const n8nOk = health && health.checks && health.checks.sensing_engine && health.checks.sensing_engine.ok;
  if (n8nOk) return { action: 'none', detail: 'n8n يعمل' };
  return {
    action: 'warning',
    detail: 'n8n غير متاح — يُتابَع الإنتاج بدونه (Scout يعتمد على تحليل Groq الاحتياطي مؤقتاً، كما صُمِّم في مسار Scout)',
  };
}

// ── HUNT ──
// "Highest traffic niche": today's Scout pipeline (see [4]) has no real
// trend-volume number from n8n yet (n8n only acks that it started, it
// doesn't return real Google Trends data — a documented, known gap). With no
// real traffic metric to rank by, the most-recent quality-gate-passed niche
// among the last 3 successful runs is used as an honest stand-in, rather than
// inventing a fake traffic score.
async function hunt(reachable) {
  if (!reachable) return { action: 'skipped', detail: 'السيرفر غير متاح — تخطي HUNT' };

  // Literal reading of the spec: look at the last 3 raw log entries (whatever
  // they are — successes, errors, anything), THEN filter those specifically
  // for one that passed the Quality Gate. This intentionally does NOT reach
  // further back into history to find an older gate-passed niche if the most
  // recent 3 entries happen to be failures — that would be "last N successes"
  // instead of "last 3 entries", a different (looser) query than what was
  // asked for.
  const entries = readScoutLog();
  const lastThree = entries.slice(-3);
  const eligible = lastThree.filter(e => e.context === 'success' && e.brief && e.book && e.book.quality_gate && e.book.quality_gate.passed);
  if (!eligible.length) {
    return { action: 'none', detail: `لا يوجد بين آخر ${lastThree.length} سجل في scout_runs.log أي نيتش اجتاز Quality Gate` };
  }

  const chosen = eligible[eligible.length - 1]; // most recent eligible — see "highest traffic" note above

  // Circuit breaker: don't waste a Groq call retrying a niche that Dual
  // Inspection already rejected within the last 7 days — see REJECTED_NICHES.md.
  const rejection = isNicheRejected(chosen.brief.topic);
  if (rejection) {
    const detail = `تخطي نيتش مرفوض (${chosen.brief.title}) — قاطع الدائرة نشط حتى ${rejection.retryAfter}: ${rejection.reason}`;
    return { action: 'skipped', detail };
  }

  const expectedFile = chosen.book && chosen.book.file;
  const stillExists = expectedFile && fs.existsSync(path.join(BOOKS_DIR, expectedFile));
  if (stillExists) {
    return { action: 'none', detail: `أحدث نيتش مؤهَّل (${chosen.brief.title}) له كتاب موجود بالفعل` };
  }

  const result = await triggerGenerateBook(chosen.brief);
  return {
    action: result.ok ? 'healed' : (result.rejected ? 'rejected' : 'failed'),
    detail: `كتاب مفقود لنيتش مؤهَّل من آخر ${lastThree.length} سجلات (${chosen.brief.title}): ${result.detail}`,
    distribution: result.distribution,
  };
}

// ── GOLDEN HUNTER ──
// CONSTITUTION.md §19: market_hunter.py scans for new golden opportunities,
// consulting the Knowledge Brain (REJECTED_NICHES.md included) before
// proposing anything. It's a standalone Python script, spawned locally —
// unlike HUNT/HEAL it needs no dashboard reachability, so it runs
// regardless. Gated to once per calendar day (not every 10-minute tick):
// scanning the same curated candidate list more than once a day would just
// re-discover the same niches for no new information.
function detectPythonForHunter() {
  const candidates = ['python3', 'python', 'py'];
  for (const cmd of candidates) {
    try {
      execSync(`${cmd} --version`, { stdio: 'ignore' });
      return cmd;
    } catch (_) { /* try next candidate */ }
  }
  return 'python';
}

function lastHuntDate() {
  if (!fs.existsSync(MARKET_HUNTER_LOG)) return null;
  const lines = fs.readFileSync(MARKET_HUNTER_LOG, 'utf8').split('\n').filter(Boolean);
  if (!lines.length) return null;
  try {
    const last = JSON.parse(lines[lines.length - 1]);
    const t = Date.parse(last.timestamp);
    return Number.isFinite(t) ? isoDate(new Date(t)) : null;
  } catch (_) {
    return null;
  }
}

function runMarketHunter() {
  return new Promise((resolve) => {
    const pythonPath = detectPythonForHunter();
    const child = spawn(pythonPath, [path.join(FACTORY_DIR, 'market_hunter.py'), '--run'], { cwd: FACTORY_DIR });
    let output = '', errOut = '';
    const timer = setTimeout(() => {
      child.kill();
      resolve({ ok: false, detail: 'انتهت مهلة market_hunter.py (60 ثانية)' });
    }, 60000);
    child.stdout.on('data', d => { output += d.toString(); });
    child.stderr.on('data', d => { errOut += d.toString(); });
    child.on('close', () => {
      clearTimeout(timer);
      try {
        const result = JSON.parse(output.trim());
        resolve({
          ok: !!result.success,
          detail: `مسح ${result.scanned} نيتش، ${result.skipped} تخطّي، ${result.golden} ذهبي`,
        });
      } catch (e) {
        resolve({ ok: false, detail: `فشل تحليل ناتج market_hunter.py: ${e.message}${errOut ? ' — ' + errOut.slice(0, 200) : ''}` });
      }
    });
  });
}

async function maybeRunMarketHunter(now = new Date()) {
  const today = isoDate(now);
  if (lastHuntDate() === today) {
    return { action: 'none', detail: `تم تشغيل Golden Hunter اليوم بالفعل (${today})` };
  }
  const result = await runMarketHunter();
  return { action: result.ok ? 'hunted' : 'failed', detail: result.detail };
}

// ── STRATEGIC PHASE (2026-07-19): the modern Product Definition
// Registry + Commercial Execution Layer pipeline, for ladder-tagged
// golden opportunities only. Reuses the SAME FACTORY_AUTO_PRODUCE gate
// AUTO_PRODUCE_ACTIVATION_CHECKLIST.md already documents (no new env
// var, no new review process) — this function is only ever called from
// huntGolden() when that gate is already on. Spawns
// `python -m orchestrator.orchestrator` (NOT the raw script path — see
// orchestrator/orchestrator.py's own docstring: the raw-path form
// shadows Python's stdlib `types` module via orchestrator/types.py).
function runLadderOpportunityPipeline(niche, ladder, { timeoutMs = 150000, pythonPath } = {}) {
  return new Promise((resolve) => {
    let python;
    try {
      python = spawn(pythonPath || detectPythonForHunter(), ['-m', 'orchestrator.orchestrator', '--run-ladder-opportunity'], { cwd: FACTORY_DIR });
    } catch (err) {
      resolve({ ok: false, detail: `تعذّر تشغيل orchestrator.orchestrator: ${err.message}` });
      return;
    }

    let output = '', errOut = '', settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };
    const timer = setTimeout(() => {
      try { python.kill(); } catch (_) { /* best effort */ }
      finish({ ok: false, detail: `انتهت مهلة orchestrator.orchestrator --run-ladder-opportunity (${timeoutMs / 1000} ثانية)` });
    }, timeoutMs);

    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', (err) => finish({ ok: false, detail: err.message }));
    python.on('close', () => {
      try {
        const result = JSON.parse(output.trim());
        if (!result.success) {
          finish({ ok: false, detail: result.error || 'فشل غير محدَّد من orchestrator.orchestrator' });
          return;
        }
        finish({
          ok: result.production_success === true && result.publishing_status === 'SUCCESS',
          detail: `production=${result.production_status} (${result.production_id || 'no id'}), publishing=${result.publishing_status}`,
          production_id: result.production_id,
          publish_record: result.publish_record,
        });
      } catch (e) {
        finish({ ok: false, detail: `فشل تحليل ناتج orchestrator.orchestrator: ${e.message}${errOut ? ' — ' + errOut.slice(0, 200) : ''}` });
      }
    });

    python.stdin.write(JSON.stringify({ niche, ladder, tier: 'tier4' }));
    python.stdin.end();
  });
}

// Autonomous Digital Company v1, Track A (2026-07-19): the same joined
// executive_intelligence + strategic_intelligence + validation_layer +
// revenue_pipeline report Mission Control's "Export Executive Report"
// button produces (mission_control_api.py::_export_executive_report()),
// reused here rather than re-derived, so the weekly report and the
// on-demand button can never disagree. ~13s on real data (4 real report
// generators reading real files) — timeoutMs gives ample margin.
function runExportExecutiveReport({ timeoutMs = 60000, pythonPath } = {}) {
  return new Promise((resolve) => {
    let python;
    try {
      python = spawn(pythonPath || detectPythonForHunter(), [path.join(FACTORY_DIR, 'mission_control_api.py'), 'export_executive_report'], { cwd: FACTORY_DIR });
    } catch (err) {
      resolve({ ok: false, detail: `تعذّر تشغيل mission_control_api.py: ${err.message}` });
      return;
    }

    let output = '', errOut = '', settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };
    const timer = setTimeout(() => {
      try { python.kill(); } catch (_) { /* best effort */ }
      finish({ ok: false, detail: `انتهت مهلة export_executive_report (${timeoutMs / 1000} ثانية)` });
    }, timeoutMs);

    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', (err) => finish({ ok: false, detail: err.message }));
    python.on('close', () => {
      try {
        const result = JSON.parse(output.trim());
        if (!result.success) {
          finish({ ok: false, detail: result.error || 'فشل غير محدَّد من export_executive_report' });
          return;
        }
        finish({ ok: true, path: result.path, markdown: result.markdown });
      } catch (e) {
        finish({ ok: false, detail: `فشل تحليل ناتج export_executive_report: ${e.message}${errOut ? ' — ' + errOut.slice(0, 200) : ''}` });
      }
    });
  });
}

// EOS Phase 2, Autonomous Recommendations (2026-07-19): same subprocess
// pattern as runExportExecutiveReport() above, calling
// mission_control_api.py's evolution_report section (evolution_engine.
// build_evolution_report(), real bottleneck/tech-debt/ROI/capability-gap
// signals -- no new business logic here).
function runEvolutionReport({ timeoutMs = 30000, pythonPath } = {}) {
  return new Promise((resolve) => {
    let python;
    try {
      python = spawn(pythonPath || detectPythonForHunter(), [path.join(FACTORY_DIR, 'mission_control_api.py'), 'evolution_report'], { cwd: FACTORY_DIR });
    } catch (err) {
      resolve({ ok: false, detail: `تعذّر تشغيل mission_control_api.py: ${err.message}` });
      return;
    }

    let output = '', errOut = '', settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };
    const timer = setTimeout(() => {
      try { python.kill(); } catch (_) { /* best effort */ }
      finish({ ok: false, detail: `انتهت مهلة evolution_report (${timeoutMs / 1000} ثانية)` });
    }, timeoutMs);

    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', (err) => finish({ ok: false, detail: err.message }));
    python.on('close', () => {
      try {
        const result = JSON.parse(output.trim());
        if (!result.success) {
          finish({ ok: false, detail: result.error || 'فشل غير محدَّد من evolution_report' });
          return;
        }
        finish({ ok: true, markdown: result.markdown });
      } catch (e) {
        finish({ ok: false, detail: `فشل تحليل ناتج evolution_report: ${e.message}${errOut ? ' — ' + errOut.slice(0, 200) : ''}` });
      }
    });
  });
}

function evolutionReportPath(now) {
  return path.join(REPORTS_DIR, `EVOLUTION_${isoDate(now)}.md`);
}

// Company Evolution Protocol V1 (ADR-173, 2026-08-05): same subprocess
// pattern as runEvolutionReport() above, calling mission_control_api.py's
// galaxy_evolution_report section (evolution_engine.build_galaxy_
// evolution_report(), a real relabel/extension of build_evolution_report()
// -- no new business logic here).
function runGalaxyEvolutionReport({ timeoutMs = 30000, pythonPath } = {}) {
  return new Promise((resolve) => {
    let python;
    try {
      python = spawn(pythonPath || detectPythonForHunter(), [path.join(FACTORY_DIR, 'mission_control_api.py'), 'galaxy_evolution_report'], { cwd: FACTORY_DIR });
    } catch (err) {
      resolve({ ok: false, detail: `تعذّر تشغيل mission_control_api.py: ${err.message}` });
      return;
    }

    let output = '', errOut = '', settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };
    const timer = setTimeout(() => {
      try { python.kill(); } catch (_) { /* best effort */ }
      finish({ ok: false, detail: `انتهت مهلة galaxy_evolution_report (${timeoutMs / 1000} ثانية)` });
    }, timeoutMs);

    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', (err) => finish({ ok: false, detail: err.message }));
    python.on('close', () => {
      try {
        const result = JSON.parse(output.trim());
        if (!result.success) {
          finish({ ok: false, detail: result.error || 'فشل غير محدَّد من galaxy_evolution_report' });
          return;
        }
        finish({ ok: true, markdown: result.markdown });
      } catch (e) {
        finish({ ok: false, detail: `فشل تحليل ناتج galaxy_evolution_report: ${e.message}${errOut ? ' — ' + errOut.slice(0, 200) : ''}` });
      }
    });
  });
}

function galaxyEvolutionReportPath(now) {
  return path.join(REPORTS_DIR, `GALAXY_EVOLUTION_${now.getUTCFullYear()}-${String(now.getUTCMonth() + 1).padStart(2, '0')}.md`);
}

// The directive's own "monthly" cadence, genuinely new (every other real
// report in this factory is daily or weekly-on-Sunday) -- same file-
// existence gate technique, one real file per real calendar month instead
// of per day. First tick of a new real month generates it; every other
// tick that real month is a real no-op.
async function maybeGenerateMonthlyGalaxyEvolutionReport(now = new Date()) {
  const datedPath = galaxyEvolutionReportPath(now);
  if (fs.existsSync(datedPath)) {
    return { action: 'none', detail: `تقرير التطوّر الشهري لهذا الشهر موجود بالفعل: ${path.basename(datedPath)}` };
  }
  const result = await runGalaxyEvolutionReport();
  if (!result.ok) {
    return { action: 'failed', detail: result.detail };
  }
  try {
    fs.mkdirSync(REPORTS_DIR, { recursive: true });
    fs.writeFileSync(datedPath, result.markdown, 'utf-8');
    return { action: 'generated', detail: `تقرير تطوّر شهري جديد: ${path.basename(datedPath)}` };
  } catch (err) {
    return { action: 'failed', detail: `تعذّر كتابة تقرير التطوّر الشهري: ${err.message}` };
  }
}

// Galaxy Forge Executive Constitution (ADR-177, 2026-08-06): the real
// quarterly Architecture Review + annual Strategic Review cadences --
// this factory's first quarterly/annual gates, alongside its existing
// daily/weekly/monthly ones. Same subprocess pattern as every report
// function above, calling mission_control_api.py's real endpoints
// (enterprise_validation.py/strategic_planning.py, both already real,
// never a second computation).
function runEnterpriseValidationReportQuarterly({ timeoutMs = 1000000, pythonPath } = {}) {
  return new Promise((resolve) => {
    let python;
    try {
      python = spawn(pythonPath || detectPythonForHunter(), [path.join(FACTORY_DIR, 'mission_control_api.py'), 'enterprise_validation_report_quarterly'], { cwd: FACTORY_DIR });
    } catch (err) {
      resolve({ ok: false, detail: `تعذّر تشغيل mission_control_api.py: ${err.message}` });
      return;
    }
    let output = '', errOut = '', settled = false;
    const finish = (result) => { if (settled) return; settled = true; clearTimeout(timer); resolve(result); };
    const timer = setTimeout(() => {
      try { python.kill(); } catch (_) { /* best effort */ }
      finish({ ok: false, detail: `انتهت مهلة enterprise_validation_report_quarterly (${timeoutMs / 1000} ثانية)` });
    }, timeoutMs);
    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', (err) => finish({ ok: false, detail: err.message }));
    python.on('close', () => {
      try {
        const result = JSON.parse(output.trim());
        if (!result.success) { finish({ ok: false, detail: result.error || 'فشل غير محدَّد' }); return; }
        finish({ ok: true, markdown: result.markdown });
      } catch (e) {
        finish({ ok: false, detail: `فشل تحليل الناتج: ${e.message}${errOut ? ' — ' + errOut.slice(0, 200) : ''}` });
      }
    });
  });
}

function runStrategicPlanningReportAnnual({ timeoutMs = 200000, pythonPath } = {}) {
  return new Promise((resolve) => {
    let python;
    try {
      python = spawn(pythonPath || detectPythonForHunter(), [path.join(FACTORY_DIR, 'mission_control_api.py'), 'strategic_planning_report_annual'], { cwd: FACTORY_DIR });
    } catch (err) {
      resolve({ ok: false, detail: `تعذّر تشغيل mission_control_api.py: ${err.message}` });
      return;
    }
    let output = '', errOut = '', settled = false;
    const finish = (result) => { if (settled) return; settled = true; clearTimeout(timer); resolve(result); };
    const timer = setTimeout(() => {
      try { python.kill(); } catch (_) { /* best effort */ }
      finish({ ok: false, detail: `انتهت مهلة strategic_planning_report_annual (${timeoutMs / 1000} ثانية)` });
    }, timeoutMs);
    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', (err) => finish({ ok: false, detail: err.message }));
    python.on('close', () => {
      try {
        const result = JSON.parse(output.trim());
        if (!result.success) { finish({ ok: false, detail: result.error || 'فشل غير محدَّد' }); return; }
        finish({ ok: true, markdown: result.markdown });
      } catch (e) {
        finish({ ok: false, detail: `فشل تحليل الناتج: ${e.message}${errOut ? ' — ' + errOut.slice(0, 200) : ''}` });
      }
    });
  });
}

function architectureReviewReportPath(now) {
  const quarter = Math.floor(now.getUTCMonth() / 3) + 1;
  return path.join(REPORTS_DIR, `ARCHITECTURE_REVIEW_${now.getUTCFullYear()}-Q${quarter}.md`);
}

function annualStrategicReviewReportPath(now) {
  return path.join(REPORTS_DIR, `ANNUAL_STRATEGIC_REVIEW_${now.getUTCFullYear()}.md`);
}

// Once-per-calendar-quarter gate, same file-existence technique as the
// monthly/weekly/daily gates above, just widened to 3 real months.
async function maybeGenerateQuarterlyArchitectureReview(now = new Date()) {
  const datedPath = architectureReviewReportPath(now);
  if (fs.existsSync(datedPath)) {
    return { action: 'none', detail: `مراجعة العمارة الفصلية لهذا الفصل موجودة بالفعل: ${path.basename(datedPath)}` };
  }
  const result = await runEnterpriseValidationReportQuarterly();
  if (!result.ok) return { action: 'failed', detail: result.detail };
  try {
    fs.mkdirSync(REPORTS_DIR, { recursive: true });
    fs.writeFileSync(datedPath, result.markdown, 'utf-8');
    return { action: 'generated', detail: `مراجعة عمارة فصلية جديدة: ${path.basename(datedPath)}` };
  } catch (err) {
    return { action: 'failed', detail: `تعذّر كتابة مراجعة العمارة الفصلية: ${err.message}` };
  }
}

// Once-per-calendar-year gate.
async function maybeGenerateAnnualStrategicReview(now = new Date()) {
  const datedPath = annualStrategicReviewReportPath(now);
  if (fs.existsSync(datedPath)) {
    return { action: 'none', detail: `المراجعة الاستراتيجية السنوية لهذا العام موجودة بالفعل: ${path.basename(datedPath)}` };
  }
  const result = await runStrategicPlanningReportAnnual();
  if (!result.ok) return { action: 'failed', detail: result.detail };
  try {
    fs.mkdirSync(REPORTS_DIR, { recursive: true });
    fs.writeFileSync(datedPath, result.markdown, 'utf-8');
    return { action: 'generated', detail: `مراجعة استراتيجية سنوية جديدة: ${path.basename(datedPath)}` };
  } catch (err) {
    return { action: 'failed', detail: `تعذّر كتابة المراجعة الاستراتيجية السنوية: ${err.message}` };
  }
}

// Same once-per-calendar-day gating pattern as maybeGenerateWeeklyReport()
// (file-existence check for today's dated report) -- no new scheduler,
// reuses the exact existing daily-gate shape already proven for Golden
// Hunter's own maybeRunMarketHunter()/lastHuntDate().
async function maybeGenerateDailyEvolutionReport(now = new Date()) {
  const datedPath = evolutionReportPath(now);
  if (fs.existsSync(datedPath)) {
    return { action: 'none', detail: `تقرير التطوّر اليومي موجود بالفعل: ${path.basename(datedPath)}` };
  }
  const result = await runEvolutionReport();
  if (!result.ok) {
    return { action: 'failed', detail: result.detail };
  }
  try {
    fs.mkdirSync(REPORTS_DIR, { recursive: true });
    fs.writeFileSync(datedPath, result.markdown, 'utf8');
    return { action: 'generated', detail: `تم إنشاء تقرير التطوّر اليومي: ${path.basename(datedPath)}` };
  } catch (err) {
    return { action: 'failed', detail: `فشل حفظ تقرير التطوّر: ${err.message}` };
  }
}

// Executive Intelligence Core, Round 1 (2026-07-29): ai_doctor.py and
// department_health.py already had the exact real report shape
// (render_markdown() + a mission_control_api.py dispatch command) that
// evolution_report/self_awareness above already run daily -- they were
// just never wired into the tick. Same subprocess pattern verbatim,
// nothing new invented.
function runAiDoctorReport({ timeoutMs = 30000, pythonPath } = {}) {
  return new Promise((resolve) => {
    let python;
    try {
      python = spawn(pythonPath || detectPythonForHunter(), [path.join(FACTORY_DIR, 'mission_control_api.py'), 'ai_doctor'], { cwd: FACTORY_DIR });
    } catch (err) {
      resolve({ ok: false, detail: `تعذّر تشغيل mission_control_api.py: ${err.message}` });
      return;
    }

    let output = '', errOut = '', settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };
    const timer = setTimeout(() => {
      try { python.kill(); } catch (_) { /* best effort */ }
      finish({ ok: false, detail: `انتهت مهلة ai_doctor (${timeoutMs / 1000} ثانية)` });
    }, timeoutMs);

    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', (err) => finish({ ok: false, detail: err.message }));
    python.on('close', () => {
      try {
        const result = JSON.parse(output.trim());
        if (!result.success) {
          finish({ ok: false, detail: result.error || 'فشل غير محدَّد من ai_doctor' });
          return;
        }
        finish({ ok: true, markdown: result.markdown });
      } catch (e) {
        finish({ ok: false, detail: `فشل تحليل ناتج ai_doctor: ${e.message}${errOut ? ' — ' + errOut.slice(0, 200) : ''}` });
      }
    });
  });
}

function aiDoctorReportPath(now) {
  return path.join(REPORTS_DIR, `AI_DOCTOR_${isoDate(now)}.md`);
}

async function maybeGenerateDailyAiDoctorReport(now = new Date()) {
  const datedPath = aiDoctorReportPath(now);
  if (fs.existsSync(datedPath)) {
    return { action: 'none', detail: `تقرير AI Doctor اليومي موجود بالفعل: ${path.basename(datedPath)}` };
  }
  const result = await runAiDoctorReport();
  if (!result.ok) {
    return { action: 'failed', detail: result.detail };
  }
  try {
    fs.mkdirSync(REPORTS_DIR, { recursive: true });
    fs.writeFileSync(datedPath, result.markdown, 'utf8');
    return { action: 'generated', detail: `تم إنشاء تقرير AI Doctor اليومي: ${path.basename(datedPath)}` };
  } catch (err) {
    return { action: 'failed', detail: `فشل حفظ تقرير AI Doctor: ${err.message}` };
  }
}

function runDepartmentHealthReport({ timeoutMs = 30000, pythonPath } = {}) {
  return new Promise((resolve) => {
    let python;
    try {
      python = spawn(pythonPath || detectPythonForHunter(), [path.join(FACTORY_DIR, 'mission_control_api.py'), 'department_health'], { cwd: FACTORY_DIR });
    } catch (err) {
      resolve({ ok: false, detail: `تعذّر تشغيل mission_control_api.py: ${err.message}` });
      return;
    }

    let output = '', errOut = '', settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };
    const timer = setTimeout(() => {
      try { python.kill(); } catch (_) { /* best effort */ }
      finish({ ok: false, detail: `انتهت مهلة department_health (${timeoutMs / 1000} ثانية)` });
    }, timeoutMs);

    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', (err) => finish({ ok: false, detail: err.message }));
    python.on('close', () => {
      try {
        const result = JSON.parse(output.trim());
        if (!result.success) {
          finish({ ok: false, detail: result.error || 'فشل غير محدَّد من department_health' });
          return;
        }
        finish({ ok: true, markdown: result.markdown });
      } catch (e) {
        finish({ ok: false, detail: `فشل تحليل ناتج department_health: ${e.message}${errOut ? ' — ' + errOut.slice(0, 200) : ''}` });
      }
    });
  });
}

function departmentHealthReportPath(now) {
  return path.join(REPORTS_DIR, `DEPARTMENT_HEALTH_${isoDate(now)}.md`);
}

async function maybeGenerateDailyDepartmentHealthReport(now = new Date()) {
  const datedPath = departmentHealthReportPath(now);
  if (fs.existsSync(datedPath)) {
    return { action: 'none', detail: `تقرير صحة الأقسام اليومي موجود بالفعل: ${path.basename(datedPath)}` };
  }
  const result = await runDepartmentHealthReport();
  if (!result.ok) {
    return { action: 'failed', detail: result.detail };
  }
  try {
    fs.mkdirSync(REPORTS_DIR, { recursive: true });
    fs.writeFileSync(datedPath, result.markdown, 'utf8');
    return { action: 'generated', detail: `تم إنشاء تقرير صحة الأقسام اليومي: ${path.basename(datedPath)}` };
  } catch (err) {
    return { action: 'failed', detail: `فشل حفظ تقرير صحة الأقسام: ${err.message}` };
  }
}

// Strategic Intelligence Core (2026-07-29): same subprocess + daily-gate
// pattern as runDepartmentHealthReport() immediately above, calling
// mission_control_api.py's executive_brief section
// (strategic_intelligence_core.build_executive_brief() + its own
// render_markdown() -- no new business logic here, this is a report
// generator only).
function runExecutiveBrief({ timeoutMs = 30000, pythonPath } = {}) {
  return new Promise((resolve) => {
    let python;
    try {
      python = spawn(pythonPath || detectPythonForHunter(), [path.join(FACTORY_DIR, 'mission_control_api.py'), 'executive_brief'], { cwd: FACTORY_DIR });
    } catch (err) {
      resolve({ ok: false, detail: `تعذّر تشغيل mission_control_api.py: ${err.message}` });
      return;
    }

    let output = '', errOut = '', settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };
    const timer = setTimeout(() => {
      try { python.kill(); } catch (_) { /* best effort */ }
      finish({ ok: false, detail: `انتهت مهلة executive_brief (${timeoutMs / 1000} ثانية)` });
    }, timeoutMs);

    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', (err) => finish({ ok: false, detail: err.message }));
    python.on('close', () => {
      try {
        const result = JSON.parse(output.trim());
        if (!result.success) {
          finish({ ok: false, detail: result.error || 'فشل غير محدَّد من executive_brief' });
          return;
        }
        finish({ ok: true, markdown: result.markdown });
      } catch (e) {
        finish({ ok: false, detail: `فشل تحليل ناتج executive_brief: ${e.message}${errOut ? ' — ' + errOut.slice(0, 200) : ''}` });
      }
    });
  });
}

function executiveBriefReportPath(now) {
  return path.join(REPORTS_DIR, `EXECUTIVE_BRIEF_${isoDate(now)}.md`);
}

async function maybeGenerateDailyExecutiveBrief(now = new Date()) {
  const datedPath = executiveBriefReportPath(now);
  if (fs.existsSync(datedPath)) {
    return { action: 'none', detail: `الموجَز التنفيذي اليومي موجود بالفعل: ${path.basename(datedPath)}` };
  }
  const result = await runExecutiveBrief();
  if (!result.ok) {
    return { action: 'failed', detail: result.detail };
  }
  try {
    fs.mkdirSync(REPORTS_DIR, { recursive: true });
    fs.writeFileSync(datedPath, result.markdown, 'utf8');
    return { action: 'generated', detail: `تم إنشاء الموجَز التنفيذي اليومي: ${path.basename(datedPath)}` };
  } catch (err) {
    return { action: 'failed', detail: `فشل حفظ الموجَز التنفيذي: ${err.message}` };
  }
}

// ── EXECUTIVE BRAIN — DAILY DIRECTIVE (ADR-144, 2026-07-30) ──
// The one real path that grows the permanent data/executive_directives.
// jsonl ledger — a live Mission Control view (the 'executive-brain'
// SERVICE_REGISTRY entry) deliberately never records, to avoid a page
// refresh silently duplicating "permanent" knowledge. Chains 3 real
// full-portfolio scans (measured live ~55-60s), so this is gated to once
// per calendar day like every other daily report — never approves,
// rejects, publishes, or reallocates anything; the returned directive is
// a recommendation only, requires_founder_approval is always true.
const EXECUTIVE_DIRECTIVE_DAILY_MARKER = path.join(FACTORY_DIR, 'data', '.executive_directive_daily_marker');

function runGenerateDailyExecutiveDirective({ timeoutMs = 120000, pythonPath } = {}) {
  return new Promise((resolve) => {
    let python;
    try {
      python = spawn(pythonPath || detectPythonForHunter(), [path.join(FACTORY_DIR, 'mission_control_api.py'), 'generate_daily_executive_directive'], { cwd: FACTORY_DIR });
    } catch (err) {
      resolve({ ok: false, detail: `تعذّر تشغيل mission_control_api.py: ${err.message}` });
      return;
    }

    let output = '', errOut = '', settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };
    const timer = setTimeout(() => {
      try { python.kill(); } catch (_) { /* best effort */ }
      finish({ ok: false, detail: `انتهت مهلة generate_daily_executive_directive (${timeoutMs / 1000} ثانية)` });
    }, timeoutMs);

    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', (err) => finish({ ok: false, detail: err.message }));
    python.on('close', () => {
      try {
        const result = JSON.parse(output.trim());
        if (!result.success) {
          finish({ ok: false, detail: result.error || 'فشل غير محدَّد من generate_daily_executive_directive' });
          return;
        }
        finish({ ok: true, status: result.directive && result.directive.status, action: result.current_mission });
      } catch (e) {
        finish({ ok: false, detail: `فشل تحليل ناتج generate_daily_executive_directive: ${e.message}${errOut ? ' — ' + errOut.slice(0, 200) : ''}` });
      }
    });
  });
}

async function maybeGenerateDailyExecutiveDirective(now = new Date()) {
  const today = isoDate(now);
  let lastRun = null;
  try {
    lastRun = fs.readFileSync(EXECUTIVE_DIRECTIVE_DAILY_MARKER, 'utf8').trim();
  } catch (_) { /* no marker yet — first run */ }
  if (lastRun === today) {
    return { action: 'none', detail: `تم إنشاء التوجيه التنفيذي اليومي بالفعل (${today})` };
  }
  const result = await runGenerateDailyExecutiveDirective();
  if (!result.ok) {
    return { action: 'failed', detail: result.detail };
  }
  try {
    fs.mkdirSync(path.dirname(EXECUTIVE_DIRECTIVE_DAILY_MARKER), { recursive: true });
    fs.writeFileSync(EXECUTIVE_DIRECTIVE_DAILY_MARKER, today, 'utf8');
  } catch (err) {
    return { action: 'failed', detail: `فشل حفظ علامة التوجيه التنفيذي: ${err.message}` };
  }
  return { action: 'generated', detail: `تم إنشاء توجيه تنفيذي حقيقي (${result.status}): ${result.action || 'لا إجراء معلَّق'}` };
}

// ── GOLDEN HUNTER — DAILY COMMISSION OPPORTUNITY SCAN (ADR-234, 2026-08-08) ──
// Phase 38b ("Chief Commercial Engineer" directive), Section 12: Golden
// Hunter must periodically discover/verify/score/compare/recommend
// commission opportunities. Reuses commission_engine.py::
// rank_commission_shortlist() directly (no new scoring engine) via the
// same spawn+marker-file daily-gate pattern as every other daily report
// in this file. Read-only: never contacts a prospect, never fabricates
// revenue, never bypasses CEO approval -- the dispatch it calls has no
// side effect beyond this marker write.
const COMMISSION_OPPORTUNITY_SCAN_DAILY_MARKER = path.join(FACTORY_DIR, 'data', '.commission_opportunity_scan_daily_marker');

function runCommissionOpportunityScan({ timeoutMs = 60000, pythonPath } = {}) {
  return new Promise((resolve) => {
    let python;
    try {
      python = spawn(pythonPath || detectPythonForHunter(), [path.join(FACTORY_DIR, 'mission_control_api.py'), 'commission_opportunity_scan'], { cwd: FACTORY_DIR });
    } catch (err) {
      resolve({ ok: false, detail: `تعذّر تشغيل mission_control_api.py: ${err.message}` });
      return;
    }

    let output = '', errOut = '', settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };
    const timer = setTimeout(() => {
      try { python.kill(); } catch (_) { /* best effort */ }
      finish({ ok: false, detail: `انتهت مهلة commission_opportunity_scan (${timeoutMs / 1000} ثانية)` });
    }, timeoutMs);

    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', (err) => finish({ ok: false, detail: err.message }));
    python.on('close', () => {
      try {
        const result = JSON.parse(output.trim());
        if (!result.success) {
          finish({ ok: false, detail: result.error || 'فشل غير محدَّد من commission_opportunity_scan' });
          return;
        }
        finish({ ok: true, best: result.BEST_FIRST_COMMERCIAL_EXPERIMENT, total: result.total_portfolio_size });
      } catch (e) {
        finish({ ok: false, detail: `فشل تحليل ناتج commission_opportunity_scan: ${e.message}${errOut ? ' — ' + errOut.slice(0, 200) : ''}` });
      }
    });
  });
}

async function maybeRunDailyCommissionOpportunityScan(now = new Date()) {
  const today = isoDate(now);
  let lastRun = null;
  try {
    lastRun = fs.readFileSync(COMMISSION_OPPORTUNITY_SCAN_DAILY_MARKER, 'utf8').trim();
  } catch (_) { /* no marker yet — first run */ }
  if (lastRun === today) {
    return { action: 'none', detail: `تم مسح فرص العمولة اليومي بالفعل (${today})` };
  }
  const result = await runCommissionOpportunityScan();
  if (!result.ok) {
    return { action: 'failed', detail: result.detail };
  }
  try {
    fs.mkdirSync(path.dirname(COMMISSION_OPPORTUNITY_SCAN_DAILY_MARKER), { recursive: true });
    fs.writeFileSync(COMMISSION_OPPORTUNITY_SCAN_DAILY_MARKER, today, 'utf8');
  } catch (err) {
    return { action: 'failed', detail: `فشل حفظ علامة مسح فرص العمولة: ${err.message}` };
  }
  return { action: 'generated', detail: `مسح فرص عمولة حقيقي (${result.total} فرصة) — الأفضل: ${result.best || 'لا يوجد مرشَّح مؤهَّل'}` };
}

// ── ENTERPRISE GROWTH ENGINE — DAILY GROWTH STAGE SNAPSHOT (ADR-159, 2026-07-31) ──
// The ONE real write path for Growth Stage history: appends the current
// real Growth Stage to data/growth_stage_snapshots.jsonl. growth_stages.
// py's own classifier (current_growth_stage()) stays exactly as stateless
// as ADR-158 left it — never calls this itself. Same once-per-calendar-
// day pattern as every other daily report above; cheap (a single real
// growth_stages.build_growth_dashboard() call, not the ~70s Strategic
// Planning Dashboard chain).
// Enterprise Evidence Engine (ADR-163) closed a real, disclosed gap
// (ADR-166, ADR-169): reality_audit.audit_all_endpoints()'s own
// record_evidence=True default had never actually been exercised --
// both real callers (enterprise_validation.py, truth_registry.py)
// deliberately pass record_evidence=False to avoid growing the ledger
// on every routine report view. This is the one deliberate real caller
// that DOES record, gated to once per calendar day (a full sequential
// audit is real, measured minutes of work -- no value running it every
// ~10-minute tick), dispatched via a special case in
// mission_control_api.py's main() that is kept OUT of _ENDPOINTS on
// purpose so no other audit pass can ever discover and live-invoke it
// as a side effect (the exact class of bug ADR-162 already taught this
// factory to avoid).
const EVIDENCE_RECORDING_AUDIT_DAILY_MARKER = path.join(FACTORY_DIR, 'data', '.evidence_recording_audit_daily_marker');

function runDailyEvidenceRecordingAudit({ timeoutMs = 600000, pythonPath } = {}) {
  return new Promise((resolve) => {
    let python;
    try {
      python = spawn(pythonPath || detectPythonForHunter(), [path.join(FACTORY_DIR, 'mission_control_api.py'), 'run_daily_evidence_recording_audit'], { cwd: FACTORY_DIR });
    } catch (err) {
      resolve({ ok: false, detail: `تعذّر تشغيل mission_control_api.py: ${err.message}` });
      return;
    }

    let output = '', errOut = '', settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };
    const timer = setTimeout(() => {
      try { python.kill(); } catch (_) { /* best effort */ }
      finish({ ok: false, detail: `انتهت مهلة run_daily_evidence_recording_audit (${timeoutMs / 1000} ثانية)` });
    }, timeoutMs);

    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', (err) => finish({ ok: false, detail: err.message }));
    python.on('close', () => {
      try {
        const result = JSON.parse(output.trim());
        if (!result.success) {
          finish({ ok: false, detail: result.error || 'فشل غير محدَّد من run_daily_evidence_recording_audit' });
          return;
        }
        finish({ ok: true, recorded: result.recorded, reality_score: result.reality_score });
      } catch (e) {
        finish({ ok: false, detail: `فشل تحليل ناتج run_daily_evidence_recording_audit: ${e.message}${errOut ? ' — ' + errOut.slice(0, 200) : ''}` });
      }
    });
  });
}

async function maybeRunDailyEvidenceRecordingAudit(now = new Date()) {
  const today = isoDate(now);
  let lastRun = null;
  try {
    lastRun = fs.readFileSync(EVIDENCE_RECORDING_AUDIT_DAILY_MARKER, 'utf8').trim();
  } catch (_) { /* no marker yet — first run */ }
  if (lastRun === today) {
    return { action: 'none', detail: `تم تسجيل تدقيق الأدلة اليومي بالفعل (${today})` };
  }
  const result = await runDailyEvidenceRecordingAudit();
  if (!result.ok) {
    return { action: 'failed', detail: result.detail };
  }
  try {
    fs.mkdirSync(path.dirname(EVIDENCE_RECORDING_AUDIT_DAILY_MARKER), { recursive: true });
    fs.writeFileSync(EVIDENCE_RECORDING_AUDIT_DAILY_MARKER, today, 'utf8');
  } catch (err) {
    return { action: 'failed', detail: `فشل حفظ علامة تدقيق الأدلة: ${err.message}` };
  }
  const pct = result.reality_score && result.reality_score.percentages;
  return { action: 'generated', detail: `تم تسجيل ${result.recorded} دليل حقيقي — Reality Score: ${pct ? pct.REAL : '؟'}%` };
}

// Pricing Review Trigger (ADR-182, 2026-08-07): founder directive after
// approving Premium-tier ($155) for the EU AI Act Compliance Toolkit --
// "after the first verified customer and testimonials, schedule an
// automatic pricing review" toward Elite tier ($310, already validated
// real). Real, mechanical, daily-gated: only ever notifies once real
// evidence (>=1 real paid customer + >=1 real review) exists, never on
// elapsed time.
const PRICING_REVIEW_DAILY_MARKER = path.join(FACTORY_DIR, 'data', '.eu_ai_act_pricing_review_daily_marker');

function runEuAiActPricingReview({ timeoutMs = 60000, pythonPath } = {}) {
  return new Promise((resolve) => {
    let python;
    try {
      python = spawn(pythonPath || detectPythonForHunter(), [path.join(FACTORY_DIR, 'mission_control_api.py'), 'eu_ai_act_pricing_review'], { cwd: FACTORY_DIR });
    } catch (err) {
      resolve({ ok: false, detail: `تعذّر تشغيل mission_control_api.py: ${err.message}` });
      return;
    }

    let output = '', errOut = '', settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };
    const timer = setTimeout(() => {
      try { python.kill(); } catch (_) { /* best effort */ }
      finish({ ok: false, detail: `انتهت مهلة eu_ai_act_pricing_review (${timeoutMs / 1000} ثانية)` });
    }, timeoutMs);

    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', (err) => finish({ ok: false, detail: err.message }));
    python.on('close', () => {
      try {
        const result = JSON.parse(output.trim());
        if (!result.success) {
          finish({ ok: false, detail: result.error || 'فشل غير محدَّد من eu_ai_act_pricing_review' });
          return;
        }
        finish({ ok: true, ready: result.ready_for_elite_tier_review, evidence: result.evidence, eliteEvaluation: result.elite_tier_evaluation });
      } catch (e) {
        finish({ ok: false, detail: `فشل تحليل ناتج eu_ai_act_pricing_review: ${e.message}${errOut ? ' — ' + errOut.slice(0, 200) : ''}` });
      }
    });
  });
}

async function maybeCheckEuAiActPricingReview(now = new Date()) {
  const today = isoDate(now);
  let lastRun = null;
  try {
    lastRun = fs.readFileSync(PRICING_REVIEW_DAILY_MARKER, 'utf8').trim();
  } catch (_) { /* no marker yet — first run */ }
  if (lastRun === today) {
    return { action: 'none', detail: `تم فحص جاهزية مراجعة التسعير اليوم بالفعل (${today})` };
  }
  const result = await runEuAiActPricingReview();
  if (!result.ok) {
    return { action: 'failed', detail: result.detail };
  }
  try {
    fs.mkdirSync(path.dirname(PRICING_REVIEW_DAILY_MARKER), { recursive: true });
    fs.writeFileSync(PRICING_REVIEW_DAILY_MARKER, today, 'utf8');
  } catch (err) {
    return { action: 'failed', detail: `فشل حفظ علامة مراجعة التسعير: ${err.message}` };
  }
  if (result.ready) {
    telegramDirect.sendTelegramMessage(
      `\u{1F4B0} جاهز لمراجعة تسعير Elite tier\nEU AI Act Compliance Toolkit: ${result.evidence}\nتقييم Elite ($310): ${result.eliteEvaluation ? JSON.stringify(result.eliteEvaluation) : 'غير محسوب'}`
    ).catch(() => {});
    return { action: 'ready', detail: result.evidence };
  }
  return { action: 'not_ready', detail: result.evidence };
}

const GROWTH_STAGE_SNAPSHOT_DAILY_MARKER = path.join(FACTORY_DIR, 'data', '.growth_stage_snapshot_daily_marker');

function runRecordDailyGrowthStageSnapshot({ timeoutMs = 60000, pythonPath } = {}) {
  return new Promise((resolve) => {
    let python;
    try {
      python = spawn(pythonPath || detectPythonForHunter(), [path.join(FACTORY_DIR, 'mission_control_api.py'), 'record_daily_growth_stage_snapshot'], { cwd: FACTORY_DIR });
    } catch (err) {
      resolve({ ok: false, detail: `تعذّر تشغيل mission_control_api.py: ${err.message}` });
      return;
    }

    let output = '', errOut = '', settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };
    const timer = setTimeout(() => {
      try { python.kill(); } catch (_) { /* best effort */ }
      finish({ ok: false, detail: `انتهت مهلة record_daily_growth_stage_snapshot (${timeoutMs / 1000} ثانية)` });
    }, timeoutMs);

    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', (err) => finish({ ok: false, detail: err.message }));
    python.on('close', () => {
      try {
        const result = JSON.parse(output.trim());
        if (!result.success) {
          finish({ ok: false, detail: result.error || 'فشل غير محدَّد من record_daily_growth_stage_snapshot' });
          return;
        }
        finish({ ok: true, stage: result.snapshot && result.snapshot.stage });
      } catch (e) {
        finish({ ok: false, detail: `فشل تحليل ناتج record_daily_growth_stage_snapshot: ${e.message}${errOut ? ' — ' + errOut.slice(0, 200) : ''}` });
      }
    });
  });
}

async function maybeRecordDailyGrowthStageSnapshot(now = new Date()) {
  const today = isoDate(now);
  let lastRun = null;
  try {
    lastRun = fs.readFileSync(GROWTH_STAGE_SNAPSHOT_DAILY_MARKER, 'utf8').trim();
  } catch (_) { /* no marker yet — first run */ }
  if (lastRun === today) {
    return { action: 'none', detail: `تم تسجيل لقطة مرحلة النمو اليومية بالفعل (${today})` };
  }
  const result = await runRecordDailyGrowthStageSnapshot();
  if (!result.ok) {
    return { action: 'failed', detail: result.detail };
  }
  try {
    fs.mkdirSync(path.dirname(GROWTH_STAGE_SNAPSHOT_DAILY_MARKER), { recursive: true });
    fs.writeFileSync(GROWTH_STAGE_SNAPSHOT_DAILY_MARKER, today, 'utf8');
  } catch (err) {
    return { action: 'failed', detail: `فشل حفظ علامة لقطة مرحلة النمو: ${err.message}` };
  }
  return { action: 'generated', detail: `تم تسجيل لقطة مرحلة نمو حقيقية: ${result.stage}` };
}

const COMMERCIAL_READINESS_SNAPSHOT_DAILY_MARKER = path.join(FACTORY_DIR, 'data', '.commercial_readiness_snapshot_daily_marker');

function runRecordDailyCommercialReadinessSnapshot({ timeoutMs = 60000, pythonPath } = {}) {
  return new Promise((resolve) => {
    let python;
    try {
      python = spawn(pythonPath || detectPythonForHunter(), [path.join(FACTORY_DIR, 'mission_control_api.py'), 'record_daily_commercial_readiness_snapshot'], { cwd: FACTORY_DIR });
    } catch (err) {
      resolve({ ok: false, detail: `تعذّر تشغيل mission_control_api.py: ${err.message}` });
      return;
    }

    let output = '', errOut = '', settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };
    const timer = setTimeout(() => {
      try { python.kill(); } catch (_) { /* best effort */ }
      finish({ ok: false, detail: `انتهت مهلة record_daily_commercial_readiness_snapshot (${timeoutMs / 1000} ثانية)` });
    }, timeoutMs);

    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', (err) => finish({ ok: false, detail: err.message }));
    python.on('close', () => {
      try {
        const result = JSON.parse(output.trim());
        if (!result.success) {
          finish({ ok: false, detail: result.error || 'فشل غير محدَّد من record_daily_commercial_readiness_snapshot' });
          return;
        }
        finish({ ok: true, overall: result.snapshot && result.snapshot.overall });
      } catch (e) {
        finish({ ok: false, detail: `فشل تحليل ناتج record_daily_commercial_readiness_snapshot: ${e.message}${errOut ? ' — ' + errOut.slice(0, 200) : ''}` });
      }
    });
  });
}

async function maybeRecordDailyCommercialReadinessSnapshot(now = new Date()) {
  const today = isoDate(now);
  let lastRun = null;
  try {
    lastRun = fs.readFileSync(COMMERCIAL_READINESS_SNAPSHOT_DAILY_MARKER, 'utf8').trim();
  } catch (_) { /* no marker yet — first run */ }
  if (lastRun === today) {
    return { action: 'none', detail: `تم تسجيل لقطة الجاهزية التجارية اليومية بالفعل (${today})` };
  }
  const result = await runRecordDailyCommercialReadinessSnapshot();
  if (!result.ok) {
    return { action: 'failed', detail: result.detail };
  }
  try {
    fs.mkdirSync(path.dirname(COMMERCIAL_READINESS_SNAPSHOT_DAILY_MARKER), { recursive: true });
    fs.writeFileSync(COMMERCIAL_READINESS_SNAPSHOT_DAILY_MARKER, today, 'utf8');
  } catch (err) {
    return { action: 'failed', detail: `فشل حفظ علامة لقطة الجاهزية التجارية: ${err.message}` };
  }
  return { action: 'generated', detail: `تم تسجيل لقطة جاهزية تجارية حقيقية: ${result.overall}` };
}

// ── AUTONOMOUS COMPANY EVOLUTION ENGINE — DAILY INTAKE/SIMULATE/DECIDE ──
// Runs mission_control_api.py's evolution_queue_daily_cycle: real
// proposals get pulled into the Evolution Queue, simulated, and decided
// (routed to AWAITING_FOUNDER_APPROVAL) — never approved, rejected, or
// marked implemented automatically. This is the one concrete code
// enforcement of the founder's explicit "human-gated always" choice for
// Execute, not just a policy note — approve/reject/mark-implemented stay
// exclusively founder-triggered Mission Control actions. Gated to once
// per calendar day via a plain marker file: run_daily_cycle() is
// naturally idempotent (it only ever touches newly-intake proposals,
// per evolution_queue.py's own contract), but there's no real value in
// spawning a Python subprocess every ~10-minute tick when nothing new
// can exist that fast.
const EVOLUTION_QUEUE_DAILY_MARKER = path.join(FACTORY_DIR, 'data', '.evolution_queue_daily_marker');

function runEvolutionQueueDailyCycle({ timeoutMs = 30000, pythonPath } = {}) {
  return new Promise((resolve) => {
    let python;
    try {
      python = spawn(pythonPath || detectPythonForHunter(), [path.join(FACTORY_DIR, 'mission_control_api.py'), 'evolution_queue_daily_cycle'], { cwd: FACTORY_DIR });
    } catch (err) {
      resolve({ ok: false, detail: `تعذّر تشغيل mission_control_api.py: ${err.message}` });
      return;
    }

    let output = '', errOut = '', settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };
    const timer = setTimeout(() => {
      try { python.kill(); } catch (_) { /* best effort */ }
      finish({ ok: false, detail: `انتهت مهلة evolution_queue_daily_cycle (${timeoutMs / 1000} ثانية)` });
    }, timeoutMs);

    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', (err) => finish({ ok: false, detail: err.message }));
    python.on('close', () => {
      try {
        const result = JSON.parse(output.trim());
        if (!result.success) {
          finish({ ok: false, detail: result.error || 'فشل غير محدَّد من evolution_queue_daily_cycle' });
          return;
        }
        finish({ ok: true, added_count: result.added_count, processed: result.processed });
      } catch (e) {
        finish({ ok: false, detail: `فشل تحليل ناتج evolution_queue_daily_cycle: ${e.message}${errOut ? ' — ' + errOut.slice(0, 200) : ''}` });
      }
    });
  });
}

async function maybeGenerateDailyEvolutionQueueIntake(now = new Date()) {
  const today = isoDate(now);
  let lastRun = null;
  try {
    lastRun = fs.readFileSync(EVOLUTION_QUEUE_DAILY_MARKER, 'utf8').trim();
  } catch (_) { /* no marker yet -- first run */ }
  if (lastRun === today) {
    return { action: 'none', detail: `تم تحديث طابور التطوّر اليوم بالفعل (${today})` };
  }
  const result = await runEvolutionQueueDailyCycle();
  if (!result.ok) {
    return { action: 'failed', detail: result.detail };
  }
  try {
    fs.mkdirSync(path.dirname(EVOLUTION_QUEUE_DAILY_MARKER), { recursive: true });
    fs.writeFileSync(EVOLUTION_QUEUE_DAILY_MARKER, today, 'utf8');
  } catch (err) {
    return { action: 'failed', detail: `فشل حفظ علامة طابور التطوّر: ${err.message}` };
  }
  return { action: 'processed', detail: `تمت معالجة ${result.added_count} اقتراح جديد في طابور التطوّر (${result.processed.join(', ') || 'لا شيء'})` };
}

// Autonomous Evolution Engine directive, Round 2 (2026-07-30): "continuously
// measures whether every implemented evolution actually improved" X — the
// real automatic Measure path. Read-only against every decision field
// (approve/reject/mark-implemented stay exclusively founder-triggered);
// only ever appends a dated entry to an IMPLEMENTED record's own
// outcome_measurements. Same once-per-calendar-day gate as the intake
// cycle above — nothing here can produce a meaningfully different real
// reading faster than that.
const EVOLUTION_OUTCOME_DAILY_MARKER = path.join(FACTORY_DIR, 'data', '.evolution_outcome_daily_marker');

function runEvolutionOutcomeMeasurementCycle({ timeoutMs = 30000, pythonPath } = {}) {
  return new Promise((resolve) => {
    let python;
    try {
      python = spawn(pythonPath || detectPythonForHunter(), [path.join(FACTORY_DIR, 'mission_control_api.py'), 'evolution_outcome_daily_cycle'], { cwd: FACTORY_DIR });
    } catch (err) {
      resolve({ ok: false, detail: `تعذّر تشغيل mission_control_api.py: ${err.message}` });
      return;
    }

    let output = '', errOut = '', settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };
    const timer = setTimeout(() => {
      try { python.kill(); } catch (_) { /* best effort */ }
      finish({ ok: false, detail: `انتهت مهلة evolution_outcome_daily_cycle (${timeoutMs / 1000} ثانية)` });
    }, timeoutMs);

    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', (err) => finish({ ok: false, detail: err.message }));
    python.on('close', () => {
      try {
        const result = JSON.parse(output.trim());
        if (!result.success) {
          finish({ ok: false, detail: result.error || 'فشل غير محدَّد من evolution_outcome_daily_cycle' });
          return;
        }
        finish({ ok: true, measured_count: result.measured_count, measured: result.measured, skipped: result.skipped });
      } catch (e) {
        finish({ ok: false, detail: `فشل تحليل ناتج evolution_outcome_daily_cycle: ${e.message}${errOut ? ' — ' + errOut.slice(0, 200) : ''}` });
      }
    });
  });
}

async function maybeMeasureEvolutionOutcomes(now = new Date()) {
  const today = isoDate(now);
  let lastRun = null;
  try {
    lastRun = fs.readFileSync(EVOLUTION_OUTCOME_DAILY_MARKER, 'utf8').trim();
  } catch (_) { /* no marker yet — first run */ }
  if (lastRun === today) {
    return { action: 'none', detail: `تم قياس نتائج التطوّر اليوم بالفعل (${today})` };
  }
  const result = await runEvolutionOutcomeMeasurementCycle();
  if (!result.ok) {
    return { action: 'failed', detail: result.detail };
  }
  try {
    fs.mkdirSync(path.dirname(EVOLUTION_OUTCOME_DAILY_MARKER), { recursive: true });
    fs.writeFileSync(EVOLUTION_OUTCOME_DAILY_MARKER, today, 'utf8');
  } catch (err) {
    return { action: 'failed', detail: `فشل حفظ علامة قياس نتائج التطوّر: ${err.message}` };
  }
  return { action: 'processed', detail: `تم قياس ${result.measured_count} مقترح مُنفَّذ (${result.measured.join(', ') || 'لا شيء'})` };
}

// Final Executive Directive (2026-07-29): "maintain institutional
// knowledge" — knowledge_graph.build_graph() has zero prior callers in
// this tick (confirmed via direct grep before adding this). Pure,
// read-only rebuild from already-real data (decisions.jsonl/market_
// intelligence_analyses.jsonl/sales_ledger.jsonl/ai_cost_log.jsonl),
// persisted via knowledge_graph.build.save_snapshot() (already existed,
// never called until now) — no side effects on any decision, production,
// or publish state. Same once-per-calendar-day gate as the report
// engines above.
const KNOWLEDGE_GRAPH_DAILY_MARKER = path.join(FACTORY_DIR, 'data', '.knowledge_graph_daily_marker');

function runKnowledgeGraphDailySnapshot({ timeoutMs = 30000, pythonPath } = {}) {
  return new Promise((resolve) => {
    let python;
    try {
      python = spawn(pythonPath || detectPythonForHunter(), [path.join(FACTORY_DIR, 'mission_control_api.py'), 'knowledge_graph_daily_snapshot'], { cwd: FACTORY_DIR });
    } catch (err) {
      resolve({ ok: false, detail: `تعذّر تشغيل mission_control_api.py: ${err.message}` });
      return;
    }

    let output = '', errOut = '', settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };
    const timer = setTimeout(() => {
      try { python.kill(); } catch (_) { /* best effort */ }
      finish({ ok: false, detail: `انتهت مهلة knowledge_graph_daily_snapshot (${timeoutMs / 1000} ثانية)` });
    }, timeoutMs);

    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', (err) => finish({ ok: false, detail: err.message }));
    python.on('close', () => {
      try {
        const result = JSON.parse(output.trim());
        if (!result.success) {
          finish({ ok: false, detail: result.error || 'فشل غير محدَّد من knowledge_graph_daily_snapshot' });
          return;
        }
        finish({ ok: true, node_count: result.node_count, edge_count: result.edge_count });
      } catch (e) {
        finish({ ok: false, detail: `فشل تحليل ناتج knowledge_graph_daily_snapshot: ${e.message}${errOut ? ' — ' + errOut.slice(0, 200) : ''}` });
      }
    });
  });
}

async function maybeGenerateDailyKnowledgeGraph(now = new Date()) {
  const today = isoDate(now);
  let lastRun = null;
  try {
    lastRun = fs.readFileSync(KNOWLEDGE_GRAPH_DAILY_MARKER, 'utf8').trim();
  } catch (_) { /* no marker yet — first run */ }
  if (lastRun === today) {
    return { action: 'none', detail: `تم تحديث خريطة المعرفة اليوم بالفعل (${today})` };
  }
  const result = await runKnowledgeGraphDailySnapshot();
  if (!result.ok) {
    return { action: 'failed', detail: result.detail };
  }
  try {
    fs.mkdirSync(path.dirname(KNOWLEDGE_GRAPH_DAILY_MARKER), { recursive: true });
    fs.writeFileSync(KNOWLEDGE_GRAPH_DAILY_MARKER, today, 'utf8');
  } catch (err) {
    return { action: 'failed', detail: `فشل حفظ علامة خريطة المعرفة: ${err.message}` };
  }
  return { action: 'generated', detail: `تم بناء خريطة المعرفة (${result.node_count} عقدة، ${result.edge_count} رابط)` };
}

// Final Executive Directive (2026-07-29): "create business blueprints" —
// autonomous_business_builder.generate_pending_business_blueprints() was
// built earlier the same day with zero automatic wiring (ACTION_REGISTRY-
// only until now). Read-only/no-execution (a blueprint is pure analysis,
// never a publish or spend) — safe to add to the tick without touching
// any of the 4 Founder-protected gates. Capped at a small real batch per
// call (each blueprint costs ~16s real compute) and diffed against
// data/generated_business_blueprints.jsonl inside the Python call itself
// — this wrapper only needs its own once-per-calendar-day gate so a
// ~10-minute tick doesn't re-spawn Python for a cheap, already-empty diff.
const BUSINESS_BLUEPRINT_DAILY_MARKER = path.join(FACTORY_DIR, 'data', '.business_blueprint_daily_marker');

function runGeneratePendingBusinessBlueprints({ timeoutMs = 120000, pythonPath, limit = 2 } = {}) {
  return new Promise((resolve) => {
    let python;
    try {
      python = spawn(pythonPath || detectPythonForHunter(), [path.join(FACTORY_DIR, 'mission_control_api.py'), 'generate_pending_business_blueprints', JSON.stringify({ limit })], { cwd: FACTORY_DIR });
    } catch (err) {
      resolve({ ok: false, detail: `تعذّر تشغيل mission_control_api.py: ${err.message}` });
      return;
    }

    let output = '', errOut = '', settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };
    const timer = setTimeout(() => {
      try { python.kill(); } catch (_) { /* best effort */ }
      finish({ ok: false, detail: `انتهت مهلة generate_pending_business_blueprints (${timeoutMs / 1000} ثانية)` });
    }, timeoutMs);

    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', (err) => finish({ ok: false, detail: err.message }));
    python.on('close', () => {
      try {
        const result = JSON.parse(output.trim());
        if (!result.success) {
          finish({ ok: false, detail: result.error || 'فشل غير محدَّد من generate_pending_business_blueprints' });
          return;
        }
        finish({ ok: true, generated: result.generated, remaining_pending: result.remaining_pending });
      } catch (e) {
        finish({ ok: false, detail: `فشل تحليل ناتج generate_pending_business_blueprints: ${e.message}${errOut ? ' — ' + errOut.slice(0, 200) : ''}` });
      }
    });
  });
}

async function maybeGenerateBusinessBlueprintsForNewAcceptedDecisions(now = new Date()) {
  const today = isoDate(now);
  let lastRun = null;
  try {
    lastRun = fs.readFileSync(BUSINESS_BLUEPRINT_DAILY_MARKER, 'utf8').trim();
  } catch (_) { /* no marker yet — first run */ }
  if (lastRun === today) {
    return { action: 'none', detail: `تم توليد مخططات الأعمال اليوم بالفعل (${today})` };
  }
  const result = await runGeneratePendingBusinessBlueprints();
  if (!result.ok) {
    return { action: 'failed', detail: result.detail };
  }
  try {
    fs.mkdirSync(path.dirname(BUSINESS_BLUEPRINT_DAILY_MARKER), { recursive: true });
    fs.writeFileSync(BUSINESS_BLUEPRINT_DAILY_MARKER, today, 'utf8');
  } catch (err) {
    return { action: 'failed', detail: `فشل حفظ علامة مخططات الأعمال: ${err.message}` };
  }
  const generatedNiches = (result.generated || []).map(g => g.niche).join(', ') || 'لا شيء';
  return { action: 'generated', detail: `تم توليد ${(result.generated || []).length} مخطط أعمال جديد (${generatedNiches}) — المتبقي: ${result.remaining_pending}` };
}

// ── COMMERCIAL EXECUTION ENGINE v1 (ADR-180, 2026-08-06) ──
// Exact mirror of the Business Blueprint auto-generation pattern above:
// every real ACCEPTED decision without an already-recorded real
// commercial launch kit gets one, up to a small real batch per call
// (each kit costs one real Groq call, generate_pending_commercial_kits()
// itself dedups against data/generated_commercial_kits.jsonl) — this
// wrapper only needs its own once-per-calendar-day gate so a
// ~10-minute tick doesn't re-spawn Python for a cheap, already-empty diff.
const COMMERCIAL_KIT_DAILY_MARKER = path.join(FACTORY_DIR, 'data', '.commercial_kit_daily_marker');

function runGeneratePendingCommercialKits({ timeoutMs = 120000, pythonPath, limit = 2 } = {}) {
  return new Promise((resolve) => {
    let python;
    try {
      python = spawn(pythonPath || detectPythonForHunter(), [path.join(FACTORY_DIR, 'mission_control_api.py'), 'generate_pending_commercial_kits', JSON.stringify({ limit })], { cwd: FACTORY_DIR });
    } catch (err) {
      resolve({ ok: false, detail: `تعذّر تشغيل mission_control_api.py: ${err.message}` });
      return;
    }

    let output = '', errOut = '', settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };
    const timer = setTimeout(() => {
      try { python.kill(); } catch (_) { /* best effort */ }
      finish({ ok: false, detail: `انتهت مهلة generate_pending_commercial_kits (${timeoutMs / 1000} ثانية)` });
    }, timeoutMs);

    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', (err) => finish({ ok: false, detail: err.message }));
    python.on('close', () => {
      try {
        const result = JSON.parse(output.trim());
        if (!result.success) {
          finish({ ok: false, detail: result.error || 'فشل غير محدَّد من generate_pending_commercial_kits' });
          return;
        }
        finish({ ok: true, generated: result.generated, remaining_pending: result.remaining_pending });
      } catch (e) {
        finish({ ok: false, detail: `فشل تحليل ناتج generate_pending_commercial_kits: ${e.message}${errOut ? ' — ' + errOut.slice(0, 200) : ''}` });
      }
    });
  });
}

async function maybeGenerateCommercialKitsForNewAcceptedDecisions(now = new Date()) {
  const today = isoDate(now);
  let lastRun = null;
  try {
    lastRun = fs.readFileSync(COMMERCIAL_KIT_DAILY_MARKER, 'utf8').trim();
  } catch (_) { /* no marker yet — first run */ }
  if (lastRun === today) {
    return { action: 'none', detail: `تم توليد حزم تسويق تجارية اليوم بالفعل (${today})` };
  }
  const result = await runGeneratePendingCommercialKits();
  if (!result.ok) {
    return { action: 'failed', detail: result.detail };
  }
  try {
    fs.mkdirSync(path.dirname(COMMERCIAL_KIT_DAILY_MARKER), { recursive: true });
    fs.writeFileSync(COMMERCIAL_KIT_DAILY_MARKER, today, 'utf8');
  } catch (err) {
    return { action: 'failed', detail: `فشل حفظ علامة حزم التسويق: ${err.message}` };
  }
  const generatedNiches = (result.generated || []).map(g => g.niche).join(', ') || 'لا شيء';
  return { action: 'generated', detail: `تم توليد ${(result.generated || []).length} حزمة تسويق تجارية جديدة (${generatedNiches}) — المتبقي: ${result.remaining_pending}` };
}

// ── PADDLE CHECKOUT READINESS NOTIFICATION (CEO Directive, 2026-08-06) ──
// A real, already-built, already-tested function
// (scripts/check_paddle_checkout_status.py::check_and_notify_all()) that
// re-checks Paddle's real account-onboarding status live and sends a
// real Telegram message the moment checkout_ready flips true — existed
// since ADR-085/086 but was never wired into the automatic tick, so
// nobody was actually notified without someone remembering to re-run it
// by hand. Runs every tick (not daily-gated), same "closest thing to
// real-time a scheduler-less factory can offer" reasoning as the
// resilience monitor immediately below: this is the one real external
// gate blocking first revenue, so minimizing detection latency directly
// serves time-to-first-dollar. Safe to run every ~10 minutes — the
// underlying function is a lightweight read + is already idempotent
// (already_notified guards against ever re-sending).
function runCheckPaddleCheckoutStatus({ timeoutMs = 60000, pythonPath } = {}) {
  return new Promise((resolve) => {
    let python;
    try {
      python = spawn(pythonPath || detectPythonForHunter(), [path.join(FACTORY_DIR, 'scripts', 'check_paddle_checkout_status.py'), '--json'], { cwd: FACTORY_DIR });
    } catch (err) {
      resolve({ ok: false, detail: `تعذّر تشغيل check_paddle_checkout_status.py: ${err.message}` });
      return;
    }

    let output = '', errOut = '', settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };
    const timer = setTimeout(() => {
      try { python.kill(); } catch (_) { /* best effort */ }
      finish({ ok: false, detail: `انتهت مهلة check_paddle_checkout_status.py (${timeoutMs / 1000} ثانية)` });
    }, timeoutMs);

    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', (err) => finish({ ok: false, detail: err.message }));
    python.on('close', () => {
      try {
        const result = JSON.parse(output.trim());
        if (!result.success) {
          finish({ ok: false, detail: result.error || 'فشل غير محدَّد من check_paddle_checkout_status.py' });
          return;
        }
        finish({
          ok: true,
          totalProducts: result.total_products,
          newlyReady: result.newly_ready,
        });
      } catch (e) {
        finish({ ok: false, detail: `فشل تحليل ناتج check_paddle_checkout_status.py: ${e.message}${errOut ? ' — ' + errOut.slice(0, 200) : ''}` });
      }
    });

    python.stdin.write('{}');
    python.stdin.end();
  });
}

async function maybeNotifyPaddleCheckoutReady() {
  const result = await runCheckPaddleCheckoutStatus();
  if (!result.ok) {
    return { action: 'failed', detail: result.detail };
  }
  if (result.newlyReady > 0) {
    return { action: 'notified', detail: `Paddle checkout أصبح جاهزاً فعلاً لـ ${result.newlyReady} منتج حقيقي — تم إرسال تنبيه Telegram حقيقي` };
  }
  return { action: 'none', detail: `لا يزال Paddle checkout غير مفعَّل (${result.totalProducts} منتج حقيقي مفحوص) — لا تنبيه جديد` };
}

// ── CONTINUOUS TRUST & RESILIENCE MONITORING ──
// resilience_monitor.py's assess_resilience() + record_incidents_for_
// findings() in one call (mission_control_api.py's resilience_monitor_
// tick). Runs every tick, unlike the daily-gated reports above — see
// the call site's own comment for why "every tick" is the honest
// definition of "real-time" here.

// Enterprise Operations Center (ADR-155, 2026-07-31): pure, side-effect-
// free extraction of "which of this tick's real recorded incidents are
// actually new, high-value alerts worth a Telegram push" -- filters to
// event:'opened' only (a 'resolved' event is good news, not an alert)
// and formats each into buildCriticalErrorMessage()'s expected string
// shape. Extracted as its own function so this real filtering logic is
// unit-testable without spawning a real Python subprocess.
function newIncidentTelegramReasons(recordedIncidents) {
  return (recordedIncidents || [])
    .filter(inc => inc && inc.event === 'opened')
    .map(inc => `${inc.area}: ${inc.detail}`);
}

function runResilienceMonitorTick({ timeoutMs = 30000, pythonPath } = {}) {
  return new Promise((resolve) => {
    let python;
    try {
      python = spawn(pythonPath || detectPythonForHunter(), [path.join(FACTORY_DIR, 'mission_control_api.py'), 'resilience_monitor_tick'], { cwd: FACTORY_DIR });
    } catch (err) {
      resolve({ action: 'failed', detail: `تعذّر تشغيل mission_control_api.py: ${err.message}` });
      return;
    }

    let output = '', errOut = '', settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };
    const timer = setTimeout(() => {
      try { python.kill(); } catch (_) { /* best effort */ }
      finish({ action: 'failed', detail: `انتهت مهلة resilience_monitor_tick (${timeoutMs / 1000} ثانية)` });
    }, timeoutMs);

    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', (err) => finish({ action: 'failed', detail: err.message }));
    python.on('close', () => {
      try {
        const result = JSON.parse(output.trim());
        if (!result.success) {
          finish({ action: 'failed', detail: result.error || 'فشل غير محدَّد من resilience_monitor_tick' });
          return;
        }
        // Enterprise Operations Center (ADR-155, 2026-07-31): "executive
        // notifications, only high-value alerts, no spam." Reuses two
        // already-real pieces verbatim -- resilience_monitor.py's own
        // real severity gate (only critical/emergency ever reaches
        // recorded_incidents) and dedup (an already-open incident is
        // never re-recorded, so this fires once per real new incident,
        // not once per tick) -- and telegramDirect's existing send path
        // + buildCriticalErrorMessage() convention. No new notification
        // infrastructure.
        const reasons = newIncidentTelegramReasons(result.recorded_incidents);
        if (reasons.length > 0) {
          telegramDirect.sendTelegramMessage(telegramDirect.buildCriticalErrorMessage(reasons)).catch(() => {});
        }
        finish({
          action: 'assessed',
          detail: `resilience_score=${result.resilience_score}, تنبيهات نشطة=${result.active_alert_count}, حوادث جديدة مُسجَّلة=${result.recorded_incidents.length}`,
        });
      } catch (e) {
        finish({ action: 'failed', detail: `فشل تحليل ناتج resilience_monitor_tick: ${e.message}${errOut ? ' — ' + errOut.slice(0, 200) : ''}` });
      }
    });
  });
}

// ── CUSTOMER PAYMENT STATUS CHECK ──
// Revenue Mode directive (2026-07-31): "check-customer-payments" (Customer
// Platform Round 3, 2026-07-29) has existed as a real, tested, ACTION_
// REGISTRY-only manual trigger since it shipped -- "the one-click-away
// manual trigger until real payment completion is wired to a webhook" per
// its own server.js comment. No webhook exists yet (would need a public
// endpoint + Paddle-side configuration, out of scope here), but wiring the
// existing real function into the tick removes the *human* step: the
// instant a real customer's Paddle transaction completes, the next tick
// (not the next time someone remembers to click a button) confirms it,
// generates the real invoice, and fires the founder Telegram notification
// that already lives inside check_payment_status() itself -- zero new
// notification code needed here. Runs every tick, not daily-gated, same
// as resilience_monitor above: payment confirmation latency directly
// affects real customer experience once real revenue exists, unlike the
// daily reports where a once-a-day cadence is genuinely sufficient.
function runPaymentStatusCheckTick({ timeoutMs = 30000, pythonPath } = {}) {
  return new Promise((resolve) => {
    let python;
    try {
      python = spawn(pythonPath || detectPythonForHunter(), [path.join(FACTORY_DIR, 'mission_control_api.py'), 'check_customer_payments'], { cwd: FACTORY_DIR });
    } catch (err) {
      resolve({ action: 'failed', detail: `تعذّر تشغيل mission_control_api.py: ${err.message}` });
      return;
    }

    let output = '', errOut = '', settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };
    const timer = setTimeout(() => {
      try { python.kill(); } catch (_) { /* best effort */ }
      finish({ action: 'failed', detail: `انتهت مهلة check_customer_payments (${timeoutMs / 1000} ثانية)` });
    }, timeoutMs);

    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', (err) => finish({ action: 'failed', detail: err.message }));
    python.on('close', () => {
      try {
        const result = JSON.parse(output.trim());
        if (!result.success) {
          finish({ action: 'failed', detail: result.error || 'فشل غير محدَّد من check_customer_payments' });
          return;
        }
        const paidCount = (result.checked || []).filter(c => c.already_paid).length;
        finish({
          action: 'checked',
          detail: `تم فحص ${result.checked_count || 0} طلب بانتظار الدفع، ${paidCount} دفعة حقيقية مؤكَّدة الآن`,
        });
      } catch (e) {
        finish({ action: 'failed', detail: `فشل تحليل ناتج check_customer_payments: ${e.message}${errOut ? ' — ' + errOut.slice(0, 200) : ''}` });
      }
    });
  });
}

// ── SELF-AWARENESS ──
// CONSTITUTION.md §20. self_awareness.js is a plain Node module — required
// directly (no subprocess needed, unlike market_hunter.py). Gated to once
// per calendar day: the growth comparison itself is day-over-day, so
// running it more often than daily produces the same "same as an hour ago"
// result and just wastes a health round-trip.
async function maybeRunSelfAwareness(now = new Date()) {
  const today = isoDate(now);
  const history = selfAwareness.readGrowthLog();
  const lastDate = history.length ? history[history.length - 1].date : null;
  if (lastDate === today) {
    return { action: 'none', detail: `تم تقييم الوعي الذاتي اليوم بالفعل (${today})` };
  }
  try {
    const assessment = await selfAwareness.runDailyAwareness(now);
    return { action: 'assessed', detail: assessment.verdict };
  } catch (err) {
    return { action: 'failed', detail: `فشل تقييم الوعي الذاتي: ${err.message}` };
  }
}

// ── WEEKLY REPORT ──
// "Every Sunday at 00:00" is the nominal trigger, but a 10-minute-tick loop
// can't guarantee it's alive at that exact instant (restarts, maintenance).
// So the actual rule implemented is: "on any tick that falls on a Sunday, if
// this week's report file doesn't exist yet, generate it" — this covers the
// literal Sunday-at-midnight case (the first tick after 00:00 will do it)
// while also self-healing if the process happened to be down exactly then,
// rather than silently skipping that week's report forever.
function isoDate(d) { return d.toISOString().slice(0, 10); }

function weekReportPath(now) {
  return path.join(REPORTS_DIR, `WEEK_${isoDate(now)}.md`);
}

function booksProducedSince(sinceMs) {
  if (!fs.existsSync(BOOKS_DIR)) return [];
  // Recover real titles for Scout-generated books from scout_runs.log where
  // possible; anything else (manually generated books) falls back to a
  // title derived from its filename — the only identifier guaranteed to
  // exist for every book regardless of how it was produced.
  const titleByFile = {};
  for (const e of readScoutLog()) {
    if (e.context === 'success' && e.brief && e.book && e.book.file) {
      titleByFile[e.book.file] = e.brief.title;
    }
  }
  const files = fs.readdirSync(BOOKS_DIR).filter(f => f.toLowerCase().endsWith('.pdf'));
  const recent = [];
  for (const f of files) {
    let mtimeMs;
    try { mtimeMs = fs.statSync(path.join(BOOKS_DIR, f)).mtimeMs; } catch (_) { continue; }
    if (mtimeMs >= sinceMs) {
      const title = titleByFile[f] || f.replace(/\.pdf$/i, '').replace(/_/g, ' ');
      recent.push({ file: f, title });
    }
  }
  return recent;
}

function revenueSince(sinceMs) {
  const empty = { totalKDP: 0, totalEtsy: 0, totalGumroad: 0, total: 0, count: 0 };
  if (!fs.existsSync(FINANCE_FILE)) return empty;
  let data;
  try {
    data = JSON.parse(fs.readFileSync(FINANCE_FILE, 'utf8'));
  } catch (err) {
    return { ...empty, note: `finance_data.json فاسد وقت إعداد التقرير: ${err.message}` };
  }
  const sales = Array.isArray(data.sales) ? data.sales : [];
  const recentSales = sales.filter(s => {
    const t = Date.parse(s.date);
    return Number.isFinite(t) && t >= sinceMs;
  });
  const sum = (platform) => recentSales.filter(s => s.platform === platform).reduce((a, s) => a + (Number(s.amount) || 0), 0);
  return {
    totalKDP: sum('KDP'),
    totalEtsy: sum('Etsy'),
    totalGumroad: sum('Gumroad'),
    total: recentSales.reduce((a, s) => a + (Number(s.amount) || 0), 0),
    count: recentSales.length,
  };
}

function healingActionsSince(sinceMs) {
  if (!fs.existsSync(LOOP_LOG)) return { totalTicks: 0, actions: [] };
  const lines = fs.readFileSync(LOOP_LOG, 'utf8').split('\n').filter(Boolean);
  const recentTicks = [];
  const actions = [];
  for (const line of lines) {
    let entry;
    try { entry = JSON.parse(line); } catch (_) { continue; }
    const t = Date.parse(entry.timestamp);
    if (!Number.isFinite(t) || t < sinceMs) continue;
    recentTicks.push(entry);
    for (const a of (entry.actions || [])) {
      if (a.action && a.action !== 'none') {
        actions.push({ timestamp: entry.timestamp, step: a.step, action: a.action, detail: a.detail });
      }
    }
  }
  return { totalTicks: recentTicks.length, actions };
}

function readOpportunities() {
  if (!fs.existsSync(OPPORTUNITIES_FILE)) return null; // honestly absent, not invented
  try {
    const text = fs.readFileSync(OPPORTUNITIES_FILE, 'utf8').trim();
    return text || null;
  } catch (_) {
    return null;
  }
}

function buildRecommendations({ health, books, revenue, healing }) {
  const recs = [];
  if (health.status && health.status !== 'healthy') {
    recs.push(`حالة المصنع الحالية "${health.status}" — راجع /health لمعرفة أي مكون متعطّل قبل الأسبوع القادم.`);
  }
  if (books.length === 0) {
    recs.push('لم يُنتَج أي كتاب هذا الأسبوع — تحقّق من عمل Scout ومن استجابة Groq (قد تكون هناك قيود معدّل/rate limit).');
  } else if (books.length < 3) {
    recs.push(`إنتاج منخفض هذا الأسبوع (${books.length} كتاب فقط) — فكّر بزيادة وتيرة تشغيل Scout.`);
  }
  if (revenue.total === 0) {
    recs.push('لا إيرادات مسجَّلة هذا الأسبوع — تذكَّر تسجيل المبيعات عبر Dashboard، أو راجع استراتيجية النشر/التسعير.');
  }
  const healedCount = healing.actions.filter(a => a.action === 'healed').length;
  const failedCount = healing.actions.filter(a => a.action === 'failed').length;
  const warningCount = healing.actions.filter(a => a.action === 'warning').length;
  if (failedCount > 0) {
    recs.push(`فشلت ${failedCount} محاولة إصلاح ذاتي هذا الأسبوع — راجع factory_loop.log لمعرفة التفاصيل.`);
  }
  if (warningCount > 2) {
    recs.push(`n8n كان غير متاح بشكل متكرر (${warningCount} مرة) هذا الأسبوع — تحقّق من استقرار خدمة n8n.`);
  }
  if (healedCount > 0 && failedCount === 0) {
    recs.push(`نجحت كل محاولات الإصلاح الذاتي (${healedCount}) — النظام يعمل كما هو مصمَّم.`);
  }
  if (!recs.length) {
    recs.push('لا توصيات خاصة — الأسبوع كان مستقراً.');
  }
  return recs;
}

function updateFactoryStatusWithReport(dateStr, reportFilename, stats) {
  // FACTORY_STATUS.md belongs to the Knowledge Base task ([7]) — this only
  // appends a row to it and never creates or restructures the file, so a
  // missing FACTORY_STATUS.md is left alone rather than reinvented here.
  if (!fs.existsSync(FACTORY_STATUS_FILE)) return;
  try {
    let content = fs.readFileSync(FACTORY_STATUS_FILE, 'utf8');
    const row = `| ${dateStr} | ${stats.books} | $${stats.revenue.toFixed(2)} | ${stats.healed} | [${reportFilename}](./reports/${reportFilename}) |`;
    const sectionMarker = '## 5. Weekly Reports';
    // A row for this exact date may already exist (e.g. --force re-running
    // the same day's report) — replace it in place instead of duplicating.
    const existingRowRe = new RegExp(`^\\|\\s*${dateStr}\\s*\\|.*\\|\\s*$`, 'm');

    if (content.includes(sectionMarker)) {
      if (existingRowRe.test(content)) {
        content = content.replace(existingRowRe, row);
      } else {
        const headerRe = /(\|\s*التاريخ\s*\|[^\n]*\|\s*\n\|[-\s|]+\|\s*\n)/;
        content = headerRe.test(content)
          ? content.replace(headerRe, `$1${row}\n`)
          : content.trimEnd() + `\n${row}\n`;
      }
    } else {
      content = content.trimEnd() + `\n\n${sectionMarker}\n\n` +
        'تقارير أسبوعية تلقائية من `factory_loop.js` (Task [10]) — صف جديد يُضاف تلقائياً بعد كل تقرير.\n\n' +
        '| التاريخ | كتب | إيرادات | إصلاحات ذاتية | التقرير |\n' +
        '|---|---|---|---|---|\n' +
        `${row}\n`;
    }
    fs.writeFileSync(FACTORY_STATUS_FILE, content, 'utf8');
  } catch (err) {
    appendLoopLog({ diagnosis: { status: 'loop_error' }, actions: [{ step: 'update_factory_status', action: 'error', detail: err.message }] });
  }
}

async function generateWeeklyReport(diagnosis, now, { pythonPath } = {}) {
  const sinceMs = now.getTime() - WEEK_MS;
  const health = diagnosis.reachable ? diagnosis.health : { status: 'unreachable', error: diagnosis.error };

  const books = booksProducedSince(sinceMs);
  const revenue = revenueSince(sinceMs);
  const healing = healingActionsSince(sinceMs);
  const opportunities = readOpportunities();
  const recommendations = buildRecommendations({ health, books, revenue, healing });
  const executiveReport = await runExportExecutiveReport({ pythonPath });

  const dateStr = isoDate(now);
  const lines = [];
  lines.push('# تقرير Galaxy Forge الأسبوعي');
  lines.push('');
  lines.push(`**تاريخ التقرير:** ${dateStr}`);
  lines.push(`**الفترة المشمولة:** آخر 7 أيام (منذ ${isoDate(new Date(sinceMs))})`);
  lines.push('');
  lines.push('## 1. حالة المصنع');
  lines.push(`**الحالة العامة:** ${health.status}`);
  if (health.checks) {
    for (const [name, c] of Object.entries(health.checks)) {
      lines.push(`- **${name}**: ${c.ok ? '✅' : '❌'} ${c.detail}`);
    }
  } else if (health.error) {
    lines.push(`- تعذّر الوصول للسيرفر وقت إعداد التقرير: ${health.error}`);
  }
  lines.push('');
  lines.push('## 2. الكتب المُنتَجة هذا الأسبوع');
  lines.push(`**العدد:** ${books.length}`);
  if (books.length) {
    for (const b of books) lines.push(`- ${b.title} (\`${b.file}\`)`);
  } else {
    lines.push('- لا يوجد كتب جديدة هذا الأسبوع.');
  }
  lines.push('');
  lines.push('## 3. الفرص المكتشَفة');
  lines.push(opportunities || 'لا يوجد ملف `OPPORTUNITIES.md` بعد — لا فرص مسجَّلة للعرض.');
  lines.push('');
  lines.push('## 4. الإيرادات هذا الأسبوع');
  lines.push(`- **KDP:** $${revenue.totalKDP.toFixed(2)}`);
  lines.push(`- **Etsy:** $${revenue.totalEtsy.toFixed(2)}`);
  lines.push(`- **Gumroad:** $${revenue.totalGumroad.toFixed(2)}`);
  lines.push(`- **الإجمالي:** $${revenue.total.toFixed(2)} (${revenue.count} عملية بيع)`);
  if (revenue.note) lines.push(`- ⚠️ ${revenue.note}`);
  lines.push('');
  lines.push('## 5. إجراءات الإصلاح الذاتي');
  lines.push(`- عدد دورات factory_loop المسجَّلة هذا الأسبوع: ${healing.totalTicks}`);
  if (healing.actions.length) {
    for (const a of healing.actions) {
      lines.push(`- [${a.timestamp}] ${a.step}: **${a.action}** — ${a.detail}`);
    }
  } else {
    lines.push('- لا إجراءات إصلاح ذاتي مسجَّلة هذا الأسبوع (كل شيء كان سليماً أو الحلقة لم تعمل).');
  }
  lines.push('');
  lines.push('## 6. توصيات الأسبوع القادم');
  for (const r of recommendations) lines.push(`- ${r}`);
  lines.push('');
  lines.push('## 7. التقرير التنفيذي الموحّد (Executive / Strategic / Validation / Revenue)');
  if (executiveReport.ok) {
    lines.push(executiveReport.markdown);
  } else {
    lines.push(`- ⚠️ تعذّر إنشاء التقرير التنفيذي الموحّد هذا الأسبوع: ${executiveReport.detail}`);
  }
  lines.push('');

  const content = lines.join('\n');

  fs.mkdirSync(REPORTS_DIR, { recursive: true });
  const datedPath = weekReportPath(now);
  fs.writeFileSync(datedPath, content, 'utf8');
  fs.writeFileSync(WEEKLY_REPORT_STABLE, content, 'utf8'); // stable "latest" pointer

  updateFactoryStatusWithReport(dateStr, path.basename(datedPath), {
    books: books.length,
    revenue: revenue.total,
    healed: healing.actions.filter(a => a.action === 'healed').length,
  });

  return { datedPath, stablePath: WEEKLY_REPORT_STABLE };
}

async function maybeGenerateWeeklyReport(diagnosis, now = new Date()) {
  if (now.getDay() !== 0) {
    return { action: 'none', detail: 'ليس يوم الأحد — لا تقرير أسبوعي في هذه الدورة' };
  }
  const datedPath = weekReportPath(now);
  if (fs.existsSync(datedPath)) {
    return { action: 'none', detail: `تقرير هذا الأسبوع موجود بالفعل: ${path.basename(datedPath)}` };
  }
  try {
    const { datedPath: p } = await generateWeeklyReport(diagnosis, now);
    return { action: 'generated', detail: `تم إنشاء التقرير الأسبوعي: ${path.basename(p)}` };
  } catch (err) {
    return { action: 'failed', detail: `فشل إنشاء التقرير الأسبوعي: ${err.message}` };
  }
}

// ── ONE TICK ──
// Operational Resilience Architecture §3/§4 (Phase A, 2026-07-18): marks
// the named step as in-flight in data/factory_state.json before it runs.
// This is the missing persisted "how far did the tick get" signal —
// tickRunning (safeTick, below) is in-memory only and loses this on a
// crash. Best-effort (factory_state's own functions never throw) — a
// disk error here must never affect the real tick.
function markStep(step) {
  factoryState.setCurrentTask('golden_hunter_tick', step);
}

// Unified Recovery System §3 (2026-07-18): replays every currently-due
// retry. `telegram_notify:*` entries carry enough stored context
// (payload/webhookUrl/envVarName) to be genuinely resent — a failed
// replay re-enqueues itself with an incremented attempt via
// notifyN8nProductionEvent()'s own existing enqueueRetry call, so the
// backoff schedule keeps escalating rather than resetting.
//
// `arm_publish:*`/`groq_generation` entries have no stored replay
// context yet in this pass — genuinely replaying a specific publish or
// regeneration needs the original product/request captured too, a
// real, separate follow-up (documented in DISASTER_RECOVERY_PLAN.md's
// Unified Recovery System section) rather than something guessed at
// here. They are still counted and reported via retry_queue_status —
// never silently dropped from view, just not auto-replayed yet.
async function processPendingRetries() {
  const beforeCount = factoryState.loadState().pending_retries.length;
  const due = factoryState.dueRetries();
  let replayed = 0;

  for (const retry of due) {
    if (retry.task.startsWith('telegram_notify:') && retry.context && retry.context.payload) {
      factoryState.clearRetry(retry.task);
      // Called via the module object (not the destructured const above)
      // so a test can mock it directly -- see tests/test_process_pending_retries.js.
      const result = await n8nNotify.notifyN8nProductionEvent(retry.context.payload, {
        webhookUrl: retry.context.webhookUrl,
        envVarName: retry.context.envVarName,
        attempt: (retry.attempt || 1) + 1,
      }).catch(() => null);
      if (result && result.success) replayed++;
    }
  }

  const stillPending = factoryState.loadState().pending_retries;
  // Only notify when the queue's size actually changed since before this
  // pass — a queue that stays at a constant size across many ticks (e.g.
  // one entry with no replay context yet) must never spam the founder
  // every ~10 minutes.
  if (stillPending.length !== beforeCount) {
    notifyFactoryRecoveryEvent(buildRetryQueueStatusPayload(stillPending)).catch(() => {});
  }
  return { processed: due.length, replayed, still_pending: stillPending.length };
}

// Stale-job recovery (CTO+COO audit closure 2026-08-15, Phase 11): arm_publish
// and groq_generation retries carry no replay context and are never replayed
// (dangerous publish = human gate, by design). That meant they accumulated in
// pending_retries forever, silently filling the queue. This expires entries
// past RETRY_STALE_TTL_MS that the processor cannot and must not replay, and
// archives each to data/recovery_actions.jsonl so the decision is auditable.
const RETRY_STALE_TTL_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

function isUnreplayableRetry(task) {
  return task.startsWith('arm_publish:') || task.startsWith('groq_generation');
}

async function expireStaleRetries() {
  const state = factoryState.loadState();
  const pending = state.pending_retries || [];
  const now = Date.now();
  let expired = 0;
  for (const retry of pending) {
    if (!isUnreplayableRetry(retry.task)) continue;
    const queued = Date.parse(retry.queued_at || '');
    if (Number.isNaN(queued)) continue;
    if (now - queued >= RETRY_STALE_TTL_MS) {
      factoryState.clearRetry(retry.task);
      appendRecoveryAction({
        event_type: 'stale_retry_expired',
        component: retry.task,
        error: retry.last_error || 'no replay context; unreplayable by design',
        retry: retry.attempt || 1,
        fallback: 'expired',
        recoverable: false,
        status: 'EXPIRED',
        queued_at: retry.queued_at,
        timestamp: new Date(now).toISOString(),
      });
      expired++;
    }
  }
  return { expired };
}

function appendRecoveryAction(record) {
  try {
    const dir = path.join(FACTORY_DIR, 'data');
    fs.mkdirSync(dir, { recursive: true });
    fs.appendFileSync(path.join(dir, 'recovery_actions.jsonl'), JSON.stringify(record) + '\n', 'utf8');
  } catch (err) {
    console.error('[factory_loop] appendRecoveryAction failed:', err.message);
  }
}

async function runTick() {
  markStep('process_retries');
  await processPendingRetries();
  await expireStaleRetries();

  markStep('diagnose');
  const diagnosis = await diagnose();
  const actions = [];

  if (diagnosis.reachable) {
    // Global Trust & Resilience Layer, Round 1 (2026-07-29): a real
    // health snapshot every tick (cheap append, unlike the daily-gated
    // reports below) -- this factory's own health-trend history, so
    // detectHealthDegradation() (lib/health_trend.js) has real readings
    // to compare instead of only ever seeing the current instant.
    markStep('health_snapshot');
    healthTrend.recordHealthSnapshot(diagnosis.health.status);

    markStep('heal_finance');
    actions.push({ step: 'heal_finance', ...healFinance(diagnosis.health) });

    markStep('heal_books_empty');
    const healBooksResult = await healEmptyBooks(true);
    const { distribution: healBooksDistribution, ...healBooksAction } = healBooksResult;
    actions.push({ step: 'heal_books_empty', ...healBooksAction });
    if (healBooksDistribution) {
      actions.push({ step: 'distribute', ...formatDistributionAction(healBooksDistribution) });
    }

    actions.push({ step: 'heal_n8n', ...healN8n(diagnosis.health) });

    markStep('sales_poll');
    actions.push({ step: 'sales_poll', ...(await pollSales(true)) });

    markStep('hunt');
    const huntResult = await hunt(true);
    const { distribution: huntDistribution, ...huntAction } = huntResult;
    actions.push({ step: 'hunt', ...huntAction });
    if (huntDistribution) {
      actions.push({ step: 'distribute', ...formatDistributionAction(huntDistribution) });
    }

    markStep('golden_hunter_bridge');
    const goldenResult = await huntGolden(true);
    const { distribution: goldenDistribution, ...goldenAction } = goldenResult;
    actions.push({ step: 'golden_hunter_bridge', ...goldenAction });
    if (goldenDistribution) {
      actions.push({ step: 'distribute', ...formatDistributionAction(goldenDistribution) });
    }
  } else {
    actions.push({
      step: 'diagnose',
      action: 'failed',
      detail: `تعذّر الوصول لـ ${DASHBOARD_URL}/health: ${diagnosis.error} — تخطي HEAL/HUNT هذه الدورة`,
    });
  }

  // Runs regardless of reachability — every data source it needs (books/,
  // finance_data.json, factory_loop.log, OPPORTUNITIES.md) is a direct
  // filesystem read; only the health section degrades to "unreachable" if
  // the dashboard happened to be down at the time.
  markStep('weekly_report');
  actions.push({ step: 'weekly_report', ...(await maybeGenerateWeeklyReport(diagnosis)) });

  // EOS Phase 2, Autonomous Recommendations (2026-07-19): same
  // once-per-calendar-day pattern as Golden Hunter's own
  // maybeRunMarketHunter() below — a standalone local Python call, runs
  // regardless of dashboard reachability.
  markStep('evolution_report');
  actions.push({ step: 'evolution_report', ...(await maybeGenerateDailyEvolutionReport()) });

  // Company Evolution Protocol V1 (ADR-173, 2026-08-05): the directive's
  // own "monthly" cadence -- once-per-calendar-month gate, same file-
  // existence technique as every daily/weekly report above, just a wider
  // window. Runs regardless of dashboard reachability, same as
  // evolution_report immediately above.
  markStep('galaxy_evolution_report');
  actions.push({ step: 'galaxy_evolution_report', ...(await maybeGenerateMonthlyGalaxyEvolutionReport()) });

  // Galaxy Forge Executive Constitution (ADR-177, 2026-08-06): the
  // directive's own "quarterly architecture review" and "annual
  // strategic review" cadences -- genuinely new gates, same
  // once-per-calendar-window technique widened further.
  markStep('architecture_review_quarterly');
  actions.push({ step: 'architecture_review_quarterly', ...(await maybeGenerateQuarterlyArchitectureReview()) });
  markStep('annual_strategic_review');
  actions.push({ step: 'annual_strategic_review', ...(await maybeGenerateAnnualStrategicReview()) });

  // Executive Intelligence Core, Round 1 (2026-07-29): same once-per-
  // calendar-day pattern as evolution_report immediately above -- these
  // two report engines already had the real render_markdown()/dispatch
  // shape, just never had the daily tick wiring evolution_report/
  // self_awareness already do.
  markStep('ai_doctor_report');
  actions.push({ step: 'ai_doctor_report', ...(await maybeGenerateDailyAiDoctorReport()) });

  markStep('department_health_report');
  actions.push({ step: 'department_health_report', ...(await maybeGenerateDailyDepartmentHealthReport()) });

  // Strategic Intelligence Core (2026-07-29): same once-per-calendar-day
  // pattern as the two report engines immediately above — a strategic-
  // level report (Executive Brief), not a per-tick monitor like
  // resilience_monitor below.
  markStep('executive_brief');
  actions.push({ step: 'executive_brief', ...(await maybeGenerateDailyExecutiveBrief()) });

  // Golden Hunter — Daily Commission Opportunity Scan (ADR-234, 2026-08-08):
  // same once-per-calendar-day pattern as the report engines around it.
  // Read-only discover/verify/score/compare/recommend -- never contacts a
  // prospect, never bypasses CEO approval.
  markStep('commission_opportunity_scan');
  actions.push({ step: 'commission_opportunity_scan', ...(await maybeRunDailyCommissionOpportunityScan()) });

  // Autonomous Company Evolution Engine, Round 4 (2026-07-29): same
  // once-per-calendar-day pattern as the two report engines immediately
  // above — intake/simulate/decide only, never approve/reject/mark-
  // implemented (those stay exclusively founder-triggered).
  markStep('evolution_queue_intake');
  actions.push({ step: 'evolution_queue_intake', ...(await maybeGenerateDailyEvolutionQueueIntake()) });

  // Autonomous Evolution Engine directive, Round 2 (2026-07-30): the real
  // automatic Measure path — never approves/rejects/marks-implemented,
  // only appends a dated measurement to an already-IMPLEMENTED record.
  markStep('evolution_outcome_measurement');
  actions.push({ step: 'evolution_outcome_measurement', ...(await maybeMeasureEvolutionOutcomes()) });

  // Executive Brain (ADR-144, 2026-07-30): runs last among the daily
  // report/measurement steps above so it arbitrates over today's freshest
  // evolution-queue/outcome state. Same once-per-calendar-day pattern —
  // never approves/rejects/publishes/reallocates anything, only appends
  // a recommendation to the permanent ledger.
  markStep('executive_directive');
  actions.push({ step: 'executive_directive', ...(await maybeGenerateDailyExecutiveDirective()) });

  // Enterprise Growth Engine (ADR-159, 2026-07-31): runs after the
  // executive directive step so it records the freshest real Growth
  // Stage each day. Same once-per-calendar-day pattern — never called
  // from growth_stages.py's own stateless classifier.
  markStep('growth_stage_snapshot');
  actions.push({ step: 'growth_stage_snapshot', ...(await maybeRecordDailyGrowthStageSnapshot()) });

  // Commercial Readiness historical trend (ADR-200, 2026-08-07): closes
  // EVOLUTION_SCORE.md's disclosed gap ("no real per-company historical
  // readiness score exists") — same once-per-calendar-day snapshot
  // pattern as growth_stage_snapshot immediately above.
  markStep('commercial_readiness_snapshot');
  actions.push({ step: 'commercial_readiness_snapshot', ...(await maybeRecordDailyCommercialReadinessSnapshot()) });

  // Enterprise Evidence Engine (ADR-163) daily recording pass (2026-08-07):
  // the only real caller of reality_audit.audit_all_endpoints(record_evidence=True),
  // gated once per calendar day. See runDailyEvidenceRecordingAudit's own
  // comment for why this is dispatched outside _ENDPOINTS.
  markStep('evidence_recording_audit');
  actions.push({ step: 'evidence_recording_audit', ...(await maybeRunDailyEvidenceRecordingAudit()) });

  // Pricing Review Trigger (ADR-182, 2026-08-07): once per calendar day,
  // checks whether the EU AI Act Compliance Toolkit has earned a real,
  // evidence-backed Elite-tier pricing review. Never fires on elapsed
  // time -- only ever notifies once a real paid customer AND a real
  // review both exist.
  markStep('eu_ai_act_pricing_review');
  actions.push({ step: 'eu_ai_act_pricing_review', ...(await maybeCheckEuAiActPricingReview()) });

  // Final Executive Directive (2026-07-29): same once-per-calendar-day
  // pattern as the report engines above — the 2 confirmed-safe, genuinely
  // new autonomy additions ("maintain institutional knowledge" +
  // "create business blueprints"), see the two functions' own docstrings
  // for why each is safe to run without founder gating.
  markStep('knowledge_graph_snapshot');
  actions.push({ step: 'knowledge_graph_snapshot', ...(await maybeGenerateDailyKnowledgeGraph()) });

  markStep('business_blueprint_generation');
  actions.push({ step: 'business_blueprint_generation', ...(await maybeGenerateBusinessBlueprintsForNewAcceptedDecisions()) });

  // Commercial Execution Engine v1 (ADR-180, 2026-08-06): same real,
  // capped, dedup'd auto-generation discipline as the business-blueprint
  // step immediately above -- every real ACCEPTED decision without a
  // commercial launch kit gets one automatically, never triggered from
  // inside executive_brain.py itself (that only cites the real pending
  // count, read-only).
  markStep('commercial_kit_generation');
  actions.push({ step: 'commercial_kit_generation', ...(await maybeGenerateCommercialKitsForNewAcceptedDecisions()) });

  // Paddle Checkout Readiness Notification (CEO Directive, 2026-08-06):
  // every tick, not daily-gated -- this is the one real external gate
  // blocking first revenue today, so minimizing detection latency
  // directly serves time-to-first-dollar. Never publishes, never
  // transacts -- a real, idempotent read + an already-approved
  // Telegram notification channel this factory already uses for dozens
  // of other real events.
  markStep('paddle_checkout_notification');
  actions.push({ step: 'paddle_checkout_notification', ...(await maybeNotifyPaddleCheckoutReady()) });

  // Continuous Trust & Resilience Monitoring (2026-07-29): runs every
  // tick, not daily-gated — this is meant to be the closest thing to
  // "real-time" a scheduler-less factory can honestly offer, same
  // reasoning healthTrend.recordHealthSnapshot() above already uses.
  // Monitor + Classify + Learn only — never calls trigger_emergency_
  // stop()/mark_subsystem_unstable() itself; those stay exclusively
  // founder-triggered Mission Control actions.
  markStep('resilience_monitor');
  actions.push({ step: 'resilience_monitor', ...(await runResilienceMonitorTick()) });

  // Revenue Mode directive (2026-07-31): every tick, not daily-gated, same
  // reasoning as resilience_monitor above — a real customer's payment
  // confirmation latency should be one tick, not "whenever someone next
  // opens Mission Control." check_payment_status() already fires the real
  // founder Telegram notification itself; this step only removes the
  // human click that used to be required to trigger the check at all.
  markStep('payment_status_check');
  actions.push({ step: 'payment_status_check', ...(await runPaymentStatusCheckTick()) });

  // Golden Hunter also runs regardless of dashboard reachability — it's a
  // standalone local Python process, not an HTTP call to the dashboard.
  markStep('golden_hunter');
  actions.push({ step: 'golden_hunter', ...(await maybeRunMarketHunter()) });

  // Self-Awareness also runs regardless of reachability — an unreachable
  // dashboard is itself an honest, reportable vital sign (see
  // self_awareness.js's own health.reachable field), not a reason to skip.
  markStep('self_awareness');
  actions.push({ step: 'self_awareness', ...(await maybeRunSelfAwareness()) });

  // Pending-review notification (Human-in-the-Loop, HIGH_VALUE_EXECUTION_
  // PLAN.md) — a plain filesystem count, runs regardless of reachability.
  // reviewWasActive captured BEFORE the call so a real desktop
  // notification only fires on the actual transition into "needs review"
  // (never repeated every ~10min tick while already flagged).
  markStep('pending_review');
  const reviewWasActive = fs.existsSync(NEEDS_REVIEW_FILE);
  const pendingReviewResult = checkPendingReview();
  actions.push({ step: 'pending_review', ...pendingReviewResult });
  if (!reviewWasActive && fs.existsSync(NEEDS_REVIEW_FILE)) {
    sendDesktopNotification('📝 Galaxy Forge needs review', 'New drafts are waiting in pending_review/queue/.');
    notifyFactoryRecoveryEvent(buildPendingReviewNeededPayload(countPendingReviewDrafts())).catch(() => {});
  }

  factoryState.clearCurrentTask();

  appendLoopLog({
    diagnosis: diagnosis.reachable
      ? { status: diagnosis.health.status, checks: diagnosis.health.checks }
      : { status: 'unreachable', error: diagnosis.error },
    actions,
  });

  const attentionWasActive = fs.existsSync(NEEDS_ATTENTION_FILE);
  const attentionReasons = checkNeedsAttention(actions);
  if (attentionReasons.length) {
    writeNeedsAttention(attentionReasons);
    if (!attentionWasActive) {
      sendDesktopNotification('⚠️ Galaxy Forge needs attention', attentionReasons[0]);
      // ADR-085: "Errors" was ADR-073's third named-but-unwired Telegram
      // category (NEEDS_ATTENTION.md/sendDesktopNotification existed, but
      // neither reached Telegram). Direct send, only on the same
      // newly-active transition as the desktop toast above — never
      // re-sent every tick while the same condition stays flagged.
      telegramDirect.sendTelegramMessage(telegramDirect.buildCriticalErrorMessage(attentionReasons)).catch(() => {});
    }
  } else {
    clearNeedsAttention();
  }

  return { diagnosis, actions };
}

// Absolute safety net: whatever happens inside a tick, the loop itself must
// never die and must never let an exception escape to crash this process
// (let alone the dashboard, which is a separate process entirely).
//
// Zero-assumption audit follow-up — Medium-High finding, fixed: setInterval
// does not wait for an async callback to resolve before scheduling the
// next call. Summing this tick's own real per-step timeouts (health 5s +
// sales_poll ~45s + market_hunter.py 60s x2 (hunt + golden_hunter) +
// generate-book 180s + distribute 140s) shows a single real tick can
// plausibly approach or exceed the 10-minute INTERVAL_MS once real
// (non-dry-run) generation/distribution calls start firing — this has
// never been observed only because FACTORY_AUTO_PRODUCE has been off for
// this factory's entire history. Once it's turned on, two concurrent
// runTick() calls would each independently evaluate huntGolden()/
// goldenNicheAlreadyAttempted() — a real window for duplicate production/
// distribution and duplicate Groq spend. This in-process guard closes it.
let tickRunning = false;

// tickFn defaults to the real runTick — parameterized (same pattern as
// acquireLock's lockFile/exitFn) purely so a test can inject a slow fake
// tick and verify the overlap guard without ever running a real tick's
// actual Groq/network calls.
async function safeTick(tickFn = runTick) {
  if (tickRunning) {
    appendLoopLog({
      diagnosis: { status: 'tick_skipped_overlap' },
      actions: [{ step: 'tick', action: 'skipped', detail: 'previous tick still running — overlap guard' }],
    });
    return;
  }
  tickRunning = true;
  try {
    await tickFn();
  } catch (err) {
    appendLoopLog({
      diagnosis: { status: 'loop_error' },
      actions: [{ step: 'tick', action: 'error', detail: err && err.message ? err.message : String(err) }],
    });
  } finally {
    tickRunning = false;
  }
}

// Manual/testing entry point: force a weekly report right now regardless of
// day-of-week (the real schedule only fires it on Sunday — see
// maybeGenerateWeeklyReport). Still respects the existing-file idempotency
// check unless --force is also given, so it won't clobber a report already
// generated for the current calendar date.
async function forceWeeklyReport(force) {
  const now = new Date();
  const datedPath = weekReportPath(now);
  if (fs.existsSync(datedPath) && !force) {
    console.log(`[factory_loop] report for today already exists: ${datedPath} (use --force to overwrite)`);
    return;
  }
  const diagnosis = await diagnose();
  const { datedPath: p } = await generateWeeklyReport(diagnosis, now);
  console.log(`[factory_loop] weekly report generated: ${p}`);
}

function main() {
  const wasStaleLock = acquireLock();

  const once = process.argv.includes('--once');
  const forceReportIdx = process.argv.indexOf('--weekly-report');

  if (forceReportIdx !== -1) {
    forceWeeklyReport(process.argv.includes('--force')).catch(err => {
      console.error('[factory_loop] --weekly-report failed:', err.message);
      process.exitCode = 1;
    });
    return;
  }

  // Unified Recovery System §2 (2026-07-18): a stale reclaimed lock means
  // the previous instance died uncleanly — classify whether it's safe to
  // resume automatically before starting the tick loop at all.
  const startup = checkStartupSafety(wasStaleLock);

  if (startup.classification === 'NEEDS_CONFIRMATION') {
    console.log(`[factory_loop] NEEDS_CONFIRMATION: ${startup.reason} — tick loop is NOT starting until confirmed via Mission Control (confirm-safe-to-resume action)`);
    writeNeedsAttention([`استرجاع يحتاج تأكيد: ${startup.reason}`]);
    notifyFactoryRecoveryEvent(buildFactoryStoppedUnexpectedlyPayload(startup.reason, startup.current_task)).catch(() => {});
    return;
  }

  if (startup.classification === 'RECOVERING') {
    console.log(`[factory_loop] RECOVERING: ${startup.reason}`);
    notifyFactoryRecoveryEvent(buildFactoryRecoveredPayload(startup.reason, startup.current_task)).catch(() => {});
  }

  console.log(`[factory_loop] starting — dashboard=${DASHBOARD_URL}, interval=${INTERVAL_MS / 60000}min${once ? ' (--once)' : ''}`);

  safeTick().then(() => {
    if (once) {
      console.log('[factory_loop] --once tick complete, exiting.');
      return;
    }
    setInterval(safeTick, INTERVAL_MS);
    console.log('[factory_loop] running — a tick will fire every 10 minutes.');
  });
}

// Enterprise Upgrade Roadmap Phase 1.1 (2026-07-23) — real bug found
// live while testing server.js's own new SIGINT/SIGTERM handlers: these
// process.on() registrations below used to run unconditionally at
// require() time, not gated behind require.main === module the way
// main() already is. server.js requires this file only for two
// functions (readLastGenerationRecord, getButterPrice) — but requiring
// it also silently registered THIS module's SIGINT/SIGTERM/
// uncaughtException/unhandledRejection handlers inside server.js's own
// process. Because these were registered first (factory_loop is
// required near the top of server.js), Node ran this SIGINT/SIGTERM
// handler before server.js's own newer one ever got a chance to run,
// and — worse — releaseLock() released THIS module's PID lockfile
// (meant to detect a duplicate real `node factory_loop.js` process)
// from inside server.js's process, which is never actually the real
// factory_loop process. If a real, separate `node factory_loop.js` were
// running at the same time, stopping server.js could have silently
// released factory_loop's own lock out from under it. Gating this
// behind the same require.main === module check main() already uses
// fixes both: these handlers now only ever attach in factory_loop.js's
// own real, standalone process, never as a side effect of another
// module requiring it as a library.
if (require.main === module) {
  // Belt-and-suspenders: catch anything that somehow still escapes a
  // tick (e.g. an error thrown from inside a timer callback), so the
  // loop process itself stays alive indefinitely instead of needing a
  // human to restart it.
  process.on('unhandledRejection', (err) => {
    appendLoopLog({ diagnosis: { status: 'loop_error' }, actions: [{ step: 'unhandledRejection', action: 'error', detail: String(err) }] });
  });
  process.on('uncaughtException', (err) => {
    appendLoopLog({ diagnosis: { status: 'loop_error' }, actions: [{ step: 'uncaughtException', action: 'error', detail: String(err) }] });
  });

  // Release the PID lockfile on every exit path — normal exit, Ctrl+C,
  // or a kill signal — so a clean shutdown never leaves a stale lock
  // behind for the next startup to have to detect-and-reclaim.
  //
  // Unified Recovery System §2 (2026-07-18) — real bug found while
  // verifying the new startup-safety check: Node's 'exit' event passes
  // the process's exit CODE as its listener's first argument. Passing
  // releaseLock directly made every natural exit call releaseLock(0) —
  // colliding with releaseLock(lockFile = LOCK_FILE)'s own first
  // parameter, so fs.unlinkSync(0) silently failed (caught by its own
  // empty catch) and the lock was NEVER actually released on ANY exit
  // path, clean or not. This made Safe Startup Detection unusable —
  // every restart looked like a crash. Wrapped in a no-arg arrow so the
  // real default path is always used.
  process.on('SIGINT', () => { releaseLock(); process.exit(0); });
  process.on('SIGTERM', () => { releaseLock(); process.exit(0); });
  process.on('exit', () => releaseLock());

  main();
}

module.exports = {
  runTick, healFinance, healEmptyBooks, healN8n, hunt, diagnose,
  generateWeeklyReport, maybeGenerateWeeklyReport, weekReportPath, runExportExecutiveReport,
  runEvolutionReport, evolutionReportPath, maybeGenerateDailyEvolutionReport,
  runGalaxyEvolutionReport, galaxyEvolutionReportPath, maybeGenerateMonthlyGalaxyEvolutionReport,
  runEnterpriseValidationReportQuarterly, architectureReviewReportPath, maybeGenerateQuarterlyArchitectureReview,
  runStrategicPlanningReportAnnual, annualStrategicReviewReportPath, maybeGenerateAnnualStrategicReview,
  runAiDoctorReport, aiDoctorReportPath, maybeGenerateDailyAiDoctorReport,
  runDepartmentHealthReport, departmentHealthReportPath, maybeGenerateDailyDepartmentHealthReport,
  runExecutiveBrief, executiveBriefReportPath, maybeGenerateDailyExecutiveBrief,
  runEvolutionQueueDailyCycle, maybeGenerateDailyEvolutionQueueIntake,
  runEvolutionOutcomeMeasurementCycle, maybeMeasureEvolutionOutcomes,
  runGenerateDailyExecutiveDirective, maybeGenerateDailyExecutiveDirective,
  runCommissionOpportunityScan, maybeRunDailyCommissionOpportunityScan,
  runRecordDailyGrowthStageSnapshot, maybeRecordDailyGrowthStageSnapshot,
  runRecordDailyCommercialReadinessSnapshot, maybeRecordDailyCommercialReadinessSnapshot,
  runDailyEvidenceRecordingAudit, maybeRunDailyEvidenceRecordingAudit,
  runEuAiActPricingReview, maybeCheckEuAiActPricingReview,
  runKnowledgeGraphDailySnapshot, maybeGenerateDailyKnowledgeGraph,
  runGeneratePendingBusinessBlueprints, maybeGenerateBusinessBlueprintsForNewAcceptedDecisions,
  runResilienceMonitorTick, newIncidentTelegramReasons, runPaymentStatusCheckTick,
  booksProducedSince, revenueSince, healingActionsSince,
  recordRejectedNiche, readRejectedNiches, isNicheRejected, summarizeInspectionFailure,
  maybeRunMarketHunter, maybeRunSelfAwareness,
  readLastGenerationRecord, triggerDistribute, triggerGenerateBook, formatDistributionAction, pollSales,
  huntGolden, readGoldenOpportunities, pickTopGoldenOpportunity, briefFromGoldenOpportunity,
  appendGoldenHunterEvent, readGoldenHunterEvents, goldenNicheAlreadyAttempted,
  evaluateGoldenOpportunities, getButterPrice, getOpportunityScore, getLadderOpportunityScore,
  checkProductionEngineHealth,
  checkNeedsAttention, writeNeedsAttention, clearNeedsAttention, checkGoldenStagnation,
  checkPendingAiCeoDecision,
  checkPendingReview, countPendingReviewDrafts, writeNeedsReview, clearNeedsReview,
  acquireLock, releaseLock, isPidAlive, LOCK_FILE,
  safeTick,
  sendDesktopNotification,
  notifyGoldenHunterAccepted,
  notifyFactoryRecoveryEvent,
  processPendingRetries,
  expireStaleRetries,
};

#!/usr/bin/env node
/**
 * OpenClaw Factory — Self-Healing Loop (Task [8])
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
const { spawn, execSync } = require('child_process');
const selfAwareness = require('./self_awareness');

const FACTORY_DIR = __dirname;
const DASHBOARD_URL = process.env.DASHBOARD_URL || 'http://localhost:3000';
const INTERVAL_MS = 10 * 60 * 1000; // 10 minutes

const LOOP_LOG = path.join(FACTORY_DIR, 'factory_loop.log');
const SCOUT_LOG = path.join(FACTORY_DIR, 'scout_runs.log');
const FINANCE_FILE = path.join(FACTORY_DIR, 'finance_data.json');
const BOOKS_DIR = path.join(FACTORY_DIR, 'books');
const GENERATION_LOG_FILE = path.join(BOOKS_DIR, '_generation_log.jsonl');
const GOLDEN_JSON_FILE = path.join(FACTORY_DIR, 'golden_opportunities.json');
const GOLDEN_HUNTER_EVENTS_FILE = path.join(FACTORY_DIR, 'data', 'golden_hunter_events.jsonl');
const GOLDEN_FRESHNESS_MS = 24 * 60 * 60 * 1000; // ADR-009: >24h old = stale, skip without failing

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

function acquireLock() {
  try {
    if (fs.existsSync(LOCK_FILE)) {
      const existingPid = parseInt(fs.readFileSync(LOCK_FILE, 'utf8').trim(), 10);
      if (Number.isFinite(existingPid) && isPidAlive(existingPid)) {
        console.log(`[factory_loop] another factory_loop running (PID ${existingPid}), exiting`);
        process.exit(0);
      }
      // Stale lock (owning process is gone, or the file is unreadable/
      // corrupt) — fall through and reclaim it below.
    }
    fs.writeFileSync(LOCK_FILE, String(process.pid));
  } catch (err) {
    // Disk full, permissions, etc. — never let the lockfile itself block
    // startup; worst case this run just isn't guarded against a duplicate.
    console.error('[factory_loop] lockfile check failed, continuing without guard:', err.message);
  }
}

function releaseLock() {
  try {
    fs.unlinkSync(LOCK_FILE);
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
      headers: { 'Content-Type': 'application/json' },
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

async function triggerGenerateBook(brief) {
  try {
    const res = await fetchWithTimeout(`${DASHBOARD_URL}/generate-book`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: brief.title,
        topic: brief.topic,
        chapters: brief.chapters,
        audience: brief.audience,
        price: brief.price,
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

function appendGoldenHunterEvent(fields, logPath = GOLDEN_HUNTER_EVENTS_FILE) {
  try {
    fs.mkdirSync(path.dirname(logPath), { recursive: true });
    const record = { timestamp: new Date().toISOString(), ...fields };
    fs.appendFileSync(logPath, JSON.stringify(record) + '\n');
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

// Builds a /generate-book-compatible brief straight from a scored
// opportunity — bypasses Scout's free-association Groq prompt entirely,
// since the niche is already real, tested data from profit_oracle.py, not
// something to re-invent. The price is NOT taken from opportunity.
// recommended_price directly (see getButterPrice() above) — it always goes
// through butter_price(), with a fail-safe floor-clamp if that call itself
// fails for any reason (never silently use an unchecked, possibly
// sub-floor, raw price).
async function briefFromGoldenOpportunity(opportunity, butterOpts = {}) {
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

async function generateWeeklyReport(diagnosis, now) {
  const sinceMs = now.getTime() - WEEK_MS;
  const health = diagnosis.reachable ? diagnosis.health : { status: 'unreachable', error: diagnosis.error };

  const books = booksProducedSince(sinceMs);
  const revenue = revenueSince(sinceMs);
  const healing = healingActionsSince(sinceMs);
  const opportunities = readOpportunities();
  const recommendations = buildRecommendations({ health, books, revenue, healing });

  const dateStr = isoDate(now);
  const lines = [];
  lines.push('# تقرير OpenClaw Factory الأسبوعي');
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
async function runTick() {
  const diagnosis = await diagnose();
  const actions = [];

  if (diagnosis.reachable) {
    actions.push({ step: 'heal_finance', ...healFinance(diagnosis.health) });

    const healBooksResult = await healEmptyBooks(true);
    const { distribution: healBooksDistribution, ...healBooksAction } = healBooksResult;
    actions.push({ step: 'heal_books_empty', ...healBooksAction });
    if (healBooksDistribution) {
      actions.push({ step: 'distribute', ...formatDistributionAction(healBooksDistribution) });
    }

    actions.push({ step: 'heal_n8n', ...healN8n(diagnosis.health) });

    const huntResult = await hunt(true);
    const { distribution: huntDistribution, ...huntAction } = huntResult;
    actions.push({ step: 'hunt', ...huntAction });
    if (huntDistribution) {
      actions.push({ step: 'distribute', ...formatDistributionAction(huntDistribution) });
    }

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
  actions.push({ step: 'weekly_report', ...(await maybeGenerateWeeklyReport(diagnosis)) });

  // Golden Hunter also runs regardless of dashboard reachability — it's a
  // standalone local Python process, not an HTTP call to the dashboard.
  actions.push({ step: 'golden_hunter', ...(await maybeRunMarketHunter()) });

  // Self-Awareness also runs regardless of reachability — an unreachable
  // dashboard is itself an honest, reportable vital sign (see
  // self_awareness.js's own health.reachable field), not a reason to skip.
  actions.push({ step: 'self_awareness', ...(await maybeRunSelfAwareness()) });

  appendLoopLog({
    diagnosis: diagnosis.reachable
      ? { status: diagnosis.health.status, checks: diagnosis.health.checks }
      : { status: 'unreachable', error: diagnosis.error },
    actions,
  });

  return { diagnosis, actions };
}

// Absolute safety net: whatever happens inside a tick, the loop itself must
// never die and must never let an exception escape to crash this process
// (let alone the dashboard, which is a separate process entirely).
async function safeTick() {
  try {
    await runTick();
  } catch (err) {
    appendLoopLog({
      diagnosis: { status: 'loop_error' },
      actions: [{ step: 'tick', action: 'error', detail: err && err.message ? err.message : String(err) }],
    });
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
  acquireLock();

  const once = process.argv.includes('--once');
  const forceReportIdx = process.argv.indexOf('--weekly-report');

  if (forceReportIdx !== -1) {
    forceWeeklyReport(process.argv.includes('--force')).catch(err => {
      console.error('[factory_loop] --weekly-report failed:', err.message);
      process.exitCode = 1;
    });
    return;
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

// Belt-and-suspenders: catch anything that somehow still escapes a tick
// (e.g. an error thrown from inside a timer callback), so the loop process
// itself stays alive indefinitely instead of needing a human to restart it.
process.on('unhandledRejection', (err) => {
  appendLoopLog({ diagnosis: { status: 'loop_error' }, actions: [{ step: 'unhandledRejection', action: 'error', detail: String(err) }] });
});
process.on('uncaughtException', (err) => {
  appendLoopLog({ diagnosis: { status: 'loop_error' }, actions: [{ step: 'uncaughtException', action: 'error', detail: String(err) }] });
});

// Release the PID lockfile on every exit path — normal exit, Ctrl+C, or a
// kill signal — so a clean shutdown never leaves a stale lock behind for
// the next startup to have to detect-and-reclaim.
process.on('SIGINT', () => { releaseLock(); process.exit(0); });
process.on('SIGTERM', () => { releaseLock(); process.exit(0); });
process.on('exit', releaseLock);

if (require.main === module) {
  main();
}

module.exports = {
  runTick, healFinance, healEmptyBooks, healN8n, hunt, diagnose,
  generateWeeklyReport, maybeGenerateWeeklyReport, weekReportPath,
  booksProducedSince, revenueSince, healingActionsSince,
  recordRejectedNiche, readRejectedNiches, isNicheRejected, summarizeInspectionFailure,
  maybeRunMarketHunter, maybeRunSelfAwareness,
  readLastGenerationRecord, triggerDistribute, triggerGenerateBook, formatDistributionAction,
  huntGolden, readGoldenOpportunities, pickTopGoldenOpportunity, briefFromGoldenOpportunity,
  appendGoldenHunterEvent, readGoldenHunterEvents, goldenNicheAlreadyAttempted,
  evaluateGoldenOpportunities, getButterPrice,
};

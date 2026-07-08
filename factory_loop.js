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

const FACTORY_DIR = __dirname;
const DASHBOARD_URL = process.env.DASHBOARD_URL || 'http://localhost:3000';
const INTERVAL_MS = 10 * 60 * 1000; // 10 minutes

const LOOP_LOG = path.join(FACTORY_DIR, 'factory_loop.log');
const SCOUT_LOG = path.join(FACTORY_DIR, 'scout_runs.log');
const FINANCE_FILE = path.join(FACTORY_DIR, 'finance_data.json');
const BOOKS_DIR = path.join(FACTORY_DIR, 'books');
const REPORTS_DIR = path.join(FACTORY_DIR, 'reports');
const WEEKLY_REPORT_STABLE = path.join(FACTORY_DIR, 'FACTORY_WEEKLY_REPORT.md');
const OPPORTUNITIES_FILE = path.join(FACTORY_DIR, 'OPPORTUNITIES.md');
const FACTORY_STATUS_FILE = path.join(FACTORY_DIR, 'FACTORY_STATUS.md');
const REJECTED_NICHES_FILE = path.join(FACTORY_DIR, 'REJECTED_NICHES.md');
const WEEK_MS = 7 * 24 * 60 * 60 * 1000;
const REJECTION_COOLDOWN_MS = WEEK_MS;

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
    // Record it so the circuit breaker can recognize this niche next time.
    if (data.success && data.published === false) {
      const reason = summarizeInspectionFailure(data.inspection);
      recordRejectedNiche(brief.topic, brief.title, reason);
      return { ok: false, rejected: true, detail: `تم التوليد لكن رُفض النشر (Dual Inspection): ${reason}` };
    }

    return {
      ok: !!data.success,
      detail: data.success ? `تم توليد الكتاب: ${data.filename} (${data.pages} صفحة)` : `فشل التوليد: ${data.error}`,
    };
  } catch (err) {
    return { ok: false, detail: `فشل الاتصال بـ /generate-book: ${err.message}` };
  }
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
  };
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
    actions.push({ step: 'heal_books_empty', ...(await healEmptyBooks(true)) });
    actions.push({ step: 'heal_n8n', ...healN8n(diagnosis.health) });
    actions.push({ step: 'hunt', ...(await hunt(true)) });
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

if (require.main === module) {
  main();
}

module.exports = {
  runTick, healFinance, healEmptyBooks, healN8n, hunt, diagnose,
  generateWeeklyReport, maybeGenerateWeeklyReport, weekReportPath,
  booksProducedSince, revenueSince, healingActionsSince,
  recordRejectedNiche, readRejectedNiches, isNicheRejected, summarizeInspectionFailure,
};

#!/usr/bin/env node
/**
 * OpenClaw Factory — Self-Awareness Engine
 *
 * Per OPENCLAW_OS_CONSTITUTION.md's North Star ("the factory must become
 * smarter every single day") and CONSTITUTION.md §20 (Self-Awareness): the
 * factory has cells (Scout, profit_oracle, market_hunter, inspectors, the
 * circuit breaker, the Knowledge Brain) but nothing that looks at all of
 * them together and says, honestly, how the whole is doing.
 *
 * This module answers exactly one question: "How am I doing, truthfully?"
 * Truth over flattery — every function here is built to be able to report
 * bad news. There is no code path that forces a positive verdict.
 *
 * Usage:
 *   node self_awareness.js --run      # compute today's assessment, append to GROWTH_LOG.md
 *   node self_awareness.js --check    # compute and print today's assessment, no write
 */

const fs = require('fs');
const path = require('path');
const knowledgeBrain = require('./knowledge_brain');

const FACTORY_DIR = __dirname;
const DASHBOARD_URL = process.env.DASHBOARD_URL || 'http://localhost:3000';

const GROWTH_LOG = path.join(FACTORY_DIR, 'GROWTH_LOG.md');
const REJECTED_NICHES_FILE = path.join(FACTORY_DIR, 'REJECTED_NICHES.md');
const QUARANTINE_FILE = path.join(FACTORY_DIR, 'QUARANTINE.md');
const INSPECTIONS_LOG = path.join(FACTORY_DIR, 'inspections.log');
const HUNTER_LOG = path.join(FACTORY_DIR, 'market_hunter_runs.log');
const GOLDEN_JSON = path.join(FACTORY_DIR, 'golden_opportunities.json');
const LESSONS_DIR = path.join(FACTORY_DIR, 'OpenClaw_Brain', '19_Lessons_Learned');

const PIPELINE_FRESHNESS_MS = 48 * 60 * 60 * 1000; // "flowing" = active within 48h

// ── UTIL ──

function isoDate(d) { return d.toISOString().slice(0, 10); }

async function fetchWithTimeout(url, ms = 5000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  try {
    return await fetch(url, { signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

function countBlocks(filePath, marker) {
  if (!fs.existsSync(filePath)) return 0;
  const content = fs.readFileSync(filePath, 'utf8');
  const matches = content.match(new RegExp(`^${marker}`, 'gm'));
  return matches ? matches.length : 0;
}

function lastJsonlTimestamp(filePath) {
  if (!fs.existsSync(filePath)) return null;
  const lines = fs.readFileSync(filePath, 'utf8').split('\n').filter(Boolean);
  if (!lines.length) return null;
  try {
    const last = JSON.parse(lines[lines.length - 1]);
    const t = Date.parse(last.timestamp);
    return Number.isFinite(t) ? t : null;
  } catch (_) {
    return null;
  }
}

// ── VITAL SIGNS ──

async function getHealth() {
  try {
    const res = await fetchWithTimeout(`${DASHBOARD_URL}/health`);
    const data = await res.json();
    return { reachable: true, status: data.status, checks: data.checks || {} };
  } catch (err) {
    return { reachable: false, status: 'unreachable', checks: {}, error: err.message };
  }
}

function countLessons() {
  if (!fs.existsSync(LESSONS_DIR)) return 0;
  return fs.readdirSync(LESSONS_DIR)
    .filter(f => f.toLowerCase().endsWith('.md') && f.toLowerCase() !== 'readme.md')
    .length;
}

function getGoldenOpportunitiesCount() {
  if (!fs.existsSync(GOLDEN_JSON)) return 0;
  try {
    const data = JSON.parse(fs.readFileSync(GOLDEN_JSON, 'utf8'));
    return Array.isArray(data.results) ? data.results.length : 0;
  } catch (_) {
    return 0;
  }
}

// Dual Inspection's butter_price pass rate over the most recent N runs —
// the real, checkable signal for "are prices staying $30+", not an assumption.
function getButterCompliance(limit = 20) {
  if (!fs.existsSync(INSPECTIONS_LOG)) return null;
  const lines = fs.readFileSync(INSPECTIONS_LOG, 'utf8').split('\n').filter(Boolean).slice(-limit);
  let total = 0, passed = 0;
  for (const line of lines) {
    try {
      const entry = JSON.parse(line);
      const check = entry.commercial && entry.commercial.checks &&
        entry.commercial.checks.find(c => c.name === 'butter_price');
      if (check) {
        total++;
        if (check.passed) passed++;
      }
    } catch (_) { /* skip a malformed line */ }
  }
  return total ? { total, passed, rate: Math.round((passed / total) * 100) } : null;
}

function getDualInspectionPassRate(limit = 20) {
  if (!fs.existsSync(INSPECTIONS_LOG)) return null;
  const lines = fs.readFileSync(INSPECTIONS_LOG, 'utf8').split('\n').filter(Boolean).slice(-limit);
  let total = 0, passed = 0;
  for (const line of lines) {
    try {
      const entry = JSON.parse(line);
      total++;
      if (entry.passed) passed++;
    } catch (_) { /* skip */ }
  }
  return total ? { total, passed, rate: Math.round((passed / total) * 100) } : null;
}

// "Golden pipeline flowing" — real recency checks on each stage's own log,
// not an assumption that because code exists, it's running.
function checkGoldenPipeline(now) {
  const nowMs = now.getTime();
  const freshness = (filePath, label) => {
    if (!fs.existsSync(filePath)) {
      return { flowing: false, reason: `${label}: لا سجل موجود بعد` };
    }
    const t = lastJsonlTimestamp(filePath);
    if (t === null) {
      return { flowing: false, reason: `${label}: السجل فارغ أو غير قابل للقراءة` };
    }
    const ageHours = Math.round((nowMs - t) / (60 * 60 * 1000));
    const flowing = (nowMs - t) <= PIPELINE_FRESHNESS_MS;
    return {
      flowing,
      reason: flowing
        ? `${label}: آخر نشاط منذ ${ageHours} ساعة`
        : `${label}: راكد منذ ${ageHours} ساعة (الحد: 48)`,
    };
  };

  return {
    hunter: freshness(HUNTER_LOG, 'market_hunter'),
    inspectors: freshness(INSPECTIONS_LOG, 'inspectors'),
    // profit_oracle doesn't keep its own JSONL log — golden_opportunities.json's
    // generated_at is the real signal of when it last actually ran.
    oracle: (() => {
      if (!fs.existsSync(GOLDEN_JSON)) return { flowing: false, reason: 'profit_oracle: golden_opportunities.json غير موجود' };
      try {
        const data = JSON.parse(fs.readFileSync(GOLDEN_JSON, 'utf8'));
        const t = Date.parse(data.generated_at);
        if (!Number.isFinite(t)) return { flowing: false, reason: 'profit_oracle: تاريخ غير صالح' };
        const ageHours = Math.round((nowMs - t) / (60 * 60 * 1000));
        const flowing = (nowMs - t) <= PIPELINE_FRESHNESS_MS;
        return { flowing, reason: flowing ? `profit_oracle: آخر تشغيل منذ ${ageHours} ساعة` : `profit_oracle: راكد منذ ${ageHours} ساعة` };
      } catch (_) {
        return { flowing: false, reason: 'profit_oracle: golden_opportunities.json غير قابل للقراءة' };
      }
    })(),
  };
}

async function computeVitalSigns(now) {
  const health = await getHealth();
  const brainMap = knowledgeBrain.getBrainMap();
  return {
    timestamp: now.toISOString(),
    health,
    knowledge_entries: brainMap.totalMarkdownFiles || 0,
    lessons_learned: countLessons(),
    golden_opportunities: getGoldenOpportunitiesCount(),
    rejected_niches: countBlocks(REJECTED_NICHES_FILE, '## 🚫'),
    quarantine_entries: countBlocks(QUARANTINE_FILE, '## 🚫'),
    butter_compliance: getButterCompliance(),
    dual_inspection: getDualInspectionPassRate(),
    golden_pipeline: checkGoldenPipeline(now),
  };
}

// ── GROWTH LOG (daily snapshots) ──

const GROWTH_ROW_RE = /^\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*([^|]*)\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)%?\s*\|\s*(\d+)\s*\|/;

function readGrowthLog() {
  if (!fs.existsSync(GROWTH_LOG)) return [];
  const rows = [];
  for (const line of fs.readFileSync(GROWTH_LOG, 'utf8').split('\n')) {
    const m = line.match(GROWTH_ROW_RE);
    if (m) {
      rows.push({
        date: m[1],
        status: m[2].trim(),
        knowledge_entries: parseInt(m[3], 10),
        lessons_learned: parseInt(m[4], 10),
        golden_opportunities: parseInt(m[5], 10),
        dual_inspection_pass_rate: parseInt(m[6], 10),
        rejected_niches: parseInt(m[7], 10),
      });
    }
  }
  return rows;
}

function writeGrowthRow(vitals, now) {
  const today = isoDate(now);
  const row = `| ${today} | ${vitals.health.status} | ${vitals.knowledge_entries} | ${vitals.lessons_learned} | ` +
    `${vitals.golden_opportunities} | ${vitals.dual_inspection ? vitals.dual_inspection.rate : 0}% | ${vitals.rejected_niches} |`;

  const header = '# 📈 GROWTH_LOG — هل المصنع أذكى من الأمس؟\n\n' +
    'سجل يومي واحد لكل يوم (CONSTITUTION.md §20، Self-Awareness) — سطر واحد، لا يُعاد كتابته إلا إذا تكرر التشغيل في نفس اليوم.\n\n' +
    '| التاريخ | الحالة | معرفة (ملفات) | دروس | فرص ذهبية | نسبة اجتياز الفحص المزدوج | نيتشات مرفوضة (تراكمي) |\n' +
    '|---|---|---|---|---|---|---|\n';

  if (!fs.existsSync(GROWTH_LOG)) {
    fs.writeFileSync(GROWTH_LOG, header + row + '\n');
    return;
  }

  let content = fs.readFileSync(GROWTH_LOG, 'utf8');
  const existingRowRe = new RegExp(`^\\|\\s*${today}\\s*\\|.*\\|\\s*$`, 'm');
  if (existingRowRe.test(content)) {
    content = content.replace(existingRowRe, row); // re-running the same day replaces, doesn't duplicate
  } else {
    content = content.trimEnd() + '\n' + row + '\n';
  }
  fs.writeFileSync(GROWTH_LOG, content);
}

const METRIC_LABELS = {
  knowledge_entries: 'ملفات المعرفة',
  lessons_learned: 'الدروس المستفادة',
  golden_opportunities: 'الفرص الذهبية',
  dual_inspection_pass_rate: 'نسبة اجتياز الفحص المزدوج',
};

function compareGrowth(todayMetrics, yesterday) {
  if (!yesterday) {
    return { has_baseline: false, direction: 'baseline', reason: 'أول قياس على الإطلاق — لا يوجد يوم سابق للمقارنة', deltas: null };
  }
  const deltas = {
    knowledge_entries: todayMetrics.knowledge_entries - yesterday.knowledge_entries,
    lessons_learned: todayMetrics.lessons_learned - yesterday.lessons_learned,
    golden_opportunities: todayMetrics.golden_opportunities - yesterday.golden_opportunities,
    dual_inspection_pass_rate: todayMetrics.dual_inspection_pass_rate - yesterday.dual_inspection_pass_rate,
  };
  const entries = Object.entries(deltas);
  const positive = entries.filter(([, d]) => d > 0).length;
  const negative = entries.filter(([, d]) => d < 0).length;

  let direction, reason;
  if (positive > negative) {
    direction = 'smarter';
    const best = entries.reduce((a, b) => (b[1] > a[1] ? b : a));
    reason = `تحسّن أبرز في ${METRIC_LABELS[best[0]]} (${best[1] > 0 ? '+' : ''}${best[1]})`;
  } else if (negative > positive) {
    direction = 'weaker';
    const worst = entries.reduce((a, b) => (b[1] < a[1] ? b : a));
    reason = `تراجع في ${METRIC_LABELS[worst[0]]} (${worst[1]})`;
  } else {
    direction = 'same';
    reason = 'لا تغيّر صافٍ في المؤشرات الأربعة الرئيسية منذ الأمس';
  }
  return { has_baseline: true, direction, reason, deltas };
}

// ── SELF-DIAGNOSIS ──

function selfDiagnose(vitals) {
  const weaknesses = [];

  if (!vitals.health.reachable) {
    weaknesses.push({ cell: 'Dashboard', issue: `غير متاح: ${vitals.health.error}` });
  } else if (vitals.health.status !== 'healthy') {
    weaknesses.push({ cell: 'Dashboard/Health', issue: `الحالة العامة: ${vitals.health.status}` });
  }
  for (const [name, c] of Object.entries(vitals.health.checks || {})) {
    if (!c.ok) weaknesses.push({ cell: name, issue: c.detail });
  }
  if (!vitals.golden_pipeline.hunter.flowing) {
    weaknesses.push({ cell: 'market_hunter', issue: vitals.golden_pipeline.hunter.reason });
  }
  if (!vitals.golden_pipeline.oracle.flowing) {
    weaknesses.push({ cell: 'profit_oracle', issue: vitals.golden_pipeline.oracle.reason });
  }
  if (!vitals.golden_pipeline.inspectors.flowing) {
    weaknesses.push({ cell: 'inspectors', issue: vitals.golden_pipeline.inspectors.reason });
  }
  if (vitals.butter_compliance && vitals.butter_compliance.rate < 100) {
    weaknesses.push({
      cell: 'Butter compliance',
      issue: `${vitals.butter_compliance.rate}% فقط من آخر ${vitals.butter_compliance.total} فحص اجتاز حد $30`,
    });
  }
  if (vitals.rejected_niches === 0 && vitals.quarantine_entries === 0) {
    // Not necessarily bad — could mean nothing weak has been tried yet — but
    // worth naming as "untested," not silently treated as "immune and fine."
    weaknesses.push({ cell: 'Circuit breaker / Immunity', issue: 'لم يُختبَر بعد — لا رفض واحد مسجَّل حتى الآن' });
  }

  return {
    weaknesses,
    weakest_cell: weaknesses.length ? weaknesses[0].cell : null,
  };
}

function checkConstitutionCompliance(vitals, growth) {
  const notes = [];
  if (vitals.butter_compliance && vitals.butter_compliance.rate < 100) {
    notes.push(`§16 (Butter Principle): ${100 - vitals.butter_compliance.rate}% من آخر الفحوصات لم تصل لحد $30 — ` +
      'ليس انتهاكاً (النظام يرفض هذه بدل أن يخترق الحد)، لكنه يستحق متابعة إن استمر الاتجاه.');
  }
  if (!vitals.golden_pipeline.inspectors.flowing) {
    notes.push('§17 (Dual Inspection): لا سجلات فحص حديثة — تحقّق أن generate_book() لا يزال يستدعي inspectors.py فعلياً.');
  }
  if (growth.has_baseline && growth.deltas.knowledge_entries <= 0) {
    notes.push('§18 (Knowledge Brain): لم ينمُ العقل المعرفي منذ الأمس — تحقّق أن دروساً جديدة تُوثَّق فعلياً بدل البقاء في المحادثات فقط.');
  }
  // §19 (Golden Hunter): this used to be a hardcoded, unconditional warning
  // ("REJECTED_NICHES.md doesn't cover /api/scout/run yet") — itself a small
  // dishonesty for a module whose whole purpose is truth over flattery: a
  // hardcoded note can't ever report that a gap got fixed. Now a real,
  // verifiable check — does book_generator.py's own source actually contain
  // the shared recording point? — not an assumption held in this file.
  notes.push(checkScoutCircuitBreakerCoverage());
  return notes;
}

function checkScoutCircuitBreakerCoverage() {
  const bookGenPath = path.join(FACTORY_DIR, 'book_generator.py');
  try {
    const source = fs.readFileSync(bookGenPath, 'utf8');
    const fixed = source.includes('_record_rejected_niche');
    return fixed
      ? '§19 (Golden Hunter): مُغلَقة — generate_book() يسجّل الرفض مباشرة (نقطة مشتركة لكل المسارات: Scout وhunt() وmarket_hunter)، ' +
        'وليس factory_loop.js وحده كما كان سابقاً.'
      : '§19 (Golden Hunter): فجوة مفتوحة — REJECTED_NICHES.md لا يزال لا يغطي /api/scout/run ' +
        '(انظر OpenClaw_Brain/19_Lessons_Learned/The_Circuit_Breaker_Discovery.md).';
  } catch (_) {
    return '§19 (Golden Hunter): تعذّر التحقق من book_generator.py لمعرفة حالة هذه الفجوة.';
  }
}

// ── THE DAILY VERDICT ──

function cellScores(vitals) {
  const scores = {
    'Dashboard/Health': vitals.health.reachable ? (vitals.health.status === 'healthy' ? 100 : 50) : 0,
    'market_hunter': vitals.golden_pipeline.hunter.flowing ? 100 : 0,
    'profit_oracle': vitals.golden_pipeline.oracle.flowing ? 100 : 0,
    'inspectors': vitals.golden_pipeline.inspectors.flowing ? 100 : 0,
    'Knowledge Brain': vitals.knowledge_entries > 0 ? 100 : 0,
  };
  if (vitals.butter_compliance) scores['Butter Compliance'] = vitals.butter_compliance.rate;
  return scores;
}

function generateVerdict(vitals, growth, diagnosis) {
  const healthWord = !vitals.health.reachable ? 'غير متاح تماماً'
    : vitals.health.status === 'healthy' ? 'سليم'
    : vitals.health.status === 'degraded' ? 'متدهور جزئياً'
    : 'في حالة حرجة';

  const growthWord = growth.direction === 'smarter' ? 'أذكى'
    : growth.direction === 'weaker' ? 'أضعف'
    : growth.direction === 'same' ? 'كما هو بالضبط'
    : 'بلا نقطة مقارنة (أول قياس اليوم)';

  const scores = cellScores(vitals);
  const scoreEntries = Object.entries(scores);
  const strongest = scoreEntries.reduce((a, b) => (b[1] > a[1] ? b : a));
  const weakest = scoreEntries.reduce((a, b) => (b[1] < a[1] ? b : a));

  const biggestOpportunity = vitals.golden_opportunities > 0
    ? `${vitals.golden_opportunities} فرصة مسجَّلة في GOLDEN_OPPORTUNITIES.md بانتظار مراجعة Galaxy`
    : 'لا فرص ذهبية مسجَّلة حالياً — شغّل market_hunter.py --run';

  const nextFocus = diagnosis.weakest_cell
    ? `معالجة ${diagnosis.weakest_cell} (${diagnosis.weaknesses[0].issue})`
    : 'لا ضعف واضح اليوم — استمر بمراقبة الاتجاه';

  return `اليوم المصنع ${healthWord}. أصبح ${growthWord} مقارنة بالأمس لأن ${growth.reason}. ` +
    `أقوى خلية: ${strongest[0]} (${strongest[1]}%). أضعف خلية: ${weakest[0]} (${weakest[1]}%). ` +
    `أكبر فرصة: ${biggestOpportunity}. التركيز التالي الموصى به: ${nextFocus}.`;
}

// ── ORCHESTRATION ──

async function assessSelfAwareness(now = new Date()) {
  const vitals = await computeVitalSigns(now);
  const history = readGrowthLog();
  const yesterday = history.length ? history[history.length - 1] : null;

  const growth = compareGrowth({
    knowledge_entries: vitals.knowledge_entries,
    lessons_learned: vitals.lessons_learned,
    golden_opportunities: vitals.golden_opportunities,
    dual_inspection_pass_rate: vitals.dual_inspection ? vitals.dual_inspection.rate : 0,
  }, yesterday);

  const diagnosis = selfDiagnose(vitals);
  const constitutionNotes = checkConstitutionCompliance(vitals, growth);
  const verdict = generateVerdict(vitals, growth, diagnosis);

  return { timestamp: now.toISOString(), vitals, growth, diagnosis, constitution_notes: constitutionNotes, verdict };
}

async function runDailyAwareness(now = new Date()) {
  const assessment = await assessSelfAwareness(now);
  writeGrowthRow(assessment.vitals, now);
  return assessment;
}

function main() {
  const run = async () => {
    if (process.argv.includes('--run')) {
      const assessment = await runDailyAwareness();
      console.log(JSON.stringify({ success: true, verdict: assessment.verdict }, null, 2));
    } else {
      const assessment = await assessSelfAwareness();
      console.log(JSON.stringify(assessment, null, 2));
    }
  };
  run().catch(err => {
    console.error('[self_awareness] failed:', err.message);
    process.exitCode = 1;
  });
}

if (require.main === module) {
  main();
}

module.exports = {
  assessSelfAwareness, runDailyAwareness, computeVitalSigns, compareGrowth,
  selfDiagnose, checkConstitutionCompliance, generateVerdict,
  readGrowthLog, writeGrowthRow, getGoldenOpportunitiesCount, countLessons,
};

const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const Groq = require('groq-sdk');
const knowledgeBrain = require('./knowledge_brain');
const selfAwareness = require('./self_awareness');
// readLastGenerationRecord is a pure file read (no side effects) — requiring
// factory_loop.js here never starts its loop or acquires its lockfile: both
// only happen inside main(), guarded by `if (require.main === module)`
// (see factory_loop.js's own comment on that guard).
const { readLastGenerationRecord, getButterPrice } = require('./factory_loop');

require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;
const GROQ_KEY = process.env.GROQ_KEY;
const groq = new Groq({ apiKey: GROQ_KEY || 'missing' });

// Same gate factory_loop.js already enforces for its own automatic
// distribution calls (ADR-018) — absent by default, so a real Gumroad push
// still requires both this AND GUMROAD_ACCESS_TOKEN (channels/gumroad_arm.py
// checks that independently).
const LIVE_PUBLISH_ENABLED = process.env.FACTORY_LIVE_PUBLISH === 'true';

app.use(cors());
app.use(express.json());

// ── NICHE SAFETY FILTER ──
// Gates any niche/title/description before it can reach book generation.
// Wraps safety_filter.py (blocklists for brand-poison, financial,
// medical, trademark, adult content — see safety_filter.py). This is a
// safety gate, not a UX nicety: any failure to get a clean verdict from the
// Python process (spawn error, timeout, non-zero exit, unparseable output)
// must REJECT, never silently let an unchecked niche through.
function runSafetyCheck(payload, timeoutMs = 5000) {
  const FAIL_SAFE = () => ({
    allowed: false,
    score: 0,
    risk_level: 'blocked',
    reasons: [{ category: 'filter_error', level: 'blocked', reason: 'safety filter unavailable — failing safe' }],
  });

  return new Promise((resolve) => {
    let settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };

    let python;
    try {
      const pythonPath = detectPython();
      const scriptPath = path.join(__dirname, 'safety_filter.py');
      python = spawn(pythonPath, [scriptPath], { cwd: __dirname });
    } catch (err) {
      resolve(FAIL_SAFE());
      return;
    }

    const timer = setTimeout(() => {
      try { python.kill(); } catch (_) { /* best effort */ }
      finish(FAIL_SAFE());
    }, timeoutMs);

    let output = '', errOut = '';
    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });

    python.on('error', () => finish(FAIL_SAFE()));

    python.on('close', code => {
      try {
        if (code !== 0) throw new Error(`safety_filter.py exited ${code}: ${errOut}`);
        const result = JSON.parse(output.trim());
        if (typeof result.allowed !== 'boolean') throw new Error('malformed safety-check result');
        finish(result);
      } catch (err) {
        finish(FAIL_SAFE());
      }
    });

    try {
      python.stdin.write(JSON.stringify(payload));
      python.stdin.end();
    } catch (err) {
      finish(FAIL_SAFE());
    }
  });
}

app.post('/api/safety/check', async (req, res) => {
  try {
    const result = await runSafetyCheck(req.body || {});
    res.json({ success: true, ...result });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// ── GENERATE BOOK ──
app.post('/generate-book', async (req, res) => {
  // `output` is destructured as `outputName` to avoid colliding with the
  // `output`/`errOut` stdout-accumulator variables used below.
  const { title, subtitle, type, theme, pages, author, topic, chapters, audience, price, output: outputName } = req.body;

  if (!title) return res.json({ success: false, error: 'Title is required' });

  try {
    const safetyResult = await runSafetyCheck({
      niche: req.body.niche || '',
      title: req.body.title || '',
      subtitle: req.body.subtitle || '',
      description: req.body.description || '',
      type: req.body.type || '',
    });

    if (safetyResult.allowed === false) {
      return res.json({
        success: false,
        blocked: true,
        reason: 'safety_rejected',
        risk_level: safetyResult.risk_level,
        score: safetyResult.score,
        reasons: safetyResult.reasons,
        message: 'Niche rejected by Niche Safety Filter.',
      });
    }

    const pythonPath = detectPython();
    const bookScript = path.join(__dirname, 'book_generator.py');

    if (!fs.existsSync(bookScript)) {
      return res.status(404).json({ success: false, error: 'book_generator.py not found' });
    }

    const filename = outputName || (title.replace(/\s+/g, '_').toLowerCase() + '.pdf');

    // With a `topic`, route to the real AI content engine (generate_book());
    // otherwise keep the original fixed-template path exactly as before.
    const payload = topic
      ? JSON.stringify({
          title,
          topic,
          chapters: chapters || 8,
          audience: audience || 'القارئ العام',
          price: price != null ? price : 9.99,
          theme: theme || 'blue',
          author: author || '',
          output: filename,
        })
      : JSON.stringify({
          title: title || 'My Book',
          subtitle: subtitle || '',
          type: type || 'journal',
          theme: theme || 'blue',
          pages: parseInt(pages) || 120,
          author: author || '',
          output: filename
        });

    const python = spawn(pythonPath, [bookScript, '--json'], { cwd: __dirname });

    let output = '', errOut = '';
    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.stdin.write(payload);
    python.stdin.end();

    python.on('close', code => {
      try {
        const result = JSON.parse(output.trim());
        if (result.success) {
          // `published`/`inspection` (Dual Inspection, CONSTITUTION.md §17)
          // must reach the caller — a book can be generated successfully yet
          // still be quarantined. Silently dropping these fields here was
          // exactly why factory_loop.js couldn't tell a rejection from a
          // real success and kept retrying the same rejected niche forever.
          res.json({
            success: true,
            filename: result.file || filename,
            pages: result.pages,
            published: result.published,
            inspection: result.inspection,
          });
        } else {
          res.json({ success: false, error: result.error });
        }
      } catch {
        res.json({ success: false, error: 'Parse error: ' + output + errOut });
      }
    });

  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// ── DISTRIBUTE ──
// Wraps distributor.py (OCTOPUS_ARCHITECTURE.md) via the same
// spawn + stdin-JSON + stdout-JSON pattern as /generate-book. Every safety
// property lives in distributor.py/channels/gumroad_arm.py, not here —
// this endpoint is a thin passthrough and must not duplicate or bypass any
// of it:
//   - dry_run defaults to true. Only an explicit `dry_run: false` in the
//     request body goes live; anything else (missing, true, a truthy
//     non-boolean) stays a dry run — mirrors distributor.py's own
//     job.get("dry_run", True), made explicit here too so the default is
//     visible at this layer instead of only inherited silently.
//   - Every attempt (dry-run or live, success or failure) is recorded to
//     data/sales_ledger.jsonl by distributor.py itself.
//   - No arm can push live without its own platform secret — GumroadArm's
//     status() fails safe on a missing GUMROAD_ACCESS_TOKEN regardless of
//     dry_run, and nothing here checks or touches that secret.
// ── PUBLISHER → DISTRIBUTION LINK (ADR-019) ──
// Publisher was the one dashboard-only agent with a genuinely unique role
// (SEO listing copy) — nothing else in the real pipeline produces it, unlike
// Builder/Design/QA/Finance which duplicate book_generator.py/
// cover_designer_v2/Dual Inspection/economics.py respectively (see
// ADR-019). This makes Publisher's existing prompt (AGENT_PROMPTS.publisher
// — unchanged) run automatically on every real distribution attempt instead
// of only through its manual dashboard button. It never blocks or fails a
// distribution: a Groq error here is logged, not thrown, exactly like every
// other fail-safe wrapper in this file.
//
// The actual logic lives in lib/publisher_seo.js (groq client/key/prompt are
// injected there) so it's unit-testable without a real network call — see
// tests/test_publisher_seo.js.
const { logPublisherSEO, generatePublisherSEO: generatePublisherSEOCore } = require('./lib/publisher_seo');

async function generatePublisherSEO(record) {
  return generatePublisherSEOCore(record, {
    groqClient: groq,
    groqKey: GROQ_KEY,
    systemPrompt: AGENT_PROMPTS.publisher.system,
  });
}

// Shared spawn + stdin-JSON/stdout-JSON helper — extracted so both the
// route below AND the Scout auto-distribute link (ADR-018) call the exact
// same distributor.py invocation, instead of two divergent copies.
async function runDistributor(record, { arms, dryRun = true } = {}, timeoutMs = 140000) {
  const seo = await generatePublisherSEO(record);
  logPublisherSEO({
    product_title: (record && (record.title || record.topic)) || null,
    ok: seo.ok,
    content: seo.ok ? seo.content : null,
    error: seo.ok ? null : seo.error,
  });

  const distributorResult = await new Promise((resolve, reject) => {
    const pythonPath = detectPython();
    const distributorScript = path.join(__dirname, 'distributor.py');
    if (!fs.existsSync(distributorScript)) {
      reject(new Error('distributor.py not found'));
      return;
    }

    let python;
    try {
      python = spawn(pythonPath, [distributorScript, '--json'], { cwd: __dirname });
    } catch (err) {
      reject(err);
      return;
    }

    let output = '', errOut = '', settled = false;
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      try { python.kill(); } catch (_) { /* best effort */ }
      reject(new Error('انتهت مهلة distributor.py'));
    }, timeoutMs);

    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', err => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      reject(err);
    });
    python.on('close', () => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      try {
        resolve(JSON.parse(output.trim()));
      } catch (e) {
        reject(new Error('Parse error: ' + output + errOut));
      }
    });

    python.stdin.write(JSON.stringify({ record, arms, dry_run: dryRun }));
    python.stdin.end();
  });

  return { ...distributorResult, seo: { ok: seo.ok, content: seo.ok ? seo.content : null, error: seo.ok ? null : seo.error } };
}

app.post('/api/distribute', async (req, res) => {
  const { record, arms } = req.body || {};

  if (!record || typeof record !== 'object' || Array.isArray(record)) {
    return res.status(400).json({ success: false, error: 'record (a JSONL production-log record) is required' });
  }
  if (arms !== undefined && !Array.isArray(arms)) {
    return res.status(400).json({ success: false, error: 'arms must be an array of arm names, if provided' });
  }

  const dryRun = req.body.dry_run === false ? false : true;

  try {
    const result = await runDistributor(record, { arms, dryRun });
    res.json(result);
  } catch (err) {
    res.status(500).json({ success: false, error: 'Failed to run distributor.py: ' + err.message });
  }
});

// ── SCOUT → DISTRIBUTOR LINK (ADR-018) ──
// /api/scout/run generates a real book via book_generator.py directly (see
// runBookGenerator above) but, unlike factory_loop.js's hunt()/
// healEmptyBooks()/huntGolden() (all routed through triggerGenerateBook()
// -> triggerDistribute()), it never used to call distributor.py at all — a
// Scout-generated book sat with zero distribution attempt recorded. This
// closes that gap using the exact same record-matching + dry_run gate
// factory_loop.js already applies, so a manual Scout run behaves like the
// automatic loop instead of being a second, inconsistent path.
async function autoDistributeScoutBook(bookResult) {
  if (!bookResult || bookResult.success !== true) return null;

  if (bookResult.published === false) {
    return { ok: false, dry_run: null, outcomes: null, detail: 'تم التوليد لكن رُفض النشر (Dual Inspection) — تخطّي التوزيع' };
  }

  const record = readLastGenerationRecord();
  if (!record || record.file !== bookResult.file) {
    return { ok: false, dry_run: null, outcomes: null, detail: 'تعذّر مطابقة سجل التوليد الأخير في books/_generation_log.jsonl — تخطّي التوزيع الآلي' };
  }

  const dryRun = !LIVE_PUBLISH_ENABLED;
  try {
    const result = await runDistributor(record, { dryRun });
    if (!result.success) {
      return { ok: false, dry_run: dryRun, outcomes: null, seo: result.seo, detail: `فشل التوزيع: ${result.error}` };
    }
    return { ok: true, dry_run: dryRun, outcomes: result.outcomes, seo: result.seo };
  } catch (err) {
    return { ok: false, dry_run: dryRun, outcomes: null, detail: `فشل الاتصال بـ distributor.py: ${err.message}` };
  }
}

// ── SALES POLL ──
// Wraps scripts/poll_sales.py (ADR-016) via the same spawn + stdin-JSON +
// stdout-JSON pattern as /api/distribute. This endpoint never talks to
// Gumroad directly — poll_sales.py calls each registered arm's get_sales(),
// which itself refuses (skip_reason, never a network call) without a real
// GUMROAD_ACCESS_TOKEN, same fail-safe channels/gumroad_arm.py already
// enforces for publish().
app.post('/api/sales/poll', (req, res) => {
  const { arms } = req.body || {};
  if (arms !== undefined && !Array.isArray(arms)) {
    return res.status(400).json({ success: false, error: 'arms must be an array of arm names, if provided' });
  }

  const pythonPath = detectPython();
  const pollScript = path.join(__dirname, 'scripts', 'poll_sales.py');

  if (!fs.existsSync(pollScript)) {
    return res.status(404).json({ success: false, error: 'scripts/poll_sales.py not found' });
  }

  const payload = JSON.stringify({ arms });

  let python;
  try {
    python = spawn(pythonPath, [pollScript, '--json'], { cwd: __dirname });
  } catch (err) {
    return res.status(500).json({ success: false, error: 'Failed to spawn poll_sales.py: ' + err.message });
  }

  let output = '', errOut = '', responded = false;
  python.stdout.on('data', d => { output += d.toString(); });
  python.stderr.on('data', d => { errOut += d.toString(); });

  python.on('error', (err) => {
    if (responded) return;
    responded = true;
    res.status(500).json({ success: false, error: 'Failed to spawn poll_sales.py: ' + err.message });
  });

  python.on('close', () => {
    if (responded) return;
    responded = true;
    try {
      const result = JSON.parse(output.trim());
      res.json(result);
    } catch {
      res.json({ success: false, error: 'Parse error: ' + output + errOut });
    }
  });

  python.stdin.write(payload);
  python.stdin.end();
});

// ── CHAT ──
app.post('/chat', async (req, res) => {
  const { message, agent } = req.body;
  try {
    const response = await groq.chat.completions.create({
      model: 'llama-3.1-8b-instant',
      max_tokens: 1024,
      messages: [{ role: 'user', content: message }]
    });
    res.json({ success: true, reply: response.choices[0].message.content, agent: agent || 'Scout' });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// ── FINANCE ──
// Hardened per the Factory Constitution: defensive read (corrupt JSON -> empty
// data, never a 500), atomic write (temp file + rename), structured error
// logging, and input validation on the write endpoints.
const FINANCE_FILE = path.join(__dirname, 'finance_data.json');
const FINANCE_ERROR_LOG = path.join(__dirname, 'finance_errors.log');
const FINANCE_PLATFORMS = ['KDP', 'Etsy', 'Gumroad'];

function financeDefault() {
  return { sales: [], totalKDP: 0, totalEtsy: 0, totalGumroad: 0, totalSales: 0, lastUpdated: null };
}

function logFinanceError(context, err) {
  const line = JSON.stringify({
    timestamp: new Date().toISOString(),
    context,
    error: err && err.message ? err.message : String(err),
  });
  try { fs.appendFileSync(FINANCE_ERROR_LOG, line + '\n'); } catch (_) { /* logging must never break the request */ }
  console.error(`[finance] ${context}:`, err);
}

function loadFin() {
  if (!fs.existsSync(FINANCE_FILE)) {
    const init = financeDefault();
    try { saveFin(init); } catch (err) { logFinanceError('init-write', err); }
    return init;
  }

  let raw;
  try {
    raw = fs.readFileSync(FINANCE_FILE, 'utf8');
  } catch (err) {
    logFinanceError('read', err);
    return financeDefault();
  }

  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch (err) {
    // Corrupt JSON: quarantine the bad file instead of losing it, then fall
    // back to empty data so the endpoint never 500s (self-healing).
    logFinanceError('parse', err);
    try {
      fs.copyFileSync(FINANCE_FILE, `${FINANCE_FILE}.corrupt-${Date.now()}.bak`);
    } catch (copyErr) {
      logFinanceError('quarantine', copyErr);
    }
    const init = financeDefault();
    try { saveFin(init); } catch (writeErr) { logFinanceError('recover-write', writeErr); }
    return init;
  }

  // Defensive shape normalization — tolerates a partially-missing/legacy file.
  return {
    sales: Array.isArray(parsed.sales) ? parsed.sales : [],
    totalKDP: Number.isFinite(parsed.totalKDP) ? parsed.totalKDP : 0,
    totalEtsy: Number.isFinite(parsed.totalEtsy) ? parsed.totalEtsy : 0,
    totalGumroad: Number.isFinite(parsed.totalGumroad) ? parsed.totalGumroad : 0,
    totalSales: Number.isFinite(parsed.totalSales) ? parsed.totalSales : 0,
    lastUpdated: parsed.lastUpdated || null,
  };
}

function saveFin(data) {
  data.totalSales = (data.totalKDP || 0) + (data.totalEtsy || 0) + (data.totalGumroad || 0);
  data.lastUpdated = new Date().toISOString();
  // Atomic write: write to a temp file then rename over the target, so a crash
  // mid-write can never leave finance_data.json half-written/corrupt.
  const tmpFile = `${FINANCE_FILE}.tmp-${process.pid}-${Date.now()}`;
  fs.writeFileSync(tmpFile, JSON.stringify(data, null, 2));
  fs.renameSync(tmpFile, FINANCE_FILE);
}

function recomputeFinTotals(data) {
  data.totalKDP = data.sales.filter(s => s.platform === 'KDP').reduce((a, s) => a + s.amount, 0);
  data.totalEtsy = data.sales.filter(s => s.platform === 'Etsy').reduce((a, s) => a + s.amount, 0);
  data.totalGumroad = data.sales.filter(s => s.platform === 'Gumroad').reduce((a, s) => a + s.amount, 0);
}

app.get('/finance', (req, res) => {
  try {
    res.json(loadFin());
  } catch (err) {
    logFinanceError('get', err);
    res.json(financeDefault());
  }
});

app.post('/finance/add', (req, res) => {
  const { platform, amount, product, date } = req.body || {};

  if (!FINANCE_PLATFORMS.includes(platform)) {
    return res.status(400).json({ success: false, error: `platform يجب أن يكون أحد: ${FINANCE_PLATFORMS.join(', ')}` });
  }
  const parsedAmount = parseFloat(amount);
  if (!Number.isFinite(parsedAmount) || parsedAmount < 0) {
    return res.status(400).json({ success: false, error: 'amount يجب أن يكون رقماً موجباً' });
  }
  const parsedDate = /^\d{4}-\d{2}-\d{2}$/.test(date) ? date : new Date().toISOString().split('T')[0];

  try {
    const data = loadFin();
    const sale = {
      id: Date.now(),
      platform,
      amount: parsedAmount,
      product: String(product || 'Unknown').slice(0, 200),
      date: parsedDate,
    };
    data.sales.push(sale);
    recomputeFinTotals(data);
    saveFin(data);
    res.json({ success: true, sale });
  } catch (err) {
    logFinanceError('add', err);
    res.status(500).json({ success: false, error: 'تعذّر حفظ عملية البيع' });
  }
});

app.delete('/finance/delete/:id', (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (!Number.isFinite(id)) {
    return res.status(400).json({ success: false, error: 'id غير صالح' });
  }
  try {
    const data = loadFin();
    data.sales = data.sales.filter(s => s.id !== id);
    recomputeFinTotals(data);
    saveFin(data);
    res.json({ success: true });
  } catch (err) {
    logFinanceError('delete', err);
    res.status(500).json({ success: false, error: 'تعذّر حذف العملية' });
  }
});

// ── AGENT SYSTEM PROMPTS ──
const AGENT_PROMPTS = {
  scout: {
    system: `أنت وكيل استكشاف الأسواق في OpenClaw Factory. مهمتك تحليل أسواق الكتب الرقمية وتقديم أفكار رابحة لـ Amazon KDP وEtsy وGumroad.
عند تشغيلك قدّم:
1. 3-5 أفكار كتب رابحة حالياً بناءً على اتجاهات السوق
2. لكل فكرة: النيش، مستوى المنافسة (منخفض/متوسط/عالي)، السعر المقترح، الجمهور المستهدف
3. توصيتك الأولى بوضوح
أجب باللغة العربية، بشكل منظم ومختصر.`,
    trigger: 'حلّل السوق الآن وأعطني أفضل 5 أفكار كتب رابحة لهذا الشهر على Amazon KDP وEtsy'
  },

  builder: {
    system: `أنت وكيل بناء المحتوى في OpenClaw Factory. مهمتك توليد محتوى الكتب الرقمية (journals, planners, trackers, cookbooks).
عند تشغيلك قدّم:
1. هيكل كتاب جديد مقترح: عنوان، فصول رئيسية، عدد الصفحات
2. مثال محتوى صفحة واحدة كاملة من الكتاب
3. 3 نصائح لجعل المحتوى أكثر قيمة وأعلى تقييماً
أجب باللغة العربية، بشكل عملي وقابل للتطبيق مباشرة.`,
    trigger: 'اقترح كتاباً رقمياً جديداً مع هيكله الكامل ومثال على محتواه'
  },

  design: {
    system: `أنت وكيل التصميم في OpenClaw Factory. مهمتك اقتراح أفكار تصميم احترافية للأغلفة والصفحات الداخلية للكتب الرقمية بحجم 6×9 إنش.
عند تشغيلك قدّم:
1. مفهوم تصميم غلاف: الألوان الرئيسية، نوع الخط، الأسلوب البصري، العناصر الجرافيكية
2. أفكار للصفحات الداخلية: التخطيط، التوزيع، الأيقونات، الفراغات
3. 3 توصيات لجعل التصميم يبرز في نتائج البحث على Amazon وEtsy
أجب باللغة العربية بتفاصيل دقيقة قابلة للتنفيذ.`,
    trigger: 'اقترح تصميماً احترافياً كاملاً لغلاف وصفحات داخلية لكتاب journal أو planner'
  },

  qa: {
    system: `أنت وكيل ضمان الجودة في OpenClaw Factory. مهمتك فحص المنتجات الرقمية وضمان جودتها قبل النشر على KDP وEtsy.
عند تشغيلك قدّم:
1. قائمة تحقق شاملة لجودة الكتاب الرقمي (PDF، محتوى، تصميم، بيانات)
2. أبرز 5 أخطاء تؤدي لرفض المنتج على KDP أو شكاوى على Etsy
3. معايير الجودة الدنيا المطلوبة لكل منصة
أجب باللغة العربية بقوائم منظمة وعملية.`,
    trigger: 'افحص معايير الجودة وأعطني checklist كاملة لضمان قبول منتجنا الرقمي'
  },

  publisher: {
    system: `أنت وكيل النشر في OpenClaw Factory. مهمتك تحضير بيانات النشر المحسّنة لـ SEO على Amazon KDP وEtsy وGumroad.
عند تشغيلك قدّم:
1. عنوان محسّن لـ SEO يتضمن الكلمات المفتاحية الأكثر بحثاً (بالإنجليزية)
2. وصف تسويقي جذاب 150-200 كلمة (بالإنجليزية)
3. 7 كلمات مفتاحية مقترحة لـ KDP Backend Keywords (بالإنجليزية)
4. أنسب 2 فئة (Browse Categories) على Amazon
قدّم البيانات الفعلية بالإنجليزية لأن المنصات إنجليزية، مع شرح مختصر بالعربية لكل قسم.`,
    trigger: 'حضّر بيانات نشر كاملة ومحسّنة لـ SEO لكتاب daily journal على Amazon KDP'
  },

  finance: {
    system: `أنت وكيل التمويل في OpenClaw Factory. مهمتك تحليل الربحية واقتراح استراتيجيات تسعير للكتب الرقمية.
عند تشغيلك قدّم:
1. استراتيجية تسعير: سعر الإطلاق، السعر الدائم، أوقات التخفيض
2. مقارنة هوامش الربح الصافي على KDP (35% أو 70%) وEtsy وGumroad
3. حساب نقطة التعادل وهدف إيرادات شهري واقعي للمبتدئين
4. نصيحة واحدة لزيادة الإيرادات بأقل جهد
أجب باللغة العربية مع أرقام واضحة وقابلة للتطبيق.`,
    trigger: 'حلّل الربحية وأعطني استراتيجية تسعير كاملة لكتبنا الرقمية على KDP وEtsy وGumroad'
  }
};

// ── AGENT ENDPOINTS ──
app.post('/api/agent/:name', async (req, res) => {
  const { name } = req.params;
  const agentConfig = AGENT_PROMPTS[name];

  if (!agentConfig) {
    return res.status(404).json({ success: false, error: `وكيل غير معروف: ${name}` });
  }
  if (!GROQ_KEY) {
    return res.status(500).json({ success: false, error: 'GROQ_KEY غير مضبوط في .env' });
  }

  try {
    const userMessage = (req.body && req.body.message) || agentConfig.trigger;
    const response = await groq.chat.completions.create({
      model: 'llama-3.1-8b-instant',
      max_tokens: 1024,
      messages: [
        { role: 'system', content: agentConfig.system },
        { role: 'user',   content: userMessage }
      ]
    });
    res.json({
      success: true,
      message: response.choices[0].message.content,
      agent: name
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// ── SCOUT PRODUCTION PIPELINE ──
// Scout button -> trigger n8n Sensing Engine -> pick a niche/brief -> generate
// a real book via book_generator.py -> log the run. Hardened per the Factory
// Constitution: every external call (n8n, Groq) has a timeout + retry, and a
// failure at any stage degrades to a fallback instead of crashing the request.
const N8N_SCOUT_WEBHOOK = process.env.N8N_SCOUT_WEBHOOK || 'http://localhost:5678/webhook/scout-trigger';
const SCOUT_LOG_FILE = path.join(__dirname, 'scout_runs.log');

function logScout(context, data) {
  try {
    fs.appendFileSync(SCOUT_LOG_FILE, JSON.stringify({ timestamp: new Date().toISOString(), context, ...data }) + '\n');
  } catch (_) { /* logging must never break a run */ }
  console.log(`[scout] ${context}`, data);
}

function withTimeout(promise, ms, label) {
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(`${label} timed out after ${ms}ms`)), ms);
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}

async function triggerN8nTrends(retries = 2, timeoutMs = 8000) {
  let lastErr = null;
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const r = await withTimeout(fetch(N8N_SCOUT_WEBHOOK), timeoutMs, 'n8n');
      const text = await r.text();
      let body = text;
      try { body = JSON.parse(text); } catch (_) { /* plain text ack — fine */ }
      return { ok: r.ok, status: r.status, body };
    } catch (err) {
      lastErr = err;
      if (attempt < retries) await new Promise(res => setTimeout(res, 1000 * attempt));
    }
  }
  return { ok: false, error: lastErr ? lastErr.message : 'unknown error' };
}

async function groqChatWithRetry(messages, { maxTokens = 1024, retries = 2, timeoutMs = 20000 } = {}) {
  let lastErr;
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const resp = await withTimeout(
        groq.chat.completions.create({ model: 'llama-3.1-8b-instant', max_tokens: maxTokens, messages }),
        timeoutMs, 'Groq'
      );
      return resp.choices[0].message.content;
    } catch (err) {
      lastErr = err;
      if (attempt < retries) await new Promise(r => setTimeout(r, 1000 * attempt));
    }
  }
  throw lastErr;
}

function scoutBriefPrompt(trendsHint) {
  return `اقترح نيتش كتاب رقمي واحد فقط (الأقوى) مناسب للنشر الفوري على Amazon KDP${trendsHint ? `، مستفيداً من هذه الترندات الحالية: ${trendsHint}` : ''}.

عند تحديد ##PRICE##: سعّر هذا الكتاب كمنتج احترافي متميز (Premium)، وليس كتاباً رقمياً عادياً رخيصاً. اعتبارات التسعير:
- عمق المحتوى ومدى تخصصه (كلما كان أعمق وأكثر تخصصاً، كلما استحق سعراً أعلى)
- الجمهور المستهدف: هل هم محترفون/أصحاب أعمال مستعدون للدفع مقابل قيمة حقيقية؟
- أسعار المنتجات المماثلة في السوق (Market comparables) لنفس الفئة والجمهور
- الحد الأدنى المقبول هو 30 دولاراً (مستوى "الزبدة" — Butter-tier)، ولا تقترح رقماً أقل من ذلك أبداً
اجعل السعر مبرَّراً بالقيمة التي يقدّمها الكتاب فعلياً، لا رقماً افتراضياً.

هذا مثال على الشكل المطلوب فقط (نيتش مختلف تماماً — لا تكرر محتواه أبداً):
##TITLE##
دليل العادات الذهبية للصباح المنتج
##TOPIC##
كتاب عملي يعلّم القارئ بناء روتين صباحي يرفع تركيزه وطاقته خلال 30 يوماً
##AUDIENCE##
الموظفون وأصحاب الأعمال الذين يعانون من قلة التركيز
##PRICE##
39
##CHAPTERS##
6

الآن، بنفس التنسيق الحرفي بالضبط (##TITLE## ثم ##TOPIC## ثم ##AUDIENCE## ثم ##PRICE## ثم ##CHAPTERS##)، اكتب اقتراحك الخاص لنيتش مختلف تماماً بمحتوى حقيقي جديد. لا تعد أي شرح خارج هذه الأقسام، ولا تكرر نص المثال.`;
}

function parseScoutBrief(text) {
  // The small/fast Groq model is inconsistent run-to-run: sometimes it follows
  // the literal ##TITLE##/##TOPIC##/... tags exactly; other times it invents
  // its own '## <actual title text> ##' header and inline Arabic labels
  // ("وصف النيش:", "الجمهور المستهدف:", ...) instead of separate tag lines.
  // Handle both shapes explicitly rather than guessing from one heuristic
  // (same lesson learned in book_generator.py's content parser).
  if (/##TITLE##/i.test(text) && /##TOPIC##/i.test(text)) {
    const section = (tag) => {
      const m = text.match(new RegExp(`##${tag}##\\s*([\\s\\S]*?)(?=##[A-Z]+##|$)`, 'i'));
      return m ? m[1].trim() : '';
    };
    const priceMatch = section('PRICE').match(/[\d.]+/);
    const chaptersMatch = section('CHAPTERS').match(/\d+/);
    return {
      title: section('TITLE'),
      topic: section('TOPIC'),
      audience: section('AUDIENCE') || 'القارئ العام',
      price: priceMatch ? parseFloat(priceMatch[0]) : 9.99,
      chapters: chaptersMatch ? Math.max(4, Math.min(10, parseInt(chaptersMatch[0], 10))) : 6,
    };
  }

  // Loose fallback: first '## ... ##' line is the title (whatever it says),
  // the rest is scanned for inline Arabic field labels.
  const headerMatch = text.match(/^#{1,4}\s*(.+?)\s*#{0,4}\s*$/m);
  const title = headerMatch ? headerMatch[1].trim() : '';
  let body = headerMatch ? text.slice(headerMatch.index + headerMatch[0].length) : text;
  body = body.replace(/^\/+/gm, ''); // strip a stray leading "/" the model sometimes emits before a label

  // Bare word stems (no "ال" prefix, no fixed multi-word phrase) — the model
  // has been observed using "نيش"/"موضوع", "جمهور"/"الجمهور المستهدف",
  // "سعر"/"السعر المقترح", "فصول"/"عدد الفصول المتوقعة" interchangeably.
  const STEMS = { topic: '(?:نيش|موضوع)', audience: 'جمهور', price: 'سعر', chapters: 'فصول' };
  const LABELS = `(?:${STEMS.topic}|${STEMS.audience}|${STEMS.price}|${STEMS.chapters})`;
  const grab = (stem) => {
    // Skip the rest of the label's own line (and an optional inline ":"),
    // then capture up to the next label line (matched within its first ~30
    // chars, so the word can't accidentally match deep inside a paragraph).
    const re = new RegExp(`${stem}[^\\n:]*[:#]?\\s*([\\s\\S]*?)(?=\\n\\s*#*\\s*[^\\n]{0,30}?${LABELS}|$)`, 'i');
    const m = body.match(re);
    return m ? m[1].trim() : '';
  };

  const topic = grab(STEMS.topic);
  const audience = grab(STEMS.audience) || 'القارئ العام';
  const priceMatch = grab(STEMS.price).match(/[\d.]+/);
  const chaptersMatch = grab(STEMS.chapters).match(/\d+/);
  return {
    title,
    topic,
    audience,
    price: priceMatch ? parseFloat(priceMatch[0]) : 9.99,
    chapters: chaptersMatch ? Math.max(4, Math.min(10, parseInt(chaptersMatch[0], 10))) : 6,
  };
}

function fallbackScoutBrief() {
  return {
    title: 'دليل الإنتاجية اليومية للمبتدئين',
    topic: 'تحسين الإنتاجية وإدارة الوقت للمبتدئين',
    audience: 'القارئ العام',
    price: 9.99,
    chapters: 6,
  };
}

function runBookGenerator(payload, timeoutMs = 150000) {
  return new Promise((resolve, reject) => {
    const pythonPath = detectPython();
    const bookScript = path.join(__dirname, 'book_generator.py');
    const python = spawn(pythonPath, [bookScript, '--json'], { cwd: __dirname });
    let output = '', errOut = '', settled = false;

    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      python.kill();
      reject(new Error('انتهت مهلة توليد الكتاب'));
    }, timeoutMs);

    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.stdin.write(JSON.stringify(payload));
    python.stdin.end();

    python.on('error', err => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      reject(err);
    });
    python.on('close', () => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      try {
        resolve(JSON.parse(output.trim()));
      } catch (e) {
        reject(new Error('Parse error: ' + output + errOut));
      }
    });
  });
}

app.post('/api/scout/run', async (req, res) => {
  const startedAt = Date.now();

  // 1) Trigger the n8n Sensing Engine. Today the webhook responds immediately
  //    ("Workflow was started") rather than waiting for real trend data — we
  //    still call it, but treat the lack of structured trends as expected and
  //    degrade to the Groq-based brief below instead of failing the request.
  let n8nStatus = 'not_attempted';
  let trendsHint = null;
  try {
    const n8nResult = await triggerN8nTrends();
    if (n8nResult.ok) {
      n8nStatus = 'triggered';
      const list = n8nResult.body && (n8nResult.body.trends || n8nResult.body.topics);
      if (Array.isArray(list) && list.length) {
        trendsHint = list.slice(0, 10)
          .map(t => (typeof t === 'string' ? t : (t.title || t.query || '')))
          .filter(Boolean).join('، ');
      }
    } else {
      n8nStatus = n8nResult.status ? `http_${n8nResult.status}` : 'unreachable';
    }
  } catch (err) {
    n8nStatus = 'unreachable';
    logScout('n8n-error', { error: err.message });
  }

  // 2) Pick a niche + build a publishable brief.
  let brief = null;
  let briefSource = 'groq';
  if (!GROQ_KEY) {
    brief = fallbackScoutBrief();
    briefSource = 'fallback-no-key';
  } else {
    try {
      const raw = await groqChatWithRetry([
        { role: 'system', content: AGENT_PROMPTS.scout.system },
        { role: 'user', content: scoutBriefPrompt(trendsHint) },
      ]);
      const parsed = parseScoutBrief(raw);
      // Guard against the model echoing its own tag name back as the "title"
      // (e.g. a literal "标题"/"TITLE") — a real title is never that short.
      if (parsed.title && parsed.title.length >= 5 && parsed.topic) {
        brief = parsed;
      } else {
        logScout('brief-unparseable', { raw });
      }
    } catch (err) {
      logScout('brief-error', { error: err.message });
    }
    if (!brief) {
      brief = fallbackScoutBrief();
      briefSource = 'fallback';
    }
  }

  // 2.4) Real butter_price() (ADR-018) — Scout's own Groq prompt only
  // self-instructs a >=$30 floor with no market-comparable computation
  // behind it, unlike the Golden Hunter bridge (factory_loop.js's
  // briefFromGoldenOpportunity()), which already calls the real
  // profit_oracle.py butter_price(). Reusing that exact function here so
  // Scout's price is the same constitutional number, not a second,
  // divergent estimate — same fail-safe floor-clamp on failure.
  const MIN_BUTTER_PRICE = 30; // mirrors factory_loop.js's own constant (CONSTITUTION.md §16)
  const butter = await getButterPrice(brief.topic);
  if (butter.ok) {
    brief._raw_scout_price = brief.price;
    brief.price = butter.price;
    brief._price_source = 'butter_price';
  } else {
    brief.price = Math.max(brief.price || 0, MIN_BUTTER_PRICE);
    brief._price_source = 'fallback_floor_clamped';
    brief._butter_price_error = butter.error;
  }

  // 2.5) Niche Safety Filter gate — brief.topic/title/audience are what
  // actually reaches book_generator.py via runBookGenerator() below
  // (this route never reads req.body for the niche; Scout always picks
  // its own via Groq or the hardcoded fallback), so the gate must run on
  // the finalized brief, not on whatever the caller posted. Same
  // fail-safe contract as /generate-book: any failure from runSafetyCheck
  // itself is treated as blocked, never allowed through.
  console.log(`[scout] brief sent to safety filter — title: "${brief.title}" | topic: "${brief.topic}"`);

  let safetyResult;
  try {
    safetyResult = await runSafetyCheck({
      niche: brief.topic || '',
      title: brief.title || '',
      subtitle: '',
      description: brief.audience || '',
      type: brief.type || 'journal',
    });
  } catch (err) {
    safetyResult = {
      allowed: false,
      score: 0,
      risk_level: 'blocked',
      reasons: [{ category: 'filter_error', level: 'blocked', reason: 'safety filter unavailable — failing safe' }],
    };
  }

  if (safetyResult.allowed === false) {
    logScout('safety-rejected', { brief, risk_level: safetyResult.risk_level, reasons: safetyResult.reasons });
    return res.json({
      success: false,
      blocked: true,
      reason: 'safety_rejected',
      risk_level: safetyResult.risk_level,
      score: safetyResult.score,
      reasons: safetyResult.reasons,
      brief_intercepted: { title: brief.title, topic: brief.topic },
      message: 'Scout brief rejected by Niche Safety Filter.',
    });
  }

  // 3) Generate the actual book (real AI content, saved into books/).
  let bookResult;
  try {
    bookResult = await runBookGenerator({
      title: brief.title,
      topic: brief.topic,
      chapters: brief.chapters,
      audience: brief.audience,
      price: brief.price,
    });
  } catch (err) {
    logScout('generate-error', { error: err.message, brief });
    return res.status(502).json({ success: false, error: 'فشل توليد الكتاب: ' + err.message, n8n: n8nStatus, brief });
  }

  if (!bookResult || bookResult.success === false) {
    logScout('generate-failed', { bookResult, brief });
    return res.status(502).json({ success: false, error: (bookResult && bookResult.error) || 'فشل توليد الكتاب', n8n: n8nStatus, brief });
  }

  const distribution = await autoDistributeScoutBook(bookResult);

  const result = {
    success: true,
    n8n: n8nStatus,
    briefSource,
    brief,
    book: bookResult,
    distribution,
    durationMs: Date.now() - startedAt,
  };
  logScout('success', result);
  res.json(result);
});

// ── TRENDS INTAKE (n8n Sensing Engine → server.js Brain) ──
// Constitution: "n8n is the Sensing layer. server.js is the Brain. They
// communicate only via HTTP POST /api/trends." This is the receiving end of
// that contract: n8n's workflow POSTs whatever trend item it discovered,
// each one is run through quality_gate() (reusing book_generator.py's real
// implementation — not a duplicated JS copy), and anything that passes is
// recorded in OPPORTUNITIES.md.
const OPPORTUNITIES_FILE = path.join(__dirname, 'OPPORTUNITIES.md');
const TRENDS_LOG_FILE = path.join(__dirname, 'trends_received.log');

function logTrendsError(context, err) {
  try {
    fs.appendFileSync(TRENDS_LOG_FILE, JSON.stringify({ timestamp: new Date().toISOString(), context, error: err && err.message ? err.message : String(err) }) + '\n');
  } catch (_) { /* logging must never break the request */ }
}

// n8n's exact upstream node shape is unknown (no n8n API access to inspect
// the Sensing Engine workflow — see CONSTITUTION/FACTORY_STATUS notes), so
// this accepts whichever of these common field names actually carries the
// trend text, rather than assuming one specific schema.
function extractNiche(item) {
  if (!item || typeof item !== 'object') return null;
  const candidates = [item.niche, item.trend, item.topic, item.title, item.keyword, item.query, item.name];
  for (const c of candidates) {
    if (typeof c === 'string' && c.trim()) return c.trim().slice(0, 300);
  }
  return null;
}

function runQualityGate(niche, theme = 'blue', timeoutMs = 15000) {
  return new Promise((resolve, reject) => {
    const pythonPath = detectPython();
    const bookScript = path.join(__dirname, 'book_generator.py');
    const python = spawn(pythonPath, [bookScript, '--quality-gate'], { cwd: __dirname });
    let output = '', errOut = '', settled = false;

    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      python.kill();
      reject(new Error('quality_gate timed out'));
    }, timeoutMs);

    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.stdin.write(JSON.stringify({ niche, theme }));
    python.stdin.end();

    python.on('error', err => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      reject(err);
    });
    python.on('close', () => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      try {
        resolve(JSON.parse(output.trim()));
      } catch (e) {
        reject(new Error('Parse error: ' + output + errOut));
      }
    });
  });
}

function appendOpportunity(niche, gate) {
  if (!fs.existsSync(OPPORTUNITIES_FILE)) {
    fs.writeFileSync(
      OPPORTUNITIES_FILE,
      '# الفرص المكتشَفة (Opportunities)\n\nنيتشات اجتازت Quality Gate، مُستقبَلة تلقائياً من n8n عبر `/api/trends`.\n\n',
      'utf8'
    );
  }
  const timestamp = new Date().toISOString();
  fs.appendFileSync(OPPORTUNITIES_FILE, `- [${timestamp}] ${niche} — ${gate.reason}\n`, 'utf8');
}

app.post('/api/trends', async (req, res) => {
  // Always 200 to n8n regardless of what happened downstream — a rejected
  // trend or a malformed payload is normal business logic, not a delivery
  // failure n8n should retry over.
  const body = req.body;
  const items = Array.isArray(body) ? body : [body];
  const results = [];

  for (const item of items) {
    const niche = extractNiche(item);
    if (!niche) {
      results.push({ added: false, reason: 'لم يُعثر على حقل نيتش قابل للاستخدام في العنصر الوارد' });
      continue;
    }
    try {
      const gate = await runQualityGate(niche);
      if (!gate.passed) {
        results.push({ added: false, niche, reason: gate.reason });
        continue;
      }

      // Niche Safety Filter gate — quality_gate() only scores commercial
      // viability, it has no idea what a scam/trademark/medical niche is.
      // A niche that passes quality must also clear runSafetyCheck() before
      // it's written to OPPORTUNITIES.md (a human-facing dashboard file,
      // surfaced via /brain and /good-morning). Same fail-safe contract as
      // every other caller: a runSafetyCheck() failure is treated as blocked.
      const trendTitle = (typeof item.title === 'string' && item.title.trim()) || niche;
      let safety;
      try {
        safety = await runSafetyCheck({ niche, title: trendTitle, description: gate.reason || '' });
      } catch (err) {
        safety = {
          allowed: false,
          score: 0,
          risk_level: 'blocked',
          reasons: [{ category: 'filter_error', level: 'blocked', reason: 'safety filter unavailable — failing safe' }],
        };
      }

      if (safety.allowed === false) {
        console.log(`[trends] blocked by safety filter — niche: "${niche}" | title: "${trendTitle}" | risk: ${safety.risk_level}`);
        results.push({ added: false, niche, reason: 'safety_rejected', risk_level: safety.risk_level, safety_reasons: safety.reasons });
      } else {
        appendOpportunity(niche, gate);
        results.push({ added: true, niche, reason: gate.reason, safety: { score: safety.score, risk_level: safety.risk_level } });
      }
    } catch (err) {
      logTrendsError('quality_gate', err);
      results.push({ added: false, niche, error: err.message });
    }
  }

  res.json({ success: true, received: items.length, added: results.filter(r => r.added).length, results });
});

app.post('/api/market-analyze', (req, res) => {
  try {
    const pythonPath = detectPython();
    const scriptPath = path.join(__dirname, 'market_analyzer.py');
    if (!fs.existsSync(scriptPath)) {
      return res.json({ success: false, error: 'market_analyzer.py not found' });
    }
    const python = spawn(pythonPath, [scriptPath], { cwd: __dirname });
    let output = '', errOut = '';
    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('close', async () => {
      let data;
      try {
        data = JSON.parse(output.trim());
      } catch {
        return res.json({ success: false, error: 'Parse error: ' + output + errOut });
      }

      try {
        const niches = data.recommended_niches || [];

        // Niche Safety Filter gate: a niche must clear runSafetyCheck() before
        // it's ever shown to the user — market_analyzer.py's scoring has no
        // idea what a "scam trading" niche is, so it could otherwise sit at
        // position #1 unfiltered.
        const checked = await Promise.all(niches.map(async (n) => {
          try {
            const safety = await runSafetyCheck({
              niche: n.niche,
              title: n.niche,
              description: n.recommendation_reason || '',
            });
            return { n, safety };
          } catch (err) {
            // A single niche's safety check blowing up must never take
            // down the whole endpoint — fail that niche closed instead.
            return {
              n,
              safety: {
                allowed: false,
                score: 0,
                risk_level: 'blocked',
                reasons: [{ category: 'filter_error', level: 'blocked', reason: 'filter_error' }],
              },
            };
          }
        }));

        const approved_niches = [];
        const blocked_niches = [];
        for (const { n, safety } of checked) {
          if (safety.allowed === true) {
            approved_niches.push({ ...n, safety: { score: safety.score, risk_level: safety.risk_level } });
          } else {
            blocked_niches.push({ ...n, safety: { score: safety.score, risk_level: safety.risk_level, reasons: safety.reasons } });
          }
        }

        const lines = approved_niches.map((n, i) =>
          `${i + 1}. ${n.niche}\n   💰 $${n.avg_price} | Score: ${n.profit_score} | ${n.recommendation_reason}`
        );
        const summary = approved_niches.length
          ? [
              `📅 ${data.current_month} — ${data.seasonal_opportunity}`,
              `🔍 أفضل ${approved_niches.length} نيشات (من ${data.total_analyzed} محلَّل):`,
              ...lines
            ].join('\n')
          : '⚠️ جميع النيتشات المقترحة رُفضت من Niche Safety Filter. أعد التحليل.';

        res.json({
          success: true,
          summary,
          data: {
            ...data,
            recommended_niches: approved_niches,
            blocked_niches,
            safety_stats: {
              total: niches.length,
              approved: approved_niches.length,
              blocked: blocked_niches.length,
            },
          },
        });
      } catch (err) {
        res.json({ success: false, error: err.message });
      }
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// ── QA CHECK ──
app.post('/api/qa-check', (req, res) => {
  try {
    const pythonPath = detectPython();
    const scriptPath = path.join(__dirname, 'quality_doctor.py');
    if (!fs.existsSync(scriptPath)) {
      return res.json({ success: false, error: 'quality_doctor.py not found' });
    }
    const productData = JSON.stringify(req.body || {});
    const python = require('child_process').execFile(
      pythonPath, [scriptPath, productData],
      { cwd: __dirname },
      (err, stdout, stderr) => {
        try {
          const result = JSON.parse(stdout.trim());
          res.json({ success: true, ...result });
        } catch {
          res.json({ success: false, error: stderr || stdout || String(err) });
        }
      }
    );
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// ── FACTORY DOCTOR: HEALTH ──
// Read-only status of the factory's core components. Never mutates state —
// in particular this must NOT hit the n8n webhook (that would trigger a real
// Scout run); it only pings n8n's root to check reachability.
// Shared by /health and /good-morning so the two never drift out of sync.
// ── REALITY SCORECARD ──
// Ground-truth business state (Task 14) — reality.py reads config/reality.json
// (human-maintained: only a real KDP ASIN counts as "published") and
// finance_data.json (real recorded sales). Fail-safe: any spawn error,
// timeout, parse error, or non-zero exit is treated as CRITICAL — a broken
// truth-teller means we assume the worst, never the best.
function runReality(timeoutMs = 5000) {
  const FAIL_SAFE = (extra) => ({
    verdict: 'CRITICAL',
    reason: 'reality engine unavailable',
    ...(extra || {}),
  });

  return new Promise((resolve) => {
    let settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };

    let python;
    try {
      const pythonPath = detectPython();
      const scriptPath = path.join(__dirname, 'reality.py');
      python = spawn(pythonPath, [scriptPath], { cwd: __dirname });
    } catch (err) {
      resolve(FAIL_SAFE({ error: err.message }));
      return;
    }

    const timer = setTimeout(() => {
      try { python.kill(); } catch (_) { /* best effort */ }
      finish(FAIL_SAFE({ error: 'timeout' }));
    }, timeoutMs);

    let output = '', errOut = '';
    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });

    python.on('error', err => finish(FAIL_SAFE({ error: err.message })));

    python.on('close', code => {
      try {
        if (code !== 0) throw new Error(`reality.py exited ${code}: ${errOut}`);
        const result = JSON.parse(output.trim());
        if (typeof result.verdict !== 'string') throw new Error('malformed reality result');
        finish(result);
      } catch (err) {
        finish(FAIL_SAFE({ error: err.message }));
      }
    });

    try {
      python.stdin.end(); // reality.py takes no stdin input
    } catch (err) {
      finish(FAIL_SAFE({ error: err.message }));
    }
  });
}

app.get('/api/reality', async (req, res) => {
  res.json(await runReality());
});

async function computeHealthStatus() {
  const checks = {};

  // sensing_engine — is n8n reachable? Not fatal on its own: Scout already
  // degrades gracefully to its Groq-based fallback when n8n is unavailable.
  try {
    await withTimeout(fetch('http://localhost:5678'), 3000, 'n8n-health');
    checks.sensing_engine = { ok: true, severity: 'degraded', detail: 'n8n يستجيب على localhost:5678' };
  } catch (err) {
    checks.sensing_engine = { ok: false, severity: 'degraded', detail: `n8n غير متاح: ${err.message}` };
  }

  // book_generator — without this file nothing can be produced at all.
  const bookGenExists = fs.existsSync(path.join(__dirname, 'book_generator.py'));
  checks.book_generator = {
    ok: bookGenExists,
    severity: 'critical',
    detail: bookGenExists ? 'book_generator.py موجود' : 'book_generator.py غير موجود — لا يمكن توليد أي كتاب',
  };

  // finance — NOTE: the file actually read/written by /finance is
  // finance_data.json (see the Finance fix task) — data/finance.json is a
  // stale, unused leftover from before that fix, so it is intentionally not
  // what's checked here. A corrupt finance_data.json is not fatal: loadFin()
  // already quarantines and self-heals it on the next request.
  let financeOk = false;
  let financeDetail;
  try {
    if (!fs.existsSync(FINANCE_FILE)) {
      financeDetail = 'finance_data.json غير موجود (سيُنشأ تلقائياً عند أول طلب)';
    } else {
      JSON.parse(fs.readFileSync(FINANCE_FILE, 'utf8'));
      financeOk = true;
      financeDetail = 'JSON صالح';
    }
  } catch (err) {
    financeDetail = `JSON فاسد: ${err.message} (يُصلح تلقائياً عند أول طلب /finance)`;
  }
  checks.finance = { ok: financeOk, severity: 'degraded', detail: financeDetail };

  // books_folder — count of produced PDFs; missing folder is not fatal, it's
  // created automatically by generate_book() on first use.
  const booksDir = path.join(__dirname, 'books');
  let pdfCount = 0;
  let booksOk = true;
  let booksDetail;
  try {
    if (fs.existsSync(booksDir)) {
      pdfCount = fs.readdirSync(booksDir).filter(f => f.toLowerCase().endsWith('.pdf')).length;
      booksDetail = `${pdfCount} كتاب PDF`;
    } else {
      booksOk = false;
      booksDetail = 'مجلد books/ غير موجود بعد (سيُنشأ تلقائياً عند أول توليد)';
    }
  } catch (err) {
    booksOk = false;
    booksDetail = err.message;
  }
  checks.books_folder = { ok: booksOk, severity: 'degraded', count: pdfCount, detail: booksDetail };

  const failing = Object.values(checks).filter(c => !c.ok);
  let status = 'healthy';
  if (failing.some(c => c.severity === 'critical')) status = 'critical';
  else if (failing.length > 0) status = 'degraded';

  // Reality Scorecard override (Task 14): a factory with every cell green
  // but zero published books, or zero sales 30+ days after publishing, is
  // not "healthy" — self-awareness measures CELL health, not OUTCOMES. The
  // cell-based status above is preserved as-is when reality itself is OK
  // (or unreachable-but-not-worse); it's only overridden toward a worse
  // verdict, never softened.
  const reality = await runReality();
  let statusSource = 'cells';
  if (reality.verdict === 'CRITICAL') {
    status = 'critical';
    statusSource = 'reality';
  } else if (reality.verdict === 'WARNING') {
    status = 'warning';
    statusSource = 'reality';
  }

  return { status, status_source: statusSource, timestamp: new Date().toISOString(), checks, reality };
}

app.get('/health', async (req, res) => {
  res.json(await computeHealthStatus());
});

// ── FACTORY DOCTOR: SELF-HEALING LOOP STATUS ──
// Read-only view into factory_loop.js's own log (that script runs as a
// separate process — see factory_loop.js — so this route only ever reads a
// file; it never starts, stops, or depends on the loop being alive).
app.get('/factory-loop/status', (req, res) => {
  const logPath = path.join(__dirname, 'factory_loop.log');
  try {
    if (!fs.existsSync(logPath)) {
      return res.json({ likelyRunning: false, count: 0, entries: [], note: 'factory_loop.js لم يعمل بعد — لا يوجد سجل حتى الآن' });
    }
    const lines = fs.readFileSync(logPath, 'utf8').split('\n').filter(Boolean);
    const entries = lines.slice(-10).map(line => {
      try { return JSON.parse(line); } catch (_) { return { raw: line }; }
    });
    // NOTE: a log file existing only proves the loop ran at some point in the
    // past — this route has no PID/process handle, so it can't truly confirm
    // the loop is alive right now. "likelyRunning" is a heuristic: the loop
    // ticks every 10 minutes, so a last entry within 2x that window suggests
    // it's still going; older than that suggests it has stopped.
    const last = entries[entries.length - 1];
    const lastTimestamp = last && last.timestamp ? Date.parse(last.timestamp) : NaN;
    const lastTickAgoMs = Number.isFinite(lastTimestamp) ? Date.now() - lastTimestamp : null;
    const likelyRunning = lastTickAgoMs !== null && lastTickAgoMs < 20 * 60 * 1000;
    res.json({ likelyRunning, lastTickAgoMs, count: lines.length, entries });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ── GOOD MORNING: GALAXY'S DAILY BRIEFING ──
// One request, full factory picture — see GOOD_MORNING.md for the spec this
// implements. Every section degrades independently: if one file is missing
// or unreadable, that section reports it honestly instead of failing the
// whole briefing.
function readTopOpportunities(limit = 3) {
  const oppFile = path.join(__dirname, 'OPPORTUNITIES.md');
  if (!fs.existsSync(oppFile)) {
    return { items: [], note: 'OPPORTUNITIES.md غير موجود بعد — لا فرص مسجَّلة' };
  }
  const lines = fs.readFileSync(oppFile, 'utf8').split('\n');
  const re = /^-\s*\[(.+?)\]\s*(.+?)\s*—\s*(.+)$/;
  const items = [];
  for (const line of lines) {
    const m = line.match(re);
    if (m) items.push({ timestamp: m[1], niche: m[2].trim(), reason: m[3].trim() });
  }
  // NOTE: "top by traffic" as asked isn't possible with real data yet — no
  // trend-volume number exists anywhere in this system (n8n doesn't return
  // real Google Trends counts; see [4]/[8]/[11]'s documented gap). Most
  // recent entries are used as an honest stand-in, same pattern as
  // factory_loop.js's HUNT step — flagged here rather than silently
  // mislabeling recency as traffic.
  return {
    items: items.slice(-limit).reverse(),
    note: items.length ? 'لا يوجد رقم "ترافيك" حقيقي بعد — معروضة الأحدث بدل الأعلى ترافيكاً فعلياً' : 'لا فرص مسجَّلة بعد',
  };
}

function readLastLoopActions(limit = 10) {
  const logFile = path.join(__dirname, 'factory_loop.log');
  if (!fs.existsSync(logFile)) {
    return { entries: [], note: 'factory_loop.js لم يعمل بعد — لا يوجد سجل' };
  }
  const lines = fs.readFileSync(logFile, 'utf8').split('\n').filter(Boolean);
  const entries = lines.slice(-limit).map(line => {
    try { return JSON.parse(line); } catch (_) { return { raw: line }; }
  });
  return { entries };
}

function readNextDollarActions() {
  const statusFile = path.join(__dirname, 'FACTORY_STATUS.md');
  if (!fs.existsSync(statusFile)) return { text: null, note: 'FACTORY_STATUS.md غير موجود' };
  const content = fs.readFileSync(statusFile, 'utf8');
  const marker = '## 6. Next Dollar Actions';
  const idx = content.indexOf(marker);
  if (idx === -1) return { text: null, note: 'قسم "Next Dollar Actions" غير موجود في FACTORY_STATUS.md' };
  const rest = content.slice(idx + marker.length);
  const nextHeaderMatch = rest.match(/\n## /);
  const section = (nextHeaderMatch ? rest.slice(0, nextHeaderMatch.index) : rest).trim();
  return { text: section };
}

app.get('/good-morning', async (req, res) => {
  const [factoryStatus, opportunities, lastNightActions, nextDollar, awareness] = await Promise.all([
    computeHealthStatus().catch(err => ({ status: 'error', error: err.message })),
    Promise.resolve().then(() => readTopOpportunities(3)).catch(err => ({ items: [], note: `error: ${err.message}` })),
    Promise.resolve().then(() => readLastLoopActions(10)).catch(err => ({ entries: [], note: `error: ${err.message}` })),
    Promise.resolve().then(() => readNextDollarActions()).catch(err => ({ text: null, note: `error: ${err.message}` })),
    // CONSTITUTION.md §20: Galaxy sees the truth every morning, not just the
    // health check — the same honest verdict GET /awareness computes.
    selfAwareness.assessSelfAwareness().catch(err => ({ verdict: null, note: `error: ${err.message}` })),
  ]);

  res.json({
    success: true,
    generated_at: new Date().toISOString(),
    title: '🏭 OpenClaw Factory — Daily Briefing',
    factory_status: factoryStatus,
    top_opportunities: opportunities,
    last_night_actions: lastNightActions,
    next_dollar_actions: nextDollar,
    self_awareness: { verdict: awareness.verdict, growth: awareness.growth, weakest_cell: awareness.diagnosis ? awareness.diagnosis.weakest_cell : null },
  });
});

// ── PROFIT ORACLE ──
// Read-only view into profit_oracle.py's own output (that script runs
// on-demand or via factory_loop.js — this route never invokes it, it only
// reads golden_opportunities.json, the same way /factory-loop/status only
// reads factory_loop.log).
app.get('/oracle', (req, res) => {
  const jsonFile = path.join(__dirname, 'golden_opportunities.json');
  try {
    if (!fs.existsSync(jsonFile)) {
      return res.json({
        success: true, count: 0, top: [],
        note: 'لم يُشغَّل profit_oracle.py بعد — شغّله عبر: python profit_oracle.py --run',
      });
    }
    const data = JSON.parse(fs.readFileSync(jsonFile, 'utf8'));
    const results = Array.isArray(data.results) ? data.results : [];
    const golden = results.filter(r => r.verdict === 'GOLDEN'); // already sorted by profit_score desc
    res.json({
      success: true,
      generated_at: data.generated_at,
      golden_count: golden.length,
      total_scored: results.length,
      top: golden.slice(0, 5),
    });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// ── DUAL-INSPECTOR QUALITY SYSTEM ──
// Read-only view into inspectors.py's own log (CONSTITUTION.md §17). This
// route never runs an inspection itself — final_inspection() is invoked
// automatically inside book_generator.py's generate_book(), right after a
// product is written to disk; this only reads inspections.log afterward.
app.get('/inspections', (req, res) => {
  const logFile = path.join(__dirname, 'inspections.log');
  try {
    if (!fs.existsSync(logFile)) {
      return res.json({ success: true, count: 0, entries: [], note: 'لا فحوصات مسجَّلة بعد' });
    }
    const lines = fs.readFileSync(logFile, 'utf8').split('\n').filter(Boolean);
    const entries = lines.slice(-10).map(line => {
      try { return JSON.parse(line); } catch (_) { return { raw: line }; }
    }).reverse(); // most recent first
    res.json({ success: true, count: lines.length, entries });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// ── KNOWLEDGE BRAIN ──
// CONSTITUTION.md §18: "search the Brain before building." Read-only view of
// OpenClaw_Brain/'s real, current folder map — computed from disk every
// call, never a stale hardcoded copy. Optional ?q= does a keyword search
// across every .md file instead (see knowledge_brain.js).
app.get('/brain', (req, res) => {
  try {
    const q = req.query.q;
    if (q) {
      const results = knowledgeBrain.searchBrain(q);
      return res.json({ success: true, query: q, count: results.length, results });
    }
    const map = knowledgeBrain.getBrainMap();
    res.json({ success: true, ...map });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// ── GOLDEN HUNTER ──
// CONSTITUTION.md §19: Golden Hunter. Read-only — this route never runs
// market_hunter.py itself (that happens inside factory_loop.js's daily
// cycle, or manually via `python market_hunter.py --run`); it only reads
// the most recent entry from market_hunter_runs.log, the same pattern
// /inspections and /oracle already use for their own logs.
app.get('/hunter', (req, res) => {
  const logFile = path.join(__dirname, 'market_hunter_runs.log');
  try {
    if (!fs.existsSync(logFile)) {
      return res.json({
        success: true, count: 0, golden_catch: [],
        note: 'لم يُشغَّل market_hunter.py بعد — شغّله عبر: python market_hunter.py --run',
      });
    }
    const lines = fs.readFileSync(logFile, 'utf8').split('\n').filter(Boolean);
    const last = JSON.parse(lines[lines.length - 1]);
    res.json({
      success: true,
      timestamp: last.timestamp,
      scanned_count: last.scanned_count,
      skipped_count: last.skipped_count,
      golden_count: last.golden_count,
      golden_catch: last.golden_catch,
    });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// ── SELF-AWARENESS ──
// CONSTITUTION.md §20: "how am I doing, truthfully?" This computes a fresh
// assessment on every call (vitals + growth-vs-yesterday + honest
// diagnosis + verdict) but does NOT write to GROWTH_LOG.md itself — that
// write happens once daily from factory_loop.js, the same read-vs-write
// split /oracle and /hunter already use for their own logs.
app.get('/awareness', async (req, res) => {
  try {
    const assessment = await selfAwareness.assessSelfAwareness();
    res.json({ success: true, ...assessment });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// ── STATIC ──
// index.html is saved as UTF-16 LE with BOM (see CLAUDE.md's "index.html
// encoding" note) — deliberate, not something to convert. express.static's
// default index-file serving and a plain res.sendFile() both label it
// Content-Type: text/html; charset=utf-8 regardless of the file's real
// bytes, so every browser misrenders the whole page (every ASCII byte gets
// a null byte between it from the UTF-16 encoding, read as UTF-8 garbage/
// blank). sendIndexHtml() sets the correct charset explicitly instead.
function sendIndexHtml(res) {
  res.set('Content-Type', 'text/html; charset=utf-16le');
  res.sendFile(path.join(__dirname, 'index.html'));
}

app.get('/', (req, res) => sendIndexHtml(res));
app.use(express.static(path.join(__dirname), { index: false }));
app.get('/{*path}', (req, res) => {
  sendIndexHtml(res);
});

function detectPython() {
  const candidates = ['python3', 'python', 'py'];
  for (const cmd of candidates) {
    try {
      require('child_process').execSync(`${cmd} --version`, { stdio: 'ignore' });
      return cmd;
    } catch { }
  }
  return 'python';
}

app.listen(PORT, () => {
  console.log(`✅ OpenClaw Factory — http://localhost:${PORT}`);
  console.log(`🔧 Static dir: ${path.join(__dirname)}`);
});
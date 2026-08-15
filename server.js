const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const { spawn, execFile } = require('child_process');
const Groq = require('groq-sdk');
const knowledgeBrain = require('./knowledge_brain');
const selfAwareness = require('./self_awareness');
const dashboardData = require('./lib/dashboard_data');
const infrastructureIntelligence = require('./lib/infrastructure_intelligence');
const metricsLib = require('./lib/metrics');
const n8nNotify = require('./lib/n8n_notify');
const telegramDirect = require('./lib/telegram_direct');
const { nextSaleId } = require('./lib/next_sale_id');
const healthChecks = require('./lib/health_checks');
const { readJsonlEntries } = require('./lib/jsonl');
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

// CORS hardening (CTO+COO audit closure 2026-08-15): the prior permissive
// `cors()` reflected ANY origin. Every real caller (mission_control.html,
// dashboard.html, customer_site/*, public_site/*) uses same-origin relative
// /api/... fetches — there is no legitimate cross-origin consumer. origin:
// false sends no Access-Control-Allow-Origin, so browsers refuse any
// cross-origin request while same-origin calls are unaffected. A founder who
// later deliberately widens BIND_HOST must also revisit this deliberately.
app.use(cors({ origin: false }));
// verify callback stashes the exact raw request bytes onto req.rawBody
// before JSON-parsing -- needed only by POST /webhooks/paddle (real
// Paddle HMAC signatures are computed over the exact raw body, and
// re-serializing req.body would silently break verification on any
// key-order/whitespace difference). Every other route's behavior is
// completely unchanged -- req.body still parses exactly as before.
app.use(express.json({
  verify: (req, res, buf) => { req.rawBody = buf; },
}));

// ── MISSION CONTROL: simple password gate (Phase 8) ──
// Deliberately NOT express-session/cookie-parser — no new npm dependency
// for a single-operator local tool (per explicit direction: "simple
// password gate", not multi-user accounts/roles). A signed, in-memory-
// secret session token (crypto.createHmac), set as an httpOnly cookie;
// the secret is generated fresh every server start, so restarting the
// process invalidates every session — acceptable for a local tool, not a
// hosted multi-instance service.
//
// Scope, deliberately narrow: this gates ONLY /mission_control.html and
// /api/mission-control/* — every pre-existing route's security posture
// is left exactly as it was. Retroactively adding auth to the dozens of
// existing routes would be a much larger, riskier change to already-
// relied-upon behavior, and was not asked for.
const crypto = require('crypto');
const MISSION_CONTROL_SESSION_SECRET = crypto.randomBytes(32).toString('hex');
const MISSION_CONTROL_PASSWORD = process.env.MISSION_CONTROL_PASSWORD;

function signMissionControlSession(payload) {
  const mac = crypto.createHmac('sha256', MISSION_CONTROL_SESSION_SECRET).update(payload).digest('hex');
  return `${payload}.${mac}`;
}

function verifyMissionControlSession(token) {
  if (!token || !token.includes('.')) return false;
  const dot = token.lastIndexOf('.');
  const payload = token.slice(0, dot);
  const mac = token.slice(dot + 1);
  const expected = crypto.createHmac('sha256', MISSION_CONTROL_SESSION_SECRET).update(payload).digest('hex');
  try {
    return crypto.timingSafeEqual(Buffer.from(mac), Buffer.from(expected));
  } catch {
    return false;
  }
}

function parseCookies(req) {
  const header = req.headers.cookie;
  const out = {};
  if (!header) return out;
  for (const part of header.split(';')) {
    const idx = part.indexOf('=');
    if (idx === -1) continue;
    out[part.slice(0, idx).trim()] = decodeURIComponent(part.slice(idx + 1).trim());
  }
  return out;
}

function requireMissionControlAuth(req, res, next) {
  const cookies = parseCookies(req);
  if (verifyMissionControlSession(cookies.mc_session)) return next();
  // Path-based, not Accept-header-based: curl and fetch() both send
  // "Accept: */*" by default, which also satisfies req.accepts('html'),
  // so an Accept check would wrongly redirect API calls (including the
  // frontend's own fetch() calls on session expiry) to the login page
  // instead of returning JSON it can react to.
  //
  // req.originalUrl, not req.path: this middleware is also mounted via
  // app.use('/api/v1', requireMissionControlAuth, v1Router), and Express
  // rewrites req.path to be relative to the mount point inside a sub-
  // router (e.g. '/company-health', not '/api/v1/company-health') —
  // req.originalUrl always holds the real, full request path regardless
  // of mount depth.
  if (req.method === 'GET' && !req.originalUrl.startsWith('/api/')) {
    return res.redirect('/mission_control_login.html');
  }
  return res.status(401).json({ success: false, error: 'unauthenticated' });
}

// Enterprise Security & Cyber Defense Mission, Phase 2 (2026-07-23),
// finding 2.1: most routes had zero authentication, including a direct,
// unmetered proxy to the founder's real, paid Groq API key
// (/api/agent/:name). requireMissionControlAuth alone can't gate every
// route, because 4 of them are real, working internal callers with no
// browser session to present: factory_loop.js's own automated pipeline
// (/api/distribute, /api/sales/poll, /generate-book) and the
// 01_Market_Scout n8n workflow (/api/scout/run). Naively requiring a
// session on those 4 would silently break real, already-working
// automation, not fix a vulnerability -- exactly the "never introduce
// regressions" rule this whole mission runs under.
//
// INTERNAL_SERVICE_TOKEN (.env, generated once) is that other real
// credential: a shared secret only this process and its own known
// internal callers hold, sent as X-Internal-Token. Same trust model as
// MISSION_CONTROL_PASSWORD -- a single shared secret for a single-
// operator factory, not a fake multi-tenant auth system this factory
// doesn't need. If INTERNAL_SERVICE_TOKEN is ever unset (a fresh
// checkout before .env is configured), this fails CLOSED -- these 4
// routes require a real Mission Control session until it's set, the
// same as every other route below, never a silent unauthenticated
// fallback.
const INTERNAL_SERVICE_TOKEN = process.env.INTERNAL_SERVICE_TOKEN;

function timingSafeEqualStrings(a, b) {
  const bufA = Buffer.from(String(a));
  const bufB = Buffer.from(String(b));
  if (bufA.length !== bufB.length) return false;
  return crypto.timingSafeEqual(bufA, bufB);
}

function requireMissionControlOrInternalToken(req, res, next) {
  const cookies = parseCookies(req);
  if (verifyMissionControlSession(cookies.mc_session)) return next();
  const provided = req.headers['x-internal-token'];
  if (INTERNAL_SERVICE_TOKEN && provided && timingSafeEqualStrings(provided, INTERNAL_SERVICE_TOKEN)) {
    return next();
  }
  return res.status(401).json({ success: false, error: 'unauthenticated' });
}

// Security Mission Tracker finding 2.3 (2026-07-23): the password
// comparison below used to be a plain `!==` -- a real, if minor, timing
// side-channel -- and there was no brute-force/rate-limit protection on
// login at all. Real fix: reuse timingSafeEqualStrings() (the same
// helper requireMissionControlOrInternalToken() already uses for the
// internal-token comparison) for the password check, and a real,
// in-memory rate limiter -- the same bounded-sliding-window-of-real-
// timestamps pattern scripts/supervisor.js's own crash-loop guard
// already established, reset on success. Global, not per-IP: this
// factory is single-tenant (BIND_HOST=127.0.0.1, one real founder
// account) -- an IP-keyed limiter would add real complexity for a
// threat model this deployment doesn't actually have.
const LOGIN_MAX_ATTEMPTS = parseInt(process.env.MISSION_CONTROL_LOGIN_MAX_ATTEMPTS || '5', 10);
const LOGIN_WINDOW_MS = parseInt(process.env.MISSION_CONTROL_LOGIN_WINDOW_MS || String(15 * 60 * 1000), 10);
let loginFailureTimestamps = [];

function pruneLoginFailures() {
  const now = Date.now();
  loginFailureTimestamps = loginFailureTimestamps.filter(t => now - t < LOGIN_WINDOW_MS);
}

app.post('/api/mission-control/login', (req, res) => {
  if (!MISSION_CONTROL_PASSWORD) {
    return res.status(500).json({
      success: false,
      error: 'MISSION_CONTROL_PASSWORD غير مُعرَّف في .env — أضِفه أولاً (سطر واحد: MISSION_CONTROL_PASSWORD=...)',
    });
  }

  pruneLoginFailures();
  if (loginFailureTimestamps.length >= LOGIN_MAX_ATTEMPTS) {
    const retryAfterMs = LOGIN_WINDOW_MS - (Date.now() - loginFailureTimestamps[0]);
    return res.status(429).json({
      success: false,
      error: `محاولات كثيرة جداً — أعد المحاولة بعد ${Math.max(1, Math.ceil(retryAfterMs / 1000))} ثانية`,
    });
  }

  const { password } = req.body || {};
  if (!timingSafeEqualStrings(password || '', MISSION_CONTROL_PASSWORD)) {
    loginFailureTimestamps.push(Date.now());
    return res.status(401).json({ success: false, error: 'كلمة مرور خاطئة' });
  }

  loginFailureTimestamps = [];
  const token = signMissionControlSession(`mc|${Date.now()}`);
  res.cookie('mc_session', token, { httpOnly: true, sameSite: 'lax', maxAge: 12 * 60 * 60 * 1000 });
  res.json({ success: true });
});

app.post('/api/mission-control/logout', (req, res) => {
  res.clearCookie('mc_session');
  res.json({ success: true });
});

app.get('/api/mission-control/session', (req, res) => {
  const cookies = parseCookies(req);
  res.json({ success: true, authenticated: verifyMissionControlSession(cookies.mc_session) });
});

app.get('/mission_control.html', requireMissionControlAuth, (req, res) => {
  res.sendFile(path.join(__dirname, 'mission_control.html'));
});

// Galaxy Forge Executive Mission Control v1 (2026-07-24): a separate,
// purpose-built executive presentation layer over the exact same real
// /api/v1/* services above — not a replacement for mission_control.html
// (the day-to-day Arabic ops console), a distinct dark, English,
// boardroom-facing view. Same auth as every other Mission Control page.
app.get('/mission_control_executive_v1.html', requireMissionControlAuth, (req, res) => {
  res.sendFile(path.join(__dirname, 'mission_control_executive_v1.html'));
});

// ── UNIFIED SERVICE LAYER (Phase 8 — Unified Service Layer) ──
// Every core capability exposed through one stable, versioned internal
// API: GET /api/v1/<service> (data) + GET /api/v1/<service>/health
// (liveness). Reuse only — every handler below calls straight into an
// already-built, already-tested module; nothing here computes a new
// score, decision, or metric. Gated by the exact same
// requireMissionControlAuth built above (no second auth mechanism —
// "authentication-ready" means reusing the one that exists, not
// inventing a parallel one).

const SERVICE_LOG_DIR = path.join(__dirname, 'logs');
const SERVICE_LOG_PATH = path.join(SERVICE_LOG_DIR, 'service_layer.log');

// Structured logging: one JSON line per service call, real fields only
// (service, path, status, duration — never a fabricated metric). Never
// allowed to break the request it's logging.
function logServiceCall(entry) {
  const line = JSON.stringify({ timestamp: new Date().toISOString(), ...entry });
  try {
    fs.mkdirSync(SERVICE_LOG_DIR, { recursive: true });
    fs.appendFileSync(SERVICE_LOG_PATH, line + '\n');
  } catch { /* logging must never break a request */ }
  console.log(`[service_layer] ${line}`);
}

// Phase 10B (Production Hardening): shared timeout guard for every
// mission_control_api.py subprocess this file spawns. Without this, a
// genuinely hung subprocess (network stall, an infinite loop) never
// emits 'close', so runPythonService's promise never settles (an HTTP
// request hangs forever) and an async action's job never leaves
// 'running' — which permanently wedges the single-writer guard on that
// action until the whole server restarts. Kills the process and lets
// the caller's own 'close'/'error' handling produce a clear timeout
// error instead of an indefinite hang.
function killAfterTimeout(childProcess, timeoutMs, onTimeout) {
  const timer = setTimeout(() => {
    onTimeout();
    childProcess.kill();
  }, timeoutMs);
  const clear = () => clearTimeout(timer);
  childProcess.once('close', clear);
  childProcess.once('error', clear);
  return clear;
}

// Fast, local-file-only services (opportunities/production/revenue/
// automation/decision_history/system_configuration) — generous but
// bounded; none of these normally take more than a couple of seconds.
const PYTHON_SERVICE_TIMEOUT_MS = 30000;

// Single shared bridge to mission_control_api.py's CLI dispatcher —
// replaces the old ad hoc inline spawn/parse block that used to live
// only in /api/mission-control/:section (Phase 8 Mission Control), so
// there is exactly one place that knows how to run a Python service,
// not two copies of the same spawn/parse glue.
// `timeoutMs` (Strategic Intelligence Core, 2026-07-29): optional
// override, defaulting to PYTHON_SERVICE_TIMEOUT_MS -- every existing
// caller is unaffected. Added because executive_brief is a real,
// disclosed outlier: it aggregates ceo_dashboard() + evolution_report,
// each independently already a real ~20s full-portfolio computation,
// so the shared 30s default was measured to time it out (confirmed via
// a live run: 500 "executive_brief timed out after 30000ms").
function runPythonService(section, extraArgs = [], timeoutMs = PYTHON_SERVICE_TIMEOUT_MS) {
  return new Promise((resolve, reject) => {
    const pythonPath = detectPython();
    const scriptPath = path.join(__dirname, 'mission_control_api.py');
    const python = spawn(pythonPath, [scriptPath, section, ...extraArgs], { cwd: __dirname });
    let output = '', errOut = '', timedOut = false;
    killAfterTimeout(python, timeoutMs, () => { timedOut = true; });
    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', reject);
    python.on('close', () => {
      if (timedOut) return reject(new Error(`${section} timed out after ${timeoutMs}ms`));
      let parsed;
      try {
        parsed = JSON.parse(output.trim());
      } catch {
        return reject(new Error(`parse error: ${output}${errOut}`));
      }
      if (parsed.success === false) return reject(new Error(parsed.error || 'python endpoint reported failure'));
      resolve(parsed);
    });
  });
}

// Galaxy Forge v1.0 "World-Class Quality" directive (2026-07-25),
// Performance bucket: "cache expensive operations... optimize Python/
// Node communication." Same real pattern already adopted for
// runRealityCached() (reality.py was costing 3-4 real seconds per call
// with zero caching) -- applied here to runPythonService() itself, the
// one real chokepoint every Python-backed SERVICE_REGISTRY read spawns
// through. Every service wrapped with this (see call sites below) is a
// pure read of slow-moving business state -- decisions, production,
// revenue, knowledge graph, AI capability -- never per-request-sensitive,
// and independently measured (Mission Control CEO review, ADR-124) at
// 1-14 real seconds per call. A short TTL removes the redundant spawn
// cost without ever serving meaningfully stale data.
//
// Deliberately NOT applied to runPythonService() itself, nor to every
// call site: several existing callers are real MUTATIONS (e.g.
// ai_capability_request, resolve_recovery) or route through the
// separate, already-job-tracked ACTION_REGISTRY -- caching those would
// be a real correctness bug (a mutation silently not re-executing on a
// repeat call inside the TTL window), not a performance win. Only the
// confirmed pure-read SERVICE_REGISTRY handlers below use this wrapper;
// runPythonService() itself stays available, uncached, for every other
// real caller exactly as before.
const PYTHON_SERVICE_CACHE_TTL_MS = 20000;
const pythonServiceCache = new Map(); // "section|args" -> { result, expiresAt }

// Execution Roadmap Phase 2 (ADR-174, 2026-08-05): real request-coalescing,
// closing the operational risk ADR-168's own text disclosed and left
// unfixed ("no request-coalescing exists... an operator leaving the panel
// open could pile up overlapping subprocesses"). For the heaviest panels
// (Truth Registry ~255-485s, Strategic Planning ~70s, etc.) two requests
// landing seconds apart -- two browser tabs, an accidental double-click, a
// page reload during a slow first load -- used to each spawn their own
// full-cost Python subprocess computing the exact same real answer. Now
// the second request awaits the first's already-in-flight promise instead.
// Deliberately keyed identically to pythonServiceCache (same "section|args"
// key) so it only ever coalesces truly-identical concurrent calls, never a
// different section or different args.
const pythonServiceInFlight = new Map(); // "section|args" -> Promise

// `req` is optional -- passed through so a caller can force a real,
// uncached re-fetch via `?fresh=1` (Mission Control's own Refresh button
// does this: a founder clicking "Refresh" should always get a genuinely
// fresh read, never a stale cached one, even inside the TTL window).
// `?fresh=1` also skips coalescing -- a founder explicitly asking for a
// fresh read should never be handed someone else's in-flight result.
function runPythonServiceCached(section, extraArgs = [], req = null, timeoutMs = PYTHON_SERVICE_TIMEOUT_MS) {
  const bypass = !!(req && req.query && (req.query.fresh === '1' || req.query.fresh === 'true'));
  const key = section + '|' + JSON.stringify(extraArgs);
  if (!bypass) {
    const cached = pythonServiceCache.get(key);
    if (cached && Date.now() < cached.expiresAt) return Promise.resolve(cached.result);
    const inFlight = pythonServiceInFlight.get(key);
    if (inFlight) return inFlight;
  }
  const promise = runPythonService(section, extraArgs, timeoutMs).then(result => {
    pythonServiceCache.set(key, { result, expiresAt: Date.now() + PYTHON_SERVICE_CACHE_TTL_MS });
    return result;
  }).finally(() => {
    pythonServiceInFlight.delete(key);
  });
  if (!bypass) pythonServiceInFlight.set(key, promise);
  return promise;
}

// Cheap dependency check, not a full data run: confirms the Python
// interpreter is resolvable and the dispatcher script exists on disk.
// Deliberately does NOT spawn mission_control_api.py itself — that would
// make every health poll pay for a real subprocess + module import just
// to answer "is this wired up", which is a different question from "is
// the data fresh".
function pythonHealthCheck(section) {
  return async () => {
    const scriptPath = path.join(__dirname, 'mission_control_api.py');
    if (!fs.existsSync(scriptPath)) {
      return { status: 'error', detail: 'mission_control_api.py not found on disk' };
    }
    const pythonPath = detectPython();
    return {
      status: 'ok',
      detail: `dependency check only (not a full data run): python=${pythonPath}, script=mission_control_api.py, section=${section}`,
    };
  };
}

// For JS-backed services: runs the same real, cheap read the data
// endpoint itself would use, and reports whether it threw.
function fsHealthCheck(probeFn, label) {
  return async () => {
    probeFn();
    return { status: 'ok', detail: label };
  };
}

async function companyHealthService() {
  // Standing charter follow-up — same fix as GET /api/dashboard/good-morning:
  // avoid assessSelfAwareness()'s own redundant self-fetch of the health
  // object this function already computed a line earlier.
  const health = await computeHealthStatus().catch(err => ({ status: 'error', error: err.message }));
  const awareness = await selfAwareness.assessSelfAwareness(new Date(), health).catch(err => ({ verdict: null, error: err.message }));
  const needsAttention = dashboardData.readAttentionFlag();
  const risk = dashboardData.deriveRiskLevel(health, needsAttention);
  const current_priorities = readNextDollarActions();
  // Additive field (Phase 9 — Mission Control Operations): the real
  // automation/production/system events feed Mission Control's activity
  // timeline reads, merged client-side with GET /api/v1/actions' user-
  // action jobs. Same function GET /api/dashboard already exposes —
  // reused, not recomputed.
  const activity = dashboardData.readActivityTimeline({});
  return { health, risk, self_awareness: awareness, current_priorities, activity };
}

// Executive Score (Executive Intelligence Core, Round 6, 2026-07-29) --
// merges executive_score.py's Python-side real sub-scores with the two
// JS-native real signals it can't reach across the language boundary
// (Operational Stability: the same computeHealthStatus() every other
// health surface already trusts, including the Reality Scorecard
// override; Customer Happiness: real average review rating, scaled to
// 0-100). "overall" is a transparent average of only the real (non-
// Unknown) sub-scores, computed fresh here -- same value_engine.py/
// reality.py precedent this whole module follows: never a single
// invented number, an honest Unknown count always disclosed alongside it.
async function executiveScoreService(req) {
  const pythonResult = await runPythonServiceCached('executive_score', [], req);
  const subScores = { ...pythonResult.sub_scores };

  const health = await computeHealthStatus().catch(err => ({ status: 'error', error: err.message }));
  const HEALTH_STATUS_MAP = { healthy: 100, degraded: 50, critical: 0 };
  subScores.operational_stability = (health.status in HEALTH_STATUS_MAP)
    ? { value: HEALTH_STATUS_MAP[health.status], source: 'server.js computeHealthStatus() (real infra checks + Reality Scorecard override, never softened)' }
    : { value: 'Unknown', reason: `computeHealthStatus() رجع حالة غير متوقَّعة أو تعذّر الوصول: ${health.status}` };

  const reviews = dashboardData.readCustomerReviewsSummary();
  subScores.customer_happiness = (reviews.average_rating != null)
    ? { value: Math.round(reviews.average_rating / 5 * 100), source: 'lib/dashboard_data.js readCustomerReviewsSummary() (average_rating, 1-5 scaled to 0-100)', detail: reviews }
    : { value: 'Unknown', reason: reviews.note || 'لا مراجعات عملاء حقيقية بعد' };

  const numericValues = Object.values(subScores).filter(s => typeof s.value === 'number').map(s => s.value);
  const unknownCount = Object.values(subScores).filter(s => s.value === 'Unknown').length;
  const overall = numericValues.length ? Math.round(numericValues.reduce((a, b) => a + b, 0) / numericValues.length) : 'Unknown';

  return {
    sub_scores: subScores,
    overall,
    overall_note: `متوسط شفّاف لـ ${numericValues.length} من ${Object.keys(subScores).length} مكوّنات حقيقية معروفة اليوم — ${unknownCount} مكوّن غير معروف بصدق (لا بيانات حقيقية كافية بعد)، لم يُدرَج في المتوسط ولم يُفترَض صفراً. لا يُستخدَم هذا الرقم في أي بوابة قبول/رفض حقيقية — معلوماتي فقط.`,
    generated_at: new Date().toISOString(),
  };
}

// Continuous Trust & Resilience Monitoring (2026-07-29): merges
// resilience_monitor.py's real Python-side findings (safe_mode,
// publish_protection, customer_risk, security_drift, health_trend) with
// the 2 JS-native signals (storage_integrity from the same
// computeHealthStatus() operational_stability already trusts;
// customer reviews/support tickets from lib/dashboard_data.js) --
// exact same merge pattern executiveScoreService() already established.
// Informational only; never gates anything.
const RESILIENCE_SEVERITY_SCORE = { informational: 100, warning: 60, critical: 20, emergency: 0 };

// CEO Home (ADR-184, 2026-08-07): "Company Health Score" is the one
// field ceo_home.py deliberately does not compute itself --
// computeHealthStatus() is JS-only, no Python port exists, same
// resilience-status merge pattern below. Cached like every other
// service (60s window, matches Mission Control's own polling cadence,
// so the 60-second-glance page never re-runs a fresh scan per view).
async function ceoHomeService(req) {
  const pythonResult = await runPythonServiceCached('ceo_home_briefing', [], req);
  const health = await computeHealthStatus().catch(err => ({ status: 'error', checks: {}, error: err.message }));
  return {
    ...pythonResult,
    company_health: { status: health.status, status_source: health.status_source, checks_summary: health.checks ? Object.keys(health.checks).length : 0 },
  };
}

async function resilienceStatusService(req) {
  const pythonResult = await runPythonServiceCached('resilience_status', [], req);
  const findings = [...(pythonResult.findings || [])];

  const health = await computeHealthStatus().catch(err => ({ status: 'error', checks: {}, error: err.message }));
  const storageIntegrity = health.checks && health.checks.storage_integrity;
  if (storageIntegrity) {
    findings.push({
      area: 'data_integrity:storage',
      severity: storageIntegrity.ok ? 'informational' : (storageIntegrity.severity === 'critical' ? 'critical' : 'warning'),
      detail: storageIntegrity.detail, evidence: storageIntegrity, data_available: true,
    });
  } else {
    findings.push({ area: 'data_integrity:storage', severity: 'informational', detail: 'تعذّر تشغيل فحص storage_integrity', evidence: {}, data_available: false });
  }

  const reviews = dashboardData.readCustomerReviewsSummary();
  if (reviews.average_rating != null) {
    const severity = reviews.average_rating < 3 ? 'critical' : (reviews.average_rating < 4 ? 'warning' : 'informational');
    findings.push({ area: 'customer_trust:reviews', severity, detail: `متوسط تقييم حقيقي ${reviews.average_rating} (${reviews.count} مراجعة)`, evidence: reviews, data_available: true });
  } else {
    findings.push({ area: 'customer_trust:reviews', severity: 'informational', detail: reviews.note || 'لا مراجعات عملاء حقيقية بعد', evidence: {}, data_available: false });
  }

  const tickets = dashboardData.readSupportTicketSummary();
  if (tickets.count > 0) {
    const severity = tickets.open_count >= 5 ? 'critical' : (tickets.open_count >= 1 ? 'warning' : 'informational');
    findings.push({ area: 'customer_trust:support_tickets', severity, detail: `${tickets.open_count} تذكرة مفتوحة حقيقية من أصل ${tickets.count}`, evidence: tickets, data_available: true });
  } else {
    findings.push({ area: 'customer_trust:support_tickets', severity: 'informational', detail: tickets.note || 'لا تذاكر دعم حقيقية بعد', evidence: {}, data_available: false });
  }

  const activeAlerts = findings.filter(f => ['warning', 'critical', 'emergency'].includes(f.severity));
  const scored = findings.filter(f => f.data_available);
  const resilienceScore = scored.length
    ? Math.round(scored.reduce((sum, f) => sum + RESILIENCE_SEVERITY_SCORE[f.severity], 0) / scored.length)
    : 'Unknown';

  return {
    findings,
    active_alerts: activeAlerts,
    resilience_score: resilienceScore,
    resilience_score_note: `متوسط شفّاف لـ ${scored.length} من ${findings.length} مجالات مُقيَّمة فعلياً اليوم (Python + JS مدمجان) — ${findings.length - scored.length} بلا بيانات حقيقية بعد، لم تُدرَج في المتوسط. معلوماتي فقط — لا يُستخدَم في أي بوابة قبول/رفض حقيقية.`,
    generated_at: new Date().toISOString(),
  };
}

async function knowledgeBaseService(req) {
  const q = req.query.q;
  if (q) {
    const results = knowledgeBrain.searchBrain(q);
    return { query: q, count: results.length, results };
  }
  return knowledgeBrain.getBrainMap();
}

async function alertsService() {
  return {
    needs_attention: dashboardData.readAttentionFlag(),
    needs_review: dashboardData.readReviewFlag(),
  };
}

// Galaxy Forge Executive Mission Control v1 (2026-07-24): 4 new, thin,
// read-only services -- zero new engines, each reuses a real, already-
// existing data source verbatim. "No verified data" is returned honestly
// wherever the real source is genuinely empty or unavailable, never a
// fabricated placeholder.

const EVIDENCE_PAYMENT_TYPES = new Set(['complaining_review', 'paid_job_posting', 'freelancer_agency_pricing', 'subscription_escape']);

async function evidenceEngineService() {
  const evidencePath = path.join(__dirname, 'data', 'market_evidence.jsonl');
  if (!fs.existsSync(evidencePath)) {
    return { total_events: 0, niches_with_evidence: 0, by_event_type: {}, payment_evidence_events: 0, note: 'السجل فارغ حقيقةً — لا أحداث دليل سوق مسجَّلة بعد لأي نيتش' };
  }
  const events = readJsonlEntries(evidencePath);
  const byType = {};
  const niches = new Set();
  let paymentCount = 0;
  for (const e of events) {
    byType[e.event_type] = (byType[e.event_type] || 0) + 1;
    if (e.niche) niches.add(e.niche);
    if (EVIDENCE_PAYMENT_TYPES.has(e.event_type)) paymentCount += 1;
  }
  return {
    total_events: events.length,
    niches_with_evidence: niches.size,
    by_event_type: byType,
    payment_evidence_events: paymentCount,
  };
}

function schedulerStatusService() {
  return new Promise((resolve) => {
    if (process.platform !== 'win32') {
      resolve({ available: false, note: 'فحص المجدول مبني لـ Windows فقط اليوم — لا نشر آخر لاختباره بعد' });
      return;
    }
    const psCommand = [
      "$t = Get-ScheduledTask -TaskName 'OpenClaw-WeeklyPublicReport' -ErrorAction SilentlyContinue;",
      "if ($t) {",
      "  $trig = $t.Triggers | Select-Object -First 1;",
      "  [PSCustomObject]@{",
      "    TaskName = $t.TaskName; State = $t.State.ToString(); Enabled = $t.Settings.Enabled;",
      "    StartBoundary = $trig.StartBoundary; DaysOfWeek = $trig.DaysOfWeek;",
      "  } | ConvertTo-Json",
      "}",
    ].join(' ');
    execFile('powershell', ['-NoProfile', '-Command', psCommand], { timeout: 5000 }, (err, stdout) => {
      if (err || !stdout || !stdout.trim()) {
        resolve({ available: false, note: 'تعذّر العثور على المهمة المجدولة الحقيقية في Windows Task Scheduler، أو خطأ في الاستعلام' });
        return;
      }
      try {
        const parsed = JSON.parse(stdout);
        resolve({
          available: true, task_name: parsed.TaskName, state: parsed.State, enabled: parsed.Enabled,
          next_trigger_days_of_week_bitmask: parsed.DaysOfWeek, start_boundary: parsed.StartBoundary,
        });
      } catch {
        resolve({ available: false, note: 'تعذّر تحليل استجابة PowerShell الحقيقية' });
      }
    });
  });
}

async function recentAdrDecisionsService() {
  const govDir = path.join(__dirname, 'OpenClaw_Brain', '00_Governance');
  if (!fs.existsSync(govDir)) {
    return { total: 0, recent: [], note: 'مجلد الحوكمة غير موجود' };
  }
  const files = fs.readdirSync(govDir).filter((f) => /^ADR-\d+/.test(f));
  const parsed = files.map((f) => {
    const match = f.match(/^ADR-(\d+)/);
    const number = match ? parseInt(match[1], 10) : 0;
    let title = f, date = null, status = null;
    try {
      const content = fs.readFileSync(path.join(govDir, f), 'utf8');
      const lines = content.split('\n');
      const h1 = lines.find((l) => l.startsWith('# '));
      if (h1) title = h1.replace(/^#\s*/, '').trim();
      const dateLine = lines.find((l) => l.startsWith('**Date:**'));
      if (dateLine) date = dateLine.replace('**Date:**', '').trim();
      const statusLine = lines.find((l) => l.startsWith('**Status:**'));
      if (statusLine) status = statusLine.replace('**Status:**', '').trim();
    } catch { /* a single unreadable ADR file must never break the whole listing */ }
    return { number, filename: f, title, date, status };
  }).sort((a, b) => b.number - a.number);
  return { total: parsed.length, recent: parsed.slice(0, 20) };
}

const SYSTEM_LOG_FILES = ['factory_loop.log', 'scout_runs.log', 'finance_errors.log', 'supervisor.log', 'server_crashes.log'];

async function systemLogsService() {
  const result = {};
  for (const f of SYSTEM_LOG_FILES) {
    const p = path.join(__dirname, f);
    if (!fs.existsSync(p)) { result[f] = { exists: false }; continue; }
    try {
      const lines = fs.readFileSync(p, 'utf8').split('\n').filter(Boolean);
      result[f] = { exists: true, total_lines: lines.length, last_lines: lines.slice(-20) };
    } catch (e) {
      result[f] = { exists: true, error: e.message };
    }
  }
  return result;
}

// EOS Phase 1 (2026-07-19): "show only decisions that require founder
// approval; everything else should operate autonomously." Merges the
// Python-side half (blocked channels + DEFERRED decisions,
// founder_console.py) with two already-real JS-native reads —
// dashboardData.readAttentionFlag()/readReviewFlag() (written by
// factory_loop.js's real checkNeedsAttention()/checkPendingReview() on
// real state transitions) and a BLOCKERS.md read (same markdown-scrape
// technique readNextDollarActions() already uses on FACTORY_STATUS.md).
// Zero new judgment — pure assembly of already-real signals.
function readBlockersFile() {
  const p = path.join(__dirname, 'BLOCKERS.md');
  if (!fs.existsSync(p)) return { text: null, note: 'BLOCKERS.md غير موجود' };
  try {
    return { text: fs.readFileSync(p, 'utf8') };
  } catch (err) {
    return { text: null, note: `تعذّر قراءة BLOCKERS.md: ${err.message}` };
  }
}

async function founderConsoleService() {
  const partial = await runPythonService('founder_console');
  return {
    blocked_channels: partial.blocked_channels || [],
    autonomous_channels: partial.autonomous_channels || [],
    pending_decisions: partial.pending_decisions || [],
    attention_flag: dashboardData.readAttentionFlag(),
    review_flag: dashboardData.readReviewFlag(),
    blockers: readBlockersFile(),
  };
}

async function publishingStatusService(req) {
  const production = await runPythonServiceCached('production', [], req);
  const dossiers = production.dossiers || [];
  return {
    processed: production.processed,
    reason: production.reason || null,
    publishing: dossiers.map(d => ({
      production_id: d.production_id,
      niche: d.niche,
      checklist: d.publishing_checklist || [],
    })),
  };
}

const SERVICE_REGISTRY = [
  {
    name: 'company-health',
    description: 'Overall factory health status, derived risk level, self-awareness verdict, and current next-dollar priorities.',
    reused: 'server.js computeHealthStatus() + self_awareness.js assessSelfAwareness() + lib/dashboard_data.js deriveRiskLevel()/readAttentionFlag()/readActivityTimeline() + server.js readNextDollarActions() — identical composition to the pre-existing GET /api/dashboard.',
    handler: companyHealthService,
    health: fsHealthCheck(() => dashboardData.readAttentionFlag(), 'dashboardData module reachable, NEEDS_ATTENTION.md read check ok'),
  },
  {
    // CEO Home (ADR-184, 2026-08-07): the founder's EOS directive's
    // literal 60-second test. Pure citation over 8 already-real
    // modules/ledgers (commercial_readiness.py, the daily evidence
    // ledger, decisions.jsonl, finance_data.json, ai_cost_log.jsonl,
    // incidents.jsonl, executive_directives.jsonl, ai_capability
    // registry) plus the real GET /health check -- zero new judgment
    // engine, deliberately fast (no fresh multi-minute scans).
    name: 'ceo-home',
    description: "The single 60-second executive briefing: company health, commercial/financial/technical/marketing/legal/global/operational readiness, AI systems status, open critical risks, revenue/expenses/cash flow, products ready/selling/waiting, the highest-ROI real opportunity, and today's real executive recommendation. Every field cites a real, already-computed source -- never fabricated, never re-scanned live just to render this page.",
    reused: 'ceo_home.py::build_ceo_home_briefing() merged with server.js computeHealthStatus() -- same merge pattern as resilience-status/executive-score.',
    handler: ceoHomeService,
    health: pythonHealthCheck('ceo_home_briefing'),
  },
  {
    // EOS Decision Feed (ADR-186, 2026-08-07): reshapes 4 already-real
    // engines into one consistent 9-field recommendation card shape --
    // zero new judgment/scoring, zero fabricated ROI/time-to-execute.
    name: 'eos-decision-feed',
    description: "Every open real recommendation the company currently has, each carrying Problem/Evidence/Business impact/Financial impact/Confidence/Recommended action/Estimated ROI/Time to execute/Priority -- sourced from executive_brain.py (today's arbitrated directive), resilience_monitor.py (active critical/emergency risks), commercial_readiness.py (the lowest-scoring readiness dimension), and goos.py (top-ranked unbuilt opportunities). Fields with no real signal anywhere in this factory read 'Unknown', never a fabricated number.",
    reused: 'eos_decision_feed.py::build_eos_decision_feed(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('eos_decision_feed', [], req),
    health: pythonHealthCheck('eos_decision_feed'),
  },
  {
    // Global Business Development Division (ADR-188, 2026-08-07):
    // founder's explicit Golden Rule override, matching the ADR-149/150
    // precedent for Affiliate Commerce. Real, WebSearch-verified
    // opportunity registry, never fabricated per the directive's own
    // "never recommend partnerships without evidence" rule.
    name: 'business-development-dashboard',
    description: "Real partnership/affiliate/integration opportunity registry across 19 named platforms (Amazon, Gumroad, Paddle, Etsy, Shopify, Creative Market, Envato, Adobe, Microsoft, Google, OpenAI, Anthropic, Stripe, Notion, Canva, Figma, GitHub, Zapier, n8n) -- every entry cites real, WebSearch-verified program evidence or is honestly marked DISCOVERY. Top 20 partnership / Top 10 affiliate / Top 10 integration / Top 10 recurring-revenue opportunities, plus the real CRM-style pipeline board (Discovery/Evaluation/Preparation/Negotiation/Implementation/Active/Optimization).",
    reused: 'business_development.py::build_business_development_dashboard(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('business_development_dashboard', [], req),
    health: pythonHealthCheck('business_development_dashboard'),
  },
  {
    // Product Readiness Score (ADR-199, 2026-08-07): the one genuine,
    // buildable gap READINESS_SCORE_ENGINE.md (Phase 9) named --
    // threads the 3 already-per-product real scores through instead of
    // leaving them scattered across 3 modules. Live for the one real
    // shipped product.
    name: 'eu-ai-act-readiness-score',
    description: "Real, per-product Overall Readiness for the EU AI Act Compliance Toolkit -- averages only the 3 dimensions with a real per-product signal (technical/commercial/strategic), honestly excluding customer/automation/security (no real per-product signal exists for any of them anywhere in this factory).",
    reused: 'product_readiness_score.py::compute_product_readiness_score(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('eu_ai_act_readiness_score', [], req),
    health: pythonHealthCheck('eu_ai_act_readiness_score'),
  },
  {
    // Trust & Excellence Constitution (ADR-189, 2026-08-07): pure
    // citation over 6 already-real enforcement mechanisms -- same
    // on-demand view the weekly export now also includes.
    name: 'trust-audit-report',
    description: "Weekly Trust Audit: potential misleading claims, product weaknesses (the real REJECT_IF_FAIL gate), customer risks, quality regressions (honestly disclosed as having no real trend metric), reputation risks, security risks, ethical risks, and recent real QUARANTINE.md rejection activity. Every section cites an already-real enforcement mechanism -- zero new judgment engine, zero fabricated risk scores.",
    reused: 'trust_audit.py::build_trust_audit_report(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('trust_audit_report', [], req),
    health: pythonHealthCheck('trust_audit_report'),
  },
  {
    // Golden Hunter Room (ADR-192, 2026-08-07): "Galaxy Forge becomes
    // the visual brain of Golden Hunter" -- CEO View over
    // goos.py::rank_build_candidates(), never a new scoring engine.
    name: 'golden-hunter-room',
    description: "The CEO's window into Golden Hunter: best opportunity today, second best, the highest real long-term-potential candidate (ranked by real ROI score, never a fabricated dollar figure), and which candidates should be ignored -- reshapes goos.py::rank_build_candidates() into the founder's named CEO View questions.",
    reused: 'golden_hunter_room.py::ceo_view(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('golden_hunter_room', [], req),
    health: pythonHealthCheck('golden_hunter_room'),
  },
  {
    name: 'market-intelligence',
    description: 'The most recent real market intelligence analysis (scores, risk, customer pain, pricing, AI CEO verdict).',
    reused: 'lib/dashboard_data.js readLatestMarketIntelligence() — same field this session already confirmed is served by GET /api/dashboard.',
    handler: async () => ({ latest: dashboardData.readLatestMarketIntelligence() }),
    health: fsHealthCheck(() => dashboardData.readLatestMarketIntelligence(), 'market_intelligence_analyses.jsonl read check ok'),
  },
  {
    name: 'opportunity-queue',
    description: 'Every ranked opportunity plus the ACCEPTED queue ready for production.',
    reused: 'decision_engine/ranking.py rank_all()/rank_queue(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('opportunities', [], req),
    health: pythonHealthCheck('opportunities'),
  },
  {
    name: 'unified-priorities',
    description: "EOS Phase 2, Round 2 (2026-07-19): three real priority signals shown side by side, never merged into one fabricated composite score -- FACTORY_STATUS.md's Next Dollar Actions, the ranked ACCEPTED opportunity queue, and MASTER_CHARTER.md's Strategic Production Priority Ladder. Closes the real Opportunity Intelligence gap (today spread across the market/goldenhunter/pioneer/opportunities tabs) without inventing a new ranking algorithm.",
    reused: 'server.js readNextDollarActions() (existing, also used by company-health) + decision_engine/ranking.py rank_queue() via the existing opportunity-queue service + a new MASTER_CHARTER.md markdown-section read using the same technique as readNextDollarActions().',
    handler: unifiedPrioritiesService,
    health: fsHealthCheck(() => readNextDollarActions(), 'FACTORY_STATUS.md read check ok'),
  },
  {
    // Opportunity Intelligence Round 2 (2026-07-22): fast, local-only
    // (reads already-recorded decisions.jsonl, zero live network) -- a
    // plain GET service, same reasoning as product-concept-comparison
    // below.
    name: 'opportunity-pipeline',
    description: "The real, ranked Opportunity Pipeline: every currently-scored opportunity annotated with 10 real fields (market size, customer type, pain level, competition, price, recurring revenue, technical complexity, time to MVP, defensibility, scalability) -- real data where it exists, honestly Unknown where it doesn't. Product Laboratory = decisions already ACCEPTED by the real existing gate; everything else stays in the backlog.",
    reused: 'opportunity_pipeline.py build_opportunity_pipeline() (Opportunity Intelligence Round 2, 2026-07-22) -- reuses decision_engine.ranking.rank_all() verbatim, never recomputes accept/reject.',
    handler: (req) => runPythonServiceCached('opportunity_pipeline', [], req),
    health: pythonHealthCheck('opportunity_pipeline'),
  },
  {
    // Strategic Phase 3, Round 1 (2026-07-22): Product Laboratory MVP --
    // fast, local-only (no live network), so a plain query-param GET
    // service, unlike go-deep-evidence's async job (which does real
    // live-network calls and needs the job/polling pattern).
    name: 'product-concept-comparison',
    description: "Real per-ladder price/score variants for one niche (profit_oracle.ladder_opportunity_score() across all 6 ladder ranks) plus real pre-acceptance ROI per variant -- side by side, never auto-selecting a winner.",
    reused: 'revenue_pipeline/plan.py compare_ladder_variants() (Strategic Phase 3, Round 1, 2026-07-22) -- reuses profit_oracle.ladder_opportunity_score()/estimate_pre_acceptance_roi() verbatim.',
    handler: (req) => {
      const niche = (req.query.niche || '').trim();
      if (!niche) {
        return Promise.resolve({ variants: [], note: 'مرِّر ?niche=<النيتش> لمقارنة مسارات إنتاج فرصة محدَّدة — لا نيتش مُحدَّد بعد' });
      }
      return runPythonServiceCached('product_concept_comparison', [JSON.stringify({ niche })], req);
    },
    health: pythonHealthCheck('product_concept_comparison'),
  },
  {
    name: 'decision-history',
    description: 'Every ACCEPTED/REJECTED/DEFERRED decision ever recorded, newest first, summary fields only.',
    reused: 'decision_engine/store.py read_decisions(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('decision_history', [], req),
    health: pythonHealthCheck('decision_history'),
  },
  {
    name: 'production-queue',
    description: 'Production dossiers for every ACCEPTED opportunity (pricing, assets, pre-production verification), plus the current pause/resume state (Phase 9).',
    reused: 'production_factory/factory.py run_production_factory(), via mission_control_api.py, plus server.js readProductionControl() (Phase 9 pause/resume flag).',
    handler: async (req) => ({ ...(await runPythonServiceCached('production', [], req)), production_control: readProductionControl() }),
    health: pythonHealthCheck('production'),
  },
  {
    name: 'publishing-status',
    description: "Per-platform publishing checklist for every production dossier — a projection of production-queue's own publishing_checklist field, not a new computation.",
    reused: 'production_factory/factory.py (via the production-queue service above), projected to just the checklist fields.',
    handler: publishingStatusService,
    health: pythonHealthCheck('production'),
  },
  {
    name: 'revenue-summary',
    description: 'Revenue pipeline results for every ACCEPTED opportunity plus the rendered CEO revenue report.',
    reused: 'revenue_pipeline/pipeline.py run_revenue_pipeline()/render_ceo_revenue_report(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('revenue', [], req),
    health: pythonHealthCheck('revenue'),
  },
  {
    name: 'automation-status',
    description: 'n8n workflow status from the last real exported definitions (n8n_workflows/*.fixed.json) — honestly labelled as a static export, not live state (n8n REST API still needs a manual login, BLOCKERS.md #1).',
    reused: 'mission_control_api.py\'s existing n8n_workflows/*.fixed.json reader.',
    handler: (req) => runPythonServiceCached('automation', [], req),
    health: pythonHealthCheck('automation'),
  },
  {
    name: 'knowledge-base',
    description: 'OpenClaw_Brain folder map, or full-text search results when called with ?q=.',
    reused: 'knowledge_brain.js searchBrain()/getBrainMap() — same module already backing the pre-existing GET /brain.',
    handler: knowledgeBaseService,
    health: fsHealthCheck(() => knowledgeBrain.getBrainMap(), 'OpenClaw_Brain directory read check ok'),
  },
  {
    name: 'alerts',
    description: 'NEEDS_ATTENTION.md and NEEDS_REVIEW.md — active flags and their content, if any.',
    reused: 'lib/dashboard_data.js readAttentionFlag()/readReviewFlag() — same fields already confirmed served by GET /api/dashboard.',
    handler: alertsService,
    health: fsHealthCheck(() => dashboardData.readAttentionFlag(), 'dashboardData module reachable'),
  },
  {
    name: 'system-configuration',
    description: 'Real, non-secret configuration: unit economics (config/economics.json), tier weights/floor and per-tier automation/long-term-value constants (profit_oracle.py), and the capability maturity registry.',
    reused: 'config/economics.json, config/capability_registry.json, profit_oracle.py\'s TIER_WEIGHTS/MIN_OPPORTUNITY_SCORE/AUTOMATION_POTENTIAL_BY_TIER/LONG_TERM_VALUE_BY_TIER, via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('system_configuration', [], req),
    health: pythonHealthCheck('system_configuration'),
  },
  {
    name: 'recovery-status',
    description: 'Unified Recovery System (2026-07-18) dashboard: current in-flight task, recovery state, pending retries, last checkpoint, and the last real recovery action.',
    reused: 'factory_state.py load_state() + data/recovery_actions.jsonl, via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('recovery', [], req),
    health: pythonHealthCheck('recovery'),
  },
  {
    name: 'production-families',
    description: 'Universal Production Engine (2026-07-18): which of the 11 UPE product families have a real registered adapter today, under the founder-approved canonical family names, plus each manifest-driven family\'s real Product Manifest (Roadmap Step 3) — category, generators, pricing, supported marketplaces.',
    reused: 'product_families.registry + product_families.manifest, via mission_control_api.py — same data-driven discipline as production_factory/dossier.py\'s _product_type_capability().',
    handler: (req) => runPythonServiceCached('production_families', [], req),
    health: pythonHealthCheck('production_families'),
  },
  {
    name: 'commercial-execution',
    description: 'Universal Production Engine (2026-07-19): the Commercial Execution Layer — which marketplaces are autonomous vs need real founder action right now (approval gates, computed off every arm\'s own live status()), plus the most recent real publish attempts from the ledger.',
    reused: 'commercial_execution.approval_gates + channels.ledger, via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('commercial_execution', [], req),
    health: pythonHealthCheck('commercial_execution'),
  },
  {
    name: 'ai-capability-registry',
    description: 'Real AI provider capability registry (Claude, GPT, Gemini, Grok, DeepSeek, Qwen, Mistral, local models, plus Groq itself) — Groq metrics computed live from data/ai_cost_log.jsonl (REAL where measured), every other provider honestly DISCOVERY-level until a credential exists and is actually called. Plus the append-only log of real department requests for a different/better model.',
    reused: 'ai_capability/registry.py list_providers()/read_capability_requests() (Autonomous Digital Company v1, Track B2, 2026-07-19), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('ai_capability', [], req),
    health: pythonHealthCheck('ai_capability'),
  },
  {
    name: 'evidence-network-status',
    description: "Galaxy Forge Evidence Network (ADR-128, 2026-07-25): the real, honest connector inventory -- which evidence sources are actually callable today (competitor_discovery.py, market_intelligence_engine.py) vs. declared-but-not-built (job postings, pricing pages, marketplaces, patents, enterprise demand, iteration tracking). Never fabricates a connector that doesn't exist.",
    reused: 'evidence_network.py network_status_report(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('evidence_network_status', [], req),
    health: pythonHealthCheck('evidence_network_status'),
  },
  {
    name: 'evidence-coverage-status',
    description: "Galaxy Forge Evidence Network (ADR-128, 2026-07-25): real, aggregate Evidence Coverage / Unknown Count / Research Queue / Top Missing Signals across every real decision carrying a persisted evidence_completeness snapshot (ADR-127 onward), plus real freshness stats over the two real persistent evidence caches (competitor_discovery.py, market_intelligence_engine.py).",
    reused: 'evidence_network.py aggregate_evidence_report()/evidence_freshness_report(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('evidence_coverage_status', [], req),
    health: pythonHealthCheck('evidence_coverage_status'),
  },
  {
    name: 'customer-pipeline-status',
    description: "Galaxy Forge Customer Platform, Phase 2 Round 1 (ADR-130, 2026-07-25): real Mission Control supervision over every real customer request's pipeline -- per-request Status/Progress/Logs/Failures/Recovery/Estimated-completion, stage distribution, and which requests need a real founder action right now (Paddle onboarding gate, missing custom product, or a real failure).",
    reused: 'customer_pipeline.py list_pipeline_overview(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('customer_pipeline_status', [], req),
    health: pythonHealthCheck('customer_pipeline_status'),
  },
  {
    name: 'customer-accounts',
    description: 'Real signed-up customer accounts (Customer Platform Round 6, 2026-07-29) -- count + most recently created, name/email/company/created_at only, never password hashes.',
    reused: 'lib/dashboard_data.js readCustomerAccountsSummary() over data/customer_accounts.json.',
    handler: async () => dashboardData.readCustomerAccountsSummary(),
    health: fsHealthCheck(() => dashboardData.readCustomerAccountsSummary(), 'dashboardData module reachable, customer_accounts.json read check ok'),
  },
  {
    name: 'customer-fulfillment-queue',
    description: 'Real Production/QA/Packaging/Delivery queue (Round 6, 2026-07-29) -- every request that reached PAID or later, plus the real founder-action queue (PENDING_FOUNDER_FULFILLMENT) surfaced separately. Never fabricates a production/QA status.',
    reused: 'customer_pipeline.py list_fulfillment_queue(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('customer_fulfillment_queue', [], req),
    health: pythonHealthCheck('customer_fulfillment_queue'),
  },
  {
    name: 'customer-invoices',
    description: 'Real invoices generated from actual completed Paddle payments (Round 6, 2026-07-29) -- honestly empty until a real payment completes, never a fabricated revenue number.',
    reused: 'customer_pipeline.py list_invoices(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('customer_invoices', [], req),
    health: pythonHealthCheck('customer_invoices'),
  },
  {
    name: 'customer-reviews',
    description: 'Real customer reviews (Round 6, 2026-07-29) -- count, real average rating, most recent reviews. Honestly empty until a real review exists, never a placeholder testimonial.',
    reused: 'lib/dashboard_data.js readCustomerReviewsSummary() over data/customer_reviews.jsonl (Round 5).',
    handler: async () => dashboardData.readCustomerReviewsSummary(),
    health: fsHealthCheck(() => dashboardData.readCustomerReviewsSummary(), 'dashboardData module reachable, customer_reviews.jsonl read check ok'),
  },
  {
    name: 'executive-score',
    description: 'Executive Score (Round 6, 2026-07-29) -- a transparent, real-component composite (Trust, Production Quality, Technical Debt, Security Health, Delivery Quality, Automation, Growth, Architecture Health, Operational Stability, Customer Happiness). Every sub-score is a real number from an existing real function or an honest "Unknown" -- never blended into any accept/reject/production gate, informational only.',
    reused: 'executive_score.py compute_executive_score() (Python sub-scores) merged with server.js computeHealthStatus() and lib/dashboard_data.js readCustomerReviewsSummary() (JS-native sub-scores).',
    handler: executiveScoreService,
    health: pythonHealthCheck('executive_score'),
  },
  {
    name: 'support-tickets',
    description: 'Real support ticket summary (Executive Intelligence Core, Round 3, 2026-07-29) -- count, open count, most recent tickets. data/support_tickets.jsonl was write-only until now; honestly empty today, zero real customer traffic yet.',
    reused: 'lib/dashboard_data.js readSupportTicketSummary() over data/support_tickets.jsonl.',
    handler: async () => dashboardData.readSupportTicketSummary(),
    health: fsHealthCheck(() => dashboardData.readSupportTicketSummary(), 'dashboardData module reachable, support_tickets.jsonl read check ok'),
  },
  {
    name: 'golden-hunter-status',
    description: "Golden Hunter Evolution -- real recent activity + top currently-scored opportunities, each with a real, informational pre-acceptance ROI estimate. Never changes the real accept/reject gate.",
    reused: 'mission_control_api.py _golden_hunter_status() (EOS Phase 2, 2026-07-19) -- reuses golden_opportunities.json, data/golden_hunter_events.jsonl, and revenue_pipeline.plan.estimate_pre_acceptance_roi() verbatim.',
    handler: (req) => runPythonServiceCached('golden_hunter_status', [], req),
    health: pythonHealthCheck('golden_hunter_status'),
  },
  {
    name: 'pioneer-status',
    description: "Pioneer -- real discovery activity. Honestly discloses that Pioneer's candidates share the same event log as Golden Hunter (no separate Pioneer-only counter exists).",
    reused: 'mission_control_api.py _pioneer_status() (EOS Phase 2, 2026-07-19).',
    handler: (req) => runPythonServiceCached('pioneer_status', [], req),
    health: pythonHealthCheck('pioneer_status'),
  },
  {
    name: 'knowledge-graph',
    description: "A real, queryable company memory -- nodes (Niche, Decision, ProductionRun, PublishChannel, AIProvider) and edges built fresh from 5 real data sources on every call. The Decision->ProductionRun edge is honestly labelled 'exact' (real production_id match) or 'approximate' (best-effort niche-text fallback) -- never presented as certain when it isn't.",
    reused: 'knowledge_graph/build.py build_graph() (EOS Phase 2, 2026-07-19) -- reuses data/decisions.jsonl, data/market_intelligence_analyses.jsonl, data/sales_ledger.jsonl, data/ai_cost_log.jsonl verbatim, no new data collection.',
    handler: (req) => runPythonServiceCached('knowledge_graph', [], req),
    health: pythonHealthCheck('knowledge_graph'),
  },
  {
    name: 'department-health',
    description: "Per-named-department health rollup -- pure assembly of already-computed real signals (orchestrator engine success rates, channel approval status, real activity counts, AI provider status, infrastructure status, recovery/retry state). Researchers and Customer Intelligence are honestly 'no real data' -- never a fabricated score.",
    reused: 'department_health.py build_department_health() (EOS Phase 2, 2026-07-19) -- reuses executive_intelligence.engine_health, commercial_execution.approval_gates, ai_capability.registry, infrastructure_bridge.py, channels.ledger, and factory_state.py verbatim.',
    handler: (req) => runPythonServiceCached('department_health', [], req),
    health: pythonHealthCheck('department_health'),
  },
  {
    name: 'research-department',
    description: "Real analysis assembled under 7 named research categories (Market, Competitor, Pricing, Publishing, Automation, Technology, Customer) -- pure assembly of already-real signals, no new analysis logic. Technology and Customer research are honestly 'Unknown' -- no module evaluates tech choices, and this factory has zero real customer data.",
    reused: 'research_department.py build_research_report() (EOS Phase 2, 2026-07-19) -- reuses market_intelligence_analyses.jsonl, competitor_discovery.py, profit_oracle.py constants, commercial_execution.approval_gates, and evolution_engine.py verbatim.',
    handler: (req) => runPythonServiceCached('research_department', [], req),
    health: pythonHealthCheck('research_department'),
  },
  {
    name: 'ai-doctor',
    description: "The real, non-fabricated engineering-health system replacing quality_doctor.py's confirmed-fake pattern -- combines evolution_engine's bottleneck/tech-debt/ROI/capability-gap signals with real infrastructure status and a real (never-fabricated) dependency-pinning + npm-audit check.",
    reused: 'ai_doctor.py build_ai_doctor_report() (EOS Phase 2, 2026-07-19) -- reuses evolution_engine.py and infrastructure_bridge.py verbatim, no reimplementation.',
    handler: (req) => runPythonServiceCached('ai_doctor', [], req),
    health: pythonHealthCheck('ai_doctor'),
  },
  {
    name: 'integration-registry',
    description: "Real, adapter-based extension points for every founder-named future vendor (n8n, GitHub, Notion, Slack, Discord, Cloudflare, Docker, Supabase, PostgreSQL, vector databases, Shopify, KDP, Perplexity, MiniMax, etc.), plus AI providers/commerce channels referenced from their own real registries -- never a second, duplicate source of truth for those. No live 'test connection' calls -- real env-var presence only.",
    reused: 'integration_registry.py list_integrations() (EOS Phase 2, 2026-07-19) -- references ai_capability/registry.py and channels/registry.py rather than duplicating them.',
    handler: (req) => runPythonServiceCached('integration_registry', [], req),
    health: pythonHealthCheck('integration_registry'),
  },
  {
    name: 'founder-console',
    description: "The only view framed as 'you need to decide something': blocked marketplace channels + why, DEFERRED decisions awaiting a call, the real attention/review flags, and BLOCKERS.md's founder-only action list. Everything else in Mission Control stays informational.",
    reused: 'founder_console.py build_founder_queue_partial() (EOS Phase 1, 2026-07-19) + lib/dashboard_data.js readAttentionFlag()/readReviewFlag() + a BLOCKERS.md read (same technique as readNextDollarActions()).',
    handler: founderConsoleService,
    health: fsHealthCheck(() => dashboardData.readAttentionFlag(), 'dashboardData module reachable'),
  },
  {
    name: 'evolution-report',
    description: "Company Evolution Engine -- real bottleneck detection, technical debt, high-ROI opportunity ranking, tool-integration proposals, and a new capability-gap scan (config/capability_registry.json entries not yet REAL). Detection only, never automatic execution.",
    reused: 'evolution_engine.py build_evolution_report() (EOS Phase 1, 2026-07-19) -- combines executive_intelligence.bottlenecks, strategic_intelligence.technical_debt, revenue_pipeline.pipeline, tool_intelligence.proposals, and the new capability_registry_scanner.py.',
    handler: (req) => runPythonServiceCached('evolution_report', [], req),
    health: pythonHealthCheck('evolution_report'),
  },
  {
    // Company Evolution Protocol V1 (ADR-173, 2026-08-05): a real
    // relabel/extension of evolution_report above onto the directive's
    // 10 named sections, ROI-ranked. No new judgment engine.
    name: 'galaxy-evolution-report',
    description: "The real monthly Galaxy Evolution Report -- Current Strengths/Weaknesses, Critical Risks, Hidden Opportunities, Recommended Improvements, High Priority Actions (ranked by real capital_allocation_engine.py ROI data), Expected Long-Term Impact, Potential Monthly Revenue Impact, Estimated Implementation Effort, Global Benchmark. The last 3 are honestly disclosed gaps, never fabricated: zero real revenue exists to model an impact against, zero real historical per-task duration data exists to estimate effort from, and no real external company-research pipeline exists to study world-class companies with. Already wired into factory_loop.js's tick with a genuinely new once-per-calendar-month gate (this factory's first monthly cadence, alongside its existing daily/weekly ones).",
    reused: 'evolution_engine.py::build_galaxy_evolution_report() (ADR-173) + capital_allocation_engine.py, via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('galaxy_evolution_report', [], req),
    health: pythonHealthCheck('galaxy_evolution_report'),
  },
  {
    // Continuous Trust & Resilience Monitoring (2026-07-29): the real,
    // unified Monitor + Classify + Report view over every signal built
    // across the Global Trust & Resilience Layer + Global Commercial
    // Hardening. Read-only -- Respond/Protect/Founder-approval stay
    // exactly as gated as they already were (safe-mode/publish-
    // protection actions above); this panel only makes the evidence for
    // using them more visible, faster.
    name: 'resilience-status',
    description: "The real, unified resilience view: every monitored area (unstable subsystems, publish/marketplace risk, customer/payment risk, security drift, data integrity, health trend, customer trust) classified informational/warning/critical/emergency, plus a transparent resilience_score (an average of only the real, data-available areas -- never gates anything, never fabricates a severity when no real data exists yet).",
    reused: 'resilience_monitor.py assess_resilience() (Python signals) merged with server.js computeHealthStatus() storage_integrity + lib/dashboard_data.js reviews/tickets (JS-native signals) -- same merge pattern as executive-score.',
    handler: resilienceStatusService,
    health: pythonHealthCheck('resilience_status'),
  },
  {
    name: 'resilience-incidents',
    description: "Learn: the real incident history (opened/resolved), each with a real root_cause/prevention_rule/detection_rule citing the actual existing mechanism, a live-checked improvement_proposal_id when one currently exists, and rollback_guidance pointing at the real founder action that reverses it. Honestly empty until a real critical/emergency finding has ever occurred.",
    reused: 'resilience_monitor.py list_incidents()/record_incident() (Continuous Trust & Resilience Monitoring, 2026-07-29), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('resilience_incidents', [], req),
    health: pythonHealthCheck('resilience_incidents'),
  },
  {
    // Strategic Intelligence Core (2026-07-29): the one real aggregator
    // this factory never had. Every one of its 9 named fields cites an
    // already-real function (resilience_monitor, ceo_decision_center,
    // evolution_engine, scheduler, founder_console, this module's own
    // evaluate_strategic_horizons()/customer_pipeline's cost-trend
    // signal) -- read-only, recommend-only, exactly like every panel
    // above it. Nothing here executes autonomously on anything
    // irreversible; Constitution-first + no-autonomous-high-risk-
    // decisions are already real everywhere a real decision is made.
    name: 'executive-brief',
    description: "The real Executive Brief: company_health, top_risks, top_opportunities, top_bottlenecks, recommended_priorities, products_to_accelerate/pause, research_needed (the real, current NOT ENOUGH EVIDENCE gaps -- multi-year horizons and customer-problem cost trend, never an invented topic), founder_decisions_required.",
    reused: 'strategic_intelligence_core.py build_executive_brief() (Strategic Intelligence Core, 2026-07-29), via mission_control_api.py.',
    // Real, disclosed outlier timeout (measured ~45-55s cold, well past
    // the shared 30s default): this aggregator's own two dominant real
    // sub-computations (ceo_dashboard()'s investment pipeline + full
    // scheduling scan, evolution_engine's bottleneck/tech-debt/ROI scan)
    // are each independently already ~20s. The 20s cache TTL still
    // absorbs repeat cost the same as every other panel; this only
    // affects the first, cold call.
    handler: (req) => runPythonServiceCached('executive_brief', [], req, 90000),
    health: pythonHealthCheck('executive_brief'),
  },
  {
    // Galaxy Council Learning (2026-07-29): the real, cheap, no-input
    // read (JSONL reads + decision_engine.store joins only -- never a
    // per-opportunity value_engine scan) for the auto-refreshing
    // Mission Control panel. Same underlying python section as the
    // ACTION_REGISTRY's get-council-learning-summary below (dual
    // exposure, same precedent as evolution_report/department_health/
    // ai_doctor being both a live panel and a factory_loop.js caller).
    name: 'galaxy-council-learning',
    description: "The real 3-way join: Council Recommendation vs. the real Founder Decision that followed vs. the real eventual Outcome. Honestly NOT ENOUGH EVIDENCE until real triples accumulate -- never backfilled for a niche/decision that predates the Council's existence.",
    reused: 'galaxy_council.py::council_learning_summary()',
    handler: (req) => runPythonServiceCached('council_learning_summary', [], req),
    health: pythonHealthCheck('council_learning_summary'),
  },
  {
    // Capital Allocation Engine (2026-07-29): reuses value_engine.
    // build_value_engine_report() + scheduler.decide_next_actions() --
    // the same real, disclosed outlier class as executive-brief above
    // (measured live: ~22s of real compute alone; this machine's
    // `python3` alias adds a further real ~30s startup tax on top of
    // that per subprocess, confirmed live during the Galaxy Council
    // round -- so the shared 30s default is not safely enough margin).
    // Executive Brain (ADR-144, 2026-07-30): the founder's "one executive
    // decision only, no conflicting actions" directive. Reuses
    // strategic_intelligence_core.build_executive_brief() +
    // global_opportunity_exchange + capital_allocation_engine +
    // evolution_queue verbatim -- chains 3 full-portfolio scans, measured
    // live ~55-60s, hence the long timeout below. Deliberately a LIVE
    // preview only (record_ledger=False) -- never grows the permanent
    // ledger on a page view; only the daily tick does that (see
    // generate-daily-executive-directive action, factory_loop.js). Never
    // executes/approves/rejects/publishes/reallocates anything --
    // requires_founder_approval is always true in the real response.
    name: 'executive-brain',
    description: "The one real, single Executive Directive for this cycle -- arbitrates real candidate actions from every existing intelligence system into exactly ONE recommendation via the founder's own Priority 1-5 framework (System Stability > Opportunity Discovery > Premium Product Creation > Revenue Growth > Self Evolution). A genuine same-tier tie is honestly reported as SPLIT, never arbitrarily resolved. Read-only/recommend-only -- execution stays exactly as human-gated as every other irreversible action in this factory (evolution_queue.py's Execute step, capital reallocation, publish protection).",
    reused: 'executive_brain.py::build_executive_directive() (ADR-144), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('executive_brain_directive', [], req, 120000),
    health: pythonHealthCheck('executive_brain_directive'),
  },
  {
    name: 'executive-directives-history',
    description: "The real Learning History for the Executive Brain -- every real directive it has ever generated via the daily tick (never a live-view side effect), most recent first. Read-only.",
    reused: 'executive_brain.py::list_executive_directives() (ADR-144), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('executive_directives_history', [], req),
    health: pythonHealthCheck('executive_directives_history'),
  },
  {
    // GF-OS (ADR-147, 2026-07-30): a coordination/citation layer, not a
    // mandatory gateway -- confirmed via AskUserQuestion before building.
    // Every department below is still called directly by every other
    // real caller exactly as before; safe_mode.py's per-subsystem
    // independence (ADR-135) is unchanged. "Mission Queue" is a pure
    // citation of scheduler.py's real buckets + orchestrator.py's real
    // stages -- no new queue infrastructure (a question already asked
    // and declined 4x: ADR-107/110/115/142).
    name: 'gfos-status',
    description: "The single real Enterprise Operating System status view -- all 12 real departments (Identity/Capabilities/Dependencies/Workload/Health/Confidence, each a citation of an already-real signal), the real mission lifecycle (scheduler.py's 5 buckets + orchestrator.py's 5 execution stages, honestly None where no real per-mission signal exists), and the 10 most recent real Enterprise Timeline entries. A citation layer only -- nothing here executes, approves, or force-routes anything.",
    reused: 'gfos.py::gfos_status() (ADR-147), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('gfos_status', [], req, 40000),
    health: pythonHealthCheck('gfos_status'),
  },
  {
    // Galaxy Operating System (ADR-172, 2026-08-05): the real 9-engine
    // map. All 9 named engines (Galaxy Brain/GOOS/Product Forge/Capital
    // Engine/Customer Happiness Engine/Security Engine/Knowledge Engine/
    // Evolution Engine/Executive Council) already exist as real modules
    // -- this is a citation layer, not a 10th parallel system.
    name: 'engine-registry',
    description: "The real 9-engine map the founder's 'Galaxy Operating System' directive asked for -- each entry citing its already-real module(s) and identity. 'Evolution Engine' is already this factory's literal, existing module name; GOOS/Capital Engine/Executive Council/Knowledge Engine were all built in prior rounds this session. Cheap, no live scan.",
    reused: 'gfos.py::engine_registry() (ADR-172), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('engine_registry', [], req),
    health: pythonHealthCheck('engine_registry'),
  },
  {
    // Galaxy Operating System (ADR-172, 2026-08-05): the real weekly
    // self-governance report -- already wired into factory_loop.js's
    // existing Sunday-gated weekly executive report (no new scheduling).
    name: 'if-i-were-the-ceo-report',
    description: "The real weekly 'IF I WERE THE CEO' report -- 7 named questions (what should stop/start/improve/be automated, where money is wasted, hidden opportunities, what prevents world-class status), each answered from an already-real citation (ceo_decision_center.py's real answer_ceo_questions(), evolution_engine.py's real bottleneck detection, the real Company Readiness Audit/Enterprise Truth/Factory Audits for the final question). Never a new judgment engine. Expensive (~56s, chains ceo_decision_center's own real sub-calls).",
    reused: 'gfos.py::if_i_were_the_ceo_report() (ADR-172) + ceo_decision_center.py + evolution_engine.py, via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('if_i_were_the_ceo_report', [], req, 90000),
    health: pythonHealthCheck('if_i_were_the_ceo_report'),
  },
  {
    name: 'gfos-enterprise-timeline',
    description: "The full real Enterprise Timeline (up to 50 entries) -- a real merge of decisions.jsonl + department_events.jsonl + evolution_queue_state.json + executive_directives.jsonl + council_recommendations.jsonl, most recent first. \"Nothing is lost\": every entry already existed in its own real ledger before this merge existed -- zero new logging call sites.",
    reused: 'gfos.py::enterprise_timeline() (ADR-147), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('gfos_enterprise_timeline', [], req),
    health: pythonHealthCheck('gfos_enterprise_timeline'),
  },
  {
    // Affiliate Commerce (ADR-149, 2026-07-30): the founder's explicit
    // override of the ADR-148 Golden Rule deferral -- the smallest real,
    // honest slice (one network, one category, real click tracking, no
    // conversion/commission -- that needs Amazon's real postback). This
    // is the internal, Mission-Control-authenticated status view; the
    // customer-facing product data/click routes are public
    // (/api/affiliate/products, /api/affiliate/click/:product_id above
    // /api/customer/catalog), unauthenticated by design.
    name: 'affiliate-commerce-status',
    description: "The real Affiliate Commerce status -- real click counts per product (data/affiliate_clicks.jsonl, never fabricated), whether a real Amazon Associates tag is configured, the real static product dataset, and an honest not-implemented-yet list (real account signup, real conversion/commission tracking, SEO engine/multi-partner/auto-discovery -- explicitly excluded by the founder's own directive as premature).",
    reused: 'affiliate_commerce/networks.py + click_tracking.py + products.py (ADR-149), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('affiliate_commerce_status', [], req),
    health: pythonHealthCheck('affiliate_commerce_status'),
  },
  {
    // Simulation-First Company Build (ADR-153, 2026-07-30): generalizes
    // this factory's own already-real dry_run discipline
    // (channels/base_arm.py/distributor.py/reality.py's real dry_run
    // filter) to "don't really transact." Every field is explicitly
    // labeled SIMULATED -- never merged with affiliate-commerce-status's
    // real click counts above, never written to any real financial
    // ledger. NOT cached (runPythonServiceCached would serve a stale
    // simulated funnel) -- cheap, and each call triggers one real
    // simulation cycle over the real click ledger.
    name: 'affiliate-simulation-report',
    description: "The real, honestly SIMULATED Affiliate Commerce funnel (clicks -> conversion -> commission), drawn from the real click ledger with a disclosed, labeled assumed conversion rate and commission rate -- never a confirmed real number, never counted in any real revenue figure. Exercises the pipeline end-to-end before ADR-150's real Phase 2 gate (real Associates tag + real confirmed conversion) clears.",
    reused: 'affiliate_commerce/simulation.py + simulation_mode.py (ADR-153), via mission_control_api.py.',
    handler: () => runPythonService('affiliate_simulation_report'),
    health: pythonHealthCheck('affiliate_simulation_report'),
  },
  {
    // Simulation-First Company Build (ADR-153, 2026-07-30): a per-
    // division scorecard, distinct from executive_score.py's own
    // company-wide score. Every dimension is a real, mechanical,
    // disclosed-heuristic check (file existence, real test-function
    // counts, real text-marker presence) -- SaaS/AI Services/Licensing
    // report honestly not_architected (no real code exists for any of
    // them), never invented to look more built-out.
    name: 'launch-readiness-score',
    description: "The real, per-division 8-dimension Launch Readiness Score (Architecture/Automation/Testing/Compliance/Monitoring/Documentation/Integration/Operational readiness) -- Affiliate Commerce and Digital Products score real signals today; SaaS/AI Services/Licensing honestly report not_architected (zero real code exists for any of them in this factory).",
    reused: 'launch_readiness.py (ADR-153), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('launch_readiness_score', [], req),
    health: pythonHealthCheck('launch_readiness_score'),
  },
  {
    // Executive Intelligence Layer (ADR-154, 2026-07-31): chains 3 real
    // full-portfolio scans (capital_allocation_engine, strategic_
    // intelligence_core, global_opportunity_exchange) exactly once each
    // -- same real cost class as executive-brief/executive-brain, cached
    // like them.
    name: 'executive-intelligence-questions',
    description: "The real answers to 8 named strategic questions (what deserves attention today / which division is slowing the company / where is revenue highest / which automations are underutilized / what to build next / what to pause / highest ROI / which bottleneck blocks scaling) -- almost entirely citation of already-real functions (executive_brain.py, capital_allocation_engine.py, strategic_intelligence_core.py). Honestly reports WAITING FOR REAL SOURCE where no real per-division or utilization signal exists, never a fabricated answer.",
    reused: 'executive_questions.py (ADR-154), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('executive_intelligence_questions', [], req, 90000),
    health: pythonHealthCheck('executive_intelligence_questions'),
  },
  {
    // Enterprise Operations Center (ADR-155, 2026-07-31): chains
    // build_executive_brief() + founder_console + capital_allocation_
    // engine + executive_questions.py + executive_intelligence/
    // inactivity.py, each exactly once. Same real cost class as
    // executive-brain/executive-intelligence-questions above.
    name: 'company-pulse',
    description: "The real \"Company Pulse\" -- 7 named questions (is the company healthy / what's working / what's blocked / where's money expected / which division needs attention / which automations are idle / which opportunities are waiting), each citing an already-real source. \"Which automations are idle\" reuses a real, previously-unwired module (executive_intelligence/inactivity.py, ADR-052) -- zero-execution orchestrator engines + zero-publish-attempt channel arms.",
    reused: 'enterprise_operations.py::company_pulse() (ADR-155), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('company_pulse', [], req, 120000),
    health: pythonHealthCheck('company_pulse'),
  },
  {
    name: 'dependency-matrix',
    description: "A real, mechanical, AST-based Python-import dependency analysis (dependency_graph.py) over each of the 12 real departments' one primary module -- a disclosed code-level proxy for operational dependency, never a fabricated business-relationship graph.",
    reused: 'enterprise_operations.py::dependency_matrix() (ADR-155) + dependency_graph.py + gfos.py\'s real department->primary-module mapping, via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('dependency_matrix', [], req),
    health: pythonHealthCheck('dependency_matrix'),
  },
  {
    name: 'executive-analytics',
    description: "Real trends over time -- health_trend.py's real GET /health snapshot trend, channels/ledger.py's real revenue_trend(), evolution_queue.py's real per-proposal outcome measurements (ADR-143) -- consolidated into one view, zero new computation, never an isolated snapshot number presented as a trend.",
    reused: 'enterprise_operations.py::executive_analytics() (ADR-155), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('executive_analytics', [], req),
    health: pythonHealthCheck('executive_analytics'),
  },
  {
    // Enterprise Executive Brain (ADR-156, 2026-07-31): computes
    // build_executive_brief()/global_opportunity_exchange/capital_
    // allocation_engine exactly once (the exact redundant-computation
    // bug class ADR-155's company_pulse() hit and fixed) -- same real
    // cost class as executive-brain/company-pulse above.
    name: 'unified-decision-engine',
    description: "The real prioritized executive action list, plus real conflict/duplicated-work/idle-division/bottleneck/missing-dependency detection -- each citing an already-real function (executive_brain.py, executive_decision_memory.py, executive_intelligence/inactivity.py) or a new, small, disclosed mechanical heuristic (duplicated work: department pairs sharing 3+ real imported modules; missing dependencies: divisions with zero real architecture).",
    reused: 'enterprise_executive_brain.py::unified_decision_engine() (ADR-156), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('unified_decision_engine', [], req, 120000),
    health: pythonHealthCheck('unified_decision_engine'),
  },
  {
    name: 'executive-kpi-system',
    description: "The real per-division 8-KPI scorecard (Health/Readiness/Progress/Revenue Potential/Automation Level/Intelligence Score/Production Capacity/Risk Level), reusing launch_readiness.py's real 5-division registry. Most fields honestly disclose a real company-wide (not yet per-division) signal rather than fabricating a division-specific number; Intelligence Score and Production Capacity are honestly NOT_ARCHITECTED -- no real source exists for either.",
    reused: 'enterprise_executive_brain.py::executive_kpi_system() (ADR-156), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('executive_kpi_system', [], req),
    health: pythonHealthCheck('executive_kpi_system'),
  },
  {
    name: 'enterprise-dependency-graph',
    description: "Extends the real department dependency matrix (ADR-155) with real reverse-dependents, real cascade-impact ('what breaks if this department fails'), and real cycle detection -- all from dependency_graph.py's already-real functions, never surfaced in Mission Control until now.",
    reused: 'enterprise_executive_brain.py::enterprise_dependency_graph() (ADR-156) + dependency_graph.py, via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('enterprise_dependency_graph', [], req),
    health: pythonHealthCheck('enterprise_dependency_graph'),
  },
  {
    name: 'enterprise-scheduler',
    description: "Merges capital_allocation_engine's real ROI ranking with gfos.py's real scheduler buckets into one ranked view -- no new ranking algorithm, no new queue. Execution time is honestly 'Unknown' -- no real historical per-stage duration tracking exists anywhere in this factory.",
    reused: 'enterprise_executive_brain.py::enterprise_scheduler() (ADR-156), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('enterprise_scheduler', [], req, 60000),
    health: pythonHealthCheck('enterprise_scheduler'),
  },
  {
    name: 'executive-scenario-simulator',
    description: "3 real, disclosed-assumption HYPOTHETICAL projections (revenue growth off channels/ledger.py's real baseline, AI cost increase off data/ai_cost_log.jsonl's real baseline, infrastructure-failure cascade off the real dependency graph) + 4 scenarios honestly reported NOT_ARCHITECTED (traffic spikes, publishing delays, affiliate expansion, digital product expansion -- no real, distinct baseline exists to honestly perturb). Never a prediction, never written to any ledger, never touches Simulation Mode's AFFILIATE_MODE switch or any production code path. Accepts optional ?cascade_department=<name> query param.",
    reused: 'enterprise_executive_brain.py::executive_scenario_simulator() (ADR-156), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('executive_scenario_simulator', [JSON.stringify({ cascade_department: req.query && req.query.cascade_department })], req),
    health: pythonHealthCheck('executive_scenario_simulator'),
  },
  {
    // Autonomous Company Runtime (ADR-157, 2026-07-31): flagged via
    // AskUserQuestion before any code -- the directive's Company
    // Runtime/Event Bus/Workflow Engine/Queue Manager asks together
    // describe an always-on daemon + new queue/event infrastructure,
    // declined 5x already (ADR-107/110/115/142/147). Founder's answer:
    // document only, build the genuinely safe citation-only parts
    // below. No daemon, no event bus, no queue exists here or anywhere
    // in this factory.
    name: 'executive-replay',
    description: "Real chronological replay over gfos.py's real Enterprise Timeline (6 merged real ledgers), optionally date-filtered, plus executive_decision_memory.py's real explain-decision detail for one decision_id. No new storage, no new event log. Accepts optional ?from_date=&to_date=&decision_id= query params.",
    reused: 'company_runtime.py::executive_replay() (ADR-157) + gfos.py (ADR-147) + executive_decision_memory.py (ADR-145), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('executive_replay', [JSON.stringify({ from_date: req.query && req.query.from_date, to_date: req.query && req.query.to_date, decision_id: req.query && req.query.decision_id })], req),
    health: pythonHealthCheck('executive_replay'),
  },
  {
    name: 'autonomous-daily-cycle-status',
    description: "A real, disclosed, static citation of factory_loop.js's real tick-driven functions for each of the directive's 9 named daily-cycle stages (morning review/opportunity scan/production/QA/publishing/affiliate updates/analytics/knowledge update/executive report) -- honestly NOT_ARCHITECTED where no real tick-wired function exists (morning review, affiliate updates). factory_loop.js has no cron/systemd -- 'tick-wired' only means it runs when someone runs `node factory_loop.js` and leaves it running.",
    reused: 'company_runtime.py::autonomous_daily_cycle_status() (ADR-157), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('autonomous_daily_cycle_status', [], req),
    health: pythonHealthCheck('autonomous_daily_cycle_status'),
  },
  {
    name: 'company-state',
    description: "A real, priority-ordered, disclosed read-only status label (BOOT/RECOVERY/MAINTENANCE/PRODUCTION/OPTIMIZING/LEARNING/READY/SCALING) -- every condition cites a real signal (resilience_monitor.py, safe_mode.py, factory_state.py, evolution_queue.py). SCALING is defined (per the directive) but never selected -- no real scale-out signal exists anywhere in this factory. BOOT is checked here, not in Python (mission_control_api.py runs as a fresh, stateless subprocess per call -- it has no real process uptime to measure) -- reuses this real Node server process's own real process.uptime(), the same real signal GET /api/v1/health already exposes. Informational only: nothing in this factory reads this label to change its own behavior.",
    reused: 'company_runtime.py::company_state() (ADR-157) + this process\'s own real process.uptime(), via mission_control_api.py.',
    handler: async (req) => {
      const BOOT_WINDOW_SECONDS = 60;
      if (process.uptime() < BOOT_WINDOW_SECONDS) {
        return {
          success: true,
          state: 'BOOT',
          reason: `This real Node server process started ${Math.round(process.uptime())}s ago (< ${BOOT_WINDOW_SECONDS}s window) -- process.uptime(), the same real signal GET /api/v1/health already exposes.`,
          generated_at: new Date().toISOString(),
        };
      }
      return runPythonServiceCached('company_state', [], req);
    },
    health: pythonHealthCheck('company_state'),
  },
  {
    // Truth First Constitution (ADR-160, 2026-07-31): the company's
    // highest law (OPENCLAW_OS_CONSTITUTION.md's new "TRUTH FIRST"
    // section). A governance-ratification round, not a feature build --
    // this factory already practiced this discipline all session under
    // inconsistent vocabulary (350 real honest-disclosure instances
    // across 9 variants, grandfathered not retrofitted); the canonical
    // 9-term vocabulary governs new code going forward.
    name: 'truth-first-compliance',
    description: "The real vocabulary census (a mechanical *.py file scan for the 9 pre-ADR-160 honest-disclosure variants, re-runnable, not a one-time snapshot) + citations of the 3 already-real standing controls: simulation_mode.py's real production/simulation separation (ADR-153), executive_quality_gate.py's real REJECT_IF_FAIL hard-reject pipeline (now including the new check_copyright_trademark_risk, the one genuine Legal Safety Review gap this round found and closed), and the 3 existing self-audit subsystems (resilience_monitor.py/ai_doctor.py/self_awareness.js). Never a fabricated compliance score -- see OpenClaw_Brain/00_Governance/TRUTH_FIRST_CONSTITUTION.md for the full per-item audit.",
    reused: 'truth_first.py::truth_first_compliance_report() (ADR-160) + simulation_mode.py (ADR-153) + executive_quality_gate.py, via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('truth_first_compliance', [], req),
    health: pythonHealthCheck('truth_first_compliance'),
  },
  {
    // Enterprise Digital Twin (ADR-161, 2026-07-31): flagged via
    // AskUserQuestion before any code -- "mandatory approval layer
    // before production" read as an automated execution gate,
    // colliding with the 4 standing founder-protected human-gates.
    // Founder's answer: advisory preview only. This service, and every
    // digital_twin.py function it calls, NEVER authorizes or blocks a
    // real action -- see digital_twin.py's own top docstring.
    name: 'digital-twin-dashboard',
    description: "Real REAL STATE + DIGITAL TWIN across 17 named domains (inventory honestly not_applicable -- a digital-only business), 8 named 'what happens if...' scenarios (mostly citing enterprise_scenario_simulator() and ai_provider_concentration() directly), and the real preview-action registry (5 named production action types: growth stage progression, roadmap execution, affiliate simulation cycle, publish, capital reallocation -- each honestly disclosing which of PREVIEW/SIMULATE/ESTIMATE IMPACT/ROLLBACK PLAN it can really provide). Advisory only -- never authorizes or blocks any real action. Expensive (~40s, chains growth_stages/strategic_planning/gfos/customer_pipeline/etc.).",
    reused: 'digital_twin.py::build_digital_twin_dashboard() (ADR-161) + growth_stages.py/strategic_planning.py/enterprise_executive_brain.py/global_opportunity_exchange.py/gfos.py, via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('digital_twin_dashboard', [], req, 60000),
    health: pythonHealthCheck('digital_twin_dashboard'),
  },
  {
    // Enterprise Evidence Engine (ADR-163, 2026-07-31): a real,
    // immutable, append-only evidence framework. Deliberately does NOT
    // retrofit the 18 pre-existing real data/*.jsonl ledgers or
    // logs/service_layer.log into this new schema -- they remain real,
    // valid evidence sources in their own right, cited here.
    name: 'evidence-coverage-report',
    description: "The real Evidence Coverage Report: for each of the 10 named evidence types (EXECUTION/TEST/PUBLICATION/MARKET_RESEARCH/AI_DECISION/AUTOMATION/FINANCIAL/CUSTOMER/SYSTEM/SECURITY), cites the real, already-existing evidence source(s) confirmed in this factory (18 real data/*.jsonl ledgers, logs/service_layer.log, books/_generation_log.jsonl, inspections.log/QUARANTINE.md), or honestly lists it as lacking evidence if none exists. Never invents a source.",
    reused: 'evidence_engine.py::evidence_coverage_report() (ADR-163), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('evidence_coverage_report', [], req),
    health: pythonHealthCheck('evidence_coverage_report'),
  },
  {
    name: 'evidence-viewer',
    description: "Real chronological reader over the new evidence_engine.py ledger (data/evidence_ledger.jsonl) -- honestly empty until real evidence has been recorded. Accepts optional ?evidence_type=&module= query params.",
    reused: 'evidence_engine.py::read_evidence() (ADR-163), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('evidence_viewer', [JSON.stringify({ evidence_type: req.query && req.query.evidence_type, module: req.query && req.query.module })], req),
    health: pythonHealthCheck('evidence_viewer'),
  },
  {
    // Global Search (ADR-185, 2026-08-07): a real substring search over
    // the real knowledge graph snapshot (4308+ real nodes) + competitors
    // + generated products -- never a fabricated "AI semantic search"
    // claim. Customers/files/agents/logs/tasks are honestly NOT indexed
    // (see global_search.py's own sources_not_indexed field) -- zero
    // real customer records exist, and file/log/agent indexing is a
    // separate, larger undertaking not attempted here.
    name: 'global-search',
    description: "Real substring search across the knowledge graph, competitors, and generated products. Accepts ?q= (query) and optional &limit=. Honestly discloses which named categories (customers, files, agents, logs, tasks) are not yet indexed rather than silently omitting them.",
    reused: 'global_search.py::search(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('global_search', [JSON.stringify({ query: req.query && req.query.q, limit: req.query && req.query.limit ? parseInt(req.query.limit, 10) : undefined })], req),
    health: pythonHealthCheck('global_search'),
  },
  {
    name: 'executive-evidence-dashboard',
    description: "Merges real per-type Evidence Verification (last_verified/verification_status/evidence_count/source -- honestly 'NOT VERIFIED' when a type has zero real evidence recorded) with the Evidence Coverage Report summary. Never displays a fabricated success.",
    reused: 'evidence_engine.py::verify()/evidence_coverage_report() (ADR-163), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('executive_evidence_dashboard', [], req),
    health: pythonHealthCheck('executive_evidence_dashboard'),
  },
  {
    // AI Automation Revenue Engine (ADR-164, 2026-07-31 -- the
    // directive itself said "ADR-162", already allocated to Enterprise
    // Truth Audit; renumbered). Reuses profit_oracle.py::
    // ladder_opportunity_score() verbatim -- never a second scoring
    // algorithm. Deliberately never calls golden_hunter.hunt.run_hunt()
    // (real, passive-only scanner -- see automation_opportunity_
    // scanner.py's own docstring for why, an ADR-162-addendum-informed
    // design decision made proactively this time).
    name: 'automation-revenue-dashboard',
    description: "Real opportunity discovery/scoring for AI automation-product categories (workflow systems, n8n templates, CRM/email/invoice/HR/sales/ops automation, AI copilots, knowledge assistants, etc.) -- 15 named categories mapped to real ladders, real candidates from market_hunter.py's static seed list + already-recorded real decisions (never a new live evaluation triggered), scored via profit_oracle.py's real 9-hard-gate ladder_opportunity_score(), ranked B2B-first. Honestly returns 'NO VERIFIED OPPORTUNITY FOUND' when no real candidate clears the real gates -- never invents one. 'Do NOT build products' honored literally -- zero product-generation code.",
    reused: 'automation_dashboard.py::build_automation_dashboard() (ADR-164) + profit_oracle.py, via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('automation_revenue_dashboard', [], req),
    health: pythonHealthCheck('automation_revenue_dashboard'),
  },
  {
    // Global Market Domination Engine (ADR-175, 2026-08-05): a real
    // consolidation over market_hunter.py/automation_opportunity_
    // scanner.py's real candidate discovery (now un-scoped from
    // automation-only) + GOOS's real 10-dimension evaluation (ADR-171,
    // which happens to name the exact 10 dimensions this directive
    // asks for). 6 of 8 named regions are honestly NOT_MEASURABLE -- a
    // standing, 3x-reconfirmed founder deferral (GCID/ADR-148, Global
    // Affiliate Commerce Engine/ADR-152, growth_stages.py's Stage 4),
    // applied directly here rather than re-asked a 4th time.
    // Strategic Intelligence Engine, Revenue Mode (ADR-178, 2026-08-06):
    // the founder's "generate real revenue, not more reports" directive.
    // Research found every one of its 10 named questions/8 named fields
    // already real and citable, scattered across goos.py/profit_oracle.py/
    // capital_allocation_engine.py -- the one real gap was a GLOBAL
    // cross-niche ranker (every existing ranker only orders the already-
    // ACCEPTED portfolio, currently empty). "Must feed the production
    // pipeline" repeats the exact tension goos.py itself already resolved
    // (ADR-171, AskUserQuestion): advisory citation into executive_brain.py
    // only, real 65/100 floor unchanged -- applied directly without
    // re-asking the identical question a 2nd time.
    name: 'strategic-intelligence-engine',
    description: "Global, cross-niche 'what to build next' ranking -- every real candidate niche (any decision_engine status, plus never-evaluated seed candidates) scored via GOOS's own real per-niche citation, bundling confidence/evidence sources/expected ROI/competition/difficulty/time-to-revenue/recurring-potential/strategic-importance, plus a real duplicate-product-family check and an engineering-without-revenue check. Ranked build_next / ignore / not_yet_scorable / never_evaluated buckets. Passive-only, advisory-only -- the real production gate (profit_oracle.py's 65/100 floor) is unchanged.",
    reused: 'goos.py::strategic_intelligence_engine_report() (ADR-178) + global_opportunity_exchange.py + automation_opportunity_scanner.py + capital_allocation_engine.py + decision_engine/store.py, via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('strategic_intelligence_engine_report', [], req, 60000),
    health: pythonHealthCheck('strategic_intelligence_engine_report'),
  },
  {
    name: 'market-domination-dashboard',
    description: "Real, ranked, high-value opportunity candidates across all 6 real ladders (ai_saas/b2b_systems/automation_tools/reusable_assets/educational/kdp_books, ranked by profit_oracle.py's real LADDER_RANKS priority order), each evaluated via GOOS's real 10-dimension citation (real_customer_pain/willingness_to_pay/competition_level/difficulty_of_copying/scalability/recurring_revenue_potential/automation_potential/strategic_fit/long_term_asset_value + market_size honestly NOT_MEASURABLE). Global reach: 8 of 11 registered multi_source_intelligence connectors (Amazon/Etsy/Gumroad/GitHub/Hacker News/arXiv/public search/Stack Overflow) are real and query-capable. Regional coverage for 6 of the directive's 8 named regions (everywhere except North America and 'Global online markets') is honestly NOT_MEASURABLE -- zero real local-market data connector exists anywhere in this factory, the founder's own standing 2026-07-23 deferral. Never triggers a new live evaluation cycle.",
    reused: 'market_domination_engine.py::build_market_domination_dashboard() (ADR-175) + automation_opportunity_scanner.py (ADR-164) + goos.py (ADR-171) + profit_oracle.py, via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('market_domination_dashboard', [], req),
    health: pythonHealthCheck('market_domination_dashboard'),
  },
  {
    // Enterprise Capital Allocation Engine (ADR-165, 2026-07-31 -- the
    // directive itself said "ADR-163", already allocated to Enterprise
    // Evidence Engine; renumbered). Extends -- never duplicates --
    // capital_allocation_engine.py's real 14-dim Investment Score
    // (ADR-139), reused verbatim via injection.
    name: 'enterprise-capital-allocation-dashboard',
    description: "Extends the real 14-dim Investment Score (ADR-139) with 5 more: 2 already-real-but-previously-uncited (expected_roi, scalability, both already inside value_engine.py) + 3 genuinely new (market_maturity -- honestly INSUFFICIENT EVIDENCE per niche, company-wide market_health() cited for context; legal_risk -- real per-niche executive_quality_gate.py citation; operational_risk -- real but company-wide only, disclosed). Also: Resource Allocation across 10 named strategic resources (6 have a real signal today, 4 honestly INSUFFICIENT EVIDENCE -- development time/research capacity/marketing effort/infrastructure have no real tracking anywhere in this factory), Company Capacity Utilization, Top Investments/Projects Starved of Resources/Expected Long-Term ROI (all reused verbatim from capital_allocation_engine.py), and a real, disclosed 'Projects Overfunded' heuristic (real production-run-count vs. real priority rank -- no prior analog). Expensive (reuses capital-allocation-dashboard's own real ~90s cost).",
    reused: 'enterprise_capital_allocation.py::build_enterprise_capital_allocation_dashboard() (ADR-165) + capital_allocation_engine.py (ADR-139), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('enterprise_capital_allocation_dashboard', [], req, 100000),
    health: pythonHealthCheck('enterprise_capital_allocation_dashboard'),
  },
  {
    // Capital Allocation Engine: Investment Decisions & Portfolio
    // Balance (ADR-176, 2026-08-05) -- the same name as ADR-139/165,
    // both already real. 17 of 20 named dimensions already covered;
    // the INVEST NOW/BUILD LATER/EXPERIMENT/REJECT output is a real
    // relabeling of scheduler.py's already-real 5 buckets.
    name: 'capital-decisions-report',
    description: "Real INVEST NOW/BUILD LATER/EXPERIMENT/REJECT decision + written reasoning for every real niche in scheduler.py's real buckets (run_now/accelerate -> INVEST NOW, cancel/stop -> REJECT, wait split into BUILD LATER/EXPERIMENT by the niche's own real decision-confidence level). Portfolio Balance by real ladder character (recurring income vs one-time sales; high-risk/stable/long-term-strategic honestly NOT_MEASURABLE -- no real per-niche risk-maturity signal exists). Resource optimization citing strategic_planning.py's real rolling roadmap. Expected Monthly/Annual Revenue and Time to First Sale are honestly NOT_MEASURABLE as forward projections (this factory's real 'expected_revenue' is retrospective closed-sale revenue to date, never a forecast -- multiplying it by 12 would be a fabricated projection). Customer Trust Impact and Compounding Value cite brand_dna.py's Trust Framework and a real combination of 2 already-real Investment Score dimensions, respectively.",
    reused: 'enterprise_capital_allocation.py::build_capital_decisions_report() (ADR-176) + scheduler.py + strategic_planning.py + brand_dna.py, via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('capital_decisions_report', [], req, 60000),
    health: pythonHealthCheck('capital_decisions_report'),
  },
  {
    // Enterprise Truth Registry (ADR-168, 2026-07-31): the real,
    // mechanical per-component inventory over all ~246 real internal
    // Python modules -- name/category/purpose/location/owner/
    // dependencies/dependents/status/production usage/live verified/
    // test coverage/last verification/last commit/confidence/
    // criticality -- plus the directive's 10 named summary sections
    // and an Enterprise Truth Score. Re-invokes reality_audit.py's own
    // live 152-endpoint scan internally -- genuinely the most
    // expensive panel in this factory (measured live ~255s for the
    // registry alone, before the report's own cheap aggregation).
    name: 'truth-registry-report',
    description: "The single authoritative real inventory of every one of this factory's ~246 real internal Python modules -- never invented, never inferred, every field traced to a real signal (reality_audit.py's live endpoint classification attributed down to the modules each endpoint's own source imports, dependency_graph.py's real AST-based import graph, gfos.py's real per-department module citation, real git history per file). Most modules honestly report UNKNOWN status/confidence -- reality_audit.py only classifies the ~152 Mission Control endpoint wrapper functions, not every module they transitively import, and this scan never inflates that gap. Produces Company Inventory / Operational / Experimental / Missing / Broken / Duplicate / Dead Code / Orphan / Never-Verified Components + Enterprise Truth Score (0-100, a disclosed additive heuristic), and answers 'could the company be reconstructed from this registry alone' -- always honestly NO, with the real reasons why (gitignored secrets, live third-party account state, the real UNKNOWN-status modules themselves). Extremely expensive: measured live ~255s.",
    reused: 'truth_registry.py::build_truth_registry()/build_truth_registry_report() (ADR-168) + reality_audit.py (ADR-162) + dependency_graph.py + gfos.py, via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('truth_registry_report', [], req, 600000),
    health: pythonHealthCheck('truth_registry_report'),
  },
  {
    // Customer Experience & Brand DNA (ADR-170, 2026-08-05): the real
    // Company Personality/Communication Standards/Customer Journey
    // Standards/Trust Framework/Customer Memory Architecture/Continuous
    // Improvement citation report. Cheap -- no live scan.
    name: 'brand-dna-report',
    description: "Company Personality (9 named traits, each a real behavioral rule + a real citation of where this factory already demonstrates it in practice, e.g. customer_site/index.html's own copy), Communication Standards (8 named rules), Customer Journey Standards (10 named stages, honestly 8/10 REAL against customer_pipeline.py's real STAGE_ORDER -- Complaint Handling and Refund Requests are genuine, disclosed gaps, not fabricated as done), Trust Framework (5 named principles, 5/5 REAL -- 4 already-existing executive_quality_gate.py checks + one new one, check_fake_urgency_risk(), the one genuine gap found), Customer Memory Architecture (honestly FUTURE_INSTRUMENTATION -- a real design sketch, not a built system, since zero real customer preference data exists yet), and Continuous Improvement sources (citing evolution_queue.py's real signals, never a second learning loop).",
    reused: 'brand_dna.py::brand_dna_report() (ADR-170) + executive_quality_gate.py + customer_pipeline.py, via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('brand_dna_report', [], req),
    health: pythonHealthCheck('brand_dna_report'),
  },
  {
    // Enterprise Growth Engine (ADR-158, 2026-07-31): "automatic
    // fallback" (the directive's Objective 3) is implemented as
    // non-cached, non-sticky recomputation, not a triggered action --
    // same read-only-status-label discipline as company_state() above
    // (ADR-157). Stage 5 is honestly reported as blocked by standing
    // founder policy (the 4 protected gates), never a fabricated data
    // threshold.
    name: 'growth-stage-status',
    description: "The real Executive Growth Dashboard: current company-wide Growth Stage (0 Bootstrap - 5 Autonomous Enterprise, recomputed fresh every call from real signals -- decision_engine ACCEPTED count, real production runs, channels/ledger.py revenue, resilience_monitor incidents, launch_readiness.py per-division scores), remaining requirements/blocking factors for the next stage, estimated readiness %, per-division stage objectives (7 named divisions, a disclosed strategic-guidance template paired with each division's real signal), and the highest-ROI action to advance (pure citation of enterprise_scheduler(), no new ranking). Answers the directive's 3 named questions directly. Expensive (chains enterprise_scheduler() -> capital_allocation_engine, measured live ~30s).",
    reused: 'growth_stages.py::build_growth_dashboard()/answer_growth_questions() (ADR-158) + enterprise_executive_brain.py::enterprise_scheduler() (ADR-156), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('growth_stage_status', [], req, 60000),
    health: pythonHealthCheck('growth_stage_status'),
  },
  {
    // Enterprise Strategic Planning System (ADR-159, 2026-07-31): almost
    // entirely a citation/relabeling layer over gfos.py/growth_stages.py/
    // executive_questions.py/execution_status.py, each computed exactly
    // once inside strategic_planning.py::build_strategic_planning_
    // dashboard() -- the 4th consecutive round this session guarding
    // against the redundant-full-portfolio-scan bug class (ADR-155/156).
    name: 'strategic-planning-dashboard',
    description: "The real rolling roadmap (Today/This Week/This Month/This Quarter/This Year -- a disclosed heuristic re-bucketing of scheduler.py's real buckets + Growth Stage requirements, never a committed calendar date, since this factory has no scheduler and no real historical duration model), per-division status board (7 divisions: objectives/progress/risks/dependencies/blocked tasks/estimated completion -- estimated completion is honestly Unknown), the Enterprise Priority Matrix (8 real columns per ACCEPTED opportunity, execution_status.py's own real Priority Score order, never a second ranking algorithm), instant answers to 'build next / delay / highest ROI / blocks growth', and an extended Executive Timeline (milestones + real Growth Stage history + architectural decisions). Expensive (measured live ~70s, chains answer_strategic_questions() + build_growth_dashboard() + build_execution_status_report()).",
    reused: 'strategic_planning.py::build_strategic_planning_dashboard() (ADR-159) + gfos.py/growth_stages.py/executive_questions.py/execution_status.py/launch_readiness.py/enterprise_operations.py, via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('strategic_planning_dashboard', [], req, 90000),
    health: pythonHealthCheck('strategic_planning_dashboard'),
  },
  {
    // Executive Command Center (ADR-146, 2026-07-30): reuses
    // multi_source_intelligence.registry.get_connectors() verbatim --
    // never a second connector list. Static-unavailable sources
    // (reddit/product_hunt/google_trends) are cheaply checked (none of
    // the three touches its own niche argument, confirmed by reading
    // each); real live-capable sources (hacker_news/github/etc.) are
    // listed as registered without being triggered, avoiding an
    // accidental live network call from a passive dashboard read.
    name: 'market-intelligence-source-status',
    description: "The real, registered external-evidence-source inventory for the Market Intelligence panel -- which real connectors exist, which are honestly unavailable today and why (missing credentials, requires prior commercial contact, n8n gate not activated), and which are real/live-capable but not triggered from this read-only view.",
    reused: 'multi_source_intelligence/registry.py::get_connectors() (ADR-059) + each connector real check() (ADR-146), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('market_intelligence_source_status', [], req),
    health: pythonHealthCheck('market_intelligence_source_status'),
  },
  {
    // Executive Decision Memory (ADR-145, 2026-07-30): distinct from the
    // existing 'decision-history' panel below (niche decisions only) --
    // this merges real niche decisions AND real Executive Directives
    // into one unified, decision_id-tagged view with confidence/
    // duplicate-check annotations. Cheap: two real file reads + a
    // merge-sort, no dashboard rebuild.
    name: 'decision-memory',
    description: "The real unified recent-decision view across both real ledgers (decision_engine/store.py niche decisions + executive_brain.py Executive Directives), most recent first, each tagged with its own real decision_id/status/confidence/duplicate_check.",
    reused: 'executive_decision_memory.py::list_decision_memory() (ADR-145), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('decision_memory_list', [], req),
    health: pythonHealthCheck('decision_memory_list'),
  },
  {
    name: 'decision-memory-conflicts',
    description: "Real, mechanical conflict detection across the most recent Executive Directives -- the same real niche recommended both 'accelerate' and 'stop' within the lookback window. Never a semantic/AI judgment; honestly empty when no real conflict exists.",
    reused: 'executive_decision_memory.py::detect_ledger_conflicts() (ADR-145), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('decision_memory_conflicts', [], req),
    health: pythonHealthCheck('decision_memory_conflicts'),
  },
  {
    name: 'decision-memory-explain',
    description: "The real 'explain why' function -- pass ?decision_id=<id> to get the full real evidence/reasoning/conflict-check trail for either a real niche Decision or a real Executive Directive, whichever real ledger actually carries that decision_id.",
    reused: 'executive_decision_memory.py::explain_decision() (ADR-145), via mission_control_api.py.',
    handler: (req) => {
      const decisionId = (req.query.decision_id || '').trim();
      if (!decisionId) {
        return Promise.resolve({ found: false, reason: 'مرِّر ?decision_id=<المعرِّف> لشرح قرار محدَّد -- لا معرِّف مُحدَّد بعد' });
      }
      return runPythonServiceCached('decision_memory_explain', [JSON.stringify({ decision_id: decisionId })], req);
    },
    health: pythonHealthCheck('decision_memory_explain'),
  },
  {
    name: 'capital-allocation-dashboard',
    description: "Top ROI Initiatives, Projects Losing Value, Projects Consuming Resources Without Results, Resource Distribution, Expected Portfolio Return, and real opportunity-cost pairings -- every field a citation of an already-real portfolio/scheduling/lifecycle function, computed exactly once and threaded through, never a second scan.",
    reused: 'capital_allocation_engine.py::build_capital_allocation_dashboard()',
    handler: (req) => runPythonServiceCached('capital_allocation_dashboard', [], req, 90000),
    health: pythonHealthCheck('capital_allocation_dashboard'),
  },
  {
    // Capital Allocation Engine (2026-07-29) -- the opportunity-cost
    // pairing on its own, without the full dashboard above. Found
    // orphaned by the Company Readiness Audit (2026-07-31); real,
    // tested, callable, simply never wired into a route of its own.
    name: 'opportunity-cost-report',
    description: "The real opportunity-cost pairing alone -- for every real ACCEPTED opportunity in scheduler.py's own wait/stop/cancel buckets, which run_now/accelerate opportunities rank higher by the same real Priority Score order. A narrower, cheaper citation than the full capital-allocation-dashboard above for a caller that only needs this one field.",
    reused: 'capital_allocation_engine.py::opportunity_cost()',
    handler: (req) => runPythonServiceCached('opportunity_cost_report', [], req, 60000),
    health: pythonHealthCheck('opportunity_cost_report'),
  },
  {
    // Global Opportunity Exchange (2026-07-29): measured live at ~11s of
    // real compute (build_value_engine_report() + the 4 concentration
    // checks); given this machine's disclosed `python3` startup-tax
    // variability (0-30s, confirmed across earlier rounds this session),
    // a 60s timeout gives real margin without the full 90s the heavier
    // capital-allocation-dashboard/executive-brief outliers needed.
    name: 'global-opportunity-exchange',
    description: "Global Opportunity Map, Capital Flow Between Markets, Market Health/Saturation, Opportunity Ranking, Revenue Distribution, Market Dependency Index (platform/product_family/country/ai_provider concentration vs. named thresholds), and real diversification recommendations. Honestly DISCOVERY-heavy today -- only 4 of 15 named marketplaces have a real channel arm, 0 real sale events exist, country dependency is a permanent structural DISCOVERY per CLAUDE.md's own founder-confirmed 2026-07-23 decision.",
    reused: 'global_opportunity_exchange.py::build_global_opportunity_exchange_dashboard()',
    handler: (req) => runPythonServiceCached('global_opportunity_exchange_dashboard', [], req, 60000),
    health: pythonHealthCheck('global_opportunity_exchange_dashboard'),
  },
  {
    // Global Opportunity Exchange (2026-07-29) -- the 4 named
    // concentration-risk checks alone, without the full dashboard
    // above. Found orphaned by the Company Readiness Audit
    // (2026-07-31); real, tested, callable, never wired to a route.
    name: 'concentration-risk-report',
    description: "The real 4 named concentration-risk checks alone (platform/product_family/country/ai_provider vs. their named thresholds: >40%/>30%/>25%/>20%) -- a narrower, cheaper citation than the full global-opportunity-exchange dashboard above for a caller that only needs this one field.",
    reused: 'global_opportunity_exchange.py::concentration_risk_report()',
    handler: (req) => runPythonServiceCached('concentration_risk_report', [], req, 30000),
    health: pythonHealthCheck('concentration_risk_report'),
  },
  {
    // Autonomous Business Builder (2026-07-29): a thin citation of
    // production_blueprint.py's already-real, already-cheap 6-bucket
    // missions board (its own existing callers already treat this as
    // fast -- no new timeout disclosure needed beyond the shared default).
    name: 'business-pipeline',
    description: "ABB's real Business Pipeline / Blueprint Status: every real ACCEPTED opportunity bucketed into 6 real production statuses (READY TO BUILD/BUILDING/QUALITY REVIEW/READY TO SELL/LIVE/LEARNING). Investment Required/Expected Return/Priority/Risk/Confidence are direct citations of investment_score()'s/value_engine's already-real fields, available per-niche via the build-business-blueprint action.",
    reused: 'autonomous_business_builder.py::business_pipeline_summary() -> production_blueprint.py::build_production_missions_board()',
    handler: (req) => runPythonServiceCached('business_pipeline_summary', [], req),
    health: pythonHealthCheck('business_pipeline_summary'),
  },
  {
    // Commercial Execution Engine v1 (ADR-180, 2026-08-06): read-only
    // ledger passthrough -- real generation happens exclusively in
    // factory_loop.js's daily tick (maybeGenerateCommercialKitsForNew
    // AcceptedDecisions()) or via a real founder-triggered run; this
    // panel never generates anything itself.
    name: 'generated-commercial-kits',
    description: "Real, append-only record of every commercial launch kit this factory has auto-generated for a real ACCEPTED opportunity (product positioning, pricing strategy, Gumroad/sales/landing page copy, SEO package, launch checklist, marketing assets, email + social campaigns, customer acquisition plan, continuous optimization plan) -- product_marketing_engine.py, most recent first.",
    reused: 'product_marketing_engine.py::list_generated_commercial_kits()',
    handler: (req) => runPythonServiceCached('list_generated_commercial_kits', [], req),
    health: pythonHealthCheck('list_generated_commercial_kits'),
  },
  {
    // Pricing Review Trigger (ADR-182, 2026-08-07): real, mechanical,
    // read-only -- never recommends a tier change without >=1 real paid
    // customer and >=1 real review. Same check factory_loop.js's daily
    // tick also runs (maybeCheckEuAiActPricingReview()); this panel is
    // just the on-demand view, never a second computation.
    name: 'eu-ai-act-pricing-review',
    description: "Whether the EU AI Act Compliance Toolkit has earned an Elite-tier ($310, already validated real) pricing review yet -- requires >=1 real paid customer AND >=1 real review, never elapsed time alone.",
    reused: 'pricing_review.py::check_eu_ai_act_toolkit_pricing_review()',
    handler: (req) => runPythonServiceCached('eu_ai_act_pricing_review', [], req),
    health: pythonHealthCheck('eu_ai_act_pricing_review'),
  },
  {
    name: 'execution-phases',
    description: "The real, company-wide 5-phase execution roadmap (orchestrator.types.EXECUTION_ORDER): market_intelligence -> decision -> production -> publishing -> learning, each with real per-stage engine health and a real, disclosed deterministic rollback plan (Dual Inspection quarantine, publish-protection emergency stop, etc.) -- never a fabricated task list this factory doesn't track.",
    reused: 'autonomous_business_builder.py::execution_phases()',
    handler: (req) => runPythonServiceCached('execution_phases', [], req),
    health: pythonHealthCheck('execution_phases'),
  },
  {
    // Final Executive Directive (2026-07-29): pure citation, no real
    // sub-computation beyond activity_status()/autonomous_operations_
    // summary()'s own fixed dict lookups -- cheap, no timeout disclosure
    // needed beyond the shared default.
    name: 'autonomous-operations-status',
    description: "Answers the directive's own implicit question -- is Galaxy Forge running autonomously right now, and exactly what does that include. The directive's ~21 named activities, each honestly tagged automatic/automatic_new/human_gated_by_design/ambiguous_not_touched against this factory's real, current code, plus the 4 Founder-protected gates and the master_loop.py always-on-daemon precedent (declined 3x: ADR-107/110/115) -- so this decision's history is never lost or silently re-litigated.",
    reused: 'autonomous_operations_status.py::activity_status()/autonomous_operations_summary()',
    handler: (req) => runPythonServiceCached('autonomous_operations_status', [], req),
    health: pythonHealthCheck('autonomous_operations_status'),
  },
  {
    // Global Trust & Resilience Layer, Round 2 (2026-07-29): real
    // per-subsystem Safe Mode -- an unstable subsystem is isolated on
    // its own, the rest of the company keeps running. Read-only here;
    // the founder-only mark/clear actions are in ACTION_REGISTRY below.
    name: 'safe-mode-status',
    description: "Real per-subsystem isolation state -- ai_generation and market_intelligence have their own real flag; marketplace_publishing is a live passthrough to channels/publish_protection.py's global emergency stop (never a second, duplicated flag for the same real concern). Never auto-clears -- only a real founder action does.",
    reused: 'safe_mode.py list_safe_mode_status() (Global Trust & Resilience Layer, Round 2), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('safe_mode_status', [], req),
    health: pythonHealthCheck('safe_mode_status'),
  },
  {
    // Global Commercial Hardening, Phase 1 (2026-07-29): the real
    // Marketplace Publish Protection Layer -- per-arm publish counts,
    // cooldowns, and a real risk_score, plus the global emergency-stop
    // flag. Read-only here; the two founder actions that actually halt/
    // resume publishing are in ACTION_REGISTRY below, never auto-fired.
    name: 'publish-protection-status',
    description: "Real marketplace publish-protection state -- per-arm daily/hourly publish counts, active cooldowns (from repeated real failures), a real risk_score, and whether each arm is currently allowed to publish. Honestly empty until a real (non-dry-run) publish attempt has ever been recorded for an arm.",
    reused: 'channels/publish_protection.py list_publish_protection_status() (Global Commercial Hardening, Phase 1), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('publish_protection_status', [], req),
    health: pythonHealthCheck('publish_protection_status'),
  },
  {
    // Autonomous Company Evolution Engine, Round 6 (2026-07-29): the real
    // Evolution Queue -- every real proposal's stage, the founder's own
    // real approval backlog (with a real, informational stuck-too-long
    // flag), and the full Learning History. Read-only here; the three
    // founder actions that actually move a proposal (approve/reject/
    // mark-implemented) are in ACTION_REGISTRY below, never auto-fired.
    name: 'evolution-queue',
    description: "The real Evolution Queue -- every real proposal from tool_intelligence.proposals.list_proposals(), its real simulated impact/rollback-complexity, a real disclosed-heuristic ranking (revenue_impact/execution_cost/long_term_sustainability_concern/risk/confidence -- strategic_value honestly not_computed, no per-proposal signal exists), and its real stage (PROPOSED/SIMULATED/AWAITING_FOUNDER_APPROVAL/APPROVED/REJECTED/IMPLEMENTED). Nothing auto-approves or auto-executes; every proposal, whatever its computed risk tier, waits for a real founder decision.",
    reused: 'evolution_queue.py list_evolution_queue() (Round 1) + rank_proposal() (Round 2), fed daily by factory_loop.js maybeGenerateDailyEvolutionQueueIntake() (Round 4), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('evolution_queue', [], req),
    health: pythonHealthCheck('evolution_queue'),
  },
  {
    // Autonomous Evolution Engine directive, Round 2 (2026-07-30): "the
    // system continuously measures whether every implemented evolution
    // actually improved" revenue/reliability/customer value -- the real
    // Measure step. Read-only here; the automatic daily measurement cycle
    // is factory_loop.js's maybeMeasureEvolutionOutcomes(), never a new
    // execute-capable action.
    name: 'evolution-measured-outcomes',
    description: "Real before/after outcome measurement for every real IMPLEMENTED evolution proposal -- a real baseline snapshot captured at mark-implemented time (revenue via channels/ledger.py revenue_trend(), reliability via health_trend.py's GET /health history, customer value via customer_pipeline.py funnel_conversion_summary()) compared against a fresh snapshot no sooner than 7 real elapsed days later. Reports IMPROVED/DEGRADED/NO_CHANGE/NOT_ENOUGH_DATA per dimension -- scalability/automation/execution_speed are honestly NO_REAL_SIGNAL, never fabricated. Each real measurement appends to the proposal's own trend, so this panel is a real Learning History of whether this factory's own self-changes actually helped.",
    reused: 'evolution_queue.py list_measured_outcomes() + measure_outcome() (Round 2, 2026-07-30), fed daily by factory_loop.js maybeMeasureEvolutionOutcomes(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('evolution_measured_outcomes', [], req),
    health: pythonHealthCheck('evolution_measured_outcomes'),
  },
  {
    name: 'market-review',
    description: "Weekly Market Review -- niches scanned, real opportunity-gap/customer-pain trend (period vs. all-time), and top rejection reasons. The one weekly Continuous Improvement Engine review type that had no real generator before EOS Phase 1.",
    reused: 'market_intelligence_core/market_review.py generate_market_review() (EOS Phase 1, 2026-07-19) -- reuses strategic_intelligence.rejection_patterns.most_frequent_rejection_reasons() verbatim, no reimplementation.',
    handler: (req) => runPythonServiceCached('market_review', [], req),
    health: pythonHealthCheck('market_review'),
  },
  {
    name: 'strategic-recommendations',
    description: "Strategic Recommendations tab: strategic_intelligence's real decision-pattern/rejection/technical-debt report (ADR-054), previously only reachable bundled inside the combined executive report, plus the same real tool-integration proposals as tool-recommendations.",
    reused: 'strategic_intelligence/report.py generate_strategic_report() (ADR-054) + tool_intelligence/proposals.py, via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('strategic_report', [], req),
    health: pythonHealthCheck('strategic_report'),
  },
  {
    name: 'tool-recommendations',
    description: "Real, evidence-cited software/AI-tool integration proposals -- '(مقترَح، لا تنفيذ)' (proposed, not implemented), matching the existing ADR-024 convention. Every proposal is grounded in a real gap this factory's own audits found, with why/business-value/effort/ROI/dependencies/risks fields — never a generic tool pitch.",
    reused: 'tool_intelligence/proposals.py list_proposals() (Autonomous Digital Company v1, Track B3, 2026-07-19), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('tool_intelligence', [], req),
    health: pythonHealthCheck('tool_intelligence'),
  },
  {
    name: 'infrastructure-status',
    description: "Real CPU/memory/disk (Node's os/fs modules) plus a real AI cost-rate trend over data/ai_cost_log.jsonl (this week's real spend vs. the real trailing daily average). No fabricated 'quota remaining' — Groq exposes no queryable quota API.",
    reused: 'lib/infrastructure_intelligence.js getInfrastructureStatus() (Autonomous Digital Company v1, Track B1, 2026-07-19) — pure os/fs + JSONL reads, no new dependency.',
    handler: async () => infrastructureIntelligence.getInfrastructureStatus(),
    health: fsHealthCheck(() => infrastructureIntelligence.getSystemResources(), 'os/fs resource read check ok'),
  },
  {
    name: 'evidence-engine-status',
    description: 'Galaxy Forge Executive Mission Control v1 (2026-07-24): real aggregate over the Market Evidence Ledger (ADR-088, extended by ADR-121/122) — total real events, how many real niches have any, a breakdown by event type, and how many are Proof-of-Payment-qualifying. Honestly reports the ledger as empty when it is (it has never been populated automatically, by design — ADR-121).',
    reused: 'data/market_evidence.jsonl, the exact same real ledger market_evidence.py/profit_oracle.py already read — no new engine, a plain read + count.',
    handler: evidenceEngineService,
    health: fsHealthCheck(() => fs.existsSync(path.join(__dirname, 'data')), 'data/ directory reachable'),
  },
  {
    name: 'scheduler-status',
    description: 'Galaxy Forge Executive Mission Control v1 (2026-07-24): the one real, durable scheduler in this factory — the Windows Scheduled Task OpenClaw-WeeklyPublicReport (ADR-119), queried live via Get-ScheduledTask. Honestly reports unavailable on non-Windows or if the task cannot be found.',
    reused: 'Windows Task Scheduler itself, via a real PowerShell Get-ScheduledTask call — same pattern lib/health_checks.js checkDiskSpace() already established for real Windows-only checks.',
    handler: schedulerStatusService,
    health: async () => ({ status: 'ok', detail: 'dependency check only: PowerShell availability assumed on this Windows host' }),
  },
  {
    name: 'recent-adr-decisions',
    description: 'Galaxy Forge Executive Mission Control v1 (2026-07-24): the 20 most recent real ADRs (title/date/status parsed from each file\'s own real header) — every governance decision this factory has actually made, newest first.',
    reused: 'OpenClaw_Brain/00_Governance/ADR-*.md — a plain directory read, no new engine.',
    handler: recentAdrDecisionsService,
    health: fsHealthCheck(() => fs.existsSync(path.join(__dirname, 'OpenClaw_Brain', '00_Governance')), 'governance directory reachable'),
  },
  {
    name: 'system-logs',
    description: 'Galaxy Forge Executive Mission Control v1 (2026-07-24): the real tail (last 20 lines) of every real operational log file this factory writes — factory_loop.log, scout_runs.log, finance_errors.log, supervisor.log, server_crashes.log. Honestly reports a file as not existing if it has never been written.',
    reused: 'the real log files themselves, at the repo root — a plain tail read, no new engine.',
    handler: systemLogsService,
    health: async () => ({ status: 'ok', detail: 'dependency check only: fs module reachable' }),
  },
  {
    // Global Commercial Revenue Operating System, Sections 1 + 18
    // (ADR-202, 2026-08-07): the CEO's real revenue dashboard, tagged
    // ACTUAL/ESTIMATED/PROJECTED explicitly, + the Global Commercial
    // Score.
    name: 'commercial-control-center',
    description: "Real revenue dashboard (Total/Today/Week/Month/MRR/ARR/Net/Refunds/Fees/by-Platform/by-Product/by-Country/Trend/Conversion/CAC/CLV), every field tagged ACTUAL/ESTIMATED/PROJECTED explicitly, plus a Global Commercial Score averaging only the dimensions with a real computed value. $0 real revenue today -- honestly reported, not hidden.",
    reused: 'commercial_control_center.py::revenue_snapshot()/global_commercial_score(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('commercial_control_center', [], req),
    health: pythonHealthCheck('commercial_control_center'),
  },
  {
    name: 'commercial-daily-brief',
    description: "CEO Daily Commercial Brief: Revenue/Net Revenue/Best Product/Best Platform/Best Market/Best Acquisition Channel/Top Opportunity/Top Partnership/Top Affiliate Opportunity/Biggest Commercial Risk/Biggest Revenue Leak/Recommended Action -- every field a real citation, never a fabricated 'best' when all real values are tied at $0.",
    reused: 'commercial_control_center.py::commercial_daily_brief(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('commercial_daily_brief', [], req),
    health: pythonHealthCheck('commercial_daily_brief'),
  },
  {
    name: 'commercial-reconciliation',
    description: "Real, read-only reconciliation of Paddle's live /transactions API against internal finance_data.json -- Gumroad/Etsy/Payhip honestly report NOT_RECONCILABLE (no real credential configured) rather than a fabricated zero-discrepancy match. Never modifies any financial record.",
    reused: 'commercial_reconciliation.py::reconcile_all(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('commercial_reconciliation_report', [], req),
    health: pythonHealthCheck('commercial_reconciliation_report'),
  },
  {
    name: 'product-master-catalog',
    description: "Real, read-only merged product catalog over data/paddle_products.json (real Paddle products), affiliate_commerce/products.py (real Amazon Associates products), and config/reality.json's published_books -- never a second mutable source of truth. Deliberately not built from books/_generation_log.jsonl's 5,000+ mostly-test entries.",
    reused: 'product_master_catalog.py::build_product_master_catalog(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('product_master_catalog', [], req),
    health: pythonHealthCheck('product_master_catalog'),
  },
  {
    name: 'commercial-alerts',
    description: "6 of 11 named commercial alert triggers with a real, mechanical check (revenue drop, platform failure, checkout unavailable, payment integration failure, high-value partnership, commercial discrepancy) -- the other 5 honestly disclosed NOT_ARCHITECTED with a specific real reason each (no fabricated refund/trend/competitor-pricing signal exists anywhere in this factory).",
    reused: 'commercial_alerts.py::assess_commercial_alerts(), via mission_control_api.py; reuses resilience_monitor.py\'s own _finding() shape.',
    handler: (req) => runPythonServiceCached('commercial_alerts_status', [], req),
    health: pythonHealthCheck('commercial_alerts_status'),
  },
  {
    name: 'commercial-acquisition-and-funnel',
    description: "Customer Acquisition (9 named channels) + Commercial Funnel (11 named stages) -- top-of-funnel and per-channel CAC/LTV/ROI honestly report INSUFFICIENT_DATA/NO_REAL_SOURCE (no web analytics, lead-capture, or per-channel attribution exists yet); bottom-funnel stages real-cite customer_pipeline.py's own STAGE_ORDER and business_development.py's real partnership pipeline.",
    reused: 'commercial_acquisition.py::customer_acquisition_report()/commercial_funnel(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('commercial_acquisition_and_funnel', [], req),
    health: pythonHealthCheck('commercial_acquisition_and_funnel'),
  },
  {
    // Adaptive Growth & Resource Allocation Engine, Section 16 (ADR-206,
    // Phase 16, 2026-08-08).
    name: 'adaptive-priority-queue',
    description: "Dynamic priority queue -- wraps eos-decision-feed's real, already-cited cards with the 4 genuinely missing structural fields (Actual Value, Owner, Status, Last Evaluation) plus a real weak-evidence flag per item via anti_bias_check.py. Actual Value is never backfilled from Expected Value -- it stays NOT_YET_MEASURED until a real outcome exists.",
    reused: 'adaptive_priority_queue.py::build_adaptive_priority_queue(), via mission_control_api.py -- reuses eos_decision_feed.py verbatim, never a second ranking engine.',
    handler: (req) => runPythonServiceCached('adaptive_priority_queue', [], req),
    health: pythonHealthCheck('adaptive_priority_queue'),
  },
  {
    name: 'capital-efficiency-report',
    description: "Revenue per unit of development effort/AI cost/marketing cost/human intervention/product/platform/customer -- computed where a real denominator exists (AI cost, product count, platform count), honestly UNKNOWN where no real tracking exists anywhere in this factory (development time, marketing spend, human intervention time). $0 real revenue today means every computable ratio correctly evaluates to $0.",
    reused: 'capital_efficiency.py::capital_efficiency_report(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('capital_efficiency_report', [], req),
    health: pythonHealthCheck('capital_efficiency_report'),
  },
  {
    // Global Intelligence & Competitive Moat Engine, Sections 16-17
    // (ADR-207, Phase 17, 2026-08-08).
    name: 'competitive-moat-assessment',
    description: "Real, evidence-cited classification of the 12 named defensibility mechanisms (WEAK/MODERATE/STRONG/NON-EXISTENT) for the one real product with real evidence -- distinct from profit_oracle.py's own market-crowding defensibility score, cited not duplicated. 0 of 12 mechanisms are STRONG today; unique_intelligence (the real, verified regulatory timeline) is the strongest real moat this product has.",
    reused: 'competitive_moat_engine.py::assess_eu_ai_act_toolkit_moat(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('competitive_moat_assessment', [], req),
    health: pythonHealthCheck('competitive_moat_assessment'),
  },
  {
    // Knowledge Graph & Institutional Memory Engine, Section 15
    // (ADR-208, Phase 18, 2026-08-08).
    name: 'contradiction-report',
    description: "Real, mechanical contradiction detection: conflicting market-estimate scores or ACCEPTED/REJECTED status flip-flops for the same real niche across its own real evaluation history (decisions.jsonl), plus a live price cross-check between the internal Paddle product record and the live Paddle API. 19 real contradictions found in this factory's own decision history as of this build -- never silently resolved to whichever value is convenient.",
    reused: 'contradiction_engine.py::detect_all_contradictions(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('contradiction_report', [], req),
    health: pythonHealthCheck('contradiction_report'),
  },
  {
    name: 'knowledge-staleness-report',
    description: "Real staleness check over a manually-maintained registry of already-dated facts (Payhip API status, commission rates, EU AI Act regulatory timeline, AI model capabilities) against real, disclosed per-category thresholds. A real, disclosed limitation: this registry does not automatically discover new facts to track.",
    reused: 'knowledge_decay.py::assess_all_known_knowledge(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('knowledge_staleness_report', [], req),
    health: pythonHealthCheck('knowledge_staleness_report'),
  },
  {
    // Autonomous Operations & Continuous Improvement Engine, Section 4
    // (ADR-209, Phase 19, 2026-08-08).
    name: 'unified-operations-queue',
    description: "Merges 5 already-real sources (adaptive priority queue, open resilience incidents, evolution proposals awaiting founder approval, DEFERRED decisions, automation candidates) into one shape -- never a second, competing priority engine. Priority/Risk/Confidence stay honestly heterogeneous across source types.",
    reused: 'autonomous_operations.py::unified_operations_queue(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('unified_operations_queue', [], req),
    health: pythonHealthCheck('unified_operations_queue'),
  },
  {
    name: 'autonomy-levels',
    description: "The 7 named autonomy levels (0 OBSERVE ONLY through 6 NEVER AUTOMATE) plus the real, disclosed action-category registry every authorize_action() call is checked against, each citing the real function that already enforces it.",
    reused: 'autonomous_operations.py::AUTONOMY_LEVELS/ACTION_CATEGORY_AUTONOMY, via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('autonomy_levels', [], req),
    health: pythonHealthCheck('autonomy_levels'),
  },
  {
    name: 'automation-candidates',
    description: "Real, disclosed catalog of this factory's known repeated human tasks (manual evidence verification, founder approvals), each classified AUTOMATE_NOW/AUTOMATE_LATER/KEEP_HUMAN/REMOVE with a cited real reason -- never 'automate because repetitive.'",
    reused: 'autonomous_operations.py::automation_candidate_report(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('automation_candidates', [], req),
    health: pythonHealthCheck('automation_candidates'),
  },
  {
    name: 'incident-lifecycle',
    description: "Honest 8-stage lifecycle view (DETECTED...LEARNED) over resilience_monitor.py's real incident record -- only DETECTED/CLOSED have a real, separately-timestamped signal today; the other 6 stages are disclosed as unmeasured, never inferred.",
    reused: 'autonomous_operations.py::incident_lifecycle_view(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('incident_lifecycle', [], req),
    health: pythonHealthCheck('incident_lifecycle'),
  },
  {
    name: 'daily-autonomous-review',
    description: "Citation-only aggregator over ceo_home.build_ceo_home_briefing() (ADR-184) + the real unified operations queue, reshaped into Top-5 Risks/Actions/Opportunities/Improvements + items requiring CEO approval. Computes nothing new.",
    reused: 'autonomous_operations.py::daily_autonomous_review(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('daily_autonomous_review', [], req),
    health: pythonHealthCheck('daily_autonomous_review'),
  },
  {
    name: 'autonomous-daily-score',
    description: "10 named operational indicators (Automation Success, Recovery Success, Human Intervention, Commercial Reliability, Customer Trust, AI Reliability, Data Integrity, Knowledge Growth, Decision Accuracy, Continuous Improvement) -- each a real citation of an already-computed value or an honest NOT_MEASURABLE. No single fabricated composite score.",
    reused: 'autonomous_operations.py::autonomous_daily_score(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('autonomous_daily_score', [], req),
    health: pythonHealthCheck('autonomous_daily_score'),
  },
  {
    // Global Commercial Scale & Expansion Engine, Section 26/33
    // (ADR-210, Phase 20, 2026-08-08).
    name: 'global-commercial-scale-dashboard',
    description: "The Evidence Gate (16 named fields, honestly INSUFFICIENT_EVIDENCE today -- $0 real revenue), Scaling Eligibility (per real product, evidence-driven, never above TESTING/VALIDATED today), Unit Economics (real fee model for 5 tiers, every untracked cost honestly UNKNOWN), Concentration Risk (reused verbatim), Market Prioritization (reused verbatim), the real B2B Commercial Engine finding (0 of 98 real niches ever tagged ai_saas/b2b_systems), Partnerships, Revenue Forecast (6 categories kept structurally separate), and Commercial Reputation -- 9 real sub-reports computed exactly once.",
    reused: 'global_commercial_scale.py::build_global_commercial_scale_dashboard(), via mission_control_api.py. Measured live ~23s.',
    handler: (req) => runPythonServiceCached('global_commercial_scale_dashboard', [], req, 60000),
    health: pythonHealthCheck('global_commercial_scale_dashboard'),
  },
  {
    name: 'autonomous-scale-recommendations',
    description: "Real, per-product scale recommendations (TEST/MEASURE/SCALE/MAINTAIN), each checked through autonomous_operations.py's real authorize_action() (ADR-209) -- never self-executes anything; irreversible actions stay founder-gated exactly as before.",
    reused: 'global_commercial_scale.py::autonomous_scale_recommendations(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('autonomous_scale_recommendations', [], req),
    health: pythonHealthCheck('autonomous_scale_recommendations'),
  },
  {
    // Global Revenue Operating System, Section 24/35 (ADR-211, Phase
    // 21, 2026-08-08).
    name: 'revenue-operating-system-dashboard',
    description: "Financial Source of Truth, Revenue Classification (17 named types), Gross vs Net ($0/$0 today, never conflated with profit), Currency (honestly single-USD, NOT_BUILT for multi-currency), Ledger Conformance, Idempotency (real: finance-layer dedup is real via source_ledger_key, raw-ledger-append dedup is honestly NOT_IDEMPOTENT), Reconciliation (relabeled onto the 8 named states, never a 2nd reconciliation engine), Payment-vs-Revenue, Subscriptions/Commissions/B2B/Receivables/Payouts (all honestly $0/NOT_BUILT), Leakage, Data Quality, and an explainable 10-component Revenue Health view with no fabricated composite score.",
    reused: 'revenue_operating_system.py::build_revenue_operating_system_dashboard(), via mission_control_api.py. Measured live ~4s.',
    handler: (req) => runPythonServiceCached('revenue_operating_system_dashboard', [], req),
    health: pythonHealthCheck('revenue_operating_system_dashboard'),
  },
  {
    name: 'revenue-leakage-report',
    description: "Real, mechanical leakage checks: unpublished-but-sellable products, order/revenue mismatches (via commercial_reconciliation.py), duplicate raw ledger entries, broken attribution -- plus 4 honestly disclosed NOT_ARCHITECTED categories (unclaimed commission, fee auditing, subscription renewal failures, currency anomalies), never a fabricated 'no leakage found.'",
    reused: 'revenue_operating_system.py::revenue_leakage_report(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('revenue_leakage_report', [], req),
    health: pythonHealthCheck('revenue_leakage_report'),
  },
  {
    // Customer Intelligence & Retention Engine, Section 4/38 (ADR-212,
    // Phase 22, 2026-08-08).
    name: 'customer-intelligence-dashboard',
    description: "Data Minimization, Purchase/Non-Purchase Reason taxonomy, Customer Problem Mining, Feedback, Sentiment Safety (honestly NOT_BUILT), Customer Trust, Refunds, Churn (NOT_APPLICABLE -- 0 real subscriptions), Retention (real action taxonomy, no dark patterns), Customer Value/LTV, Segmentation, Support, Cohorts, Privacy, Incident Protection, Revenue link, and the 10 named Executive Customer Questions each tagged FACT/INFERENCE/ESTIMATE/UNKNOWN. 19 real sub-reports, honestly empty across the board at 0 real customers.",
    reused: 'customer_intelligence.py::build_customer_intelligence_dashboard(), via mission_control_api.py. Measured live ~4s.',
    handler: (req) => runPythonServiceCached('customer_intelligence_dashboard', [], req),
    health: pythonHealthCheck('customer_intelligence_dashboard'),
  },
  {
    name: 'customer-trust-score',
    description: "9 named trust components (Product Accuracy, Delivery Reliability, Support Quality, Refund Experience, Pricing Transparency, Communication Quality, Privacy, Complaint Rate, Satisfaction) -- each a real citation of trust_audit.py (ADR-189) or an honest gap. No single fabricated composite Trust score.",
    reused: 'customer_intelligence.py::customer_trust_score(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('customer_trust_score', [], req),
    health: pythonHealthCheck('customer_trust_score'),
  },
  {
    // Autonomous Product Innovation Engine, Section 32/38 (ADR-213,
    // Phase 23, 2026-08-08).
    name: 'product-innovation-dashboard',
    description: "Problem Registry, Product Portfolio (8 named buckets), Cannibalization check, Customer/Revenue innovation signals, Product Experiments, Innovation Efficiency, and Autonomous Innovation Boundaries -- relabels profit_oracle.py's real 9 hard gates onto Section 15's 6 named validation gates, galaxy_council.py's real 9-member council for AI Council challenge, and a new structured Red Team checklist that cites real signals rather than a fabricatable AI critique. Golden Hunter remains the primary opportunity-hunting intelligence throughout, never replaced.",
    reused: 'product_innovation_engine.py::build_product_innovation_dashboard(), via mission_control_api.py. Measured live ~3.5s.',
    handler: (req) => runPythonServiceCached('product_innovation_dashboard', [], req),
    health: pythonHealthCheck('product_innovation_dashboard'),
  },
  {
    name: 'product-innovation-efficiency',
    description: "Real counts from decision_engine.store: ideas generated, problems validated, killed products, deferred-for-more-evidence -- honestly UNKNOWN for concepts tested/MVPs built/paid pilots/average validation cost/time-to-validation (no real tracking exists for any of these yet). Never optimized for idea count alone.",
    reused: 'product_innovation_engine.py::innovation_efficiency_report(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('product_innovation_efficiency', [], req),
    health: pythonHealthCheck('product_innovation_efficiency'),
  },
  {
    // Enterprise & Transformation Division, Section 37/41 (ADR-214,
    // Phase 24, 2026-08-08).
    name: 'enterprise-transformation-dashboard',
    description: "Enterprise Problem Registry, 16-stage Discovery Pipeline, Vertical Solution status, Knowledge System/Security/Multi-Tenancy/Integrations (all honestly NOT_BUILT -- 0 real enterprise infrastructure exists), Revenue Model (10 named types, $0), Product-to-Enterprise Conversion, Reusability Inventory, Success Metrics, Expansion, and Autonomous Enterprise Boundaries (2 new real contract/legal-commitment authorization categories, both Level 5/6).",
    reused: 'enterprise_transformation_engine.py::build_enterprise_transformation_dashboard(), via mission_control_api.py. Measured live ~2.9s.',
    handler: (req) => runPythonServiceCached('enterprise_transformation_dashboard', [], req),
    health: pythonHealthCheck('enterprise_transformation_dashboard'),
  },
  {
    name: 'enterprise-reusability-inventory',
    description: "Real, mechanical inventory over dependency_graph.py's AST-based import analysis -- a component counts as reusable only when 2+ real modules already import it (238 real components found live). Never asserted as reusable from intent alone.",
    reused: 'enterprise_transformation_engine.py::reusability_inventory(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('enterprise_reusability_inventory', [], req),
    health: pythonHealthCheck('enterprise_reusability_inventory'),
  },
  {
    // Global Partnership & Distribution Network, Section 37/42
    // (ADR-215, Phase 25, 2026-08-08).
    name: 'partnership-network-dashboard',
    description: "Relabels business_development.py's real 21-platform registry (ADR-188, WebSearch-verified, never a partner's own self-reported claim) onto the directive's shape: real 11-stage Lifecycle mapping, Affiliate/Referral/Reseller/Distributor engines (referral/reseller/distributor honestly NOT_BUILT), Partner Attribution, Conflict Check, a real SUSPICION->INVESTIGATION->EVIDENCE->DECISION Fraud state machine (never auto-accuses), Security (honestly NOT_BUILT), and Distribution Network Health.",
    reused: 'global_partnership_network.py::build_partnership_network_dashboard(), via mission_control_api.py. Measured live ~0.5s.',
    handler: (req) => runPythonServiceCached('partnership_network_dashboard', [], req),
    health: pythonHealthCheck('partnership_network_dashboard'),
  },
  {
    name: 'distribution-network-health',
    description: "10 named health components (Revenue Diversity, Partner Quality, Reliability, Customer Quality, Channel Stability, Concentration, Recurring Revenue, Security, Compliance, Confidence) -- each a real citation or an honest gap. No fabricated composite score. Real finding: 1 real ACTIVE relationship (Paddle, a payment processor, not a distribution partner), confidence LOW.",
    reused: 'global_partnership_network.py::distribution_network_health(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('distribution_network_health', [], req),
    health: pythonHealthCheck('distribution_network_health'),
  },
  {
    // Global Commercial Operations Engine, Section 38/47 (ADR-216,
    // Phase 26, 2026-08-08).
    name: 'commercial-operations-dashboard',
    description: "Platform Registry (real 21-platform business_development.py registry), Product<->Platform Matrix, Currency (honest single-USD), Commission/Order/Refund Normalization, Payout Reconciliation, Platform Account Health, Payment Infrastructure, Commercial Task Queue, Alerts, Anomaly Detection, Fraud Protection (real SUSPICION->INVESTIGATION->EVIDENCE->DECISION), Channel Profitability, Concentration Risk, and a real Governance Level 0-4 relabeling of autonomous_operations.py's Level 0-6 taxonomy.",
    reused: 'global_commercial_operations_engine.py::build_commercial_operations_dashboard(), via mission_control_api.py. Measured live ~7s.',
    handler: (req) => runPythonServiceCached('commercial_operations_dashboard', [], req),
    health: pythonHealthCheck('commercial_operations_dashboard'),
  },
  {
    name: 'commercial-operations-simulations',
    description: "8 named commercial simulations (Sections A-H) -- 7 clearly labeled HYPOTHETICAL (multi-platform net contribution, partner profitability with refunds, high-revenue-poor-margin, payout discrepancy, payment-provider outage, platform suspension, new-marketplace evaluation), never a real transaction, never written to any ledger (verified by a regression test); Simulation G reuses real, live concentration-risk data.",
    reused: 'global_commercial_operations_engine.py::run_all_commercial_simulations(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('commercial_operations_simulations', [], req),
    health: pythonHealthCheck('commercial_operations_simulations'),
  },
  {
    // Commercial Autonomy & Revenue Optimization Engine, Section 34/41
    // (ADR-217, Phase 27, 2026-08-08).
    name: 'commercial-autonomy-dashboard',
    description: "Commercial Forecast, Scenario Engine (real BASE/UPSIDE/DOWNSIDE/STRESS cases off a real revenue baseline, all HYPOTHETICAL PROJECTION-labeled), Risk Engine, Revenue Leakage Tasks, Margin Protection, Anomaly Response, Autonomous Recommendations (real, evidence-cited, never fabricated), Resource Allocation, Commercial Queue (real NOW/NEXT/HUMAN_REVIEW/BLOCKED states derived from real authorization levels), Prediction vs Reality, Experiment Learning, Execution/Rollback status (0 real automated executions, 0 real rollbacks), and an 11-component Commercial Health Score with no fabricated composite.",
    reused: 'commercial_autonomy_engine.py::build_commercial_autonomy_dashboard(), via mission_control_api.py. Measured live ~18-19s.',
    handler: (req) => runPythonServiceCached('commercial_autonomy_dashboard', [], req, 60000),
    health: pythonHealthCheck('commercial_autonomy_dashboard'),
  },
  {
    name: 'commercial-autonomy-simulations',
    description: "10 named commercial simulations (Sections 1-10) -- real arithmetic over disclosed hypothetical assumptions (margin/fee/refund-rate scenarios), Simulation 5/7/9/10 reuse real, live concentration/AI-Council/payout/partner data. Verified by a regression test that none ever writes to a real ledger.",
    reused: 'commercial_autonomy_engine.py::run_all_phase27_simulations(), via mission_control_api.py. Measured live ~19s.',
    handler: (req) => runPythonServiceCached('commercial_autonomy_simulations', [], req, 60000),
    health: pythonHealthCheck('commercial_autonomy_simulations'),
  },
  {
    // Global Growth & Customer Acquisition Engine, Section 41/46
    // (ADR-218, Phase 28, 2026-08-08).
    name: 'growth-dashboard',
    description: "Lead Registry (reuses customer_pipeline.py's real intake requests as this factory's real lead registry), Acquisition (real 9-channel report), CAC/LTV/LTV-CAC (honestly UNKNOWN -- 0 real ad spend), Organic Growth, Customer Success/Churn/Retention/Expansion/Referral (reused from Phase 22/25), Growth Forecast/Scenarios (reuses Phase 27's real BASE/UPSIDE/DOWNSIDE/STRESS scenario_engine() verbatim)/Risk, and real Autonomy Boundaries.",
    reused: 'global_growth_engine.py::build_growth_dashboard(), via mission_control_api.py. Measured live ~10s.',
    handler: (req) => runPythonServiceCached('growth_dashboard', [], req),
    health: pythonHealthCheck('growth_dashboard'),
  },
  {
    name: 'growth-simulations',
    description: "10 named growth simulations (Sections 1-10) -- real arithmetic over disclosed hypothetical assumptions (traffic/conversion/CAC/retention/segment-value scenarios). Simulation 10 reuses the real AI Council + Red Team. Verified by a regression test that none ever writes to a real ledger.",
    reused: 'global_growth_engine.py::run_all_phase28_simulations(), via mission_control_api.py. Measured live ~18-19s.',
    handler: (req) => runPythonServiceCached('growth_simulations', [], req, 60000),
    health: pythonHealthCheck('growth_simulations'),
  },
  {
    // Customer Success, Retention & Recurring Revenue Engine, Section
    // 41/48 (ADR-219, Phase 29, 2026-08-08).
    name: 'customer-success-dashboard',
    description: "Customer Outcome, Onboarding, Churn, Retention, Support, Root Cause (real clustering over customer_pipeline.py's real problem-cost signal), Refunds, Feedback, Recurring Revenue (real 6-question gate -- SUBSCRIPTION_JUSTIFIED requires at least 1 real yes, never defaults to yes), Renewal, Expansion, LTV, Segment Profitability, Queue, Automation Boundaries (7 named human-required categories, 9 safe-to-automate), Community, Enterprise Success, Forecast, Experiments, Trust, Autonomy (6th relabeling this session of autonomous_operations.py's Level 0-6 taxonomy).",
    reused: 'customer_success_engine.py::build_customer_success_dashboard(), via mission_control_api.py. Measured live ~13s.',
    handler: (req) => runPythonServiceCached('customer_success_dashboard', [], req),
    health: pythonHealthCheck('customer_success_dashboard'),
  },
  {
    name: 'customer-success-simulations',
    description: "10 named customer simulations (Sections 1-10) -- real logic over disclosed hypothetical assumptions (activation/churn/refund-spike/expansion/subscription-redesign/feature-request scenarios). Simulation 10 reuses the real AI Council + Red Team. Verified by a regression test that none ever writes to a real ledger.",
    reused: 'customer_success_engine.py::run_all_phase29_simulations(), via mission_control_api.py. Measured live ~18s.',
    handler: (req) => runPythonServiceCached('customer_success_simulations', [], req, 60000),
    health: pythonHealthCheck('customer_success_simulations'),
  },
  {
    // Enterprise & High-Value Transformation Sales Engine, Sections
    // 2-3/9-31/36-38 (ADR-220, Phase 30, 2026-08-08).
    name: 'enterprise-sales-dashboard',
    description: "Opportunity Registry, Sales Pipeline (real 13-stage relabeling of business_development.py's real 9-stage pipeline -- a 3rd relabeling this session), Pipeline Priority, Account Registry (0 real accounts, honestly disclosed), Stakeholder Map (never fabricates identity/authority), Contract Value, Recurring Revenue (reuses customer_success_engine.py's real 6-question gate), Expansion, Partnership, Objections, Security & Trust, AI Governance, Delivery Handoff, Contract Risk (11 named categories, never auto-clears without a real contract), Forecast, Autonomy Boundaries.",
    reused: 'enterprise_sales_engine.py::build_enterprise_sales_dashboard(), via mission_control_api.py. Measured live ~0.1s.',
    handler: (req) => runPythonServiceCached('enterprise_sales_dashboard', [], req),
    health: pythonHealthCheck('enterprise_sales_dashboard'),
  },
  {
    name: 'enterprise-sales-simulations',
    description: "10 named enterprise sales simulations (Section 45) -- real logic over disclosed hypothetical assumptions (value-based pricing/budget-shortfall/pilot-expansion/margin/contract-risk/competitor/evidence-gate scenarios). Simulation 8 is real (not hypothetical) -- reuses global_opportunity_exchange.py's concentration risk directly. Simulation 10 reuses the real AI Council + Red Team (6th reuse this session). Verified by a regression test that none ever writes to a real ledger.",
    reused: 'enterprise_sales_engine.py::run_all_phase30_simulations(), via mission_control_api.py. Measured live ~15s.',
    handler: (req) => runPythonServiceCached('enterprise_sales_simulations', [], req, 60000),
    health: pythonHealthCheck('enterprise_sales_simulations'),
  },
  {
    // Account Routing & Payment Identity Policy (ADR-241, 2026-08-09).
    name: 'account-routing-status',
    description: "Read-only platform -> commercial_identity -> payout_identity -> status table. Amazon/KDP routes to aekgalaxy47@gmail.com with a real, founder-confirmed Payoneer payout identity (the only fully VERIFIED category); every other real commercial/affiliate platform (Gumroad, Paddle, Etsy, n8n, NordVPN, etc.) routes to the primary commercial identity galaxyaek7@gmail.com with an honestly UNKNOWN payout method, never assumed to be Payoneer. An unlisted platform is BLOCKED, never guessed -- no substring/fuzzy inference exists anywhere in account_routing.py. Holds only non-secret routing metadata (email addresses already disclosed by the founder); no password, API key, token, or other credential is stored or exposed here.",
    reused: 'account_routing.py::account_routing_table(), via mission_control_api.py. Pure in-memory lookup, no live scan.',
    handler: (req) => runPythonServiceCached('account_routing_status', [], req),
    health: pythonHealthCheck('account_routing_status'),
  },
  {
    // Executive Truth Dashboard (ADR-221, Phase 30.5 forensic audit, 2026-08-08).
    name: 'executive-truth-dashboard',
    description: "Real, live-checked commercial reality: real vs. simulated revenue (excludes the disclosed finance_data.json smoke-test record), real customers (0, file-existence checked), connected vs. blocked platforms (live channels/*_arm.py status() calls), automations verified fresh today (real daily-marker timestamp check), automations partial (the Golden Hunter ranked-feed refresh gap), manual tasks, critical risks (real resilience_monitor.py findings), unknown states. Never a frozen snapshot -- every field recomputed on each call.",
    reused: 'institutional_truth_dashboard.py::build_executive_truth_dashboard(), via mission_control_api.py. Measured live ~0.6s.',
    handler: (req) => runPythonServiceCached('executive_truth_dashboard', [], req),
    health: pythonHealthCheck('executive_truth_dashboard'),
  },
  {
    // Commercial Activation & First Real Dollar (ADR-223, Phase 31, 2026-08-08).
    name: 'commercial-activation-status',
    description: "Per-platform 8-dimension readiness (TECHNICAL/COMMERCIAL/CHECKOUT/PAYMENT/DELIVERY/FINANCE/WEBHOOK/PAYOUT_READY, never collapsed into one score) for Paddle/Gumroad/Etsy/Payhip, including a live re-check of real Paddle checkout status. Founder Action Center (real human actions only -- account onboarding, webhook secret, credentials, payout destination). Golden Hunter freshness (real, live-checked -- honestly reports STALE, never silently fresh). Refunds/disputes/chargebacks (NOT_AVAILABLE, never confused with a verified $0).",
    reused: 'commercial_activation.py::build_commercial_activation_status() + scripts/check_paddle_checkout_status.py, via mission_control_api.py. Measured live ~4s.',
    handler: (req) => runPythonServiceCached('commercial_activation_status', [], req, 30000),
    health: pythonHealthCheck('commercial_activation_status'),
  },
  {
    // Commission Commerce Engine (ADR-226, Phase 33, 2026-08-08).
    name: 'commission-commerce-dashboard',
    description: "Real, evidence-cited commission opportunity portfolio (13 real records derived from business_development.py's existing WebSearch-verified registry, ADR-188 -- no new research performed this round), verified/partially-verified/unverified counts, real commission ledger summary (REAL/TEST/SIMULATION kept strictly separate -- only CONFIRMED/PAID REAL records count), stale-opportunity detection, honest INCOMPLETE/UNKNOWN markers everywhere real customer or economic data doesn't exist yet, and the 3 Commission Commerce agents' real health (commercial_deal_agent/partner_intelligence_agent/lead_outreach_agent -- status/last_run/error_rate/queue_size/blocked_reason, computed from real event data, ADR-227).",
    reused: 'commission_engine.py::build_commission_commerce_dashboard() + commission_ledger.py::real_commission_summary() + 3 agents\' agent_health(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('commission_commerce_dashboard', [], req),
    health: pythonHealthCheck('commission_commerce_dashboard'),
  },
  {
    name: 'commission-daily-brief',
    description: "Golden Hunter Daily Commercial Brief (Section 13) -- the 10 named questions, every answer citing real portfolio/pipeline data. Never claims a sale unless independently verified in commission_ledger.py's REAL environment.",
    reused: 'commission_engine.py::build_daily_commercial_brief(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('commission_daily_brief', [], req),
    health: pythonHealthCheck('commission_daily_brief'),
  },
  {
    // Lead Discovery (Phase 37A, ADR-230, 2026-08-08).
    name: 'lead-discovery-status',
    description: "Real, read-only summary of already-discovered leads (via lead_discovery.py's legitimate, keyless HN Algolia + GitHub Search queries -- no scraping, no purchased data). Qualified/rejected/blocked counts, top real candidate, agent health. Real vs. simulation-only leads shown separately -- simulation activity is never displayed as real commercial activity. Does NOT trigger a new live discovery pass on every poll.",
    reused: 'lead_discovery.py::load_leads()/agent_health(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('lead_discovery_status', [], req),
    health: pythonHealthCheck('lead_discovery_status'),
  },
  {
    // Outreach Adapter Infrastructure (Phase 37A, ADR-230, 2026-08-08).
    name: 'outreach-infrastructure-status',
    description: "Real, read-only outreach adapter status -- extends outreach_engine.py's capability inventory with outreach_adapter.py's concrete SMTPOutreachAdapter state: credential presence (values never exposed), MAX_REAL_SENDS usage, channel documentation. Never claims LIVE/real-send-capability without a real, present credential -- CREDENTIAL_STATUS=MISSING today.",
    reused: 'outreach_adapter.py::adapter_status(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('outreach_infrastructure_status', [], req),
    health: pythonHealthCheck('outreach_infrastructure_status'),
  },
  {
    // Golden Hunter Opportunity Rotation Engine (Phase 38, ADR-233, 2026-08-08).
    name: 'golden-hunter-rotation-status',
    description: "Real, read-only opportunity-lifecycle summary -- every real opportunity's PURSUE/WATCH/ABANDON/ROTATE state (opportunity_rotation_engine.py's own real, append-only lifecycle ledger), plus the top-2 opportunity comparison from the most recent committed live validation run, with a real 'why this beats that' citation. A WATCH/PURSUE opportunity is never displayed as a customer, deal, or revenue.",
    reused: 'opportunity_rotation_engine.py::all_known_opportunity_ids()/opportunity_memory() + the committed data/phase38_rotation_validation_result.json, via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('golden_hunter_rotation_status', [], req),
    health: pythonHealthCheck('golden_hunter_rotation_status'),
  },
  {
    // Ranked Commission Opportunity Shortlist (Phase 38b, "Chief Commercial Engineer" directive, ADR-234, 2026-08-08).
    name: 'commission-opportunity-shortlist',
    description: "Real, ranked top-5 shortlist over the 13-opportunity commission portfolio -- 9 named scores per opportunity (opportunity/evidence/commercial/commission/freshness/competition/execution-difficulty/expected-value/risk), citing score_commission_opportunity()'s existing 13-dim function directly. BEST_FIRST_COMMERCIAL_EXPERIMENT excludes known evidence conflicts and any opportunity currently WATCH/ABANDON in the real Golden Hunter Rotation lifecycle ledger.",
    reused: 'commission_engine.py::rank_commission_shortlist(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('commission_opportunity_scan', [], req),
    health: pythonHealthCheck('commission_opportunity_scan'),
  },
  {
    // FIRST_REAL_DOLLAR Gate (Phase 38b, "Chief Commercial Engineer" directive, ADR-234, 2026-08-08).
    name: 'first-real-dollar-status',
    description: "The one formal, named commercial-truth gate -- FIRST_REAL_DOLLAR is False until an independently verifiable real commission/payout exists in commission_ledger.py's own REAL/CONFIRMED-or-PAID records. Every REAL_REVENUE/REAL_COMMISSION_REVENUE/REAL_CUSTOMERS/REAL_DEALS/REAL_PAYOUTS field is 0 with no exceptions until then -- no partial credit, no averaging toward true.",
    reused: 'commission_ledger.py::first_real_dollar_status(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('first_real_dollar_status', [], req),
    health: pythonHealthCheck('first_real_dollar_status'),
  },
  {
    // Commercial Flight-Control Gate (Phase 39, "Commercial Flight Control & First-Real-Dollar Execution" directive, ADR-236, 2026-08-08).
    name: 'commercial-flight-control-status',
    description: "The one authoritative gate for the first controlled commercial action -- returns exactly one of LAUNCH_READY/FIRST_CONTROLLED_ACTION_READY/CEO_APPROVAL_REQUIRED/BLOCKED, derived from live system state (real portfolio, real ledger, real adapter/credential status, real opportunity lifecycle state), never a generic boolean. Discloses the real, unresolved disagreement between this factory's two selection functions (rank_commission_shortlist() picks Amazon, select_first_launch_opportunity() picks Adobe) rather than forcing agreement, and checks each opportunity against its own real commercial mechanism (outreach-based referral vs. self-service affiliate-link publication) rather than silently coercing one onto the other.",
    reused: 'commission_engine.py::commercial_flight_control_status(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('commercial_flight_control_status', [], req),
    health: pythonHealthCheck('commercial_flight_control_status'),
  },
  {
    name: 'commercial-control-panel',
    description: "The Section 10 concise commercial control view -- CURRENT_OPPORTUNITY, EVIDENCE_STATUS, FRESHNESS, COMMISSION_ECONOMICS, CEO_APPROVAL_STATUS, ACTION_READINESS, REAL_COMMISSION_USD, PENDING_COMMISSION, PAYOUT_STATUS, FIRST_REAL_DOLLAR_STATUS, BLOCKERS, LAST_VERIFIED_TIMESTAMP. Pure read-only citation of the Flight-Control Gate + the real commission ledger, no independently computed field.",
    reused: 'commission_engine.py::commercial_control_panel(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('commercial_control_panel', [], req),
    health: pythonHealthCheck('commercial_control_panel'),
  },
  {
    name: 'golden-hunter-commission-verification',
    description: "Section 11 audit: real, evidence-cited verification of rank_commission_shortlist() (this factory's real commission-side Golden Hunter) against 7 named properties -- discovers real opportunities, never fabricates an opportunity, never manufactures evidence, respects freshness, respects verification status, ranks by expected value and confidence, exposes uncertainty (expected_value stays honestly UNKNOWN), never bypasses a CEO gate (structurally proven: no write/send function is ever called).",
    reused: 'commission_engine.py::golden_hunter_commission_verification(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('golden_hunter_commission_verification', [], req),
    health: pythonHealthCheck('golden_hunter_commission_verification'),
  },
  {
    // First Real Commission Execution Gate (Phase 40, ADR-237, 2026-08-09).
    name: 'live-program-eligibility',
    description: "Step 2: the 10 named eligibility fields (program/company, official source URL, current eligibility requirements, geographic restrictions, payout/commission structure, attribution/cookie rules, application/approval requirement, VERIFIED/PROVISIONAL/REJECTED status, evidence timestamp, evidence source, freshness) for the real, top-ranked commission opportunity. Third-party-only evidence is never classified as officially VERIFIED -- a REJECTED program's payout structure is explicitly withheld, never leaked as if officially confirmed.",
    reused: 'commission_engine.py::live_program_eligibility(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('live_program_eligibility', [], req),
    health: pythonHealthCheck('live_program_eligibility'),
  },
  {
    name: 'founder-action-state',
    description: "Step 3: READY_FOR_FOUNDER_ACTION/CREDENTIALS_REQUIRED/APPROVAL_REQUIRED/READY_FOR_CONTROLLED_TEST/BLOCKED -- a pure relabeling of commercial-flight-control-status's own real checks, distinguishing 'founder must create a real external account' from 'founder must configure a credential' from 'founder must issue a real approval'. Never invents credentials, fabricates approval, or bypasses an external platform's onboarding.",
    reused: 'commission_engine.py::founder_action_state(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('founder_action_state', [], req),
    health: pythonHealthCheck('founder_action_state'),
  },
  {
    name: 'trackable-commission-object',
    description: "Step 4: the 14 named canonical commission-opportunity fields (opportunity_id/program_id/partner_id/source_url/official_evidence/commission_terms/tracking_method/affiliate_link_status/approval_status/freshness_status/risk_status/CEO_approval_status/created_at/updated_at) for the real, top-ranked opportunity. A pure, computed-on-demand read-only view -- no new persisted store created.",
    reused: 'commission_engine.py::trackable_commission_object(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('trackable_commission_object', [], req),
    health: pythonHealthCheck('trackable_commission_object'),
  },
  {
    name: 'reality-firewall-status',
    description: "Step 5: the 9 named reality-firewall requirements (verified real program/opportunity/tracking path, explicit founder approval, correct scope, no fabricated evidence, no duplicate commission, no synthetic event counted as real, no test event in real state), each citing an already-real, already-tested mechanism. Zero new protection logic.",
    reused: 'commission_engine.py::reality_firewall_status(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('reality_firewall_status', [], req),
    health: pythonHealthCheck('reality_firewall_status'),
  },
  {
    name: 'first-controlled-action-gate',
    description: "Step 6: EXECUTION_AUTHORIZED requires CEO_APPROVAL=true AND FIRST_CONTROLLED_ACTION_READY=true AND REALITY_FIREWALL_PASSED=true -- all three independently checked, defense in depth. This function never executes a real send/publish/ledger-write itself; the Mission Control view always calls it with ceo_approval=false, since founder approval must be a real, separate, deliberate act, never a side effect of viewing a dashboard.",
    reused: 'commission_engine.py::first_controlled_action_gate(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('first_controlled_action_gate', [], req),
    health: pythonHealthCheck('first_controlled_action_gate'),
  },
  {
    name: 'real-vs-test-commission-metrics',
    description: "Step 7: REAL_REVENUE/REAL_COMMISSION_REVENUE vs TEST_REVENUE/TEST_COMMISSION vs SIMULATION_COMMISSION, cross-checked (isolation_verified) against real_commission_summary()'s own independently-computed total. TEST/SIMULATION dollar amounts can never contaminate REAL_REVENUE -- structurally guaranteed by commission_ledger.py's environment field, not merely asserted.",
    reused: 'commission_engine.py::real_vs_test_commission_metrics(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('real_vs_test_commission_metrics', [], req),
    health: pythonHealthCheck('real_vs_test_commission_metrics'),
  },
  {
    // OpenClaw Directive — Commission Commerce Launch (Phase 41, ADR-238, 2026-08-09).
    name: 'opportunity-economics',
    description: "The real, top-ranked commission opportunity's full economic scorecard -- 12 named factors (extending score_commission_opportunity()'s real 13 dimensions with sales-cycle length/probability-of-conversion/prospect-availability), plus EXPECTED_COMMISSION_VALUE/EXPECTED_VALUE_PER_PROSPECT (honestly UNKNOWN without real conversion-rate/deal-value inputs). Never ranks by advertised commission alone.",
    reused: 'commission_engine.py::opportunity_economics_panel(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('opportunity_economics_panel', [], req),
    health: pythonHealthCheck('opportunity_economics_panel'),
  },
  {
    name: 'qualified-prospect-queue',
    description: "Real, read-only citation of lead_discovery.py's own already-persisted qualified leads -- company identity, public source, evidence, freshness, confidence per lead. Never triggers a new live discovery pass on view; no email/credential harvesting anywhere in the underlying discovery.",
    reused: 'commission_engine.py::qualified_prospect_queue(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('qualified_prospect_queue', [], req),
    health: pythonHealthCheck('qualified_prospect_queue'),
  },
  {
    name: 'referral-deal-pipeline',
    description: "Real citation of commercial_deal_agent.track_deal_state() per real opportunity -- every real recorded pipeline transition, no fabricated stage. Opportunities with zero real pipeline activity are listed separately and honestly, never silently omitted.",
    reused: 'commission_engine.py::referral_deal_pipeline(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('referral_deal_pipeline', [], req),
    health: pythonHealthCheck('referral_deal_pipeline'),
  },
  {
    name: 'first-dollar-mode-status',
    description: "ARMED_WAITING_FOR_FIRST_VERIFIED_COMMISSION until a real commission exists -- every post-first-dollar metric (acquisition_path/conversion_economics/time_to_deal/commission_margin/repeatable) explicitly NOT_YET_TRIGGERED, never estimated in advance. After a real commission exists, computes all 5 from the real, preserved ledger record.",
    reused: 'commission_engine.py::first_dollar_mode_status(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('first_dollar_mode_status', [], req),
    health: pythonHealthCheck('first_dollar_mode_status'),
  },
  {
    name: 'thousand-dollar-month-status',
    description: "TARGET=$1,000 REAL COMMISSION for the first commercial month (a target, never a guaranteed outcome). Realized revenue (REAL_REVENUE/REAL_COMMISSION/REAL_CUSTOMERS/REAL_DEALS/REAL_PAYOUTS) and pipeline value (VERIFIED_OPPORTUNITIES/QUALIFIED_PROSPECTS/ACTIVE_REFERRALS/OPEN_DEALS/EXPECTED_COMMISSION) are structurally separate sections, never summed or blended.",
    reused: 'commission_engine.py::thousand_dollar_month_status(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('thousand_dollar_month_status', [], req),
    health: pythonHealthCheck('thousand_dollar_month_status'),
  },
  {
    name: 'commercial-blockers',
    description: "Aggregates every real blocker already surfaced by commercial-flight-control-status, founder-action-state, and verify_commission_opportunity() for the real top-ranked opportunity, plus the standing, factory-wide geography/jurisdiction gap (this factory's own real operating jurisdiction has never been confirmed anywhere in code). Never an independently-computed blocker list.",
    reused: 'commission_engine.py::commercial_blockers_panel(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('commercial_blockers_panel', [], req),
    health: pythonHealthCheck('commercial_blockers_panel'),
  },
  {
    name: 'opportunity-experiments-report',
    description: "The directive's 4 named experiment categories (B2B SaaS recurring affiliate, high-ticket B2B referral, AI automation/service referral, one evidence-supported other) over the real 13-opportunity portfolio -- a disclosed, manually-curated categorization, not derived from any existing field. Every per-experiment metric is honestly zero/N-A today, since zero real outreach has occurred in any category.",
    reused: 'commission_engine.py::opportunity_experiments_report(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('opportunity_experiments_report', [], req),
    health: pythonHealthCheck('opportunity_experiments_report'),
  },
  {
    // OpenClaw Revenue Activation Directive (ADR-239, 2026-08-09).
    name: 'revenue-activation-dashboard',
    description: "One consolidated read-only commercial view over the directive's 14 named items: top affiliate opportunities, best current offer, real clicks/conversions, pending/paid commission, revenue MTD + target progress, conversion rate, commission/customer, program status, founder actions required, commercial blockers, evidence freshness. Zero new computation -- aggregates 8 already-real functions rather than proliferating a dozen thin panels.",
    reused: 'commission_engine.py::revenue_activation_dashboard(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('revenue_activation_dashboard', [], req),
    health: pythonHealthCheck('revenue_activation_dashboard'),
  },
  {
    // CTO+COO audit closure (2026-08-15): expose the previously dead-code
    // commercial orchestration layer through Mission Control.
    name: 'commercial-ops',
    description: "Unified commercial operations view: revenue-arm audit (READY/PARTIAL/BLOCKED), VERIFIED/PENDING revenue, blockers, consolidated founder queue, TOP revenue path, Paddle activation queue. Exposes autonomous_commerce_ops.mission_control() which was previously imported only by tests.",
    reused: 'autonomous_commerce_ops.py::mission_control(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('commercial_mission_control', [], req),
    health: pythonHealthCheck('commercial_mission_control'),
  },
  {
    name: 'commercial-founder-queue',
    description: "ONE consolidated founder queue with explicit horizons: TODAY (Gumroad payment), NEXT (Paddle onboarding), LATER (Etsy authorization), TOMORROW (Awin + DigitalOcean + Payoneer). The founder never has to search the codebase to discover what must be done.",
    reused: 'autonomous_commerce_ops.py::founder_gate_consolidation(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('commercial_founder_queue', [], req),
    health: pythonHealthCheck('commercial_founder_queue'),
  },
  {
    name: 'commercial-revenue-router',
    description: "Dynamic revenue-arm router: score = REVENUE POTENTIAL x SPEED x CONFIDENCE x AUTOMATION x PROFIT x RECURRING, ranked TOP TODAY / SECOND / THIRD / DEFERRED. Recomputed every call; no arm is permanently preferred.",
    reused: 'autonomous_commerce_ops.py::revenue_router(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('commercial_revenue_router', [], req),
    health: pythonHealthCheck('commercial_revenue_router'),
  },
  {
    name: 'operational-readiness',
    description: "Honest GALAXY_FORGE_OPERATIONAL_READINESS % + per-dimension scores (TECHNICAL/COMMERCIAL/AUTOMATION/REVENUE/SECURITY/RECOVERY), computed from real code/config signals. Never inflated.",
    reused: 'commercial_operations.py::operational_readiness(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('operational_readiness', [], req),
    health: pythonHealthCheck('operational_readiness'),
  },
  {
    name: 'commercial-gap-register',
    description: "Live COMMERCIAL_GAP_REGISTER: every gap with gap_id/category/severity/business_impact/current_state/target_state/automation_possible/human_gate/recommended_fix/status. Only gaps verified against actual code/config.",
    reused: 'commercial_operations.py::commercial_gap_register(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('commercial_gap_register', [], req),
    health: pythonHealthCheck('commercial_gap_register'),
  },
  {
    name: 'revenue-event-model',
    description: "Canonical revenue event model (CLICK/LEAD/ORDER/PAYMENT/COMMISSION/...) -- a READ-ONLY projection over the real ledgers. Only REAL VERIFIED events feed VERIFIED_REVENUE; TEST/MOCK/PROJECTED/UNKNOWN are reported separately and never summed.",
    reused: 'commercial_operations.py::revenue_event_model(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('revenue_event_model', [], req),
    health: pythonHealthCheck('revenue_event_model'),
  },
  {
    name: 'profit-engine',
    description: "Profit separation (revenue is not profit): gross_revenue/platform_fees/refunds/net_revenue/profit, with cash_received/pending/projected kept separate. Zero-discretionary-spend mode: no unapproved cost is ever introduced.",
    reused: 'commercial_operations.py::profit_engine(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('profit_engine', [], req),
    health: pythonHealthCheck('profit_engine'),
  },
  {
    name: 'distribution-capability-matrix',
    description: "Per-channel capability truth for Pinterest/TikTok/YouTube/X/Facebook/LinkedIn/SEO: CONTENT_AUTOMATED vs PUBLISHING_AUTOMATED vs ANALYTICS_AUTOMATED. Never claims automated merely because content can be generated.",
    reused: 'commercial_operations.py::distribution_capability_matrix(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('distribution_capability_matrix', [], req),
    health: pythonHealthCheck('distribution_capability_matrix'),
  },
  {
    name: 'commercial-link-monitor',
    description: "Safe link & destination monitor for known commercial links (dry-run registry check by default; live checks bounded and rate-limited). Never hammers external services.",
    reused: 'commercial_operations.py::link_monitor(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('commercial_link_monitor', [], req),
    health: pythonHealthCheck('commercial_link_monitor'),
  },
  {
    name: 'commercial-treasury',
    description: "Unified treasury with the real ledger values: cash / verified revenue / pending / cost / profit. Fixed the prior bug where verified was hardcoded to 0.0.",
    reused: 'revenue_os.py::treasury_status(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('commercial_treasury', [], req),
    health: pythonHealthCheck('commercial_treasury'),
  },
  {
    name: 'affiliate-chain-readiness',
    description: "Affiliate chain readiness: portfolio count/verified, launch prep state, tracking IDs, click/conversion funnel, and the single remaining human gate (APPLY_AWIN_DIGITALOCEAN). Read-only; verifiably ready for a real affiliate link with zero further coding.",
    reused: 'commercial_operations.py::affiliate_chain_readiness(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('affiliate_chain_readiness', [], req),
    health: pythonHealthCheck('affiliate_chain_readiness'),
  },
  {
    name: 'first-dollar-engine',
    description: "FIRST-DOLLAR ENGINE: read-only scoring/ranking/router over the existing infrastructure. Computes FIRST_DOLLAR_SCORE (12 weighted criteria), classifies AUTOMATABLE vs HUMAN_GATE, returns the best first-dollar path + scale ladder. Never writes a ledger, never spends.",
    reused: 'first_dollar_engine.py::run_first_dollar_cycle(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('first_dollar_engine', [], req),
    health: pythonHealthCheck('first_dollar_engine'),
  },
  {
    name: 'founder-next-action',
    description: "FOUNDER ONE-NEXT-ACTION: consolidates every human gate across all arms into one prioritized next action for the founder (mandate section 22 — one action, not twenty tasks). Real-state only: .env presence, publish protection, paddle products, commission opportunities, real clicks. Read-only, never publishes, never spends.",
    reused: 'founder_next_action.py::build_founder_next_action(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('founder_next_action', [], req),
    health: pythonHealthCheck('founder_next_action'),
  },
  {
    name: 'seo-distribution',
    description: "SEO DISTRIBUTION: the only READY distribution channel (zero-cost, no external approval). Publishes honest, problem-first SEO pages to the customer site from real portfolio opportunities; idempotent; never contacts a platform, never fabricates revenue.",
    reused: 'seo_distribution.py::publish_seo_pages(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('seo_distribution', [], req),
    health: pythonHealthCheck('seo_distribution'),
  },
  {
    name: 'golden-hunter-refresh',
    description: "GOLDEN HUNTER AUTO-REFRESH: closes the DISCOVER->RE-RANK feed. Re-ranks the same real, already-scored niches with a fresh generated_at so the golden bridge never stalls on the 24h freshness window; never fabricates an opportunity.",
    reused: 'commercial_activation.py::force_refresh_golden_opportunities(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('golden_hunter_refresh', [], req),
    health: pythonHealthCheck('golden_hunter_refresh'),
  },
  {
    name: 'experiment-cycle',
    description: "EXPERIMENT AUTO LOOP: closes LEARN->SCALE/ITERATE/KILL. Records real page-view observations into running experiments, auto-evaluates due experiments (ADOPT->SCALE / REJECT->KILL / NO_DIFF->WATCH / INSUFFICIENT->ITERATE), retires stale ones so none runs forever silently.",
    reused: 'commercial_experiment_automation.py::run_experiment_cycle(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('experiment_cycle', [], req),
    health: pythonHealthCheck('experiment_cycle'),
  },
  {
    name: 'executive-orchestrator',
    description: "EXECUTIVE ORCHESTRATOR: the unified control layer. ONE company state + ONE priority system (TOP opportunity/arm/autonomous action/human gate/failure/experiment/learning) + auditable decision state machine + deduped work queue + executive memory. Composition-only, reusing revenue_os / first_dollar_engine / founder_next_action / experiment loop / retry queue.",
    reused: 'executive_orchestrator.py::run_executive_orchestrator(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('executive_orchestrator', [], req),
    health: pythonHealthCheck('executive_orchestrator'),
  },
  {
    name: 'portfolio-routing',
    description: "GLOBAL REVENUE PORTFOLIO ROUTER (Task 6): selects the best existing business-model/channel for every VERIFIED opportunity by reusing the real engines (revenue_os arm router, profit-first rank, ladder_opportunity_score, offer/channel router, experiment registry). Read-only, evidence-gated (VERIFIED-tier + non-stale only).",
    reused: 'portfolio_routing.py::portfolio_routing_report(), via mission_control_api.py.',
    handler: (req) => runPythonServiceCached('portfolio_routing', [], req),
    health: pythonHealthCheck('portfolio_routing'),
  },
];

// Renders SERVICE_LAYER_API.md straight from SERVICE_REGISTRY so the doc
// can never hand-drift from the real, live set of services — "API
// documentation generated automatically", not a hand-maintained file.
function generateServiceLayerDocs() {
  const lines = [
    '# Galaxy Forge Unified Service Layer — API Reference (v1)',
    '',
    '_Auto-generated from SERVICE_REGISTRY in server.js at server startup — do not hand-edit, it is overwritten on every restart. Source of truth: server.js._',
    '',
    `Generated at: ${new Date().toISOString()}`,
    '',
    'Every endpoint below requires an authenticated Mission Control session (`POST /api/mission-control/login`) and returns the standard envelope:',
    '',
    '```json',
    '{ "success": true, "service": "<name>", "version": "v1", "generated_at": "<ISO>", "data": { /* ... */ } }',
    '```',
    '',
    'Errors:',
    '```json',
    '{ "success": false, "service": "<name>", "version": "v1", "error": { "code": "...", "message": "..." } }',
    '```',
    '',
    '## Services',
    '',
  ];
  for (const svc of SERVICE_REGISTRY) {
    lines.push(`### ${svc.name}`, '', svc.description, '',
      `- Data: \`GET /api/v1/${svc.name}\``,
      `- Health: \`GET /api/v1/${svc.name}/health\``,
      `- Reuses: ${svc.reused}`, '');
  }
  lines.push('### docs', '', 'Machine-readable version of this same file: `GET /api/v1/docs`.', '');
  try {
    fs.writeFileSync(path.join(__dirname, 'SERVICE_LAYER_API.md'), lines.join('\n'));
  } catch (err) {
    console.error('Failed to write SERVICE_LAYER_API.md:', err.message);
  }
}
generateServiceLayerDocs();

const v1Router = express.Router();

// ── OBSERVABILITY (Phase 10A — Production Stability) ──
// Real request/error/latency counters for every request that reaches
// this router, plus service-health aggregation. Pure recording logic
// lives in lib/metrics.js (framework-free, unit-tested in isolation);
// this middleware only wires it to real request/response timing.
const METRICS_REGISTRY = metricsLib.createMetricsRegistry();

v1Router.use((req, res, next) => {
  const startedAtNs = process.hrtime.bigint();
  res.on('finish', () => {
    // req.route is only set once Express matches a route (by 'finish' time
    // it always is, even for routes with params) — using the pattern
    // ('/actions/:id', not '/actions/act_f83...') keeps route cardinality
    // bounded instead of growing one label per random job id.
    const route = (req.route && req.route.path) || req.path;
    const durationMs = Number(process.hrtime.bigint() - startedAtNs) / 1e6;
    metricsLib.recordRequest(METRICS_REGISTRY, { method: req.method, route, status: res.statusCode, durationMs });
  });
  next();
});

// Reused by both GET /api/v1/health and the health gauge inside
// GET /api/v1/metrics — one real computation, not two.
async function computeServiceLayerHealth() {
  return Promise.all(SERVICE_REGISTRY.map(async (svc) => {
    try {
      const r = await svc.health();
      return { name: svc.name, status: r.status, detail: r.detail };
    } catch (err) {
      return { name: svc.name, status: 'error', detail: err.message };
    }
  }));
}

v1Router.get('/health', async (req, res) => {
  const services = await computeServiceLayerHealth();
  const aggregate = metricsLib.aggregateHealth(services);
  res.json({
    success: true, version: 'v1', checked_at: new Date().toISOString(),
    uptime_seconds: process.uptime(), ...aggregate, services,
  });
});

v1Router.get('/metrics', async (req, res) => {
  const services = await computeServiceLayerHealth();
  const text = metricsLib.renderPrometheusText(METRICS_REGISTRY, {
    uptimeSeconds: process.uptime(), serviceHealth: services,
  });
  res.set('Content-Type', 'text/plain; version=0.0.4; charset=utf-8');
  res.send(text);
});

// Executive Mission Control V3 (ADR-151, 2026-07-30): a JSON-shaped
// sibling of /metrics above, for the dashboard's real per-division
// "Performance Indicators" field -- same METRICS_REGISTRY, same real
// counters recordRequest() already fills, no new instrumentation.
v1Router.get('/metrics.json', (req, res) => {
  res.json({ success: true, version: 'v1', generated_at: new Date().toISOString(), routes: metricsLib.summarizeRoutes(METRICS_REGISTRY) });
});

v1Router.get('/docs', (req, res) => {
  res.json({
    success: true,
    version: 'v1',
    generated_at: new Date().toISOString(),
    services: SERVICE_REGISTRY.map(s => ({
      name: s.name,
      description: s.description,
      reused: s.reused,
      data_endpoint: `/api/v1/${s.name}`,
      health_endpoint: `/api/v1/${s.name}/health`,
    })),
  });
});

for (const svc of SERVICE_REGISTRY) {
  v1Router.get(`/${svc.name}`, (req, res) => {
    const startedAt = Date.now();
    Promise.resolve(svc.handler(req))
      .then((data) => {
        logServiceCall({ service: svc.name, path: req.path, method: req.method, status: 200, duration_ms: Date.now() - startedAt });
        res.json({ success: true, service: svc.name, version: 'v1', generated_at: new Date().toISOString(), data });
      })
      .catch((err) => {
        logServiceCall({ service: svc.name, path: req.path, method: req.method, status: 500, duration_ms: Date.now() - startedAt, error: err.message });
        res.status(500).json({ success: false, service: svc.name, version: 'v1', error: { code: 'internal_error', message: err.message } });
      });
  });

  v1Router.get(`/${svc.name}/health`, async (req, res) => {
    const startedAt = Date.now();
    try {
      const result = await svc.health();
      logServiceCall({ service: svc.name, path: req.path, method: req.method, status: 200, duration_ms: Date.now() - startedAt, health: result.status });
      res.json({ success: true, service: svc.name, version: 'v1', checked_at: new Date().toISOString(), ...result });
    } catch (err) {
      logServiceCall({ service: svc.name, path: req.path, method: req.method, status: 500, duration_ms: Date.now() - startedAt, error: err.message });
      res.status(500).json({ success: false, service: svc.name, version: 'v1', error: { code: 'health_check_failed', message: err.message } });
    }
  });
}

// ── ACTIONS (Phase 9 — Mission Control Operations) ──
// Mutating/triggering endpoints, still reuse-only: every action calls
// straight into an already-built module, nothing here decides anything
// new. Two actions (rerun-market-analysis, trigger-opportunity-
// evaluation) touch live external services and can take minutes, so they
// run as background jobs: POST returns a job immediately (status
// 'running'); GET /api/v1/actions/:id polls for progress/result. The
// rest are fast, local-file-only operations and complete inline.

const ACTION_JOBS = new Map();
const ACTION_JOBS_MAX = 200; // bound memory; only ever prunes jobs that already finished

function pruneActionJobs() {
  if (ACTION_JOBS.size <= ACTION_JOBS_MAX) return;
  const finished = [...ACTION_JOBS.values()]
    .filter(j => j.status !== 'running')
    .sort((a, b) => a.started_at.localeCompare(b.started_at));
  for (const job of finished) {
    if (ACTION_JOBS.size <= ACTION_JOBS_MAX) break;
    ACTION_JOBS.delete(job.id);
  }
}

function newActionJob(action) {
  const id = 'act_' + crypto.randomBytes(8).toString('hex');
  const job = {
    id, action, status: 'running',
    started_at: new Date().toISOString(), finished_at: null,
    result: null, error: null,
    progress: [{ at: new Date().toISOString(), message: `started ${action}` }],
  };
  ACTION_JOBS.set(id, job);
  pruneActionJobs();
  return job;
}

// Spawns immediately and returns the job record right away
// (status:'running'); updates the SAME job object in place whenever the
// process actually finishes, fully decoupled from any HTTP response —
// so a five-minute real evaluation never holds a request open.
// Lightweight tracing (Phase 10A — Production Stability): real,
// timestamped lifecycle spans for the two actions this applies to today
// (rerun-market-analysis / Market Analysis, trigger-opportunity-evaluation
// / Opportunity Evaluation — the only two registered with kind:'async').
// Not a new tracing system — just more granular entries in the exact same
// job.progress array/logServiceCall() calls Phase 9 already built, so a
// slow multi-minute real run has real, inspectable stage timestamps
// instead of only "started"/"finished".
function traceSpan(job, action, span) {
  const at = new Date().toISOString();
  job.progress.push({ at, message: span });
  logServiceCall({ service: 'actions', action, job_id: job.id, event: 'span', span });
}

// Slow, real-network async actions (rerun-market-analysis, trigger-
// opportunity-evaluation, run-full-cycle) — observed taking 3-5 minutes
// against 111 real signals. This is a hang safety net, not a normal-
// operation limit: 15 minutes is far above any observed real run, just
// enough to guarantee a stuck subprocess eventually gets killed instead
// of wedging the single-writer guard on that action forever.
const PYTHON_ACTION_TIMEOUT_MS = 15 * 60 * 1000;

// Zero-assumption audit follow-up — High finding, fixed: /generate-book and
// /api/sales/poll spawned Python subprocesses with no timeout at all,
// unlike every other spawn site in this file. Both are business-critical
// and frequently invoked (sales_poll fires every factory_loop tick, ~every
// 10 min) — a genuine hang (Groq stall, network hang) would previously run
// forever server-side with nothing to kill it. Set generously above each
// caller's own client-side timeout (factory_loop.js: 150s for
// generate-book, 30s for sales_poll) so the server reports a clean timeout
// error before the caller gives up first.
const PYTHON_GENERATE_BOOK_TIMEOUT_MS = 180000;
const PYTHON_SALES_POLL_TIMEOUT_MS = 45000;

function runPythonActionAsync(action, section, extraArgs = []) {
  const job = newActionJob(action);
  const pythonPath = detectPython();
  const scriptPath = path.join(__dirname, 'mission_control_api.py');
  const python = spawn(pythonPath, [scriptPath, section, ...extraArgs], { cwd: __dirname });
  traceSpan(job, action, 'python_process_spawned');
  let output = '', errOut = '', timedOut = false;
  killAfterTimeout(python, PYTHON_ACTION_TIMEOUT_MS, () => { timedOut = true; });
  python.stdout.on('data', d => { output += d.toString(); });
  python.stderr.on('data', d => { errOut += d.toString(); });
  const finish = (status, resultOrError) => {
    job.status = status;
    job.finished_at = new Date().toISOString();
    if (status === 'completed') job.result = resultOrError; else job.error = resultOrError;
    job.progress.push({ at: job.finished_at, message: status });
    logServiceCall({ service: 'actions', action, job_id: job.id, event: 'finished', status, duration_ms: Date.parse(job.finished_at) - Date.parse(job.started_at) });
  };
  python.on('error', (err) => finish('failed', err.message));
  python.on('close', () => {
    traceSpan(job, action, 'python_process_exited');
    if (timedOut) return finish('failed', `timed out after ${PYTHON_ACTION_TIMEOUT_MS}ms`);
    let parsed;
    try {
      parsed = JSON.parse(output.trim());
    } catch {
      return finish('failed', `parse error: ${output}${errOut}`);
    }
    if (parsed.success === false) return finish('failed', parsed.error || 'action reported failure');
    finish('completed', parsed);
  });
  logServiceCall({ service: 'actions', action, job_id: job.id, event: 'started' });
  return job;
}

// Phase 11 (Autonomous Production Launch): the one action that needs one
// extra step beyond runPythonActionAsync's plain "spawn, wait, parse" —
// after the Python side's full_cycle stages finish, this appends a
// company_health_monitoring section using the exact same companyHealthService()
// handler already registered in SERVICE_REGISTRY (JS-side Company Health
// isn't reachable from Python). Wrapped independently so a failure here
// never discards the real Python-side results that already completed —
// the same graceful-degradation principle applied one level up.
function runFullCycleActionAsync(action) {
  const job = newActionJob(action);
  const pythonPath = detectPython();
  const scriptPath = path.join(__dirname, 'mission_control_api.py');
  const python = spawn(pythonPath, [scriptPath, 'full_cycle'], { cwd: __dirname });
  traceSpan(job, action, 'python_process_spawned');
  let output = '', errOut = '', timedOut = false;
  killAfterTimeout(python, PYTHON_ACTION_TIMEOUT_MS, () => { timedOut = true; });
  python.stdout.on('data', d => { output += d.toString(); });
  python.stderr.on('data', d => { errOut += d.toString(); });
  const finish = (status, resultOrError) => {
    job.status = status;
    job.finished_at = new Date().toISOString();
    if (status === 'completed') job.result = resultOrError; else job.error = resultOrError;
    job.progress.push({ at: job.finished_at, message: status });
    logServiceCall({ service: 'actions', action, job_id: job.id, event: 'finished', status, duration_ms: Date.parse(job.finished_at) - Date.parse(job.started_at) });
  };
  python.on('error', (err) => finish('failed', err.message));
  python.on('close', async () => {
    traceSpan(job, action, 'python_process_exited');
    if (timedOut) return finish('failed', `timed out after ${PYTHON_ACTION_TIMEOUT_MS}ms`);
    let parsed;
    try {
      parsed = JSON.parse(output.trim());
    } catch {
      return finish('failed', `parse error: ${output}${errOut}`);
    }
    if (parsed.success === false) return finish('failed', parsed.error || 'action reported failure');

    let companyHealthSection;
    try {
      companyHealthSection = { ok: true, result: await companyHealthService() };
    } catch (err) {
      companyHealthSection = { ok: false, error: err.message };
    }
    traceSpan(job, action, 'company_health_monitoring_collected');
    finish('completed', { ...parsed, company_health_monitoring: companyHealthSection });
  });
  logServiceCall({ service: 'actions', action, job_id: job.id, event: 'started' });
  return job;
}

// For actions cheap enough (local file reads/writes only, no live
// network) that a job/polling round-trip would just be overhead — runs
// to completion before the HTTP response, but still recorded as a job
// so it shows up in the same activity/audit trail as the async ones.
async function runActionSync(action, fn, req) {
  const job = newActionJob(action);
  try {
    const result = await fn(req);
    job.status = 'completed';
    job.result = result;
    job.finished_at = new Date().toISOString();
    logServiceCall({ service: 'actions', action, job_id: job.id, event: 'finished', status: 'completed', duration_ms: Date.parse(job.finished_at) - Date.parse(job.started_at) });
  } catch (err) {
    job.status = 'failed';
    job.error = err.message;
    job.finished_at = new Date().toISOString();
    logServiceCall({ service: 'actions', action, job_id: job.id, event: 'finished', status: 'failed', error: err.message });
  }
  return job;
}

// ── Production pause/resume ──
// This factory has no scheduler and no live background production
// process to literally "pause" (CLAUDE.md: "No scheduler exists"). This
// flag gates the one real thing "production" means here: the manually-
// triggered start-production-pipeline action below. Toggling it back is
// the exact reverse operation — fully reversible by design.
const PRODUCTION_CONTROL_PATH = path.join(__dirname, 'data', 'production_control.json');

function readProductionControl() {
  try {
    return JSON.parse(fs.readFileSync(PRODUCTION_CONTROL_PATH, 'utf8'));
  } catch {
    return { paused: false, changed_at: null, reason: null };
  }
}

function writeProductionControl(state) {
  fs.mkdirSync(path.dirname(PRODUCTION_CONTROL_PATH), { recursive: true });
  fs.writeFileSync(PRODUCTION_CONTROL_PATH, JSON.stringify(state, null, 2));
  return state;
}

// ── N8N PRODUCTION NOTIFY (n8n Integration Gap fix) ──
// Before this, n8n's only real touchpoints were Market Intelligence
// (Openclaw_Sensing_Engine -> POST /api/trends) and status/sales
// (00_CEO -> GET /api/dashboard, 02_Sales_Poll -> POST /api/sales/poll) —
// nothing in the chain notified n8n once a real Production dossier
// completed. Actual fetch/timeout/logging logic lives in
// lib/n8n_notify.js (no Express dependency, unit-tested in isolation by
// mocking global.fetch — same convention as lib/metrics.js); this is a
// thin wrapper supplying the real env var and log sink.
const N8N_PRODUCTION_WEBHOOK_URL = process.env.N8N_PRODUCTION_WEBHOOK_URL || null;
// Unified Recovery System §4/§6 (2026-07-18): the same real webhook var
// factory_loop.js's own recovery/founder-facing events already use
// (N8N_TELEGRAM_WEBHOOK_URL, distinct from N8N_PRODUCTION_WEBHOOK_URL) —
// so a recovery_completed event fired from a Mission Control action
// lands on the same Telegram channel as the other 3 recovery events.
const N8N_TELEGRAM_WEBHOOK_URL = process.env.N8N_TELEGRAM_WEBHOOK_URL || null;

async function notifyN8nProductionEvent(payload) {
  return n8nNotify.notifyN8nProductionEvent(payload, {
    webhookUrl: N8N_PRODUCTION_WEBHOOK_URL,
    log: (entry) => logServiceCall({ service: 'n8n_notify', ...entry }),
  });
}

async function notifyN8nRecoveryEvent(payload) {
  return n8nNotify.notifyN8nProductionEvent(payload, {
    webhookUrl: N8N_TELEGRAM_WEBHOOK_URL,
    envVarName: 'N8N_TELEGRAM_WEBHOOK_URL',
    log: (entry) => logServiceCall({ service: 'n8n_notify', ...entry }),
  });
}

async function startProductionPipelineAction() {
  const control = readProductionControl();
  if (control.paused) {
    throw new Error(`production is paused (${control.reason || 'no reason given'}, since ${control.changed_at})`);
  }
  const result = await runPythonService('production');
  if (result.processed > 0) {
    // Fire-and-forget on purpose: a slow/unreachable n8n notify must
    // never delay the action's own response back to Mission Control.
    for (const dossier of result.dossiers || []) {
      notifyN8nProductionEvent(n8nNotify.buildProductionNotifyPayload(dossier))
        .catch(() => {}); // notifyN8nProductionEvent already never rejects; belt-and-suspenders only
      // ADR-085: "Product ready" was ADR-073's other named-but-unwired
      // Telegram category (n8n's workflow only logs this event, never
      // sent it on). Direct send, same fire-and-forget discipline.
      telegramDirect.sendTelegramMessage(telegramDirect.buildProductReadyMessage(dossier)).catch(() => {});
    }
  }
  return result;
}

async function pauseProductionAction(req) {
  const reason = (req.body && req.body.reason) || 'paused via Mission Control';
  return writeProductionControl({ paused: true, changed_at: new Date().toISOString(), reason });
}

async function resumeProductionAction() {
  return writeProductionControl({ paused: false, changed_at: new Date().toISOString(), reason: null });
}

// Global Commercial Hardening, Phase 1 (2026-07-29): the founder's own
// real, immediate halt across every marketplace arm -- reuses
// channels/publish_protection.py's trigger_emergency_stop()/
// clear_emergency_stop() via mission_control_api.py, same spawn pattern
// as requestAiCapabilityAction below. Never fired automatically anywhere
// in this factory.
async function publishEmergencyStopAction(req) {
  const reason = (req.body && req.body.reason) || '';
  if (!reason.trim()) throw new Error('{ reason } is required');
  return runPythonService('publish_emergency_stop', [JSON.stringify({ reason })]);
}

async function publishEmergencyResumeAction() {
  return runPythonService('publish_emergency_resume');
}

// Global Trust & Resilience Layer, Round 2 (2026-07-29): the founder's
// own real action to isolate one named subsystem (ai_generation,
// market_intelligence) without halting the rest of the company.
// marketplace_publishing has no mark/clear action here by design -- use
// publish-emergency-stop/publish-emergency-resume above, its own real
// signal.
async function approveCommissionOpportunityAction(req) {
  const opportunity_id = (req.body && req.body.opportunity_id) || '';
  const from_state = (req.body && req.body.from_state) || '';
  const to_state = (req.body && req.body.to_state) || '';
  const evidence = (req.body && req.body.evidence) || '';
  if (!opportunity_id.trim() || !from_state.trim() || !to_state.trim()) {
    throw new Error('{ opportunity_id, from_state, to_state } are required');
  }
  return runPythonService('approve_commission_opportunity', [JSON.stringify({ opportunity_id, from_state, to_state, evidence })]);
}

async function rejectCommissionOpportunityAction(req) {
  const opportunity_id = (req.body && req.body.opportunity_id) || '';
  const from_state = (req.body && req.body.from_state) || '';
  const reason = (req.body && req.body.reason) || '';
  if (!opportunity_id.trim() || !from_state.trim()) {
    throw new Error('{ opportunity_id, from_state } are required');
  }
  return runPythonService('reject_commission_opportunity', [JSON.stringify({ opportunity_id, from_state, reason })]);
}

async function markSubsystemUnstableAction(req) {
  const name = (req.body && req.body.name) || '';
  const reason = (req.body && req.body.reason) || '';
  if (!name.trim() || !reason.trim()) throw new Error('{ name, reason } are required');
  return runPythonService('mark_subsystem_unstable', [JSON.stringify({ name, reason })]);
}

async function clearSubsystemUnstableAction(req) {
  const name = (req.body && req.body.name) || '';
  if (!name.trim()) throw new Error('{ name } is required');
  return runPythonService('clear_subsystem_unstable', [JSON.stringify({ name })]);
}

// Founder Protection (Global Trust & Resilience Layer, Round 4,
// 2026-07-29): the founder's own real, explicit clearance for a
// genuinely new arm's first real publish, or one publish attempt whose
// computed risk_score crossed the real high-risk threshold. Never
// fired automatically anywhere in this factory.
async function approveFirstPublishAction(req) {
  const armName = (req.body && req.body.arm_name) || '';
  if (!armName.trim()) throw new Error('{ arm_name } is required');
  return runPythonService('approve_first_publish', [JSON.stringify({ arm_name: armName })]);
}

async function approveElevatedRiskPublishAction(req) {
  const armName = (req.body && req.body.arm_name) || '';
  if (!armName.trim()) throw new Error('{ arm_name } is required');
  return runPythonService('approve_elevated_risk_publish', [JSON.stringify({ arm_name: armName })]);
}

// Autonomous Digital Company v1, Track B2 (2026-07-19): a real, logged
// department request for a different/better AI model — never an
// autonomous model switch (ai_capability/evaluator.py's own recommendation
// stays advisory only, since there is zero comparative data across
// providers today beyond Groq).
async function requestAiCapabilityAction(req) {
  const { department, task_type, requested_provider, reason } = req.body || {};
  if (!department || !task_type || !requested_provider) {
    throw new Error('{ department, task_type, requested_provider } are required');
  }
  const payload = JSON.stringify({ department, task_type, requested_provider, reason: reason || '' });
  return runPythonService('ai_capability_request', [payload]);
}

// Customer Platform Round 4 (2026-07-29): the founder's own real action --
// attaches a real deliverable (a local file path or a real URL) to a
// request stuck in PENDING_FOUNDER_FULFILLMENT (a genuinely bespoke
// request with no automated production trigger). Never a fabricated
// placeholder -- customer_pipeline.fulfill_manually() itself refuses an
// empty or nonexistent local path.
async function fulfillCustomerRequestManuallyAction(req) {
  const { request_id, delivery_ref, note } = req.body || {};
  if (!request_id || !delivery_ref) {
    throw new Error('{ request_id, delivery_ref } are required');
  }
  return runCustomerPipelineCommand('fulfill_manually', { request_id, delivery_ref, note: note || '' });
}

// Autonomous Company Evolution Engine, Round 6 (2026-07-29): the three
// founder-only actions that actually move a real proposal past
// AWAITING_FOUNDER_APPROVAL. Never fired automatically -- factory_loop.js's
// daily tick only ever runs intake/simulate/decide (Round 4), which stops
// at AWAITING_FOUNDER_APPROVAL by design. This is the one concrete code
// enforcement of the founder's explicit "human-gated always" choice.
async function approveEvolutionProposalAction(req) {
  const { proposal_id, note } = req.body || {};
  if (!proposal_id) throw new Error('{ proposal_id } is required');
  return runPythonService('approve_evolution_proposal', [JSON.stringify({ proposal_id, note: note || '' })]);
}

async function rejectEvolutionProposalAction(req) {
  const { proposal_id, reason } = req.body || {};
  if (!proposal_id) throw new Error('{ proposal_id } is required');
  return runPythonService('reject_evolution_proposal', [JSON.stringify({ proposal_id, reason: reason || '' })]);
}

async function markEvolutionProposalImplementedAction(req) {
  const { proposal_id, note } = req.body || {};
  if (!proposal_id) throw new Error('{ proposal_id } is required');
  return runPythonService('mark_evolution_proposal_implemented', [JSON.stringify({ proposal_id, note: note || '' })]);
}

// Round 5 (2026-07-29): the founder's own real, manual confirmation that
// they actually followed up with a delivered customer -- no scheduler
// exists in this factory (CLAUDE.md), so this is never auto-fired.
async function markCustomerFollowedUpAction(req) {
  const { request_id } = req.body || {};
  if (!request_id) throw new Error('{ request_id } is required');
  return runCustomerPipelineCommand('mark_followed_up', { request_id });
}

// Unified Recovery System §2/§6 (2026-07-18): the founder's explicit
// clear-to-proceed after startup classified a real interruption as
// NEEDS_CONFIRMATION (recovery/startup_check.py) — e.g. they checked the
// real Paddle dashboard for a stray product and confirmed it's safe.
// Refuses honestly if nothing is actually marked interrupted, rather
// than silently no-opping.
async function confirmSafeToResumeAction() {
  const recovery = await runPythonService('recovery');
  if (!recovery.recovery_info || !recovery.recovery_info.interrupted) {
    throw new Error('nothing is currently marked as needing confirmation — recovery_info.interrupted is false');
  }
  const currentTask = recovery.current_task || {};
  const result = await runPythonService('resolve_recovery');
  notifyN8nRecoveryEvent(n8nNotify.buildRecoveryCompletedPayload(currentTask.name, currentTask.idempotency_key))
    .catch(() => {}); // never blocks the action's own response
  return result;
}

const ACTION_REGISTRY = [
  {
    name: 'refresh-data',
    description: 'No backend computation — logs a manual refresh event for the activity timeline/audit trail. The actual data re-fetch happens client-side against the existing read services.',
    reversible: true,
    kind: 'sync',
    run: async () => ({ refreshed_at: new Date().toISOString() }),
  },
  {
    name: 'rerun-market-analysis',
    description: 'Re-scans every real signal source and re-ranks the golden opportunity queue.',
    reused: 'golden_hunter/hunt.py run_hunt() (ADR-060)',
    reversible: true, // read-only re-scan; nothing it does is destructive
    kind: 'async',
    section: 'rerun_market_analysis',
  },
  {
    name: 'trigger-opportunity-evaluation',
    description: 'Runs every real signal through the orchestrator cycle and records fresh decisions. Never triggers real production — execute_production is hardcoded false.',
    reused: 'real_world_mode/operating_mode.py run_real_world_cycle(execute_production=False) (ADR-056)',
    reversible: true,
    kind: 'async',
    section: 'trigger_opportunity_evaluation',
  },
  {
    // Strategic Phase 3, Round 1 (2026-07-22): "Go Deep" -- the real,
    // usable version of Market Validation's "collect evidence before
    // production, multiple independent signals" for ONE opportunity the
    // founder selects. Never gates any decision itself (informational
    // only, same discipline as the ROI estimate) -- the fully-automatic
    // ladder_fast_gate path stays honestly single-signal, unchanged.
    name: 'go-deep-evidence',
    description: 'Runs real customer-pain evidence (GitHub Issues + HN Algolia), live competitor classification, and the full 11-source evidence-coverage score for ONE opportunity. Informational only — never changes any accept/reject gate.',
    reused: 'market_intelligence_engine.analyze_customer_pain() + competitor_discovery.get_or_refresh_competitors() + multi_source_intelligence.coverage.evidence_coverage_score()',
    reversible: true, // read-only evidence gathering; nothing it does is destructive
    kind: 'async',
    asyncRunner: (req) => {
      const niche = (req.body && req.body.niche || '').trim();
      if (!niche) return Promise.reject(new Error('{ niche } is required in the request body'));
      return runPythonActionAsync('go-deep-evidence', 'go_deep_evidence', [JSON.stringify({ niche })]);
    },
  },
  {
    name: 'start-production-pipeline',
    description: 'Builds a production dossier for every currently ACCEPTED opportunity. Refuses to run while production is paused. Notifies n8n (fire-and-forget, opt-in via N8N_PRODUCTION_WEBHOOK_URL) once dossiers complete.',
    reused: 'production_factory/factory.py run_production_factory() (Phase 7)',
    reversible: true, // dossier building only — no real purchase/publish side effect
    kind: 'sync',
    run: startProductionPipelineAction,
  },
  {
    name: 'pause-production',
    description: 'Gates start-production-pipeline off until resumed. Does not affect factory_loop.js (this factory has no scheduler to pause — see CLAUDE.md).',
    reversible: true,
    kind: 'sync',
    run: pauseProductionAction,
  },
  {
    name: 'resume-production',
    description: 'Reverses pause-production.',
    reversible: true,
    kind: 'sync',
    run: resumeProductionAction,
  },
  {
    // Global Commercial Hardening, Phase 1 (2026-07-29): the founder's
    // real, instant, all-arms publish halt -- registered `kind: 'sync'`
    // (not async/Python-spawned as a background job) for exactly the
    // same reliability reason pause-production above is sync: no
    // subprocess/timeout risk on an action meant to be immediate.
    name: 'publish-emergency-stop',
    description: 'Immediately blocks every marketplace arm from publishing, real or dry-run notwithstanding -- the real pre-publish gate in channels/publish_protection.py checks this first. Requires { reason } in the request body.',
    reused: 'channels/publish_protection.py trigger_emergency_stop() (Global Commercial Hardening, Phase 1)',
    reversible: true,
    kind: 'sync',
    run: publishEmergencyStopAction,
  },
  {
    name: 'publish-emergency-resume',
    description: 'Reverses publish-emergency-stop.',
    reused: 'channels/publish_protection.py clear_emergency_stop() (Global Commercial Hardening, Phase 1)',
    reversible: true,
    kind: 'sync',
    run: publishEmergencyResumeAction,
  },
  {
    // Founder Protection (Global Trust & Resilience Layer, Round 4,
    // 2026-07-29): the one new piece of Priority 9 actually built --
    // proven arms (Gumroad et al.) stay fully autonomous, unchanged.
    name: 'approve-first-publish',
    description: 'Clears a genuinely new marketplace arm (never a proven one -- KDP/Shopify/AliExpress today) for its very first real publish. Requires { arm_name } in the request body.',
    reused: 'channels/publish_protection.py approve_first_publish() (Global Trust & Resilience Layer, Round 4)',
    reversible: false,
    kind: 'sync',
    run: approveFirstPublishAction,
  },
  {
    name: 'approve-elevated-risk-publish',
    description: 'A real, single-use clearance for one publish attempt whose computed risk_score crossed the real high-risk threshold -- consumed by the very next real attempt for that arm, whatever its outcome. Requires { arm_name } in the request body.',
    reused: 'channels/publish_protection.py approve_elevated_risk_publish() (Global Trust & Resilience Layer, Round 4)',
    reversible: false,
    kind: 'sync',
    run: approveElevatedRiskPublishAction,
  },
  {
    name: 'confirm-safe-to-resume',
    description: 'Clears a recovery_info.interrupted flag after the founder has verified it is actually safe (e.g. checked the real Paddle dashboard for a stray product following an unclean shutdown mid-production/publishing). Refuses honestly if nothing is currently marked as needing confirmation.',
    reused: 'recovery/startup_check.py resolve_recovery(), via mission_control_api.py',
    reversible: false, // resolves a real state transition, not a toggle
    kind: 'sync',
    run: confirmSafeToResumeAction,
  },
  {
    // ADR-085 (2026-07-22): Paddle checkout creation for the real $388
    // techdoc has been blocked since ADR-074 by Paddle's own account-
    // onboarding gate (transaction_checkout_not_enabled) -- entirely on
    // Paddle's side, nothing here can clear it. This action re-attempts
    // checkout-link creation for that exact, already-existing price and,
    // the moment it succeeds, sends the real link directly to the
    // founder's Telegram in Arabic (bypasses n8n -- same precedent as
    // ADR-072/074's addenda for critical one-off messages). Idempotent:
    // a second run after a real link was already sent reports
    // already_notified=true rather than re-sending. This factory
    // deliberately has no scheduler (CLAUDE.md) -- "automatic" here means
    // zero further code changes, one click away, not a background timer.
    name: 'check-paddle-checkout-status',
    description: 'Re-attempts Paddle checkout-link creation for the real $388 techdoc price. Sends a one-time Arabic Telegram message with the real link the moment Paddle onboarding clears. Reports honestly, with no message sent, while still blocked.',
    reused: 'scripts/check_paddle_checkout_status.py (ADR-085)',
    reversible: true, // read-only check; the real Telegram send is idempotent, never repeats
    kind: 'async',
    section: 'check_paddle_checkout_status',
  },
  {
    // ADR-130 (2026-07-25): batch-sweeps every real customer request
    // still in NEW through real Qualification + Opportunity Evaluation +
    // Price Generation + Proposal. Async for the same reason rerun-
    // market-analysis/trigger-opportunity-evaluation are: each NEW
    // request runs a real, live Groq market-research call.
    name: 'advance-customer-pipeline',
    description: 'Runs every real customer request still in NEW through the real evidence gate, real pricing, and real proposal generation (customer_pipeline.py). Never attempts payment -- that only happens once the customer approves their own proposal.',
    reused: 'customer_pipeline.py advance_all_new_requests() (ADR-130)',
    reversible: true, // evaluates/prices/proposes only; no purchase/production side effect
    kind: 'async',
    section: 'advance_customer_pipeline',
  },
  {
    // Customer Platform Round 3 (2026-07-29): batch-sweeps every real
    // customer request AWAITING_PAYMENT against Paddle's real transaction
    // list. No scheduler exists (CLAUDE.md) -- this is the one-click-away
    // manual trigger until real payment completion is wired to a webhook.
    name: 'check-customer-payments',
    description: 'Checks every real customer request currently awaiting payment against Paddle\'s real transaction list, moving any that actually completed to PAID and generating a real invoice. Never fabricates a completion.',
    reused: 'customer_pipeline.py check_all_awaiting_payments() (Round 3)',
    reversible: true, // read-only check against Paddle; only advances a record that Paddle itself already confirmed paid
    kind: 'async',
    section: 'check_customer_payments',
  },
  {
    // Round 4 (2026-07-29): the honest founder-in-the-loop completion for
    // requests with no automated production trigger (see customer_
    // pipeline.py's _fulfill_paid_request()). Requires a real payload --
    // { request_id, delivery_ref } -- so this is a sync action, not a
    // zero-payload async sweep.
    name: 'fulfill-customer-request-manually',
    description: 'Attaches a real deliverable (local file path or URL) to a customer request stuck in PENDING_FOUNDER_FULFILLMENT, moving it to DELIVERED. Requires { request_id, delivery_ref } in the request body, optional { note }.',
    reused: 'customer_pipeline.py fulfill_manually() (Round 4)',
    reversible: false, // moves a real request to DELIVERED -- the customer sees this immediately
    kind: 'sync',
    run: fulfillCustomerRequestManuallyAction,
  },
  {
    name: 'mark-customer-followed-up',
    description: 'Marks a real DELIVERED customer request as FOLLOWED_UP once the founder has actually checked in with the customer. Requires { request_id } in the request body.',
    reused: 'customer_pipeline.py mark_followed_up() (Round 5)',
    reversible: false,
    kind: 'sync',
    run: markCustomerFollowedUpAction,
  },
  {
    // Executive Directive (2026-07-22): the permanent core Executive
    // Quality Gate every opportunity/product must pass before entering
    // production. Reads the real, already-recorded decision -- never
    // re-scores anything. Where this factory has no real data source at
    // all (willingness-to-pay, per-niche customer-acquisition-difficulty,
    // customer-retention -- zero real sales exist to measure retention
    // from) the gate reports Unknown honestly and routes to
    // NEEDS_HUMAN_REVIEW rather than a fabricated PASS.
    name: 'executive-quality-gate',
    description: 'Runs the real Executive Quality Gate (20 criteria) against an already-recorded decision. Never re-scores, never fabricates a criterion with no real data source -- Unknown criteria route to NEEDS_HUMAN_REVIEW, never a silent APPROVED.',
    reused: 'executive_quality_gate.py (Executive Directive)',
    reversible: true, // read-only evaluation; changes no data
    kind: 'async',
    asyncRunner: (req) => {
      const niche = (req.body && req.body.niche || '').trim();
      if (!niche) return Promise.reject(new Error('{ niche } is required in the request body'));
      return runPythonActionAsync('executive-quality-gate', 'executive_quality_gate', [JSON.stringify({ niche })]);
    },
  },
  {
    // Market Learning Loop (Executive Directive, 2026-07-22): the real,
    // human-driven entry point for evidence categories nothing in this
    // factory can automatically observe -- a real discovery call
    // outcome, a real cold-email reply, a real objection heard on a
    // call. Once logged, the Executive Quality Gate consumes it
    // automatically from that point on, no further code changes.
    name: 'record-market-evidence',
    description: 'Logs one real market-evidence event (discovery call, cold outreach result, objection, closed sale, etc.) for a niche. The Executive Quality Gate reads this automatically -- UNKNOWN fields disappear only because real evidence was recorded here, never assumed.',
    reused: 'market_evidence.py (Market Learning Loop)',
    reversible: true, // append-only evidence log; nothing it does is destructive
    kind: 'async',
    asyncRunner: (req) => {
      const { niche, event_type, payload } = req.body || {};
      if (!niche || !event_type) return Promise.reject(new Error('{ niche, event_type } are both required in the request body'));
      return runPythonActionAsync('record-market-evidence', 'record_market_evidence', [JSON.stringify({ niche, event_type, payload })]);
    },
  },
  {
    // Enterprise Readiness Layer (Executive Directive, 2026-07-22).
    // Applies PROSPECTIVELY ONLY per the founder's explicit decision --
    // the 5 real products shipped before this gate existed keep an
    // honest pre-gate status, never a silent retroactive rejection.
    name: 'enterprise-readiness-gate',
    description: 'Runs the full Enterprise Readiness Layer (10 product reviews, risk register, documentation completeness, transparency report) against an already-recorded decision. Prospective only -- pre-gate products report PRE_GATE, never REJECTED.',
    reused: 'enterprise_readiness.py (Executive Directive)',
    reversible: true, // read-only evaluation; changes no data
    kind: 'async',
    asyncRunner: (req) => {
      const niche = (req.body && req.body.niche || '').trim();
      if (!niche) return Promise.reject(new Error('{ niche } is required in the request body'));
      return runPythonActionAsync('enterprise-readiness-gate', 'enterprise_readiness_gate', [JSON.stringify({ niche })]);
    },
  },
  {
    // Risk Intelligence Engine (Executive Directive, 2026-07-22) --
    // on-demand only, this factory has no scheduler. Regulation
    // changes, pricing changes, technology disruption, and demand
    // decline are honestly reported Unknown -- no real, funded data
    // source exists for them in this factory.
    name: 'risk-intelligence-scan',
    description: 'On-demand real risk scan (competitors, market saturation, customer complaints) for one niche. Regulation/pricing/tech-disruption/demand-decline are honestly Unknown -- no real data source exists for these yet.',
    reused: 'enterprise_readiness.py::run_risk_intelligence_scan()',
    reversible: true,
    kind: 'async',
    asyncRunner: (req) => {
      const { niche, refresh_competitors } = req.body || {};
      if (!niche) return Promise.reject(new Error('{ niche } is required in the request body'));
      return runPythonActionAsync('risk-intelligence-scan', 'risk_intelligence_scan', [JSON.stringify({ niche, refresh_competitors: !!refresh_competitors })]);
    },
  },
  {
    // AI Executive Board (Executive Directive, 2026-07-22) -- the
    // highest decision-making authority in this factory. All 10
    // executives are deterministic real-evidence analyses, never a
    // free-form LLM opinion. "No single agent may approve strategic
    // decisions alone" is enforced structurally: this action is the
    // ONLY path to a real board decision.
    name: 'convene-executive-board',
    description: 'Convenes all 10 executive roles against an already-recorded decision, real evidence only. Majority required for "production" decisions, unanimous for "irreversible". Every meeting is stored permanently with complete reasoning.',
    reused: 'executive_board.py (Executive Directive)',
    reversible: true, // read-only evaluation + an append-only meeting record; changes no other data
    kind: 'async',
    asyncRunner: (req) => {
      const { niche, decision_type } = req.body || {};
      if (!niche) return Promise.reject(new Error('{ niche } is required in the request body'));
      return runPythonActionAsync('convene-executive-board', 'convene_executive_board', [JSON.stringify({ niche, decision_type: decision_type || 'production' })]);
    },
  },
  {
    name: 'review-board-track-record',
    description: 'On-demand (not continuous -- no scheduler exists): compares real past board decisions against whatever real market evidence has accumulated since, for one niche or every real meeting.',
    reused: 'executive_board.py::review_board_track_record()',
    reversible: true,
    kind: 'async',
    asyncRunner: (req) => {
      const niche = (req.body && req.body.niche) || null;
      return runPythonActionAsync('review-board-track-record', 'review_board_track_record', [JSON.stringify({ niche })]);
    },
  },
  {
    // Executive Board Integration (2026-07-23) -- read-only lookup of
    // whatever the board already decided for one niche (6-lens
    // strategic brief + 6-field decision summary), without convening a
    // new meeting. Same real data convene-executive-board already wrote.
    name: 'get-board-brief',
    description: 'Read-only lookup of the latest real board decision for one niche (strategic brief: threat/opportunity/market/financial/technical/trust; decision summary: decision/confidence/evidence/risks/recommended actions/follow-up tasks). Never convenes a new meeting.',
    reused: 'executive_board.py::get_latest_board_brief()',
    reversible: true,
    kind: 'async',
    asyncRunner: (req) => {
      const niche = (req.body && req.body.niche || '').trim();
      if (!niche) return Promise.reject(new Error('{ niche } is required in the request body'));
      return runPythonActionAsync('get-board-brief', 'get_board_brief', [JSON.stringify({ niche })]);
    },
  },
  {
    // Galaxy Council (2026-07-29) -- "no single module dominates": all 9
    // real intelligence-domain members convened side by side for one
    // niche, honest disagreement never averaged into a fake consensus.
    // Answers a different question than convene-executive-board above
    // ("what does each intelligence domain currently believe" vs.
    // "should we approve this one already-evaluated decision") -- both
    // stay, deliberately distinct (ADR-138). Read-only -- does not
    // persist anything; use record-council-recommendation for that.
    name: 'convene-galaxy-council',
    description: "Convenes all 9 real Council members (Strategic/Market/Production/Customer/Financial/Security/Resilience/Innovation/Executive-Memory) for one niche -- each with opinion/confidence/evidence/risk/recommendation/founder_approval_required, honest stance-based disagreement detection, and Expected Impact/Long-term Effect citing Strategic Intelligence Core's own real dimensions. Never fabricates consensus, never hides disagreement.",
    reused: 'galaxy_council.py::convene_council()',
    reversible: true, // read-only -- persists nothing by itself
    kind: 'async',
    asyncRunner: (req) => {
      const niche = (req.body && req.body.niche || '').trim();
      if (!niche) return Promise.reject(new Error('{ niche } is required in the request body'));
      return runPythonActionAsync('convene-galaxy-council', 'convene_galaxy_council', [JSON.stringify({ niche })]);
    },
  },
  {
    name: 'record-council-recommendation',
    description: 'Re-convenes the Galaxy Council fresh for one niche and permanently appends the real result to data/council_recommendations.jsonl -- the real substrate get-council-learning-summary needs (Recommendation vs Founder Decision vs Real Outcome). Explicit, founder-triggered only -- never automatic.',
    reused: 'galaxy_council.py::record_council_recommendation()',
    reversible: true, // append-only, same convention as data/board_meetings.jsonl
    kind: 'async',
    asyncRunner: (req) => {
      const { niche, decision_id } = req.body || {};
      if (!niche) return Promise.reject(new Error('{ niche } is required in the request body'));
      return runPythonActionAsync('record-council-recommendation', 'record_council_recommendation', [JSON.stringify({ niche, decision_id: decision_id || null })]);
    },
  },
  {
    name: 'get-council-learning-summary',
    description: "The real 3-way join: Council Recommendation vs. the real Founder Decision that followed vs. the real eventual Outcome -- same True/False/None non-forced-verdict discipline as review-board-track-record. Honestly NOT ENOUGH EVIDENCE until real triples accumulate.",
    reused: 'galaxy_council.py::council_learning_summary()',
    reversible: true,
    kind: 'async',
    asyncRunner: () => runPythonActionAsync('get-council-learning-summary', 'council_learning_summary', []),
  },
  {
    // Capital Allocation Engine (2026-07-29) -- the real, per-niche
    // 14-dimension Investment Score. Async-job shape (not SERVICE_
    // REGISTRY) since it chains real sub-calls (strategic_score() +
    // compute_value_profile()), same precedent as convene-galaxy-council.
    name: 'investment-score',
    description: "The real 14-dimension Investment Score for one niche (Expected Revenue, Recurring Revenue Potential, Customer Impact, Strategic Importance, Market Defensibility, Competition Level, Automation Potential, Engineering Cost, Maintenance Cost, Risk, Execution Complexity, Knowledge Reuse, Brand Value, Long-Term Asset Value) -- 7 delegated verbatim to strategic_score(), 7 newly cited from value_engine, each honestly Unknown wherever no real signal exists.",
    reused: 'capital_allocation_engine.py::investment_score()',
    reversible: true, // read-only
    kind: 'async',
    asyncRunner: (req) => {
      const niche = (req.body && req.body.niche || '').trim();
      if (!niche) return Promise.reject(new Error('{ niche } is required in the request body'));
      return runPythonActionAsync('investment-score', 'investment_score', [JSON.stringify({ niche })]);
    },
  },
  {
    // Strategic Intelligence Core (2026-07-29) -- the real, standalone
    // 11-dimension Strategic Score for one niche. Found orphaned by
    // the Enterprise Validation Phase (ADR-166) and the Company
    // Readiness Audit (2026-07-31): investment-score above already
    // calls strategic_score() internally for 7 of its own 14
    // dimensions, but the full 11-dimension result was never exposed
    // directly on its own. Real, tested, callable function -- wiring
    // it is pure technical-debt closure, not new computation.
    name: 'strategic-score',
    description: "The real, standalone 11-dimension Strategic Score for one niche (Competition, Demand, Difficulty, and 8 more, each {value, source, reason} citing an already-real signal) -- the full result investment-score above only partially re-exposes (7 of its 14 dims delegate to this same function). Honestly NOT ENOUGH EVIDENCE per-dimension wherever no real signal exists.",
    reused: 'strategic_intelligence_core.py::strategic_score()',
    reversible: true, // read-only
    kind: 'async',
    asyncRunner: (req) => {
      const niche = (req.body && req.body.niche || '').trim();
      if (!niche) return Promise.reject(new Error('{ niche } is required in the request body'));
      return runPythonActionAsync('strategic-score', 'strategic_score', [JSON.stringify({ niche })]);
    },
  },
  {
    // Galaxy Opportunity Operating System (ADR-171, 2026-08-05): a real
    // consolidation/citation layer over profit_oracle.py/executive_
    // quality_gate.py/strategic_intelligence_core.py/capital_allocation_
    // engine.py/autonomous_business_builder.py -- never a second decision
    // engine, never gates production itself. Its own 0-100 score is
    // advisory only (an 85-line for visibility); the real production gate
    // remains decision_engine's ACCEPTED/REJECTED/DEFERRED status and
    // profit_oracle.py's real 65/100 weighted floor, both unchanged.
    name: 'goos-evaluate-opportunity',
    description: "The real 15-section Opportunity Intelligence Report for one niche (Executive Summary/Problem/Customer/Competitor/Market Analysis/Business Model/Revenue Potential/Strategic Advantages/Weaknesses/Implementation Difficulty/Automation Possibilities/Estimated ROI/Recommended Pricing/Expansion Potential/Overall Recommendation) + the 20 named GOOS evaluation dimensions, each a real citation of an already-real signal. TAM/SAM/SOM is honestly NOT_MEASURABLE -- no free real market-sizing data source exists anywhere in this factory. Post-acceptance sections (Business Model/Revenue Potential/Estimated ROI/Competitor Analysis/Weaknesses) are only available for a real ACCEPTED opportunity, honestly NOT_AVAILABLE otherwise. The GOOS score's 85-line is advisory only -- it never replaces or tightens the real 65/100 weighted production floor.",
    reused: 'goos.py::build_opportunity_intelligence_report() (ADR-171) + decision_engine/store.py + value_engine.py + capital_allocation_engine.py + autonomous_business_builder.py, via mission_control_api.py.',
    reversible: true, // read-only
    kind: 'async',
    asyncRunner: (req) => {
      const niche = (req.body && req.body.niche || '').trim();
      if (!niche) return Promise.reject(new Error('{ niche } is required in the request body'));
      return runPythonActionAsync('goos-evaluate-opportunity', 'goos_evaluate_opportunity', [JSON.stringify({ niche })]);
    },
  },
  {
    // Real Evidence Provider abstraction (ADR-179, 2026-08-06): the
    // founder's directive after a real session hit HTTP 403s trying to
    // manually gather Proof of Payment evidence against Upwork/Fiverr/
    // G2/Etsy -- never let one blocked marketplace source stop
    // evaluation. Queries every real evidence source for one niche in
    // the founder's own named priority order (Official APIs > RSS
    // feeds > Public reports > Google Trends > GitHub > Product Hunt >
    // Reddit > Hacker News > Stack Overflow > Web pages), catching
    // every failure (including an actively-blocked one) per source --
    // never raises, never halts. RSS feeds/Public reports are honestly
    // NOT_ARCHITECTED (no real connector exists); Web pages is
    // honestly Claude-session-only (reads the real manual_verification
    // ledger, never an autonomous scraper).
    name: 'evidence-provider-summary',
    description: "Confidence/evidence_count/verification_status/missing_evidence for one real niche, queried across every registered evidence source in the founder's own named priority order. A blocked source (real HTTP 403/429/401) is recorded as BLOCKED, distinct from NOT_ARCHITECTED (no connector exists) and UNKNOWN (connector exists, no credentials) -- confidence only ever rises from a real VERIFIED source, never from a source merely being attempted.",
    reused: 'multi_source_intelligence/coverage.py::prioritized_evidence_summary() (ADR-179) + multi_source_intelligence/manual_verification.py, via mission_control_api.py.',
    reversible: true, // read-only
    kind: 'async',
    asyncRunner: (req) => {
      const niche = (req.body && req.body.niche || '').trim();
      if (!niche) return Promise.reject(new Error('{ niche } is required in the request body'));
      return runPythonActionAsync('evidence-provider-summary', 'prioritized_evidence_summary', [JSON.stringify({ niche })]);
    },
  },
  {
    // Autonomous Business Builder (2026-07-29) -- the real 12-section/
    // 8-estimate Business Blueprint for one niche. Async-job shape
    // (chains production_blueprint + value_engine + investment_score),
    // same precedent as investment-score/convene-galaxy-council.
    name: 'build-business-blueprint',
    description: "The real Business Blueprint: business model, revenue model, customer profile, competitor map, product roadmap, pricing/marketing/distribution strategy, launch checklist, risk assessment, growth plan, automation plan -- reshaping business_dossier.py/production_blueprint.py/capital_allocation_engine.py's already-real output, never a second blueprint generator. 4 of 8 named estimates (monthly/yearly revenue, break-even time, market durability) are honestly Unknown -- zero real signal exists anywhere in this factory for them today.",
    reused: 'autonomous_business_builder.py::business_blueprint()',
    reversible: true, // read-only
    kind: 'async',
    asyncRunner: (req) => {
      const niche = (req.body && req.body.niche || '').trim();
      if (!niche) return Promise.reject(new Error('{ niche } is required in the request body'));
      return runPythonActionAsync('build-business-blueprint', 'business_blueprint', [JSON.stringify({ niche })]);
    },
  },
  {
    // Enterprise Growth Engine (ADR-158, 2026-07-31), Objective 7 --
    // Simulation Mode integration. Every accepted override key
    // replaces exactly one real signal (e.g. total_revenue_usd) with a
    // hypothetical value; growth_stages.py rejects any unknown key.
    // Writes nothing to disk -- a stateless what-if, not a production
    // action, same simulation_mode.py framework as ADR-153.
    name: 'simulate-growth-stage-progression',
    description: "Recomputes the real Growth Stage classification against hypothetical overrides (e.g. { total_revenue_usd: 500 }) instead of real signals -- proves 'what would it take to reach the next stage' without touching production data. Accepts any subset of: accepted_opportunities_count, real_production_runs, total_revenue_usd, open_critical_incidents, launch_readiness, automation_level_pct, quality_score_pct, platforms_with_real_revenue.",
    reused: 'growth_stages.py::simulate_stage_progression() (ADR-158) + simulation_mode.py (ADR-153)',
    reversible: true, // read-only, writes nothing to disk
    kind: 'async',
    asyncRunner: (req) => {
      // Strip the confirmation-gate's own `confirmed` field before
      // forwarding -- growth_stages.py::simulate_stage_progression()
      // rejects any key it doesn't recognize as a real hypothetical
      // override, exactly as designed; `confirmed` is HTTP-layer-only.
      const { confirmed, ...overrides } = req.body || {};
      return runPythonActionAsync('simulate-growth-stage-progression', 'simulate_growth_stage_progression', [JSON.stringify(overrides)]);
    },
  },
  {
    // Enterprise Strategic Planning System (ADR-159, 2026-07-31),
    // Objective 7 -- reuses growth_stages.py's exact overrides
    // mechanism/known-key rejection via simulate_stage_progression().
    // Same confirmed-stripping fix ADR-158's own action just needed.
    name: 'simulate-roadmap-execution',
    description: "Recomputes the real rolling roadmap against a hypothetical Growth Stage (same override keys as simulate-growth-stage-progression) -- proves what the roadmap would look like under hypothetical conditions without touching production data.",
    reused: 'strategic_planning.py::simulate_roadmap_execution() (ADR-159) + growth_stages.py::simulate_stage_progression() (ADR-158) + simulation_mode.py (ADR-153)',
    reversible: true, // read-only, writes nothing to disk
    kind: 'async',
    asyncRunner: (req) => {
      const { confirmed, ...overrides } = req.body || {};
      return runPythonActionAsync('simulate-roadmap-execution', 'simulate_roadmap_execution', [JSON.stringify(overrides)]);
    },
  },
  {
    // Enterprise Digital Twin (ADR-161, 2026-07-31) -- advisory only.
    // Dispatches to one of 5 real, named production action types
    // (digital_twin.py::PREVIEW_ACTIONS); never calls a real
    // approve/reject/publish/reallocate function itself.
    name: 'preview-production-action',
    description: "Real PREVIEW/SIMULATE/ESTIMATE IMPACT/ROLLBACK PLAN for one named production action type (growth_stage_progression, roadmap_execution, affiliate_simulation_cycle, publish, capital_reallocation) -- each honestly discloses which of the 4 it can really provide. Body: { action_type, ...params }. Advisory only.",
    reused: 'digital_twin.py::preview_action() (ADR-161)',
    reversible: true, // read-only, writes nothing to disk
    kind: 'async',
    asyncRunner: (req) => {
      const { confirmed, action_type, ...params } = req.body || {};
      if (!action_type) return Promise.reject(new Error('{ action_type } is required in the request body'));
      return runPythonActionAsync('preview-production-action', 'preview_production_action', [JSON.stringify({ action_type, ...params })]);
    },
  },
  {
    // Market Evidence & Alerting layer (2026-07-23) -- real, on-demand
    // scan (no scheduler exists): auto-detects competitor changes
    // already computed by competitor_discovery.py plus real, human-
    // recorded competitor-landscape events from market_evidence.py,
    // dedupes against the persisted alert log, appends only new ones.
    name: 'scan-market-alerts',
    description: 'Scans for new real competitor alerts for one niche (auto-detected competitor changes + human-recorded competitor-landscape events), dedupes against already-recorded alerts, persists only genuinely new ones. Never fabricates an event.',
    reused: 'market_alerts.py::scan_market_alerts()',
    reversible: true, // append-only alert log; no destructive write
    kind: 'async',
    asyncRunner: (req) => {
      const niche = (req.body && req.body.niche || '').trim();
      if (!niche) return Promise.reject(new Error('{ niche } is required in the request body'));
      return runPythonActionAsync('scan-market-alerts', 'scan_market_alerts', [JSON.stringify({ niche })]);
    },
  },
  {
    name: 'get-market-alerts',
    description: 'Read-only lookup of every real alert already recorded for one niche (Critical/High/Medium/Low), grouped by severity. Never triggers a new scan.',
    reused: 'market_alerts.py::get_active_alerts()',
    reversible: true,
    kind: 'async',
    asyncRunner: (req) => {
      const niche = (req.body && req.body.niche || '').trim();
      if (!niche) return Promise.reject(new Error('{ niche } is required in the request body'));
      return runPythonActionAsync('get-market-alerts', 'get_market_alerts', [JSON.stringify({ niche })]);
    },
  },
  {
    // Decision Re-open Trigger (2026-07-23) -- read-only: would this
    // niche's board decision be reopened right now, given whatever real
    // alerts are already active? Never convenes a new meeting.
    name: 'check-decision-reopen-trigger',
    description: 'Read-only: would this niche\'s board decision be reopened right now, given real alerts already active? Never convenes a new meeting.',
    reused: 'decision_reopen.py::check_for_reopen_trigger()',
    reversible: true,
    kind: 'async',
    asyncRunner: (req) => {
      const niche = (req.body && req.body.niche || '').trim();
      if (!niche) return Promise.reject(new Error('{ niche } is required in the request body'));
      return runPythonActionAsync('check-decision-reopen-trigger', 'check_decision_reopen_trigger', [JSON.stringify({ niche })]);
    },
  },
  {
    // Decision Re-open Trigger (2026-07-23) -- the one real, on-demand
    // entrypoint: real alert scan, then reopens the board's decision for
    // this niche ONLY if that scan finds a materially new Critical alert
    // (or 2+ new High alerts) since the last real board meeting. Never
    // reopens on speculation -- see decision_reopen.py's own docstring
    // for the full deterministic rule.
    name: 'scan-and-maybe-reopen-decision',
    description: 'Real alert scan, then reopens this niche\'s board decision ONLY if materially warranted (1+ new Critical alert or 2+ new High alerts since the last meeting). Records a permanent reopen event with timestamp, reason, previous decision, new evidence, confidence delta, and the new board outcome.',
    reused: 'decision_reopen.py::scan_and_maybe_reopen()',
    reversible: true, // append-only reopen log + a new append-only board meeting; the previous meeting is never mutated
    kind: 'async',
    asyncRunner: (req) => {
      const niche = (req.body && req.body.niche || '').trim();
      if (!niche) return Promise.reject(new Error('{ niche } is required in the request body'));
      return runPythonActionAsync('scan-and-maybe-reopen-decision', 'scan_and_maybe_reopen_decision', [JSON.stringify({ niche })]);
    },
  },
  {
    name: 'get-decision-reopen-history',
    description: 'Read-only: the full real, permanent audit trail of every real reopen event for one niche.',
    reused: 'decision_reopen.py::get_reopen_history()',
    reversible: true,
    kind: 'async',
    asyncRunner: (req) => {
      const niche = (req.body && req.body.niche || '').trim();
      if (!niche) return Promise.reject(new Error('{ niche } is required in the request body'));
      return runPythonActionAsync('get-decision-reopen-history', 'get_decision_reopen_history', [JSON.stringify({ niche })]);
    },
  },
  {
    // Galaxy Forge Value Engine (2026-07-23) -- read-only per-niche synthesis:
    // Priority Score, Expected ROI, Strategic Value, cost/lifetime-value
    // estimates, Recommendation, and all 17 requested dimensions. Reuses
    // opportunity_pipeline.py/revenue_pipeline/plan.py/market_evidence.py
    // directly -- never a second, competing scoring system.
    name: 'get-value-profile',
    description: 'Read-only: the real Value Engine profile for one niche (Priority Score, Expected ROI, Strategic Value, Estimated Build/Maintenance Cost, Estimated Lifetime Value, Recommendation, and all 17 requested dimensions). Null when the niche has no real ACCEPTED decision.',
    reused: 'value_engine.py::compute_value_profile()',
    reversible: true,
    kind: 'async',
    asyncRunner: (req) => {
      const niche = (req.body && req.body.niche || '').trim();
      if (!niche) return Promise.reject(new Error('{ niche } is required in the request body'));
      return runPythonActionAsync('get-value-profile', 'get_value_profile', [JSON.stringify({ niche })]);
    },
  },
  {
    // Galaxy Forge Value Engine (2026-07-23) -- the real, automatic resource-
    // allocation output: every real ACCEPTED opportunity, ranked by real
    // Priority Score descending.
    name: 'get-value-engine-report',
    description: 'Read-only: every real ACCEPTED opportunity (Product Laboratory), each with a full Value Engine profile, ranked by real Priority Score descending -- the real resource-allocation view.',
    reused: 'value_engine.py::build_value_engine_report()',
    reversible: true,
    kind: 'async',
    asyncRunner: () => runPythonActionAsync('get-value-engine-report', 'get_value_engine_report', []),
  },
  {
    // Global Market Learning Engine (2026-07-23) -- real Market Memory
    // aggregate for one niche. Honestly empty until real sales exist.
    name: 'get-niche-commercial-profile',
    description: 'Read-only: the real Market Memory commercial profile for one niche (sample size, real revenue to date, average price, platforms, seasons sold in). Honestly empty until real sales exist for it.',
    reused: 'market_memory.py::niche_commercial_profile()',
    reversible: true,
    kind: 'async',
    asyncRunner: (req) => {
      const niche = (req.body && req.body.niche || '').trim();
      if (!niche) return Promise.reject(new Error('{ niche } is required in the request body'));
      return runPythonActionAsync('get-niche-commercial-profile', 'get_niche_commercial_profile', [JSON.stringify({ niche })]);
    },
  },
  {
    // Global Market Learning Engine (2026-07-23) -- the founder-named
    // monthly report, gated on a real minimum sample size.
    name: 'get-monthly-market-evolution-report',
    description: 'Read-only: top growing niches, best platforms, and related monthly commercial trends, computed only from real closed sales. Honestly reports insufficient data below the real minimum sample size, never a fabricated trend.',
    reused: 'market_memory.py::monthly_evolution_report()',
    reversible: true,
    kind: 'async',
    asyncRunner: () => runPythonActionAsync('get-monthly-market-evolution-report', 'get_monthly_market_evolution_report', []),
  },
  {
    // Global Market Learning Engine (2026-07-23) -- evidence-gated
    // autonomous recommendations. Empty list is the correct output
    // while real sales are scarce, never a fabricated suggestion.
    name: 'get-commercial-recommendations',
    description: 'Read-only: evidence-gated commercial recommendations (increase investment, review pricing) -- only emitted once a niche has enough real closed sales to support one. Empty while evidence is scarce.',
    reused: 'market_memory.py::recommend_actions()',
    reversible: true,
    kind: 'async',
    asyncRunner: () => runPythonActionAsync('get-commercial-recommendations', 'get_commercial_recommendations', []),
  },
  {
    // Autonomous Global Execution Engine (2026-07-23) -- Mission
    // Control's single operational window. Assembled entirely from
    // already-real sources on the Python side (execution_status.py,
    // scheduler.py, market_memory.py, ai_capability), merged here with
    // the real, already-live computeHealthStatus() this server already
    // has synchronously -- never a second health computation.
    name: 'get-global-execution-view',
    description: 'Read-only: the single unified operational view (execution status, real scheduling buckets, revenue, production, market learning, AI utilization, health) -- every field reused from an already-real, already-tested source, nothing recomputed. Optional { limit } caps how many opportunities get a full execution-status profile (scheduling always covers every real opportunity, unlimited).',
    reused: 'mission_control_api.py::_get_global_execution_view() + computeHealthStatus()',
    reversible: true,
    kind: 'async',
    asyncRunner: async (req) => {
      const limit = req.body && Number.isFinite(req.body.limit) ? req.body.limit : undefined;
      const view = await runPythonActionAsync('get-global-execution-view', 'get_global_execution_view', [JSON.stringify({ limit })]);
      let health;
      try {
        health = await computeHealthStatus();
      } catch (e) {
        health = { error: e.message };
      }
      return { ...view, health };
    },
  },
  {
    // Global Growth Engine (2026-07-24) -- real Product Multiplication +
    // Channel Expansion for one real ACCEPTED niche.
    name: 'get-growth-report',
    description: 'Read-only: the real Product Multiplication (premium/subscription/bundle/API/SaaS candidates, each honestly available or not) and Channel Expansion evaluation for one niche. Null when the niche has no real ACCEPTED decision.',
    reused: 'growth_engine.py::build_growth_report()',
    reversible: true,
    kind: 'async',
    asyncRunner: (req) => {
      const niche = (req.body && req.body.niche || '').trim();
      if (!niche) return Promise.reject(new Error('{ niche } is required in the request body'));
      return runPythonActionAsync('get-growth-report', 'get_growth_report', [JSON.stringify({ niche })]);
    },
  },
  {
    // Global Growth Engine (2026-07-24) -- real, factory-wide channel
    // readiness across the 10 founder-named channels.
    name: 'get-channel-expansion-status',
    description: 'Read-only: real channel readiness across the 10 founder-named channels -- live arms referenced from channels/registry.py, everything else an honest env-var-based catalog entry, never a live test-connection call.',
    reused: 'growth_engine.py::evaluate_channel_expansion()',
    reversible: true,
    kind: 'async',
    asyncRunner: () => runPythonActionAsync('get-channel-expansion-status', 'get_channel_expansion_status', []),
  },
  {
    // Real World Commercial Expansion (2026-07-24) -- the real, unified
    // Commercial Intelligence report for one niche.
    name: 'get-commercial-intelligence-report',
    description: 'Read-only: the real Commercial Intelligence report for one niche (demand, willingness to pay, competition, price ranges, buying behavior, product opportunities, customer pain). regional_differences always honestly unavailable -- no real country-level data exists in this factory today. Null when the niche has no real decision on record.',
    reused: 'commercial_intelligence.py::build_commercial_intelligence_report()',
    reversible: true,
    kind: 'async',
    asyncRunner: (req) => {
      const niche = (req.body && req.body.niche || '').trim();
      if (!niche) return Promise.reject(new Error('{ niche } is required in the request body'));
      return runPythonActionAsync('get-commercial-intelligence-report', 'get_commercial_intelligence_report', [JSON.stringify({ niche })]);
    },
  },
  {
    // Real World Commercial Expansion, Priority 3 (2026-07-24) -- real
    // status of the 7 named premium categories + the real pricing-
    // ceiling finding.
    name: 'get-premium-product-catalog-status',
    description: 'Read-only: real status of the 7 founder-named $100-$5000 premium categories against this factory\'s actual product family adapters, plus a disclosed real finding -- the live pricing ceiling (elite band, $497) is well below the mission\'s own stated $5000 ambition; raising it is a real pricing-policy decision for the founder, not made here.',
    reused: 'growth_engine.py::premium_product_catalog_status()',
    reversible: true,
    kind: 'async',
    asyncRunner: () => runPythonActionAsync('get-premium-product-catalog-status', 'get_premium_product_catalog_status', []),
  },
  {
    // Global Revenue Discovery Engine (2026-07-24) -- real, unified
    // Investment Pipeline entry for one niche.
    name: 'get-investment-pipeline-entry',
    description: 'Read-only: the real Investment Pipeline entry for one niche (10 ranking dimensions -- market size, competition, urgency, willingness to pay, production difficulty, long-term strategic value, defensibility, recurring revenue potential, global scalability, AI leverage -- plus 12 named commercial fields). country_priority always honestly deferred. Null when the niche has no real decision on record.',
    reused: 'investment_pipeline.py::build_investment_pipeline_entry()',
    reversible: true,
    kind: 'async',
    asyncRunner: (req) => {
      const niche = (req.body && req.body.niche || '').trim();
      if (!niche) return Promise.reject(new Error('{ niche } is required in the request body'));
      return runPythonActionAsync('get-investment-pipeline-entry', 'get_investment_pipeline_entry', [JSON.stringify({ niche })]);
    },
  },
  {
    // Global Revenue Discovery Engine (2026-07-24) -- the real, whole-
    // factory Investment Pipeline.
    name: 'get-investment-pipeline',
    description: 'Read-only: every real decision (any status) as a full Investment Pipeline entry, ranked by real opportunity_score descending. Optional { limit } caps how many full entries get built.',
    reused: 'investment_pipeline.py::build_investment_pipeline()',
    reversible: true,
    kind: 'async',
    asyncRunner: (req) => {
      const limit = req.body && Number.isFinite(req.body.limit) ? req.body.limit : undefined;
      return runPythonActionAsync('get-investment-pipeline', 'get_investment_pipeline', [JSON.stringify({ limit })]);
    },
  },
  {
    // Global Product Portfolio Engine (2026-07-24) -- real 13-class
    // portfolio entry for one niche.
    name: 'get-portfolio-entry',
    description: 'Read-only: the real portfolio entry for one niche -- 13-class classification (Premium SaaS, AI Agents, AI APIs, Enterprise Automation, Premium Digital Products, Online Courses, Bundles, Templates, AI Prompt Packs, Design Assets, Stock Images, Fonts/Icons/SVG Packs, Books), NOW/NEXT/LATER/REJECT bucket (reused from scheduler.py), and the founder-named metrics. Null when the niche has no real decision on record.',
    reused: 'portfolio_engine.py::build_portfolio_entry()',
    reversible: true,
    kind: 'async',
    asyncRunner: (req) => {
      const niche = (req.body && req.body.niche || '').trim();
      if (!niche) return Promise.reject(new Error('{ niche } is required in the request body'));
      return runPythonActionAsync('get-portfolio-entry', 'get_portfolio_entry', [JSON.stringify({ niche })]);
    },
  },
  {
    // Global Product Portfolio Engine (2026-07-24) -- the real
    // Executive Board portfolio view.
    name: 'get-portfolio-report',
    description: 'Read-only: the real Executive Board portfolio view -- Top 100 worldwide, Top 25 enterprise, Top 25 recurring revenue, ordered by real founder-specified class priority then real Priority Score. Top 50 China always honestly empty -- no real China data connector exists in this factory today.',
    reused: 'portfolio_engine.py::build_portfolio_report()',
    reversible: true,
    kind: 'async',
    asyncRunner: () => runPythonActionAsync('get-portfolio-report', 'get_portfolio_report', []),
  },
  {
    // Global Product Factory (2026-07-24) -- real 15-component
    // Production Blueprint for one niche.
    name: 'get-production-blueprint',
    description: 'Read-only: the real 15-component Production Blueprint for one niche (spec, architecture, persona, pain map, competitive analysis, UVP, pricing, brand position, checklist, required AI models, human review points, distribution, marketing assets, sales funnel, revenue projection) plus its real production pipeline and status. Null when the niche has no real decision on record.',
    reused: 'production_blueprint.py::build_production_blueprint()',
    reversible: true,
    kind: 'async',
    asyncRunner: (req) => {
      const niche = (req.body && req.body.niche || '').trim();
      if (!niche) return Promise.reject(new Error('{ niche } is required in the request body'));
      return runPythonActionAsync('get-production-blueprint', 'get_production_blueprint', [JSON.stringify({ niche })]);
    },
  },
  {
    // Global Product Factory (2026-07-24) -- Mission Control's real
    // continuous production-status board.
    name: 'get-production-missions-board',
    description: 'Read-only: every real ACCEPTED opportunity bucketed under the 6 named production states (READY TO BUILD, BUILDING, QUALITY REVIEW, READY TO SELL, LIVE, LEARNING) -- reused from value_engine.classify_lifecycle_stage() and inspectors.py\'s real quarantine record, never a new state machine.',
    reused: 'production_blueprint.py::build_production_missions_board()',
    reversible: true,
    kind: 'async',
    asyncRunner: () => runPythonActionAsync('get-production-missions-board', 'get_production_missions_board', []),
  },
  {
    // Complete Autonomous Company Master Loop (2026-07-24) -- real
    // 20-named-stage evidence trace for one niche. Pure orchestration
    // over already-real modules, per the directive's own explicit
    // "do not create another isolated engine" rule.
    name: 'get-lifecycle-trace',
    description: 'Read-only: the real 20-named-stage evidence trace for one niche (Global Opportunity Discovery through Automatic Discovery of Next Opportunity), each stage naming its real owning module. Several stages share the same underlying real signal, reported honestly rather than split into fabricated independent booleans. Null when the niche has no real decision on record.',
    reused: 'master_loop.py::trace_lifecycle()',
    reversible: true,
    kind: 'async',
    asyncRunner: (req) => {
      const niche = (req.body && req.body.niche || '').trim();
      if (!niche) return Promise.reject(new Error('{ niche } is required in the request body'));
      return runPythonActionAsync('get-lifecycle-trace', 'get_lifecycle_trace', [JSON.stringify({ niche })]);
    },
  },
  {
    // Complete Autonomous Company Master Loop (2026-07-24) -- the real
    // 6-field Mission Control heartbeat.
    name: 'get-mission-control-heartbeat',
    description: 'Read-only: the real 6-field heartbeat (Current Opportunity, Current Product, Current Stage, Current Revenue, Current Learning, Current Next Action) -- thin reuse of scheduler.py\'s real run_now pick, production_blueprint.py, and this server\'s own revenue action. On-demand only, never a live process.',
    reused: 'master_loop.py::mission_control_heartbeat()',
    reversible: true,
    kind: 'async',
    asyncRunner: () => runPythonActionAsync('get-mission-control-heartbeat', 'get_mission_control_heartbeat', []),
  },
  {
    // Reality Mode (2026-07-24) -- the real, transparent Company
    // Reality Score. Every 4-level evidence taxonomy field this
    // directive named (VERIFIED_REALITY/ESTIMATED/SIMULATED/UNKNOWN)
    // is available via reality_mode.py for any future action; this is
    // the one dedicated, dashboard-facing score.
    name: 'get-company-reality-score',
    description: 'Read-only: the real, transparent Company Reality Score -- share of real ACCEPTED opportunities backed by at least one real external evidence source (a real sale, real market evidence, a real cached competitor snapshot, a real board meeting). Built entirely from real counts, all disclosed alongside the score. Increases only when real evidence increases.',
    reused: 'reality_mode.py::compute_company_reality_score()',
    reversible: true,
    kind: 'async',
    asyncRunner: () => runPythonActionAsync('get-company-reality-score', 'get_company_reality_score', []),
  },
  {
    // Global CEO Decision Center (2026-07-24) -- real, evidence-based
    // answers to the 10 named CEO questions. Pure orchestration over
    // investment_pipeline.py/scheduler.py/production_blueprint.py/
    // competitor_discovery.py/ai_capability.orchestrator.py.
    name: 'get-ceo-questions',
    description: 'Read-only: real answers to the 10 named CEO questions (most profitable opportunity, opportunity to abandon, deserves more investment, country priority, saturating market, strengthening niche, best AI model per department, highest real ROI products, wasted production pipelines, next commercial experiment). Country question always honestly deferred.',
    reused: 'ceo_decision_center.py::answer_ceo_questions()',
    reversible: true,
    kind: 'async',
    asyncRunner: () => runPythonActionAsync('get-ceo-questions', 'get_ceo_questions', []),
  },
  {
    // Global CEO Decision Center (2026-07-24) -- real, descriptive
    // capital allocation snapshot across the 10 named functions.
    name: 'get-capital-allocation-snapshot',
    description: 'Read-only: a real, descriptive snapshot of where real opportunities/evidence currently concentrate across the 10 named functions (Research, Production, Automation, Marketing, Publishing, Sales, Commercial Intelligence, China Division, Enterprise Division, Premium Products) -- real counts only, never a fabricated dollar budget.',
    reused: 'ceo_decision_center.py::capital_allocation_snapshot()',
    reversible: true,
    kind: 'async',
    asyncRunner: () => runPythonActionAsync('get-capital-allocation-snapshot', 'get_capital_allocation_snapshot', []),
  },
  {
    // Global CEO Decision Center (2026-07-24) -- the real 8-field CEO
    // dashboard.
    name: 'get-ceo-dashboard',
    description: 'Read-only: the real 8-field CEO dashboard (Company Health, Capital Allocation, Growth Rate, Revenue Trend, Top Opportunities, Top Risks, Current Strategic Priority, Next Executive Decision) -- thin reuse only, Company Health referenced from GET /health rather than re-derived.',
    reused: 'ceo_decision_center.py::ceo_dashboard()',
    reversible: true,
    kind: 'async',
    asyncRunner: () => runPythonActionAsync('get-ceo-dashboard', 'get_ceo_dashboard', []),
  },
  {
    // Build in Public (2026-07-24) -- real, honest-numbers-only weekly
    // progress report.
    name: 'get-weekly-progress-report',
    description: 'Read-only: the real weekly progress report (opportunities scored/accepted/rejected, real revenue) in English, honest numbers only, no hype language.',
    reused: 'build_in_public.py::build_weekly_progress_report()',
    reversible: true,
    kind: 'async',
    asyncRunner: () => runPythonActionAsync('get-weekly-progress-report', 'get_weekly_progress_report', []),
  },
  {
    // Build in Public (2026-07-24) -- real AI-generated public post
    // draft from one real ADR. Never auto-published.
    name: 'draft-adr-post',
    description: 'Generates a real AI-drafted public post from one real ADR file (never auto-published -- returns the draft for review/queuing). Uses real Groq API calls; subject to real rate limits.',
    reused: 'build_in_public.py::draft_adr_post()',
    reversible: true,
    kind: 'async',
    asyncRunner: (req) => {
      const adrPath = (req.body && req.body.adr_path || '').trim();
      if (!adrPath) return Promise.reject(new Error('{ adr_path } is required in the request body'));
      return runPythonActionAsync('draft-adr-post', 'draft_adr_post', [JSON.stringify({ adr_path: adrPath })]);
    },
  },
  {
    // Build in Public (2026-07-24) -- writes a real draft to a real
    // pending-review file and sends a real Arabic Telegram approval
    // notification. Never auto-publishes anything.
    name: 'queue-draft-for-approval',
    description: 'Writes a real draft (weekly report or ADR post) to a real pending-review file and sends a real Arabic Telegram notification for the founder\'s approval. Never publishes anything automatically.',
    reused: 'build_in_public.py::queue_draft_for_approval()',
    reversible: true,
    kind: 'async',
    asyncRunner: (req) => {
      const body = req.body || {};
      for (const field of ['draft_type', 'title', 'content_markdown', 'telegram_summary_arabic']) {
        if (!body[field] || !String(body[field]).trim()) {
          return Promise.reject(new Error(`{ ${field} } is required in the request body`));
        }
      }
      return runPythonActionAsync('queue-draft-for-approval', 'queue_draft_for_approval', [JSON.stringify(body)]);
    },
  },
  {
    // Factory Master Orchestrator (Full Architecture Review, 2026-07-22)
    // -- the single real call composing Executive Quality Gate + AI
    // Executive Board (which itself calls Enterprise Readiness) +
    // Revenue Pipeline production, instead of 3+ separate manual
    // actions. advisory_only by default: the Board's verdict is
    // reported but does not block a real execute=true production run.
    name: 'run-master-cycle',
    description: 'Runs the full real governance + production chain for one already-accepted niche in a single call: Quality Gate, Executive Board, and (if execute=true) real production. Board verdict is advisory unless enforce_board=true.',
    reused: 'factory_orchestrator.py (Full Architecture Review)',
    reversible: true, // read-only evaluation unless execute=true is explicitly passed, which reuses run_cycle's own existing safety switch
    kind: 'async',
    asyncRunner: (req) => {
      const { niche, execute, enforce_board } = req.body || {};
      if (!niche) return Promise.reject(new Error('{ niche } is required in the request body'));
      return runPythonActionAsync('run-master-cycle', 'run_master_cycle', [JSON.stringify({ niche, execute: !!execute, enforce_board: !!enforce_board })]);
    },
  },
  {
    name: 'run-validation',
    description: 'Generates the real daily validation report (opportunities, bottlenecks, stalled items, reliability, recommendations).',
    reused: 'validation_layer/daily_report.py (ADR-053)',
    reversible: true,
    kind: 'sync',
    section: 'validation_report',
  },
  {
    name: 'export-executive-report',
    description: 'Combines the validation report and the CEO revenue report into one markdown file under reports/.',
    reused: 'validation_layer/daily_report.py + revenue_pipeline/pipeline.py',
    reversible: true, // only ever adds a new timestamped file, never overwrites
    kind: 'sync',
    section: 'export_executive_report',
  },
  {
    name: 'request-ai-capability',
    description: 'Logs a real department request for a different/better AI model, plus the current honest recommendation for that task type. Requires { department, task_type, requested_provider } in the request body.',
    reused: 'ai_capability/registry.py record_capability_request() + evaluator.py recommend_for_task() (Autonomous Digital Company v1, Track B2, 2026-07-19)',
    reversible: true, // append-only log entry, never an autonomous model switch
    kind: 'sync',
    run: requestAiCapabilityAction,
  },
  {
    name: 'run-full-cycle',
    description: 'Runs one complete, deliberate pass through the full business lifecycle (Market Intelligence -> Decision Engine -> Production -> Quality Validation -> Executive Reports -> Learning -> Knowledge Base update), plus a Company Health/Automation/Security monitoring snapshot. A manually-triggered orchestration, not an unattended scheduler — this factory has no scheduler by design (CLAUDE.md), to keep paid-API calls and production/publish actions under explicit human control. Every stage is independently graceful-degraded: one stage failing never blocks the rest.',
    reused: 'real_world_mode/operating_mode.py, production_factory/factory.py, validation_layer/daily_report.py, revenue_pipeline/pipeline.py, decision_engine/feedback.py+learning.py, mission_control_api.py\'s _automation() — every stage reuses an already-built module, nothing new.',
    reversible: true, // read/append only — no destructive action, no real publish, no real spend beyond what the reused modules already do
    kind: 'async',
    asyncRunner: () => runFullCycleActionAsync('run-full-cycle'),
  },
  {
    // Autonomous Company Evolution Engine, Round 6 (2026-07-29): the
    // founder's real approval -- the one concrete code enforcement of
    // "human-gated always" for Execute (see the plan's Architecture
    // decisions). Requires { proposal_id } in the request body.
    name: 'approve-evolution-proposal',
    description: 'Moves a real Evolution Queue proposal from AWAITING_FOUNDER_APPROVAL to APPROVED. Requires { proposal_id } in the request body, optional { note }. Never fired automatically -- factory_loop.js only ever runs intake/simulate/decide.',
    reused: 'evolution_queue.py approve_proposal() (Round 1)',
    reversible: false, // a real founder decision, permanently recorded in stage_history
    kind: 'sync',
    run: approveEvolutionProposalAction,
  },
  {
    name: 'reject-evolution-proposal',
    description: 'Moves a real Evolution Queue proposal from AWAITING_FOUNDER_APPROVAL to REJECTED. Requires { proposal_id } in the request body, optional { reason }.',
    reused: 'evolution_queue.py reject_proposal() (Round 1)',
    reversible: false,
    kind: 'sync',
    run: rejectEvolutionProposalAction,
  },
  {
    // Global Trust & Resilience Layer, Round 2 (2026-07-29).
    name: 'approve-commission-opportunity',
    description: 'CEO Commercial Control (ADR-226, Section 17): approves a real commission opportunity into its next real pipeline stage. Requires { opportunity_id, from_state, to_state } in the request body, optional { evidence }. Creates a real, append-only audit event -- never silently advances a stage without a human-triggered call.',
    reused: 'commission_engine.py record_pipeline_transition()',
    reversible: false,
    kind: 'sync',
    run: approveCommissionOpportunityAction,
  },
  {
    name: 'reject-commission-opportunity',
    description: 'CEO Commercial Control: rejects a real commission opportunity. Requires { opportunity_id, from_state } in the request body, optional { reason }.',
    reused: 'commission_engine.py record_pipeline_transition()',
    reversible: false,
    kind: 'sync',
    run: rejectCommissionOpportunityAction,
  },
  {
    name: 'mark-subsystem-unstable',
    description: 'Isolates one real, named subsystem (ai_generation or market_intelligence) without halting the rest of the company. Requires { name, reason } in the request body. marketplace_publishing is not accepted here -- use publish-emergency-stop instead.',
    reused: 'safe_mode.py mark_subsystem_unstable() (Global Trust & Resilience Layer, Round 2)',
    reversible: true,
    kind: 'sync',
    run: markSubsystemUnstableAction,
  },
  {
    name: 'clear-subsystem-unstable',
    description: 'Reverses mark-subsystem-unstable. Requires { name } in the request body.',
    reused: 'safe_mode.py clear_subsystem_unstable() (Global Trust & Resilience Layer, Round 2)',
    reversible: true,
    kind: 'sync',
    run: clearSubsystemUnstableAction,
  },
  {
    name: 'mark-evolution-proposal-implemented',
    description: 'Closes the loop after a real, separately-reviewed Claude Code session has actually shipped an APPROVED proposal. Requires { proposal_id } in the request body, optional { note }. Requires the proposal to already be APPROVED -- can never be used to skip founder review.',
    reused: 'evolution_queue.py mark_implemented() (Round 1)',
    reversible: false,
    kind: 'sync',
    run: markEvolutionProposalImplementedAction,
  },
];
const ACTION_BY_NAME = new Map(ACTION_REGISTRY.map(a => [a.name, a]));

function triggerAction(action, req) {
  if (action.kind === 'async') {
    // asyncRunner lets one action (run-full-cycle) use a bespoke runner
    // instead of the generic single-Python-call one, without changing
    // runPythonActionAsync's signature for every other async action.
    const runner = action.asyncRunner || (() => runPythonActionAsync(action.name, action.section));
    return Promise.resolve(runner(req));
  }
  if (action.section) {
    return runActionSync(action.name, () => runPythonService(action.section), req);
  }
  return runActionSync(action.name, action.run, req);
}

v1Router.get('/actions', (req, res) => {
  const jobs = [...ACTION_JOBS.values()]
    .sort((a, b) => b.started_at.localeCompare(a.started_at))
    .slice(0, 50)
    .map(({ id, action, status, started_at, finished_at, error }) => ({ id, action, status, started_at, finished_at, error }));
  res.json({
    success: true,
    version: 'v1',
    generated_at: new Date().toISOString(),
    actions: ACTION_REGISTRY.map(a => ({ name: a.name, description: a.description, reused: a.reused || null, reversible: a.reversible, kind: a.kind })),
    recent_jobs: jobs,
  });
});

v1Router.get('/actions/:id', (req, res) => {
  const job = ACTION_JOBS.get(req.params.id);
  if (!job) {
    return res.status(404).json({ success: false, version: 'v1', error: { code: 'unknown_job', message: `no such job: ${req.params.id}` } });
  }
  res.json({ success: true, version: 'v1', job });
});

// Single-writer guard (Phase 10A — Production Stability): refuses to start
// a second run of the SAME action while one is still 'running'. This is a
// real gap Phase 9 left open — nothing previously stopped two overlapping
// triggers of e.g. rerun-market-analysis from spawning two Python
// subprocesses that both call orchestrator.run_cycle() and append to the
// same shared files (data/decisions.jsonl, data/orchestrator_timeline.jsonl)
// at once. factory_loop.js's own PID lockfile already gives it single-writer
// safety for its own process; this is the equivalent guard for actions
// triggered through Mission Control.
function isActionRunning(actionName) {
  for (const job of ACTION_JOBS.values()) {
    if (job.action === actionName && job.status === 'running') return job;
  }
  return null;
}

v1Router.post('/actions/:name', async (req, res) => {
  const action = ACTION_BY_NAME.get(req.params.name);
  if (!action) {
    return res.status(404).json({ success: false, version: 'v1', error: { code: 'unknown_action', message: `no such action: ${req.params.name}` } });
  }
  if (!req.body || req.body.confirmed !== true) {
    return res.status(400).json({ success: false, version: 'v1', error: { code: 'confirmation_required', message: 'this action requires { "confirmed": true } in the request body' } });
  }
  const alreadyRunning = isActionRunning(action.name);
  if (alreadyRunning) {
    return res.status(409).json({
      success: false, version: 'v1',
      error: { code: 'action_already_running', message: `${action.name} is already running (job ${alreadyRunning.id}, started ${alreadyRunning.started_at})` },
    });
  }
  try {
    const job = await triggerAction(action, req);
    logServiceCall({ service: 'actions', action: action.name, job_id: job.id, event: 'requested', status: job.status });
    res.json({ success: true, version: 'v1', job });
  } catch (err) {
    logServiceCall({ service: 'actions', action: action.name, event: 'request_failed', error: err.message });
    res.status(500).json({ success: false, version: 'v1', error: { code: 'action_dispatch_failed', message: err.message } });
  }
});

// Any /api/v1/* path that matched none of the registered services above
// must 404 as JSON — without this, it would otherwise fall through past
// this router entirely and hit the SPA catch-all route at the bottom of
// this file, returning a 200 HTML page for a bad API call.
v1Router.use((req, res) => {
  res.status(404).json({ success: false, version: 'v1', error: { code: 'unknown_service', message: `no such service: ${req.path}` } });
});

app.use('/api/v1', requireMissionControlAuth, v1Router);

// Superseded by /api/v1/* above but kept working: mission_control.html
// (Phase 8 Mission Control) still calls this ad hoc catch-all directly.
// Rewiring its fetch() calls to the versioned services is deliberately
// deferred — this directive was backend-only ("No UI work yet").
// Refactored to share runPythonService() with the v1 layer instead of
// its own inline spawn/parse block, so there is no duplicated glue code.
const MISSION_CONTROL_ENDPOINTS = ['opportunities', 'production', 'revenue', 'automation'];
app.get('/api/mission-control/:section', requireMissionControlAuth, async (req, res) => {
  const section = req.params.section;
  if (!MISSION_CONTROL_ENDPOINTS.includes(section)) {
    return res.status(404).json({ success: false, error: `unknown section: ${section}` });
  }
  try {
    const result = await runPythonService(section);
    res.json(result);
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

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

app.post('/api/safety/check', requireMissionControlAuth, async (req, res) => {
  try {
    const result = await runSafetyCheck(req.body || {});
    res.json({ success: true, ...result });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// ── GENERATE BOOK ──
app.post('/generate-book', requireMissionControlOrInternalToken, async (req, res) => {
  // `output` is destructured as `outputName` to avoid colliding with the
  // `output`/`errOut` stdout-accumulator variables used below.
  const { title, subtitle, type, theme, pages, author, topic, chapters, audience, price, product_type, sections, output: outputName } = req.body;

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

    // ADR-071 (mission follow-up, 2026-07-18): with product_type:"techdoc"
    // (factory_loop.js's briefFromGoldenOpportunity(), a ladder-tagged
    // Golden Hunter pick, MASTER_CHARTER.md §2), route to
    // book_generator.generate_product_package() — the technical-docs/
    // product-package generator — instead of the AI-generated-book path.
    // `sections` passes through only when the caller supplies its own
    // (Array.isArray guard so a stray non-array value never reaches
    // book_generator.py); otherwise generate_product_package() fills its
    // own default section skeleton. Checked BEFORE the `topic` branch
    // below so a techdoc request (which also carries a `topic`, for
    // content context) doesn't fall into the AI-book path instead.
    const payload = product_type === 'techdoc'
      ? JSON.stringify({
          title,
          subtitle: subtitle || '',
          product_type: 'techdoc',
          topic: topic || title,
          price: price != null ? price : 197,
          theme: theme || 'blue',
          author: author || '',
          output: filename,
          ...(Array.isArray(sections) ? { sections } : {}),
        })
      // With a `topic`, route to the real AI content engine (generate_book());
      // otherwise keep the original fixed-template path exactly as before.
      : topic
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

    let output = '', errOut = '', timedOut = false;
    killAfterTimeout(python, PYTHON_GENERATE_BOOK_TIMEOUT_MS, () => { timedOut = true; });
    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.stdin.write(payload);
    python.stdin.end();

    python.on('close', code => {
      if (timedOut) {
        return res.status(504).json({ success: false, error: `book_generator.py timed out after ${PYTHON_GENERATE_BOOK_TIMEOUT_MS}ms` });
      }
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
    systemPrompt: COMPANY_PERSONALITY_PREAMBLE + AGENT_PROMPTS.publisher.system,
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

app.post('/api/distribute', requireMissionControlOrInternalToken, async (req, res) => {
  const { record, arms } = req.body || {};

  if (!record || typeof record !== 'object' || Array.isArray(record)) {
    return res.status(400).json({ success: false, error: 'record (a JSONL production-log record) is required' });
  }
  if (arms !== undefined && !Array.isArray(arms)) {
    return res.status(400).json({ success: false, error: 'arms must be an array of arm names, if provided' });
  }

  const dryRun = req.body.dry_run === false ? false : true;

  // Restores the pre-refactor 404 for a missing distributor.py — the
  // runDistributor() helper itself just rejects with a generic Error for
  // this case (it has no HTTP status opinion, correctly), so the specific
  // "misconfigured deployment" status has to be checked here, same as
  // /api/sales/poll already does for its own script.
  const distributorScript = path.join(__dirname, 'distributor.py');
  if (!fs.existsSync(distributorScript)) {
    return res.status(404).json({ success: false, error: 'distributor.py not found' });
  }

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
app.post('/api/sales/poll', requireMissionControlOrInternalToken, (req, res) => {
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

  let output = '', errOut = '', responded = false, timedOut = false;
  killAfterTimeout(python, PYTHON_SALES_POLL_TIMEOUT_MS, () => { timedOut = true; });
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
    if (timedOut) {
      return res.status(504).json({ success: false, error: `poll_sales.py timed out after ${PYTHON_SALES_POLL_TIMEOUT_MS}ms` });
    }
    try {
      const result = JSON.parse(output.trim());
      res.json(result);
      // ADR-085: "Sale made" was one of ADR-073's 3 named-but-unwired
      // Telegram categories (no notification hook existed anywhere in this
      // path). One real, summary message per poll run — never one per
      // individual sale, so a multi-sale poll can't spam the founder.
      // Fire-and-forget: a slow/unreachable Telegram must never delay this
      // response, which has already been sent above.
      if (result.success && (result.new_sale_details || []).length > 0) {
        const details = result.new_sale_details;
        const total = details.reduce((sum, d) => sum + (d.amount || 0), 0);
        const byPlatform = {};
        for (const d of details) byPlatform[d.platform] = (byPlatform[d.platform] || 0) + 1;
        const platformLine = Object.entries(byPlatform).map(([p, c]) => `${p} (${c})`).join('، ');
        const lines = ['💰 بيع جديد!', '', `عدد العمليات: ${details.length}`, `المنصة: ${platformLine}`];
        if (total > 0) lines.push(`الإجمالي: $${total.toFixed(2)}`);
        telegramDirect.sendTelegramMessage(lines.join('\n')).catch(() => {});
      }
    } catch {
      res.json({ success: false, error: 'Parse error: ' + output + errOut });
    }
  });

  python.stdin.write(payload);
  python.stdin.end();
});

// ── CHAT ──
// Zero-assumption audit follow-up — Critical finding, fixed: this route
// predates Mission Control's auth layer and was never retrofitted.
// CLAUDE.md already documented zero real callers (superseded by
// POST /api/agent/:name); confirmed again here — zero references anywhere
// in index.html/dashboard.html/any script — so gating it has no UI/
// automation regression risk, only removes unbounded unauthenticated
// paid-Groq-API exposure.
app.post('/chat', requireMissionControlAuth, async (req, res) => {
  const { message, agent } = req.body;
  try {
    const response = await groq.chat.completions.create({
      model: 'openai/gpt-oss-20b',
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
// ADR-065/MASTER_CHARTER.md: Paddle added alongside the existing three
// platforms (Step 4's paddle_arm.py) — additive, existing KDP/Etsy/Gumroad
// callers unaffected.
const FINANCE_PLATFORMS = ['KDP', 'Etsy', 'Gumroad', 'Paddle'];

// Same six ranks as profit_oracle.py's LADDER_RANKS (MASTER_CHARTER.md §2)
// — duplicated here rather than spawning Python just to read a constant
// list; both must be kept in sync if the ladder itself ever changes.
const LADDER_RANKS = ['ai_saas', 'b2b_systems', 'automation_tools', 'reusable_assets', 'educational', 'kdp_books'];

function financeDefault() {
  return {
    sales: [], totalKDP: 0, totalEtsy: 0, totalGumroad: 0, totalPaddle: 0, totalSales: 0,
    byLadder: Object.fromEntries(LADDER_RANKS.map(r => [r, 0])),
    lastUpdated: null,
  };
}

// ADR-065 Step 3(c): the "4-layer" finance view this fix implements —
// (1) per-sale records (data.sales, unchanged), (2) per-platform totals
// (totalKDP/Etsy/Gumroad/Paddle), (3) per-ladder-rank rollup (byLadder —
// which Strategic Production Priority Ladder rank each sale's revenue
// belongs to, MASTER_CHARTER.md §2), (4) one overall total (totalSales).
// Every sale not tagged with a `ladder` field (every sale recorded before
// this fix, and any future caller that omits it) rolls up under
// 'kdp_books' — the honest default for a factory whose only live product
// today is books, never a silent guess at a different rank.
function recomputeByLadder(sales) {
  const byLadder = Object.fromEntries(LADDER_RANKS.map(r => [r, 0]));
  for (const s of sales) {
    const rank = LADDER_RANKS.includes(s.ladder) ? s.ladder : 'kdp_books';
    byLadder[rank] += s.amount;
  }
  return byLadder;
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
  const sales = Array.isArray(parsed.sales) ? parsed.sales : [];
  return {
    sales,
    totalKDP: Number.isFinite(parsed.totalKDP) ? parsed.totalKDP : 0,
    totalEtsy: Number.isFinite(parsed.totalEtsy) ? parsed.totalEtsy : 0,
    totalGumroad: Number.isFinite(parsed.totalGumroad) ? parsed.totalGumroad : 0,
    totalPaddle: Number.isFinite(parsed.totalPaddle) ? parsed.totalPaddle : 0,
    totalSales: Number.isFinite(parsed.totalSales) ? parsed.totalSales : 0,
    // A legacy file saved before this fix has no byLadder at all — rather
    // than guess, recompute it once from the real sales it already has, so
    // a pre-existing finance_data.json self-heals to the new shape exactly
    // like the corrupt-JSON path above already does for the whole file.
    byLadder: (parsed.byLadder && typeof parsed.byLadder === 'object')
      ? { ...Object.fromEntries(LADDER_RANKS.map(r => [r, 0])), ...parsed.byLadder }
      : recomputeByLadder(sales),
    lastUpdated: parsed.lastUpdated || null,
  };
}

function saveFin(data) {
  data.totalSales = (data.totalKDP || 0) + (data.totalEtsy || 0) + (data.totalGumroad || 0) + (data.totalPaddle || 0);
  data.byLadder = recomputeByLadder(data.sales);
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
  data.totalPaddle = data.sales.filter(s => s.platform === 'Paddle').reduce((a, s) => a + s.amount, 0);
}

app.get('/finance', requireMissionControlAuth, (req, res) => {
  try {
    res.json(loadFin());
  } catch (err) {
    logFinanceError('get', err);
    res.json(financeDefault());
  }
});

// Zero-assumption audit follow-up — Critical finding, fixed: this route
// mutates the real financial ledger (finance_data.json) with zero
// authentication — confirmed zero callers anywhere in index.html or any
// script (CLAUDE.md already noted no UI button wires to it), so gating it
// has no regression risk, only removes the ability for anyone reaching
// this server to inject fake sales records.
app.post('/finance/add', requireMissionControlAuth, (req, res) => {
  const { platform, amount, product, date, ladder } = req.body || {};

  if (!FINANCE_PLATFORMS.includes(platform)) {
    return res.status(400).json({ success: false, error: `platform يجب أن يكون أحد: ${FINANCE_PLATFORMS.join(', ')}` });
  }
  const parsedAmount = parseFloat(amount);
  if (!Number.isFinite(parsedAmount) || parsedAmount < 0) {
    return res.status(400).json({ success: false, error: 'amount يجب أن يكون رقماً موجباً' });
  }
  const parsedDate = /^\d{4}-\d{2}-\d{2}$/.test(date) ? date : new Date().toISOString().split('T')[0];
  // Unknown/omitted ladder rank defaults to 'kdp_books' — same honest-
  // default rule as recomputeByLadder() above, never a guess at a
  // different rank.
  const parsedLadder = LADDER_RANKS.includes(ladder) ? ladder : 'kdp_books';

  try {
    const data = loadFin();
    const sale = {
      id: nextSaleId(data.sales),
      platform,
      amount: parsedAmount,
      product: String(product || 'Unknown').slice(0, 200),
      date: parsedDate,
      ladder: parsedLadder,
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

// Zero-assumption audit follow-up — Critical finding, fixed: same
// rationale as /finance/add above — zero callers confirmed, real
// financial-ledger mutation, no auth. Anyone reaching this server could
// previously delete real sale records with zero credentials.
app.delete('/finance/delete/:id', requireMissionControlAuth, (req, res) => {
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

// Real inbound Paddle payment webhook (ADR-223, Phase 31, 2026-08-08).
// Deliberately unauthenticated by Mission Control session -- Paddle's
// own servers never have a mc_session cookie. Trust comes entirely
// from channels/paddle_webhook.py's real HMAC-SHA256 signature
// verification against PADDLE_WEBHOOK_SECRET (not yet configured in
// this factory -- every real event is honestly rejected as
// MISSING_SECRET until the founder sets it, never bypassed). req.rawBody
// (captured by the express.json() verify callback above) is passed
// through base64-encoded so the exact bytes Paddle signed are never
// altered by a Node<->Python JSON round-trip.
const PADDLE_WEBHOOK_ALERT_MIN_INTERVAL_MS = 60 * 60 * 1000; // throttle per reason: 1h
const paddleWebhookAlertLastSent = new Map();
app.post('/webhooks/paddle', (req, res) => {
  const pythonPath = detectPython();
  const scriptPath = path.join(__dirname, 'channels', 'paddle_webhook.py');
  const python = spawn(pythonPath, [scriptPath, '--json'], { cwd: __dirname });
  let output = '', errOut = '';
  const timer = setTimeout(() => { try { python.kill(); } catch (_) {} }, 15000);
  python.stdout.on('data', d => { output += d.toString(); });
  python.stderr.on('data', d => { errOut += d.toString(); });
  python.on('close', () => {
    clearTimeout(timer);
    let parsed;
    try {
      parsed = JSON.parse(output.trim());
    } catch (e) {
      // A parse failure here is this factory's own bug, not evidence
      // about the webhook event itself -- still respond 200 (Paddle
      // retries on non-2xx) so a transient Node-side issue doesn't
      // trigger Paddle's own retry storm on top of it.
      return res.status(200).json({ status: 'ERROR', detail: `local parse error: ${e.message}${errOut ? ' -- ' + errOut.slice(0, 200) : ''}` });
    }
    // CTO+COO audit closure (2026-08-15): a REJECTED event (e.g.
    // MISSING_SECRET because PADDLE_WEBHOOK_SECRET is unset) was previously
    // only appended to the local ledger and returned as a blanket 200 -- a
    // real Paddle event silently dropped once the founder sets the secret.
    // Surface it via Telegram (throttled per reason) so it can't vanish
    // unnoticed; the 200 response itself is kept to avoid a retry storm.
    if (parsed && parsed.status === 'REJECTED' && parsed.reason !== 'DUPLICATE_EVENT') {
      const nowMs = Date.now();
      const last = paddleWebhookAlertLastSent.get(parsed.reason) || 0;
      if (nowMs - last > PADDLE_WEBHOOK_ALERT_MIN_INTERVAL_MS) {
        paddleWebhookAlertLastSent.set(parsed.reason, nowMs);
        telegramDirect.sendTelegramMessage(
          `[Paddle webhook] event REJECTED — ${parsed.reason}: ${parsed.detail || ''}${parsed.event_id ? ` (event ${parsed.event_id})` : ''}`
        ).catch(() => {});
      }
    }
    res.status(200).json(parsed);
  });
  python.stdin.write(JSON.stringify({
    raw_body_base64: (req.rawBody || Buffer.from(JSON.stringify(req.body || {}))).toString('base64'),
    signature_header: req.get('Paddle-Signature') || null,
  }));
  python.stdin.end();
});

// ── AGENT SYSTEM PROMPTS ──
const AGENT_PROMPTS = {
  scout: {
    system: `أنت وكيل استكشاف الأسواق في Galaxy Forge. مهمتك تحليل أسواق الكتب الرقمية وتقديم أفكار رابحة لـ Amazon KDP وEtsy وGumroad.
عند تشغيلك قدّم:
1. 3-5 أفكار كتب رابحة حالياً بناءً على اتجاهات السوق
2. لكل فكرة: النيش، مستوى المنافسة (منخفض/متوسط/عالي)، السعر المقترح، الجمهور المستهدف
3. توصيتك الأولى بوضوح
أجب باللغة العربية، بشكل منظم ومختصر.`,
    trigger: 'حلّل السوق الآن وأعطني أفضل 5 أفكار كتب رابحة لهذا الشهر على Amazon KDP وEtsy'
  },

  builder: {
    system: `أنت وكيل بناء المحتوى في Galaxy Forge. مهمتك توليد محتوى الكتب الرقمية (journals, planners, trackers, cookbooks).
عند تشغيلك قدّم:
1. هيكل كتاب جديد مقترح: عنوان، فصول رئيسية، عدد الصفحات
2. مثال محتوى صفحة واحدة كاملة من الكتاب
3. 3 نصائح لجعل المحتوى أكثر قيمة وأعلى تقييماً
أجب باللغة العربية، بشكل عملي وقابل للتطبيق مباشرة.`,
    trigger: 'اقترح كتاباً رقمياً جديداً مع هيكله الكامل ومثال على محتواه'
  },

  design: {
    system: `أنت وكيل التصميم في Galaxy Forge. مهمتك اقتراح أفكار تصميم احترافية للأغلفة والصفحات الداخلية للكتب الرقمية بحجم 6×9 إنش.
عند تشغيلك قدّم:
1. مفهوم تصميم غلاف: الألوان الرئيسية، نوع الخط، الأسلوب البصري، العناصر الجرافيكية
2. أفكار للصفحات الداخلية: التخطيط، التوزيع، الأيقونات، الفراغات
3. 3 توصيات لجعل التصميم يبرز في نتائج البحث على Amazon وEtsy
أجب باللغة العربية بتفاصيل دقيقة قابلة للتنفيذ.`,
    trigger: 'اقترح تصميماً احترافياً كاملاً لغلاف وصفحات داخلية لكتاب journal أو planner'
  },

  qa: {
    system: `أنت وكيل ضمان الجودة في Galaxy Forge. مهمتك فحص المنتجات الرقمية وضمان جودتها قبل النشر على KDP وEtsy.
عند تشغيلك قدّم:
1. قائمة تحقق شاملة لجودة الكتاب الرقمي (PDF، محتوى، تصميم، بيانات)
2. أبرز 5 أخطاء تؤدي لرفض المنتج على KDP أو شكاوى على Etsy
3. معايير الجودة الدنيا المطلوبة لكل منصة
أجب باللغة العربية بقوائم منظمة وعملية.`,
    trigger: 'افحص معايير الجودة وأعطني checklist كاملة لضمان قبول منتجنا الرقمي'
  },

  publisher: {
    system: `أنت وكيل النشر في Galaxy Forge. مهمتك تحضير بيانات النشر المحسّنة لـ SEO على Amazon KDP وEtsy وGumroad.
عند تشغيلك قدّم:
1. عنوان محسّن لـ SEO يتضمن الكلمات المفتاحية الأكثر بحثاً (بالإنجليزية)
2. وصف تسويقي جذاب 150-200 كلمة (بالإنجليزية)
3. 7 كلمات مفتاحية مقترحة لـ KDP Backend Keywords (بالإنجليزية)
4. أنسب 2 فئة (Browse Categories) على Amazon
قدّم البيانات الفعلية بالإنجليزية لأن المنصات إنجليزية، مع شرح مختصر بالعربية لكل قسم.`,
    trigger: 'حضّر بيانات نشر كاملة ومحسّنة لـ SEO لكتاب daily journal على Amazon KDP'
  },

  finance: {
    system: `أنت وكيل التمويل في Galaxy Forge. مهمتك تحليل الربحية واقتراح استراتيجيات تسعير للكتب الرقمية.
عند تشغيلك قدّم:
1. استراتيجية تسعير: سعر الإطلاق، السعر الدائم، أوقات التخفيض
2. مقارنة هوامش الربح الصافي على KDP (35% أو 70%) وEtsy وGumroad
3. حساب نقطة التعادل وهدف إيرادات شهري واقعي للمبتدئين
4. نصيحة واحدة لزيادة الإيرادات بأقل جهد
أجب باللغة العربية مع أرقام واضحة وقابلة للتطبيق.`,
    trigger: 'حلّل الربحية وأعطني استراتيجية تسعير كاملة لكتبنا الرقمية على KDP وEtsy وGumroad'
  }
};

// Customer Experience & Brand DNA (ADR-170, 2026-08-05): the real
// mechanism by which "every AI agent must reflect one unified company
// personality" is enforced -- one shared preamble, injected at every
// real call site an AGENT_PROMPTS system prompt passes through (3 real
// ones found by direct search: this route, generatePublisherSEO()'s
// reuse of AGENT_PROMPTS.publisher.system, and the real Scout pipeline's
// reuse of AGENT_PROMPTS.scout.system below) -- so a future agent or
// call site inherits it the moment it references AGENT_PROMPTS, without
// anyone needing to remember a checklist. Canonical definition lives in
// brand_dna.py::COMPANY_PERSONALITY -- keep this text in sync with that
// module's real behavioral rules (checked by tests/test_brand_dna.js's
// key-phrase cross-check, not a live Python call at request time, per
// this ADR's own "do not overengineer" instruction).
const COMPANY_PERSONALITY_PREAMBLE = `أنت جزء من Galaxy Forge. شخصية الشركة الموحّدة: احترافي، صادق، محترم، هادئ، متعاون، شفّاف، ذكي (دليل لا تخمين)، متميز، وطبيعي في أسلوبك دون التظاهر بأنك إنسان. لا تبالغ، لا تستخدم لغة استعجال أو ندرة مصطنعة، اذكر السبب الحقيقي دائماً بدلاً من اعتذار عام، واحترم وقت من يقرأ ردّك.

`;

// ── AGENT ENDPOINTS ──
app.post('/api/agent/:name', requireMissionControlAuth, async (req, res) => {
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
      model: 'openai/gpt-oss-20b',
      max_tokens: 1024,
      messages: [
        { role: 'system', content: COMPANY_PERSONALITY_PREAMBLE + agentConfig.system },
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
        groq.chat.completions.create({ model: 'openai/gpt-oss-20b', max_tokens: maxTokens, messages }),
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

app.post('/api/scout/run', requireMissionControlOrInternalToken, async (req, res) => {
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
        { role: 'system', content: COMPANY_PERSONALITY_PREAMBLE + AGENT_PROMPTS.scout.system },
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

app.post('/api/trends', requireMissionControlOrInternalToken, async (req, res) => {
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

app.post('/api/market-analyze', requireMissionControlAuth, (req, res) => {
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

// Zero-assumption audit follow-up — Medium-High finding, fixed: runReality()
// spawned a fresh Python interpreter on every single call with no caching,
// making GET /api/dashboard — the exact endpoint dashboard.html polls every
// 60s — take 3-4 real seconds per request (measured live against the real
// running server). reality.py reflects slow-moving business state (KDP
// publish status, real sales), not per-request-sensitive data, so a short
// TTL cache removes the redundant spawn cost without ever serving
// meaningfully stale data. runReality() itself is untouched/still directly
// callable (tests use it uncached); only the two live call sites route
// through this cached wrapper.
const REALITY_CACHE_TTL_MS = 30000;
let realityCache = null; // { result, expiresAt }

function runRealityCached(timeoutMs = 5000) {
  if (realityCache && Date.now() < realityCache.expiresAt) {
    return Promise.resolve(realityCache.result);
  }
  return runReality(timeoutMs).then(result => {
    realityCache = { result, expiresAt: Date.now() + REALITY_CACHE_TTL_MS };
    return result;
  });
}

app.get('/api/reality', requireMissionControlAuth, async (req, res) => {
  res.json(await runRealityCached());
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

  // Enterprise Infrastructure & HA Mission (2026-07-23), finding 4.7:
  // real memory/CPU/disk/network/storage-integrity checks, plus honest
  // "not_applicable" entries for infrastructure this factory genuinely
  // does not have (database, message queue, worker pool) — see
  // lib/health_checks.js's own module docstring for why those are
  // reported this way instead of a fabricated green check.
  const [diskCheck, networkCheck] = await Promise.all([
    healthChecks.checkDiskSpace(__dirname),
    healthChecks.checkNetworkReachability({ hasGitRemote: true }),
  ]);
  checks.memory = healthChecks.checkMemory();
  checks.cpu = healthChecks.checkCpu();
  checks.disk = diskCheck;
  checks.network = networkCheck;
  checks.storage_integrity = healthChecks.checkStorageIntegrity([
    { name: 'decisions', filePath: path.join(__dirname, 'data', 'decisions.jsonl'), format: 'jsonl' },
    { name: 'finance', filePath: FINANCE_FILE, format: 'json' },
    { name: 'factory_state', filePath: path.join(__dirname, 'data', 'factory_state.json'), format: 'json' },
  ]);
  Object.assign(checks, healthChecks.notApplicableChecks());

  // not_applicable checks (database/queue/worker — none exist) must
  // never count as "failing": ok is deliberately null for them, and
  // `!null` is true, which would otherwise wrongly drag overall status
  // down for infrastructure this factory was never supposed to have.
  const failing = Object.values(checks).filter(c => c.severity !== 'not_applicable' && !c.ok);
  let status = 'healthy';
  if (failing.some(c => c.severity === 'critical')) status = 'critical';
  else if (failing.length > 0) status = 'degraded';

  // Reality Scorecard override (Task 14): a factory with every cell green
  // but zero published books, or zero sales 30+ days after publishing, is
  // not "healthy" — self-awareness measures CELL health, not OUTCOMES. The
  // cell-based status above is preserved as-is when reality itself is OK
  // (or unreachable-but-not-worse); it's only overridden toward a worse
  // verdict, never softened.
  const reality = await runRealityCached();
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

// Resilience & Stress Hardening audit (2026-08-08): a real, safe load
// test against a temporary, non-live server instance found /health's
// real network-reachability checks (Groq/GitHub/Telegram, uncached, no
// coalescing) degrade severely under concurrency -- p50 latency went
// from ~6s at 10 concurrent requests to ~44s at 100 concurrent, because
// every single request independently re-ran the same real outbound
// calls. Fixed with the exact same in-flight-coalescing + short-TTL
// cache pattern already proven at runPythonServiceCached() (`:361`) --
// reused verbatim, not a new mechanism. A short 3s TTL keeps health
// data close to real-time while absorbing a concurrency burst; `?fresh=1`
// still forces a genuinely fresh, uncoalesced read.
const healthCheckCache = { result: null, expiresAt: 0 };
let healthCheckInFlight = null;

function computeHealthStatusCached(req) {
  const bypass = !!(req && req.query && (req.query.fresh === '1' || req.query.fresh === 'true'));
  if (!bypass) {
    if (healthCheckCache.result && Date.now() < healthCheckCache.expiresAt) {
      return Promise.resolve(healthCheckCache.result);
    }
    if (healthCheckInFlight) return healthCheckInFlight;
  }
  const promise = computeHealthStatus().then(result => {
    healthCheckCache.result = result;
    healthCheckCache.expiresAt = Date.now() + 3000;
    return result;
  }).finally(() => {
    healthCheckInFlight = null;
  });
  if (!bypass) healthCheckInFlight = promise;
  return promise;
}

app.get('/health', async (req, res) => {
  res.json(await computeHealthStatusCached(req));
});

// ── FACTORY DOCTOR: SELF-HEALING LOOP STATUS ──
// Read-only view into factory_loop.js's own log (that script runs as a
// separate process — see factory_loop.js — so this route only ever reads a
// file; it never starts, stops, or depends on the loop being alive).
app.get('/factory-loop/status', requireMissionControlAuth, (req, res) => {
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

// EOS Phase 2, Round 2 (2026-07-19): same markdown-section-scrape technique
// as readNextDollarActions() above, applied to MASTER_CHARTER.md's own
// "## 2. Strategic Production Priority Ladder" heading -- one more real
// priority signal for the Unified Priorities Engine below.
function readStrategicPriorityLadder() {
  const charterFile = path.join(__dirname, 'OpenClaw_Brain', '00_Governance', 'MASTER_CHARTER.md');
  if (!fs.existsSync(charterFile)) return { text: null, note: 'MASTER_CHARTER.md غير موجود' };
  const content = fs.readFileSync(charterFile, 'utf8');
  const marker = '## 2. Strategic Production Priority Ladder';
  const idx = content.indexOf(marker);
  if (idx === -1) return { text: null, note: 'قسم "Strategic Production Priority Ladder" غير موجود في MASTER_CHARTER.md' };
  const rest = content.slice(idx + marker.length);
  const nextHeaderMatch = rest.match(/\n## /);
  const section = (nextHeaderMatch ? rest.slice(0, nextHeaderMatch.index) : rest).trim();
  return { text: section };
}

// EOS Phase 2, Round 2 (2026-07-19): Unified Priorities Engine. Combines
// three already-real priority signals SIDE BY SIDE -- never merged into
// one fabricated composite score, per the founder's own "no invented
// metrics" standing rule. Closes Opportunity Intelligence's one real gap
// (today a founder needs 4 separate tabs -- market/goldenhunter/pioneer/
// opportunities -- to piece this picture together) without building a
// second, competing consolidation layer.
async function unifiedPrioritiesService() {
  const opportunityQueue = await runPythonService('opportunities').catch(err => ({ error: err.message }));
  return {
    next_dollar_actions: readNextDollarActions(),
    opportunity_queue: opportunityQueue,
    strategic_priority_ladder: readStrategicPriorityLadder(),
  };
}

app.get('/good-morning', requireMissionControlAuth, async (req, res) => {
  // Standing charter follow-up — same fix as GET /api/dashboard: this used
  // to run computeHealthStatus() and assessSelfAwareness() in Promise.all,
  // but assessSelfAwareness() independently re-fetched the identical
  // health object over HTTP from this same server (necessary only when
  // self_awareness.js runs as a separate process via factory_loop.js).
  // Computed once, handed directly to assessSelfAwareness() instead.
  const factoryStatus = await computeHealthStatus().catch(err => ({ status: 'error', error: err.message }));
  const [opportunities, lastNightActions, nextDollar, awareness] = await Promise.all([
    Promise.resolve().then(() => readTopOpportunities(3)).catch(err => ({ items: [], note: `error: ${err.message}` })),
    Promise.resolve().then(() => readLastLoopActions(10)).catch(err => ({ entries: [], note: `error: ${err.message}` })),
    Promise.resolve().then(() => readNextDollarActions()).catch(err => ({ text: null, note: `error: ${err.message}` })),
    // CONSTITUTION.md §20: Galaxy sees the truth every morning, not just the
    // health check — the same honest verdict GET /awareness computes.
    selfAwareness.assessSelfAwareness(new Date(), factoryStatus).catch(err => ({ verdict: null, note: `error: ${err.message}` })),
  ]);

  res.json({
    success: true,
    generated_at: new Date().toISOString(),
    title: '🏭 Galaxy Forge — Daily Briefing',
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
app.get('/oracle', requireMissionControlAuth, (req, res) => {
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
app.get('/inspections', requireMissionControlAuth, (req, res) => {
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
app.get('/brain', requireMissionControlAuth, (req, res) => {
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
app.get('/hunter', requireMissionControlAuth, (req, res) => {
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
app.get('/awareness', requireMissionControlAuth, async (req, res) => {
  try {
    const assessment = await selfAwareness.assessSelfAwareness();
    res.json({ success: true, ...assessment });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// ── EXECUTIVE DASHBOARD ──
// ADR-034's 2026-07-15 override update: built by aggregating real,
// already-existing signals (this route computes nothing new — it calls the
// same computeHealthStatus()/selfAwareness.assessSelfAwareness() every other
// status route already uses, plus lib/dashboard_data.js's pure file reads
// over golden_opportunities.json, finance_data.json, market_hunter_runs.log,
// pending_review/, tier1_intake/, NEEDS_ATTENTION.md, NEEDS_REVIEW.md).
// Zero fabricated metrics — a section with no data yet reports that
// honestly instead of inventing a number.
// Standing charter follow-up — verified live during the reality-cache fix's
// own measurement: this used to run computeHealthStatus() and
// assessSelfAwareness() in Promise.all (parallel), but assessSelfAwareness()
// independently made its OWN HTTP round-trip back to THIS SAME server's
// /health endpoint (self_awareness.js's getHealth(), necessary when it runs
// as a separate process via factory_loop.js, but pure waste when called
// in-process here) — recomputing the identical health object a second time
// over a network hop, ~1s of real, measured cost on every /api/dashboard
// call even after runReality()'s caching fix. Now computed once and handed
// directly to assessSelfAwareness(), which skips its own fetch entirely
// when a precomputed health object is given (self_awareness.js's own
// default behavior is unchanged for factory_loop.js/the CLI).
app.get('/api/dashboard', async (req, res) => {
  try {
    const health = await computeHealthStatus().catch(err => ({ status: 'error', error: err.message }));
    const awareness = await selfAwareness.assessSelfAwareness(new Date(), health).catch(err => ({ verdict: null, error: err.message }));
    const priorities = readNextDollarActions();
    res.json({ success: true, ...dashboardData.computeDashboard({ health, awareness, priorities }) });
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

// Red-team audit (Phase 10 follow-up) — CRITICAL finding, fixed: this used
// to be `app.use(express.static(path.join(__dirname), { index: false }))`,
// which served the ENTIRE repo root unauthenticated — finance_data.json,
// data/*.jsonl, config/*.json, and every real product PDF under books/
// were all publicly downloadable with no session. Neither dashboard.html
// nor mission_control_login.html reference any other local asset (checked:
// no relative <script>/<link>/fetch() to a sibling file), so only these
// two named files need bare-path serving — nothing else in the repo does.
app.get('/dashboard.html', (req, res) => {
  res.sendFile(path.join(__dirname, 'dashboard.html'));
});
app.get('/mission_control_login.html', (req, res) => {
  res.sendFile(path.join(__dirname, 'mission_control_login.html'));
});

// Global Commercial Readiness Mission (2026-07-23) — Customer Trust
// System. A real bug found by this feature's own test suite, not
// assumed safe: without this, GET /trust/* fell through to the
// wildcard catch-all below and silently served the wrong file (the
// UTF-16-encoded root index.html, garbled when read as UTF-8) instead
// of any real trust-center page — a 200 status code with completely
// wrong content, which a status-code-only check would have missed.
//
// This is deliberately NOT the same mistake as the removed repo-root
// express.static() above (the real prior CRITICAL finding): that one
// exposed the entire repository, including finance_data.json and
// every real data file, because its root was `__dirname` itself. This
// one is scoped to `trust/` alone — a small, dedicated directory that
// contains nothing but these public-by-design pages, the same
// "intentionally public, nothing sensitive can end up here" reasoning
// dashboard.html's own bare-path route already relies on.
app.use('/trust', express.static(path.join(__dirname, 'trust')));

// ── GALAXY FORGE CUSTOMER PLATFORM, Phase 1 (2026-07-25) ──
// Real, public-facing site — landing page + company presentation +
// services catalog + a real "Request a Custom Product" intake. Scoped
// deliberately to what can operate on 100% real data today: the real
// Paddle product catalog (data/paddle_products.json) and a real,
// persisted customer request ledger. Payment/Order Tracking/Customer
// Dashboard are honestly NOT built this round — Paddle's own account
// onboarding gate blocks real checkout completion today (confirmed live,
// channels/paddle_publisher.py's create_checkout_transaction()), and
// zero real orders exist yet for any dashboard to honestly show. Same
// "intentionally public, nothing sensitive can end up here" scoping as
// the /trust mount just above -- customer_site/ contains only these
// public-by-design pages.
app.use('/site', express.static(path.join(__dirname, 'customer_site')));

// Deploy-readiness (Phase 1, Quality Supremacy directive, 2026-07-25):
// real, standard-convention crawler files. /site/ and /trust/ are the only
// two mounts meant for public search indexing -- everything else in this
// repo is either an authenticated internal surface (Mission Control) or an
// API with nothing worth indexing. Disallow those explicitly rather than
// relying on crawlers just not finding them.
app.get('/robots.txt', (req, res) => {
  res.type('text/plain').send(
    'User-agent: *\n' +
    'Allow: /site/\n' +
    'Allow: /trust/\n' +
    'Disallow: /site/status.html\n' +
    'Disallow: /api/\n' +
    'Disallow: /mission_control\n' +
    'Disallow: /dashboard.html\n' +
    'Sitemap: /site/sitemap.xml\n'
  );
});

app.get('/site/sitemap.xml', (req, res) => {
  const pages = ['/site/', '/site/#approach', '/site/#how-it-works', '/site/#services', '/site/#support', '/site/#knowledge-base', '/trust/index.html'];
  // Autonomous Enterprise Master Plan Task 2 (2026-08-15): the autonomous
  // SEO distribution engine publishes real guide pages to the customer
  // site; the sitemap must list them so crawlers can discover them. The
  // registry (data/seo_pages.json) is the single source of truth — the
  // sitemap can never drift from the real, published pages.
  try {
    const seoPages = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'seo_pages.json'), 'utf8'));
    if (Array.isArray(seoPages)) {
      for (const e of seoPages) {
        if (e && typeof e.page === 'string') pages.push(e.page);
      }
    }
  } catch (_) { /* no SEO pages yet — sitemap stays with the base pages */ }
  const urls = pages.map(p => `  <url><loc>${p}</loc></url>`).join('\n');
  res.type('application/xml').send(`<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`);
});

const PADDLE_PRODUCTS_FILE = path.join(__dirname, 'data', 'paddle_products.json');
const CUSTOMER_REQUESTS_FILE = path.join(__dirname, 'data', 'customer_requests.jsonl');
const CUSTOMER_REQUEST_FIELD_MAX = 2000;
// Simple, bounded, in-memory sliding-window rate limit -- this endpoint has
// no session/auth (it's a public intake form), so it's the one real spam
// vector this Phase 1 surface introduces. Proportionate to the real risk:
// a small in-memory map, not a new rate-limiting engine/dependency.
// CEO Review cycle (2026-07-25) finding: every rate limiter on the
// customer-facing routes below keys on req.ip. That's correct today --
// this server binds to 127.0.0.1 only (see the startup log / test_api_
// contract.js's "server binds to loopback only" check) and no reverse
// proxy or tunnel config exists anywhere in this repo (confirmed by
// grep), so req.ip is always the real caller. PRE-LAUNCH REQUIREMENT:
// the moment this site goes behind any reverse proxy/tunnel for real
// public exposure, req.ip will report the proxy's address for every
// customer unless `app.set('trust proxy', ...)` is configured to read
// the real forwarded-for header -- silently collapsing every customer
// into one shared rate-limit bucket (or none at all). Not built around
// speculatively since the real proxy topology isn't chosen yet -- revisit
// the moment one is.
const CUSTOMER_REQUEST_RATE_LIMIT = { windowMs: 10 * 60 * 1000, maxPerWindow: 5 };
const customerRequestRateState = new Map(); // ip -> [timestamps]

function isRateLimited(ip) {
  const now = Date.now();
  const windowStart = now - CUSTOMER_REQUEST_RATE_LIMIT.windowMs;
  const timestamps = (customerRequestRateState.get(ip) || []).filter(t => t > windowStart);
  timestamps.push(now);
  customerRequestRateState.set(ip, timestamps);
  // Bound total memory regardless of how many distinct IPs ever hit this --
  // a real, cheap safeguard, not a full LRU cache.
  if (customerRequestRateState.size > 5000) customerRequestRateState.clear();
  return timestamps.length > CUSTOMER_REQUEST_RATE_LIMIT.maxPerWindow;
}

// ── Customer Accounts (Customer Platform Round 1, 2026-07-29) ──
// Real per-customer login, replacing "possession of the request_id URL" as
// the only way to look at your own order. Deliberately its own signing
// scheme/cookie, separate from MISSION_CONTROL_SESSION_SECRET (lib/
// customer_auth.js's own header explains why) -- a customer must never be
// able to forge a founder Mission Control session, or vice versa. Guest
// (no-login) submission via /api/customer/request-product is UNCHANGED --
// this only adds an optional account layer on top, never a requirement to
// use the site.
const customerAuth = require('./lib/customer_auth');
const CUSTOMER_ACCOUNTS_FILE = path.join(__dirname, 'data', 'customer_accounts.json');
const CUSTOMER_SESSION_SECRET_FILE = path.join(__dirname, 'data', '.customer_session_secret');
const CUSTOMER_SESSION_SECRET = customerAuth.loadOrCreateSessionSecret(CUSTOMER_SESSION_SECRET_FILE);
const CUSTOMER_SESSION_COOKIE = 'cust_session';
const CUSTOMER_SESSION_MAX_AGE_MS = 30 * 24 * 60 * 60 * 1000; // 30 days -- real customers, not a founder daily tool
const CUSTOMER_DUMMY_PASSWORD_HASH = customerAuth.hashPassword('dummy-timing-equalizer'); // fixed once at startup, login's no-such-account timing equalizer

function loadCustomerAccounts() {
  try {
    if (!fs.existsSync(CUSTOMER_ACCOUNTS_FILE)) return {};
    const data = JSON.parse(fs.readFileSync(CUSTOMER_ACCOUNTS_FILE, 'utf8'));
    return (data && typeof data === 'object' && !Array.isArray(data)) ? data : {};
  } catch {
    return {};
  }
}

function saveCustomerAccounts(accounts) {
  fs.mkdirSync(path.dirname(CUSTOMER_ACCOUNTS_FILE), { recursive: true });
  fs.writeFileSync(CUSTOMER_ACCOUNTS_FILE, JSON.stringify(accounts, null, 2));
}

function findCustomerAccountByEmail(accounts, email) {
  const target = email.trim().toLowerCase();
  return Object.values(accounts).find(a => (a.email || '').trim().toLowerCase() === target) || null;
}

// Same dedicated-limiter-per-surface convention as isConsultationRateLimited
// -- an auth-brute-force attempt must not also exhaust a customer's own
// request-product quota, and vice versa.
const CUSTOMER_AUTH_RATE_LIMIT = { windowMs: 10 * 60 * 1000, maxPerWindow: 8 };
const customerAuthRateState = new Map();
function isCustomerAuthRateLimited(ip) {
  const now = Date.now();
  const windowStart = now - CUSTOMER_AUTH_RATE_LIMIT.windowMs;
  const timestamps = (customerAuthRateState.get(ip) || []).filter(t => t > windowStart);
  timestamps.push(now);
  customerAuthRateState.set(ip, timestamps);
  if (customerAuthRateState.size > 5000) customerAuthRateState.clear();
  return timestamps.length > CUSTOMER_AUTH_RATE_LIMIT.maxPerWindow;
}

function publicAccountView(account) {
  return { account_id: account.account_id, email: account.email, name: account.name, company: account.company || '' };
}

// Reusable for any future customer-facing route that needs a real logged-in
// account (order history, invoices, downloads -- later rounds).
function getAuthenticatedCustomerAccount(req) {
  const cookies = parseCookies(req);
  const accountId = customerAuth.verifyCustomerSession(CUSTOMER_SESSION_SECRET, cookies[CUSTOMER_SESSION_COOKIE]);
  if (!accountId) return null;
  const accounts = loadCustomerAccounts();
  return accounts[accountId] || null;
}

function requireCustomerAuth(req, res, next) {
  const account = getAuthenticatedCustomerAccount(req);
  if (!account) return res.status(401).json({ success: false, error: 'please log in to continue' });
  req.customerAccount = account;
  next();
}

app.post('/api/customer/signup', (req, res) => {
  try {
    const ip = req.ip || (req.socket && req.socket.remoteAddress) || 'unknown';
    if (isCustomerAuthRateLimited(ip)) {
      return res.status(429).json({ success: false, error: 'too many attempts — please try again later' });
    }
    const body = req.body || {};
    if (body.website) {
      // Honeypot -- same silent-accept-but-drop convention as request-product.
      return res.json({ success: true });
    }
    const name = String(body.name || '').trim();
    const email = String(body.email || '').trim();
    const company = String(body.company || '').trim();
    const password = String(body.password || '');

    if (!name || !email || !password) {
      return res.status(400).json({ success: false, error: 'name, email, and password are required' });
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return res.status(400).json({ success: false, error: 'a valid email address is required' });
    }
    if (password.length < 8) {
      return res.status(400).json({ success: false, error: 'password must be at least 8 characters' });
    }
    if (name.length > CUSTOMER_REQUEST_FIELD_MAX || company.length > CUSTOMER_REQUEST_FIELD_MAX) {
      return res.status(400).json({ success: false, error: 'field exceeds the maximum length' });
    }

    const accounts = loadCustomerAccounts();
    if (findCustomerAccountByEmail(accounts, email)) {
      return res.status(409).json({ success: false, error: 'an account with this email already exists' });
    }

    const accountId = customerAuth.generateAccountId();
    const account = {
      account_id: accountId,
      email, name, company,
      password_hash: customerAuth.hashPassword(password),
      created_at: new Date().toISOString(),
    };
    accounts[accountId] = account;
    saveCustomerAccounts(accounts);

    const token = customerAuth.signCustomerSession(CUSTOMER_SESSION_SECRET, accountId);
    res.cookie(CUSTOMER_SESSION_COOKIE, token, { httpOnly: true, sameSite: 'lax', maxAge: CUSTOMER_SESSION_MAX_AGE_MS });
    res.json({ success: true, account: publicAccountView(account) });
  } catch (err) {
    res.status(500).json({ success: false, error: 'could not create account — please try again' });
  }
});

app.post('/api/customer/login', (req, res) => {
  try {
    const ip = req.ip || (req.socket && req.socket.remoteAddress) || 'unknown';
    if (isCustomerAuthRateLimited(ip)) {
      return res.status(429).json({ success: false, error: 'too many attempts — please try again later' });
    }
    const email = String((req.body && req.body.email) || '').trim();
    const password = String((req.body && req.body.password) || '');
    if (!email || !password) {
      return res.status(400).json({ success: false, error: 'email and password are required' });
    }

    const accounts = loadCustomerAccounts();
    const account = findCustomerAccountByEmail(accounts, email);
    // Same shape of response whether the email doesn't exist or the
    // password is wrong -- never confirms which one to an attacker.
    // Running verifyPassword against a fixed dummy hash even when no
    // account was found keeps the timing roughly consistent either way.
    const passwordOk = customerAuth.verifyPassword(password, account ? account.password_hash : CUSTOMER_DUMMY_PASSWORD_HASH);
    if (!account || !passwordOk) {
      return res.status(401).json({ success: false, error: 'invalid email or password' });
    }

    const token = customerAuth.signCustomerSession(CUSTOMER_SESSION_SECRET, account.account_id);
    res.cookie(CUSTOMER_SESSION_COOKIE, token, { httpOnly: true, sameSite: 'lax', maxAge: CUSTOMER_SESSION_MAX_AGE_MS });
    res.json({ success: true, account: publicAccountView(account) });
  } catch (err) {
    res.status(500).json({ success: false, error: 'could not log in — please try again' });
  }
});

app.post('/api/customer/logout', (req, res) => {
  res.clearCookie(CUSTOMER_SESSION_COOKIE);
  res.json({ success: true });
});

app.get('/api/customer/session', (req, res) => {
  const account = getAuthenticatedCustomerAccount(req);
  res.json({ success: true, authenticated: !!account, account: account ? publicAccountView(account) : null });
});

// Real Customer History (Round 5, 2026-07-29) -- every real request tied
// to this logged-in account, either by account_id (stamped at submission
// time while logged in) or by matching email (reconciles guest requests
// made before the customer ever created an account).
app.get('/api/customer/account/requests', requireCustomerAuth, async (req, res) => {
  try {
    const result = await runCustomerPipelineCommand('list_for_account', {
      account_id: req.customerAccount.account_id, email: req.customerAccount.email,
    });
    res.json(result);
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// ADR-130 (2026-07-25): direct spawn of customer_pipeline.py -- a single-
// purpose CLI script (command + JSON payload), same pattern as /generate-
// book spawning book_generator.py directly rather than going through
// mission_control_api.py's read-only aggregation layer, which stays
// Mission-Control-auth-only. These three commands (status/approve/reject)
// are public and customer-facing, a different trust boundary entirely.
const CUSTOMER_PIPELINE_SYNC_TIMEOUT_MS = 45000; // a real single Paddle API call, well under this
function runCustomerPipelineCommand(command, payload = {}) {
  return new Promise((resolve, reject) => {
    const pythonPath = detectPython();
    const scriptPath = path.join(__dirname, 'customer_pipeline.py');
    const python = spawn(pythonPath, [scriptPath, command, JSON.stringify(payload)], { cwd: __dirname });
    let output = '', errOut = '', timedOut = false;
    killAfterTimeout(python, CUSTOMER_PIPELINE_SYNC_TIMEOUT_MS, () => { timedOut = true; });
    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', reject);
    python.on('close', () => {
      if (timedOut) return reject(new Error(`customer_pipeline ${command} timed out after ${CUSTOMER_PIPELINE_SYNC_TIMEOUT_MS}ms`));
      let parsed;
      try {
        parsed = JSON.parse(output.trim());
      } catch {
        return reject(new Error(`parse error: ${output}${errOut}`));
      }
      if (parsed.success === false) return reject(new Error(parsed.error || 'customer_pipeline command reported failure'));
      resolve(parsed);
    });
  });
}

// Fire-and-forget post-intake trigger -- real Qualification/Evaluation can
// take minutes (live Groq call), and nothing here waits on it, so this
// gets the SAME generous 15-minute hang-safety-net timeout as the other
// slow real async actions (PYTHON_ACTION_TIMEOUT_MS), not the 45s sync
// budget above. Errors are swallowed by design -- the request stays
// safely in NEW and customer_pipeline.py's own stuck-NEW detection
// surfaces it to the founder instead of failing the (already-sent)
// customer response.
function triggerCustomerPipelineAdvanceFireAndForget(requestId) {
  try {
    const pythonPath = detectPython();
    const scriptPath = path.join(__dirname, 'customer_pipeline.py');
    const python = spawn(pythonPath, [scriptPath, 'advance', JSON.stringify({ request_id: requestId })], { cwd: __dirname, detached: false });
    killAfterTimeout(python, PYTHON_ACTION_TIMEOUT_MS, () => {});
    python.on('error', () => {});
  } catch {
    // best-effort only -- see stuck-NEW detection above
  }
}

// Public, read-only, real: the exact same real Paddle catalog
// data/paddle_products.json already holds (5 real products, real
// product_id/price_id/price -- ADR-085/086). Never a second, hand-
// maintained copy on the customer_site page itself, which would drift
// stale the moment a real product/price changes.
app.get('/api/customer/catalog', (req, res) => {
  try {
    if (!fs.existsSync(PADDLE_PRODUCTS_FILE)) {
      return res.json({ success: true, products: [] });
    }
    const products = JSON.parse(fs.readFileSync(PADDLE_PRODUCTS_FILE, 'utf8'));
    res.json({ success: true, products: Array.isArray(products) ? products : [] });
  } catch (err) {
    res.status(500).json({ success: false, error: 'catalog temporarily unavailable' });
  }
});

// Instant Checkout (ADR-183, 2026-08-07): Readiness Audit Stage 6 found
// the worst real friction in the entire funnel -- every catalog product
// routed into a manual multi-step request/review flow, even ones with an
// already-real, already-priced Paddle price_id. This is the fix: a
// direct redirect straight to a real Paddle-hosted checkout URL for any
// catalog product that has one, skipping manual review entirely for a
// pre-cleared digital SKU. Public, unauthenticated, same trust boundary
// as /api/customer/catalog -- a stranger reaching this route has no
// Mission Control session by definition. Falls back gracefully (never a
// dead end) to the existing, working manual-request flow the moment
// Paddle's real transaction_checkout_not_enabled account-onboarding gate
// fires -- confirmed via direct testing this session that this gate is
// still active, so every real click through this route will genuinely
// hit that fallback until onboarding clears, not a hypothetical path.
app.get('/api/customer/checkout/:product_id', async (req, res) => {
  try {
    const ip = req.ip || (req.socket && req.socket.remoteAddress) || 'unknown';
    if (isRateLimited(ip)) {
      return res.redirect(302, `/site/index.html?checkout_unavailable=${encodeURIComponent(req.params.product_id)}#request`);
    }
    if (!fs.existsSync(PADDLE_PRODUCTS_FILE)) {
      return res.redirect(302, `/site/index.html?checkout_unavailable=${encodeURIComponent(req.params.product_id)}#request`);
    }
    const products = JSON.parse(fs.readFileSync(PADDLE_PRODUCTS_FILE, 'utf8'));
    const product = (Array.isArray(products) ? products : []).find(p => p.product_id === req.params.product_id);
    if (!product || !product.price_id) {
      return res.redirect(302, `/site/index.html?checkout_unavailable=${encodeURIComponent(req.params.product_id)}#request`);
    }
    const result = await runPythonService('create_paddle_checkout', [JSON.stringify({ price_id: product.price_id })]);
    if (result && result.success && result.checkout_url) {
      return res.redirect(302, result.checkout_url);
    }
    return res.redirect(302, `/site/index.html?checkout_unavailable=${encodeURIComponent(req.params.product_id)}#request`);
  } catch (err) {
    return res.redirect(302, `/site/index.html?checkout_unavailable=${encodeURIComponent(req.params.product_id)}#request`);
  }
});

// ── Affiliate Commerce (ADR-149, 2026-07-30) ──
// Public, unauthenticated -- a customer_site visitor has no Mission
// Control login, same reasoning as /api/customer/catalog above. Real,
// static, disclosed-source product data (affiliate_commerce/products.py)
// -- never cached (runPythonService, not runPythonServiceCached): cheap,
// static-in-Python-anyway, and click-adjacent routes on this same
// surface must never be cached, so neither is kept behind a shared cache
// key by accident.
app.get('/api/affiliate/products', async (req, res) => {
  try {
    const category = req.query.category || 'standing_desk_converters';
    const result = await runPythonService('affiliate_products', [JSON.stringify({ category })]);
    res.json(result);
  } catch (err) {
    res.status(500).json({ success: false, error: 'affiliate product data temporarily unavailable' });
  }
});

// Real click tracking (not conversion -- that needs the real Amazon
// Associates postback, which does not exist yet). Every call is a real,
// distinct, honestly-recorded click -- appended to
// data/affiliate_clicks.jsonl (affiliate_commerce/click_tracking.py)
// before the real redirect fires. Amazon's own real product URL is
// built by affiliate_commerce/networks.py, honestly untagged until the
// founder's own real Amazon Associates account exists.
app.get('/api/affiliate/click/:product_id', async (req, res) => {
  try {
    const payload = { product_id: req.params.product_id, referrer: req.get('referer') || null };
    const result = await runPythonService('affiliate_click', [JSON.stringify(payload)]);
    if (!result.found || !result.url) {
      return res.status(404).json({ success: false, error: 'no real product with that id' });
    }
    res.redirect(302, result.url);
  } catch (err) {
    res.status(500).json({ success: false, error: 'affiliate redirect temporarily unavailable' });
  }
});

// Public Solutions Engine (Galaxy Forge Customer-Facing Commercial
// Front Door directive, ADR-240, 2026-08-09). Public, unauthenticated
// -- same reasoning as /api/affiliate/products above. Real, PUBLIC-SAFE
// reshaping of the internal commercial portfolio (commission_engine.py::
// public_solutions_catalog()) -- never the internal Mission Control
// panel data, never cached for the same click-adjacency reason as
// /api/affiliate/products.
app.get('/api/solutions', async (req, res) => {
  try {
    const category = req.query.category || null;
    const result = await runPythonService('public_solutions_catalog', [JSON.stringify({ category })]);
    res.json(result);
  } catch (err) {
    res.status(500).json({ success: false, error: 'solutions catalog temporarily unavailable' });
  }
});

// Real click tracking + redirect to the opportunity's own real,
// official terms/info page -- same real, auditable discipline as
// /api/affiliate/click/:product_id above.
app.get('/api/solutions/click/:opportunity_id', async (req, res) => {
  try {
    const payload = { opportunity_id: req.params.opportunity_id, referrer: req.get('referer') || null };
    const result = await runPythonService('solutions_click', [JSON.stringify(payload)]);
    if (!result.found || !result.url) {
      return res.status(404).json({ success: false, error: 'no real solution with that id' });
    }
    res.redirect(302, result.url);
  } catch (err) {
    res.status(500).json({ success: false, error: 'solutions redirect temporarily unavailable' });
  }
});

// Real "content published -> visitor" tracking (Customer Front Door
// directive Section 7). Public, unauthenticated -- fires from every
// new customer-facing page's own inline JS on load. Reuses affiliate_
// commerce.click_tracking.record_page_view() directly (Revenue
// Activation Directive, ADR-239) -- no second page-view mechanism.
app.post('/api/page-view', async (req, res) => {
  try {
    const rawPageId = req.body && req.body.page_id;
    const payload = { page_id: rawPageId || null, referrer: req.get('referer') || null };
    if (!payload.page_id) {
      return res.status(400).json({ success: false, error: 'page_id is required' });
    }
    // Phase 41.1 fix (2026-08-09): a non-string truthy page_id (e.g. a
    // JSON number/array/object) previously passed this falsy-only check
    // and crashed record_public_page_view()'s real `.strip()` call in
    // mission_control_api.py, surfacing as an unhandled 500 instead of a
    // controlled 400. Reject wrong-typed input at the boundary, before
    // it ever reaches the Python subprocess.
    if (typeof payload.page_id !== 'string') {
      return res.status(400).json({ success: false, error: 'page_id must be a string' });
    }
    const result = await runPythonService('record_public_page_view', [JSON.stringify(payload)]);
    res.json(result);
  } catch (err) {
    res.status(500).json({ success: false, error: 'page-view tracking temporarily unavailable' });
  }
});

// ── INTERNAL MARKET VALIDATION SYSTEM (Founder Directive, 2026-08-14) ──
// Purpose: test real market demand for the Legal Case Research opportunity
// before any product is built. NOT an MVP, NOT a launch, NOT payments.
//
// Two distinct surfaces:
//   1. Public validation page (market-validation.html) + a public, tightly
//      validated POST that records exactly ONE response per call. Public
//      because a prospective respondent has no login — the same reasoning
//      the /api/consultations intake already uses. It stores real rows only
//      and returns NO stored data (no contact info, no verbatim pain text).
//   2. Internal dashboard (validation-dashboard.html + GET
//      /api/validation/dashboard) — gated by the EXISTING Mission Control
//      auth (requireMissionControlAuth), exactly like every other internal
//      panel. Never exposes submitted personal information publicly.
const VALIDATION_SOURCES = new Set(['linkedin', 'facebook', 'x', 'direct', 'other']);
const VALIDATION_Q1 = new Set(['rarely', 'monthly', 'weekly', 'several_times_per_week']);
const VALIDATION_Q2 = new Set(['yes', 'maybe', 'no']);

app.post('/api/validation/submit', async (req, res) => {
  try {
    const body = req.body || {};
    // Boundary validation, before anything reaches the Python subprocess —
    // the same lesson /api/page-view learned (a wrong-typed truthy value
    // crashing the real `.strip()` call downstream). q3 is the one free
    // text field; cap it hard to keep a single POST cheap and honest.
    if (typeof body.q1_frequency !== 'string' || !VALIDATION_Q1.has(body.q1_frequency)) {
      return res.status(400).json({ success: false, error: 'q1_frequency must be one of: rarely, monthly, weekly, several_times_per_week' });
    }
    if (typeof body.q2_intent !== 'string' || !VALIDATION_Q2.has(body.q2_intent)) {
      return res.status(400).json({ success: false, error: 'q2_intent must be one of: yes, maybe, no' });
    }
    if (typeof body.q3_pain !== 'string' || !body.q3_pain.trim()) {
      return res.status(400).json({ success: false, error: 'q3_pain must be a non-empty statement' });
    }
    if (body.q3_pain.length > 2000) {
      return res.status(400).json({ success: false, error: 'q3_pain too long (max 2000 chars)' });
    }
    const source = (body.source || 'other').toString().toLowerCase();
    if (!VALIDATION_SOURCES.has(source)) {
      return res.status(400).json({ success: false, error: 'source must be one of: linkedin, facebook, x, direct, other' });
    }
    const sampleRequest = (body.sample_request || '').toString().toLowerCase();
    if (sampleRequest && !['yes', 'no'].includes(sampleRequest)) {
      return res.status(400).json({ success: false, error: 'sample_request must be yes, no, or empty' });
    }
    const waitlist = (body.waitlist || '').toString().toLowerCase();
    if (waitlist && !['yes', 'no'].includes(waitlist)) {
      return res.status(400).json({ success: false, error: 'waitlist must be yes, no, or empty' });
    }

    const payload = {
      q1_frequency: body.q1_frequency,
      q2_intent: body.q2_intent,
      q3_pain: body.q3_pain.trim(),
      source,
      professional_role: typeof body.professional_role === 'string' ? body.professional_role.trim() : '',
      practice_area: typeof body.practice_area === 'string' ? body.practice_area.trim() : '',
      contact: typeof body.contact === 'string' ? body.contact.trim() : '',
      session_id: typeof body.session_id === 'string' ? body.session_id.trim() : '',
      sample_request: sampleRequest,
      waitlist,
    };

    const result = await runPythonService('validation_submit', [JSON.stringify(payload)]);
    if (result.success === false) {
      return res.status(400).json({ success: false, error: result.error });
    }
    res.json({ success: true, recorded: true });
  } catch (err) {
    // The Python layer prefixes its validation errors with "validation: "
    // as a stable contract — a duplicate or malformed-response rejection is
    // the client's fault (400), not a server fault (500). Everything else
    // (parse failure, subprocess failure, timeout) is a genuine server error.
    if (err && typeof err.message === 'string' && err.message.startsWith('validation: ')) {
      return res.status(400).json({ success: false, error: err.message.replace(/^validation: /, '') });
    }
    res.status(500).json({ success: false, error: 'validation submission temporarily unavailable' });
  }
});

// Internal dashboard API — auth-gated. Returns aggregated counts only;
// never contact info, never verbatim q3 text.
app.get('/api/validation/dashboard', requireMissionControlAuth, async (req, res) => {
  try {
    const result = await runPythonService('validation_dashboard');
    res.json({ success: true, summary: result.summary });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// Internal dashboard page — auth-gated by the existing Mission Control login.
app.get('/validation-dashboard.html', requireMissionControlAuth, (req, res) => {
  res.sendFile(path.join(__dirname, 'public_site', 'validation-dashboard.html'));
});

// Public validation page — intentionally public (a respondent has no login).
app.get('/market-validation.html', (req, res) => {
  res.sendFile(path.join(__dirname, 'public_site', 'market-validation.html'));
});

// Public visit tracking for the validation page — fires on page load,
// records one real visit into the factory's single existing page-view
// ledger via market_validation.record_visit (never a second system).
app.post('/api/validation/page-view', async (req, res) => {
  try {
    const body = req.body || {};
    const source = (body.source || 'direct').toString().toLowerCase();
    if (!VALIDATION_SOURCES.has(source)) {
      return res.status(400).json({ success: false, error: 'source must be one of: linkedin, facebook, x, direct, other' });
    }
    const result = await runPythonService('validation_page_view', [JSON.stringify({ source })]);
    res.json({ success: true, recorded: true });
  } catch (err) {
    res.status(500).json({ success: false, error: 'validation page-view tracking temporarily unavailable' });
  }
});

// Real, persisted customer intake -- no fabricated qualification/scoring
// pipeline behind this yet (that's genuinely new logic, Phase 2, not
// built this round). Every real submission is appended, never
// overwritten, and the founder is notified via the same real, already-
// live Telegram channel every other real factory event already uses --
// no second notification system.
// ── AI Consultation (ADR-130, 2026-07-25) ──
// Public, unauthenticated -- unlike /api/agent/:name (Mission Control-
// gated since the Phase 1 Security Audit's finding 2.1: an arbitrary
// `message` reaching a real Groq call with no rate limit is a real spend
// vector). This route is deliberately public (a prospective customer has
// no login), so it closes that same hole differently: a FIXED system
// prompt (never user-controllable), a hard per-message length cap, a low
// max_tokens ceiling, and its own tighter rate limit (real Groq spend per
// call, tighter than the free-to-persist request-product route above).
const CUSTOMER_CONSULTATION_RATE_LIMIT = { windowMs: 10 * 60 * 1000, maxPerWindow: 8 };
const customerConsultationRateState = new Map();
const CUSTOMER_CONSULTATION_MESSAGE_MAX = 500;
const CUSTOMER_CONSULTATION_LOG_FILE = path.join(__dirname, 'data', 'consultation_log.jsonl');
const CONSULTATION_SYSTEM_PROMPT = `You are Galaxy Forge's pre-sales consultant. Your ONLY job: help a visitor articulate a business software problem clearly enough to submit as a real product request (compliance automation, workflow systems, customer operations tools, or similar B2B software).

Rules:
- Ask ONE clarifying question if their description is vague, or write a tightened 2-3 sentence version they could paste into a request form if it's already clear.
- Never invent pricing, timelines, or promises Galaxy Forge hasn't made elsewhere on this site.
- If asked about anything unrelated to describing a software need (general chat, other companies, personal advice, anything else), politely decline and redirect to describing their software problem.
- Keep replies under 100 words.`;

function isConsultationRateLimited(ip) {
  const now = Date.now();
  const windowStart = now - CUSTOMER_CONSULTATION_RATE_LIMIT.windowMs;
  const timestamps = (customerConsultationRateState.get(ip) || []).filter(t => t > windowStart);
  timestamps.push(now);
  customerConsultationRateState.set(ip, timestamps);
  if (customerConsultationRateState.size > 5000) customerConsultationRateState.clear();
  return timestamps.length > CUSTOMER_CONSULTATION_RATE_LIMIT.maxPerWindow;
}

app.post('/api/customer/consultation', async (req, res) => {
  try {
    const ip = req.ip || (req.socket && req.socket.remoteAddress) || 'unknown';
    if (isConsultationRateLimited(ip)) {
      return res.status(429).json({ success: false, error: 'too many messages — please try again later' });
    }
    if (!GROQ_KEY) {
      return res.status(503).json({ success: false, error: 'consultation temporarily unavailable' });
    }
    const message = String((req.body && req.body.message) || '').trim();
    if (!message) {
      return res.status(400).json({ success: false, error: 'message is required' });
    }
    if (message.length > CUSTOMER_CONSULTATION_MESSAGE_MAX) {
      return res.status(400).json({ success: false, error: `message exceeds ${CUSTOMER_CONSULTATION_MESSAGE_MAX} characters` });
    }

    const response = await groq.chat.completions.create({
      model: 'openai/gpt-oss-20b',
      max_tokens: 220,
      messages: [
        { role: 'system', content: CONSULTATION_SYSTEM_PROMPT },
        { role: 'user', content: message },
      ],
    });
    const reply = response.choices[0].message.content;

    // Every customer action must be logged (directive requirement 7) --
    // real, append-only, no PII beyond what the visitor typed themselves.
    try {
      fs.mkdirSync(path.dirname(CUSTOMER_CONSULTATION_LOG_FILE), { recursive: true });
      fs.appendFileSync(CUSTOMER_CONSULTATION_LOG_FILE, JSON.stringify({
        at: new Date().toISOString(), ip, message: message.slice(0, 500), reply: reply.slice(0, 1000),
      }) + '\n');
    } catch { /* logging failure never blocks the real reply */ }

    res.json({ success: true, reply });
  } catch (err) {
    res.status(500).json({ success: false, error: 'consultation temporarily unavailable — please try again' });
  }
});

app.post('/api/customer/request-product', (req, res) => {
  try {
    const ip = req.ip || (req.socket && req.socket.remoteAddress) || 'unknown';
    if (isRateLimited(ip)) {
      return res.status(429).json({ success: false, error: 'too many requests — please try again later' });
    }

    const body = req.body || {};
    // Honeypot: a real field named to look attractive to bots, invisible
    // to real users via customer_site's own CSS -- a non-empty value
    // means an automated submission, silently accepted-but-dropped
    // (never reveals to the caller that it was detected).
    if (body.website) {
      return res.json({ success: true, request_id: null });
    }

    const name = String(body.name || '').trim();
    const email = String(body.email || '').trim();
    const description = String(body.description || '').trim();
    const company = String(body.company || '').trim();
    const budgetRange = String(body.budget_range || '').trim();
    const productId = String(body.product_id || '').trim();

    if (!name || !email || !description) {
      return res.status(400).json({ success: false, error: 'name, email, and description are required' });
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return res.status(400).json({ success: false, error: 'a valid email address is required' });
    }
    for (const [field, value] of Object.entries({ name, email, description, company, budgetRange, productId })) {
      if (value.length > CUSTOMER_REQUEST_FIELD_MAX) {
        return res.status(400).json({ success: false, error: `${field} exceeds the maximum length` });
      }
    }

    // Commercial Readiness Report (2026-07-25), finding P1: validate
    // product_id against the REAL live catalog before persisting it --
    // never trust a client-supplied ID blindly, and never reject the
    // whole submission over a stale/bad one (fails open to the normal
    // custom-evaluation path in customer_pipeline.py instead).
    let catalogProductId = null;
    if (productId) {
      try {
        const products = fs.existsSync(PADDLE_PRODUCTS_FILE) ? JSON.parse(fs.readFileSync(PADDLE_PRODUCTS_FILE, 'utf8')) : [];
        if (Array.isArray(products) && products.some(p => p.product_id === productId)) {
          catalogProductId = productId;
        }
      } catch { /* malformed catalog file -- fail open, treat as no match */ }
    }

    // Optional: if the visitor is logged in, stamp their account_id onto
    // the request so it shows up in their real Customer History (Round 5)
    // -- guest (no-login) submission is completely unchanged, this never
    // requires an account.
    const authenticatedAccount = getAuthenticatedCustomerAccount(req);

    const requestId = 'req_' + crypto.randomBytes(8).toString('hex');
    const record = {
      request_id: requestId,
      submitted_at: new Date().toISOString(),
      name, email, company, description,
      budget_range: budgetRange || null,
      catalog_product_id: catalogProductId,
      account_id: authenticatedAccount ? authenticatedAccount.account_id : null,
      status: 'NEW',
    };
    fs.mkdirSync(path.dirname(CUSTOMER_REQUESTS_FILE), { recursive: true });
    fs.appendFileSync(CUSTOMER_REQUESTS_FILE, JSON.stringify(record) + '\n');

    telegramDirect.sendTelegramMessage(
      `📩 طلب عميل حقيقي جديد\nالاسم: ${name}\nالبريد: ${email}\nالشركة: ${company || '—'}\nالميزانية: ${budgetRange || '—'}\nالوصف: ${description.slice(0, 300)}`
    ).catch(() => {});

    res.json({ success: true, request_id: requestId });

    // ADR-130 (2026-07-25): fire real Qualification + Opportunity
    // Evaluation + Price Generation + Proposal immediately, without
    // making the customer's own submit request wait on a live Groq call
    // (observed 3-5 real minutes for similar evaluations elsewhere in
    // this factory). Fire-and-forget, generous timeout since nothing is
    // waiting on it -- if it's ever killed or crashes, the request stays
    // safely in NEW (customer_pipeline.py's state is only ever written
    // AFTER a real stage completes) and customer_pipeline.list_pipeline_
    // overview()'s stuck-NEW check surfaces it to the founder rather than
    // leaving it silently invisible.
    triggerCustomerPipelineAdvanceFireAndForget(requestId);
  } catch (err) {
    res.status(500).json({ success: false, error: 'could not submit request — please try again' });
  }
});

// ── Support Center (ADR-130, 2026-07-25) ──
// Real ticket intake -- same validation/honeypot/rate-limit/Telegram-
// notify shape as request-product above (deliberately not a new pattern),
// persisted to its own real, separate ledger since a support ticket and a
// sales request are different real workflows with different founder
// triage needs.
const CUSTOMER_SUPPORT_TICKETS_FILE = path.join(__dirname, 'data', 'support_tickets.jsonl');
app.post('/api/customer/support-ticket', (req, res) => {
  try {
    const ip = req.ip || (req.socket && req.socket.remoteAddress) || 'unknown';
    if (isRateLimited(ip)) {
      return res.status(429).json({ success: false, error: 'too many requests — please try again later' });
    }
    const body = req.body || {};
    if (body.website) {
      return res.json({ success: true, ticket_id: null });
    }
    const name = String(body.name || '').trim();
    const email = String(body.email || '').trim();
    const message = String(body.message || '').trim();
    const requestId = String(body.request_id || '').trim();

    if (!name || !email || !message) {
      return res.status(400).json({ success: false, error: 'name, email, and message are required' });
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return res.status(400).json({ success: false, error: 'a valid email address is required' });
    }
    for (const [field, value] of Object.entries({ name, email, message, requestId })) {
      if (value.length > CUSTOMER_REQUEST_FIELD_MAX) {
        return res.status(400).json({ success: false, error: `${field} exceeds the maximum length` });
      }
    }

    const ticketId = 'tix_' + crypto.randomBytes(8).toString('hex');
    const record = {
      ticket_id: ticketId, submitted_at: new Date().toISOString(),
      name, email, message, related_request_id: requestId || null, status: 'OPEN',
    };
    fs.mkdirSync(path.dirname(CUSTOMER_SUPPORT_TICKETS_FILE), { recursive: true });
    fs.appendFileSync(CUSTOMER_SUPPORT_TICKETS_FILE, JSON.stringify(record) + '\n');

    telegramDirect.sendTelegramMessage(
      `🎫 تذكرة دعم جديدة\nالاسم: ${name}\nالبريد: ${email}\n${requestId ? 'مرتبطة بطلب: ' + requestId + '\n' : ''}الرسالة: ${message.slice(0, 300)}`
    ).catch(() => {});

    res.json({ success: true, ticket_id: ticketId });
  } catch (err) {
    res.status(500).json({ success: false, error: 'could not submit ticket — please try again' });
  }
});

// Real, request_id-scoped status lookup -- request_id itself is the real
// bearer token (crypto.randomBytes(8) = 64 bits of entropy, generated
// server-side, never guessable), same trust model as any unlisted-link
// status page. Email is never included in the response (customer_
// pipeline.get_pipeline_status() strips it).
app.get('/api/customer/requests/:id', async (req, res) => {
  try {
    const result = await runCustomerPipelineCommand('status', { request_id: req.params.id });
    res.json(result);
  } catch (err) {
    res.status(404).json({ success: false, error: err.message });
  }
});

// CEO Review cycle (2026-07-25) finding: two concurrent approve calls for
// the SAME request_id (a double-click, or a client retry racing the first
// attempt) could both read stage=="PROPOSED" from disk before either
// finishes writing back -- customer_pipeline.py itself has no lock, so
// both would proceed into a real Payment Verification attempt, risking
// two real Paddle checkout transactions once the account unblocks (low
// financial risk -- a transaction isn't a charge until paid -- but a
// real, confusing duplicate-data/reputation issue). Small, safe,
// no architecture change: a per-request_id in-process lock, same
// mutual-exclusion idea as isActionRunning()/ACTION_JOBS above, scoped to
// these two customer-facing mutating actions only.
const customerRequestActionLocks = new Set();
function withCustomerRequestLock(requestId, fn) {
  if (customerRequestActionLocks.has(requestId)) {
    return Promise.reject(new Error('this request is already being processed — please wait a moment and check its status'));
  }
  customerRequestActionLocks.add(requestId);
  return Promise.resolve().then(fn).finally(() => customerRequestActionLocks.delete(requestId));
}

app.post('/api/customer/requests/:id/approve', async (req, res) => {
  try {
    const ip = req.ip || (req.socket && req.socket.remoteAddress) || 'unknown';
    if (isRateLimited(ip)) {
      return res.status(429).json({ success: false, error: 'too many requests — please try again later' });
    }
    // Contract acceptance (Round 2, 2026-07-29): approval doubles as a real
    // e-signature -- the typed name is the customer's acceptance of the
    // contract text shown on their status page, validated server-side in
    // customer_pipeline.py's approve_request().
    const acceptedName = String((req.body && req.body.accepted_name) || '').trim().slice(0, CUSTOMER_REQUEST_FIELD_MAX);
    const result = await withCustomerRequestLock(req.params.id, () => runCustomerPipelineCommand('approve', { request_id: req.params.id, accepted_name: acceptedName }));
    res.json(result);
  } catch (err) {
    res.status(400).json({ success: false, error: err.message });
  }
});

app.post('/api/customer/requests/:id/reject', async (req, res) => {
  try {
    const ip = req.ip || (req.socket && req.socket.remoteAddress) || 'unknown';
    if (isRateLimited(ip)) {
      return res.status(429).json({ success: false, error: 'too many requests — please try again later' });
    }
    const reason = String((req.body && req.body.reason) || '').trim().slice(0, CUSTOMER_REQUEST_FIELD_MAX);
    const result = await withCustomerRequestLock(req.params.id, () => runCustomerPipelineCommand('reject', { request_id: req.params.id, reason }));
    res.json(result);
  } catch (err) {
    res.status(400).json({ success: false, error: err.message });
  }
});

// Round 4 (2026-07-29): real download center -- same trust model as the
// status lookup above (request_id itself is the bearer token). The real
// local file path is resolved server-side only via customer_pipeline.py's
// get_download_path() and streamed directly -- it never appears in any
// client-visible JSON response, and books/ is never served as a public
// static directory.
app.get('/api/customer/requests/:id/download', async (req, res) => {
  try {
    const ip = req.ip || (req.socket && req.socket.remoteAddress) || 'unknown';
    if (isRateLimited(ip)) {
      return res.status(429).json({ success: false, error: 'too many requests — please try again later' });
    }
    const result = await runCustomerPipelineCommand('get_download_path', { request_id: req.params.id });
    res.download(result.path, result.filename || path.basename(result.path));
  } catch (err) {
    res.status(404).json({ success: false, error: err.message });
  }
});

// Real customer review -- same request_id-as-bearer-token trust model as
// the rest of this request's routes, gated server-side (customer_pipeline.
// submit_review()) on the real order actually being DELIVERED/FOLLOWED_UP,
// one per request, never editable after submission.
app.post('/api/customer/requests/:id/review', async (req, res) => {
  try {
    const ip = req.ip || (req.socket && req.socket.remoteAddress) || 'unknown';
    if (isRateLimited(ip)) {
      return res.status(429).json({ success: false, error: 'too many requests — please try again later' });
    }
    const rating = (req.body && req.body.rating);
    const text = String((req.body && req.body.text) || '').trim().slice(0, 1000);
    const result = await runCustomerPipelineCommand('submit_review', { request_id: req.params.id, rating, text });
    res.json(result);
  } catch (err) {
    res.status(400).json({ success: false, error: err.message });
  }
});

// Public, read-only real reviews for the site's "What customers say"
// section -- honest empty state until a real review exists (never a
// placeholder testimonial). Same pure-reader pattern lib/dashboard_data.js
// already uses everywhere else, reused (not duplicated) here.
app.get('/api/customer/reviews', (req, res) => {
  try {
    res.json({ success: true, ...dashboardData.readCustomerReviewsSummary() });
  } catch (err) {
    res.status(500).json({ success: false, error: 'reviews temporarily unavailable' });
  }
});

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

// Zero-assumption audit follow-up — Critical finding, fixed: this used to
// have no host argument, so Express/Node defaulted to binding ALL
// interfaces (confirmed via netstat: both 0.0.0.0:PORT and [::]:PORT were
// listening). Combined with ~20 routes that predate Mission Control's auth
// layer and have no authentication at all (some of them — /generate-book,
// /api/distribute, /api/scout/run — are also called internally by
// factory_loop.js over plain http://localhost with no auth cookie, so they
// cannot be retrofitted with Mission Control's cookie-based auth without
// breaking the automated production pipeline), this meant every one of
// those routes was reachable from the LAN, not just this machine — a much
// larger exposure than the network binding alone should have allowed.
// Binding to loopback only closes that reachability gap without touching
// any route's auth logic and without breaking factory_loop.js (which
// already calls http://localhost) or the UI (same-origin) — this is
// enforcing CLAUDE.md's own stated "everything local, no cloud"
// architecture at the network layer, not inventing a new one.
// BIND_HOST exists as an explicit, deliberate override for the day this
// factory really does need to be reachable beyond localhost — never set
// by default.
const BIND_HOST = process.env.BIND_HOST || '127.0.0.1';

// Enterprise Upgrade Roadmap Phase 1.1 (2026-07-23) — Critical finding,
// fixed: this process had zero process.on('uncaughtException'/
// 'unhandledRejection') handlers, so a single unhandled error anywhere
// in the request path silently killed the entire factory with no log,
// no alert, and (until scripts/supervisor.js, added alongside this)
// nothing to restart it. Logs the real error to a dedicated crash log
// (same flat, gitignored .log-at-repo-root convention as
// factory_loop.log/finance_errors.log — never invents a new logs/
// directory structure), best-effort alerts via the same real,
// already-tested Telegram path factory_loop.js's own critical-error
// alerting already uses (lib/telegram_direct.js — never a new alert
// channel), then exits non-zero so scripts/supervisor.js can tell a
// real crash apart from a clean, intentional shutdown and restart only
// the former.
const CRASH_LOG_PATH = path.join(__dirname, 'server_crashes.log');

function logCrash(kind, err) {
  const entry = {
    at: new Date().toISOString(),
    kind,
    message: err && err.message,
    stack: err && err.stack,
  };
  try {
    fs.appendFileSync(CRASH_LOG_PATH, JSON.stringify(entry) + '\n');
  } catch { /* a failing crash-log write must never block the crash-exit itself */ }
  return entry;
}

function handleFatal(kind, err) {
  const entry = logCrash(kind, err);
  console.error(`🚨 ${kind}:`, err && err.stack ? err.stack : err);
  const reasons = [`${kind}: ${entry.message || 'no error message'} — راجع server_crashes.log`];
  telegramDirect.sendTelegramMessage(telegramDirect.buildCriticalErrorMessage(reasons))
    .catch(() => {})
    .finally(() => process.exit(1));
  // Belt-and-suspenders: if the Telegram send hangs past its own
  // internal timeout for any reason, still exit — a stuck alert must
  // never keep a genuinely crashed process technically "running."
  setTimeout(() => process.exit(1), telegramDirect.DEFAULT_TIMEOUT_MS + 2000).unref();
}

process.on('uncaughtException', (err) => handleFatal('uncaughtException', err));
process.on('unhandledRejection', (reason) => {
  handleFatal('unhandledRejection', reason instanceof Error ? reason : new Error(String(reason)));
});

// Test-only fault injection (tests/test_server_crash_handlers.js): the
// only way to prove the two real handlers above actually fire in this
// real process, not a reimplementation of their logic in a test file.
// Gated behind an explicit, never-set-in-real-operation env var. The
// 'uncaughtException' case throws synchronously here, before
// app.listen() below ever runs, so that test never needs a live port at
// all; the 'unhandledRejection' case schedules a microtask, so
// app.listen() does start first in the same tick before the handler
// fires and exits — the test only asserts on the crash log and exit
// code, so this ordering doesn't matter for what it verifies.
if (process.env.__OPENCLAW_TEST_FORCE_CRASH__ === 'uncaughtException') {
  throw new Error('deliberate test crash (__OPENCLAW_TEST_FORCE_CRASH__)');
} else if (process.env.__OPENCLAW_TEST_FORCE_CRASH__ === 'unhandledRejection') {
  Promise.reject(new Error('deliberate test crash (__OPENCLAW_TEST_FORCE_CRASH__)'));
}

// Clean, intentional shutdown (Ctrl+C, or a supervisor's SIGTERM) exits
// 0 — the supervisor must never treat this as a crash worth restarting.
let shuttingDown = false;
function handleShutdownSignal(signal) {
  if (shuttingDown) return;
  shuttingDown = true;
  // Real bug found writing this feature's own test suite: console.log()
  // immediately followed by process.exit() can drop the write when
  // stdout is piped (not a TTY) rather than a real terminal — Node's
  // piped-stdout writes aren't guaranteed synchronous, and exit() can
  // race ahead of the flush. write()'s own completion callback is the
  // documented, correct fix: exit only once the bytes are actually out.
  process.stdout.write(`\n🛑 ${signal} received — shutting down cleanly\n`, () => process.exit(0));
}
process.on('SIGINT', () => handleShutdownSignal('SIGINT'));
process.on('SIGTERM', () => handleShutdownSignal('SIGTERM'));

// Test-only (tests/test_server_crash_handlers.js): emits a real SIGINT/
// SIGTERM event directly, decoupled from how the OS actually delivers
// one. Found live while writing this test: on Windows,
// child_process.kill('SIGTERM'/'SIGINT') unconditionally hard-terminates
// the target process (exit code null) rather than delivering a graceful
// signal these process.on() handlers can intercept — a real, documented
// Node-on-Windows platform limitation, not a bug in the handlers above.
// Real interactive Ctrl+C in an attached console (the actual, common
// solo-operator shutdown path) reaches process.on('SIGINT') correctly,
// same as any standard Node CLI tool on Windows — this only isn't
// reproducible from an automated, non-interactive test. What IS this
// code's own responsibility, and what this test-only hook verifies for
// real: that handleShutdownSignal() itself behaves correctly once Node
// actually emits the event, regardless of how it got there.
if (process.env.__OPENCLAW_TEST_EMIT_SHUTDOWN_SIGNAL__) {
  process.emit(process.env.__OPENCLAW_TEST_EMIT_SHUTDOWN_SIGNAL__);
}

app.listen(PORT, BIND_HOST, () => {
  console.log(`✅ Galaxy Forge — http://localhost:${PORT} (bound to ${BIND_HOST})`);
  console.log(`🔧 Static dir: ${path.join(__dirname)}`);
});
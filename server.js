const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
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

app.post('/api/mission-control/login', (req, res) => {
  if (!MISSION_CONTROL_PASSWORD) {
    return res.status(500).json({
      success: false,
      error: 'MISSION_CONTROL_PASSWORD غير مُعرَّف في .env — أضِفه أولاً (سطر واحد: MISSION_CONTROL_PASSWORD=...)',
    });
  }
  const { password } = req.body || {};
  if (password !== MISSION_CONTROL_PASSWORD) {
    return res.status(401).json({ success: false, error: 'كلمة مرور خاطئة' });
  }
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
function runPythonService(section, extraArgs = []) {
  return new Promise((resolve, reject) => {
    const pythonPath = detectPython();
    const scriptPath = path.join(__dirname, 'mission_control_api.py');
    const python = spawn(pythonPath, [scriptPath, section, ...extraArgs], { cwd: __dirname });
    let output = '', errOut = '', timedOut = false;
    killAfterTimeout(python, PYTHON_SERVICE_TIMEOUT_MS, () => { timedOut = true; });
    python.stdout.on('data', d => { output += d.toString(); });
    python.stderr.on('data', d => { errOut += d.toString(); });
    python.on('error', reject);
    python.on('close', () => {
      if (timedOut) return reject(new Error(`${section} timed out after ${PYTHON_SERVICE_TIMEOUT_MS}ms`));
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

async function publishingStatusService() {
  const production = await runPythonService('production');
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
    handler: () => runPythonService('opportunities'),
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
    handler: () => runPythonService('opportunity_pipeline'),
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
      return runPythonService('product_concept_comparison', [JSON.stringify({ niche })]);
    },
    health: pythonHealthCheck('product_concept_comparison'),
  },
  {
    name: 'decision-history',
    description: 'Every ACCEPTED/REJECTED/DEFERRED decision ever recorded, newest first, summary fields only.',
    reused: 'decision_engine/store.py read_decisions(), via mission_control_api.py.',
    handler: () => runPythonService('decision_history'),
    health: pythonHealthCheck('decision_history'),
  },
  {
    name: 'production-queue',
    description: 'Production dossiers for every ACCEPTED opportunity (pricing, assets, pre-production verification), plus the current pause/resume state (Phase 9).',
    reused: 'production_factory/factory.py run_production_factory(), via mission_control_api.py, plus server.js readProductionControl() (Phase 9 pause/resume flag).',
    handler: async () => ({ ...(await runPythonService('production')), production_control: readProductionControl() }),
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
    handler: () => runPythonService('revenue'),
    health: pythonHealthCheck('revenue'),
  },
  {
    name: 'automation-status',
    description: 'n8n workflow status from the last real exported definitions (n8n_workflows/*.fixed.json) — honestly labelled as a static export, not live state (n8n REST API still needs a manual login, BLOCKERS.md #1).',
    reused: 'mission_control_api.py\'s existing n8n_workflows/*.fixed.json reader.',
    handler: () => runPythonService('automation'),
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
    handler: () => runPythonService('system_configuration'),
    health: pythonHealthCheck('system_configuration'),
  },
  {
    name: 'recovery-status',
    description: 'Unified Recovery System (2026-07-18) dashboard: current in-flight task, recovery state, pending retries, last checkpoint, and the last real recovery action.',
    reused: 'factory_state.py load_state() + data/recovery_actions.jsonl, via mission_control_api.py.',
    handler: () => runPythonService('recovery'),
    health: pythonHealthCheck('recovery'),
  },
  {
    name: 'production-families',
    description: 'Universal Production Engine (2026-07-18): which of the 11 UPE product families have a real registered adapter today, under the founder-approved canonical family names, plus each manifest-driven family\'s real Product Manifest (Roadmap Step 3) — category, generators, pricing, supported marketplaces.',
    reused: 'product_families.registry + product_families.manifest, via mission_control_api.py — same data-driven discipline as production_factory/dossier.py\'s _product_type_capability().',
    handler: () => runPythonService('production_families'),
    health: pythonHealthCheck('production_families'),
  },
  {
    name: 'commercial-execution',
    description: 'Universal Production Engine (2026-07-19): the Commercial Execution Layer — which marketplaces are autonomous vs need real founder action right now (approval gates, computed off every arm\'s own live status()), plus the most recent real publish attempts from the ledger.',
    reused: 'commercial_execution.approval_gates + channels.ledger, via mission_control_api.py.',
    handler: () => runPythonService('commercial_execution'),
    health: pythonHealthCheck('commercial_execution'),
  },
  {
    name: 'ai-capability-registry',
    description: 'Real AI provider capability registry (Claude, GPT, Gemini, Grok, DeepSeek, Qwen, Mistral, local models, plus Groq itself) — Groq metrics computed live from data/ai_cost_log.jsonl (REAL where measured), every other provider honestly DISCOVERY-level until a credential exists and is actually called. Plus the append-only log of real department requests for a different/better model.',
    reused: 'ai_capability/registry.py list_providers()/read_capability_requests() (Autonomous Digital Company v1, Track B2, 2026-07-19), via mission_control_api.py.',
    handler: () => runPythonService('ai_capability'),
    health: pythonHealthCheck('ai_capability'),
  },
  {
    name: 'golden-hunter-status',
    description: "Golden Hunter Evolution -- real recent activity + top currently-scored opportunities, each with a real, informational pre-acceptance ROI estimate. Never changes the real accept/reject gate.",
    reused: 'mission_control_api.py _golden_hunter_status() (EOS Phase 2, 2026-07-19) -- reuses golden_opportunities.json, data/golden_hunter_events.jsonl, and revenue_pipeline.plan.estimate_pre_acceptance_roi() verbatim.',
    handler: () => runPythonService('golden_hunter_status'),
    health: pythonHealthCheck('golden_hunter_status'),
  },
  {
    name: 'pioneer-status',
    description: "Pioneer -- real discovery activity. Honestly discloses that Pioneer's candidates share the same event log as Golden Hunter (no separate Pioneer-only counter exists).",
    reused: 'mission_control_api.py _pioneer_status() (EOS Phase 2, 2026-07-19).',
    handler: () => runPythonService('pioneer_status'),
    health: pythonHealthCheck('pioneer_status'),
  },
  {
    name: 'knowledge-graph',
    description: "A real, queryable company memory -- nodes (Niche, Decision, ProductionRun, PublishChannel, AIProvider) and edges built fresh from 5 real data sources on every call. The Decision->ProductionRun edge is honestly labelled 'exact' (real production_id match) or 'approximate' (best-effort niche-text fallback) -- never presented as certain when it isn't.",
    reused: 'knowledge_graph/build.py build_graph() (EOS Phase 2, 2026-07-19) -- reuses data/decisions.jsonl, data/market_intelligence_analyses.jsonl, data/sales_ledger.jsonl, data/ai_cost_log.jsonl verbatim, no new data collection.',
    handler: () => runPythonService('knowledge_graph'),
    health: pythonHealthCheck('knowledge_graph'),
  },
  {
    name: 'department-health',
    description: "Per-named-department health rollup -- pure assembly of already-computed real signals (orchestrator engine success rates, channel approval status, real activity counts, AI provider status, infrastructure status, recovery/retry state). Researchers and Customer Intelligence are honestly 'no real data' -- never a fabricated score.",
    reused: 'department_health.py build_department_health() (EOS Phase 2, 2026-07-19) -- reuses executive_intelligence.engine_health, commercial_execution.approval_gates, ai_capability.registry, infrastructure_bridge.py, channels.ledger, and factory_state.py verbatim.',
    handler: () => runPythonService('department_health'),
    health: pythonHealthCheck('department_health'),
  },
  {
    name: 'research-department',
    description: "Real analysis assembled under 7 named research categories (Market, Competitor, Pricing, Publishing, Automation, Technology, Customer) -- pure assembly of already-real signals, no new analysis logic. Technology and Customer research are honestly 'Unknown' -- no module evaluates tech choices, and this factory has zero real customer data.",
    reused: 'research_department.py build_research_report() (EOS Phase 2, 2026-07-19) -- reuses market_intelligence_analyses.jsonl, competitor_discovery.py, profit_oracle.py constants, commercial_execution.approval_gates, and evolution_engine.py verbatim.',
    handler: () => runPythonService('research_department'),
    health: pythonHealthCheck('research_department'),
  },
  {
    name: 'ai-doctor',
    description: "The real, non-fabricated engineering-health system replacing quality_doctor.py's confirmed-fake pattern -- combines evolution_engine's bottleneck/tech-debt/ROI/capability-gap signals with real infrastructure status and a real (never-fabricated) dependency-pinning + npm-audit check.",
    reused: 'ai_doctor.py build_ai_doctor_report() (EOS Phase 2, 2026-07-19) -- reuses evolution_engine.py and infrastructure_bridge.py verbatim, no reimplementation.',
    handler: () => runPythonService('ai_doctor'),
    health: pythonHealthCheck('ai_doctor'),
  },
  {
    name: 'integration-registry',
    description: "Real, adapter-based extension points for every founder-named future vendor (n8n, GitHub, Notion, Slack, Discord, Cloudflare, Docker, Supabase, PostgreSQL, vector databases, Shopify, KDP, Perplexity, MiniMax, etc.), plus AI providers/commerce channels referenced from their own real registries -- never a second, duplicate source of truth for those. No live 'test connection' calls -- real env-var presence only.",
    reused: 'integration_registry.py list_integrations() (EOS Phase 2, 2026-07-19) -- references ai_capability/registry.py and channels/registry.py rather than duplicating them.',
    handler: () => runPythonService('integration_registry'),
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
    handler: () => runPythonService('evolution_report'),
    health: pythonHealthCheck('evolution_report'),
  },
  {
    name: 'market-review',
    description: "Weekly Market Review -- niches scanned, real opportunity-gap/customer-pain trend (period vs. all-time), and top rejection reasons. The one weekly Continuous Improvement Engine review type that had no real generator before EOS Phase 1.",
    reused: 'market_intelligence_core/market_review.py generate_market_review() (EOS Phase 1, 2026-07-19) -- reuses strategic_intelligence.rejection_patterns.most_frequent_rejection_reasons() verbatim, no reimplementation.',
    handler: () => runPythonService('market_review'),
    health: pythonHealthCheck('market_review'),
  },
  {
    name: 'strategic-recommendations',
    description: "Strategic Recommendations tab: strategic_intelligence's real decision-pattern/rejection/technical-debt report (ADR-054), previously only reachable bundled inside the combined executive report, plus the same real tool-integration proposals as tool-recommendations.",
    reused: 'strategic_intelligence/report.py generate_strategic_report() (ADR-054) + tool_intelligence/proposals.py, via mission_control_api.py.',
    handler: () => runPythonService('strategic_report'),
    health: pythonHealthCheck('strategic_report'),
  },
  {
    name: 'tool-recommendations',
    description: "Real, evidence-cited software/AI-tool integration proposals -- '(مقترَح، لا تنفيذ)' (proposed, not implemented), matching the existing ADR-024 convention. Every proposal is grounded in a real gap this factory's own audits found, with why/business-value/effort/ROI/dependencies/risks fields — never a generic tool pitch.",
    reused: 'tool_intelligence/proposals.py list_proposals() (Autonomous Digital Company v1, Track B3, 2026-07-19), via mission_control_api.py.',
    handler: () => runPythonService('tool_intelligence'),
    health: pythonHealthCheck('tool_intelligence'),
  },
  {
    name: 'infrastructure-status',
    description: "Real CPU/memory/disk (Node's os/fs modules) plus a real AI cost-rate trend over data/ai_cost_log.jsonl (this week's real spend vs. the real trailing daily average). No fabricated 'quota remaining' — Groq exposes no queryable quota API.",
    reused: 'lib/infrastructure_intelligence.js getInfrastructureStatus() (Autonomous Digital Company v1, Track B1, 2026-07-19) — pure os/fs + JSONL reads, no new dependency.',
    handler: async () => infrastructureIntelligence.getInfrastructureStatus(),
    health: fsHealthCheck(() => infrastructureIntelligence.getSystemResources(), 'os/fs resource read check ok'),
  },
];

// Renders SERVICE_LAYER_API.md straight from SERVICE_REGISTRY so the doc
// can never hand-drift from the real, live set of services — "API
// documentation generated automatically", not a hand-maintained file.
function generateServiceLayerDocs() {
  const lines = [
    '# OpenClaw Unified Service Layer — API Reference (v1)',
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

app.post('/api/trends', requireMissionControlAuth, async (req, res) => {
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

// ── QA CHECK ──
// Strategic Phase audit (2026-07-19): quality_doctor.py's "fixes_applied"
// list is fabricated — every _check_*() method appends a plausible-
// sounding fix string ("Increasing pages to 120", "Generated
// professional cover") without ever regenerating a page, drawing a
// cover, or touching a price; health_score is `100 - issues*15`, not
// derived from any real check. inspectors.py's Dual Inspection already
// does the real version of every one of these checks (real pypdf page
// counts, real Pillow cover dimensions, real profit_oracle pricing) and
// is what every actual product in this factory is gated on — this
// endpoint has zero real callers today (confirmed: no UI button, no
// pipeline stage). Left live (not removed — a behavior change needing
// founder sign-off, not a default cleanup) but now self-disclosing, so
// nothing built on top of it in the future can mistake it for a real
// QA gate.
app.post('/api/qa-check', requireMissionControlAuth, (req, res) => {
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
          res.json({
            success: true, ...result,
            warning: 'quality_doctor.py is a legacy prototype: its "fixes_applied" entries are fabricated (nothing is actually regenerated, redrawn, or repriced) and health_score/ready_to_publish are not derived from any real check. The real, load-bearing QA gate is inspectors.py\'s Dual Inspection — every actual generated product is gated on that, not this.',
          });
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

app.get('/health', async (req, res) => {
  res.json(await computeHealthStatus());
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
  console.log(`✅ OpenClaw Factory — http://localhost:${PORT} (bound to ${BIND_HOST})`);
  console.log(`🔧 Static dir: ${path.join(__dirname)}`);
});
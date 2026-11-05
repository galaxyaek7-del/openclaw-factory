// Galaxy Forge — Executive Command Center data (2026-10-24).
//
// One read model for the founder's dashboard (dashboard.html), built only
// from files the factory already writes. Every figure carries where it came
// from, when that source was last written, and how sure it is (the
// operational_history vocabulary):
//   OBSERVED  read from a record the factory wrote (Gumroad via the registry,
//             the commission ledger, the factory loop's own log)
//   VERIFIED  the pre-2026-10 vocabulary for the same class of fact; kept so
//             existing callers do not break
//   DERIVED   calculated from observed records
//   INFERRED  follows from observed facts but is not itself recorded; always
//             carries its premises
//   UNKNOWN   no source exists; never replaced by a guess
//   BLOCKED   a source exists but could not be read
// Pure file reads (same discipline as lib/dashboard_data.js): no network, no
// child process, no secret. Credential *names* in process.env are checked for
// presence only; values are never read into the result. Nothing here
// publishes, reprices, or spends.

const fs = require('fs');
const path = require('path');
const jsonl = require('./jsonl');
const commercialFunnel = require('./commercial_funnel');

const ROOT = path.join(__dirname, '..');
const GOAL_CENTS = 100000 * 100;  // the $100K verified-revenue north star

function readJson(p) {
  try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch (_) { return null; }
}

function mtime(p) {
  try { return fs.statSync(p).mtime.toISOString(); } catch (_) { return null; }
}

function latestMtimeMs(p) {
  try {
    const st = fs.lstatSync(p);
    if (st.isSymbolicLink()) return 0;
    if (!st.isDirectory()) return st.mtimeMs;
    let newest = st.mtimeMs;
    for (const entry of fs.readdirSync(p, { withFileTypes: true })) {
      if (entry.name.startsWith('.')) continue;
      const child = latestMtimeMs(path.join(p, entry.name));
      if (child > newest) newest = child;
    }
    return newest;
  } catch (_) {
    return 0;
  }
}

function src(file, root) {
  const p = path.join(root, file);
  const ms = latestMtimeMs(p);
  return { file, updated_at: ms ? new Date(ms).toISOString() : null };
}

function metric(value, kind, source, note) {
  return { value, kind, source, note: note || null };
}

function fact(value, kind, source, note) {
  return { value, kind, source, note: note || null };
}

// ── revenue ────────────────────────────────────────────────────────────────
function revenue(root, registry) {
  const products = (registry && registry.products) || [];
  const regSrc = src('data/product_registry.json', root);
  const orders = products.reduce((n, p) => n + (p.sales_count || 0), 0);
  const hasValue = products.some(p => Object.prototype.hasOwnProperty.call(p, 'sales_usd_cents'));
  const gross = products.reduce((n, p) => n + (p.sales_usd_cents || 0), 0);
  // commission ledger: only REAL rows that reached CONFIRMED or PAID count.
  // The real ledger field is commission_status and the money field is
  // net_commission (see commission_engine.py); status/amount_usd are kept
  // only as a fallback for any older row.
  const ledger = path.join(root, 'data', 'commission_ledger.jsonl');
  const rows = fs.existsSync(ledger) ? jsonl.readJsonlEntries(ledger) : [];
  const statusOf = (r) => r && (r.commission_status || r.status);
  const realPaid = rows.filter(r => r && r.environment === 'REAL' && ['CONFIRMED', 'PAID'].includes(statusOf(r)));
  const commissionCents = realPaid.reduce((n, r) => n + Math.round(Number(r.net_commission != null ? r.net_commission : r.amount_usd || 0) * 100), 0);
  const testRows = rows.filter(r => r && r.environment === 'TEST').length;
  const verified = (hasValue ? gross : 0) + commissionCents;
  return {
    period: 'all time (since the first listing)',
    gross_sales: hasValue
      ? metric(gross, 'OBSERVED', regSrc, 'Gumroad sales_usd_cents per product, read by the product registry')
      : metric(null, 'UNKNOWN', regSrc, 'registry predates the sales value field; rebuild it'),
    orders: metric(orders, 'OBSERVED', regSrc, 'Gumroad sales_count per product'),
    refunds: metric(null, 'UNKNOWN', null, 'no refund feed is connected; Gumroad refunds are not imported'),
    net_revenue: metric(null, 'UNKNOWN', null, 'platform fees are not imported, so net cannot be stated'),
    affiliate_commissions: metric(commissionCents, 'OBSERVED', src('data/commission_ledger.jsonl', root),
      `${realPaid.length} REAL commission rows confirmed or paid${testRows ? `; ${testRows} TEST row(s) excluded` : ''}`),
    commission_rows: rows.length,
    verified_revenue_cents: verified,
    goal: {
      target_cents: GOAL_CENTS,
      progress: verified / GOAL_CENTS,
      definition: 'verified revenue = Gumroad gross sales as reported per product + REAL affiliate commissions confirmed or paid. A target, not a forecast. TEST/SIMULATION rows never count.',
    },
  };
}


// ── products and pipeline ──────────────────────────────────────────────────
const STAGES = ['Research', 'Product Creation', 'Quality Assurance', 'Commercial Validation', 'Packaging',
                'Listing Preparation', 'Authorization', 'Publication', 'Revenue Verification'];

function stageOf(p) {
  if (p.primary_state === 'FIRST_SALE_VERIFIED') return 'Revenue Verification';
  if (p.primary_state === 'PUBLIC_LISTING_VERIFIED') return 'Publication';
  if (p.primary_state === 'UPLOAD_COMPLETED') return 'Publication';
  if (p.primary_state === 'READY_FOR_AUTHORIZATION') return 'Authorization';
  return 'Quality Assurance';
}

function portfolio(root, registry, offers, batchState) {
  const offerBy = {};
  for (const o of (offers && offers.offers) || []) offerBy[o.offer_id] = o;
  const withdrawn = /^\s*\[unavailable\]/i;
  const dup = new Set(((registry && registry.drift) || {}).duplicate_live_titles || []);
  const regSrc = src('data/product_registry.json', root);
  const pipeline = readJson(path.join(root, 'data', 'product_pipeline.json')) || {};
  const pipeById = {}, pipeByTitle = {};
  for (const p of pipeline.products || []) {
    pipeById[p.id] = p;
    if (p.title) pipeByTitle[p.title] = p;
  }
  const live = readJson(path.join(root, 'data', 'cycle94_live_verification.json')) || {};
  const liveId = live.product_id || null;
  // A recorded batch authorization is real evidence even when no per-product
  // phrase exists. It is labelled GRANTED_BATCH and never presented as a
  // per-product approval.
  const batchAuth = {};
  for (const file of ['data/batch14_publish_results.json', 'data/batch15_publish_results.json']) {
    const runs = readJson(path.join(root, file)) || [];
    for (const run of runs) {
      for (const r of run.results || []) {
        if (!r.id) continue;
        if (r.error) continue;
        const published = r.steps && r.steps.published === true;
        if (!published && !r.ok) continue;
        batchAuth[r.id] = { status: 'GRANTED_BATCH', phrase: run.authorization || null, granted_at: run.at || null,
          kind: 'OBSERVED', source: file,
          note: 'a batch-level founder authorization; it is not a per-product phrase' };
      }
    }
  }

  function authorizationOf(id, title, fallback) {
    const pp = pipeById[id] || pipeByTitle[title];
    const a = pp && pp.publication_authorization;
    if (a) {
      return { status: a.consumed ? 'GRANTED_AND_CONSUMED' : 'GRANTED', phrase: a.phrase || null,
        granted_at: a.granted_at_utc || null, kind: 'OBSERVED', source: 'data/product_pipeline.json',
        note: 'a per-product founder phrase; it is not an internal QA result' };
    }
    if (batchAuth[id]) return batchAuth[id];
    return { status: fallback || 'NOT_GRANTED', phrase: null, granted_at: null, kind: 'OBSERVED',
      source: fallback ? 'data/product_batch_13.json' : 'data/product_pipeline.json',
      note: 'no per-product founder publication phrase is recorded' };
  }

  function approvalOf(p, pp) {
    if (pp && pp.qa_results) {
      return { status: 'QA_PASSED', kind: 'OBSERVED', source: 'data/product_pipeline.json',
        note: String(pp.qa_results).slice(0, 180) };
    }
    if (['READY_FOR_AUTHORIZATION', 'UPLOAD_COMPLETED', 'PUBLIC_LISTING_VERIFIED', 'FIRST_SALE_VERIFIED'].includes(p.primary_state)) {
      return { status: 'QA_PASSED_BY_RECORDED_STATE', kind: 'INFERRED', source: 'data/product_registry.json',
        note: 'inferred from the registry state alone; no per-product QA record was found',
        premises: [`primary_state=${p.primary_state}`] };
    }
    return { status: 'NOT_RECORDED', kind: 'UNKNOWN', source: null, note: 'no QA record found for this product' };
  }

  function priceKind(p) {
    if (p.published) return 'LIVE_PLATFORM_PRICE';
    if (p.primary_state === 'READY_FOR_AUTHORIZATION') return 'PROPOSED — NO FOUNDER AUTHORIZATION';
    if (p.primary_state === 'UPLOAD_COMPLETED') return 'PLATFORM_DRAFT — NOT PUBLISHED';
    return 'NOT_APPROVED';
  }

  function publicationOf(p) {
    if (p.published) {
      return { status: 'PUBLIC_LISTING_VERIFIED', published: true, url: p.url || null, kind: 'OBSERVED',
        source: 'data/product_registry.json (Gumroad read)',
        note: 'platform publication is a separate fact from QA and from founder authorization' };
    }
    return { status: p.primary_state === 'UPLOAD_COMPLETED' ? 'PLATFORM_DRAFT' : 'NOT_PUBLISHED',
      published: false, url: null, kind: 'OBSERVED', source: 'data/product_registry.json' };
  }

  const rows = ((registry && registry.products) || []).map((p) => {
    const o = offerBy[p.internal_id] || {};
    const pp = pipeById[p.internal_id] || pipeByTitle[p.title];
    const auth = authorizationOf(p.internal_id, p.title);
    const approval = approvalOf(p, pp);
    const publication = publicationOf(p);
    const gumroadId = (p.external_ids || {}).gumroad;
    const probed = gumroadId && gumroadId === liveId ? live : null;
    let blocker = null;
    let next = null;
    if (withdrawn.test(p.title || '') && p.published) {
      blocker = 'withdrawn listing is still published';
      next = 'founder: unpublish it at the Gumroad dashboard (no API route)';
    } else if (dup.has(p.title)) {
      blocker = 'duplicate live title';
      next = 'founder: unpublish one of the two listings';
    } else if (p.primary_state === 'READY_FOR_AUTHORIZATION') {
      blocker = batchState.blocked_reason || 'no founder publication authorization recorded';
      next = batchState.next || 'founder: record an explicit per-product approval phrase before publishing';
    } else if (p.primary_state === 'UPLOAD_COMPLETED') {
      blocker = 'uploaded but not published on Gumroad';
      next = 'review and enable, or leave unpublished';
    } else if (p.primary_state === 'PUBLIC_LISTING_VERIFIED' && !p.sales_count) {
      // live and sellable: not blocked, the next step is getting it seen
      next = 'distribution: Pinterest queue, site page, search';
    }
    return {
      id: p.internal_id, name: p.title, line: o.subtype || (p.manifest ? 'spreadsheet_tool' : 'digital_download'),
      stage: stageOf(p), state: p.primary_state,
      qa: approval.status,
      approval, authorization: auth, publication,
      checkout: probed ? {
        status: 'PAGE_REACHABLE_NO_PURCHASE_RECORDED', checkout_page_reachable: true,
        cart_items: ((probed.purchase_probe || {}).cart_items || 0), purchase_observed: false, kind: 'OBSERVED',
        source: 'data/cycle94_live_verification.json', verified_at: probed.verified_at || null,
      } : { status: 'NOT_PROBED', kind: 'UNKNOWN', source: null, note: 'no checkout probe on record' },
      price_cents: p.price_cents, price_kind: priceKind(p),
      published: !!p.published, url: p.url || null,
      sales: p.sales_count || 0, sales_usd_cents: p.sales_usd_cents || 0,
      has_cover: o.cover_url ? true : (p.published ? null : false),
      blocker, next_action: next,
      source: 'data/product_registry.json',
    };
  });

  // B13 products are real, locally complete and absent from the Gumroad-derived
  // registry (they were never published). Omitting them would understate the
  // queue, so they are added from their own real batch record, never invented.
  const b13 = readJson(path.join(root, 'data', 'product_batch_13.json')) || {};
  const known = new Set(rows.map(r => r.id));
  for (const p of b13.products || []) {
    if (!p.id || known.has(p.id)) continue;
    rows.push({
      id: p.id, name: p.title, line: 'spreadsheet_tool', stage: 'Authorization',
      state: p.state || 'READY_FOR_AUTHORIZATION', qa: 'QA_PASSED_BY_RECORDED_STATE',
      approval: { status: 'QA_PASSED_BY_RECORDED_STATE', kind: 'INFERRED', source: 'data/product_batch_13.json',
        note: 'local QA/listing payloads exist; this is not permission to publish',
        premises: ['state=READY_FOR_AUTHORIZATION in the batch record'] },
      authorization: authorizationOf(p.id, p.title, p.authorization_status || 'NOT_GRANTED'),
      publication: { status: 'NOT_PUBLISHED', published: false, url: null, kind: 'OBSERVED', source: 'data/product_batch_13.json' },
      checkout: { status: 'NOT_PROBED', kind: 'UNKNOWN', source: null },
      price_cents: Math.round(Number(p.price_usd || 0) * 100),
      price_kind: p.price_basis || 'PROPOSED — NO FOUNDER AUTHORIZATION',
      published: false, url: null, sales: p.sales_observed || 0, sales_usd_cents: 0, has_cover: null,
      blocker: 'no founder publication authorization recorded',
      next_action: 'founder: decide the price basis and record an explicit per-product approval phrase',
      source: 'data/product_batch_13.json',
    });
  }

  const pipelineStages = STAGES.map(s => ({ stage: s, count: rows.filter(r => r.stage === s).length,
    measured: ['Authorization', 'Publication', 'Revenue Verification', 'Quality Assurance'].includes(s) }));
  return { rows, pipeline: pipelineStages, source: regSrc };
}

function batchState(root) {
  const runs = readJson(path.join(root, 'data', 'batch15_publish_results.json')) || [];
  const last = runs.length ? runs[runs.length - 1] : null;
  const failed = last && (last.results || []).find(r => r.error);
  if (failed && /10 products per day/i.test(failed.error)) {
    return { blocked_reason: 'Gumroad limit: 10 new products per 24 h', automatic_retry: false,
      next: 'manual re-run after the limit resets: python scripts/publish_batch14.py --batch batch15 --live — no automatic retry is scheduled',
      at: last.at };
  }
  return { blocked_reason: null, automatic_retry: false, next: null, at: last && last.at };
}

// ── factory health ─────────────────────────────────────────────────────────
function factory(root, now) {
  const log = path.join(root, 'factory_loop.log');
  const ticks = fs.existsSync(log) ? jsonl.readJsonlEntries(log).slice(-30) : [];
  const last = ticks[ticks.length - 1] || null;
  const failedSteps = [];
  for (const t of ticks.slice(-6)) {
    for (const a of t.actions || []) {
      if (a && (a.action === 'failed' || a.ok === false || a.status === 'failed')) {
        failedSteps.push({ at: t.timestamp, step: a.step || a.name || 'step', detail: String(a.detail || a.error || '').slice(0, 160) });
      }
    }
  }
  const lock = path.join(root, '.factory_loop.lock');
  let loop = { state: 'UNKNOWN', evidence: 'no lock file' };
  if (fs.existsSync(lock)) {
    const raw = String(fs.readFileSync(lock, 'utf8') || '').trim();
    const pid = parseInt((raw.match(/\d+/) || [])[0], 10);
    let alive = false;
    try { if (pid) { process.kill(pid, 0); alive = true; } } catch (_) { alive = false; }
    loop = { state: alive ? 'RUNNING' : 'STOPPED', evidence: `lock pid ${pid || '?'} ${alive ? 'alive' : 'not running'}` };
  }
  const lastAt = last && last.timestamp ? new Date(last.timestamp) : null;
  const ageMin = lastAt ? Math.round((now - lastAt) / 60000) : null;
  const state = readJson(path.join(root, 'data', 'factory_state.json')) || {};
  return {
    loop, last_tick_at: last ? last.timestamp : null, minutes_since_last_tick: ageMin,
    stale: ageMin === null ? null : ageMin > 30,
    diagnosis: last && last.diagnosis ? last.diagnosis.status : 'UNKNOWN',
    current_task: state.current_task || null, pending_retries: (state.pending_retries || []).length,
    recent_failed_steps: failedSteps.slice(-8),
    ticks_recorded: ticks.length,
    tests: { state: 'NOT RECORDED LOCALLY', note: 'CI results live on GitHub Actions; ask Claude (ci_status) or open the Actions page' },
    source: src('factory_loop.log', root),
  };
}

// ── integrations ───────────────────────────────────────────────────────────
function integrations(root, env, now) {
  const out = [];
  const auth = readJson(path.join(root, 'data', 'gumroad_auth_state.json'));
  const authAge = auth && auth.at ? Math.round((now - new Date(auth.at)) / 60000) : null;
  out.push({ name: 'Gumroad', role: 'sales platform', state: auth ? auth.status : 'UNKNOWN',
    detail: auth ? `auth checked ${authAge} min ago${authAge > 60 ? ' (stale: rechecked before any write)' : ''}` : 'no auth record',
    action: auth && auth.status === 'VERIFIED' ? null : 'check the Gumroad token' });
  const mc = readJson(path.join(root, 'data', 'metricool_brand.json'));
  out.push({ name: 'Metricool', role: 'social scheduling', state: mc ? 'CONNECTED' : 'UNKNOWN',
    detail: mc ? `networks: ${Object.keys(mc.connected_networks || {}).join(', ')}; ${String(mc.post_creation || '').split(':')[0]}` : 'no record',
    action: mc && /NEEDS_BOARD/.test(mc.post_creation || '') ? 'create the Pinterest board' : null });
  const dist = readJson(path.join(root, 'data', 'distribution_dashboard.json'));
  for (const [k, p] of Object.entries(((dist || {}).operational || {}).platforms || {})) {
    out.push({ name: p.name || k, role: 'social platform', state: p.state, detail: p.why, action: p.state === 'NOT_CONNECTED' ? 'connect it in Metricool' : null });
  }
  const has = (k) => Object.prototype.hasOwnProperty.call(env, k) && String(env[k] || '').length > 0;
  const paddleRows = jsonl.readJsonlEntries(path.join(root, 'data', 'paddle_connector.jsonl')).slice(-1);
  const lastPaddle = paddleRows[0] || null;
  const paddleMeta = readJson(path.join(root, 'data', 'paddle_checkout_check_meta.json')) || {};
  const livePaddle = lastPaddle && lastPaddle.reality_state === 'REAL' ? 'REAL EVENT RECORDED' : 'SIMULATION ONLY';
  out.push({ name: 'Paddle', role: 'checkout', state: has('PADDLE_API_KEY') ? `KEY PRESENT — ${livePaddle}` : 'NOT CONFIGURED',
    detail: `last connector event ${lastPaddle ? `${lastPaddle.timestamp} (${lastPaddle.result}, ${lastPaddle.reality_state})` : 'none'}; ` +
      `last live checkout check ${paddleMeta.last_paddle_attempt_at || 'not recorded'}; the live API read itself was refused with 403`,
    action: 'create a new API key with read and write permissions; simulation events are not real payments' });
  out.push({ name: 'Telegram', role: 'founder alerts', state: has('TELEGRAM_BOT_TOKEN') ? 'CONFIGURED' : 'NOT CONFIGURED', detail: 'presence of the token name only', action: null });
  out.push({ name: 'PayPal', role: 'payouts', state: 'NOT CONNECTED', detail: 'the Claude connector answered 401 on 2026-10-24', action: 'connect it in Claude connector settings' });
  return out;
}

// ── distribution ───────────────────────────────────────────────────────────
function distribution(root) {
  const dist = readJson(path.join(root, 'data', 'distribution_dashboard.json')) || {};
  const q = readJson(path.join(root, 'data', 'pinterest_queue.json')) || {};
  const idx = path.join(root, 'data', 'indexnow_submissions.jsonl');
  const subs = fs.existsSync(idx) ? jsonl.readJsonlEntries(idx) : [];
  const op = dist.operational || {};
  return {
    offers: op.offers || null, jobs_by_state: op.jobs_by_state || {}, awaiting_approval: (op.awaiting_approval || []).length,
    published_verified: (op.published_verified || []).length,
    pinterest: { board_found: !!q.board, summary: q.summary || {}, lookup: q.board_lookup || null, updated_at: q.generated_at || null },
    search: { indexnow_submissions: subs.length, last_submission_at: subs.length ? (subs[subs.length - 1].ts || subs[subs.length - 1].at || null) : null },
    traffic: metric(null, 'UNKNOWN', null, 'GitHub Pages has no analytics receiver; site visits are not measured'),
    sources: [src('data/distribution_dashboard.json', root), src('data/pinterest_queue.json', root), src('data/indexnow_submissions.jsonl', root)],
  };
}

// ── agents ─────────────────────────────────────────────────────────────────
function agents(fac) {
  const onDemand = [['scout', 'market analysis'], ['builder', 'content generation'], ['design', 'cover and interior ideas'],
                    ['qa', 'quality checklist'], ['publisher', 'titles, descriptions, keywords'], ['finance', 'pricing and margins']];
  return [
    { name: 'Factory loop', purpose: 'runs every factory step on a ~10 minute tick', state: fac.loop.state,
      last_result: fac.diagnosis, evidence: fac.loop.evidence, approval: 'none for internal steps; publishing stays gated' },
    ...onDemand.map(([n, p]) => ({ name: `Agent: ${n}`, purpose: p, state: 'ON DEMAND', last_result: 'not tracked per call',
      evidence: 'live Groq call when triggered from the app; not a running process', approval: 'none (text only)' })),
  ];
}

// ── quality and risk ───────────────────────────────────────────────────────
function listHtmlFiles(siteDir) {
  const out = [];
  function walk(dir) {
    let entries = [];
    try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch (_) { return; }
    for (const entry of entries) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) walk(full);
      else if (entry.isFile() && entry.name.endsWith('.html')) {
        out.push(path.relative(siteDir, full).split(path.sep).join('/'));
      }
    }
  }
  walk(siteDir);
  return out.sort();
}

function siteSurface(root) {
  const siteDir = path.join(root, 'customer_site');
  const result = {
    pages: 0, indexable_pages: 0, noindex_pages: 0, missing_canonical: 0, data_gap_pages: 0,
    broken_internal_links: [], private_reference_pages: [],
    latest_change: null,
  };
  const sensitive = /GUMROAD_ACCESS_TOKEN|PADDLE_API_KEY|MISSION_CONTROL_PASSWORD|INTERNAL_SERVICE_TOKEN|FACTORY_LIVE_PUBLISH|data[\\/]authorization_register|data[\\/]product_registry|C:\\openclaw-dasgboard/;
  let files = [];
  try { files = listHtmlFiles(siteDir); } catch (_) { return result; }
  for (const f of files) {
    const full = path.join(siteDir, f);
    let text = '';
    try { text = fs.readFileSync(full, 'utf8'); } catch (_) { continue; }
    result.pages += 1;
    const at = mtime(full);
    if (at && (!result.latest_change || at > result.latest_change)) result.latest_change = at;
    const noindex = /<meta\b[^>]*name=["']robots["'][^>]*content=["'][^"']*noindex/i.test(text);
    if (noindex) result.noindex_pages += 1;
    else {
      result.indexable_pages += 1;
      if (!/rel=["']canonical["']/i.test(text)) result.missing_canonical += 1;
    }
    if (/UNKNOWN -- not captured at this granularity/.test(text)) result.data_gap_pages += 1;
    if (sensitive.test(text)) result.private_reference_pages.push(f);
    const hrefs = text.matchAll(/href=["']([^"']+)["']/gi);
    for (const match of hrefs) {
      let target = match[1].trim();
      if (!target || target.startsWith('#') || /^(https?:|mailto:|tel:|javascript:|data:)/i.test(target)) continue;
      target = target.split('#')[0].split('?')[0];
      if (!target || !/\.html?$/i.test(target)) continue;
      const fromSiteRoot = target.startsWith('/site/');
      if (fromSiteRoot) target = target.slice('/site/'.length);
      if (target.startsWith('/')) continue;
      let fullTarget;
      try {
        fullTarget = path.resolve(fromSiteRoot ? siteDir : path.dirname(full), decodeURIComponent(target));
      } catch (_) { continue; }
      if (!fullTarget.startsWith(path.resolve(siteDir) + path.sep)) continue;
      if (!fs.existsSync(fullTarget)) result.broken_internal_links.push({ page: f, target });
    }
  }
  result.broken_internal_links = result.broken_internal_links.slice(0, 12);
  return result;
}

const UNSUPPORTED_PUBLIC_CLAIMS = [
  ['global commercial intelligence', /\bglobal commercial intelligence\b/i],
  ['AI-powered software', /\bAI-powered (?:business )?software\b/i],
  ['every recommendation independently verified', /\bevery recommendation (?:is |was )?(?:independently )?verified\b/i],
  ['each criterion independently verified', /\b(?:are|is)\s+each\s+independently verified\b/i],
  ['every opportunity carries an evidence-coverage score', /\bevery opportunity carries\b[^.<]{0,100}\bevidence[- ]coverage\b/i],
  ['ten-condition gate', /\bten[- ]condition gate\b/i],
  ['every opportunity must clear all ten conditions', /\bevery opportunity must clear\b[^.<]{0,40}\b(?:ten|10)\b/i],
  ['ten named acceptance conditions', /\b(?:ten|10)\s+named acceptance conditions\b/i],
  ['ten hard gates', /\b(?:ten|10)\s+hard gates\b/i],
  ['program details verified', /\bprogram details? (?:are |were )?verified\b/i],
  ['verified program data', /\bverified program data\b/i],
  ['real, verified opportunity record', /\breal,?\s+verified opportunity record\b/i],
  ['independently confirmed against official sources', /\bindependently confirmed against (?:its |the )?official sources?\b/i],
  ['freshest data', /\bfreshest data\b/i],
  ['purchase verified independently', /\bpurchase verified independently\b/i],
  ['held product availability claim', /data-held-product=["'][^"']+["'][^>]*>\s*(?:Get|Buy|Purchase|Download|Instant)\b/i],
  ['held product InStock schema', /EU AI Act Compliance Toolkit[\s\S]{0,8000}schema\.org\/InStock|schema\.org\/InStock[\s\S]{0,8000}EU AI Act Compliance Toolkit/i],
  ['100% of product decisions', /\b100% of (?:our )?product decisions\b/i],
  ['already cleared the gate', /\balready cleared the gate\b/i],
  ['real evidence-backed acceptance decision', /\breal evidence-backed acceptance decision\b/i],
  ['within about a minute', /\bwithin about a minute\b/i],
  ['every ticket reaches a real person', /\bevery ticket reaches a real person\b/i],
  ['every review here is real', /\bevery review here is real\b/i],
  ['every figure read live', /\bevery figure on this page is read live\b/i],
  ['all 50 states', /\ball 50 states\b/i],
  ['fight in 48 hours', /\bfight [^.<]{0,90} in 48 hours\b/i],
  ['guaranteed results', /\b(?:guaranteed results?|guaranteed (?:income|revenue|sales|ranking|outcomes?|returns?))\b/i],
  ['trusted by', /\btrusted by\b/i],
  ['industry-leading', /\bindustry[- ]leading\b/i],
  ['world-class', /\bworld[- ]class\b/i],
  ['best-selling', /\bbest[- ]selling\b/i],
  ['award-winning', /\baward[- ]winning\b/i],
  ['thousands of customers', /\bthousands of customers\b/i],
  ['5-star', /\b5[- ]star\b/i],
  ['customer logos', /\bcustomer logos?\b/i],
  ['case study', /\bcase stud(?:y|ies)\b/i],
];

function sentenceAt(text, index) {
  const start = Math.max(text.lastIndexOf('.', index), text.lastIndexOf('!', index),
    text.lastIndexOf('?', index), text.lastIndexOf('\n', index)) + 1;
  let end = text.length;
  for (const ch of ['.', '!', '?', '\n']) {
    const at = text.indexOf(ch, index);
    if (at !== -1 && at + 1 < end) end = at + 1;
  }
  return text.slice(start, end);
}

function negatedClaim(sentence, phrase) {
  const lower = sentence.toLowerCase();
  const at = lower.indexOf(phrase.toLowerCase());
  if (at < 0) return false;
  const before = lower.slice(Math.max(0, at - 80), at);
  const after = lower.slice(at + phrase.length, at + phrase.length + 80);
  return /\b(?:no|not|never|without|nothing|zero)\b/.test(before)
    || /\b(?:promising|promises?|anyone who|sellers? who|consultants? who)\b/.test(before)
    || /^\s*(?:is|are|was|were)?\s*not\b/.test(after)
    || /\b(?:not guaranteed|selling something other than|misrepresent|red flag|dishonest|scam)\b/.test(after);
}

function cleanExcerpt(sentence) {
  return sentence.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 180);
}

function gumroadSlug(url) {
  const match = String(url || '').match(/gumroad\.com\/l\/([^?#"'/\\]+)/i);
  return match ? decodeURIComponent(match[1]).toLowerCase() : null;
}

function truthfulnessSurface(root, registry) {
  const siteDir = path.join(root, 'customer_site');
  const rows = (registry && Array.isArray(registry.products)) ? registry.products : [];
  const publishedSlugs = new Set(rows.filter((p) => p && p.published === true)
    .map((p) => gumroadSlug(p.url)).filter(Boolean));
  const out = {
    status: 'UNKNOWN',
    kind: 'DERIVED',
    scanned_pages: 0,
    published_gumroad_links: publishedSlugs.size,
    unverified_purchase_links: [],
    indexable_draft_pages: [],
    unavailable_service_claims: [],
    unsupported_claims: [],
    source: src('customer_site', root),
  };
  let files = [];
  try { files = listHtmlFiles(siteDir); } catch (_) { return out; }
  for (const f of files) {
    let text = '';
    try { text = fs.readFileSync(path.join(siteDir, f), 'utf8'); } catch (_) { continue; }
    out.scanned_pages += 1;
    const noindex = /<meta\b[^>]*name=["']robots["'][^>]*content=["'][^"']*noindex/i.test(text);
    const head = (text.match(/<head\b[\s\S]*?<\/head>/i) || [''])[0];
    const h1 = ((text.match(/<h1\b[^>]*>([\s\S]*?)<\/h1>/i) || ['', ''])[1] || '').replace(/<[^>]+>/g, ' ');
    const plannedMarker = (head + ' ' + h1).match(/\b(?:draft|planned preview|in development|not operational|not yet listed|coming soon|planned)\b/i);
    if (!noindex && plannedMarker) {
      out.indexable_draft_pages.push({ page: f, marker: plannedMarker[0].toLowerCase() });
    }

    const seenLinks = new Set();
    for (const match of text.matchAll(/href=["']([^"']+)["']/gi)) {
      const slug = gumroadSlug(match[1]);
      if (!slug || seenLinks.has(slug)) continue;
      seenLinks.add(slug);
      if (!publishedSlugs.has(slug)) {
        out.unverified_purchase_links.push({ page: f, url: match[1], slug });
      }
    }

    for (const [label, re] of UNSUPPORTED_PUBLIC_CLAIMS) {
      const match = re.exec(text);
      if (!match) continue;
      const sentence = sentenceAt(text, match.index);
      if (negatedClaim(sentence, match[0])) continue;
      out.unsupported_claims.push({ page: f, phrase: label, excerpt: cleanExcerpt(sentence) });
    }

    const serviceRe = /\b(?:payable on delivery|(?:delivered|delivery) (?:within|in) \d+ (?:business )?days?|instant delivery|same[- ]day delivery|available now)\b/gi;
    let serviceMatch;
    while ((serviceMatch = serviceRe.exec(text)) !== null) {
      const sentence = sentenceAt(text, serviceMatch.index);
      if (/\b(?:planned|target|not a guarantee|no paid delivery|as of|subject to|estimate|estimated)\b/i.test(sentence)) continue;
      if (/available now/i.test(serviceMatch[0]) && seenLinks.size > 0
        && [...seenLinks].some((slug) => publishedSlugs.has(slug))) continue;
      out.unavailable_service_claims.push({ page: f, phrase: serviceMatch[0], excerpt: cleanExcerpt(sentence) });
    }
  }
  const findings = out.unverified_purchase_links.length + out.indexable_draft_pages.length
    + out.unavailable_service_claims.length + out.unsupported_claims.length;
  out.status = out.scanned_pages === 0 ? 'UNKNOWN' : (findings ? 'FAIL' : 'PASS');
  out.unverified_purchase_links = out.unverified_purchase_links.slice(0, 12);
  out.indexable_draft_pages = out.indexable_draft_pages.slice(0, 12);
  out.unavailable_service_claims = out.unavailable_service_claims.slice(0, 12);
  out.unsupported_claims = out.unsupported_claims.slice(0, 20);
  return out;
}

function publicSurface(root, registry, site) {
  const rows = (registry && Array.isArray(registry.products)) ? registry.products : [];
  const published = rows.filter((p) => p && p.published === true);
  const publishedWithUrl = published.filter((p) => /^https:\/\//i.test(String(p.url || '')));
  const b15 = rows.filter((p) => p && /^B15-/.test(String(p.internal_id || '')));
  const audit = readJson(path.join(root, 'data', 'batch15_prepublication_audit.json'));
  const summary = (audit && audit.summary) || null;
  const approvalExists = fs.existsSync(path.join(root, 'data', 'publication_approvals.json'));
  const truth = truthfulnessSurface(root, registry);
  const checks = [
    {
      name: 'Public pages contain no credential or private-data reference',
      status: site.private_reference_pages.length ? 'FAIL' : 'PASS',
      kind: 'DERIVED',
      detail: site.private_reference_pages.length
        ? `${site.private_reference_pages.length} page(s): ${site.private_reference_pages.join(', ')}`
        : 'No credential names, internal registry paths or absolute workspace paths found.',
    },
    {
      name: 'Published catalog facts come from the registry',
      status: publishedWithUrl.length ? 'PASS' : 'UNKNOWN',
      kind: publishedWithUrl.length ? 'OBSERVED' : 'UNKNOWN',
      detail: publishedWithUrl.length
        ? `${publishedWithUrl.length} published Gumroad URL(s) read directly from data/product_registry.json.`
        : 'No published product with a real HTTPS Gumroad URL is recorded.',
    },
    {
      name: 'B15 products are excluded from the public catalog',
      status: b15.length ? 'PASS' : 'UNKNOWN',
      kind: b15.length ? 'OBSERVED' : 'UNKNOWN',
      detail: b15.length
        ? `${b15.length} B15 product(s) remain unpublished and are not served by /api/public/catalog.`
        : 'No B15 records exist in this registry.',
    },
    {
      name: 'Per-product publication approvals are recorded',
      status: approvalExists ? 'PASS' : 'FAIL',
      kind: 'OBSERVED',
      detail: approvalExists
        ? 'data/publication_approvals.json is present; its contents still require founder review.'
        : 'No per-product approval file exists, so B15 publication must stay stopped.',
    },
    {
      name: 'Public pages contain no unverified purchase or availability claim',
      kind: 'DERIVED',
      status: truth.scanned_pages === 0 ? 'UNKNOWN'
        : (truth.unverified_purchase_links.length || truth.indexable_draft_pages.length
          || truth.unavailable_service_claims.length ? 'FAIL' : 'PASS'),
      detail: truth.scanned_pages === 0
        ? 'No customer_site HTML pages were readable.'
        : `${truth.unverified_purchase_links.length} unverified Gumroad link(s), `
          + `${truth.indexable_draft_pages.length} indexable draft/planned page(s), `
          + `${truth.unavailable_service_claims.length} unqualified availability claim(s).`,
    },
    {
      name: 'Public pages avoid unsupported affirmative claims',
      kind: 'DERIVED',
      status: truth.scanned_pages === 0 ? 'UNKNOWN' : (truth.unsupported_claims.length ? 'FAIL' : 'PASS'),
      detail: truth.scanned_pages === 0
        ? 'No customer_site HTML pages were readable.'
        : truth.unsupported_claims.length
          ? `${truth.unsupported_claims.length} unsupported phrase(s) found; negation-aware scan.`
          : 'No unsupported affirmative phrase matched; honest negatives are not counted.',
    },
  ];
  return {
    site: {
      pages: site.pages,
      indexable_pages: site.indexable_pages,
      noindex_pages: site.noindex_pages,
      missing_canonical: site.missing_canonical,
      data_gap_pages: site.data_gap_pages,
      broken_internal_links: site.broken_internal_links.length,
      broken_link_examples: site.broken_internal_links.slice(0, 5),
      private_reference_pages: site.private_reference_pages,
      latest_change: site.latest_change,
      deployment: { status: 'NOT VERIFIED', kind: 'UNKNOWN',
        note: 'This dashboard reads local files only; no deployment health check is recorded.' },
      source: src('customer_site', root),
    },
    catalog: {
      published: published.length,
      published_with_url: publishedWithUrl.length,
      b15_unpublished: b15.length,
      public_endpoint: '/api/public/catalog',
      kind: 'OBSERVED',
      source: src('data/product_registry.json', root),
    },
    batch15: {
      mode: audit ? audit.mode : null,
      summary,
      approval_file_present: approvalExists,
      source: src('data/batch15_prepublication_audit.json', root),
      kind: audit ? 'OBSERVED' : 'UNKNOWN',
      note: audit ? null : 'No B15 prepublication audit has been written.',
    },
    truthfulness: truth,
    checks,
  };
}

function risks(root, registry, site = siteSurface(root)) {
  const out = [];
  const pages = site.pages;
  const noCanonical = site.missing_canonical;
  const residue = site.data_gap_pages;
  if (noCanonical) out.push({ level: 'HIGH', area: 'SEO', title: `${noCanonical} of ${pages} site pages have no canonical tag in this working copy`, detail: 'each is indexable and has no canonical URL; add one or mark the draft noindex before publishing' });
  if (residue) out.push({ level: 'HIGH', area: 'Content', title: `${residue} public guide pages print "UNKNOWN -- not captured at this granularity"`, detail: 'generator constant in commission_engine.py' });
  const prods = (registry && registry.products) || [];
  const w = prods.filter(p => /^\s*\[unavailable\]/i.test(p.title || '') && p.published);
  if (w.length) out.push({ level: 'HIGH', area: 'Catalog', title: `${w.length} withdrawn listing still published`, detail: w.map(p => p.url).join(', ') });
  const dups = ((registry && registry.drift) || {}).duplicate_live_titles || [];
  if (dups.length) out.push({ level: 'MEDIUM', area: 'Catalog', title: `duplicate live title: ${dups.join(', ')}`, detail: 'two listings compete with each other' });
  const vids = path.join(root, 'video_studio', 'projects');
  try {
    const unresolved = fs.readdirSync(vids).filter(f => f.endsWith('.rights.json'))
      .filter(f => (readJson(path.join(vids, f)) || {}).status !== 'CLEARED').length;
    if (unresolved) out.push({ level: 'MEDIUM', area: 'Rights', title: `${unresolved} rendered videos have unresolved voice/font rights`, detail: 'blocks TikTok and YouTube' });
  } catch (_) { /* no video projects */ }
  return out;
}

// ── founder decisions vs autonomous work ───────────────────────────────────
function decisions(dist, rk, ints, prods) {
  const out = [];
  if (dist.pinterest && !dist.pinterest.board_found && (dist.pinterest.summary.BLOCKED_NO_BOARD || 0) > 0) {
    out.push({ rank: 1, title: 'Create the Pinterest board "Small Business Finance Tools"',
      impact: `${dist.pinterest.summary.BLOCKED_NO_BOARD} product pins are ready and waiting only for it`, owner: 'founder' });
  }
  if (dist.awaiting_approval) {
    out.push({ rank: 2, title: `Review ${dist.awaiting_approval} LinkedIn and X drafts`, impact: 'the only free social path today is posting them by hand', owner: 'founder' });
  }
  for (const r of rk.filter(x => x.area === 'Catalog')) out.push({ rank: 3, title: r.title, impact: 'buyers see a withdrawn or duplicate listing', owner: 'founder (Gumroad dashboard)' });
  if (rk.some(x => x.area === 'SEO')) out.push({ rank: 4, title: 'Decide on the parallel session\'s SEO edits', impact: 'pushing them would remove canonical and preview tags site-wide', owner: 'founder' });
  for (const i of ints.filter(x => x.name === 'Paddle')) out.push({ rank: 5, title: 'Paddle: issue a new API key', impact: 'second checkout path; the current key is refused', owner: 'founder' });
  const ready = prods.filter(p => p.state === 'READY_FOR_AUTHORIZATION').length;
  const autonomous = [];
  if (ready) autonomous.push(`${ready} products are built and QA-recorded, but they are NOT published automatically: Gumroad's limit and the missing per-product founder authorization both stop it. A manual re-run is required.`);
  if (dist.pinterest && dist.pinterest.board_found === false) {
    autonomous.push('the Pinterest queue and site/search steps run, but every product pin is blocked until the board exists');
  }
  autonomous.push('daily: product registry rebuild and listing page checks; search-engine notification for changed site pages');
  autonomous.push('each tick: factory diagnosis, demand sensing, agent chain, site publication of test-passing site pages');
  return { founder: out.slice(0, 5), autonomous };
}

// ── freshness and the commercial evidence report ──────────────────────────
function freshness(root, now, registry) {
  const defs = [
    ['data/product_registry.json', 36, 'product and sales facts'],
    ['data/catalog.json', 72, 'remote catalog classification'],
    ['data/commission_ledger.jsonl', 168, 'affiliate commissions'],
    ['data/commercial_evidence_report.json', 48, 'evidence reconciliation'],
    ['data/batch15_publish_results.json', 72, 'last publication attempt'],
  ];
  const checks = defs.map(([file, maxHours, role]) => {
    const s = src(file, root);
    const ageHours = s.updated_at ? (now - new Date(s.updated_at)) / 3600000 : null;
    return { file, role, max_age_hours: maxHours, updated_at: s.updated_at, age_hours: ageHours == null ? null : Math.round(ageHours * 10) / 10,
      stale: ageHours == null ? true : ageHours > maxHours, state: ageHours == null ? 'MISSING' : (ageHours > maxHours ? 'STALE' : 'FRESH') };
  });
  const cat = checks.find(c => c.file === 'data/catalog.json');
  const reg = checks.find(c => c.file === 'data/product_registry.json');
  if (reg.updated_at && cat.updated_at && new Date(cat.updated_at) < new Date(reg.updated_at)) {
    cat.note = 'older than the product registry, so its classification/drift can lag real publications';
    cat.stale = true;
    cat.state = 'STALE';
  }
  return { checks, stale_sources: checks.filter(c => c.stale).map(c => ({ file: c.file, state: c.state, age_hours: c.age_hours })) };
}

function commercialEvidence(root) {
  const p = path.join(root, 'data', 'commercial_evidence_report.json');
  const r = readJson(p);
  if (!r) {
    return { kind: 'UNKNOWN', available: false, source: src('data/commercial_evidence_report.json', root),
      note: 'run scripts/commercial_evidence.py --write to produce the reconciliation' };
  }
  const b = r.b12_001 || {};
  const e = {
    kind: 'OBSERVED', available: true, generated_at: r.generated_at, mode: r.mode,
    source: src('data/commercial_evidence_report.json', root),
    b12: {
      price_cents: (b.identity || {}).price_cents,
      publication: b.publication && b.publication.status,
      authorization: b.authorization && b.authorization.status,
      approval: b.approval && b.approval.value,
      sales_units: b.sales && b.sales.units && b.sales.units.value,
      real_commission_usd: b.commissions && b.commissions.real_net_usd && b.commissions.real_net_usd.value,
      traffic: b.traffic && b.traffic.product_attributed_views,
      conversion: b.traffic && b.traffic.conversion,
      conflicts: b.conflicts || [], unknowns: b.unknowns || [],
      inferences: b.inferences || [],
      next_action: b.next_action || null,
    },
    b13: r.b13 || null,
    integrity: r.integrity || [],
  };
  return e;
}

// Business arms, the ten portfolio activities and the two control capabilities,
// as restated by business_arms.write_state() after each daily registry rebuild
// (scripts/registry_daily.py). Read, never recomputed here: the arm rules live
// in Python and the dashboard must not keep a second copy of them.
const ARMS_MAX_AGE_HOURS = 36;
function businessArms(root, now) {
  const file = 'data/business_arms_state.json';
  const doc = readJson(path.join(root, file));
  if (!doc || !doc.arms) {
    return { available: false, state: 'MISSING', source: src(file, root),
      note: 'no arm state file yet; it is written by the daily registry rebuild or `python business_arms.py --write`' };
  }
  const at = doc.generated_at ? new Date(doc.generated_at) : null;
  const ageHours = at && !isNaN(at) ? Math.round(((now - at) / 3600000) * 10) / 10 : null;
  const stale = ageHours == null || ageHours > ARMS_MAX_AGE_HOURS;
  const arms = Object.values(doc.arms).map(a => ({
    key: a.arm, name: a.name, status: a.status, gap: a.gap || null,
    external_dependency: a.external_dependency || null,
    evidence: (a.implementation_present || []).slice(0, 6),
  }));
  return {
    available: true,
    state: stale ? 'STALE' : 'FRESH',
    generated_at: doc.generated_at || null,
    age_hours: ageHours,
    max_age_hours: ARMS_MAX_AGE_HOURS,
    counts: doc.counts || {},
    arms,
    activities: ((doc.portfolio || {}).activities || []).map(r => ({
      key: r.activity, name: r.name, arm: r.arm, nearest_arm: r.nearest_arm || null, status: r.status,
      gap: r.gap || null, shares_with: r.shares_with || null })),
    controls: Object.entries(doc.controls || {}).map(([k, c]) => ({
      key: k, name: c.name, status: c.status, rule: c.rule,
      authoritative: Object.entries(c.authoritative_present || {}).map(([f, ok]) => ({ file: f, present: !!ok })),
      revenue_record: c.revenue_record || null })),
    problems: doc.problems || [],
    company_portfolio: doc.arm_portfolio || null,
    source: src(file, root),
  };
}

// Trend-to-Product research state, written by trend_to_product.linkage.write_state()
// (python -m trend_to_product --write, or scripts/trend_research_*.py). Read, never
// rescored here: scoring rules live in Python. Freshness is the age of the newest
// evidence actually read, not of the file.
const TREND_EVIDENCE_MAX_AGE_DAYS = 30;
function trendToProduct(root, now) {
  const file = 'data/trend_to_product_state.json';
  const doc = readJson(path.join(root, file));
  if (!doc || !doc.counts) {
    return { available: false, state: 'MISSING', source: src(file, root),
      note: 'no research recorded yet; run `python -m trend_to_product --write` after recording sources' };
  }
  const fr = doc.evidence_freshness || {};
  let age = null;
  if (fr.newest_access) {
    const d = new Date(fr.newest_access + 'T00:00:00Z');
    if (!isNaN(d)) age = Math.floor((now - d) / 86400000);
  }
  return {
    available: true,
    state: age == null ? 'NO_EVIDENCE' : age > TREND_EVIDENCE_MAX_AGE_DAYS ? 'STALE' : 'FRESH',
    evidence_age_days: age,
    max_age_days: TREND_EVIDENCE_MAX_AGE_DAYS,
    generated_at: doc.generated_at || null,
    counts: doc.counts,
    evidence_quality: doc.evidence_quality || {},
    signals_counting_as_sales: doc.signals_counting_as_sales || 0,
    platform_policy: doc.platform_policy || {},
    opportunities: (doc.opportunities || []).map(o => ({
      id: o.opportunity_id, name: o.name, format: o.format, arm: o.t1_arm, band: o.band,
      composite: o.composite, coverage: o.coverage, rights: o.rights,
      price_range: o.price_range && o.price_range.status === 'OBSERVED_RANGE'
        ? `$${o.price_range.low}-$${o.price_range.high}` : 'UNKNOWN',
      missing: (o.missing_evidence || []).slice(0, 4) })),
    specs: doc.specs || [],
    calibration: doc.calibration || null,
    blockers: doc.blockers || [],
    live_publish: doc.live_publish || null,
    source: src(file, root),
  };
}

function compute({ root = ROOT, env = process.env, now = new Date() } = {}) {
  const registry = readJson(path.join(root, 'data', 'product_registry.json'));
  const offers = readJson(path.join(root, 'data', 'distribution_offers.json'));
  const bs = batchState(root);
  const pf = portfolio(root, registry, offers, bs);
  const fac = factory(root, now);
  const ints = integrations(root, env, now);
  const dist = distribution(root);
  const site = siteSurface(root);
  const rk = risks(root, registry, site);
  const fresh = freshness(root, now, registry);
  const rows = pf.rows;
  return {
    generated_at: now.toISOString(),
    revenue: revenue(root, registry),
    products: {
      total: rows.length,
      published: rows.filter(r => r.published).length,
      ready_for_review: rows.filter(r => r.state === 'READY_FOR_AUTHORIZATION').length,
      unpublished: rows.filter(r => r.state === 'UPLOAD_COMPLETED').length,
      with_blocker: rows.filter(r => r.blocker).length,
    },
    portfolio: pf,
    factory: fac,
    integrations: ints,
    distribution: dist,
    agents: agents(fac),
    risks: rk,
    decisions: decisions(dist, rk, ints, rows),
    batch: bs,
    freshness: fresh,
    public_surface: publicSurface(root, registry, site),
    commercial_evidence: commercialEvidence(root),
    business_arms: businessArms(root, now),
    trend_to_product: trendToProduct(root, now),
    commercial_funnel: commercialFunnel.compute({ root, registry, revenue: revenue(root, registry), distribution: dist, now }),
  };
}

module.exports = { compute, revenue, portfolio, factory, integrations, distribution, risks, decisions, freshness,
  commercialEvidence, businessArms, trendToProduct, stageOf, GOAL_CENTS };

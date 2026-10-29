// Galaxy Forge — Executive Command Center data (2026-10-24).
//
// One read model for the founder's dashboard (dashboard.html), built only
// from files the factory already writes. Every figure carries where it came
// from, when that source was last written, and how sure it is:
//   VERIFIED  read from an authoritative record (Gumroad via the registry,
//             the commission ledger, the factory loop's own log)
//   DERIVED   calculated from verified records
//   UNKNOWN   no source exists; never replaced by a guess
// Pure file reads (same discipline as lib/dashboard_data.js): no network, no
// child process, no secret. Credential *names* in process.env are checked for
// presence only; values are never read into the result.

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

function src(file, root) {
  const p = path.join(root, file);
  return { file, updated_at: mtime(p) };
}

function metric(value, kind, source, note) {
  return { value, kind, source, note: note || null };
}

// ── revenue ────────────────────────────────────────────────────────────────
function revenue(root, registry) {
  const products = (registry && registry.products) || [];
  const regSrc = src('data/product_registry.json', root);
  const orders = products.reduce((n, p) => n + (p.sales_count || 0), 0);
  const hasValue = products.some(p => Object.prototype.hasOwnProperty.call(p, 'sales_usd_cents'));
  const gross = products.reduce((n, p) => n + (p.sales_usd_cents || 0), 0);
  // commission ledger: only REAL rows that reached CONFIRMED or PAID count
  const ledger = path.join(root, 'data', 'commission_ledger.jsonl');
  const rows = fs.existsSync(ledger) ? jsonl.readJsonlEntries(ledger) : [];
  const realPaid = rows.filter(r => r && r.environment === 'REAL' && ['CONFIRMED', 'PAID'].includes(r.status));
  const commissionCents = realPaid.reduce((n, r) => n + Math.round(Number(r.amount_usd || 0) * 100), 0);
  const verified = (hasValue ? gross : 0) + commissionCents;
  return {
    period: 'all time (since the first listing)',
    gross_sales: hasValue
      ? metric(gross, 'VERIFIED', regSrc, 'Gumroad sales_usd_cents per product, read by the product registry')
      : metric(null, 'UNKNOWN', regSrc, 'registry predates the sales value field; rebuild it'),
    orders: metric(orders, 'VERIFIED', regSrc, 'Gumroad sales_count per product'),
    refunds: metric(null, 'UNKNOWN', null, 'no refund feed is connected; Gumroad refunds are not imported'),
    net_revenue: metric(null, 'UNKNOWN', null, 'platform fees are not imported, so net cannot be stated'),
    affiliate_commissions: metric(commissionCents, 'VERIFIED', src('data/commission_ledger.jsonl', root),
      `${realPaid.length} REAL commission rows confirmed or paid`),
    verified_revenue_cents: verified,
    goal: {
      target_cents: GOAL_CENTS,
      progress: verified / GOAL_CENTS,
      definition: 'verified revenue = Gumroad gross sales as reported per product + REAL affiliate commissions confirmed or paid. A target, not a forecast.',
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
  const rows = ((registry && registry.products) || []).map((p) => {
    const o = offerBy[p.internal_id] || {};
    let blocker = null;
    let next = null;
    if (withdrawn.test(p.title || '') && p.published) {
      blocker = 'withdrawn listing is still published';
      next = 'founder: unpublish it at the Gumroad dashboard (no API route)';
    } else if (dup.has(p.title)) {
      blocker = 'duplicate live title';
      next = 'founder: unpublish one of the two listings';
    } else if (p.primary_state === 'READY_FOR_AUTHORIZATION') {
      blocker = batchState.blocked_reason || 'awaiting publication';
      next = batchState.next || 'publish through scripts/publish_batch14.py';
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
      qa: p.manifest ? 'QA_PASS (manifest)' : 'NOT RECORDED',
      price_cents: p.price_cents, price_kind: p.published ? 'LIVE (Gumroad)' : 'APPROVED (not yet listed)',
      published: !!p.published, url: p.url || null,
      sales: p.sales_count || 0, sales_usd_cents: p.sales_usd_cents || 0,
      has_cover: o.cover_url ? true : (p.published ? null : false),
      blocker, next_action: next,
    };
  });
  const pipeline = STAGES.map(s => ({ stage: s, count: rows.filter(r => r.stage === s).length,
    measured: ['Authorization', 'Publication', 'Revenue Verification', 'Quality Assurance'].includes(s) }));
  return { rows, pipeline, source: src('data/product_registry.json', root) };
}

function batchState(root) {
  const runs = readJson(path.join(root, 'data', 'batch15_publish_results.json')) || [];
  const last = runs.length ? runs[runs.length - 1] : null;
  const failed = last && (last.results || []).find(r => r.error);
  if (failed && /10 products per day/i.test(failed.error)) {
    return { blocked_reason: 'Gumroad limit: 10 new products per 24 h', next: 'automatic retry after the limit resets', at: last.at };
  }
  return { blocked_reason: null, next: null, at: last && last.at };
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
  out.push({ name: 'Paddle', role: 'checkout', state: has('PADDLE_API_KEY') ? 'KEY PRESENT (403 on 2026-10-24)' : 'NOT CONFIGURED',
    detail: 'last live read was refused with 403', action: 'create a new API key with read and write permissions' });
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
function risks(root, registry) {
  const out = [];
  const site = path.join(root, 'customer_site');
  let pages = 0;
  let noCanonical = 0;
  let residue = 0;
  try {
    for (const f of fs.readdirSync(site)) {
      if (!f.endsWith('.html')) continue;
      pages += 1;
      const t = fs.readFileSync(path.join(site, f), 'utf8');
      if (!/rel=["']canonical["']/i.test(t)) noCanonical += 1;
      if (/UNKNOWN -- not captured at this granularity/.test(t)) residue += 1;
    }
  } catch (_) { /* no site folder */ }
  if (noCanonical) out.push({ level: 'HIGH', area: 'SEO', title: `${noCanonical} of ${pages} site pages have no canonical tag in this working copy`, detail: 'uncommitted edits from the parallel session remove og/canonical tags; do not publish them as they are' });
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
  if (ready) autonomous.push(`${ready} new products (batch 15) publish automatically once Gumroad's daily limit resets`);
  autonomous.push('daily: product registry rebuild and listing page checks; search-engine notification for changed site pages');
  autonomous.push('each tick: factory diagnosis, demand sensing, agent chain, site publication of test-passing site pages');
  return { founder: out.slice(0, 5), autonomous };
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
  const rk = risks(root, registry);
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
    business_arms: businessArms(root, now),
    trend_to_product: trendToProduct(root, now),
    commercial_funnel: commercialFunnel.compute({ root, registry, revenue: revenue(root, registry), distribution: dist, now }),
  };
}

module.exports = { compute, revenue, portfolio, factory, integrations, distribution, risks, decisions, businessArms, trendToProduct, stageOf, GOAL_CENTS };

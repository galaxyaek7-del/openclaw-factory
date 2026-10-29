// Tests for lib/ceo_command_center.js — the Executive Command Center read model.
// Every test builds its own temp factory folder; the real data/ is never read.
//
//   node --test tests/test_ceo_command_center.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const ccc = require('../lib/ceo_command_center.js');

function factory(files = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'gf-ccc-'));
  for (const [rel, body] of Object.entries(files)) {
    const p = path.join(root, rel);
    fs.mkdirSync(path.dirname(p), { recursive: true });
    fs.writeFileSync(p, typeof body === 'string' ? body : JSON.stringify(body));
  }
  return root;
}

const REGISTRY = {
  generated_at: '2026-10-24T08:00:00Z',
  drift: { duplicate_live_titles: ['Twin Kit'] },
  products: [
    { internal_id: 'B14-001', title: 'Cash Flow', price_cents: 1900, published: true, url: 'https://x/l/a', sales_count: 2, sales_usd_cents: 3800, manifest: 'm', primary_state: 'FIRST_SALE_VERIFIED' },
    { internal_id: 'GR-1', title: 'Twin Kit', price_cents: 1500, published: true, url: 'https://x/l/b', sales_count: 0, sales_usd_cents: 0, primary_state: 'PUBLIC_LISTING_VERIFIED' },
    { internal_id: 'GR-2', title: '[Unavailable] Old thing', price_cents: 0, published: true, url: 'https://x/l/c', sales_count: 0, sales_usd_cents: 0, primary_state: 'PUBLIC_LISTING_VERIFIED' },
    { internal_id: 'B15-001', title: 'Refinance', price_cents: 1500, published: false, url: null, sales_count: 0, sales_usd_cents: 0, manifest: 'm', primary_state: 'READY_FOR_AUTHORIZATION' },
  ],
};

test('revenue is only what the records say: gross from Gumroad, refunds and net UNKNOWN, never a guess', () => {
  const root = factory({ 'data/product_registry.json': REGISTRY });
  const d = ccc.compute({ root, env: {}, now: new Date('2026-10-24T09:00:00Z') });
  assert.equal(d.revenue.gross_sales.value, 3800);
  assert.equal(d.revenue.gross_sales.kind, 'VERIFIED');
  assert.equal(d.revenue.orders.value, 2);
  assert.equal(d.revenue.refunds.value, null);
  assert.equal(d.revenue.refunds.kind, 'UNKNOWN');
  assert.equal(d.revenue.net_revenue.kind, 'UNKNOWN');
  assert.equal(d.revenue.verified_revenue_cents, 3800);
  assert.equal(d.revenue.goal.progress, 3800 / (100000 * 100));
  assert.match(d.revenue.goal.definition, /not a forecast/);
});

test('a registry without the sales value field reports gross sales as UNKNOWN, not zero', () => {
  const old = { products: [{ internal_id: 'A', title: 'A', published: true, sales_count: 0, primary_state: 'PUBLIC_LISTING_VERIFIED' }] };
  const d = ccc.compute({ root: factory({ 'data/product_registry.json': old }), env: {} });
  assert.equal(d.revenue.gross_sales.kind, 'UNKNOWN');
  assert.equal(d.revenue.gross_sales.value, null);
});

test('only REAL commissions that reached CONFIRMED or PAID count', () => {
  const ledger = [
    { environment: 'REAL', status: 'PAID', amount_usd: 12.5 },
    { environment: 'SIMULATION', status: 'PAID', amount_usd: 999 },
    { environment: 'REAL', status: 'PENDING', amount_usd: 40 },
  ].map((r) => JSON.stringify(r)).join('\n') + '\n';
  const d = ccc.compute({ root: factory({ 'data/product_registry.json': { products: [] }, 'data/commission_ledger.jsonl': ledger }), env: {} });
  assert.equal(d.revenue.affiliate_commissions.value, 1250);
});

test('portfolio: stages follow real states, blockers are real, live-without-sales is not a blocker', () => {
  const d = ccc.compute({ root: factory({ 'data/product_registry.json': REGISTRY }), env: {} });
  const by = Object.fromEntries(d.portfolio.rows.map((r) => [r.id, r]));
  assert.equal(by['B14-001'].stage, 'Revenue Verification');
  assert.equal(by['B15-001'].stage, 'Authorization');
  assert.equal(by['B15-001'].price_kind, 'APPROVED (not yet listed)');
  assert.match(by['GR-2'].blocker, /withdrawn/);
  assert.match(by['GR-1'].blocker, /duplicate/);
  assert.equal(by['B14-001'].blocker, null);
  assert.equal(d.products.published, 3);
  assert.equal(d.products.ready_for_review, 1);
  const unmeasured = d.portfolio.pipeline.filter((s) => !s.measured).map((s) => s.stage);
  assert.ok(unmeasured.includes('Research') && unmeasured.includes('Commercial Validation'));
});

test('batch blocked by the Gumroad daily limit is explained, not hidden', () => {
  const runs = [{ at: '2026-10-24T07:53:07Z', results: [{ id: 'B15-001', error: 'RuntimeError: Gumroad create_product failed: Sorry, you can only create 10 products per day.' }] }];
  const d = ccc.compute({ root: factory({ 'data/product_registry.json': REGISTRY, 'data/batch15_publish_results.json': runs }), env: {} });
  assert.match(d.batch.blocked_reason, /10 new products per 24 h/);
  assert.match(d.portfolio.rows.find((r) => r.id === 'B15-001').blocker, /Gumroad limit/);
});

test('factory loop: RUNNING only with a live pid; failed steps come from the loop log', () => {
  const log = [
    { timestamp: '2026-10-24T08:00:00Z', diagnosis: { status: 'unreachable' }, actions: [{ step: 'diagnose', action: 'failed', detail: 'health timed out' }] },
    { timestamp: '2026-10-24T08:10:00Z', diagnosis: { status: 'warning' }, actions: [{ step: 'demand_sensing', action: 'ok' }] },
  ].map((r) => JSON.stringify(r)).join('\n') + '\n';
  const live = factory({ 'factory_loop.log': log, '.factory_loop.lock': String(process.pid) });
  const d = ccc.compute({ root: live, env: {}, now: new Date('2026-10-24T08:15:00Z') });
  assert.equal(d.factory.loop.state, 'RUNNING');
  assert.equal(d.factory.diagnosis, 'warning');
  assert.equal(d.factory.minutes_since_last_tick, 5);
  assert.equal(d.factory.stale, false);
  assert.equal(d.factory.recent_failed_steps.length, 1);
  const dead = factory({ 'factory_loop.log': log, '.factory_loop.lock': '999999' });
  assert.equal(ccc.compute({ root: dead, env: {} }).factory.loop.state, 'STOPPED');
  assert.equal(ccc.compute({ root: factory({}), env: {} }).factory.loop.state, 'UNKNOWN');
});

test('integrations never expose a secret value, only whether a name is set', () => {
  const secret = 'fake-paddle-value-SHOULD-NEVER-APPEAR';
  const d = ccc.compute({ root: factory({}), env: { PADDLE_API_KEY: secret, TELEGRAM_BOT_TOKEN: 'tg-secret-value-xyz' } });
  const text = JSON.stringify(d);
  assert.ok(!text.includes(secret));
  assert.ok(!text.includes('tg-secret-value-xyz'));
  assert.equal(d.integrations.find((i) => i.name === 'Telegram').state, 'CONFIGURED');
});

test('founder decisions are separated from autonomous work and come from real signals', () => {
  const q = { board: null, summary: { BLOCKED_NO_BOARD: 86 }, board_lookup: 'no board' };
  const dist = { operational: { awaiting_approval: ['SJ-1', 'SJ-2'], platforms: {} } };
  const d = ccc.compute({ root: factory({ 'data/product_registry.json': REGISTRY, 'data/pinterest_queue.json': q, 'data/distribution_dashboard.json': dist }), env: {} });
  const titles = d.decisions.founder.map((x) => x.title).join(' | ');
  assert.match(titles, /Pinterest board/);
  assert.match(titles, /2 LinkedIn and X drafts/);
  assert.match(titles, /withdrawn/);
  assert.ok(d.decisions.founder.length <= 5);
  assert.ok(d.decisions.autonomous.some((t) => /batch 15/.test(t)));
  assert.equal(d.distribution.traffic.kind, 'UNKNOWN');
});

test('risks are computed from the files: missing canonical tags and data-gap text on site pages', () => {
  const root = factory({
    'customer_site/a.html': '<link rel="canonical" href="x">',
    'customer_site/b.html': '<p>for UNKNOWN -- not captured at this granularity in the source registry</p>',
  });
  const titles = ccc.compute({ root, env: {} }).risks.map((r) => r.title).join(' | ');
  assert.match(titles, /1 of 2 site pages have no canonical tag/);
  assert.match(titles, /1 public guide pages print/);
});

test('an empty factory renders honest empties instead of throwing', () => {
  const d = ccc.compute({ root: factory({}), env: {} });
  assert.equal(d.products.total, 0);
  assert.equal(d.revenue.verified_revenue_cents, 0);
  assert.deepEqual(d.risks, []);
});

test('business arms: shown only from the Python-written state file, with freshness', () => {
  const state = {
    generated_at: '2026-10-29T00:00:00Z',
    counts: { PARTIAL: 1, PLANNED: 1 },
    arms: { digital_products: { arm: 'digital_products', name: 'Digital Products', status: 'PARTIAL',
      gap: '102 listings live on Gumroad; no sale recorded', implementation_present: ['product_registry.py'] } },
    portfolio: { activities: [
      { activity: 'digital_products', name: 'Digital Products', arm: 'digital_products', status: 'PARTIAL' },
      { activity: 'raas', name: 'RaaS', arm: null, nearest_arm: 'micro_b2b', status: 'PLANNED', gap: 'no recurring service' }] },
    controls: { treasury_control: { name: 'Treasury Control', status: 'PRESENT', rule: 'visibility only',
      authoritative_present: { 'revenue_truth.py': true } } },
    problems: [],
  };
  const root = factory({ 'data/business_arms_state.json': state });
  const fresh = ccc.compute({ root, env: {}, now: new Date('2026-10-29T10:00:00Z') }).business_arms;
  assert.equal(fresh.state, 'FRESH');
  assert.equal(fresh.activities.length, 2);
  assert.equal(fresh.activities[1].arm, null);
  assert.equal(fresh.activities[1].nearest_arm, 'micro_b2b');
  assert.equal(fresh.controls[0].authoritative[0].present, true);
  const old = ccc.compute({ root, env: {}, now: new Date('2026-10-31T10:00:00Z') }).business_arms;
  assert.equal(old.state, 'STALE');
  assert.equal(old.age_hours, 58);
});

test('business arms: a missing state file is reported, never filled in', () => {
  const a = ccc.compute({ root: factory({}), env: {} }).business_arms;
  assert.equal(a.available, false);
  assert.equal(a.state, 'MISSING');
  assert.equal(a.arms, undefined);
});

test('trend-to-product: read from the Python state file; freshness is evidence age', () => {
  const state = {
    generated_at: '2026-10-29T01:00:00Z',
    evidence_freshness: { newest_access: '2026-10-29', oldest_access: '2026-10-29' },
    counts: { sources: 2, signals: 3, opportunities: 2, specs: 1, product_links: 0 },
    evidence_quality: { MARKETPLACE_LISTING: 2 },
    signals_counting_as_sales: 0,
    opportunities: [
      { opportunity_id: 'OPP-1', name: 'Calc', format: 'excel_tool', t1_arm: 'digital_products',
        band: 'INSUFFICIENT_EVIDENCE', composite: null, coverage: 0.4, rights: 'REVIEW',
        price_range: { status: 'OBSERVED_RANGE', low: 2.24, high: 45 }, missing_evidence: ['demand'] },
      { opportunity_id: 'OPP-2', name: 'Pattern', format: 'craft_pattern', t1_arm: 'digital_products',
        band: 'WEAK', composite: 2.1, coverage: 0.73, rights: 'REVIEW',
        price_range: { status: 'UNKNOWN' }, missing_evidence: [] }],
    specs: [{ spec_id: 'SPEC-1', title: 'T', status: 'SPEC_REVIEW', duplication: 'CANNIBALIZATION',
      duplicates: ['B14-005'], blockers: [], reviews: ['x'] }],
    blockers: ['Calc: INSUFFICIENT_EVIDENCE'],
  };
  const root = factory({ 'data/trend_to_product_state.json': state });
  const t = ccc.compute({ root, env: {}, now: new Date('2026-10-30T10:00:00Z') }).trend_to_product;
  assert.equal(t.state, 'FRESH');
  assert.equal(t.evidence_age_days, 1);
  assert.equal(t.opportunities[0].composite, null);
  assert.equal(t.opportunities[0].price_range, '$2.24-$45');
  assert.equal(t.opportunities[1].price_range, 'UNKNOWN');
  assert.equal(t.specs[0].duplicates[0], 'B14-005');
  const old = ccc.compute({ root, env: {}, now: new Date('2026-12-15T00:00:00Z') }).trend_to_product;
  assert.equal(old.state, 'STALE');
  const none = ccc.compute({ root: factory({}), env: {} }).trend_to_product;
  assert.equal(none.available, false);
  assert.equal(none.opportunities, undefined);
});

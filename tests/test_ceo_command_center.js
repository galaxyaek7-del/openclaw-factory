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
  assert.equal(d.revenue.gross_sales.kind, 'OBSERVED');
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
  assert.equal(by['B15-001'].price_kind, 'PROPOSED — NO FOUNDER AUTHORIZATION');
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
  assert.ok(d.decisions.autonomous.some((t) => /NOT published automatically/.test(t)));
  assert.ok(!d.decisions.autonomous.some((t) => /products .* publish automatically/.test(t)));
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

test('commissions use the real ledger schema: commission_status + net_commission', () => {
  const ledger = [
    { environment: 'REAL', commission_status: 'PAID', net_commission: 12.5 },
    { environment: 'TEST', commission_status: 'PAID', net_commission: 500 },
    { environment: 'REAL', commission_status: 'PENDING', net_commission: 40 },
  ].map((r) => JSON.stringify(r)).join('\n') + '\n';
  const d = ccc.compute({ root: factory({ 'data/product_registry.json': { products: [] }, 'data/commission_ledger.jsonl': ledger }), env: {} });
  assert.equal(d.revenue.affiliate_commissions.value, 1250);
  assert.match(d.revenue.affiliate_commissions.note, /1 TEST row\(s\) excluded/);
});

test('internal QA, founder authorization and platform publication are three separate facts', () => {
  const pipeline = { products: [
    { id: 'B14-001', title: 'Cash Flow', qa_results: 'Cycle 88 checks', publication_authorization: { phrase: 'APPROVE B14-001 PUBLISH', granted_at_utc: '2026-10-23T13:00Z', consumed: true } },
  ] };
  const d = ccc.compute({ root: factory({ 'data/product_registry.json': REGISTRY, 'data/product_pipeline.json': pipeline }), env: {} });
  const by = Object.fromEntries(d.portfolio.rows.map((r) => [r.id, r]));
  assert.equal(by['B14-001'].approval.status, 'QA_PASSED');
  assert.equal(by['B14-001'].authorization.status, 'GRANTED_AND_CONSUMED');
  assert.equal(by['B14-001'].publication.status, 'PUBLIC_LISTING_VERIFIED');
  assert.equal(by['B14-001'].price_kind, 'LIVE_PLATFORM_PRICE');
  assert.equal(by['B15-001'].authorization.status, 'NOT_GRANTED');
  assert.equal(by['B15-001'].publication.status, 'NOT_PUBLISHED');
  assert.equal(by['B15-001'].approval.status, 'QA_PASSED_BY_RECORDED_STATE');
  assert.equal(by['B15-001'].approval.kind, 'INFERRED');
});

test('a batch-level founder authorization is cited as GRANTED_BATCH, never as a per-product approval', () => {
  const runs = [{ at: '2026-10-23T21:00:00Z', authorization: 'founder 2026-10-23: publish ten batch-14 products',
    results: [{ id: 'GR-1', ok: true, steps: { published: true } },
              { id: 'GR-2', ok: false, steps: { published: false } }] }];
  const d = ccc.compute({ root: factory({ 'data/product_registry.json': REGISTRY, 'data/batch14_publish_results.json': runs }), env: {} });
  const by = Object.fromEntries(d.portfolio.rows.map((r) => [r.id, r]));
  assert.equal(by['GR-1'].authorization.status, 'GRANTED_BATCH');
  assert.match(by['GR-1'].authorization.phrase, /publish ten batch-14/);
  assert.match(by['GR-1'].authorization.note, /not a per-product phrase/);
  assert.equal(by['GR-2'].authorization.status, 'NOT_GRANTED');
});

test('the Gumroad batch-15 limit has no automatic retry and the dashboard says so', () => {
  const runs = [{ at: '2026-10-24T07:53:07Z', results: [{ id: 'B15-001', error: 'Sorry, you can only create 10 products per day.' }] }];
  const d = ccc.compute({ root: factory({ 'data/product_registry.json': REGISTRY, 'data/batch15_publish_results.json': runs }), env: {} });
  assert.equal(d.batch.automatic_retry, false);
  assert.match(d.batch.next, /manual re-run/);
  assert.match(d.batch.next, /no automatic retry/);
});

test('B13 products absent from the Gumroad registry are added from their real batch record', () => {
  const b13 = { products: [{ id: 'B13-001', title: 'Renovation', price_usd: 15, state: 'READY_FOR_AUTHORIZATION',
    authorization_status: 'NOT_GRANTED', published: false, price_basis: 'FOUNDER_PREFERRED_DIRECTION_NOT_AUTHORIZED' }] };
  const d = ccc.compute({ root: factory({ 'data/product_registry.json': { products: [] }, 'data/product_batch_13.json': b13 }), env: {} });
  const r = d.portfolio.rows[0];
  assert.equal(r.id, 'B13-001');
  assert.equal(r.price_cents, 1500);
  assert.equal(r.authorization.status, 'NOT_GRANTED');
  assert.equal(r.price_kind, 'FOUNDER_PREFERRED_DIRECTION_NOT_AUTHORIZED');
  assert.equal(r.publication.published, false);
});

test('freshness flags stale sources and missing evidence instead of hiding them', () => {
  const d = ccc.compute({ root: factory({ 'data/product_registry.json': REGISTRY }), env: {}, now: new Date(Date.now() + 8 * 86400000) });
  // freshness reads file mtimes (written just now), so "now" must be relative, not a fixed date
  const reg = d.freshness.checks.find((c) => c.file === 'data/product_registry.json');
  assert.equal(reg.state, 'STALE');
  assert.ok(d.freshness.stale_sources.some((s) => s.file === 'data/commercial_evidence_report.json'));
  assert.equal(d.commercial_evidence.kind, 'UNKNOWN');
  assert.equal(d.commercial_evidence.available, false);
});

test('a commercial evidence report is surfaced with its conflicts and unknowns', () => {
  const report = { generated_at: '2026-10-24T09:00:00Z', mode: 'READ_ONLY',
    b12_001: { identity: { price_cents: 1499 }, publication: { status: 'PUBLIC_LISTING_VERIFIED' },
      authorization: { status: 'GRANTED_AND_CONSUMED' }, approval: { value: 'QA_PASSED' },
      sales: { units: { value: 0 } }, commissions: { real_net_usd: { value: 0 } },
      traffic: { product_attributed_views: { kind: 'UNKNOWN' }, conversion: { kind: 'UNKNOWN' } },
      conflicts: [{ id: 'X' }], unknowns: ['traffic'], inferences: [{ kind: 'INFERRED' }], next_action: 'watch' },
    b13: { products: [] }, integrity: [] };
  const d = ccc.compute({ root: factory({ 'data/product_registry.json': REGISTRY, 'data/commercial_evidence_report.json': report }), env: {} });
  assert.equal(d.commercial_evidence.available, true);
  assert.equal(d.commercial_evidence.b12.price_cents, 1499);
  assert.equal(d.commercial_evidence.b12.conflicts.length, 1);
  assert.equal(d.commercial_evidence.b12.traffic.kind, 'UNKNOWN');
});

test('public surface separates the live site from private data and reports real B15 state', () => {
  const root = factory({
    'data/product_registry.json': REGISTRY,
    'data/batch15_prepublication_audit.json': { mode: 'DRY_RUN', summary: { products: 10, pass: 0, hold: 10, blocked: 0 } },
    'customer_site/a.html': '<p>GUMROAD_ACCESS_TOKEN must never appear here</p><a href="missing.html">broken</a>',
    'customer_site/b.html': '<link rel="canonical" href="https://example.test/b"><a href="a.html">ok</a>',
    'customer_site/c.html': '<meta name="robots" content="noindex"><p>draft</p>',
  });
  const d = ccc.compute({ root, env: {} });
  assert.equal(d.public_surface.site.pages, 3);
  assert.equal(d.public_surface.site.indexable_pages, 2);
  assert.equal(d.public_surface.site.noindex_pages, 1);
  assert.equal(d.public_surface.site.missing_canonical, 1);
  assert.equal(d.public_surface.site.broken_internal_links, 1);
  assert.deepEqual(d.public_surface.site.private_reference_pages, ['a.html']);
  assert.equal(d.public_surface.site.deployment.kind, 'UNKNOWN');
  assert.equal(d.public_surface.catalog.b15_unpublished, 1);
  assert.equal(d.public_surface.batch15.summary.hold, 10);
  assert.equal(d.public_surface.batch15.approval_file_present, false);
  assert.equal(d.public_surface.checks.find((c) => /credential/.test(c.name)).status, 'FAIL');
  assert.equal(d.public_surface.checks.find((c) => /approvals/.test(c.name)).status, 'FAIL');
  assert.ok(d.public_surface.checks.every((c) => ['OBSERVED', 'DERIVED', 'INFERRED', 'UNKNOWN'].includes(c.kind)));
  assert.equal(d.public_surface.catalog.kind, 'OBSERVED');
  assert.equal(d.public_surface.truthfulness.kind, 'DERIVED');
  assert.ok(!JSON.stringify(d.public_surface).includes('C:\\openclaw-dasgboard'));
});

test('public surface scans nested pages and resolves relative links from the page directory', () => {
  const root = factory({
    'customer_site/index.html': '<link rel="canonical" href="https://x/index">',
    'customer_site/trust/index.html': '<link rel="canonical" href="https://x/trust">'
      + '<a href="../index.html">up</a><a href="missing.html">broken</a>',
    'customer_site/edu/guide.html': '<p>No canonical tag here.</p>',
  });
  const site = ccc.compute({ root, env: {} }).public_surface.site;
  assert.equal(site.pages, 3);
  assert.equal(site.indexable_pages, 3);
  assert.equal(site.missing_canonical, 1);
  assert.equal(site.broken_internal_links, 1);
  assert.deepEqual(site.broken_link_examples, [{ page: 'trust/index.html', target: 'missing.html' }]);
});

test('truthfulness scan includes nested pages and still respects noindex', () => {
  const root = factory({
    'data/product_registry.json': { products: [] },
    'customer_site/trust/draft.html': '<html><head><title>Draft policy</title></head><body>Planned preview.</body></html>',
    'customer_site/trust/clean.html': '<html><head><meta name="robots" content="noindex"><title>Draft policy</title></head><body>Planned preview.</body></html>',
  });
  const t = ccc.compute({ root, env: {} }).public_surface.truthfulness;
  assert.equal(t.scanned_pages, 2);
  assert.deepEqual(t.indexable_draft_pages.map((x) => x.page), ['trust/draft.html']);
});

test('truthfulness scan flags unverified links, indexable drafts and unsupported claims, but respects negation and noindex', () => {
  const root = factory({
    'data/product_registry.json': { products: [
      { internal_id: 'P1', title: 'Live', published: true, url: 'https://aekraft.gumroad.com/l/live' },
    ] },
    'customer_site/live.html': '<html><head><title>Live product</title><link rel="canonical" href="https://x/live"></head><body>'
      + '<a href="https://aekraft.gumroad.com/l/live?utm=x">Buy</a>'
      + '<p>No customer logos. We do not guarantee results. This is not a case study.</p></body></html>',
    'customer_site/bad.html': '<html><head><title>Draft pack (approved, not yet listed)</title></head><body>'
      + '<a href="https://aekraft.gumroad.com/l/unlisted">Buy</a>'
      + '<p>Every recommendation independently verified. Available now. Delivered within 6 days.</p></body></html>',
    'customer_site/planned.html': '<html><head><meta name="robots" content="noindex"><title>Planned preview</title></head><body>Not operational.</body></html>',
  });
  const d = ccc.compute({ root, env: {} });
  const t = d.public_surface.truthfulness;
  assert.equal(t.status, 'FAIL');
  assert.deepEqual(t.unverified_purchase_links.map((x) => x.slug), ['unlisted']);
  assert.deepEqual(t.indexable_draft_pages.map((x) => x.page), ['bad.html']);
  assert.ok(t.unavailable_service_claims.some((x) => /Delivered within 6 days/.test(x.phrase)));
  assert.ok(t.unsupported_claims.some((x) => x.phrase === 'every recommendation independently verified'));
  assert.ok(!t.unsupported_claims.some((x) => x.phrase === 'customer logos'));
  assert.ok(!t.unsupported_claims.some((x) => x.phrase === 'case study'));
  assert.ok(!t.indexable_draft_pages.some((x) => x.page === 'planned.html'));
  assert.ok(!JSON.stringify(t).includes(root));
  assert.equal(d.public_surface.checks.find((c) => /unverified purchase/.test(c.name)).status, 'FAIL');
  assert.equal(d.public_surface.checks.find((c) => /unsupported affirmative/.test(c.name)).status, 'FAIL');
});

test('truthfulness scan catches gate and evidence-coverage overclaims', () => {
  const root = factory({
    'data/product_registry.json': { products: [] },
    'customer_site/claims.html': '<html><head><title>Claims</title><link rel="canonical" href="https://x/claims"></head><body>'
      + '<p>Every opportunity carries a real, disclosed evidence-coverage score.</p>'
      + '<p>Competition and margin are each independently verified.</p>'
      + '<div>Ten-Condition Gate</div>'
      + '<p>Every opportunity must clear all ten conditions.</p>'
      + '<p>There are 10 named acceptance conditions and ten hard gates.</p>'
      + '</body></html>',
  });
  const t = ccc.compute({ root, env: {} }).public_surface.truthfulness;
  assert.equal(t.kind, 'DERIVED');
  assert.ok(t.unsupported_claims.some((x) => x.phrase === 'every opportunity carries an evidence-coverage score'));
  assert.ok(t.unsupported_claims.some((x) => x.phrase === 'each criterion independently verified'));
  assert.ok(t.unsupported_claims.some((x) => x.phrase === 'ten-condition gate'));
  assert.ok(t.unsupported_claims.some((x) => x.phrase === 'every opportunity must clear all ten conditions'));
  assert.ok(t.unsupported_claims.some((x) => x.phrase === 'ten named acceptance conditions'));
  assert.ok(t.unsupported_claims.some((x) => x.phrase === 'ten hard gates'));
});

test('truthfulness scan catches public-surface verification and held-product availability overclaims', () => {
  const root = factory({
    'data/product_registry.json': { products: [] },
    'customer_site/overclaim.html': '<html><head><title>Overclaim</title>'
      + '<script type="application/ld+json">{"@type":"Product","name":"EU AI Act Compliance Toolkit","offers":{"availability":"https://schema.org/InStock"}}</script>'
      + '</head><body>'
      + '<p>All program details verified against the official program.</p>'
      + '<p>This is verified program data.</p>'
      + '<p>This is a real, verified opportunity record.</p>'
      + '<p>Each term was independently confirmed against official sources.</p>'
      + '<p>We show the freshest data available.</p>'
      + '<p>Every purchase verified independently via Gumroad.</p>'
      + '<a data-held-product="iaiyt">Get the Toolkit</a>'
      + '</body></html>',
  });
  const t = ccc.compute({ root, env: {} }).public_surface.truthfulness;
  assert.equal(t.kind, 'DERIVED');
  for (const phrase of [
    'program details verified',
    'verified program data',
    'real, verified opportunity record',
    'independently confirmed against official sources',
    'freshest data',
    'purchase verified independently',
    'held product availability claim',
    'held product InStock schema',
  ]) {
    assert.ok(t.unsupported_claims.some((x) => x.phrase === phrase), phrase);
  }
});

test('truthfulness scan passes a page that only makes honest negative statements', () => {
  const root = factory({
    'data/product_registry.json': { products: [] },
    'customer_site/honest.html': '<html><head><title>Honest page</title><link rel="canonical" href="https://x/honest"></head><body>'
      + '<p>No outcome is guaranteed. We have no customer logos and no case study. We do not use 5-star claims.</p></body></html>',
  });
  const t = ccc.compute({ root, env: {} }).public_surface.truthfulness;
  assert.equal(t.status, 'PASS');
  assert.deepEqual(t.unsupported_claims, []);
});

test('a directory source reports its newest file, not the folder mtime', () => {
  const root = factory({ 'customer_site/index.html': '<html><head><title>Home</title></head><body>Home.</body></html>' });
  const dir = path.join(root, 'customer_site');
  const file = path.join(dir, 'index.html');
  const old = new Date('2026-10-20T00:00:00Z');
  const fresh = new Date('2026-10-25T09:00:00Z');
  fs.utimesSync(dir, old, old);
  fs.utimesSync(file, fresh, fresh);
  const t = ccc.compute({ root, env: {} }).public_surface.truthfulness;
  assert.equal(t.source.updated_at, fresh.toISOString());
});

test('an empty factory renders honest empties instead of throwing', () => {
  const d = ccc.compute({ root: factory({}), env: {} });
  assert.equal(d.products.total, 0);
  assert.equal(d.revenue.verified_revenue_cents, 0);
  assert.deepEqual(d.risks, []);
  assert.equal(d.public_surface.site.pages, 0);
  assert.equal(d.public_surface.batch15.kind, 'UNKNOWN');
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

// Tests for lib/commercial_funnel.js — funnel states, delivery truth,
// experiments and the funnel diagnosis. Every test builds its own temp
// factory folder with synthetic fixtures; the real data/ is never read.
//
//   node --test tests/test_commercial_funnel.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const cf = require('../lib/commercial_funnel.js');

function factory(files = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'gf-cf-'));
  for (const [rel, body] of Object.entries(files)) {
    const p = path.join(root, rel);
    fs.mkdirSync(path.dirname(p), { recursive: true });
    fs.writeFileSync(p, typeof body === 'string' ? body : JSON.stringify(body));
  }
  return root;
}

const REGISTRY = {
  generated_at: '2026-10-29T12:00:00Z',
  products: [
    { internal_id: 'B16-001', manifest: 'm', primary_state: 'PUBLIC_LISTING_VERIFIED', sales_count: 0 },
    { internal_id: 'B16-008', manifest: 'm', primary_state: 'READY_FOR_AUTHORIZATION', sales_count: 0 },
    { internal_id: 'GR-1', primary_state: 'PUBLIC_LISTING_VERIFIED', sales_count: 0 },
  ],
};
const REVENUE_ZERO = {
  orders: { value: 0, kind: 'OBSERVED', source: { file: 'data/product_registry.json' } },
  gross_sales: { value: 0, kind: 'OBSERVED', source: { file: 'data/product_registry.json' } },
};
const DIST = { jobs_by_state: { QA_PASSED: 2, QA_FAILED: 1 }, published_verified: 0 };
const NOW = new Date('2026-10-29T18:00:00Z');

test('funnel has the fifteen states in order, and unmeasured states are UNKNOWN with null, never 0', () => {
  const root = factory();
  const out = cf.compute({ root, registry: REGISTRY, revenue: REVENUE_ZERO, distribution: DIST, now: NOW });
  assert.equal(out.funnel.length, 15);
  assert.deepEqual(out.funnel.map(s => s.n), [...Array(15).keys()].map(i => i + 1));
  for (const n of [8, 9, 10, 13, 14, 15]) {
    const s = out.funnel.find(x => x.n === n);
    assert.equal(s.kind, 'UNKNOWN', s.name);
    assert.equal(s.value, null, s.name);
  }
});

test('QA passed counts only products with a factory manifest and names the rest', () => {
  const out = cf.compute({ root: factory(), registry: REGISTRY, revenue: REVENUE_ZERO, distribution: DIST, now: NOW });
  const qa = out.funnel.find(s => s.n === 2);
  assert.equal(qa.value, 2);
  assert.match(qa.note, /1 older listings have no QA record/);
  assert.equal(out.funnel.find(s => s.n === 5).value, 2);
  assert.equal(out.funnel.find(s => s.n === 6).value, 2);
});

test('zero orders with unmeasured traffic does not claim a single funnel case', () => {
  const out = cf.compute({ root: factory(), registry: REGISTRY, revenue: REVENUE_ZERO, distribution: DIST, now: NOW });
  assert.equal(out.diagnosis.case, 'A_OR_B_OR_C');
  assert.match(out.diagnosis.next, /more products does not answer/);
});

test('orders without reconciled refunds and fees are not reported as verified net revenue', () => {
  const rev = { orders: { value: 3, kind: 'OBSERVED' }, gross_sales: { value: 3600, kind: 'OBSERVED' } };
  const out = cf.compute({ root: factory(), registry: REGISTRY, revenue: rev, distribution: DIST, now: NOW });
  assert.equal(out.diagnosis.case, 'E_OR_F_PENDING');
  assert.equal(out.funnel.find(s => s.n === 14).kind, 'UNKNOWN');
});

test('delivery truth: buyer-facing issues are listed, archive opacity is counted separately', () => {
  const root = factory({
    'reports/GUMROAD_DELIVERY_AUDIT_2026-10-22.json': { generated_at: '2026-10-22T00:00:00Z', rows: [] },
    'reports/GUMROAD_DELIVERY_AUDIT_2026-10-29.json': {
      generated_at: '2026-10-29T16:00:00Z', issue_counts: { THIN_DELIVERABLE: 1 },
      rows: [
        { slug: 'a', name: 'Kit A', published: true, price_usd: 69, issues: ['PROMISES_SPREADSHEET_NOT_ATTACHED'] },
        { slug: 'b', name: 'Guide B', published: true, price_usd: 29, issues: ['THIN_DELIVERABLE'] },
        { slug: 'c', name: 'Tool C', published: true, price_usd: 12, issues: ['ZIP_CONTENTS_UNVERIFIED'] },
        { slug: 'd', name: 'Draft D', published: false, price_usd: 9, issues: ['THIN_DELIVERABLE'] },
      ],
    },
  });
  const d = cf.delivery(root, NOW);
  assert.equal(d.kind, 'OBSERVED');
  assert.equal(d.source.file.replace(/\\/g, '/'), 'reports/GUMROAD_DELIVERY_AUDIT_2026-10-29.json');
  assert.equal(d.published, 3);
  assert.equal(d.with_buyer_issue, 2);
  assert.equal(d.serious, 1);
  assert.equal(d.archive_contents_unverified, 1);
  assert.deepEqual(d.flagged.map(r => r.slug), ['a', 'b']);
  assert.equal(d.stale, false);
});

test('an archive whose attached size equals its built bundle is verified; a size mismatch is not', () => {
  const root = factory({
    'books/b/M1.json': { files: { bundle: { bytes: 18002 } } },
    'books/b/M2.json': { files: { bundle: { bytes: 5000 } } },
    'reports/GUMROAD_DELIVERY_AUDIT_2026-10-29.json': { generated_at: '2026-10-29T16:00:00Z', rows: [
      { slug: 'xiimbr', published: true, price_usd: 12, attached_bytes: 18002, issues: ['ZIP_CONTENTS_UNVERIFIED'] },
      { slug: 'other', published: true, price_usd: 12, attached_bytes: 4999, issues: ['ZIP_CONTENTS_UNVERIFIED'] },
      { slug: 'legacy', published: true, price_usd: 29, attached_bytes: 900, issues: ['ZIP_CONTENTS_UNVERIFIED'] }] },
  });
  const registry = { products: [
    { internal_id: 'B16-007', url: 'https://x/l/xiimbr', manifest: 'books/b/M1.json' },
    { internal_id: 'B16-099', url: 'https://x/l/other', manifest: 'books/b/M2.json' },
    { internal_id: 'GR-1', url: 'https://x/l/legacy' }] };
  const d = cf.delivery(root, NOW, registry);
  assert.equal(d.archive_contents_verified_by_manifest, 1);
  assert.equal(d.archive_contents_unverified, 2);
});

test('no delivery audit is UNKNOWN, not a clean bill', () => {
  const d = cf.delivery(factory(), NOW);
  assert.equal(d.kind, 'UNKNOWN');
});

test('a Telegraph experiment shows its article\'s latest platform reading, labelled as a counter', () => {
  const defs = [
    { record_type: 'experiment_definition', experiment_id: 'T1', status: 'RUNNING', change: 'article https://telegra.ph/Path-One-10-09' },
    { record_type: 'experiment_definition', experiment_id: 'T2', status: 'RUNNING', change: 'article https://telegra.ph/Never-Read-10-09' },
    { record_type: 'experiment_definition', experiment_id: 'X1', status: 'RUNNING', change: 'no article' },
  ].map(r => JSON.stringify(r)).join('\n') + '\n';
  const metrics = [
    { timestamp: '2026-10-09T15:00:00Z', views: { one: 5 } },
    { timestamp: '2026-10-29T16:00:00Z', views: { one: 22 }, net_external_estimate: { one: 21 }, articles: { one: 'Path-One-10-09' } },
  ].map(r => JSON.stringify(r)).join('\n') + '\n';
  const e = cf.experiments(factory({ 'data/commercial_experiments.jsonl': defs, 'data/distribution_metrics.jsonl': metrics }));
  const byId = Object.fromEntries(e.recent.map(x => [x.id, x]));
  assert.equal(byId.T1.exposure.views, 22);
  assert.equal(byId.T1.exposure.net_external_estimate, 21);
  assert.equal(byId.T1.exposure.kind, 'OBSERVED');
  assert.match(byId.T1.exposure.note, /not a verified human visit/);
  assert.equal(byId.T2.exposure.kind, 'UNKNOWN');
  assert.equal(byId.X1.exposure, null);
  assert.equal(e.with_exposure_reading, 1);
});

test('founder queue lists only what the files show is waiting, each with a command', () => {
  const root = factory({
    'reports/GUMROAD_DELIVERY_AUDIT_2026-10-29.json': { generated_at: '2026-10-29T16:00:00Z',
      rows: [{ slug: 'a', name: 'Kit A', published: true, price_usd: 69, issues: ['PROMISES_SPREADSHEET_NOT_ATTACHED'] }] },
    'data/commercial_experiments.jsonl': JSON.stringify({ record_type: 'experiment_definition', experiment_id: 'E1', status: 'PENDING_APPROVAL' }) + '\n',
  });
  const out = cf.compute({ root, registry: REGISTRY, revenue: REVENUE_ZERO, distribution: DIST, now: NOW });
  const titles = out.founder_queue.map(q => q.title);
  assert.equal(out.founder_queue.length, 3);
  assert.match(titles[0], /Publish 1 .*B16-008/);
  assert.match(titles[1], /Repair 1 paid listing/);
  assert.match(titles[2], /Approve or reject 1/);
  for (const q of out.founder_queue) assert.ok(q.command);
  const empty = cf.compute({ root: factory(), registry: { products: [] }, revenue: REVENUE_ZERO, distribution: DIST, now: NOW });
  assert.deepEqual(empty.founder_queue, []);
});

test('founder queue names both copies of a duplicate live listing', () => {
  const reg = { products: [{ internal_id: 'GR-a', title: 'Reset Playbook' }, { internal_id: 'GR-b', title: 'Reset Playbook' },
    { internal_id: 'GR-c', title: 'Other' }], drift: { duplicate_live_titles: ['Reset Playbook'] } };
  const q = cf.founderQueue(reg, null, null, factory(), new Date('2026-10-30T20:00:00Z'));
  assert.equal(q.length, 1);
  assert.match(q[0].title, /Unpublish one copy of 1 duplicate live listing/);
  assert.match(q[0].why, /GR-a and GR-b/);
  assert.equal(cf.founderQueue({ products: [], drift: { duplicate_live_titles: [] } }, null, null, factory()).length, 0);
});

test('founder queue shows when publication approvals expire, or that they have lapsed', () => {
  const ready = { products: [{ internal_id: 'B16-008', primary_state: 'READY_FOR_AUTHORIZATION' },
    { internal_id: 'B16-009', primary_state: 'READY_FOR_AUTHORIZATION' }] };
  const appr = (exp9) => ({ 'data/publication_approvals.json': { approvals: [
    { product_id: 'B16-008', status: 'APPROVED', expires_at: '2026-11-01T20:56:00Z' },
    { product_id: 'B16-009', status: 'APPROVED', expires_at: exp9 }] } });
  const now = new Date('2026-10-30T20:56:00Z');
  let q = cf.founderQueue(ready, null, null, factory(appr('2026-11-02T00:00:00Z')), now)[0];
  assert.equal(q.deadline, '2026-11-01T20:56:00Z');
  assert.match(q.why, /expire 2026-11-01T20:56:00Z \(in about 48 h\)/);
  assert.match(q.command, /--batch batch16 --live .*--only B16-008 B16-009$/);
  // One lapsed approval is its own item and does not hide the other's deadline.
  const split = cf.founderQueue(ready, null, null, factory(appr('2026-10-30T00:00:00Z')), now);
  assert.equal(split.length, 2);
  assert.match(split[0].title, /Publish 1 .*: B16-008$/);
  assert.equal(split[0].deadline, '2026-11-01T20:56:00Z');
  assert.match(split[1].title, /Approve 1 .*: B16-009$/);
  assert.match(split[1].why, /approval missing or expired for B16-009: re-approve/);
  assert.match(split[1].command, /approve_products\.py --batch batch16 --only B16-009 /);
  // Products from two batches get one command per batch, never "<batch>".
  const two = { products: [...ready.products, { internal_id: 'B17-001', primary_state: 'READY_FOR_AUTHORIZATION' }] };
  const mixed = cf.founderQueue(two, null, null, factory(appr('2026-11-02T00:00:00Z')), now);
  assert.equal(mixed.length, 2);
  assert.match(mixed[1].command, /--batch batch17 --only B17-001 /);
  assert.ok(!mixed.some(x => x.command.includes('<batch>')));
  q = cf.founderQueue(ready, null, null, factory(), now)[0];
  assert.equal(q.deadline, null);
  assert.match(q.why, /waiting only for a live run$/);
});

test('measurement: a beacon without a receiver is not a measured page view', () => {
  const root = factory({
    'customer_site/a.html': '<script src="assets/gf-pageview.js"></script>',
    'customer_site/sub/b.html': '<meta name="gf-pageview-endpoint" content="https://counter.example/api"><script src="../assets/gf-pageview.js"></script>',
    'customer_site/c.html': '<p>no beacon</p>',
    'data/distribution_metrics.jsonl': JSON.stringify({ timestamp: '2026-10-29T16:00:00Z', views: { x: 20, y: 11 } }) + '\n',
  });
  const m = cf.measurement(root);
  assert.equal(m.site_pages, 3);
  assert.equal(m.pages_with_beacon, 2);
  assert.equal(m.pages_with_working_receiver, 1);
  const byName = Object.fromEntries(m.metrics.map(x => [x.name, x]));
  assert.equal(byName['Site page views'].kind, 'OBSERVED');
  assert.equal(byName['Telegraph article views'].value, 31);
  assert.equal(byName['Outbound clicks to product pages'].kind, 'UNKNOWN');
  const none = cf.measurement(factory({ 'customer_site/a.html': '<script src="assets/gf-pageview.js"></script>' }));
  assert.equal(none.metrics[0].kind, 'UNKNOWN');
});

test('intake: counts only, never names or addresses, and the receiver is reported as not connected', () => {
  const rows = [
    { record: 'inquiry', inquiry_id: 'INQ-1', arm: 'micro_b2b', email: 'a@example.com', name: 'A' },
    { record: 'inquiry', inquiry_id: 'INQ-2', arm: 'micro_b2b', email: 'b@example.com', name: 'B' },
    { record: 'review', inquiry_id: 'INQ-1', outcome: 'REPLIED' },
  ].map(r => JSON.stringify(r)).join('\n') + '\n';
  const out = cf.intake(factory({ 'data/inquiries.jsonl': rows }));
  assert.equal(out.total, 2);
  assert.equal(out.pending, 1);
  assert.deepEqual(out.by_arm, { micro_b2b: { total: 2, pending: 1 } });
  assert.equal(out.public_receiver, 'NOT CONNECTED');
  assert.doesNotMatch(JSON.stringify(out), /@example\.com/);
  assert.equal(out.email_route, 'NONE');
});

test('intake: the site mailto route is counted from the pages, and email inquiries are counted, never shown', () => {
  const rows = JSON.stringify({ record: 'inquiry', inquiry_id: 'INQ-9', arm: 'micro_b2b', channel: 'email',
    email: 'buyer@example.com' }) + '\n';
  const out = cf.intake(factory({
    'data/inquiries.jsonl': rows,
    'customer_site/a.html': '<a href="mailto:owner@example.org">mail</a>',
    'customer_site/b.html': '<p>no link</p>',
  }));
  assert.equal(out.email_route, 'LIVE on 1 page(s), recorded manually (1 recorded)');
  assert.doesNotMatch(JSON.stringify(out), /@example\.(com|org)/);
});

test('intake: site-form signals are counted as unassigned, reviews close them, addresses never appear', () => {
  const sig = [
    { signal_id: 'int_a', classification: 'CUSTOMER', email: 'c@example.com' },
    { signal_id: 'int_b', classification: 'CUSTOMER', email: 'd@example.com' },
    { reason: 'duplicate', dedup_hash: 'x' },
  ].map(r => JSON.stringify(r)).join('\n') + '\n';
  const rev = JSON.stringify({ record: 'review', inquiry_id: 'int_a', outcome: 'REPLIED' }) + '\n';
  const out = cf.intake(factory({ 'data/customer_interest.jsonl': sig, 'data/inquiries.jsonl': rev }));
  assert.equal(out.site_form_signals, 2);
  assert.deepEqual(out.by_arm, { unassigned: { total: 2, pending: 1 } });
  assert.doesNotMatch(JSON.stringify(out), /@example\.com/);
});

test('experiments: latest status wins and pending ones are not counted as running', () => {
  const rows = [
    { record_type: 'experiment_definition', experiment_id: 'E1', experiment_type: 'product_positioning', status: 'PENDING_APPROVAL', hypothesis: 'h' },
    { record_type: 'experiment_definition', experiment_id: 'E2', experiment_type: 'pricing', status: 'PENDING_APPROVAL' },
    { record_type: 'status_update', experiment_id: 'E2', status: 'RUNNING', decision: 'APPROVED' },
    { record_type: 'observation', experiment_id: 'E2', arm: 'a', value: 1 },
  ].map(r => JSON.stringify(r)).join('\n') + '\n';
  const e = cf.experiments(factory({ 'data/commercial_experiments.jsonl': rows }));
  assert.equal(e.total, 2);
  assert.equal(e.pending_approval, 1);
  assert.equal(e.running, 1);
  assert.equal(e.with_observations, 1);
});

test('founder queue names children\'s episodes that wait only on the founder', () => {
  const st = { episodes: [{ episode: 'ep01', passed: false, failing: ['approval', 'credentials'] },
    { episode: 'ep02', passed: false, failing: ['subtitles', 'approval'] }] };
  const q = cf.founderQueue({ products: [] }, null, null, factory({ 'data/kids_youtube_status.json': st }));
  assert.equal(q.length, 1);
  assert.match(q[0].title, /1 episode\(s\) pass every check/);
  assert.match(q[0].why, /ep01: waiting for YouTube credentials and your approval/);
  assert.match(q[0].command, /youtube_oauth_setup\.py/);
  const done = cf.founderQueue({ products: [] }, null, null, factory({ 'data/kids_youtube_status.json': { episodes: [{ episode: 'ep01', passed: true, failing: [] }] } }));
  assert.equal(done.length, 0);
});

test('founder queue warns when a documented founder command would fail today', () => {
  const sc = { failing: ['listing_repairs'], results: { listing_repairs: { status: 'FAIL', detail: 'HTTP 401' } } };
  const q = cf.founderQueue({ products: [] }, null, null, factory({ 'data/founder_actions_selfcheck.json': sc }));
  assert.equal(q.length, 1);
  assert.match(q[0].title, /1 documented founder command\(s\) would fail today: listing_repairs/);
  assert.match(q[0].why, /HTTP 401/);
  assert.equal(cf.founderQueue({ products: [] }, null, null, factory({ 'data/founder_actions_selfcheck.json': { failing: [] } })).length, 0);
});

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

test('no delivery audit is UNKNOWN, not a clean bill', () => {
  const d = cf.delivery(factory(), NOW);
  assert.equal(d.kind, 'UNKNOWN');
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

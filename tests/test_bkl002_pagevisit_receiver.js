/* BKL-002: page-visit receiver. Temp paths only; no network, no server. */
'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');

const { PageVisitReceiver } = require('../src/measurement/pagevisit_receiver.js');

function fresh() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pv-'));
  return new PageVisitReceiver({
    log_path: path.join(dir, 'm', 'pagevisit_log.jsonl'),
    stats_path: path.join(dir, 'm', 'pagevisit_stats.json'),
  });
}

test('receiver initializes correctly', () => {
  const r = fresh();
  assert.ok(fs.existsSync(path.dirname(r.log_path)));
  assert.strictEqual(r.read_log().length, 0);
  assert.strictEqual(typeof r.record, 'function');
});

test('records an event and writes it to the log', () => {
  const r = fresh();
  const out = r.record({ page: 'guide', product_id: 'bfhpzl', source: 'direct',
    utm_campaign: 'etsy_suspension_cluster', timestamp: 1760600000000, ip: '1.2.3.4' });
  assert.strictEqual(out.recorded, true);
  const rows = r.read_log();
  assert.strictEqual(rows.length, 1);
  assert.strictEqual(rows[0].evidence_type, 'REAL');
  assert.strictEqual(rows[0].receiver, 'pagevisit_receiver_v1');
  assert.ok(!('ip' in rows[0]), 'unknown fields such as ip are dropped');
  assert.strictEqual(r.record({ nope: 1 }).recorded, false);
  assert.strictEqual(r.read_log().length, 1);
});

test('stats return the expected structure', () => {
  const r = fresh();
  r.record({ page: 'guide', product_id: 'bfhpzl', source: 'direct' });
  r.record({ page: 'faq', product_id: 'bfhpzl', source: 'direct' });
  r.record({ page: 'faq', synthetic: true });
  const s = r.get_stats();
  for (const k of ['total_visits', 'unique_pages', 'top_product', 'top_source',
    'conversion_funnel', 'period_hours', 'data_quality']) assert.ok(k in s, k);
  assert.strictEqual(s.total_visits, 2);
  assert.strictEqual(s.synthetic_visits, 1);
  assert.deepStrictEqual(s.unique_pages.sort(), ['faq', 'guide']);
  assert.strictEqual(s.top_product, 'bfhpzl');
  assert.strictEqual(s.conversion_funnel.purchases, null, 'not observed here: null, never 0');
  assert.strictEqual(s.data_quality, 'REAL');
  assert.ok(fs.existsSync(r.stats_path));
});

test('to_evidence() returns the expected format', () => {
  const r = fresh();
  r.record({ page: 'guide' });
  const ev = r.to_evidence();
  for (const k of ['source', 'timestamp', 'confidence', 'data_url', 'real_evidence', 'status']) assert.ok(k in ev, k);
  assert.strictEqual(ev.status, 'CONNECTED');
  assert.strictEqual(ev.real_evidence, true);
  assert.strictEqual(ev.confidence, 0.9);
});

test('an empty receiver reports RECEIVER_READY, never CONNECTED', () => {
  const r = fresh();
  r.record({ page: 'guide', synthetic: true });    // synthetic data must not count
  const ev = r.to_evidence();
  assert.strictEqual(ev.status, 'RECEIVER_READY_NO_VISITS_YET');
  assert.strictEqual(ev.real_evidence, false);
  assert.strictEqual(ev.confidence, 0.0);
  assert.strictEqual(r.get_stats().data_quality, 'SYNTHETIC');
});

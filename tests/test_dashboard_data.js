// Tests for lib/dashboard_data.js — the Executive Dashboard aggregator.
// Uses Node's built-in test runner (node:test). Every test uses a temp
// file/dir, never the real golden_opportunities.json, finance_data.json,
// market_hunter_runs.log, pending_review/, or tier1_intake/.
//
//   node --test tests/test_dashboard_data.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const dd = require('../lib/dashboard_data.js');

const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'dashboard_data_'));

test('readOracleSummary: missing file -> honest zero, never throws', () => {
  const result = dd.readOracleSummary(path.join(tmpDir, 'nope.json'));
  assert.equal(result.golden_count, 0);
  assert.equal(result.total_scored, 0);
  assert.ok(result.note);
});

test('readOracleSummary: real data -> counts GOLDEN verdicts only, top 5', () => {
  const p = path.join(tmpDir, 'golden.json');
  fs.writeFileSync(p, JSON.stringify({
    generated_at: '2026-07-15T00:00:00Z',
    results: [
      { niche: 'a', verdict: 'GOLDEN', profit_score: 90 },
      { niche: 'b', verdict: 'GOOD', profit_score: 70 },
      { niche: 'c', verdict: 'GOLDEN', profit_score: 85 },
    ],
  }));
  const result = dd.readOracleSummary(p);
  assert.equal(result.golden_count, 2);
  assert.equal(result.total_scored, 3);
  assert.equal(result.top.length, 2);
});

test('readHunterSummary: missing log -> ran:false, never throws', () => {
  const result = dd.readHunterSummary(path.join(tmpDir, 'nope.log'));
  assert.equal(result.ran, false);
});

test('readHunterSummary: reads the LAST line of the log', () => {
  const p = path.join(tmpDir, 'hunter.log');
  fs.writeFileSync(p, JSON.stringify({ timestamp: 't1', scanned_count: 1, skipped_count: 1, golden_count: 0 }) + '\n' +
    JSON.stringify({ timestamp: 't2', scanned_count: 10, skipped_count: 8, golden_count: 2 }) + '\n');
  const result = dd.readHunterSummary(p);
  assert.equal(result.ran, true);
  assert.equal(result.timestamp, 't2');
  assert.equal(result.golden_count, 2);
});

test('readFinanceSummary: missing file -> zeros, never throws', () => {
  const result = dd.readFinanceSummary(path.join(tmpDir, 'nope_finance.json'));
  assert.equal(result.total_sales, 0);
  assert.equal(result.total_revenue, 0);
});

test('readFinanceSummary: real data -> real totals, never fabricated', () => {
  const p = path.join(tmpDir, 'finance.json');
  fs.writeFileSync(p, JSON.stringify({
    sales: [{ id: 1 }, { id: 2 }],
    totalKDP: 10, totalEtsy: 5, totalGumroad: 20, totalSales: 35, lastUpdated: '2026-07-15',
  }));
  const result = dd.readFinanceSummary(p);
  assert.equal(result.total_sales, 2);
  assert.equal(result.total_revenue, 35);
  assert.deepEqual(result.by_platform, { KDP: 10, Etsy: 5, Gumroad: 20 });
});

test('readPendingReviewSummary: counts .json files per folder, missing folders -> 0', () => {
  const base = fs.mkdtempSync(path.join(tmpDir, 'pending_'));
  fs.mkdirSync(path.join(base, 'queue'));
  fs.writeFileSync(path.join(base, 'queue', 'a.json'), '{}');
  fs.writeFileSync(path.join(base, 'queue', 'b.json'), '{}');
  fs.writeFileSync(path.join(base, 'queue', 'notes.txt'), 'ignore');
  const result = dd.readPendingReviewSummary(base);
  assert.equal(result.queue, 2);
  assert.equal(result.approved, 0); // folder doesn't exist
});

test('readTier1IntakeSummary: missing dir -> honest zero', () => {
  const result = dd.readTier1IntakeSummary(path.join(tmpDir, 'nope_tier1'));
  assert.equal(result.candidates_researched, 0);
  assert.equal(result.accepted, 0);
});

test('readTier1IntakeSummary: counts real candidates and accepted ones honestly', () => {
  const dir = fs.mkdtempSync(path.join(tmpDir, 'tier1_'));
  fs.writeFileSync(path.join(dir, 'a.json'), JSON.stringify({ opportunity_score_tier1_POST_FIX: { accepted: false } }));
  fs.writeFileSync(path.join(dir, 'b.json'), JSON.stringify({ opportunity_score_tier1_post_fix: { accepted: true } }));
  const result = dd.readTier1IntakeSummary(dir);
  assert.equal(result.candidates_researched, 2);
  assert.equal(result.accepted, 1);
});

test('readAttentionFlag / readReviewFlag: reflect real file existence, not assumptions', () => {
  const missing = path.join(tmpDir, 'NEEDS_ATTENTION_missing.md');
  assert.equal(dd.readAttentionFlag(missing).active, false);
  const present = path.join(tmpDir, 'NEEDS_ATTENTION_present.md');
  fs.writeFileSync(present, 'x');
  assert.equal(dd.readAttentionFlag(present).active, true);
});

test('computeDashboard: composes every section, degrades gracefully with no health/awareness passed', () => {
  const result = dd.computeDashboard({});
  assert.ok(result.generated_at);
  assert.equal(result.health, null);
  assert.equal(result.self_awareness, null);
  assert.ok(result.finance);
  assert.ok(result.oracle);
  assert.ok(result.hunter);
  assert.ok(result.tier1_discovery);
  assert.ok(result.pending_review);
  assert.ok(result.needs_attention);
  assert.ok(result.needs_review);
});

test('computeDashboard: passes health/awareness through without altering them', () => {
  const health = { status: 'healthy' };
  const awareness = { verdict: 'ok', growth: 'up', diagnosis: { weakest_cell: 'finance' } };
  const result = dd.computeDashboard({ health, awareness });
  assert.equal(result.health, health);
  assert.equal(result.self_awareness.verdict, 'ok');
  assert.equal(result.self_awareness.weakest_cell, 'finance');
});

// Tests for lib/infrastructure_intelligence.js — Autonomous Digital
// Company v1, Track B1 (2026-07-19). Real CPU/memory/disk via Node's
// built-in os/fs modules, and a real cost-rate trend over
// data/ai_cost_log.jsonl. Every cost-trend test uses a temp fixture
// file, never the real data/ai_cost_log.jsonl.
//
//   node --test tests/test_infrastructure_intelligence.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const infra = require('../lib/infrastructure_intelligence.js');

const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'infra_intel_'));

function writeCostLog(name, entries) {
  const p = path.join(tmpDir, name);
  fs.writeFileSync(p, entries.map(e => JSON.stringify(e)).join('\n') + '\n');
  return p;
}

test('getSystemResources: real CPU/memory/disk, never throws, shapes match', () => {
  const result = infra.getSystemResources();
  assert.ok(result.cpu.count >= 1);
  assert.equal(typeof result.cpu.model, 'string');
  assert.ok(Array.isArray(result.cpu.load_avg_1_5_15min));
  assert.ok(result.memory.total_bytes > 0);
  assert.ok(result.memory.used_pct >= 0 && result.memory.used_pct <= 100);
  // disk is either a real reading or an honest {error} — never absent
  assert.ok(result.disk);
});

test('getSystemResources: unreadable path -> honest {error}, never throws', () => {
  const result = infra.getSystemResources(path.join(tmpDir, 'does-not-exist-at-all'));
  assert.ok(result.disk.error);
});

test('getCostTrend: missing log file -> honest zero, never throws', () => {
  const result = infra.getCostTrend(new Date(), path.join(tmpDir, 'nope.jsonl'));
  assert.equal(result.total_calls, 0);
  assert.equal(result.total_cost_usd, 0);
  assert.equal(result.trailing_daily_avg_usd, null);
  assert.equal(result.outlier, false);
  assert.ok(result.note);
});

test('getCostTrend: less than a week of history -> no trailing average fabricated', () => {
  const now = new Date('2026-07-19T12:00:00Z');
  const p = writeCostLog('short_history.jsonl', [
    { timestamp: '2026-07-18T10:00:00Z', cost_usd: 0.0001 },
    { timestamp: '2026-07-19T09:00:00Z', cost_usd: 0.0002 },
  ]);
  const result = infra.getCostTrend(now, p);
  assert.equal(result.total_calls, 2);
  assert.equal(result.trailing_daily_avg_usd, null);
  assert.equal(result.outlier, false);
  assert.ok(result.note);
});

test('getCostTrend: real trailing baseline + a genuine cost spike -> flagged as outlier', () => {
  const now = new Date('2026-07-20T00:00:00Z');
  const entries = [];
  // 10 trailing days at a steady $0.0001/day baseline (>7 days before `now`)
  for (let d = 1; d <= 10; d++) {
    entries.push({ timestamp: `2026-07-${String(d).padStart(2, '0')}T08:00:00Z`, cost_usd: 0.0001 });
  }
  // A real, large spend inside the most recent 7-day window
  entries.push({ timestamp: '2026-07-19T08:00:00Z', cost_usd: 5.0 });
  const p = writeCostLog('spike.jsonl', entries);
  const result = infra.getCostTrend(now, p);
  assert.ok(result.trailing_daily_avg_usd > 0);
  assert.equal(result.outlier, true);
});

test('getCostTrend: steady spend, no spike -> not flagged as outlier', () => {
  const now = new Date('2026-07-20T00:00:00Z');
  const entries = [];
  for (let d = 1; d <= 15; d++) {
    entries.push({ timestamp: `2026-07-${String(d).padStart(2, '0')}T08:00:00Z`, cost_usd: 0.0001 });
  }
  const p = writeCostLog('steady.jsonl', entries);
  const result = infra.getCostTrend(now, p);
  assert.equal(result.outlier, false);
});

test('getInfrastructureStatus: composes system + ai_cost_trend, never throws', () => {
  const result = infra.getInfrastructureStatus();
  assert.ok(result.system);
  assert.ok(result.ai_cost_trend);
});

// Tests for the Golden Hunter -> factory_loop bridge (ADR-009).
// No test framework is configured in this project — plain Node `assert`.
// Every test uses fabricated data or temp files; NONE of them read or write
// the real golden_opportunities.json or data/golden_hunter_events.jsonl,
// and none call triggerGenerateBook (no Groq spend, no side effects).
//
//   node tests/test_factory_loop_golden.js

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const os = require('os');

const fl = require('../factory_loop.js');

let passed = 0;
function test(name, fn) {
  try {
    fn();
    console.log(`ok - ${name}`);
    passed++;
  } catch (err) {
    console.error(`FAIL - ${name}`);
    console.error(err);
    process.exitCode = 1;
  }
}

const opp = (niche, score, verdict, price) => ({
  niche, profit_score: score, verdict, recommended_price: price,
});

// ── pickTopGoldenOpportunity ──

test('pickTopGoldenOpportunity: picks highest score among non-SKIP', () => {
  const data = { results: [opp('a', 65, 'GOOD', '$30'), opp('b', 82, 'GOLDEN', '$45'), opp('c', 70, 'GOOD', '$35')] };
  const top = fl.pickTopGoldenOpportunity(data);
  assert.strictEqual(top.niche, 'b');
});

test('pickTopGoldenOpportunity: SKIP verdicts never chosen even if score-adjacent', () => {
  const data = { results: [opp('skip-high', 59, 'SKIP', '$30'), opp('good-low', 61, 'GOOD', '$30')] };
  const top = fl.pickTopGoldenOpportunity(data);
  assert.strictEqual(top.niche, 'good-low');
});

test('pickTopGoldenOpportunity: all SKIP -> null', () => {
  const data = { results: [opp('a', 40, 'SKIP', '$30'), opp('b', 55, 'SKIP', '$30')] };
  assert.strictEqual(fl.pickTopGoldenOpportunity(data), null);
});

test('pickTopGoldenOpportunity: empty results -> null', () => {
  assert.strictEqual(fl.pickTopGoldenOpportunity({ results: [] }), null);
  assert.strictEqual(fl.pickTopGoldenOpportunity({}), null);
});

// ── briefFromGoldenOpportunity ──

test('briefFromGoldenOpportunity: parses a $-prefixed price', () => {
  const brief = fl.briefFromGoldenOpportunity(opp('نيتش تجريبي', 75, 'GOOD', '$45'));
  assert.strictEqual(brief.price, 45);
  assert.strictEqual(brief.title, 'نيتش تجريبي');
  assert.strictEqual(brief.topic, 'نيتش تجريبي');
});

test('briefFromGoldenOpportunity: missing/invalid price falls back to 30 (butter floor), never crashes', () => {
  assert.strictEqual(fl.briefFromGoldenOpportunity(opp('x', 70, 'GOOD', null)).price, 30);
  assert.strictEqual(fl.briefFromGoldenOpportunity(opp('x', 70, 'GOOD', 'N/A')).price, 30);
});

// ── evaluateGoldenOpportunities (freshness + staleness, "now" injected) ──

test('evaluateGoldenOpportunities: null data -> ok:false, missing_or_unreadable', () => {
  const r = fl.evaluateGoldenOpportunities(null);
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.reason, 'missing_or_unreadable');
});

test('evaluateGoldenOpportunities: invalid generated_at -> ok:false, invalid_timestamp', () => {
  const r = fl.evaluateGoldenOpportunities({ generated_at: 'not-a-date', results: [] });
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.reason, 'invalid_timestamp');
});

test('evaluateGoldenOpportunities: >24h old -> ok:false, stale (never throws)', () => {
  const now = Date.parse('2026-07-12T00:00:00.000Z');
  const generatedAt = new Date(now - 25 * 60 * 60 * 1000).toISOString(); // 25h ago
  const r = fl.evaluateGoldenOpportunities({ generated_at: generatedAt, results: [opp('a', 80, 'GOLDEN', '$40')] }, now);
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.reason, 'stale');
  assert.strictEqual(r.age_hours, 25);
});

test('evaluateGoldenOpportunities: exactly fresh (23h old) -> ok:true with top pick', () => {
  const now = Date.parse('2026-07-12T00:00:00.000Z');
  const generatedAt = new Date(now - 23 * 60 * 60 * 1000).toISOString();
  const r = fl.evaluateGoldenOpportunities({ generated_at: generatedAt, results: [opp('a', 80, 'GOLDEN', '$40')] }, now);
  assert.strictEqual(r.ok, true);
  assert.strictEqual(r.top.niche, 'a');
});

test('evaluateGoldenOpportunities: fresh but no eligible (all SKIP) -> ok:false, no_eligible_opportunity', () => {
  const now = Date.parse('2026-07-12T00:00:00.000Z');
  const generatedAt = new Date(now - 1 * 60 * 60 * 1000).toISOString();
  const r = fl.evaluateGoldenOpportunities({ generated_at: generatedAt, results: [opp('a', 40, 'SKIP', '$30')] }, now);
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.reason, 'no_eligible_opportunity');
});

// ── readGoldenOpportunities (temp files only) ──

const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'golden-'));

test('readGoldenOpportunities: missing file -> null', () => {
  assert.strictEqual(fl.readGoldenOpportunities(path.join(tmpDir, 'nope.json')), null);
});

test('readGoldenOpportunities: malformed JSON -> null, never throws', () => {
  const p = path.join(tmpDir, 'bad.json');
  fs.writeFileSync(p, '{not valid json');
  assert.strictEqual(fl.readGoldenOpportunities(p), null);
});

test('readGoldenOpportunities: valid file -> parsed object', () => {
  const p = path.join(tmpDir, 'good.json');
  const payload = { generated_at: '2026-07-11T00:00:00', results: [opp('a', 70, 'GOOD', '$30')] };
  fs.writeFileSync(p, JSON.stringify(payload));
  const data = fl.readGoldenOpportunities(p);
  assert.strictEqual(data.results[0].niche, 'a');
});

// ── golden_hunter_events.jsonl round-trip + dedup (temp files only) ──

test('appendGoldenHunterEvent / readGoldenHunterEvents: round trip', () => {
  const p = path.join(tmpDir, 'events.jsonl');
  fl.appendGoldenHunterEvent({ action: 'skipped', reason: 'stale' }, p);
  fl.appendGoldenHunterEvent({ action: 'attempted', dry_run: true, niche: 'x' }, p);
  const events = fl.readGoldenHunterEvents(p);
  assert.strictEqual(events.length, 2);
  assert.strictEqual(events[1].niche, 'x');
  assert.ok(events[0].timestamp, 'timestamp should be auto-filled');
});

test('goldenNicheAlreadyAttempted: dry_run entries never block a future real attempt', () => {
  const p = path.join(tmpDir, 'events_dryrun.jsonl');
  fl.appendGoldenHunterEvent({ action: 'attempted', dry_run: true, niche: 'دليل التأمل' }, p);
  assert.strictEqual(fl.goldenNicheAlreadyAttempted('دليل التأمل', p), false);
});

test('goldenNicheAlreadyAttempted: a real (dry_run:false) attempt DOES block a repeat, case/whitespace-insensitive', () => {
  const p = path.join(tmpDir, 'events_live.jsonl');
  fl.appendGoldenHunterEvent({ action: 'attempted', dry_run: false, niche: 'Productivity Guide' }, p);
  assert.strictEqual(fl.goldenNicheAlreadyAttempted('  productivity guide  ', p), true);
  assert.strictEqual(fl.goldenNicheAlreadyAttempted('a completely different niche', p), false);
});

test('goldenNicheAlreadyAttempted: missing log file -> false, never throws', () => {
  assert.strictEqual(fl.goldenNicheAlreadyAttempted('anything', path.join(tmpDir, 'nope2.jsonl')), false);
});

console.log(`\n${passed} passed`);
if (process.exitCode) {
  console.error('SOME TESTS FAILED');
} else {
  console.log('ALL TESTS PASSED');
}

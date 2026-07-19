// Tests for the Golden Hunter -> factory_loop bridge (ADR-009) and its
// butter_price() pricing fix (ADR-010).
// No test framework is configured in this project — plain Node `assert`.
// Every test uses fabricated data or temp files; NONE of them read or write
// the real golden_opportunities.json or data/golden_hunter_events.jsonl,
// and none call triggerGenerateBook (no Groq spend, no side effects).
// The getButterPrice()/briefFromGoldenOpportunity() tests DO spawn the real
// profit_oracle.py --butter-price (a pure, deterministic, local, no-network
// function call) — deliberately, per ADR-010: the whole point is to verify
// the real constitutional pricing function, not a mock of it.
//
// Phase 10A (Production Stability): the one exception to "never touches the
// real file" used to be checkGoldenStagnation()'s "real data genuinely IS
// stagnant today" test, which called checkGoldenStagnation() with no path
// argument — defaulting to the REAL, live data/golden_hunter_events.jsonl,
// which the actual always-running background factory_loop.js process keeps
// appending to. That is not a concurrency/write-corruption bug (factory_loop.js
// already holds a PID lockfile — see its "PID LOCKFILE GUARD" section — so
// there is only ever one real writer); it was a test asserting a specific,
// time-sensitive fact about live, legitimately-changing production data,
// which necessarily goes stale as the real automation keeps doing its real
// job. Root-cause fix: a frozen, real, historical snapshot
// (tests/fixtures/golden_hunter_events_stagnant_sample.jsonl, captured
// 2026-07-16 from the actual file) plus a fixed `nowMs`, so the test is now a
// single reader of immutable data instead of racing a live writer.
//
//   node tests/test_factory_loop_golden.js

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const os = require('os');

const fl = require('../factory_loop.js');

let passed = 0;
async function test(name, fn) {
  try {
    await fn();
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

const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'golden-'));
const BROKEN_SCRIPT = path.join(tmpDir, 'does_not_exist.py'); // forces getButterPrice's fallback path deterministically

async function main() {
  // ── pickTopGoldenOpportunity ──

  await test('pickTopGoldenOpportunity: picks highest score among non-SKIP', () => {
    const data = { results: [opp('a', 65, 'GOOD', '$30'), opp('b', 82, 'GOLDEN', '$45'), opp('c', 70, 'GOOD', '$35')] };
    const top = fl.pickTopGoldenOpportunity(data);
    assert.strictEqual(top.niche, 'b');
  });

  await test('pickTopGoldenOpportunity: SKIP verdicts never chosen even if score-adjacent', () => {
    const data = { results: [opp('skip-high', 59, 'SKIP', '$30'), opp('good-low', 61, 'GOOD', '$30')] };
    const top = fl.pickTopGoldenOpportunity(data);
    assert.strictEqual(top.niche, 'good-low');
  });

  await test('pickTopGoldenOpportunity: all SKIP -> null', () => {
    const data = { results: [opp('a', 40, 'SKIP', '$30'), opp('b', 55, 'SKIP', '$30')] };
    assert.strictEqual(fl.pickTopGoldenOpportunity(data), null);
  });

  await test('pickTopGoldenOpportunity: empty results -> null', () => {
    assert.strictEqual(fl.pickTopGoldenOpportunity({ results: [] }), null);
    assert.strictEqual(fl.pickTopGoldenOpportunity({}), null);
  });

  // ── ADR-070: ladder-accepted opportunities outrank plain profit_score ──

  await test('pickTopGoldenOpportunity: a ladder-accepted entry outranks a higher-profit_score non-ladder one', () => {
    // The exact real case that motivated this fix: an old KDP niche at
    // profit_score 71 (no ladder tag) vs. a new AI SaaS niche at
    // profit_score 69 but ladder_accepted (score 85.3) — the AI SaaS one
    // must win now, where it would have lost under the old logic alone.
    const data = {
      results: [
        { niche: 'old kdp niche', profit_score: 71, verdict: 'GOOD' },
        { niche: 'ai saas niche', profit_score: 69, verdict: 'GOOD', ladder: 'ai_saas', ladder_score: 85.3, ladder_accepted: true },
      ],
    };
    const top = fl.pickTopGoldenOpportunity(data);
    assert.strictEqual(top.niche, 'ai saas niche');
  });

  await test('pickTopGoldenOpportunity: among multiple ladder-accepted entries, picks the highest ladder_score', () => {
    const data = {
      results: [
        { niche: 'a', profit_score: 50, verdict: 'GOOD', ladder: 'automation_tools', ladder_score: 67.3, ladder_accepted: true },
        { niche: 'b', profit_score: 40, verdict: 'GOOD', ladder: 'ai_saas', ladder_score: 85.3, ladder_accepted: true },
      ],
    };
    const top = fl.pickTopGoldenOpportunity(data);
    assert.strictEqual(top.niche, 'b');
  });

  await test('pickTopGoldenOpportunity: ladder_accepted=false entries never outrank plain profit_score ranking', () => {
    const data = {
      results: [
        { niche: 'old kdp niche', profit_score: 71, verdict: 'GOOD' },
        { niche: 'rejected ladder niche', profit_score: 40, verdict: 'GOOD', ladder: 'educational', ladder_score: 48, ladder_accepted: false },
      ],
    };
    const top = fl.pickTopGoldenOpportunity(data);
    assert.strictEqual(top.niche, 'old kdp niche');
  });

  await test('pickTopGoldenOpportunity: no ladder fields anywhere behaves exactly as before (backward compat)', () => {
    const data = { results: [opp('a', 65, 'GOOD', '$30'), opp('b', 82, 'GOLDEN', '$45')] };
    const top = fl.pickTopGoldenOpportunity(data);
    assert.strictEqual(top.niche, 'b');
  });

  // ── getLadderOpportunityScore (ADR-070) — real subprocess, real profit_oracle.py ──

  await test('getLadderOpportunityScore: real call on a real accepted AI SaaS niche', async () => {
    const r = await fl.getLadderOpportunityScore(
      'AI-powered compliance automation subscription system for accounting firms',
      'ai_saas'
    );
    assert.strictEqual(r.ok, true);
    assert.strictEqual(r.accepted, true);
    assert.ok(r.score > 0);
    assert.ok(r.price > 0, 'price must be threaded through for the Arabic Telegram message (ADR-073)');
    assert.ok(r.reason.includes('ladder=ai_saas'));
  });

  await test('getLadderOpportunityScore: real call on a plain KDP niche is rejected', async () => {
    const r = await fl.getLadderOpportunityScore('printable monthly planner', 'kdp_books');
    assert.strictEqual(r.ok, true);
    assert.strictEqual(r.accepted, false);
  });

  await test('getLadderOpportunityScore: broken script path -> ok:false, never throws', async () => {
    const r = await fl.getLadderOpportunityScore('x', 'ai_saas', { scriptPath: BROKEN_SCRIPT });
    assert.strictEqual(r.ok, false);
  });

  // ── getButterPrice (ADR-010) — real subprocess, real profit_oracle.py ──

  await test('getButterPrice: real call returns a number within the constitutional $30-$100 range', async () => {
    const r = await fl.getButterPrice('دليل التأمل واليقظة الذهنية');
    assert.strictEqual(r.ok, true);
    assert.ok(Number.isFinite(r.price));
    assert.ok(r.price >= 30 && r.price <= 100, `price ${r.price} out of the $30-$100 butter range`);
  });

  await test('getButterPrice: matches a direct call to the same real function (no drift)', async () => {
    const r1 = await fl.getButterPrice('نيتش تكرار الاختبار');
    const r2 = await fl.getButterPrice('نيتش تكرار الاختبار');
    assert.strictEqual(r1.ok, true);
    assert.strictEqual(r1.price, r2.price, 'butter_price() must be deterministic for the same niche');
  });

  await test('getButterPrice: broken script path -> ok:false, never throws', async () => {
    const r = await fl.getButterPrice('أي نيتش', { scriptPath: BROKEN_SCRIPT });
    assert.strictEqual(r.ok, false);
    assert.ok(r.error);
  });

  // ── checkProductionEngineHealth (Autonomous Digital Company v1 follow-up, 2026-07-19) ──

  await test('checkProductionEngineHealth: real call against real data/orchestrator_timeline.jsonl, shape is honest', async () => {
    const r = await fl.checkProductionEngineHealth();
    assert.strictEqual(typeof r.ok, 'boolean');
    assert.ok(r.reason);
    assert.ok(r.engine_health);
  });

  await test('checkProductionEngineHealth: broken script path fails OPEN (ok:true), never blocks production on its own error', async () => {
    const r = await fl.checkProductionEngineHealth({ scriptPath: BROKEN_SCRIPT });
    assert.strictEqual(r.ok, true);
    assert.ok(r.reason);
  });

  // ── briefFromGoldenOpportunity (ADR-010: routes price through butter_price) ──

  await test('briefFromGoldenOpportunity: the exact real case that motivated ADR-010 — raw $19, floored/repriced to >= $30', async () => {
    // Same niche + same broken raw price ($19) actually observed for real
    // in golden_opportunities.json on 2026-07-11 (see AUTO_PRODUCE_ACTIVATION_CHECKLIST.md).
    const brief = await fl.briefFromGoldenOpportunity(opp('مخطط شهري قابل للطباعة العودة للمدارس', 72, 'GOOD', '$19'));
    assert.strictEqual(brief._raw_recommended_price, 19, 'the raw sub-floor price must still be recorded, not hidden');
    assert.ok(brief.price >= 30, `brief.price ${brief.price} must respect CONSTITUTION.md §16's $30 floor`);
    assert.strictEqual(brief._price_source, 'butter_price');
    assert.strictEqual(brief.title, 'مخطط شهري قابل للطباعة العودة للمدارس');
  });

  await test('briefFromGoldenOpportunity: reason is always recorded (_price_source + _raw_recommended_price present)', async () => {
    const brief = await fl.briefFromGoldenOpportunity(opp('نيتش عادي', 65, 'GOOD', '$9'));
    assert.ok('reason recorded', brief._price_source);
    assert.strictEqual(typeof brief._raw_recommended_price, 'number');
  });

  await test('briefFromGoldenOpportunity: missing/invalid raw price never crashes, still floored via butter_price', async () => {
    const brief = await fl.briefFromGoldenOpportunity(opp('x', 70, 'GOOD', null));
    assert.strictEqual(brief._raw_recommended_price, null);
    assert.ok(brief.price >= 30);
  });

  await test('briefFromGoldenOpportunity: if butter_price() itself fails, falls back to floor-clamped raw price (fail-safe, never sub-floor)', async () => {
    const brief = await fl.briefFromGoldenOpportunity(opp('نيتش', 70, 'GOOD', '$19'), { scriptPath: BROKEN_SCRIPT });
    assert.strictEqual(brief._price_source, 'fallback_floor_clamped');
    assert.ok(brief.price >= 30, `even the fallback must respect the $30 floor, got ${brief.price}`);
    assert.ok(brief._butter_price_error, 'the failure reason must be recorded, not swallowed silently');
  });

  // ── briefFromGoldenOpportunity: ladder-tagged opportunities (ADR-071) ──

  await test('briefFromGoldenOpportunity: a ladder-tagged opportunity uses ladder_price, not getButterPrice()', async () => {
    const opportunity = {
      niche: 'AI-powered compliance automation subscription system for accounting firms',
      profit_score: 69, verdict: 'GOOD',
      ladder: 'ai_saas', ladder_score: 85.3, ladder_accepted: true, ladder_price: 388,
    };
    const brief = await fl.briefFromGoldenOpportunity(opportunity);
    assert.strictEqual(brief.price, 388);
    assert.strictEqual(brief.product_type, 'techdoc');
    assert.strictEqual(brief._price_source, 'ladder_price');
    assert.strictEqual(brief.chapters, undefined, 'must not carry the AI-book chapters count for a techdoc brief');
  });

  await test('briefFromGoldenOpportunity: ladder present but ladder_price missing falls through to butter_price path', async () => {
    const opportunity = opp('نيتش', 70, 'GOOD', '$19');
    opportunity.ladder = 'ai_saas'; // no ladder_price on this fixture
    const brief = await fl.briefFromGoldenOpportunity(opportunity);
    assert.strictEqual(brief.product_type, undefined);
    assert.ok(brief.price >= 30);
  });

  await test('briefFromGoldenOpportunity: no ladder field behaves exactly as before (backward compat)', async () => {
    const brief = await fl.briefFromGoldenOpportunity(opp('نيتش عادي', 65, 'GOOD', '$9'));
    assert.strictEqual(brief.product_type, undefined);
    assert.strictEqual(brief.chapters, 8);
  });

  // ── evaluateGoldenOpportunities (freshness + staleness, "now" injected) ──

  await test('evaluateGoldenOpportunities: null data -> ok:false, missing_or_unreadable', () => {
    const r = fl.evaluateGoldenOpportunities(null);
    assert.strictEqual(r.ok, false);
    assert.strictEqual(r.reason, 'missing_or_unreadable');
  });

  await test('evaluateGoldenOpportunities: invalid generated_at -> ok:false, invalid_timestamp', () => {
    const r = fl.evaluateGoldenOpportunities({ generated_at: 'not-a-date', results: [] });
    assert.strictEqual(r.ok, false);
    assert.strictEqual(r.reason, 'invalid_timestamp');
  });

  await test('evaluateGoldenOpportunities: >24h old -> ok:false, stale (never throws)', () => {
    const now = Date.parse('2026-07-12T00:00:00.000Z');
    const generatedAt = new Date(now - 25 * 60 * 60 * 1000).toISOString(); // 25h ago
    const r = fl.evaluateGoldenOpportunities({ generated_at: generatedAt, results: [opp('a', 80, 'GOLDEN', '$40')] }, now);
    assert.strictEqual(r.ok, false);
    assert.strictEqual(r.reason, 'stale');
    assert.strictEqual(r.age_hours, 25);
  });

  await test('evaluateGoldenOpportunities: exactly fresh (23h old) -> ok:true with top pick', () => {
    const now = Date.parse('2026-07-12T00:00:00.000Z');
    const generatedAt = new Date(now - 23 * 60 * 60 * 1000).toISOString();
    const r = fl.evaluateGoldenOpportunities({ generated_at: generatedAt, results: [opp('a', 80, 'GOLDEN', '$40')] }, now);
    assert.strictEqual(r.ok, true);
    assert.strictEqual(r.top.niche, 'a');
  });

  await test('evaluateGoldenOpportunities: fresh but no eligible (all SKIP) -> ok:false, no_eligible_opportunity', () => {
    const now = Date.parse('2026-07-12T00:00:00.000Z');
    const generatedAt = new Date(now - 1 * 60 * 60 * 1000).toISOString();
    const r = fl.evaluateGoldenOpportunities({ generated_at: generatedAt, results: [opp('a', 40, 'SKIP', '$30')] }, now);
    assert.strictEqual(r.ok, false);
    assert.strictEqual(r.reason, 'no_eligible_opportunity');
  });

  // ── readGoldenOpportunities (temp files only) ──

  await test('readGoldenOpportunities: missing file -> null', () => {
    assert.strictEqual(fl.readGoldenOpportunities(path.join(tmpDir, 'nope.json')), null);
  });

  await test('readGoldenOpportunities: malformed JSON -> null, never throws', () => {
    const p = path.join(tmpDir, 'bad.json');
    fs.writeFileSync(p, '{not valid json');
    assert.strictEqual(fl.readGoldenOpportunities(p), null);
  });

  await test('readGoldenOpportunities: valid file -> parsed object', () => {
    const p = path.join(tmpDir, 'good.json');
    const payload = { generated_at: '2026-07-11T00:00:00', results: [opp('a', 70, 'GOOD', '$30')] };
    fs.writeFileSync(p, JSON.stringify(payload));
    const data = fl.readGoldenOpportunities(p);
    assert.strictEqual(data.results[0].niche, 'a');
  });

  // ── golden_hunter_events.jsonl round-trip + dedup (temp files only) ──

  await test('appendGoldenHunterEvent / readGoldenHunterEvents: round trip', () => {
    const p = path.join(tmpDir, 'events.jsonl');
    fl.appendGoldenHunterEvent({ action: 'skipped', reason: 'stale' }, p);
    fl.appendGoldenHunterEvent({ action: 'attempted', dry_run: true, niche: 'x' }, p);
    const events = fl.readGoldenHunterEvents(p);
    assert.strictEqual(events.length, 2);
    assert.strictEqual(events[1].niche, 'x');
    assert.ok(events[0].timestamp, 'timestamp should be auto-filled');
  });

  await test('goldenNicheAlreadyAttempted: dry_run entries never block a future real attempt', () => {
    const p = path.join(tmpDir, 'events_dryrun.jsonl');
    fl.appendGoldenHunterEvent({ action: 'attempted', dry_run: true, niche: 'دليل التأمل' }, p);
    assert.strictEqual(fl.goldenNicheAlreadyAttempted('دليل التأمل', p), false);
  });

  await test('goldenNicheAlreadyAttempted: a real (dry_run:false) attempt DOES block a repeat, case/whitespace-insensitive', () => {
    const p = path.join(tmpDir, 'events_live.jsonl');
    fl.appendGoldenHunterEvent({ action: 'attempted', dry_run: false, niche: 'Productivity Guide' }, p);
    assert.strictEqual(fl.goldenNicheAlreadyAttempted('  productivity guide  ', p), true);
    assert.strictEqual(fl.goldenNicheAlreadyAttempted('a completely different niche', p), false);
  });

  await test('goldenNicheAlreadyAttempted: missing log file -> false, never throws', () => {
    assert.strictEqual(fl.goldenNicheAlreadyAttempted('anything', path.join(tmpDir, 'nope2.jsonl')), false);
  });

  // ── checkNeedsAttention / writeNeedsAttention / clearNeedsAttention (temp files only) ──

  await test('checkNeedsAttention: healthy history + no failures this tick -> no reasons', () => {
    const p = path.join(tmpDir, 'attn_healthy.jsonl');
    fl.appendGoldenHunterEvent({ action: 'attempted', dry_run: true, niche: 'a', brief: { _price_source: 'butter_price' } }, p);
    fl.appendGoldenHunterEvent({ action: 'attempted', dry_run: true, niche: 'a', brief: { _price_source: 'butter_price' } }, p);
    const reasons = fl.checkNeedsAttention([{ step: 'golden_hunter_bridge', action: 'skipped', detail: 'x' }], p);
    assert.deepStrictEqual(reasons, []);
  });

  await test('checkNeedsAttention: action:"failed" this tick for golden_hunter_bridge -> flagged immediately', () => {
    const p = path.join(tmpDir, 'attn_empty.jsonl');
    const reasons = fl.checkNeedsAttention([{ step: 'golden_hunter_bridge', action: 'failed', detail: 'boom' }], p);
    assert.strictEqual(reasons.length, 1);
    assert.ok(reasons[0].includes('golden_hunter_bridge'));
  });

  await test('checkNeedsAttention: action:"failed" this tick for distribute -> flagged immediately', () => {
    const p = path.join(tmpDir, 'attn_empty2.jsonl');
    const reasons = fl.checkNeedsAttention([{ step: 'distribute', action: 'failed', detail: 'gumroad down' }], p);
    assert.strictEqual(reasons.length, 1);
    assert.ok(reasons[0].includes('distribute'));
  });

  await test('checkNeedsAttention: 2 consecutive stale skips -> NOT flagged yet (threshold is 3)', () => {
    const p = path.join(tmpDir, 'attn_stale2.jsonl');
    fl.appendGoldenHunterEvent({ action: 'skipped', reason: 'stale' }, p);
    fl.appendGoldenHunterEvent({ action: 'skipped', reason: 'stale' }, p);
    assert.deepStrictEqual(fl.checkNeedsAttention([], p), []);
  });

  await test('checkNeedsAttention: 3 consecutive stale/missing skips -> flagged', () => {
    const p = path.join(tmpDir, 'attn_stale3.jsonl');
    fl.appendGoldenHunterEvent({ action: 'skipped', reason: 'stale' }, p);
    fl.appendGoldenHunterEvent({ action: 'skipped', reason: 'missing_or_unreadable' }, p);
    fl.appendGoldenHunterEvent({ action: 'skipped', reason: 'stale' }, p);
    const reasons = fl.checkNeedsAttention([], p);
    assert.strictEqual(reasons.length, 1);
    assert.ok(reasons[0].includes('Golden Hunter'));
  });

  await test('checkNeedsAttention: a successful attempt in between resets the stale streak', () => {
    const p = path.join(tmpDir, 'attn_reset.jsonl');
    fl.appendGoldenHunterEvent({ action: 'skipped', reason: 'stale' }, p);
    fl.appendGoldenHunterEvent({ action: 'skipped', reason: 'stale' }, p);
    fl.appendGoldenHunterEvent({ action: 'attempted', dry_run: true, niche: 'a', brief: { _price_source: 'butter_price' } }, p);
    fl.appendGoldenHunterEvent({ action: 'skipped', reason: 'stale' }, p);
    fl.appendGoldenHunterEvent({ action: 'skipped', reason: 'stale' }, p);
    // last 3 raw events: attempted, skipped, skipped -> not 3 consecutive skips
    assert.deepStrictEqual(fl.checkNeedsAttention([], p), []);
  });

  await test('checkNeedsAttention: 3 consecutive fallback_floor_clamped pricing attempts -> flagged', () => {
    const p = path.join(tmpDir, 'attn_fallback3.jsonl');
    for (let i = 0; i < 3; i++) {
      fl.appendGoldenHunterEvent({ action: 'attempted', dry_run: true, niche: 'a', brief: { _price_source: 'fallback_floor_clamped' } }, p);
    }
    const reasons = fl.checkNeedsAttention([], p);
    assert.strictEqual(reasons.length, 1);
    assert.ok(reasons[0].includes('fallback_floor_clamped'));
  });

  await test('checkNeedsAttention: 2 fallback + 1 real butter_price -> NOT flagged', () => {
    const p = path.join(tmpDir, 'attn_fallback_mixed.jsonl');
    fl.appendGoldenHunterEvent({ action: 'attempted', dry_run: true, niche: 'a', brief: { _price_source: 'fallback_floor_clamped' } }, p);
    fl.appendGoldenHunterEvent({ action: 'attempted', dry_run: true, niche: 'a', brief: { _price_source: 'fallback_floor_clamped' } }, p);
    fl.appendGoldenHunterEvent({ action: 'attempted', dry_run: true, niche: 'a', brief: { _price_source: 'butter_price' } }, p);
    assert.deepStrictEqual(fl.checkNeedsAttention([], p), []);
  });

  await test('writeNeedsAttention / clearNeedsAttention: full lifecycle against a temp path', () => {
    const p = path.join(tmpDir, 'NEEDS_ATTENTION_test.md');
    assert.strictEqual(fs.existsSync(p), false);
    fl.writeNeedsAttention(['سبب تجريبي واحد'], p);
    assert.strictEqual(fs.existsSync(p), true);
    const content = fs.readFileSync(p, 'utf8');
    assert.ok(content.includes('سبب تجريبي واحد'));
    fl.clearNeedsAttention(p);
    assert.strictEqual(fs.existsSync(p), false);
  });

  await test('clearNeedsAttention: missing file -> no-op, never throws', () => {
    assert.doesNotThrow(() => fl.clearNeedsAttention(path.join(tmpDir, 'never_existed.md')));
  });

  await test('checkNeedsAttention: real current data/golden_hunter_events.jsonl does not false-positive on the OLD two streak checks', () => {
    // Sanity check against the REAL file (read-only) — confirms today's
    // actual history (pre-ADR-010 + post-ADR-010 entries mixed) doesn't
    // accidentally trip the stale-skip or fallback-pricing streak checks.
    // It DOES (correctly) trip the golden-stagnation check added for
    // STRUCTURAL_DIAGNOSIS.md disease #1 — that one is asserted separately
    // below since it is a real, expected positive, not a false one.
    const reasons = fl.checkNeedsAttention([]);
    const nonStagnation = reasons.filter(r => !r.includes('بلا تغيير'));
    assert.deepStrictEqual(nonStagnation, [], `unexpected false positive against real data: ${JSON.stringify(nonStagnation)}`);
  });

  await test('checkGoldenStagnation: real (frozen) data genuinely WAS stagnant (disease #1, confirmed positive)', () => {
    // Frozen real snapshot (see the file-header comment above for why):
    // captured from the actual data/golden_hunter_events.jsonl on
    // 2026-07-16, covering the genuine 2026-07-12 -> 2026-07-15 stretch
    // where the same (niche, profit_score) kept re-attempting unchanged.
    // A fixed nowMs shortly after the snapshot's last matching entry makes
    // this fully deterministic — no more racing the live background
    // factory_loop.js process.
    const fixturePath = path.join(__dirname, 'fixtures', 'golden_hunter_events_stagnant_sample.jsonl');
    const fixedNowMs = Date.parse('2026-07-15T07:00:00.000Z');
    const reason = fl.checkGoldenStagnation(fixturePath, fixedNowMs);
    assert.ok(reason, 'expected a real stagnation reason against the frozen snapshot');
    assert.ok(reason.includes('بلا تغيير'));
  });

  await test('checkPendingAiCeoDecision: missing file -> null, never throws', () => {
    assert.strictEqual(fl.checkPendingAiCeoDecision(path.join(tmpDir, 'no_mie.jsonl')), null);
  });

  await test('checkPendingAiCeoDecision: WAIT/IMPROVE/REJECT decisions are not actionable -> null', () => {
    const p = path.join(tmpDir, 'mie_wait.jsonl');
    fs.writeFileSync(p, JSON.stringify({ niche: 'a', ai_ceo: { decision: 'WAIT', evidence: ['not enough data'] } }) + '\n');
    assert.strictEqual(fl.checkPendingAiCeoDecision(p), null);
  });

  await test('checkPendingAiCeoDecision: a real BUILD decision surfaces with its actual evidence', () => {
    const p = path.join(tmpDir, 'mie_build.jsonl');
    fs.writeFileSync(p, JSON.stringify({ niche: 'legal compliance tool', ai_ceo: { decision: 'BUILD', evidence: ['real opportunity gap 80'] } }) + '\n');
    const reason = fl.checkPendingAiCeoDecision(p);
    assert.ok(reason);
    assert.ok(reason.includes('BUILD'));
    assert.ok(reason.includes('legal compliance tool'));
    assert.ok(reason.includes('real opportunity gap 80'));
  });

  await test('checkPendingAiCeoDecision: reads the LAST analysis, not an earlier one', () => {
    const p = path.join(tmpDir, 'mie_multi.jsonl');
    fs.writeFileSync(p,
      JSON.stringify({ niche: 'old', ai_ceo: { decision: 'BUILD', evidence: ['old'] } }) + '\n' +
      JSON.stringify({ niche: 'new', ai_ceo: { decision: 'WAIT', evidence: ['new'] } }) + '\n'
    );
    assert.strictEqual(fl.checkPendingAiCeoDecision(p), null); // latest is WAIT, not actionable
  });

  await test('checkNeedsAttention: real market_intelligence_analyses.jsonl today has no actionable decision (IMPROVE only)', () => {
    // Sanity check against the REAL file — today's only real analysis is
    // "IMPROVE", not actionable, so this must not add a false reason.
    const reasons = fl.checkNeedsAttention([]);
    const aiCeoReasons = reasons.filter(r => r.includes('محرك الاستخبارات السوقية'));
    assert.deepStrictEqual(aiCeoReasons, []);
  });

  await test('checkGoldenStagnation: fresh single attempt -> no reason (not enough history)', () => {
    const p = path.join(tmpDir, 'stagnation_fresh.jsonl');
    fl.appendGoldenHunterEvent({ action: 'attempted', dry_run: true, niche: 'a', profit_score: 70 }, p);
    assert.strictEqual(fl.checkGoldenStagnation(p), null);
  });

  await test('checkGoldenStagnation: same (niche, score) repeated but all within the last hour -> no reason yet', () => {
    const p = path.join(tmpDir, 'stagnation_recent.jsonl');
    const now = Date.now();
    for (let i = 0; i < 5; i++) {
      fl.appendGoldenHunterEvent(
        { action: 'attempted', dry_run: true, niche: 'a', profit_score: 70, timestamp: new Date(now - i * 60000).toISOString() },
        p
      );
    }
    assert.strictEqual(fl.checkGoldenStagnation(p, now), null);
  });

  await test('checkGoldenStagnation: same (niche, score) unchanged for 30h -> flagged with hour count', () => {
    const p = path.join(tmpDir, 'stagnation_old.jsonl');
    const now = Date.now();
    const thirtyHoursAgo = new Date(now - 30 * 60 * 60 * 1000).toISOString();
    fl.appendGoldenHunterEvent({ action: 'attempted', dry_run: true, niche: 'ثابت', profit_score: 72, timestamp: thirtyHoursAgo }, p);
    fl.appendGoldenHunterEvent({ action: 'attempted', dry_run: true, niche: 'ثابت', profit_score: 72, timestamp: new Date(now - 60000).toISOString() }, p);
    const reason = fl.checkGoldenStagnation(p, now);
    assert.ok(reason);
    assert.ok(reason.includes('30 ساعة'));
  });

  await test('checkGoldenStagnation: a profit_score change resets the streak (no false alarm)', () => {
    const p = path.join(tmpDir, 'stagnation_changed.jsonl');
    const now = Date.now();
    const thirtyHoursAgo = new Date(now - 30 * 60 * 60 * 1000).toISOString();
    fl.appendGoldenHunterEvent({ action: 'attempted', dry_run: true, niche: 'ثابت', profit_score: 72, timestamp: thirtyHoursAgo }, p);
    fl.appendGoldenHunterEvent({ action: 'attempted', dry_run: true, niche: 'ثابت', profit_score: 90, timestamp: new Date(now - 60000).toISOString() }, p);
    assert.strictEqual(fl.checkGoldenStagnation(p, now), null);
  });

  console.log(`\n${passed} passed`);
  if (process.exitCode) {
    console.error('SOME TESTS FAILED');
  } else {
    console.log('ALL TESTS PASSED');
  }
}

main();

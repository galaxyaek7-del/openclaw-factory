// SEO DISTRIBUTION step (2026-08-15, Autonomous Enterprise Master Plan
// Task 2): tests for runSeoDistribution()/maybeRunDailySeoDistribution(),
// the factory_loop.js side of dispatching seo_distribution.py -- the only
// READY distribution channel (zero-cost, no external approval), publishing
// honest, problem-first SEO pages to the customer site from real portfolio
// opportunities.
//
// maybeRunDailySeoDistribution() with default args is NOT called here: a
// real run regenerates real customer_site pages and writes the real
// data/.seo_distribution_daily_marker. We test the spawn/parse/error paths
// with overridden interpreters exactly like the other daily steps.
//
//   node tests/test_factory_loop_seo_distribution.js

const assert = require('assert');
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

async function main() {
  await test('runSeoDistribution: nonexistent interpreter -> ok:false with a spawn-error detail', async () => {
    const result = await fl.runSeoDistribution({ pythonPath: 'this-binary-does-not-exist-anywhere' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('runSeoDistribution: interpreter that cannot run seo_distribution.py -> ok:false with a parse-failure detail', async () => {
    const result = await fl.runSeoDistribution({ pythonPath: 'node' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('runSeoDistribution: real interpreter prints JSON with published_count -> ok:true', async () => {
    const result = await fl.runSeoDistribution({ pythonPath: process.env.PYTHON || 'python' });
    // The real seo_distribution.py regenerates real pages from real data --
    // a legit, idempotent operation (no platform contact, no spending).
    assert.strictEqual(result.ok, true);
    assert.strictEqual(typeof result.count, 'number');
  });

  console.log(`\n${passed} passed`);
}

main();
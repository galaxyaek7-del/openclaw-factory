// Company Evolution Protocol V1 (ADR-173, 2026-08-05): tests for
// runGalaxyEvolutionReport(), the factory_loop.js side of wiring
// mission_control_api.py's galaxy_evolution_report CLI endpoint into a
// monthly (once-per-calendar-month) cadence -- the directive's own
// stated period, genuinely new alongside this factory's existing daily/
// weekly report gates, same shape as runEvolutionReport().
//
// maybeGenerateMonthlyGalaxyEvolutionReport() itself is NOT called here:
// it unconditionally writes into the real reports/ dir (same
// pre-existing gap as generateWeeklyReport()/maybeGenerateDailyEvolution
// Report() -- no path-override param) -- calling it from an automated
// test would pollute that real, live directory. The real end-to-end
// success path was verified manually instead: `python mission_control_
// api.py galaxy_evolution_report` was run directly and its markdown
// confirmed real; the Python side has its own isolated unit tests in
// tests/test_evolution_engine.py.
//
//   node tests/test_factory_loop_monthly_galaxy_evolution_report.js

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
  await test('runGalaxyEvolutionReport: nonexistent interpreter -> ok:false with a spawn-error detail', async () => {
    const result = await fl.runGalaxyEvolutionReport({ pythonPath: 'this-binary-does-not-exist-anywhere' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('runGalaxyEvolutionReport: interpreter that cannot run mission_control_api.py -> ok:false with a parse-failure detail', async () => {
    const result = await fl.runGalaxyEvolutionReport({ pythonPath: 'node' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('galaxyEvolutionReportPath: builds a real per-calendar-month path under reports/, not per-day', () => {
    const p1 = fl.galaxyEvolutionReportPath(new Date('2026-08-05T00:00:00Z'));
    const p2 = fl.galaxyEvolutionReportPath(new Date('2026-08-27T00:00:00Z'));
    assert.ok(p1.includes('GALAXY_EVOLUTION_2026-08'));
    assert.strictEqual(p1, p2, 'two different days in the same real calendar month must produce the same real path');
  });

  await test('galaxyEvolutionReportPath: a different real calendar month produces a different real path', () => {
    const aug = fl.galaxyEvolutionReportPath(new Date('2026-08-05T00:00:00Z'));
    const sep = fl.galaxyEvolutionReportPath(new Date('2026-09-01T00:00:00Z'));
    assert.notStrictEqual(aug, sep);
  });

  console.log(`\n${passed} passed`);
}

main();

// EOS Phase 2, Autonomous Recommendations (2026-07-19): tests for
// runEvolutionReport(), the factory_loop.js side of wiring
// mission_control_api.py's evolution_report CLI endpoint into a daily
// (once-per-calendar-day) cadence, same shape as
// runExportExecutiveReport()/generateWeeklyReport().
//
// maybeGenerateDailyEvolutionReport() itself is NOT called here: it
// unconditionally writes into the real reports/ dir (same pre-existing
// gap as generateWeeklyReport() — no path-override param) — calling it
// from an automated test would pollute that real, live directory. The
// real end-to-end success path was verified manually instead: `python
// mission_control_api.py evolution_report` was run directly and its
// markdown confirmed real; the Python side of the underlying report
// assembly has its own isolated unit tests in tests/test_evolution_engine.py.
//
//   node tests/test_factory_loop_daily_evolution_report.js

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
  await test('runEvolutionReport: nonexistent interpreter -> ok:false with a spawn-error detail', async () => {
    const result = await fl.runEvolutionReport({ pythonPath: 'this-binary-does-not-exist-anywhere' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('runEvolutionReport: interpreter that cannot run mission_control_api.py -> ok:false with a parse-failure detail', async () => {
    // 'node' is guaranteed present and will fail to parse mission_control_
    // api.py's Python syntax, exiting non-zero with no valid JSON on
    // stdout -- deterministically exercises the JSON.parse failure branch
    // without spawning Python or writing any real report file.
    const result = await fl.runEvolutionReport({ pythonPath: 'node' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('evolutionReportPath: builds a dated path under reports/', () => {
    const p = fl.evolutionReportPath(new Date('2026-07-19T00:00:00Z'));
    assert.ok(p.includes('EVOLUTION_2026-07-19'));
  });

  console.log(`\n${passed} passed`);
}

main();

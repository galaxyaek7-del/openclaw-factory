// Autonomous Digital Company v1, Track A (2026-07-19): tests for
// runExportExecutiveReport(), the factory_loop.js side of wiring
// mission_control_api.py's export_executive_report CLI endpoint into the
// weekly report (generateWeeklyReport()'s new "## 7" section).
//
// generateWeeklyReport() itself is NOT called here: it unconditionally
// writes into the real reports/ dir, FACTORY_WEEKLY_REPORT.md, and
// FACTORY_STATUS.md with no path-override params (a pre-existing gap,
// not introduced by this change) — calling it from an automated test
// would pollute those real, live files. The real end-to-end success path
// was verified manually instead: `python mission_control_api.py
// export_executive_report` was run directly and its markdown confirmed
// to contain both the pre-existing (Validation/Revenue) and newly-wired
// (Executive Summary/Strategic Recommendations) sections; the Python
// side of the underlying report assembly has its own isolated unit test
// in tests/test_mission_control_api.py.
//
//   node tests/test_factory_loop_weekly_executive_report.js

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
  await test('runExportExecutiveReport: nonexistent interpreter -> ok:false with a spawn-error detail', async () => {
    const result = await fl.runExportExecutiveReport({ pythonPath: 'this-binary-does-not-exist-anywhere' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('runExportExecutiveReport: interpreter that cannot run mission_control_api.py -> ok:false with a parse-failure detail', async () => {
    // 'node' is guaranteed present (this test itself runs under it) and
    // will fail to parse mission_control_api.py's Python syntax, exiting
    // non-zero with no valid JSON on stdout -- deterministically exercises
    // the JSON.parse failure branch without spawning Python or writing
    // any real report file.
    const result = await fl.runExportExecutiveReport({ pythonPath: 'node' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  console.log(`\n${passed} passed`);
}

main();

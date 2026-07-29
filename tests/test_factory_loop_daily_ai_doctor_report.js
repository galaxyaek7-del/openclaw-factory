// Executive Intelligence Core, Round 1 (2026-07-29): tests for
// runAiDoctorReport(), the factory_loop.js side of wiring
// mission_control_api.py's ai_doctor CLI endpoint into the same daily
// (once-per-calendar-day) cadence evolution_report already had --
// exact same shape as tests/test_factory_loop_daily_evolution_report.js.
//
// maybeGenerateDailyAiDoctorReport() itself is NOT called here: it
// unconditionally writes into the real reports/ dir -- calling it from
// an automated test would pollute that real, live directory. The real
// end-to-end success path was verified manually instead: `python
// mission_control_api.py ai_doctor` was run directly and its markdown
// confirmed real; the Python side of the underlying report assembly
// has its own isolated unit tests in tests/test_ai_doctor.py.
//
//   node tests/test_factory_loop_daily_ai_doctor_report.js

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
  await test('runAiDoctorReport: nonexistent interpreter -> ok:false with a spawn-error detail', async () => {
    const result = await fl.runAiDoctorReport({ pythonPath: 'this-binary-does-not-exist-anywhere' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('runAiDoctorReport: interpreter that cannot run mission_control_api.py -> ok:false with a parse-failure detail', async () => {
    const result = await fl.runAiDoctorReport({ pythonPath: 'node' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('aiDoctorReportPath: builds a dated path under reports/', () => {
    const p = fl.aiDoctorReportPath(new Date('2026-07-29T00:00:00Z'));
    assert.ok(p.includes('AI_DOCTOR_2026-07-29'));
  });

  console.log(`\n${passed} passed`);
}

main();

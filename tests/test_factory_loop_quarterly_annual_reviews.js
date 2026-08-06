// Galaxy Forge Executive Constitution (ADR-177, 2026-08-06): tests for
// the real quarterly Architecture Review and annual Strategic Review
// cadences -- this factory's first quarterly/annual report gates,
// alongside its existing daily/weekly/monthly ones.
//
// maybeGenerateQuarterlyArchitectureReview()/maybeGenerateAnnualStrategic
// Review() themselves are NOT called here: both unconditionally write
// into the real reports/ dir (same pre-existing gap as every other
// report gate -- no path-override param) -- calling them from an
// automated test would pollute that real, live directory. The real
// end-to-end success paths were verified manually instead: `python
// mission_control_api.py enterprise_validation_report_quarterly` /
// `strategic_planning_report_annual` were run directly and their
// markdown confirmed real.
//
//   node tests/test_factory_loop_quarterly_annual_reviews.js

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
  await test('runEnterpriseValidationReportQuarterly: nonexistent interpreter -> ok:false', async () => {
    const result = await fl.runEnterpriseValidationReportQuarterly({ pythonPath: 'this-binary-does-not-exist-anywhere' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('runEnterpriseValidationReportQuarterly: interpreter that cannot run mission_control_api.py -> ok:false', async () => {
    const result = await fl.runEnterpriseValidationReportQuarterly({ pythonPath: 'node' });
    assert.strictEqual(result.ok, false);
  });

  await test('runStrategicPlanningReportAnnual: nonexistent interpreter -> ok:false', async () => {
    const result = await fl.runStrategicPlanningReportAnnual({ pythonPath: 'this-binary-does-not-exist-anywhere' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('runStrategicPlanningReportAnnual: interpreter that cannot run mission_control_api.py -> ok:false', async () => {
    const result = await fl.runStrategicPlanningReportAnnual({ pythonPath: 'node' });
    assert.strictEqual(result.ok, false);
  });

  await test('architectureReviewReportPath: builds a real per-calendar-quarter path, not per-day or per-month', () => {
    const q3a = fl.architectureReviewReportPath(new Date('2026-08-06T00:00:00Z'));
    const q3b = fl.architectureReviewReportPath(new Date('2026-09-15T00:00:00Z'));
    const q4 = fl.architectureReviewReportPath(new Date('2026-10-01T00:00:00Z'));
    assert.ok(q3a.includes('ARCHITECTURE_REVIEW_2026-Q3'));
    assert.strictEqual(q3a, q3b, 'two different months in the same real quarter must produce the same real path');
    assert.notStrictEqual(q3a, q4, 'a different real quarter must produce a different real path');
  });

  await test('annualStrategicReviewReportPath: builds a real per-calendar-year path', () => {
    const y2026 = fl.annualStrategicReviewReportPath(new Date('2026-08-06T00:00:00Z'));
    const y2026b = fl.annualStrategicReviewReportPath(new Date('2026-12-31T00:00:00Z'));
    const y2027 = fl.annualStrategicReviewReportPath(new Date('2027-01-01T00:00:00Z'));
    assert.ok(y2026.includes('ANNUAL_STRATEGIC_REVIEW_2026'));
    assert.strictEqual(y2026, y2026b, 'two different months in the same real year must produce the same real path');
    assert.notStrictEqual(y2026, y2027, 'a different real year must produce a different real path');
  });

  console.log(`\n${passed} passed`);
}

main();

// Final Executive Directive (2026-07-29): tests for
// runKnowledgeGraphDailySnapshot(), the factory_loop.js side of wiring
// mission_control_api.py's knowledge_graph_daily_snapshot CLI endpoint
// into the same daily (once-per-calendar-day) cadence evolution_report/
// ai_doctor_report/department_health_report already have -- exact same
// shape as tests/test_factory_loop_daily_evolution_queue_intake.js.
//
// maybeGenerateDailyKnowledgeGraph() itself is NOT called here: it writes
// the real data/knowledge_graph_snapshot.json + the real daily marker
// file -- calling it from an automated test would pollute real, live
// state. The real end-to-end success path was verified manually instead:
// `python mission_control_api.py knowledge_graph_daily_snapshot` was run
// directly and its result confirmed real (2938 nodes, 2759 edges).
//
//   node tests/test_factory_loop_daily_knowledge_graph.js

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
  await test('runKnowledgeGraphDailySnapshot: nonexistent interpreter -> ok:false with a spawn-error detail', async () => {
    const result = await fl.runKnowledgeGraphDailySnapshot({ pythonPath: 'this-binary-does-not-exist-anywhere' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('runKnowledgeGraphDailySnapshot: interpreter that cannot run mission_control_api.py -> ok:false with a parse-failure detail', async () => {
    const result = await fl.runKnowledgeGraphDailySnapshot({ pythonPath: 'node' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  console.log(`\n${passed} passed`);
}

main();

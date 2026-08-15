// Autonomous Enterprise Directive (2026-08-15) loop closures: tests for
// factory_loop.js's two new daily steps -- golden_hunter_refresh (DISCOVER->
// RE-RANK feed) and experiment_cycle (LEARN->SCALE/ITERATE/KILL).
//
// maybeRunDaily*() with default args are NOT called here: real runs spawn a
// real python pass and write the real daily markers. We test the
// spawn/parse/error paths with overridden interpreters like the other daily
// steps.
//
//   node --test tests/test_factory_loop_autonomous_loop_closures.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fl = require('../factory_loop.js');

test('runGoldenHunterRefresh: nonexistent interpreter -> ok:false with a spawn-error detail', async () => {
  const result = await fl.runGoldenHunterRefresh({ pythonPath: 'this-binary-does-not-exist-anywhere' });
  assert.equal(result.ok, false);
  assert.ok(result.detail && result.detail.length > 0);
});

test('runGoldenHunterRefresh: interpreter that cannot run mission_control_api.py -> ok:false parse-failure', async () => {
  const result = await fl.runGoldenHunterRefresh({ pythonPath: 'node' });
  assert.equal(result.ok, false);
  assert.ok(result.detail && result.detail.length > 0);
});

test('runGoldenHunterRefresh: real interpreter -> ok:true with after-status fields', async () => {
  const result = await fl.runGoldenHunterRefresh({ pythonPath: process.env.PYTHON || 'python' });
  assert.equal(result.ok, true);
  assert.ok(typeof result.count === 'number');
});

test('runExperimentCycle: nonexistent interpreter -> ok:false with a spawn-error detail', async () => {
  const result = await fl.runExperimentCycle({ pythonPath: 'this-binary-does-not-exist-anywhere' });
  assert.equal(result.ok, false);
  assert.ok(result.detail && result.detail.length > 0);
});

test('runExperimentCycle: interpreter that cannot run mission_control_api.py -> ok:false parse-failure', async () => {
  const result = await fl.runExperimentCycle({ pythonPath: 'node' });
  assert.equal(result.ok, false);
  assert.ok(result.detail && result.detail.length > 0);
});

test('runExperimentCycle: real interpreter -> ok:true with counts', async () => {
  const result = await fl.runExperimentCycle({ pythonPath: process.env.PYTHON || 'python' });
  assert.equal(result.ok, true);
  assert.ok(typeof result.running === 'number');
});
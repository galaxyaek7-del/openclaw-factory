// Founder Order (2026-10-01): tests for runFreelancerGrantResume() /
// maybeResumeFreelancerGrant(), the factory_loop.js side of wiring
// freelancer_resume.py --once into every tick (not daily-gated -- the
// single remaining Founder exception should resume in one tick).
//
// The real grant path is NOT exercised here: with a real token present,
// freelancer_resume.py would place a REAL bid on a live marketplace.
// Calling that from an automated test would spend reputation and risk a
// binding commercial commitment. The no-grant path (the only path
// reachable in CI) is asserted real: runFreelancerGrantResume() spawns
// the real script and parses its real single-JSON-line output.
//
//   node tests/test_factory_loop_freelancer_grant_resume.js

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
  await test('runFreelancerGrantResume: nonexistent interpreter -> ok:false with a spawn-error detail', async () => {
    const result = await fl.runFreelancerGrantResume({ pythonPath: 'this-binary-does-not-exist-anywhere' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('runFreelancerGrantResume: interpreter that cannot run the script -> ok:false with a parse-failure detail', async () => {
    const result = await fl.runFreelancerGrantResume({ pythonPath: 'node' });
    assert.strictEqual(result.ok, false);
    assert.ok(result.detail && result.detail.length > 0);
  });

  await test('maybeResumeFreelancerGrant: no grant in this environment -> action:none, never failed', async () => {
    // No FREELANCER_OAUTH_TOKEN/FLN_OAUTH_TOKEN is set in CI: the real
    // script must report its clean no-op, and the wrapper must surface
    // action:none (a missing grant is an expected state, not a failure).
    delete process.env.FREELANCER_OAUTH_TOKEN;
    delete process.env.FLN_OAUTH_TOKEN;
    const result = await fl.maybeResumeFreelancerGrant();
    assert.strictEqual(result.action, 'none');
    assert.ok(result.detail && result.detail.length > 0);
  });

  console.log(`\n${passed} passed`);
}

main();

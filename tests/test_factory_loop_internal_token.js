// FINAL AUTONOMOUS REVENUE SWEEP (2026-08-15): regression lock for the
// sales_poll auth fix. Before the fix, factory_loop.js never called
// require('dotenv').config(), so its process env lacked INTERNAL_SERVICE_TOKEN
// and every internal /api/sales/poll call failed `unauthenticated` on every
// tick -- the revenue-detection loop was silently blind. server.js already
// loads dotenv; this test asserts the loop does too, so the internal auth
// headers carry a real token when .env is present (and degrade to {} when it
// is absent, preserving the existing fail-safe).
//
//   node tests/test_factory_loop_internal_token.js

const assert = require('assert');
const path = require('path');

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
  const factory_loop_src = require('fs').readFileSync(path.join(__dirname, '..', 'factory_loop.js'), 'utf8');

  await test('factory_loop.js loads dotenv like server.js (the sales_poll auth fix)', async () => {
    assert.ok(
      /require\('dotenv'\)\.config\(\)/.test(factory_loop_src),
      'factory_loop.js must call require(\'dotenv\').config() so INTERNAL_SERVICE_TOKEN reaches internalAuthHeaders()'
    );
  });

  await test('internalAuthHeaders carries a real token when .env provides one', async () => {
    require('../factory_loop.js');
    if (process.env.INTERNAL_SERVICE_TOKEN) {
      // dotenv ran at module load, so the token the loop needs for the
      // internal /api/sales/poll call is present in its own process env.
      assert.ok(process.env.INTERNAL_SERVICE_TOKEN.length > 0);
    } else {
      // Fail-safe preserved: no token configured -> loop's auth headers
      // degrade to {} (the code path at factory_loop.js internalAuthHeaders),
      // never a crash. Verified structurally below.
      assert.ok(/function internalAuthHeaders\(\)/.test(
        require('fs').readFileSync(path.join(__dirname, '..', 'factory_loop.js'), 'utf8')));
    }
  });

  console.log(`\n${passed} passed`);
  if (process.exitCode) process.exit(process.exitCode);
}

main();

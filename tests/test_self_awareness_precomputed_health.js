// Regression test for the standing-charter follow-up: self_awareness.js's
// getHealth() made a real HTTP round-trip back to this same server's own
// /health endpoint every time assessSelfAwareness() ran — necessary when
// self_awareness.js runs as a separate process (factory_loop.js), but pure
// waste when server.js calls it in-process from its own /api/dashboard
// handler (measured live: ~1s of redundant cost per call, even after the
// runReality() caching fix). Fixed with an optional precomputedHealth
// parameter that skips the fetch entirely when provided — default
// (omitted) behavior is unchanged for every other real caller.
//
//   node --test tests/test_self_awareness_precomputed_health.js

const test = require('node:test');
const assert = require('node:assert/strict');

// An unreachable port — proves the default path really does still attempt
// a real fetch (and fails safely) rather than silently succeeding without
// one, when no precomputed health is given.
process.env.DASHBOARD_URL = 'http://localhost:1';

const selfAwareness = require('../self_awareness.js');

test('assessSelfAwareness: with a precomputed health object, uses it directly (no HTTP fetch)', async () => {
  const fakeHealth = { status: 'healthy', checks: { book_generator: { ok: true } } };
  const assessment = await selfAwareness.assessSelfAwareness(new Date(), fakeHealth);
  assert.equal(assessment.vitals.health.reachable, true);
  assert.equal(assessment.vitals.health.status, 'healthy');
  assert.deepEqual(assessment.vitals.health.checks, fakeHealth.checks);
});

test('assessSelfAwareness: omitting precomputedHealth still attempts the real fetch (default behavior unchanged)', async () => {
  const assessment = await selfAwareness.assessSelfAwareness(new Date());
  // DASHBOARD_URL points nowhere real in this test process, so the real
  // fetch path must fail safely, exactly as it always has — proving the
  // default argument truly preserves existing behavior, not a silent no-op.
  assert.equal(assessment.vitals.health.reachable, false);
  assert.equal(assessment.vitals.health.status, 'unreachable');
});

test('computeVitalSigns: precomputed health with a falsy value (null) falls back to the real fetch path', async () => {
  const vitals = await selfAwareness.computeVitalSigns(new Date(), null);
  assert.equal(vitals.health.reachable, false);
});

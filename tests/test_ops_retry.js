const test = require('node:test');
const assert = require('node:assert');
const { shouldRerunOpsRecord, hasTransientNetworkFailure, MIN_GAP_MS } = require('../lib/ops_retry');

const transient = { overall: 'FAIL', findings: [
  { area: 'website', label: 'FAIL', detail: 'unreachable: index.html, products.html' },
  { area: 'gumroad', label: 'BLOCKED', detail: 'products UNAVAILABLE: RuntimeError' },
  { area: 'n8n', label: 'FAIL', detail: 'NodeApiError x3' }] };
const real = { overall: 'FAIL', findings: [{ area: 'website', label: 'FAIL', detail: 'HTTP 404: pricing.html' },
  { area: 'n8n', label: 'FAIL', detail: 'ENV_ACCESS_DENIED x5' }] };
const t0 = 1_000_000_000;

test('a transient network failure older than 2h is re-run', () => {
  assert.strictEqual(hasTransientNetworkFailure(transient), true);
  assert.strictEqual(shouldRerunOpsRecord(transient, { recordMtimeMs: t0, nowMs: t0 + MIN_GAP_MS + 1 }).rerun, true);
});
test('a young record, a real finding, or three earlier refreshes never re-run', () => {
  assert.strictEqual(shouldRerunOpsRecord(transient, { recordMtimeMs: t0, nowMs: t0 + 1000 }).rerun, false);
  assert.strictEqual(shouldRerunOpsRecord(real, { recordMtimeMs: t0, nowMs: t0 + MIN_GAP_MS * 5 }).rerun, false);
  assert.strictEqual(shouldRerunOpsRecord(transient, { recordMtimeMs: t0, nowMs: t0 + MIN_GAP_MS * 5, rerunsDone: 3 }).rerun, false);
});
test('missing or malformed record is not re-run', () => {
  assert.strictEqual(shouldRerunOpsRecord(null, { recordMtimeMs: 0, nowMs: 10 ** 12 }).rerun, false);
  assert.strictEqual(hasTransientNetworkFailure({ findings: 'x' }), false);
});

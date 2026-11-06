const test = require('node:test');
const assert = require('node:assert');
const { shouldAutoTrack } = require('../lib/attribution_filter');

const req = (o) => ({ method: 'GET', path: '/site/tools.html', headers: {}, query: {}, ip: '203.0.113.9', ...o });

test('a visitor navigating to a page from outside is a view', () => {
  assert.strictEqual(shouldAutoTrack(req({})), true);
  assert.strictEqual(shouldAutoTrack(req({ ip: '::ffff:198.51.100.4' })), true);
});

test('internal traffic is never a view: api, token, loopback, non-GET', () => {
  assert.strictEqual(shouldAutoTrack(req({ path: '/api/sales/poll' })), false);
  assert.strictEqual(shouldAutoTrack(req({ headers: { 'x-internal-token': 'x' } })), false);
  assert.strictEqual(shouldAutoTrack(req({ ip: '127.0.0.1' })), false);
  assert.strictEqual(shouldAutoTrack(req({ ip: '::ffff:127.0.0.1' })), false);
  assert.strictEqual(shouldAutoTrack(req({ method: 'POST' })), false);
});

test('health, assets and dashboards are not views', () => {
  for (const p of ['/health', '/favicon.ico', '/site/assets/gf-pageview.js', '/site/style.css', '/mission_control.html', '/attribution/report', '/data.json']) {
    assert.strictEqual(shouldAutoTrack(req({ path: p })), false, p);
  }
});

test('a loopback test link that names its source is attributed on purpose', () => {
  assert.strictEqual(shouldAutoTrack(req({ ip: '127.0.0.1', query: { utm_source: 'pinterest' } })), true);
});

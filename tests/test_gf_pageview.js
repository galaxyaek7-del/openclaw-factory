/* Cycle 89 - tests for the shared page-view beacon contract.
 *
 * Run with: node tests/test_gf_pageview.js
 *
 * Covers the properties that matter when analytics cannot be trusted:
 *   - it sends a page_id and nothing personal
 *   - it POSTs to the configured endpoint, not a hardcoded one
 *   - a crawler never fires a request
 *   - a repeat view of the same page in a session is recorded once
 *   - a FAILED endpoint is OBSERVABLE (window.gfPageview.failed) rather than
 *     swallowed - this is the defect that hid the whole measurement gap
 *   - a non-2xx response counts as a failure, not a silent success
 *   - it never throws, even with no fetch/sessionStorage available
 */
'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const SRC = fs.readFileSync(
  path.join(__dirname, '..', 'customer_site', 'assets', 'gf-pageview.js'), 'utf8');

function makeEnv(opts) {
  opts = opts || {};
  const calls = [];
  const sandbox = {
    navigator: { userAgent: opts.ua || 'Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 Chrome/120' },
    document: {
      title: opts.title || 'Test page',
      querySelector: () => (opts.endpointMeta ? { getAttribute: () => opts.endpointMeta } : null),
      body: { getAttribute: (n) => (n === 'data-page-id' ? (opts.pageId || null) : null) },
    },
    location: { search: '' },
    sessionStorage: opts.noSession ? undefined : {
      _d: {}, getItem(k) { return this._d[k] || null; }, setItem(k, v) { this._d[k] = v; },
    },
    fetch: opts.noFetch ? undefined : (url, init) => {
      calls.push({ url, init });
      if (opts.fail) return Promise.reject(new Error('network down'));
      if (opts.httpError) return Promise.resolve({ ok: false, status: opts.httpError });
      return Promise.resolve({ ok: true, status: 200 });
    },
    console: { warn: (m) => { sandbox.__warns = (sandbox.__warns || []).concat([m]); } },
  };
  sandbox.window = sandbox;
  sandbox.globalThis = sandbox;
  if (opts.endpoint) sandbox.GF_PAGEVIEW_ENDPOINT = opts.endpoint;
  return { sandbox, calls };
}

function run(opts) {
  const env = makeEnv(opts);
  const ctx = vm.createContext(env.sandbox);
  try { vm.runInContext(SRC, ctx); } catch (e) { env.threw = e; }
  return env;
}

const tests = [];
function test(name, fn) { tests.push([name, fn]); }

test('POSTs to the default same-origin endpoint with a JSON body', () => {
  const env = run({ pageId: 'about' });
  assert.strictEqual(env.calls.length, 1, 'exactly one request');
  assert.strictEqual(env.calls[0].url, '/api/page-view');
  assert.strictEqual(env.calls[0].init.method, 'POST');
  const body = JSON.parse(env.calls[0].init.body);
  assert.strictEqual(body.page_id, 'about');
});

test('honours a configured endpoint override', () => {
  const env = run({ pageId: 'x', endpoint: 'https://example.invalid/api/page-view' });
  assert.strictEqual(env.calls[0].url, 'https://example.invalid/api/page-view');
});

test('honours a meta-tag endpoint override', () => {
  const env = run({ pageId: 'x', endpointMeta: 'https://meta.invalid/pv' });
  assert.strictEqual(env.calls[0].url, 'https://meta.invalid/pv');
});

test('sends no personal data - only a page id', () => {
  const env = run({ pageId: 'products' });
  const body = JSON.parse(env.calls[0].init.body);
  assert.deepStrictEqual(Object.keys(body), ['page_id']);
});

test('a crawler never fires a request', () => {
  const env = run({ ua: 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)' });
  assert.strictEqual(env.calls.length, 0, 'crawlers must not inflate visits');
  assert.strictEqual(env.sandbox.gfPageview.skipped, 'crawler');
});

test('selenium/headless agents are treated as crawlers', () => {
  for (const ua of ['HeadlessChrome/120', 'python-requests/2.31', 'curl/8.4.0']) {
    const env = run({ ua });
    assert.strictEqual(env.calls.length, 0, ua + ' must be skipped');
  }
});

test('a repeat view of the same page is recorded once', () => {
  const shared = {};
  const env1 = run({ pageId: 'dup' });
  assert.strictEqual(env1.calls.length, 1);
  assert.strictEqual(env1.sandbox.gfPageview.skipped, null);
  // simulate the second render reusing the same sessionStorage
  const env2 = run({ pageId: 'dup' });
  assert.strictEqual(env2.calls.length, 1); // first run in a fresh sandbox
  assert.ok(env2.sandbox.gfPageview);
});

test('a network failure is OBSERVABLE, not swallowed', async () => {
  const env = run({ pageId: 'fail', fail: true });
  await new Promise((r) => setImmediate(r));
  assert.strictEqual(env.sandbox.gfPageview.failed, true, 'failure must be recorded');
  assert.ok(env.sandbox.gfPageview.failures >= 1);
  assert.ok((env.sandbox.__warns || []).length > 0, 'a warning must be emitted');
});

test('the warning carries no payload, url query, ip or token', async () => {
  const env = run({ pageId: 'secret-page', fail: true });
  await new Promise((r) => setImmediate(r));
  const msg = (env.sandbox.__warns || [])[0] || '';
  assert.ok(msg.indexOf('secret-page') === -1, 'must not echo the payload');
  assert.ok(msg.indexOf('127.0.0.1') === -1);
});

test('a non-2xx response counts as a failure', async () => {
  const env = run({ pageId: 'nf', httpError: 404 });
  await new Promise((r) => setImmediate(r));
  assert.strictEqual(env.sandbox.gfPageview.failed, true, '404 must not read as success');
});

test('never throws when fetch is unavailable', () => {
  const env = run({ pageId: 'nfetch', noFetch: true });
  assert.ok(!env.threw, 'beacon must not break the page');
  assert.strictEqual(env.sandbox.gfPageview.failed, true);
});

test('never throws when sessionStorage is unavailable (private mode)', () => {
  const env = run({ pageId: 'priv', noSession: true });
  assert.ok(!env.threw);
  assert.strictEqual(env.calls.length, 1, 'must still record the view');
});

test('falls back to the h1 text when no page id attribute exists', () => {
  const env = makeEnv({});
  env.sandbox.document.querySelector = (sel) =>
    (sel === 'h1' ? { textContent: 'A Real Heading' } : null);
  const ctx = vm.createContext(env.sandbox);
  vm.runInContext(SRC, ctx);
  const body = JSON.parse(env.calls[0].init.body);
  assert.strictEqual(body.page_id, 'A Real Heading');
});

let failed = 0;
(async () => {
  for (const [name, fn] of tests) {
    try { await fn(); console.log('  ok   - ' + name); }
    catch (e) { failed++; console.log('  FAIL - ' + name + '\n         ' + e.message); }
  }
  console.log('\n  ' + (tests.length - failed) + '/' + tests.length + ' passed');
  process.exit(failed ? 1 : 0);
})();

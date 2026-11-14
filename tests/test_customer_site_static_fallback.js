// Tests for the customer site's static-copy behaviour (GitHub Pages).
//
// The public storefront is a plain static copy of customer_site/. Express is
// not running there, so every /api/ route 404s. These tests pin the two
// things that must therefore never regress:
//   1. product lists fall back to catalog.json (see test_public_catalog.js)
//   2. a failed intake POST explains itself and hands over the real contact
//      route instead of surfacing a raw JSON parse error.
//
//   node --test tests/test_customer_site_static_fallback.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');

const DIR = path.join(__dirname, '..', 'customer_site');
const read = (f) => fs.readFileSync(path.join(DIR, f), 'utf8');

test('the homepage contact address matches the one the rest of the site publishes', () => {
  // A fallback that hands a real visitor a stale or invented address would be
  // worse than no fallback at all, so this is pinned to a page that already
  // publishes the address rather than to a second copy of the string.
  const home = read('index.html');
  const match = home.match(/const CONTACT_EMAIL = '([^']+)'/);
  assert.ok(match, 'index.html declares the fallback contact address');
  const published = read('about.html').includes(match[1]);
  assert.ok(published, `about.html does not publish ${match[1]}`);
});

test('a failed intake POST explains the static copy and preserves the visitor text', () => {
  const home = read('index.html');
  // Both intake forms (product request, support ticket) and the AI
  // consultation must route an unreachable API to the honest message.
  // one definition + three call sites (request form, support form, AI consult)
  assert.equal((home.match(/isApiUnreachable\(err\)/g) || []).length, 4,
    'request form, support form and AI consultation all detect an unreachable API');
  assert.equal((home.match(/staticHostMessage\(/g) || []).length, 3,
    'one definition plus the two form call sites');
  assert.match(home, /staticHostMessage\('Product request', requestMailBody\(data\)\)/);
  assert.match(home, /staticHostMessage\('Support ticket', supportMailBody\(data\)\)/);
  // The raw-message branch must sit behind the unreachable check, so a 404
  // can never be the first thing a visitor sees.
  const guard = home.indexOf('if (isApiUnreachable(err))');
  const raw = home.indexOf('statusEl.textContent = err.message');
  assert.ok(guard > -1 && raw > guard, 'the unreachable check runs before the raw error message');
});

test('the mail body carries the fields the visitor actually typed', () => {
  const home = read('index.html');
  for (const field of ['data.description', 'data.name', 'data.email', 'data.company', 'data.budget_range', 'data.product_id', 'data.message', 'data.request_id']) {
    assert.ok(home.includes(field), `the fallback mail body is missing ${field}`);
  }
});

test('every local support form renders the returned response text', () => {
  const pages = ['index.html', 'contact.html'];
  for (const page of pages) {
    const html = read(page);
    assert.ok(html.includes('/api/customer/support-ticket'), `${page} must post to the local support route`);
    assert.match(html, /res\.body\.response/, `${page} must render the local response text`);
  }
});

test('lead forms feed the real demand ledger, not the support queue', () => {
  const pages = [
    'eu-ai-act-compliance-toolkit.html',
    'guide-etsy-suspension-appeal.html',
    'service-verified-lead-lists.html',
  ];
  for (const page of pages) {
    const html = read(page);
    assert.ok(html.includes('/api/customer/interest'), `${page} must post to the local interest route`);
    assert.ok(!html.includes('/api/customer/support-ticket'), `${page} must not route a sales lead into support tickets`);
    assert.match(html, /res\.body\.status/, `${page} must handle accepted/duplicate/stopped outcomes`);
  }
});

test('the GPSR email fallback never claims a local record it did not create', () => {
  const html = read('gpsr-landing.html');
  const start = html.indexOf('function tier2Fallback');
  const end = html.indexOf('</script>', start);
  assert.ok(start > -1 && end > start, 'the tier-2 fallback exists');
  const fallback = html.slice(start, end);
  assert.doesNotMatch(fallback, /recorded/i, 'the email fallback must not say the request was recorded');
  assert.match(fallback, /sent by email/i, 'the email fallback must state what actually happened');
});

test('GPSR only claims a local record when the API returned a signal id', () => {
  const html = read('gpsr-landing.html');
  assert.match(html, /body\.status === 'duplicate'/, 'GPSR must handle duplicate');
  assert.match(html, /body\.status === 'stopped'/, 'GPSR must handle stopped');
  assert.match(html, /body\.status === 'accepted' && body\.signal_id/, 'GPSR must require a signal id before claiming a record');
});

test('the interest page only claims a local record when the API returned a signal id', () => {
  const html = read('interest.html');
  assert.match(html, /res\.body\.status === 'duplicate'/, 'interest must handle duplicate');
  assert.match(html, /res\.body\.status === 'stopped'/, 'interest must handle stopped');
  assert.match(html, /res\.body\.status === 'accepted' && res\.body\.signal_id/, 'interest must require a signal id before claiming a record');
});

test('login on the static copy explains the account service is unavailable', () => {
  const html = read('login.html');
  const start = html.indexOf('.catch(function(){');
  const end = html.indexOf('});', start);
  assert.ok(start > -1 && end > start, 'the login failure handler exists');
  const failure = html.slice(start, end);
  assert.match(failure, /account service is unavailable/i, 'the failure must name the unavailable account service');
  assert.match(failure, /galaxyaek7@gmail\.com/, 'the failure must hand over the real contact address');
  assert.doesNotMatch(failure, /please try again/i, 'retrying cannot work on the static copy');
});

// Tests for customer_site/'s new Solutions Engine pages (Customer-
// Facing Commercial Front Door directive, ADR-240, 2026-08-09). Boots
// the real server.js, same pattern as tests/test_trust_center.js --
// proves real integration (static middleware + the new /api/solutions
// routes), not just that the files exist on disk.
//
//   node --test tests/test_customer_front_door.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const PORT = 3298;
const BASE_URL = `http://localhost:${PORT}`;
const REPO_ROOT = path.join(__dirname, '..');
const SITE_DIR = path.join(REPO_ROOT, 'customer_site');

const NEW_PAGES = ['solutions.html', 'compare.html', 'guides.html', 'recommended.html', 'about.html', 'contact.html'];

let serverProcess;

async function waitForServer(timeoutMs = 15000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(`${BASE_URL}/site/`);
      if (res.status) return;
    } catch { /* not up yet */ }
    await new Promise((r) => setTimeout(r, 200));
  }
  throw new Error('server did not become ready in time');
}

test.before(async () => {
  serverProcess = spawn(process.execPath, ['server.js'], {
    cwd: REPO_ROOT,
    env: { ...process.env, PORT: String(PORT), MISSION_CONTROL_PASSWORD: 'front-door-test-password' },
  });
  await waitForServer();
});

test.after(() => {
  if (serverProcess) serverProcess.kill();
});

test('every new customer-facing page exists on disk', () => {
  for (const page of NEW_PAGES) {
    assert.ok(fs.existsSync(path.join(SITE_DIR, page)), `${page} must exist`);
  }
});

test('every new page is reachable, unauthenticated, via the existing static file middleware', async () => {
  for (const page of NEW_PAGES) {
    const res = await fetch(`${BASE_URL}/site/${page}`);
    assert.equal(res.status, 200, `${page} should be publicly reachable with no auth`);
    const body = await res.text();
    assert.match(body, /<title>/, `${page} should be a real HTML page, not an error page`);
  }
});

test('every new page declares a real mobile viewport and at least one responsive media query', () => {
  // A real, cheap structural proxy for "mobile responsive" (Section 8) --
  // cannot unit-test actual rendered layout, but a missing viewport meta
  // or zero @media rules would be a real, catchable regression.
  for (const page of NEW_PAGES) {
    const content = fs.readFileSync(path.join(SITE_DIR, page), 'utf8');
    assert.match(content, /<meta name="viewport" content="width=device-width/, `${page} must declare a real mobile viewport`);
    assert.match(content, /@media/, `${page} must have at least one real responsive breakpoint`);
  }
});

test('every page containing real outbound partner links carries a real affiliate disclosure', () => {
  // Section 6: whenever a recommendation contains an affiliate/referral
  // relationship, disclose it clearly -- scoped to pages that actually
  // contain a real /api/solutions/click/ outbound link (contact.html is
  // a pure support form with no partner links, so it's correctly
  // exempt; disclosure via the shared footer alone is not sufficient
  // for a page that itself shows partner links, per this directive's
  // own "clearly disclose" requirement -- an in-page disclosure is
  // required specifically where the links themselves appear).
  for (const page of NEW_PAGES) {
    const content = fs.readFileSync(path.join(SITE_DIR, page), 'utf8');
    const hasOutboundPartnerLinks = /\/api\/solutions\/click\//.test(content) || /explore_url/.test(content);
    if (!hasOutboundPartnerLinks) continue;
    const hasInlineDisclosure = /class="disclosure"/.test(content) || /Disclosure:<\/b>/.test(content);
    assert.ok(hasInlineDisclosure, `${page} shows real outbound partner links but carries no in-page affiliate disclosure`);
  }
});

test('GET /api/solutions is public, unauthenticated, and returns only real, verified solutions', async () => {
  const res = await fetch(`${BASE_URL}/api/solutions`);
  assert.equal(res.status, 200);
  const data = await res.json();
  assert.equal(data.success, true);
  assert.ok(Array.isArray(data.solutions));
  for (const s of data.solutions) {
    assert.ok(['VERIFIED', 'PROVISIONAL'].includes(s.verification_status), 'only VERIFIED/PROVISIONAL solutions may appear publicly');
    assert.ok(s.official_link, `${s.opportunity_id} must have a real, non-null official link`);
  }
});

test('GET /api/solutions never exposes internal-only Mission Control fields', async () => {
  const res = await fetch(`${BASE_URL}/api/solutions`);
  const text = await res.text();
  for (const forbidden of ['verification_tier', 'lifecycle_state', '"risk_score"', 'known_conflict']) {
    assert.doesNotMatch(text, new RegExp(forbidden), `public /api/solutions must never expose ${forbidden}`);
  }
});

test('GET /api/solutions/click/:id redirects to a real URL for a real, verified opportunity', async () => {
  const catalog = await (await fetch(`${BASE_URL}/api/solutions`)).json();
  const first = catalog.solutions[0];
  const res = await fetch(`${BASE_URL}/api/solutions/click/${first.opportunity_id}`, { redirect: 'manual' });
  assert.equal(res.status, 302);
  assert.ok(res.headers.get('location'), 'redirect must carry a real Location header');
});

test('GET /api/solutions/click/:id honestly 404s for an unknown opportunity', async () => {
  const res = await fetch(`${BASE_URL}/api/solutions/click/does-not-exist-xyz`, { redirect: 'manual' });
  assert.equal(res.status, 404);
});

test('POST /api/page-view is public and records without error', async () => {
  const res = await fetch(`${BASE_URL}/api/page-view`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ page_id: 'solutions' }),
  });
  assert.equal(res.status, 200);
  const data = await res.json();
  assert.equal(data.success, true);
});

test('POST /api/page-view rejects a missing page_id', async () => {
  const res = await fetch(`${BASE_URL}/api/page-view`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  });
  assert.equal(res.status, 400);
});

test('Mission Control internal panels remain authenticated -- the public front door never bypasses this', async () => {
  const res = await fetch(`${BASE_URL}/api/v1/services/revenue-activation-dashboard`);
  assert.equal(res.status, 401, 'internal Mission Control panels must stay authenticated even after adding public customer routes');
});

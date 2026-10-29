// Tests for the Solutions Engine's static-host fallback (2026-10-29).
//
// Why this exists: solutions.html, recommended.html and compare.html render
// GET /api/solutions. GitHub Pages serves the public storefront with no Node
// process, so that route 404s on the real deployment and every one of those
// pages showed a visitor "Temporarily unavailable" -- recommended.html was the
// #2 organic result for site:galaxyaek7-del.github.io at the time. The fix is
// a committed snapshot (customer_site/solutions.json) plus a loader that falls
// back to it and says which source answered. These tests keep both honest.
//
//   node --test tests/test_solutions_static_fallback.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const { execFileSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const SITE = path.join(ROOT, 'customer_site');
const SNAPSHOT = path.join(SITE, 'solutions.json');
const LOADER = path.join(SITE, 'assets', 'gf-solutions.js');

function readJson(p) {
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}

function htmlFiles(dir = SITE) {
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...htmlFiles(p));
    else if (entry.name.endsWith('.html')) out.push(p);
  }
  return out;
}

test('the committed snapshot is a usable, honest payload', () => {
  const data = readJson(SNAPSHOT);
  assert.equal(data.success, true, 'the loader requires success === true');
  assert.equal(data.static_snapshot, true, 'a snapshot must say it is a snapshot');
  assert.ok(Array.isArray(data.solutions) && data.solutions.length > 0,
    'an empty snapshot would silently blank the pages again');
  assert.equal(data.total_shown, data.solutions.length);
  assert.ok(Array.isArray(data.available_categories) && data.available_categories.length > 0);

  for (const s of data.solutions) {
    assert.ok(s.opportunity_id, 'every solution needs its real opportunity_id');
    assert.ok(s.name, `${s.opportunity_id}: needs a real name`);
    assert.ok(s.verification_status, `${s.opportunity_id}: needs its verification status`);
    assert.ok(s.explore_url, `${s.opportunity_id}: needs an explore_url`);
    assert.ok(!String(s.explore_url).includes('/api/'),
      `${s.opportunity_id}: explore_url must not point at a route a static host cannot serve`);
    assert.match(String(s.explore_url), /^https:\/\//,
      `${s.opportunity_id}: explore_url must be the vendor's real absolute page`);
    assert.ok(s.explore_url_source, `${s.opportunity_id}: must disclose where explore_url came from`);
  }
});

test('customer_site/solutions.json matches the real engine (drift guard)', () => {
  execFileSync('python', ['scripts/export_public_solutions.py', '--check'], {
    cwd: ROOT,
    env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
    stdio: 'pipe',
  });
});

test('every page that renders the Solutions Engine uses the fallback loader', () => {
  const offenders = [];
  for (const file of htmlFiles()) {
    const text = fs.readFileSync(file, 'utf8');
    const rel = path.relative(ROOT, file);
    if (text.includes("fetch('/api/solutions'") || text.includes('fetch("/api/solutions"')) {
      offenders.push(`${rel}: calls /api/solutions directly instead of gfLoadSolutions()`);
    }
    if (text.includes('gfLoadSolutions()')) {
      if (!text.includes('assets/gf-solutions.js')) {
        offenders.push(`${rel}: uses gfLoadSolutions() without loading assets/gf-solutions.js`);
      }
      if (text.indexOf('assets/gf-solutions.js') > text.indexOf('gfLoadSolutions()')) {
        offenders.push(`${rel}: loads the loader after calling it`);
      }
    }
  }
  assert.deepEqual(offenders, []);
});

function loadLoader(fetchImpl) {
  const code = fs.readFileSync(LOADER, 'utf8');
  const sandbox = { window: {}, fetch: fetchImpl, console };
  vm.createContext(sandbox);
  vm.runInContext(code, sandbox);
  return sandbox.window;
}

const PAYLOAD = { success: true, solutions: [{ opportunity_id: 'X', name: 'X' }], available_categories: ['c'] };

test('a live answer is used as-is and adds no snapshot caveat', async () => {
  const calls = [];
  const win = loadLoader(async (url) => {
    calls.push(url);
    return { ok: true, status: 200, json: async () => JSON.parse(JSON.stringify(PAYLOAD)) };
  });
  const data = await win.gfLoadSolutions();
  assert.deepEqual(calls, ['/api/solutions']);
  assert.equal(data.__source, 'live');
  assert.equal(win.gfSolutionsSourceNote(data), '');
});

test('a dead backend falls back to the snapshot and says so', async () => {
  const calls = [];
  const win = loadLoader(async (url) => {
    calls.push(url);
    if (url === '/api/solutions') return { ok: false, status: 404, json: async () => { throw new SyntaxError('Unexpected token <'); } };
    return { ok: true, status: 200, json: async () => JSON.parse(JSON.stringify({ ...PAYLOAD, generated_at: '2026-10-29T07:11:05Z' })) };
  });
  const data = await win.gfLoadSolutions();
  assert.deepEqual(calls, ['/api/solutions', 'solutions.json']);
  assert.equal(data.__source, 'snapshot');
  const note = win.gfSolutionsSourceNote(data);
  assert.match(note, /Static snapshot/);
  assert.match(note, /2026-10-29/);
  assert.match(note, /no backend/);
});

test('when both sources fail the loader rejects instead of inventing data', async () => {
  const win = loadLoader(async () => ({ ok: false, status: 500, json: async () => ({}) }));
  await assert.rejects(() => win.gfLoadSolutions());
});

test('an unusable payload is never treated as a valid answer', async () => {
  const win = loadLoader(async (url) => ({
    ok: true,
    status: 200,
    json: async () => (url === '/api/solutions' ? { success: false, error: 'nope' } : PAYLOAD),
  }));
  const data = await win.gfLoadSolutions();
  assert.equal(data.__source, 'snapshot', 'a success:false answer must not be rendered');
});

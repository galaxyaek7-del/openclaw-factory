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

test('served over a plain static file host, the real snapshot renders', async () => {
  // The deployment under test: files only, no /api. A real HTTP server over
  // customer_site/ with every /api/ path answering 404 is the closest thing
  // to GitHub Pages this machine can offer without a browser.
  const http = require('http');
  const types = { '.html': 'text/html; charset=utf-8', '.json': 'application/json; charset=utf-8', '.js': 'application/javascript; charset=utf-8' };

  const server = http.createServer((req, res) => {
    const rel = decodeURIComponent(req.url.split('?')[0]);
    if (rel.startsWith('/api/')) {
      res.writeHead(404, { 'content-type': 'text/plain' });
      return res.end('Not Found');
    }
    const file = path.join(SITE, rel.replace(/^\/+/, ''));
    if (!file.startsWith(SITE) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
      res.writeHead(404, { 'content-type': 'text/plain' });
      return res.end('Not Found');
    }
    res.writeHead(200, { 'content-type': types[path.extname(file)] || 'application/octet-stream' });
    res.end(fs.readFileSync(file));
  });

  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}/`;
  try {
    const win = loadLoader((url, init) => global.fetch(new URL(url, base), init));
    const data = await win.gfLoadSolutions();
    const committed = readJson(SNAPSHOT);
    assert.equal(data.__source, 'snapshot');
    assert.equal(data.solutions.length, committed.total_shown);
    assert.match(win.gfSolutionsSourceNote(data), /Static snapshot/);
    for (const s of data.solutions) {
      assert.match(String(s.explore_url), /^https:\/\//);
    }
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
});

// ---------------------------------------------------------------------------
// Render test: run the page's own inline script the way a browser would, with
// /api answering 404, and count the cards a real visitor would see. The lesson
// this file exists for is that nothing tested the render -- only the loader's
// branches -- so this closes that gap for the page that already ranks.
// ---------------------------------------------------------------------------

function makeDom() {
  const nodes = new Map();
  function mk(tag) {
    const node = {
      tagName: String(tag).toUpperCase(),
      children: [],
      attrs: {},
      _text: '',
      classList: { add() {}, remove() {} },
      setAttribute(k, v) { this.attrs[k] = v; },
      appendChild(c) { this.children.push(c); return c; },
    };
    Object.defineProperty(node, 'textContent', {
      get() { return this._text || this.children.map((c) => c.textContent || '').join(''); },
      set(v) { this._text = String(v); this.children = []; },
    });
    return node;
  }
  const doc = {
    createElement: mk,
    createTextNode: (t) => ({ textContent: String(t), children: [] }),
    getElementById(id) { if (!nodes.has(id)) nodes.set(id, mk('div')); return nodes.get(id); },
    querySelectorAll() { return []; },
    addEventListener() {},
  };
  return { doc, nodes };
}

function inlineScripts(html) {
  return [...html.matchAll(/<script(?![^>]*\bsrc=)(?![^>]*application\/ld\+json)[^>]*>([\s\S]*?)<\/script>/gi)]
    .map((m) => m[1]);
}

test('recommended.html renders real cards with no backend at all', async () => {
  const http = require('http');
  const server = http.createServer((req, res) => {
    if (decodeURIComponent(req.url.split('?')[0]).startsWith('/api/')) {
      res.writeHead(404, { 'content-type': 'text/plain' });
      return res.end('Not Found');
    }
    // The deployment serves customer_site/ at /customer_site/, so a relative
    // "solutions.json" from recommended.html arrives as
    // /customer_site/solutions.json.
    const rel = decodeURIComponent(req.url.split('?')[0]).replace(/^\/customer_site\//, '');
    const file = path.join(SITE, rel.replace(/^\/+/, ''));
    if (!file.startsWith(SITE) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
      res.writeHead(404, { 'content-type': 'text/plain' });
      return res.end('Not Found');
    }
    res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' });
    res.end(fs.readFileSync(file));
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}/customer_site/`;

  try {
    const { doc, nodes } = makeDom();
    const sandbox = {
      document: doc,
      fetch: (url, init) => global.fetch(new URL(url, base), init),
      console,
      alert() {},
    };
    // A browser makes `window.foo = ...` a global; a vm context does not, so
    // window has to be the sandbox itself for the page's bare gfLoadSolutions()
    // call to resolve.
    sandbox.window = sandbox;
    vm.createContext(sandbox);
    vm.runInContext(fs.readFileSync(LOADER, 'utf8'), sandbox);

    const html = fs.readFileSync(path.join(SITE, 'recommended.html'), 'utf8');
    const scripts = inlineScripts(html);
    assert.ok(scripts.length >= 1, 'recommended.html has an inline script');
    for (const code of scripts) vm.runInContext(code, sandbox);

    await new Promise((r) => setTimeout(r, 400));

    const expected = readJson(SNAPSHOT).solutions.filter((s) => s.verification_status === 'VERIFIED').length;
    const cards = nodes.get('pickList').children.length;
    assert.equal(cards, expected, `rendered ${cards} cards, expected ${expected} verified solutions`);
    assert.ok(cards > 0, 'a visitor must see at least one real recommendation');
    const status = nodes.get('status').textContent;
    assert.match(status, /Static snapshot/, 'the page must say the data came from the snapshot');
    assert.doesNotMatch(status, /Temporarily unavailable/);
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
});

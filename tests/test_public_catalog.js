// Tests for lib/public_catalog.js -- the public, read-only product view.
// Every test builds its own temp factory folder; the real data/ is never read.
//
//   node --test tests/test_public_catalog.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const catalog = require('../lib/public_catalog.js');

function factory(files = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'gf-public-catalog-'));
  for (const [rel, body] of Object.entries(files)) {
    const p = path.join(root, rel);
    fs.mkdirSync(path.dirname(p), { recursive: true });
    fs.writeFileSync(p, typeof body === 'string' ? body : JSON.stringify(body));
  }
  return root;
}

const MANIFEST = {
  id: 'B14-001',
  title: 'Cash Flow Forecast',
  price_cents: 1900,
  files: { cover: { path: 'books/covers/B14-001.png' } },
  qa: { listing: { description_html: '<p>See every week&#x27;s cash position &amp; spot tight weeks.</p>' } },
};

const REGISTRY = {
  products: [
    { internal_id: 'B14-001', title: 'Cash Flow Forecast', price_cents: 1900, published: true,
      url: 'https://aekraft.gumroad.com/l/cash', manifest: 'books/batch14/B14-001/manifest.json',
      sales_count: 12, external_ids: { gumroad: 'secret-id' } },
    { internal_id: 'B14-002', title: 'No Cover', price_cents: 2500, published: true,
      url: 'https://aekraft.gumroad.com/l/nocover', primary_state: 'PUBLIC_LISTING_VERIFIED' },
    { internal_id: 'B14-003', title: 'Bad Host', price_cents: 1000, published: true,
      url: 'https://evil.example/l/bad', manifest: 'books/batch14/B14-003/manifest.json' },
    { internal_id: 'B15-001', title: 'Not Published', price_cents: 4900, published: false,
      url: null, manifest: 'books/batch15/B15-001/manifest.json' },
  ],
};

function baseFiles() {
  return {
    'data/product_registry.json': REGISTRY,
    'books/batch14/B14-001/manifest.json': MANIFEST,
    'books/covers/B14-001.png': 'png',
    'books/batch15/B15-001/manifest.json': { files: { cover: { path: 'books/covers/B15-001.png' } } },
  };
}

test('only published products with a real Gumroad URL are public', () => {
  const d = catalog.catalog({ root: factory(baseFiles()), now: new Date('2026-10-25T00:00:00Z'), limit: 12, featuredOnly: false });
  assert.deepEqual(d.products.map((p) => p.id), ['B14-001', 'B14-002']);
  assert.equal(d.counts.published_total, 2);
  assert.equal(d.counts.returned, 2);
});

test('the public shape never carries private registry fields', () => {
  const d = catalog.catalog({ root: factory(baseFiles()), limit: 12, featuredOnly: false });
  const text = JSON.stringify(d);
  assert.ok(!text.includes('sales_count'));
  assert.ok(!text.includes('external_ids'));
  assert.ok(!text.includes('secret-id'));
  assert.ok(!text.includes('B14-001/manifest.json'));
  assert.ok(!text.includes('books/covers'));
  assert.ok(!text.includes('data/product_registry.json'));
  assert.ok(!text.includes('Not Published'));
});

test('the featured view needs both a real cover file and real listing copy', () => {
  const d = catalog.catalog({ root: factory(baseFiles()), limit: 12 });
  assert.equal(d.products.length, 1);
  assert.equal(d.products[0].id, 'B14-001');
  assert.equal(d.products[0].cover_url, '/api/public/catalog/cover/B14-001');
  assert.equal(d.products[0].summary, "See every week's cash position & spot tight weeks.");
  assert.equal(d.products[0].price_display, '$19');
  assert.equal(d.products[0].featured, true);
});

test('cover lookup is limited to published products and stays inside the project', () => {
  const root = factory(baseFiles());
  assert.equal(catalog.coverAsset('B14-001', { root }), path.join(root, 'books/covers/B14-001.png'));
  assert.equal(catalog.coverAsset('B15-001', { root }), null);
  assert.equal(catalog.coverAsset('../data/product_registry.json', { root }), null);
  assert.equal(catalog.coverAsset('', { root }), null);
});

test('a manifest cover path cannot escape the project or use another file type', () => {
  const root = factory({
    'data/product_registry.json': { products: [{ internal_id: 'B14-001', title: 'X', price_cents: 100,
      published: true, url: 'https://aekraft.gumroad.com/l/x', manifest: 'manifest.json' }] },
    'manifest.json': { files: { cover: { path: '../../outside.png' } }, qa: { listing: { description_html: '<p>x</p>' } } },
  });
  assert.equal(catalog.coverAsset('B14-001', { root }), null);

  const root2 = factory({
    'data/product_registry.json': { products: [{ internal_id: 'B14-001', title: 'X', price_cents: 100,
      published: true, url: 'https://aekraft.gumroad.com/l/x', manifest: 'manifest.json' }] },
    'manifest.json': { files: { cover: { path: 'data/product_registry.json' } }, qa: { listing: { description_html: '<p>x</p>' } } },
  });
  assert.equal(catalog.coverAsset('B14-001', { root: root2 }), null);
});

test('a missing registry or empty catalog is an honest empty result', () => {
  const root = factory({});
  const d = catalog.catalog({ root });
  assert.deepEqual(d.products, []);
  assert.equal(d.counts.published_total, 0);
  assert.equal(d.counts.returned, 0);
  assert.equal(d.source.updated_at, null);
});

test('prices are formatted from cents, never invented', () => {
  assert.equal(catalog.priceDisplay(1900), '$19');
  assert.equal(catalog.priceDisplay(0), '$0');
  assert.equal(catalog.priceDisplay(null), null);
  assert.equal(catalog.priceDisplay('nope'), null);
});

test('public tool pages load covers from a path the static site actually serves', () => {
  // The storefront is published as a plain static copy of customer_site/
  // (GitHub Pages) AND served under /site/ by Express, whose static root is
  // customer_site/ -- Express deliberately does not serve the repo root, so
  // an /api/ route exists only on Express and a ../ path resolves only on
  // Pages. The one path that works on both is a file inside customer_site/.
  const dir = path.join(__dirname, '..', 'customer_site');
  const files = fs.readdirSync(dir).filter((f) => /^tool-.*\.html$/.test(f));
  assert.ok(files.length > 0);
  for (const f of files) {
    const html = fs.readFileSync(path.join(dir, f), 'utf8');
    for (const match of html.matchAll(/<img[^>]+src="([^"]+)"/g)) {
      const src = match[1];
      if (!/B1[45]-/.test(src)) continue;
      assert.doesNotMatch(src, /^\/api\//, `${f}: an /api/ cover route is Express-only`);
      assert.doesNotMatch(src, /^\.\.\//, `${f}: a ../ path escapes the Pages root`);
      assert.ok(fs.existsSync(path.join(dir, src)), `${f}: ${src} is not a real file inside customer_site/`);
    }
  }
});

test('a product without a manifest is featured from its own listing media', () => {
  // 79 of 102 published products predate the manifest system: their only real
  // cover and copy live in data/public_media.json, filled from their own live
  // listing by scripts/backfill_public_media.py. Without this fallback they
  // could never appear on the storefront at all.
  const files = baseFiles();
  files['data/public_media.json'] = {
    products: {
      'B14-002': {
        cover: 'customer_site/assets/covers/B14-002.png',
        summary: 'Two-page planner that turns a lump sum into dated payments.',
        source_url: 'https://aekraft.gumroad.com/l/nocover',
      },
      'B14-003': {
        cover: '../../etc/passwd.png',
        summary: 'must never be served from outside the project',
      },
    },
  };
  files['customer_site/assets/covers/B14-002.png'] = 'png';

  const d = catalog.catalog({ root: factory(files), limit: 12 });
  const ids = d.products.map((p) => p.id);
  assert.ok(ids.includes('B14-002'), 'the manifest-less product is now featureable');
  const product = d.products.find((p) => p.id === 'B14-002');
  assert.equal(product.summary, 'Two-page planner that turns a lump sum into dated payments.');
  assert.match(product.cover_url, /^\/api\/public\/catalog\/cover\//);

  const asset = catalog.coverAsset('B14-002', { root: factory(files) });
  assert.ok(asset && asset.endsWith(path.join('customer_site', 'assets', 'covers', 'B14-002.png')),
    'coverAsset resolves the listing cover so the exporter can copy it');

  assert.equal(catalog.coverAsset('B14-003', { root: factory(files) }), null,
    'a path escaping the project is refused, never served');
});

test('the exported catalog.json points at covers both deployments can serve', () => {
  // Same dual-deployment rule as the tool pages above, applied to the static
  // snapshot GitHub Pages serves. Exported into a temp file so the real
  // customer_site/catalog.json is never rewritten by a test run.
  const { execFileSync } = require('child_process');
  const dir = path.join(__dirname, '..', 'customer_site');
  const out = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'gf-catalog-out-')), 'catalog.json');
  execFileSync(process.execPath, [path.join(__dirname, '..', 'scripts', 'export_public_catalog.js'), '24', out], { stdio: 'pipe' });
  const snapshot = JSON.parse(fs.readFileSync(out, 'utf8'));
  const products = snapshot.data.products;
  // The snapshot states its own coverage gap rather than leaving a reader to
  // recompute it: a published product with no cover is invisible on the site.
  assert.equal(typeof snapshot.data.counts.missing_media, 'number');
  assert.equal(snapshot.data.counts.missing_media,
    snapshot.data.counts.published_total - snapshot.data.counts.available_with_cover);
  assert.ok(products.length > 0);
  for (const p of products) {
    if (!p.cover_url) continue;
    assert.match(p.cover_url, /^assets\/covers\//, `${p.id}: ${p.cover_url}`);
    assert.ok(fs.existsSync(path.join(dir, p.cover_url)), `${p.id}: ${p.cover_url} is missing from customer_site/`);
  }
});

test('no customer_site page points at a root-absolute path only Express can serve', () => {
  // REAL DEFECT, 2026-10-28: login.html redirected to '/site/' after sign-in.
  // That resolves on this factory's own server (which mounts customer_site at
  // /site) and 404s on GitHub Pages, where the same file lives under
  // /openclaw-factory/customer_site/. It is now 'index.html'. This test pins
  // the whole class: every href/src a page really uses must be relative (or a
  // full URL), except /api/ routes, which are deliberately backend-only.
  const dir = path.join(__dirname, '..', 'customer_site');
  const offenders = [];
  const walk = (d) => {
    for (const entry of fs.readdirSync(d, { withFileTypes: true })) {
      const p = path.join(d, entry.name);
      if (entry.isDirectory()) { walk(p); continue; }
      if (!entry.name.endsWith('.html')) continue;
      const html = fs.readFileSync(p, 'utf8');
      for (const match of html.matchAll(/(?:href|src)\s*=\s*['"](\/(?!\/)[^'"]*)['"]/g)) {
        const url = match[1];
        if (url.startsWith('/api/')) continue;
        offenders.push(`${path.relative(dir, p)} -> ${url}`);
      }
    }
  };
  walk(dir);
  assert.deepEqual(offenders, [], 'these 404 on GitHub Pages and only work when Express mounts the site at /site');
});

test('every page that lists products from /api/ can still render them on GitHub Pages', () => {
  // REAL DEFECT, 2026-10-28: index.html fetched /api/customer/catalog and
  // /api/public/catalog?limit=6 with no fallback. GitHub Pages has no Node
  // process, so both homepage product sections showed "Catalog temporarily
  // unavailable" and "No verified releases" to every real visitor while all
  // 102 products were live, priced and covered. Any page that lists products
  // from an Express-only route must also read the static catalog.json
  // snapshot that scripts/export_public_catalog.js writes for Pages.
  const dir = path.join(__dirname, '..', 'customer_site');
  const checked = [];
  for (const f of fs.readdirSync(dir).filter((n) => n.endsWith('.html'))) {
    const html = fs.readFileSync(path.join(dir, f), 'utf8');
    if (!/\/api\/(?:public\/catalog|customer\/catalog)/.test(html)) continue;
    checked.push(f);
    assert.match(html, /catalog\.json/, `${f}: lists products from an Express-only route with no static fallback`);
  }
  assert.ok(checked.includes('index.html'), 'the homepage lists products');
  assert.ok(checked.includes('products.html'), 'the catalog page lists products');
});

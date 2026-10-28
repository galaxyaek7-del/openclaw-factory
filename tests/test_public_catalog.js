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

test('public tool pages load covers through the catalog route, not the unserved books path', () => {
  const dir = path.join(__dirname, '..', 'customer_site');
  const files = fs.readdirSync(dir).filter((f) => /^tool-.*\.html$/.test(f));
  assert.ok(files.length > 0);
  for (const f of files) {
    const html = fs.readFileSync(path.join(dir, f), 'utf8');
    assert.doesNotMatch(html, /\.\.\/books\/covers\//, f);
    for (const match of html.matchAll(/<img[^>]+src="([^"]+)"/g)) {
      if (/B1[45]-/.test(match[1])) {
        assert.match(match[1], /^\/api\/public\/catalog\/cover\//, f);
      }
    }
  }
});

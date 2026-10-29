// Tests for the storefront side of the HOLD control.
//
// Why this exists (2026-10-28): hold_policy.py decided two listings must not
// be promoted, and their own pages said "on hold", but both were still
// published and purchasable on Gumroad. Unpublishing is not reachable through
// Gumroad's public API (PUT published=false answers success and does not
// persist -- proven by re-read), so the store-side mitigation is price $0 and
// the storefront must never advertise them. These tests keep that true.
//
//   node --test tests/test_hold_policy_catalog.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const catalog = require('../lib/public_catalog.js');

const HOLD_FILE = 'data/hold_products.json';

function tempFactory(files = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'gf-hold-catalog-'));
  for (const [rel, body] of Object.entries(files)) {
    const p = path.join(root, rel);
    fs.mkdirSync(path.dirname(p), { recursive: true });
    fs.writeFileSync(p, typeof body === 'string' ? body : JSON.stringify(body));
  }
  return root;
}

function readJson(rel) {
  return JSON.parse(fs.readFileSync(path.join(ROOT, rel), 'utf8'));
}

test('a held listing is never offered by the public catalog', () => {
  const root = tempFactory({
    [HOLD_FILE]: { products: { held1: { product_id: 'x', reason: 'test' } } },
    'data/product_registry.json': {
      products: [
        { internal_id: 'B15-001', title: 'Kept', price_cents: 1500, published: true,
          url: 'https://aekraft.gumroad.com/l/kept' },
        { internal_id: 'GR-0000000001', title: 'Held', price_cents: 0, published: true,
          url: 'https://aekraft.gumroad.com/l/held1' },
        { internal_id: 'GR-0000000002', title: 'Held with query', price_cents: 0, published: true,
          url: 'https://aekraft.gumroad.com/l/HELD1?ref=x' },
      ],
    },
  });
  const d = catalog.catalog({ root, limit: 120, featuredOnly: false });
  assert.deepEqual(d.products.map((p) => p.id), ['B15-001']);
  assert.equal(d.counts.published_total, 1);
  assert.equal(catalog.coverAsset('GR-0000000001', { root }), null);
});

test('data/hold_products.json is exactly what hold_policy.py says it is', () => {
  const out = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'gf-hold-export-')), 'holds.json');
  execFileSync('python', ['hold_policy.py', '--export', out], {
    cwd: ROOT,
    env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
    stdio: 'pipe',
  });
  const exported = JSON.parse(fs.readFileSync(out, 'utf8')).products;
  const committed = readJson(HOLD_FILE).products;
  assert.deepEqual(Object.keys(committed).sort(), Object.keys(exported).sort());
  for (const slug of Object.keys(exported)) {
    assert.equal(committed[slug].product_id, exported[slug].product_id,
      `${slug}: product_id drifted from hold_policy.py`);
    assert.ok(committed[slug].reason, `${slug}: a hold must carry its reason`);
  }
});

test('every held listing is recorded at $0, so the store cannot take money for it', () => {
  const held = readJson(HOLD_FILE).products;
  const registry = readJson('data/product_registry.json');
  const byId = new Map((registry.products || []).map((p) => [p.external_ids && p.external_ids.gumroad, p]));
  for (const [slug, entry] of Object.entries(held)) {
    const record = byId.get(entry.product_id);
    assert.ok(record, `${slug}: held product missing from data/product_registry.json`);
    assert.equal(record.price_cents, 0,
      `${slug}: held listing is priced at ${record.price_cents} cents -- harm mitigation was reverted`);
  }
});

test('the published storefront snapshot carries no held listing', () => {
  const held = Object.keys(readJson(HOLD_FILE).products);
  const snapshot = readJson('customer_site/catalog.json').data;
  assert.ok(snapshot.products.length > 0, 'storefront snapshot is empty');
  for (const slug of held) {
    const pattern = new RegExp('/l/' + slug + '(?:$|[?"#])', 'i');
    assert.ok(!snapshot.products.some((p) => pattern.test(p.url || '')),
      `customer_site/catalog.json still offers /l/${slug}`);
  }
});

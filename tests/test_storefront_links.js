// Storefront link guard.
//
// REAL FINDING, 2026-11-26: customer_site/products.html still carried 14
// "Get it" links to listings the live Gumroad API reports as unpublished
// (the thin drafts), and guide-freelancer-scope-creep.html carried one more
// (fwrjot). A visitor following one of those links reached a product that
// cannot be bought. The official read-only check
// scripts/storefront_commercial_check.py already detects this class on
// products.html; this test makes it a gate and extends the same rule to every
// static page, so a stale curated card cannot silently return.
//
//   node --test tests/test_storefront_links.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const SITE = path.join(ROOT, 'customer_site');

const DRAFTS = [
  'bfdgx', 'eiebdt', 'engiwk', 'fccqk', 'fwrjot', 'ldrdm', 'palmdr',
  'roxdbe', 'tmhlb', 'uwyfje', 'vyitxf', 'yhnyn', 'zfnagp', 'zjwpx',
];

function readJson(rel) {
  return JSON.parse(fs.readFileSync(path.join(ROOT, rel), 'utf8'));
}

function purchasableSlugs() {
  const registry = readJson('data/product_registry.json');
  const held = new Set(Object.keys((readJson('data/hold_products.json').products) || {}));
  let undeliverable = new Set();
  try {
    undeliverable = new Set(Object.keys((readJson('data/undeliverable_products.json').products) || {}));
  } catch (_) { /* optional generated file */ }
  const unsellable = /\[unavailable\]|do not buy|delete me/i;
  const allowed = new Set();
  for (const p of registry.products || []) {
    if (p.published !== true || !p.url) continue;
    const hit = String(p.url).match(/\/l\/([A-Za-z0-9_-]+)/);
    if (!hit) continue;
    const slug = hit[1].toLowerCase();
    if (held.has(slug) || undeliverable.has(slug)) continue;
    if (unsellable.test(String(p.title || ''))) continue;
    allowed.add(slug);
  }
  return allowed;
}

test('the official storefront commercial check passes', () => {
  const run = spawnSync('python', ['-X', 'utf8', 'scripts/storefront_commercial_check.py', '--json'], {
    cwd: ROOT,
    encoding: 'utf8',
    maxBuffer: 4 * 1024 * 1024,
  });
  let report;
  try {
    report = JSON.parse(run.stdout);
  } catch (_) {
    assert.fail('storefront check did not return JSON: '
      + String(run.stderr || run.stdout).slice(0, 600));
  }
  assert.equal(report.status, 'PASS', JSON.stringify(report.findings, null, 1));
  assert.equal(report.counts.ERROR, 0);
});

test('no static page links an unpublished, held, or undeliverable listing', () => {
  const allowed = purchasableSlugs();
  assert.ok(allowed.size > 0, 'the registry has purchasable products');
  const offenders = [];
  for (const name of fs.readdirSync(SITE).filter((n) => n.endsWith('.html'))) {
    const html = fs.readFileSync(path.join(SITE, name), 'utf8');
    for (const m of html.matchAll(/aekraft\.gumroad\.com\/l\/([A-Za-z0-9_-]+)/g)) {
      const slug = m[1].toLowerCase();
      if (!allowed.has(slug)) offenders.push(`${name} -> /l/${slug}`);
    }
  }
  assert.deepEqual(offenders, [], 'these pages link a product that cannot be purchased');
});

test('the 14 stale draft cards are marked held, not linked', () => {
  const html = fs.readFileSync(path.join(SITE, 'products.html'), 'utf8');
  for (const slug of DRAFTS) {
    const href = new RegExp('href="[^"]*/l/' + slug + '(?:[?"#])');
    assert.ok(!href.test(html), `/l/${slug} is still an active checkout href`);
    assert.ok(html.includes(`data-held-product="${slug}"`), `${slug} is not marked held`);
  }
});

test('the freelancer guide no longer sells the held toolkit', () => {
  const html = fs.readFileSync(path.join(SITE, 'guide-freelancer-scope-creep.html'), 'utf8');
  assert.ok(!/href="[^"]*\/l\/fwrjot/.test(html), 'the guide still links /l/fwrjot');
  assert.ok(/On hold/i.test(html), 'the guide does not say the toolkit is on hold');
});

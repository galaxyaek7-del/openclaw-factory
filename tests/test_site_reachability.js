// Reachability test for the static storefront.
//
// REAL FINDING, 2026-10-28: 22 of 86 deployed pages had zero inbound internal
// links, including 5 pages that linked a live, published Gumroad product. A
// page nothing links to is a page a crawler starting at index.html can never
// reach, and a published product nobody can reach is not published.
//
// Rule pinned here: any page that links a PUBLISHED product must itself be
// reachable from another page. Deliberately unlinked pages (proposed drafts,
// login-only pages, internal previews) link no published product, so they are
// never forced into the storefront navigation.
//
//   node --test tests/test_site_reachability.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');

const DIR = path.join(__dirname, '..', 'customer_site');
const ROOT = path.join(__dirname, '..');

function pages() {
  const out = {};
  for (const f of fs.readdirSync(DIR).filter((n) => n.endsWith('.html'))) {
    out[f] = fs.readFileSync(path.join(DIR, f), 'utf8');
  }
  return out;
}

function inboundCounts(all) {
  const counts = {};
  for (const name of Object.keys(all)) counts[name] = 0;
  for (const [name, html] of Object.entries(all)) {
    for (const m of html.matchAll(/href\s*=\s*["']([^"']+)["']/g)) {
      const target = m[1].split('#')[0].split('?')[0].replace(/^\.\//, '');
      if (!target.endsWith('.html')) continue;
      if (target === name) continue;
      if (target in counts) counts[target] += 1;
    }
  }
  return counts;
}

test('every page that links a published product is reachable from another page', () => {
  const registry = JSON.parse(fs.readFileSync(path.join(ROOT, 'data', 'product_registry.json'), 'utf8'));
  const published = new Set();
  for (const p of registry.products || []) {
    if (!p.published || !p.url) continue;
    published.add(String(p.url).replace(/\/+$/, '').split('/').pop());
  }
  assert.ok(published.size > 0, 'the registry has published products to check');

  const all = pages();
  const inbound = inboundCounts(all);
  const unreachable = [];
  for (const [name, html] of Object.entries(all)) {
    const slugs = [...html.matchAll(/aekraft\.gumroad\.com\/l\/([a-z0-9]+)/g)].map((m) => m[1]);
    if (!slugs.some((s) => published.has(s))) continue;
    if (inbound[name] === 0) unreachable.push(name);
  }
  assert.deepEqual(unreachable, [], 'these pages sell a live product but nothing links to them');
});

test('the homepage links every section a visitor is expected to reach', () => {
  const all = pages();
  const home = all['index.html'];
  for (const id of ['services', 'library', 'more', 'request', 'support']) {
    assert.ok(home.includes(`id="${id}"`), `the homepage has no #${id} section`);
  }
  // The "also from" section is the only path to the free tools and the
  // fixed-price services; if its links disappear the pages become orphans again.
  for (const target of ['tool-food-truck-cost-estimator.html', 'tool-saas-waste-estimator.html',
    'service-eu-deadline-briefing.html', 'service-kdp-typesetting.html',
    'service-verified-lead-lists.html', 'affiliate-standing-desks.html', 'interest.html']) {
    assert.ok(home.includes(`href="${target}"`), `index.html no longer links ${target}`);
  }
});

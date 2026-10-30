'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const REGISTRY_FILE = 'data/product_registry.json';
// Real cover + one-line summary for a published product that has no manifest
// of its own (every product published before the manifest system). Written by
// scripts/backfill_public_media.py from the product's own live listing: the
// cover is the listing's own image, the summary its own description text.
// Nothing here is generated copy.
const MEDIA_FILE = 'data/public_media.json';
// Listings this factory has already decided must not be sold (hold_policy.py
// carries the reason for each). Generated from that module by
// `python hold_policy.py --export`, never edited by hand.
//
// This filter exists because the store cannot be withdrawn through Gumroad's
// public API: PUT /v2/products/:id with published=false answers success and
// does not persist (proven by re-read on 2026-10-28 for both held listings).
// The store-side mitigation is price $0 plus an on-hold notice; this is the
// storefront-side half, so a held listing is never advertised here even while
// it remains published on Gumroad.
const HOLD_FILE = 'data/hold_products.json';
// Listings a buyer could pay for and receive nothing: published, priced, no
// file and no delivery URL (found live on 2026-10-30 for /l/svlky and
// /l/ieashv). Same generated-copy contract as HOLD_FILE -- deliverability.py
// is the source, data/undeliverable_products.json is the copy, never edited
// by hand. Withdrawing a listing is still a founder-dashboard action; this
// only stops the storefront from advertising one that cannot deliver.
const UNDELIVERABLE_FILE = 'data/undeliverable_products.json';
// A listing the seller has itself labelled unsellable is never advertised.
// `owtmpe` ("[Unavailable] AI Workflow QA & Stress Test", $0) stayed published
// on Gumroad because the public API cannot withdraw a listing, and the
// storefront grid showed it as a $0 product next to real ones. The label is
// the evidence -- this rule reads the seller's own words, never a guess about
// price, so a genuinely free product is still published normally.
const UNSELLABLE_TITLE = /\[unavailable\]|do not buy|delete me/i;
const GUMROAD_HOSTS = new Set(['gumroad.com', 'www.gumroad.com', 'aekraft.gumroad.com']);
const COVER_EXTENSIONS = new Set(['.png', '.jpg', '.jpeg', '.webp']);

function readJson(p) {
  try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch (_) { return null; }
}

function mtime(p) {
  try { return fs.statSync(p).mtime.toISOString(); } catch (_) { return null; }
}

function inside(root, target) {
  const base = path.resolve(root);
  const resolved = path.resolve(target);
  return resolved === base || resolved.startsWith(base + path.sep);
}

function text(value, max) {
  const clean = String(value == null ? '' : value).replace(/\s+/g, ' ').trim();
  return max && clean.length > max ? clean.slice(0, max).replace(/\s+\S*$/, '') + '...' : clean;
}

function decodeEntities(value) {
  const named = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ', mdash: '-', ndash: '-', hellip: '...' };
  return String(value || '')
    .replace(/&#x([0-9a-f]+);/gi, (_, code) => String.fromCodePoint(parseInt(code, 16)))
    .replace(/&#([0-9]+);/g, (_, code) => String.fromCodePoint(parseInt(code, 10)))
    .replace(/&([a-z]+);/gi, (match, name) => Object.prototype.hasOwnProperty.call(named, name.toLowerCase())
      ? named[name.toLowerCase()] : match);
}

function plainText(html) {
  return text(decodeEntities(String(html || '').replace(/<[^>]*>/g, ' ')), 240);
}

function publicUrl(value) {
  if (typeof value !== 'string' || !/^https:\/\//i.test(value.trim())) return null;
  try {
    const parsed = new URL(value);
    if (!GUMROAD_HOSTS.has(parsed.hostname.toLowerCase())) return null;
    return parsed.toString();
  } catch (_) { return null; }
}

function manifestFor(root, product) {  if (!product || typeof product.manifest !== 'string') return null;
  const abs = path.resolve(root, product.manifest);
  if (!inside(root, abs)) return null;
  return readJson(abs);
}

function mediaFor(root, productId) {
  const wanted = text(productId, 40);
  const empty = { cover: null, summary: null };
  if (!wanted) return empty;
  const media = readJson(path.join(root, MEDIA_FILE));
  const entry = media && media.products && media.products[wanted];
  if (!entry || typeof entry !== 'object') return empty;
  let cover = null;
  const rel = entry.cover;
  if (typeof rel === 'string') {
    const abs = path.resolve(root, rel);
    if (inside(root, abs) && COVER_EXTENSIONS.has(path.extname(abs).toLowerCase())) {
      try {
        if (fs.statSync(abs).isFile()) cover = { abs, rel };
      } catch (_) { cover = null; }
    }
  }
  const summary = typeof entry.summary === 'string' ? text(entry.summary, 400) : null;
  return { cover, summary: summary || null };
}

function coverFor(root, product, manifest) {
  const rel = manifest && manifest.files && manifest.files.cover && manifest.files.cover.path;
  if (typeof rel !== 'string') return null;
  const abs = path.resolve(root, rel);
  if (!inside(root, abs)) return null;
  if (!COVER_EXTENSIONS.has(path.extname(abs).toLowerCase())) return null;
  try {
    if (!fs.statSync(abs).isFile()) return null;
  } catch (_) { return null; }
  return { abs, rel };
}

function priceDisplay(cents) {
  if (cents == null || cents === '') return null;
  const n = Number(cents);
  if (!Number.isFinite(n) || n < 0) return null;
  const dollars = n / 100;
  return '$' + dollars.toLocaleString('en-US', {
    minimumFractionDigits: Number.isInteger(dollars) ? 0 : 2,
    maximumFractionDigits: 2,
  });
}

function slugSet(root, rel) {
  const doc = readJson(path.join(root, rel));
  const products = (doc && doc.products) || {};
  return new Set(Object.keys(products).map((s) => String(s).toLowerCase()));
}

function heldSlugs(root) {
  return slugSet(root, HOLD_FILE);
}

function gumroadSlug(value) {
  const hit = /\/l\/([A-Za-z0-9_-]+)/.exec(String(value || ''));
  return hit ? hit[1].toLowerCase() : null;
}

function catalog({ root = ROOT, now = new Date(), limit = 12, featuredOnly = true } = {}) {
  const registry = readJson(path.join(root, REGISTRY_FILE));
  const products = (registry && Array.isArray(registry.products)) ? registry.products : [];
  const held = heldSlugs(root);
  const undeliverable = slugSet(root, UNDELIVERABLE_FILE);
  const cap = Math.max(1, Math.min(120, Number(limit) || 12));
  const eligible = [];

  for (const p of products) {
    if (!p || p.published !== true) continue;
    const url = publicUrl(p.url);
    if (!url) continue;
    if (held.has(gumroadSlug(url))) continue;
    if (UNSELLABLE_TITLE.test(String(p.title || ''))) continue;
    if (undeliverable.has(gumroadSlug(url))) continue;
    const manifest = manifestFor(root, p);
    const media = mediaFor(root, p.internal_id);
    const cover = coverFor(root, p, manifest) || media.cover;
    const summary = plainText(manifest && manifest.qa && manifest.qa.listing && manifest.qa.listing.description_html)
      || media.summary;
    eligible.push({
      id: text(p.internal_id, 40),
      title: text(p.title, 160),
      price_cents: Number.isFinite(Number(p.price_cents)) ? Number(p.price_cents) : null,
      price_display: priceDisplay(p.price_cents),
      price_note: 'Recorded USD price before taxes. The checkout page shows the final amount.',
      url,
      cover_url: cover ? `/api/public/catalog/cover/${encodeURIComponent(text(p.internal_id, 40))}` : null,
      summary: summary || null,
      format: summary ? 'Gumroad digital download' : 'Digital product on Gumroad',
      featured: Boolean(cover && summary),
    });
  }

  const batchOf = (id) => {
    const hit = /^B(\d+)-/i.exec(String(id || ''));
    return hit ? Number(hit[1]) : -1;
  };
  const ordered = eligible
    .map((p, index) => ({ p, index }))
    .sort((a, b) => (batchOf(b.p.id) - batchOf(a.p.id)) || (a.index - b.index))
    .map((entry) => entry.p);

  const matching = featuredOnly ? ordered.filter((p) => p.featured) : ordered;
  const selected = (matching.length ? matching : ordered).slice(0, cap);

  return {
    generated_at: now.toISOString(),
    source: {
      updated_at: mtime(path.join(root, REGISTRY_FILE)),
      note: 'Published products only. Prices, titles, URLs and covers are read from each product record.',
    },
    counts: {
      published_total: eligible.length,
      available_with_url: eligible.length,
      available_with_cover: eligible.filter((p) => p.cover_url).length,
      returned: selected.length,
    },
    products: selected,
  };
}

function coverAsset(productId, { root = ROOT } = {}) {
  const wanted = text(productId, 40);
  if (!wanted) return null;
  const registry = readJson(path.join(root, REGISTRY_FILE));
  const products = (registry && Array.isArray(registry.products)) ? registry.products : [];
  const held = heldSlugs(root);
  const product = products.find((p) => p && p.internal_id === wanted && p.published === true
    && publicUrl(p.url) && !held.has(gumroadSlug(p.url)));
  if (!product) return null;
  const manifest = manifestFor(root, product);
  const cover = coverFor(root, product, manifest);
  if (cover) return cover.abs;
  const media = mediaFor(root, wanted);
  return media.cover ? media.cover.abs : null;
}

module.exports = { catalog, coverAsset, publicUrl, plainText, priceDisplay, REGISTRY_FILE };

'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const REGISTRY_FILE = 'data/product_registry.json';
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

function manifestFor(root, product) {
  if (!product || typeof product.manifest !== 'string') return null;
  const abs = path.resolve(root, product.manifest);
  if (!inside(root, abs)) return null;
  return readJson(abs);
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

function catalog({ root = ROOT, now = new Date(), limit = 12, featuredOnly = true } = {}) {
  const registry = readJson(path.join(root, REGISTRY_FILE));
  const products = (registry && Array.isArray(registry.products)) ? registry.products : [];
  const cap = Math.max(1, Math.min(24, Number(limit) || 12));
  const eligible = [];

  for (const p of products) {
    if (!p || p.published !== true) continue;
    const url = publicUrl(p.url);
    if (!url) continue;
    const manifest = manifestFor(root, p);
    const cover = coverFor(root, p, manifest);
    const summary = plainText(manifest && manifest.qa && manifest.qa.listing && manifest.qa.listing.description_html);
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
  const product = products.find((p) => p && p.internal_id === wanted && p.published === true && publicUrl(p.url));
  if (!product) return null;
  const manifest = manifestFor(root, product);
  const cover = coverFor(root, product, manifest);
  return cover ? cover.abs : null;
}

module.exports = { catalog, coverAsset, publicUrl, plainText, priceDisplay, REGISTRY_FILE };

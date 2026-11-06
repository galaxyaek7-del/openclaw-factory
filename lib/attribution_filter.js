// Which requests count as an audience VIEW in the attribution ledger (2026-11-06).
//
// server.js recorded EVERY request as a REAL "view": 64,258 ledger rows by 2026-11-06, the latest being the loop's own
// /api/sales/poll call every ten minutes. Internal traffic classified REAL makes every audience figure meaningless
// (Truth First). A view is a person navigating to a page, so these are NOT views: non-GET requests, API calls, health and
// asset requests, anything carrying the internal service token, and loopback requests (the operator, the loop, curl)
// unless the URL itself names a source (?source= or ?utm_source=), which is how a test link is deliberately attributed.

const ASSET = /\.(?:js|mjs|css|map|png|jpe?g|gif|svg|webp|ico|woff2?|ttf|eot|json|xml|txt|pdf|mp4|webm)$/i;
const SKIP_PREFIX = ['/api/', '/attribution', '/health', '/favicon', '/mission', '/assets/'];

function isLoopback(ip) {
  const v = String(ip || '').replace(/^::ffff:/, '');
  return v === '127.0.0.1' || v === '::1' || v === 'localhost';
}

function shouldAutoTrack(req) {
  if (!req || String(req.method || 'GET').toUpperCase() !== 'GET') return false;
  const path = String(req.path || '');
  if (SKIP_PREFIX.some((p) => path.startsWith(p))) return false;
  if (ASSET.test(path)) return false;
  const headers = req.headers || {};
  if (headers['x-internal-token']) return false;
  const q = req.query || {};
  const named = Boolean(q.source || q.utm_source);
  const ip = req.ip || (req.socket && req.socket.remoteAddress) || '';
  if (isLoopback(ip) && !named) return false;
  return true;
}

module.exports = { shouldAutoTrack, isLoopback };

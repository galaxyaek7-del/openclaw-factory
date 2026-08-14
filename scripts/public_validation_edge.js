// Public validation edge proxy (safe external exposure).
//
// Listens on 0.0.0.0:<port> and forwards ONLY the three public validation
// paths to the local factory server at 127.0.0.1:3000. Every other path is
// rejected with 403 BEFORE it can reach the factory, so Mission Control,
// the validation dashboard, and every internal API stay unreachable from
// the public internet even though a tunnel exposes this proxy.
//
// Allowed public paths:
//   GET  /market-validation.html
//   POST /api/validation/submit
//   POST /api/validation/page-view
//
// This proxy does not read, write, or expose any data. It only streams
// requests/responses for the three allowed paths. ?source= query params are
// forwarded verbatim so per-source attribution is preserved.
//
// Usage:
//   node scripts/public_validation_edge.js            (default port 3001)
//   EDGE_PORT=3001 node scripts/public_validation_edge.js
//
//   The process stays running; cloudflared quick tunnel points at it:
//     cloudflared tunnel --url http://127.0.0.1:3001

const http = require('http');

const PORT = parseInt(process.env.EDGE_PORT || '3001', 10);
const UPSTREAM = { host: '127.0.0.1', port: 3000 };

const ALLOWED_PATHS = new Set([
  '/market-validation.html',
  '/api/validation/submit',
  '/api/validation/page-view',
]);

function forward(req, res) {
  const proxyReq = http.request(
    {
      host: UPSTREAM.host,
      port: UPSTREAM.port,
      method: req.method,
      path: req.url,
      headers: req.headers,
    },
    (proxyRes) => {
      res.writeHead(proxyRes.statusCode, proxyRes.headers);
      proxyRes.pipe(res);
    }
  );
  proxyReq.on('error', (err) => {
    res.writeHead(502, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ success: false, error: 'edge upstream unreachable' }));
  });
  req.pipe(proxyReq);
}

const server = http.createServer((req, res) => {
  const pathname = req.url.split('?')[0];
  if (!ALLOWED_PATHS.has(pathname)) {
    res.writeHead(403, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ success: false, error: 'forbidden' }));
    return;
  }
  forward(req, res);
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`public_validation_edge listening on 0.0.0.0:${PORT}`);
});
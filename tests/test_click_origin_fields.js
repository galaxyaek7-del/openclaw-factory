// Backlog B24 (2026-10-29): the click routes record only a coarse user-agent
// class and loopback/external origin. server.js is not require()d (it starts
// the server); the two functions are extracted from its source and evaluated.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');

const src = fs.readFileSync(path.join(__dirname, '..', 'server.js'), 'utf8');
function extract(name) {
  const start = src.indexOf(`function ${name}(`);
  assert.ok(start >= 0, `${name} not found in server.js`);
  let depth = 0;
  for (let i = src.indexOf('{', start); i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}' && --depth === 0) return src.slice(start, i + 1);
  }
  throw new Error(`unbalanced ${name}`);
}
const { clickOriginFields } = new Function(
  `${extract('classifyVisitorAgent')}\n${extract('clickOriginFields')}\nreturn { clickOriginFields };`)();

const req = (ip, ua) => ({ ip, socket: {}, get: (h) => (h.toLowerCase() === 'user-agent' ? ua : undefined) });

test('loopback addresses are internal, everything else external', () => {
  for (const ip of ['127.0.0.1', '::1', '::ffff:127.0.0.1']) {
    assert.equal(clickOriginFields(req(ip, 'Mozilla/5.0')).origin, 'loopback', ip);
  }
  for (const ip of ['203.0.113.9', '::ffff:198.51.100.2', '']) {
    assert.equal(clickOriginFields(req(ip, 'Mozilla/5.0')).origin, 'external', ip);
  }
});

test('only a coarse agent class is kept, never the raw agent or address', () => {
  const f = clickOriginFields(req('203.0.113.9', 'Mozilla/5.0 (Windows NT 10.0) Chrome/120'));
  assert.deepEqual(f, { ua_category: 'browser', origin: 'external' });
  assert.equal(clickOriginFields(req('203.0.113.9', 'curl/8.4')).ua_category, 'bot');
  assert.equal(clickOriginFields(req('203.0.113.9', undefined)).ua_category, 'unknown');
});

test('both click routes pass the fields to Python', () => {
  for (const route of ["'/api/affiliate/click/:product_id'", "'/api/solutions/click/:opportunity_id'"]) {
    const at = src.indexOf(`app.get(${route}`);
    assert.ok(at >= 0, route);
    assert.ok(src.slice(at, at + 600).includes('clickOriginFields(req)'), route);
  }
});

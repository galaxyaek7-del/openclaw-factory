// Outbound attribution tagger in customer_site/assets/gf-pageview.js (2026-11-06).
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const src = fs.readFileSync(path.join(__dirname, '..', 'customer_site', 'assets', 'gf-pageview.js'), 'utf8');

function run(pathname, hrefs, extra = {}) {
  const links = hrefs.map((h) => { const a = { h }; a.getAttribute = () => a.h; a.setAttribute = (_, v) => { a.h = v; }; return a; });
  const document = { querySelectorAll: (sel) => (sel.indexOf('aekraft.gumroad.com/l/') !== -1 ? links : []), querySelector: () => null,
    body: { getAttribute: () => 'p' }, title: 't' };
  const ctx = { document, location: { pathname }, navigator: { userAgent: extra.ua || 'Mozilla/5.0' }, window: {}, console,
    sessionStorage: { getItem: () => null, setItem: () => {} }, fetch: () => Promise.resolve({ ok: true }) };
  ctx.window = ctx;
  vm.runInNewContext(src, ctx);
  return links.map((l) => l.h);
}

let out = run('/openclaw-factory/customer_site/tool-eaa-penalty-exposure-checker.html', ['https://aekraft.gumroad.com/l/mmpoh']);
assert.strictEqual(out[0], 'https://aekraft.gumroad.com/l/mmpoh?utm_source=site&utm_medium=organic&utm_campaign=tool-eaa-penalty-exposure-checker');
out = run('/x/page.html', ['https://aekraft.gumroad.com/l/abc?ref=1']);
assert.ok(out[0].endsWith('?ref=1&utm_source=site&utm_medium=organic&utm_campaign=page'), 'existing query kept, params appended with &');
out = run('/x/page.html', ['https://aekraft.gumroad.com/l/abc?utm_source=pinterest&utm_medium=social_organic']);
assert.strictEqual(out[0], 'https://aekraft.gumroad.com/l/abc?utm_source=pinterest&utm_medium=social_organic', 'campaign links are left alone');
out = run('/', ['https://aekraft.gumroad.com/l/abc']);
assert.ok(out[0].endsWith('utm_campaign=home'));
out = run('/x/page.html', ['https://aekraft.gumroad.com/l/abc'], { ua: 'Googlebot/2.1 bot' });
assert.ok(out[0].includes('utm_source=site'), 'tagging is independent of the crawler guard (a bot never clicks, harmless)');
console.log('test_gf_outbound_utm: ok');

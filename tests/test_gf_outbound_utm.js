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

// The hosted counter hook: nothing may be injected while GF_COUNTER_CODE is empty or invalid, and exactly one script when it is valid.
// (2026-11-08: the committed file now carries the founder's real code 'aek', so the 'disabled' case is derived by blanking the code.)
{
  const mkCtx = () => {
    const appended = [];
    const document = { querySelectorAll: () => [], querySelector: () => null, body: { getAttribute: () => 'p' }, title: 't',
      createElement: () => ({ setAttribute() {} }), head: { appendChild: (e) => appended.push(e) }, addEventListener() {} };
    const ctx = { document, location: { pathname: '/x.html' }, navigator: { userAgent: 'Mozilla/5.0' }, console,
      sessionStorage: { getItem: () => null, setItem: () => {} }, fetch: () => Promise.resolve({ ok: true }) };
    ctx.window = ctx;
    return { appended, ctx };
  };
  const m = /var GF_COUNTER_CODE = '([^']*)';/.exec(src);
  assert.ok(m && /^[a-z0-9-]{2,40}$/.test(m[1]), 'the committed file carries a valid counter code');
  const blank = mkCtx();
  vm.runInNewContext(src.replace(m[0], "var GF_COUNTER_CODE = '';"), blank.ctx);
  assert.strictEqual(blank.appended.length, 0, 'counter disabled when the code is empty');
  const bad = mkCtx();
  vm.runInNewContext(src.replace(m[0], "var GF_COUNTER_CODE = 'Bad Code!';"), bad.ctx);
  assert.strictEqual(bad.appended.length, 0, 'counter disabled when the code is invalid');
  const on = mkCtx();
  vm.runInNewContext(src, on.ctx);
  assert.strictEqual(on.appended.length, 1, 'a valid code injects exactly one script');
  console.log('test_gf_outbound_utm counter hook: ok');
}
